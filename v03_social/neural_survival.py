"""Opt-in v0.3.1 policy and audit adapters for the existing simulation."""

import copy
import hashlib
import json
import math
import random
from collections import Counter

from cognition import ACTIONS, Brain, NeuralPolicy, clip, mutate
from organism import DIRECTIONS, WeightedPolicy
from social_sim import SocialSimulation


def fingerprint(genome):
    return hashlib.sha256(json.dumps(genome, sort_keys=True).encode()).hexdigest()


class SurvivalBrain(Brain):
    """Keep the same sparse modules and rotate each group by decision count."""

    temperature = .16

    def forward(self, features, valid, context, has_memory=None):
        if has_memory is None:
            has_memory = bool(self.memory.long)
        relevant = 'social' if self.social_enabled and context else (
            'memory' if has_memory else 'exploration'
        )
        self.active = [self.groups[group][self.decisions % len(self.groups[group])]
                       for group in ('survival', 'coordination', relevant)]
        scores = [0.] * (ACTIONS + 1)
        states = []
        cost = 0
        for index in self.active:
            module = self.modules[index]
            outputs, ops = module.forward(features)
            cost += ops
            scores = [score + output / 3 for score, output in zip(scores, outputs)]
            states.append((index, module.state[:]))
        peak = max(scores[action] for action in valid)
        weights = {action: math.exp((scores[action] - peak) / self.temperature) for action in valid}
        total = sum(weights.values())
        self.decisions += 1
        return scores, {action: weight / total for action, weight in weights.items()}, states, cost

    def decide(self, features, valid, rng, tick, context):
        scores, probabilities, states, cost = self.forward(features, valid, context)
        self.scores = scores
        action = rng.choices(list(probabilities), weights=list(probabilities.values()))[0]
        self.cache = (features, states, probabilities, action, clip(.5 + scores[-1], 0, 1))
        self.use.update(self.active)
        self.ops += cost
        return action, cost

    def learn(self, reward, food):
        organism, observed, birth_cost = self.transition
        action_delta = (organism.energy - observed['energy'] - observed['incoming']
                        + observed.get('birth_debit', birth_cost *
                                       (organism.offspring - observed['offspring'])))
        damage = max(0, observed['health'] - organism.health)
        corrected = clip(action_delta / 10 - damage / 48, -1, 1)
        observed['reward_before'] = reward
        observed['reward_after'] = corrected
        super().learn(corrected, food)
        self.transition = None

    def imitate(self, features, valid, context, target, has_memory):
        _, probabilities, states, _ = self.forward(features, valid, context, has_memory)
        delta = [float(a == target) - probabilities.get(a, 0.) for a in range(ACTIONS)] + [0.]
        for index, hidden in states:
            self.modules[index].learn(features, hidden, delta, .12 / (3 * self.temperature))
        return -math.log(max(1e-12, probabilities[target]))


class CaptureBrain(Brain):
    def decide(self, features, valid, rng, tick, context):
        if self.target in valid:
            self.examples.append((features, valid, context, self.target, bool(self.memory.long)))
        return valid[0], 0


class RandomBrain(Brain):
    def decide(self, features, valid, rng, tick, context):
        return rng.choice(valid), 0


class RandomComputeBrain(SurvivalBrain):
    def decide(self, features, valid, rng, tick, context):
        _, _, _, cost = self.forward(features, valid, context)
        self.ops += cost
        self.use.update(self.active)
        return rng.choice(valid), cost

    def learn(self, reward, food):
        self.transition = None


class LegacyAuditBrain(Brain):
    def decide(self, features, valid, rng, tick, context):
        action, cost = super().decide(features, valid, rng, tick, context)
        # Reconstruct the logits from the hidden states and output weights.
        self.scores = [0.] * (ACTIONS + 1)
        for index, state in self.cache[1]:
            params = self.modules[index].p
            for a in range(ACTIONS + 1):
                self.scores[a] += sum(h * weights[a] for h, weights in zip(state, params['out'])) / 3
        return action, cost


