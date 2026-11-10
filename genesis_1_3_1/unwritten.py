"""Genesis 1.3.1 headless controlled station trials. No external I/O channels."""

from collections import deque
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
import random
import sys
from time import process_time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "genesis_1_3"))
from population import (Brain, DEFAULT_GENOME, NeuralPolicy, Organism, Region, REGIONS,
                        SocialMemory, State, SurvivalBrain, fingerprint, inputs, load_founder)
from communication import broadcast
from inquiry import (CHANNELS, CONCEPTS, COSTS, OP_ENERGY, OUTCOMES, RELIABILITY,
                     InquiryModel, development_exposure, entropy, learn_concepts, relation_value, render)


DEVELOPMENT = (13100, 13101, 13102)
EVALUATION = tuple(range(13200, 13220))
ARMS = {"neither": (False, False, False), "language": (True, False, False),
        "reference": (False, True, False), "both": (True, True, False),
        "fixed_template": (True, True, True)}
ROUNDS = 8
SLOTS = 2
INITIAL_ENERGY = 45.
TURNS_PER_SLOT = 2
METABOLISM = .18
MIN_RESERVE = 7.
def audit_contexts():
    rng = random.Random(13199)
    return tuple(tuple(rng.choice((-1, 1)) for _ in CONCEPTS) for _ in range(48))


AUDIT_CONTEXTS = audit_contexts()
LEARNED_CONCEPTS = learn_concepts(development_exposure(DEVELOPMENT))


@dataclass(frozen=True)
class Family:
    name: str
    terms: tuple
    latency: int = 1
    change: bool = False


FAMILIES = (Family("signal_cycle", (0, 1)),
            Family("delayed_change", (2, 3), latency=2, change=True),
            Family("group_outcome", (2, 4)),
            Family("contradictory_memory", (5, 6)),
            Family("self_observation", (7, 8)))


def measurement(truth, reliability, rng):
    return truth if rng.random() < reliability else rng.choice(tuple(v for v in OUTCOMES if v != truth))


class Station:
    """Only this evaluator owns hidden response rules and source inventories."""

    def __init__(self, seed, family):
        self.seed, self.family = seed, family
        rng = random.Random(seed)
        self.sign = rng.choice((-1, 1))
        self.contexts = tuple(tuple(rng.choice((-1, 1)) for _ in CONCEPTS) for _ in range(ROUNDS))
        self.world = Region(REGIONS[seed % len(REGIONS)], seed)
        self.peer = Organism(2, 0, (8, 5), DEFAULT_GENOME.copy(), energy=100.)

    def actual(self, context, round_index):
        sign = -self.sign if self.family.change and round_index >= ROUNDS // 2 else self.sign
        return sign * relation_value(context, self.family.terms)

    def physical_available(self, round_index, slot):
        return (self.seed + round_index * SLOTS + slot) % 3 != 0

    @lru_cache(maxsize=128)
    def saved_reading(self, probe, round_index, slot, channel):
        # Independent noise and coverage keyed to public conditions. Reference
        # records can be stale; neither remote source delivers a causal label.
        key = sum((v + 1) * 3**i for i, v in enumerate(probe))
        rng = random.Random(self.seed * 99991 + round_index * 300007 + slot * 23
                            + key * 41 + CHANNELS.index(channel) * 1009)
        index = CHANNELS.index(channel)
        if index and rng.random() < .12:
            return None, "no matching observation"
        measured_at = 0 if channel == "reference" and rng.random() < .35 else round_index
        accuracy = RELIABILITY[index]
        if self.family.name == "contradictory_memory" and channel == "reference":
            accuracy = .60
        value = measurement(self.actual(probe, measured_at), accuracy, rng)
        return value, {"observed_round": measured_at + 1, "source": channel}

    def investigate(self, body, question, round_index, slot, tick, withheld):
        channel = question.channel
        cost = COSTS[CHANNELS.index(channel)]
        if channel == "peer":
            # Transport is reused; its four-symbol field is a carrier. The
            # experimental payload is a typed request, with no learned codebook.
            self.peer.position = (8, 5) if (round_index + slot) % 5 else (12, 5)
            packet, paid = broadcast(body, self.peer, 0, tick, distance_limit=3, cost=cost, latency=1)
            if packet is None:
                return None, "peer outside transmission range", paid
            answer, _ = broadcast(self.peer, body, 0, packet.arrives_at, distance_limit=3,
                                  cost=.10, latency=1)
            if answer is None or answer.arrives_at > tick + TURNS_PER_SLOT:
                return None, "peer response unavailable", paid
        else:
            body.energy -= cost
        if withheld:
            return None, "matched uninformative response", cost
        value, evidence = self.saved_reading(question.intervention, round_index, slot, channel)
        if isinstance(evidence, dict):
            evidence = dict(evidence, delivered_at=tick + (self.family.latency if channel == "physical" else 2))
        return value, evidence, cost

    def audit(self, learner, round_index):
        squared = 0.
        for context in AUDIT_CONTEXTS:
            truth = self.actual(context, round_index)
            squared += sum((p - (truth == outcome))**2
                           for p, outcome in zip(learner.distribution(context), OUTCOMES))
        return squared / len(AUDIT_CONTEXTS)


