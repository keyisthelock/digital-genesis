"""Run paired Genesis 1.1.1 Two Roads experiments on CPU."""

import argparse
import copy
import hashlib
import json
import random
import time
from collections import OrderedDict
from pathlib import Path
from statistics import mean

from two_roads import (ENGINE, ENERGY, HORIZON, LOW_PENALTY, PENALTY, ROOT, direction,
                       generate, make_body, next_visible)
from temporal import MINIMUM_RESIDUAL, OP_ENERGY, TemporalHead, choose_candidates
from experiment import csv_write
from cognition import NeuralPolicy
from model import EAT, NEAR, State, TransitionModel, inputs, offset, persistence

ARMS = ("reactive", "memory", "fixed", "frozen", "online", "oracle")
DEV = (101, 102, 103)
PILOT = (1201, 1202, 1203)
MODEL_PATH = ROOT.parent/"genesis_1_1"/"results"/"world_model_32"/"model.json"
WINDOW = 4
CAP_OPS = 4200


def load_model():
    model = TransitionModel(3201)
    saved = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    model.hidden, model.output = saved["hidden"], saved["output"]
    return model


class Agent:
    def __init__(self, arm, gene, start, cue_weights=None, freeze=False, explore=0.):
        self.arm = arm
        self.body = make_body(gene, start)
        self.policy = NeuralPolicy()
        self.head = TemporalHead()
        if cue_weights:
            self.head.weights = copy.deepcopy(cue_weights)
        self.model = load_model() if arm in ("online", "frozen") else None
        self.freeze = freeze or arm != "online"
        self.explore = explore
        self.local = OrderedDict()
        self.oracle = None
        self.ops = self.learn_ops = self.evals = 0

    def predict(self, x):
        self.evals += 1
        self.ops += self.model.cost if self.model else 16
        return self.model.predict(x) if self.model else persistence(x)

    def delayed(self, history, tick):
        return self.oracle(history, tick) if self.oracle else self.head.penalty(history, tick)

    def choose(self, body, observations, rng):
        visible = {p: (t, stock) for p, t, stock in observations}
        for p, value in visible.items():
            self.local[p] = value
            self.local.move_to_end(p)
        while len(self.local) > 160:
            self.local.popitem(last=False)
        options = next_visible(visible, body.position, self.previous)
        allowed = [EAT] if visible[body.position][1] > 1 else [direction(body.position, p) for p in options]
        if not allowed:
            raise ValueError(f"Corridor ended without food at {body.position}, previous {self.previous}")
        body.brain.allowed = allowed
        self.policy.choose(body, observations, rng)
        original_action = body.last_action
        choice = original_action
        state = State(body.position, body.energy, (0., 0.), self.local)
        self.candidates = {}
        self.reason = "neural action"
        self.at_fork = len(allowed) == 2
        planner = self.arm not in ("reactive", "memory")
        worst = (1+len(allowed)*HORIZON)*(self.model.cost if self.model else 16)+4*TransitionModel.cost
        funded = body.energy > 1+OP_ENERGY*worst and worst <= CAP_OPS
        if self.at_fork and planner and funded:
            self.candidates = choose_candidates(state, allowed, self.tick, self.previous, self.head,
                                                self.predict, self.delayed, original_action, self.explore)
            choice = max(self.candidates, key=lambda a: self.candidates[a]["score"])
            self.reason = "maximum discounted rollout score"
        if self.at_fork and self.probe is not None:
            choice = self.probe
            self.reason = "paired exploration probe"
        if not funded and planner:
            self.reason = "neural fallback" if self.probe is None else self.reason
        self.destination, self.x = inputs(state, choice)
        if self.at_fork:
            key = self.head.key(self.destination, visible[self.destination][0])
            self.head.history.append((self.tick, key))
        self.expected_loss = self.delayed(self.head.history, self.tick) if planner and funded else 0.
        self.forecast = (self.predict(self.x) if planner and funded else persistence(self.x))
        self.before = list(observations)
        self.accounted_ops = self.ops-self.previous_ops
        body.energy -= self.accounted_ops*OP_ENERGY
        body.last_action = choice
        if choice == EAT:
            return "eat", body.position
        body.direction = choice
        return "move", self.destination