class Demonstrator:
    """Record the neural inputs for actions taken by the existing rule policy."""

    def __init__(self):
        self.rule = WeightedPolicy()
        self.features = NeuralPolicy()

    def choose(self, organism, observations, rng):
        action, destination = self.rule.choose(organism, observations, rng)
        direction = (destination[0] - organism.position[0], destination[1] - organism.position[1])
        target = DIRECTIONS.index(direction) if action == 'move' else {
            'eat': 4, 'rest': 5, 'investigate': 7,
        }.get(action)
        organism.brain.target = target
        saved_direction = organism.direction
        self.features.choose(organism, observations, rng)
        organism.direction = saved_direction
        organism.last_action = target if target is not None else 8
        return action, destination


class AuditedPolicy:
    def __init__(self, sim, policy):
        self.sim = sim
        self.policy = policy

    def choose(self, organism, observations, rng):
        sim = self.sim
        sim.actor = organism
        row = dict(energy=organism.energy, health=organism.health, offspring=organism.offspring,
                   incoming=0., available=dict((pos, food) for pos, _, food in observations)[organism.position])
        traced = organism.id in sim.trace_ids
        if traced:
            row.update(acquired=organism.acquired, position=organism.position)
        sim.transitions[organism.id] = row
        if isinstance(organism.brain, SurvivalBrain):
            organism.brain.transition = organism, row, sim.reproduction_cost
        cost = organism.brain_cost
        action, position = self.policy.choose(organism, observations, rng)
        row.update(action=action, brain=organism.brain_cost - cost)
        cache = organism.brain.cache if organism.brain else None
        if cache:
            probabilities = cache[2]
            row['p_eat'] = probabilities.get(4)
            row['p_range'] = max(probabilities.values()) - min(probabilities.values())
            if traced:
                row.update(probabilities=probabilities, outputs=organism.brain.scores,
                           prediction=cache[-1], active=organism.brain.active)
        return action, position