def new_body(gene, learning, energy=INITIAL_ENERGY, position=(7, 5)):
    body = Organism(1, 0, position, DEFAULT_GENOME.copy(), energy=energy)
    body.brain = SurvivalBrain(gene, social=False, learning=learning)
    body.brain_cost, body.brain_energy_parameter, body.brain_energy_op = 0., .000002, .00001
    body.local_contacts = []
    body.social = SocialMemory()
    return body


def motor_proposal(body, world, motor, rng, radius=2):
    observations = world.observe(body.position, radius=radius)
    proposal = motor.choose(body, observations, rng)
    return proposal, {pos: (tile, stock) for pos, tile, stock in observations}


def best_action(distribution, neural_fallback):
    margin = distribution[2] - distribution[0]
    return (1 if margin > 0 else -1) if abs(margin) > 1e-9 else neural_fallback


def forage(seed, gene, learn):
    """Separate motor assay without the inquiry planner's decision override."""
    world = Region(REGIONS[seed % len(REGIONS)], seed + 83100)
    start = sorted(p for p in world.land if world.tiles[p] == "land")
    body = new_body(gene, learn, position=random.Random(seed + 317).choice(start))
    motor, rng = NeuralPolicy(), random.Random(seed + 312)
    for _ in range(48):
        if not body.alive:
            break
        world.advance()
        energy, health = body.energy, body.health
        body.step(world, rng, motor)
        if learn:
            stock = world.food.get(body.position, 0.)
            Brain.learn(body.brain, max(-1., min(1., (body.energy - energy) / 10.
                                                 - (health - body.health) / 48.)), stock)
            body.brain.memory.observe(body.position, stock, body.age, body.brain.genetic["decay"])
    return dict(forage_food=body.acquired, forage_survived=int(body.alive), forage_ticks=body.age,
                forage_energy=body.energy, forage_neural_ops=body.brain.ops, forage_brain_energy=body.brain_cost)