def journey(agent, roads, rng, start, risky, amount, probe, seed, phase, episode, trace):
    body = agent.body
    body.position, body.energy, body.health, body.alive = start, ENERGY, 100., True
    body.death_cause = None
    agent.head.start()
    agent.previous = roads.starts[1] if start == roads.starts[0] else None
    agent.probe = None if probe is None else direction(roads.fork, roads.paths[probe][0])
    world = roads.world(rng, body)
    queue = {}
    goal_food = body.acquired
    lost = mismatch = errors = damage_errors = stock_errors = 0.
    ops, learn_ops, evals, neural = agent.ops, agent.learn_ops, agent.evals, body.brain_cost
    hit_tick = fork_tick = 0
    picked = None
    pre = {}
    first_detection = None
    started = time.process_time()
    if agent.arm == "oracle":
        # This closure is attached to the oracle only. It is removed at the episode boundary.
        key = agent.head.key(roads.paths[risky][0], roads.tiles[roads.paths[risky][0]])
        agent.oracle = lambda h, t: sum(amount for when, ctx in h if ctx == key and t-when == roads.delay)
    for tick in range(1, 26):
        world.advance()
        agent.tick = tick
        agent.previous_ops = agent.ops
        old, health, energy, brain_cost = body.position, body.health, body.energy, body.brain_cost
        body.step(world, rng, agent)
        if agent.at_fork:
            picked = next(i for i, path in roads.paths.items() if agent.destination == path[0])
            fork_tick = tick
            pre = {i: agent.candidates.get(direction(roads.fork, path[0]), {}).get("predicted_penalty", 0.)
                   for i, path in roads.paths.items()}
            if picked == risky and body.position == agent.destination:
                queue[tick+roads.delay] = amount
        penalty = queue.pop(tick, 0.)
        body.energy -= penalty
        body.check_death()
        if penalty:
            hit_tick = tick
        lost += penalty
        actual = body.energy-energy+(body.brain_cost-brain_cost)+agent.accounted_ops*OP_ENERGY
        predicted = 10*agent.forecast[0]-agent.expected_loss
        errors += abs(predicted-actual)
        damage = health-body.health
        damage_errors += abs(12*agent.forecast[1]-damage)
        updates = []
        measured = max(0., 10*persistence(agent.x)[0]-actual)
        observed = {p: stock for p, _, stock in world.observe(body.position)}
        coords = [offset(body.position, d) for d in NEAR]
        mask = [1, 1, *(int(p in observed) for p in coords)]
        stock_errors += sum(abs(30*guess-observed[p]) for p, guess in zip(coords, agent.forecast[2:])
                            if p in observed)/sum(mask[2:])
        if measured > MINIMUM_RESIDUAL and abs(actual-predicted) > MINIMUM_RESIDUAL:
            mismatch += 1
            if first_detection is None:
                first_detection = tick
        if agent.arm != "reactive":
            body.brain.memory.observe(body.position, observed[body.position], body.age, body.brain.genetic["decay"])
        if not agent.freeze and body.alive and body.energy > 1.:
            loss, updates = agent.head.observe(tick, 10*persistence(agent.x)[0], actual)
            target = [(actual+loss)/10, damage/12, *(observed.get(p, 0.)/30 for p in coords)]
            agent.model.update(agent.x, target, mask, rate=.007)
            charge = 4*agent.model.cost+8*len(updates)
            agent.learn_ops += charge
            body.energy -= charge*OP_ENERGY
        if trace is not None:
            trace.append(dict(seed=seed, phase=phase, arm=agent.arm, episode=episode, tick=tick,
                              before_position=old, after_position=body.position, observations=agent.before,
                              action=body.last_action, reason=agent.reason, candidates=agent.candidates,
                              predicted_delta=predicted, actual_delta=actual,
                              predicted_damage=12*agent.forecast[1], actual_damage=damage,
                              error=actual-predicted, updates=updates, energy=body.energy))
        if old != body.position:
            agent.previous = old
        if not body.alive or body.acquired-goal_food >= 10.:
            break
    agent.oracle = None
    post = {}
    for route, path in roads.paths.items():
        ctx = agent.head.key(path[0], roads.tiles[path[0]])
        post[route] = sum(agent.head.penalty(((0, ctx),), lag) for lag in (2, 3, 4))
    found = int(post[risky]-post[1-risky] > MINIMUM_RESIDUAL)
    cpu = time.process_time()-started
    return dict(seed=seed, phase=phase, arm=agent.arm, episode=episode, forced=int(probe is not None),
                route=picked, risky=risky, safe=int(picked == 1-risky), fork_tick=fork_tick,
                event_tick=hit_tick, delay=roads.delay, assigned_penalty=amount, energy_loss=lost,
                pre_risk=pre.get(risky, 0.), pre_safe=pre.get(1-risky, 0.),
                post_risk=post[risky], post_safe=post[1-risky], identified=found,
                mismatches=int(mismatch), detection_tick=first_detection,
                success=int(body.alive and body.acquired-goal_food >= 10), alive=int(body.alive),
                damage=100-body.health, food=body.acquired-goal_food, ticks=tick,
                energy_spent=ENERGY+body.acquired-goal_food-world.cap_loss-body.energy,
                energy_mae=errors/tick, damage_mae=damage_errors/tick, stock_mae=stock_errors/tick,
                inference_ops=agent.ops-ops, update_ops=agent.learn_ops-learn_ops,
                evaluations=agent.evals-evals, neural_ops_energy=body.brain_cost-neural,
                cpu_s=cpu, cpu_per_decision_s=cpu/tick)