class AuditedSimulation(SocialSimulation):
    def __init__(self, *, mode, allow_sharing=True, trace_ids=(), runtime=None, **kwargs):
        self.mode = mode
        self.allow_sharing = allow_sharing
        self.trace_ids = set(trace_ids)
        self.runtime = runtime or {}
        self.founders = {}
        self.first_child = None
        self.examples = []
        self.mutations = []
        self.ledger = Counter()
        self.actions = Counter()
        self.trajectory = []
        self.peak_mature_energy = None
        self.max_generation = 1
        super().__init__(**kwargs)
        self.trace = (self.output / 'lifetimes.jsonl').open('w') if self.trace_ids else None
        policy = Demonstrator() if mode == 'teacher' else self.policy
        self.policy = AuditedPolicy(self, policy)
        self.original_eat = self.world.eat
        self.world.eat = self.eat

    def birth(self, parent=None):
        organism = super().birth(parent)
        if organism.brain:
            brain_type = {'candidate': SurvivalBrain, 'teacher': CaptureBrain,
                          'random': RandomBrain, 'random_compute': RandomComputeBrain}.get(self.mode)
            if self.mode == 'legacy' and self.trace_ids:
                brain_type = LegacyAuditBrain
            if brain_type:
                organism.brain = brain_type(organism.brain.genetic, self.social_on, self.neural_learning)
            if self.mode == 'teacher':
                organism.brain.examples = self.examples
            self.mask_sharing(organism)
            if parent is None:
                self.founders[organism.id] = organism.brain
                if organism.id in self.runtime:
                    for module, weights in zip(organism.brain.modules, self.runtime[organism.id]):
                        module.p = copy.deepcopy(weights)
        self.max_generation = max(self.max_generation, organism.generation)
        if parent is not None and organism.brain and self.mode not in ('random', 'teacher'):
            source = parent.brain.genetic
            inherited = organism.brain.genetic
            rng = random.Random(self.seed_value * 1000003 + organism.id * 9176)
            expected = source if self.freeze or self.treatment == 'C_social_fixed' else mutate(source, rng)
            assert inherited == expected
            assert [module.p for module in organism.brain.modules] == inherited['modules']
            assert not organism.brain.memory.long and organism.brain.updates == 0
            if self.first_child is None:
                self.first_child = dict(founder=source, descendant=inherited,
                                        parent=parent.id, child=organism.id, tick=self.world.tick)
            self.mutations.append(dict(
                tick=self.world.tick, parent=parent.id, child=organism.id, generation=organism.generation,
                parent_genotype=fingerprint(source), child_genotype=fingerprint(inherited),
                parent_learned_modules=sum(m.p != g for m, g in zip(parent.brain.modules, source['modules'])),
                mutated_modules=sum(a != b for a, b in zip(source['modules'], inherited['modules'])),
                child_complexity=organism.brain.complexity,
                parent_energy_before_birth=parent.energy + self.reproduction_cost,
            ))
        return organism

    def mask_sharing(self, organism):
        if not self.allow_sharing:
            decide = organism.brain.decide
            def without_sharing(features, valid, rng, tick, context):
                return decide(features, [a for a in valid if a != 6], rng, tick, context)
            organism.brain.decide = without_sharing

    def eat(self, position):
        amount = self.original_eat(position)
        self.ledger['food_retained'] += min(amount, max(0, 100 - self.actor.energy))
        return amount

    def share(self, donor):
        transferred = self.totals['energy_transferred']
        super().share(donor)
        recipient = self.transitions.get(donor.share_target)
        if recipient is not None:
            recipient['incoming'] += self.totals['energy_transferred'] - transferred
        self.transitions[donor.id]['donated'] = self.totals['energy_transferred'] - transferred

    def step(self):
        before = self.organisms[:]
        starting_energy = sum(o.energy for o in before)
        starting_births = self.total_births
        self.transitions = {}
        done = super().step()
        spent = Counter()
        for o in before:
            row = self.transitions[o.id]
            self.actions[row['action']] += 1
            basal = .14 + .08 * (1 - self.world.daylight) + .04 * (1 - o.growth)
            spent['basal'] += basal
            spent['brain'] += row['brain']
            if row['energy'] - row['brain'] - basal > 0 and row['health'] > 0:
                spent['movement'] += .32 if row['action'] == 'move' else 0.
                spent['gateway'] += .2 if row['action'] == 'investigate' else 0.
            if row['available'] > 1:
                self.ledger['food_opportunities'] += 1
                self.ledger['eat_when_available'] += row['action'] == 'eat'
            if row.get('p_eat') is not None:
                self.ledger['eat_probability_sum'] += row['p_eat']
                self.ledger['eat_probability_samples'] += 1
            if 'p_range' in row:
                self.ledger['probability_range_sum'] += row['p_range']
                self.ledger['probability_samples'] += 1
            if 'reward_after' in row:
                self.ledger['reward_changed'] += abs(row['reward_before'] - row['reward_after']) > 1e-9
                self.ledger['reward_sum'] += row['reward_after']
            if o.id in self.trace_ids:
                row.update(tick=self.world.tick, id=o.id, age=o.age, parent=o.parent_id,
                           alive=o.alive, energy_after=o.energy, health_after=o.health,
                           food_acquired=o.acquired-row['acquired'], basal=basal,
                           reward_used=o.brain.last_reward, updates=o.brain.updates,
                           prediction_error=o.brain.last_error, threshold=self.reproduction_threshold)
                self.trace.write(json.dumps(row) + '\n')
            if o.alive and o.mature:
                energy = o.energy + row.get('birth_debit', self.reproduction_cost *
                                           (o.offspring - row['offspring']))
                if self.peak_mature_energy is None or energy > self.peak_mature_energy:
                    self.peak_mature_energy = energy
        spent['birth_net'] = (self.total_births - starting_births) * (self.reproduction_cost - self.birth_energy)
        spent['removed_energy'] = sum(o.energy for o in before if not o.alive)
        self.ledger.update(spent)
        self.ledger['living_energy_change'] += sum(o.energy for o in self.organisms) - starting_energy
        if done or self.world.tick % 20 == 0:
            self.trajectory.append(dict(tick=self.world.tick, living=len(self.organisms),
                                        births=self.total_births, deaths=self.total_deaths,
                                        living_energy=sum(o.energy for o in self.organisms),
                                        max_generation=self.max_generation,
                                        food=self.metrics()['food_consumed'],
                                        updates=self.totals['learning_updates']))
        return done

    def close(self):
        if self.trace is not None:
            self.trace.close()
        super().close()
