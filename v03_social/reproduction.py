"""Opt-in reproductive types, partner selection and genetic ancestry."""

import copy
import json
import random
from collections import Counter, deque

from cognition import mutate
from neural_survival import AuditedSimulation, SurvivalBrain, fingerprint
from social_sim import SocialSimulation

MODES = ('asexual', 'random', 'social')


def recombine(a, b, rng):
    """Select whole sparse modules, preserving each module's valid topology."""
    layout = [m['group'] for m in a['modules']]
    if layout != [m['group'] for m in b['modules']] or len(layout) < 2:
        raise ValueError('incompatible neural layouts')
    sources = [rng.randrange(2) for _ in layout]
    i, j = rng.sample(range(len(layout)), 2)
    sources[i], sources[j] = 0, 1
    parents = (a, b)
    scalar_sources = {key: rng.randrange(2) for key in ('lr', 'decay', 'social_gain')}
    result = {key: parents[source][key] for key, source in scalar_sources.items()}
    result['modules'] = [copy.deepcopy(parents[source]['modules'][index])
                         for index, source in enumerate(sources)]
    return result, sources, scalar_sources


class ReproductiveSimulation(AuditedSimulation):
    def __init__(self, *, reproductive_mode='asexual', type_a_probability=.5,
                 interaction_distance=2, founder_a_fraction=None, reproduce=True, **kwargs):
        if reproductive_mode not in MODES or not 0 <= type_a_probability <= 1 or interaction_distance < 0:
            raise ValueError('invalid reproductive configuration')
        if founder_a_fraction is not None and not 0 <= founder_a_fraction <= 1:
            raise ValueError('invalid founder ratio')
        self.reproductive_mode = reproductive_mode
        self.type_a_probability = type_a_probability
        self.interaction_distance = interaction_distance
        self.reproduction_enabled = reproduce
        seed = kwargs.get('seed', 42)
        self.type_rng = random.Random(seed * 9109 + 37)
        self.pair_rng = random.Random(seed * 9311 + 97)
        self.founder_types = []
        if founder_a_fraction is not None:
            count = kwargs.get('population', 30)
            a_count = round(count * founder_a_fraction)
            self.founder_types = ['A'] * a_count + ['B'] * (count-a_count)
            self.type_rng.shuffle(self.founder_types)
        self.reproductive_totals = Counter()
        self.recent_partners = deque(maxlen=60)
        self.recent_births = deque(maxlen=24)
        self.first_birth_tick = None
        super().__init__(mode='rule' if kwargs.get('treatment') == 'A_rule' else 'candidate', **kwargs)
        self.partner_log = (self.output / 'partners.jsonl').open('w', encoding='utf-8')
        (self.output / 'reproduction_config.json').write_text(json.dumps(dict(
            mode=reproductive_mode, type_a_probability=type_a_probability,
            interaction_distance=interaction_distance, founder_a_fraction=founder_a_fraction,
            sharing=self.allow_sharing, reproduce=reproduce), indent=2), encoding='utf-8')
        (self.output / 'founders.json').write_text(json.dumps([dict(
            id=o.id, position=o.position, genome=o.genome, type=o.reproductive_type,
            neural=o.brain.genetic if o.brain else None) for o in self.organisms]), encoding='utf-8')

    def assign_type(self, organism, parents=()):
        if not parents and self.founder_types:
            organism.reproductive_type = self.founder_types[organism.id-1]
        else:
            organism.reproductive_type = 'A' if self.type_rng.random() < self.type_a_probability else 'B'
        organism.reproductive_record = dict(parent_ids=[p.id for p in parents],
                                            reproductive_type=organism.reproductive_type)

    def birth(self, parent=None):
        if parent is not None:
            raise ValueError('v0.3.2 births go through the reproductive phase')
        organism = super().birth()
        self.assign_type(organism)
        return organism

    def child(self, parents):
        first = parents[0]
        sources = scalar_sources = None
        if len(parents) == 1:
            child = SocialSimulation.birth(self, first)
            gene = child.brain.genetic if child.brain else None
        else:
            second = parents[1]
            child = SocialSimulation.birth(self)
            genetics = random.Random(self.seed_value * 1000003 + child.id * 9176)
            child.parent_id = first.id
            child.position = first.position
            child.energy = self.birth_energy
            child.generation = max(p.generation for p in parents) + 1
            child.genome = {key: genetics.choice((first.genome[key], second.genome[key]))
                            for key in first.genome}
            if not self.freeze and not self.baseline:
                for key, value in child.genome.items():
                    if genetics.random() < self.rate:
                        child.genome[key] = max(.01, min(6, value + genetics.gauss(0, self.strength)))
            gene = None
            if first.brain:
                gene, sources, scalar_sources = recombine(first.brain.genetic, second.brain.genetic, genetics)
                if not self.freeze:
                    gene = mutate(gene, genetics)
        if gene is not None:
            child.brain = SurvivalBrain(gene, self.social_on, self.neural_learning)
            self.mask_sharing(child)
            assert [module.p for module in child.brain.modules] == child.brain.genetic['modules']
            assert not child.brain.memory.long and not child.brain.memory.working
            assert not any(any(module.state) for module in child.brain.modules)
        assert not child.memory and not child.social.people
        self.assign_type(child, parents)
        return child, sources, scalar_sources

    @staticmethod
    def distance(a, b):
        return sum(abs(x-y) for x, y in zip(a.position, b.position))

    def partner_score(self, a, b, distance):
        earlier = a.social.people.get(b.id, {})
        return (a.social.bond(b.id) + min(1, earlier.get('received', 0.) / 12)
                + b.energy / 100 + b.health / 200 - .2 * distance)

    def eligible(self, o):
        return (o.alive and o.mature and o.energy >= self.reproduction_threshold
                and o.age-o.last_birth_age >= self.birth_cooldown)

    def reproduce_lifetime(self, survivors):
        self.reproductive_totals['mature_ticks'] += sum(o.mature for o in survivors)
        if not self.reproduction_enabled:
            return []
        ready = {o.id for o in survivors if self.eligible(o)}
        opportunities = Counter()
        compatible = {}
        if self.reproductive_mode != 'asexual':
            # Count each unordered compatible pair once per tick.
            for i, a in enumerate(survivors):
                for b in survivors[i+1:]:
                    if a.reproductive_type == b.reproductive_type:
                        continue
                    distance = self.distance(a, b)
                    if distance > self.interaction_distance:
                        continue
                    opportunities['encounters'] += 1
                    if a.mature and b.mature:
                        opportunities['opportunities'] += 1
                        if a.id in ready and b.id in ready:
                            opportunities['ready_pairs'] += 1
                            compatible.setdefault(a.id, []).append((b, distance))
                            compatible.setdefault(b.id, []).append((a, distance))
        self.reproductive_totals.update(opportunities)
        candidates = [o for o in survivors if o.id in ready]
        self.pair_rng.shuffle(candidates)
        newborns = []
        for initiator in candidates:
            if len(survivors) + len(newborns) >= self.max_population:
                break
            if initiator.id not in ready:
                continue
            parents = (initiator,)
            if self.reproductive_mode != 'asexual':
                options = [(o, d) for o, d in compatible.get(initiator.id, ()) if o.id in ready]
                if not options:
                    continue
                if len(options) > 1:
                    self.reproductive_totals['multi_partner_choices'] += 1
                self.pair_rng.shuffle(options)
                if self.reproductive_mode == 'social':
                    mate, distance = max(options, key=lambda pair: self.partner_score(initiator, *pair))
                else:
                    mate, distance = options[0]
                parents = (initiator, mate)
                event = dict(tick=self.world.tick, initiator=initiator.id, partner=mate.id,
                             distance=distance, bond=initiator.social.bond(mate.id),
                             prior_received=initiator.social.people.get(mate.id, {}).get('received', 0.),
                             options=len(options))
                self.recent_partners.append(event)
                self.reproductive_totals['selected_bond_sum'] += event['bond']
                self.reproductive_totals['successful_pairs'] += 1
            child, sources, scalar_sources = self.child(parents)
            debit = self.reproduction_cost / len(parents)
            energies = [parent.energy for parent in parents]
            for parent in parents:
                parent.energy -= debit
                parent.last_birth_age = parent.age
                parent.offspring += 1
                self.transitions.get(parent.id, {})['birth_debit'] = debit
                ready.remove(parent.id)
                self.reproductive_totals[f'parent_{parent.reproductive_type}'] += 1
            self.total_births += 1
            self.max_generation = max(self.max_generation, child.generation)
            if self.first_birth_tick is None:
                self.first_birth_tick = self.world.tick
            record = dict(tick=self.world.tick, id=child.id, parent_id=initiator.id,
                          **child.reproductive_record, generation=child.generation,
                          parent_types=[p.reproductive_type for p in parents],
                          energy_before=energies, contributions=[debit]*len(parents),
                          child_energy=child.energy, genome=child.genome,
                          neural=child.brain.genetic if child.brain else None,
                          parent_genomes=[dict(body=p.genome,
                                               neural_sha=fingerprint(p.brain.genetic) if p.brain else None)
                                          for p in parents],
                          module_sources=sources, scalar_sources=scalar_sources)
            self.births.write(json.dumps(record) + '\n')
            if len(parents) == 2:
                event['child'] = child.id
                self.partner_log.write(json.dumps(event) + '\n')
            self.recent_births.append({key: record[key] for key in ('id', 'tick', 'parent_ids')})
            newborns.append(child)
        return newborns

    def step(self):
        return super().step() or not self.organisms

    def close(self):
        self.partner_log.close()
        super().close()