def probes(seed):
    p = random.Random(seed+799).randrange(2)
    return p, 1-p


def develop(gene):
    prior = {}
    rows = []
    for seed in DEV:
        roads = generate(seed, cues=True)
        agent = Agent("online", gene, roads.starts[0], prior)
        rng = random.Random(seed+350)
        for i, probe in enumerate(probes(seed)*2, 1):
            rows.append(journey(agent, roads, rng, roads.starts[0], roads.risky, PENALTY,
                                probe, seed, "development", i, None))
        prior = agent.head.weights
    return prior, rows


def run_seed(seed, gene, prior, freeze, explore, trace):
    roads = generate(seed)
    new = generate(seed+30000, alternate=True)
    cued = generate(seed+60000, alternate=True, cues=True)
    rows = []
    for arm in ARMS:
        rng = random.Random(seed+350)
        agent = Agent(arm, gene, roads.starts[0], freeze=freeze, explore=explore)
        paired = probes(seed)
        schedules = [
            ("discovery", roads, agent, roads.risky, PENALTY, roads.starts[0], (None,*paired,None,None,None)),
            ("memory", roads, agent, roads.risky, PENALTY, roads.starts[1], (None,)*3),
            ("adaptation", roads, agent, 1-roads.risky, LOW_PENALTY, roads.starts[1],
             (*paired,*(None,)*(WINDOW-2))),
            ("changed_law", roads, agent, 1-roads.risky, PENALTY, roads.starts[1], (None,)*4),
            ("new_uncued", new, Agent(arm, gene, new.starts[0], freeze=freeze, explore=explore),
             new.risky, PENALTY, new.starts[0], (None,*probes(seed+30000),None,None,None)),
            ("new_cued", cued, Agent(arm, gene, cued.starts[1], prior if arm in ("online","frozen") else None,
                                     freeze=True), cued.risky, PENALTY, cued.starts[1], (None,)*3),
        ]
        for phase, terrain, current, risky, amount, start, schedule in schedules:
            for episode, probe in enumerate(schedule, 1):
                rows.append(journey(current, terrain, rng, start, risky, amount, probe,
                                    seed, phase, episode, trace))
    return rows, dict(original=roads.public(), new_uncued=new.public(), new_cued=cued.public())


def intervals(diffs):
    rng = random.Random(111)
    estimates = sorted(mean(rng.choices(diffs, k=len(diffs))) for _ in range(3000))
    return estimates[75], estimates[2924]