def trial(seed, family, arm, gene, transition, *, learn=True, blocked=None, trace=False):
    started = process_time()
    symbolic, reference, template = ARMS[arm]
    station = Station(seed, family)
    body, motor, rng = new_body(gene, learn), NeuralPolicy(), random.Random(seed + 82)
    learner = InquiryModel(LEARNED_CONCEPTS, learn)
    remote = ["peer"] * symbolic + ["reference"] * reference
    traces, decisions = [], []
    evidence_energy = modeled_self_error = raw_self_error = 0.
    total_questions = novel = valid = repeated = informative = rejected = no_response = 0
    changed = right = positive_updates = negative_updates = self_samples = 0
    tick = 0
    self_bias, self_history = {}, deque(maxlen=8)
    genome = fingerprint(gene)
    for round_index, current in enumerate(station.contexts):
        if not body.alive:
            break
        radius = 1 if current[8] > 0 else 2
        prior_brain = body.brain_cost
        _, visible = motor_proposal(body, station.world, motor, rng, radius)
        motor_energy = body.brain_cost - prior_brain
        fallback = 1 if body.last_action in (0, 1, 4, 7) else -1
        body.energy -= transition.cost * OP_ENERGY
        _, model_input = inputs(State(body.position, body.energy, (0., 0.), visible), 5)
        raw_prediction = transition.predict(model_input)[0] * 10
        self_key = current[7:9]
        own_prediction = raw_prediction + self_bias.get(self_key, 0.)
        mismatch = abs(self_history[-1]["actual"] - self_history[-1]["forecast"]) if self_history else 0.
        selected_this_round = []
        for slot in range(SLOTS):
            enabled = ["physical"] * station.physical_available(round_index, slot) + remote
            before_ops = learner.operations
            before = learner.distribution(current)
            question = learner.question(current, enabled, template, mismatch)
            if body.energy < MIN_RESERVE:
                question = None
            body.energy -= TURNS_PER_SLOT * METABOLISM
            if question is not None:
                probe, channel = question.intervention, question.channel
                total_questions += 1
                novel += len(question.conditions) > 1
                valid += int(1 <= sum(probe) <= 2 and question.conditions ==
                             tuple(name for name, present in zip(CONCEPTS, probe) if present))
                repeated += any(learner.counts[probe, name] for name in CHANNELS)
                learner.counts[probe, channel] += 1
                error = station.audit(learner, round_index)
                withheld = blocked == (round_index, slot)
                reading, source, paid = station.investigate(body, question, round_index, slot, tick, withheld)
                evidence_energy += paid
                plausibility = None
                if reading is not None:
                    plausibility = learner.observe(probe, reading, RELIABILITY[CHANNELS.index(channel)], channel)
                    informative += question.expected_information > .01
                    rejected += plausibility < .14 and channel != "physical"
                else:
                    no_response += 1
                gain = error - station.audit(learner, round_index)
                positive_updates += gain > 1e-9
                negative_updates += gain < -1e-9
                after = learner.distribution(current)
                changed += best_action(before, fallback) != best_action(after, fallback)
                if trace:
                    event = dict(seed=seed, family=family.name, arm=arm, id=body.id,
                                 genome=genome, generation=body.generation, round=round_index, slot=slot,
                                 tick=tick, uncertainty=entropy(before), question=asdict(question),
                                 rendering=render(question) if symbolic else None, recent_evidence=list(learner.history)[:-1]
                                 if reading is not None else list(learner.history),
                                 own_recent=list(self_history), visible_tiles=len(visible),
                                 brain_cost=body.brain_cost, predicted_self_delta=own_prediction,
                                 own_prior_mismatch=mismatch,
                                 available_channels=enabled, ranker_ops=learner.operations - before_ops,
                                 prediction_before=before, prediction_after=after, evidence=source,
                                 result=reading, plausibility=plausibility, common_brier_gain=gain,
                                 withheld=withheld, ablation=None)
                    selected_this_round.append(event)
                    traces.append(event)
            body.energy -= (learner.operations - before_ops) * OP_ENERGY
            tick += TURNS_PER_SLOT
            body.check_death()
            if not body.alive:
                break
        if not body.alive:
            break
        decision = best_action(learner.distribution(current), fallback)
        outcome = station.actual(current, round_index)
        correct = decision == outcome
        right += correct
        # The local station releases energy or imposes an exposure debit on
        # action. Both choices receive the same delayed observational feedback.
        body.energy += 3. if correct else -3.
        extra_loss = .70 if family.name == "self_observation" and not correct else 0.
        body.energy -= METABOLISM + extra_loss
        self_delta = -METABOLISM - extra_loss - motor_energy - transition.cost * OP_ENERGY
        body.age += TURNS_PER_SLOT * SLOTS + 1
        station.world.advance()
        body.check_death()
        raw_self_error += abs(self_delta - raw_prediction)
        modeled_self_error += abs(self_delta - own_prediction)
        self_samples += 1
        if learn:
            self_bias[self_key] = self_bias.get(self_key, 0.) + .45 * (self_delta - own_prediction)
        self_history.append(dict(action=decision, forecast=own_prediction, actual=self_delta,
                                 visible_tiles=len(visible)))
        before_ops = learner.operations
        learner.observe(current, outcome, .98, "decision")
        body.energy -= (learner.operations - before_ops) * OP_ENERGY
        body.check_death()
        if learn:
            Brain.learn(body.brain, .3 if correct else -.3, 3. if correct else 0.)
        decisions.append(dict(round=round_index, decision=decision, outcome=outcome, correct=correct,
                              energy=body.energy, own_prediction=own_prediction, own_actual=self_delta))
        for event in selected_this_round:
            event["subsequent_decision"] = decisions[-1]
        tick += 1
    row = dict(seed=seed, family=family.name, arm=arm, lifetime_learning=int(learn),
               completed=int(right >= 6 and body.alive), survived=int(body.alive), correct=right,
               decision_rounds=len(decisions), first_correct=int(bool(decisions and decisions[0]["correct"])),
               questions=total_questions, novel=novel, structurally_valid=valid, repeated=repeated,
               distinguishable=informative, no_response=no_response, discounted_answers=rejected,
               positive_updates=positive_updates, negative_updates=negative_updates,
               altered_decisions=changed, final_common_brier=station.audit(learner, ROUNDS - 1),
               energy=body.energy, inquiry_energy=evidence_energy, peer_energy=100. - station.peer.energy,
               brain_energy=body.brain_cost, model_energy=transition.cost * OP_ENERGY * self_samples,
               inquiry_ops=learner.operations, inquiry_compute_energy=learner.operations * OP_ENERGY,
               neural_ops=body.brain.ops, world_model_ops=transition.cost * self_samples,
               self_mae=modeled_self_error / max(1, self_samples), self_fixed_mae=raw_self_error / max(1, self_samples),
               brain_updates=body.brain.updates, genome=genome, cpu_seconds=process_time() - started)
    return row, traces, decisions