def summarize(rows):
    phases = dict.fromkeys(r["phase"] for r in rows)
    summaries, paired, identification = [], [], []
    for phase in phases:
        for arm in ARMS:
            observed = [r for r in rows if r["phase"] == phase and r["arm"] == arm and not r["forced"]]
            summaries.append(dict(phase=phase, arm=arm, journeys=len(observed),
                                  safe=sum(r["safe"] for r in observed),
                                  success=sum(r["success"] for r in observed),
                                  alive=sum(r["alive"] for r in observed),
                                  **{k: mean(r[k] for r in observed) for k in (
                                      "food", "energy_loss", "energy_spent", "damage", "energy_mae",
                                      "damage_mae", "stock_mae", "inference_ops", "update_ops",
                                      "evaluations", "cpu_per_decision_s", "mismatches")}))
        for metric in ("safe", "success", "energy_spent", "energy_mae"):
            for comparison in ("fixed", "frozen"):
                seeds = sorted({r["seed"] for r in rows if r["phase"] == phase})
                diffs = []
                for seed in seeds:
                    sample = [r for r in rows if r["phase"] == phase and r["seed"] == seed and not r["forced"]]
                    diffs.append(mean(r[metric] for r in sample if r["arm"] == "online") -
                                 mean(r[metric] for r in sample if r["arm"] == comparison))
                low, high = intervals(diffs)
                paired.append(dict(phase=phase, metric=metric, comparison=f"online-minus-{comparison}",
                                   seeds=len(diffs), difference=mean(diffs), low=low, high=high))
    for seed in sorted({r["seed"] for r in rows}):
        for arm in ARMS:
            for phase in ("discovery", "new_uncued", "adaptation", "changed_law"):
                subset = [r for r in rows if r["seed"] == seed and r["arm"] == arm and r["phase"] == phase]
                identified = next((i for i, r in enumerate(subset, 1) if r["identified"]), None)
                detected = next((r["episode"] for r in subset if r["detection_tick"] is not None), None)
                free = [r for r in subset if not r["forced"]]
                stable = next((b["episode"] for a,b in zip(free, free[1:]) if a["safe"] and b["safe"]), None)
                identification.append(dict(seed=seed, arm=arm, phase=phase, initial_route=subset[0]["route"],
                                           initial_safe=subset[0]["safe"], initial_forced=subset[0]["forced"],
                                           first_mismatch_journey=detected, first_identified_journey=identified,
                                           harmful_exposures_to_identification=(
                                               sum(r["event_tick"] > 0 for r in subset[:identified])
                                               if identified is not None else None),
                                           first_two_consecutive_free_safe=stable,
                                           harmful_free_journeys=sum(not r["safe"] for r in free)))
    return summaries, paired, identification


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--modules", type=int, choices=(32, 67), default=32)
    parser.add_argument("--seeds", type=int, default=3, help="3 for pilot, 20 or more for a larger evaluation")
    parser.add_argument("--development", action="store_true", help="test on separate development-only seeds")
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--exploration", type=float, default=0.)
    args = parser.parse_args()
    if args.seeds != 3 and args.seeds < 20:
        parser.error("--seeds must be 3 or at least 20")
    if not 0 <= args.exploration <= .25:
        parser.error("--exploration must be between 0 and .25")
    seeds = (201, 202, 203) if args.development else (
        PILOT if args.seeds == 3 else tuple(range(2200, 2200+args.seeds)))
    args.out.mkdir(parents=True, exist_ok=False)
    genome = ENGINE/"experiments"/"first_survival_v031"/f"trained_{args.modules}.json"
    gene = json.loads(genome.read_text())
    prior, training = develop(gene)
    rows, trace, worlds = [], [], {}
    for seed in seeds:
        result, world = run_seed(seed, gene, prior, args.freeze, args.exploration, trace)
        rows.extend(result)
        worlds[seed] = world
    summary, paired, identification = summarize(rows)
    for name, table in (("journeys", rows), ("summary", summary), ("paired", paired),
                        ("identification", identification), ("development", training)):
        csv_write(args.out/f"{name}.csv", table)
    with (args.out/"trace.jsonl").open("w", encoding="utf-8") as file:
        for row in trace:
            file.write(json.dumps(row)+"\n")
    (args.out/"worlds.json").write_text(json.dumps(worlds))
    config = dict(seeds=seeds, cue_training_seeds=DEV, modules=args.modules, horizon=HORIZON,
                  adaptation_journeys=WINDOW, initial_energy=ENERGY, penalty=PENALTY,
                  low_penalty=LOW_PENALTY, exploration=args.exploration, intrinsic_reward=False,
                  online_frozen=args.freeze, max_ops_per_decision=CAP_OPS,
                  energy_per_estimated_op=OP_ENERGY, prior_sha256=hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest(),
                  genome_sha256=hashlib.sha256(genome.read_bytes()).hexdigest(),
                  cue_prior={str(key): vars(value) for key, value in prior.items()})
    (args.out/"protocol.json").write_text(json.dumps(config, indent=2))
    print(f"{len(rows)} journeys, {len(trace)} traced decisions across {len(seeds)} paired seeds")


if __name__ == "__main__":
    main()
