"""Reproducible single-organism world-model experiment, using the existing engine."""

import argparse
import copy
import csv
import hashlib
import json
import random
import sys
import time
from collections import Counter, OrderedDict
from pathlib import Path
from statistics import mean

from model import DIRECTIONS, NEAR, REST, State, TransitionModel, choose, inputs, legal, offset, persistence

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT.parent / "v03_social"
sys.path.insert(0, str(ENGINE))
from cognition import NeuralPolicy
from neural_survival import SurvivalBrain
from organism import DEFAULT_GENOME, Organism
from social import SocialMemory
from world import World

SCENARIOS = ("route", "moving_food", "delayed_damage", "obstacles")
ARMS = ("original", "memory", "prediction", "planning", "static_planning")
TRAIN = (101, 102, 103)
HELD_OUT = (901, 902, 903)
TICKS = 80
SHIFT = 24
ENERGY = 36
PATCH_STOCK = 25.
HORIZON = 4
OP_ENERGY = .000002
SCALES = (10, 12, 30, 30, 30, 30, 30)


def make_world(scenario, seed, path):
    rng = random.Random(seed)
    width, height = 13, 9
    spawn = (3, 4)
    old = None
    walls, hazards = set(), set()
    if scenario == "route":
        target = (7, 4 + rng.choice((-1, 0, 1)))
        walls = {(5, y) for y in range(2, 7)}
    elif scenario == "moving_food":
        old, target = (4, 4), (8, rng.choice((2, 6)))
        walls = {(6, y) for y in range(2, 7) if y != target[1]}
    elif scenario == "delayed_damage":
        target = (7, rng.choice((3, 5)))
        hazards = {(x, y) for x in (4, 5, 6) for y in (3, 4, 5)}
    else:
        target = (9, rng.choice((2, 4, 6)))
        walls = {(5, y) for y in range(1, 7)} | {(7, y) for y in range(3, 8)}
        walls.remove((5, rng.choice((1, 2))))
        walls.remove((7, rng.choice((6, 7))))
    mirror = rng.choice((False, True))
    mirror_y = rng.choice((False, True))

    def orient(p):
        x, y = p
        return (width-1-x if mirror else x, height-1-y if mirror_y else y)

    tiles = []
    for y in range(height):
        for x in range(width):
            p = (x, y)
            tile = "water" if p in walls or x in (0, width-1) or y in (0, height-1) else (
                "hazard" if p in hazards else "land"
            )
            tiles.append([*orient(p), tile])
    path.write_text(json.dumps(dict(width=width, height=height, fruit=orient((0, 0)),
                                    tiles=tiles, food=[[*orient(old or target), PATCH_STOCK]])))
    return orient(spawn), orient(target), orient(old) if old else None


class TrialWorld(World):
    def eat(self, p):
        gain = super().eat(p)
        self.cap_loss += max(0., self.body.energy + gain - 100.)
        return gain


class Agent:
    def __init__(self, arm, model, intrinsic):
        self.arm, self.model, self.intrinsic = arm, model, intrinsic
        self.policy = NeuralPolicy()
        self.local = OrderedDict()
        self.visits = Counter()
        self.progress = Counter()
        self.exposures = (0., 0.)
        self.ops = self.evaluations = self.fallbacks = 0
        self.planning_energy = self.planning_cpu = 0.

    def choose(self, body, observations, rng):
        self.visits[body.position] += 1
        visible = {p: (tile, food) for p, tile, food in observations}
        if self.arm in ("prediction", "planning", "static_planning"):
            for p, value in visible.items():
                self.local[p] = value
                self.local.move_to_end(p)
            while len(self.local) > 96:
                self.local.popitem(last=False)
        original = self.policy.choose(body, observations, rng)
        action = body.last_action
        self.state = State(body.position, body.energy, self.exposures, visible)
        if self.arm == "collect":
            # A shared development policy gathers transitions. It has no target coordinates.
            if rng.random() < .75:
                action = rng.choice(legal(body.position, visible))
        elif self.arm in ("prediction", "planning", "static_planning"):
            static = self.arm == "static_planning"
            cost = 16 if static else TransitionModel.cost
            horizon = 1 if self.arm == "prediction" else HORIZON
            reserve = OP_ENERGY * cost * (6 + (horizon-1)*36)
            if body.energy > reserve + .6:
                started = time.process_time()
                state = State(body.position, body.energy-reserve, self.exposures, self.local)
                bonus = {a: self.intrinsic*v for a, v in self.progress.items()}
                action, count = choose(state, persistence if static else self.model.predict,
                                       horizon, action, self.visits, action_cost=reserve, bonus=bonus)
                self.charge(body, count*cost)
                self.evaluations += count
                self.planning_cpu += time.process_time()-started
            else:
                self.fallbacks += 1
        if action == body.last_action:
            return original
        body.last_action = action
        if action < 4:
            body.direction = action
            return "move", offset(body.position, DIRECTIONS[action])
        return ("eat" if action == 4 else "rest"), body.position

    def charge(self, body, ops):
        amount = OP_ENERGY*ops
        self.ops += ops
        self.planning_energy += amount
        body.energy -= amount


def trial(path, scenario, seed, arm, gene, spawn, target, old, model=None, intrinsic=0.):
    started = time.process_time()
    rng = random.Random(seed + 50000)
    world = TrialWorld.load(path, rng)
    world.cap_loss = 0.
    body = world.body = Organism(1, 0, spawn, DEFAULT_GENOME.copy(), energy=ENERGY)
    body.brain = SurvivalBrain(gene, social=False, learning=False)
    body.local_contacts = []
    body.social = SocialMemory()
    body.brain_energy_parameter, body.brain_energy_op = .000002, .00001
    body.brain_cost = 0.
    agent = Agent(arm, copy.deepcopy(model) if intrinsic and arm in ("prediction", "planning") else model,
                  intrinsic if arm in ("prediction", "planning") else 0.)
    examples, trace = [], []
    goal_food = immediate_hits = delayed_hits = 0
    for tick in range(1, TICKS+1):
        world.advance()
        energy, health, food = body.energy, body.health, body.acquired
        compute = body.brain_cost + agent.planning_energy
        body.step(world, rng, agent)
        hit = health > body.health
        dose = 9*agent.exposures[1]
        if dose:
            body.health -= dose
            body.pain = max(body.pain, dose)
            body.check_death()
        immediate_hits += hit
        delayed_hits += bool(dose)
        agent.exposures = (float(hit), agent.exposures[0])
        gained = body.acquired-food
        if body.position == target and (not old or tick > SHIFT):
            goal_food += gained
        if old and tick == SHIFT:
            del world.food[old]
            world.food[target] = PATCH_STOCK
        after = {p: food for p, _, food in world.observe(body.position)}
        if arm != "original":
            body.brain.memory.observe(body.position, after[body.position], body.age,
                                      body.brain.genetic["decay"])
        _, x = inputs(agent.state, body.last_action)
        actual_change = body.energy-energy + body.brain_cost+agent.planning_energy-compute
        coords = [offset(body.position, d) for d in NEAR]
        y = [actual_change/10, (health-body.health)/12, *(after.get(p, 0)/30 for p in coords)]
        mask = [1, 1, *(int(p in after) for p in coords)]
        # A basal starvation death can interrupt the selected action before it is applied.
        executed = body.alive or body.death_cause != "starvation" or body.position != agent.state.position
        if executed:
            examples.append((x, y, mask))
        trace.append(dict(scenario=scenario, seed=seed, arm=arm, tick=tick,
                          x=body.position[0], y=body.position[1], action=body.last_action,
                          food=gained, energy=body.energy, damage=health-body.health,
                          delayed_damage=dose, goal_food=goal_food))
        if agent.intrinsic and body.energy > .1 and body.alive:
            def loss():
                return sum(m*(p-t)**2 for p, t, m in zip(agent.model.predict(x), y, mask))
            progress_before = loss()
            agent.model.update(x, y, mask)
            action = body.last_action
            agent.progress[action] = .9*agent.progress[action] + .1*min(1., max(0., progress_before-loss()))
            agent.charge(body, 5*TransitionModel.cost)
        if not body.alive or (goal_food >= 10 and arm != "collect"):
            break
    row = dict(scenario=scenario, seed=seed, arm=arm, success=int(goal_food >= 10 and body.alive),
               alive=int(body.alive), ticks=tick, death=body.death_cause or "",
               food=body.acquired, goal_food=goal_food, energy_spent=ENERGY+body.acquired-world.cap_loss-body.energy,
               energy_left=body.energy, damage=100-body.health, immediate_hits=immediate_hits,
               delayed_hits=delayed_hits, coverage=len(body.visited), neural_energy=body.brain_cost,
               planning_energy=agent.planning_energy, forward_evaluations=agent.evaluations,
               model_ops=agent.ops, fallbacks=agent.fallbacks, planning_cpu_s=agent.planning_cpu,
               cpu_s=time.process_time()-started)
    return row, examples, trace


def errors(examples, predict):
    sums, counts = [0.]*7, [0]*7
    for x, y, mask in examples:
        for i, (actual, forecast, valid) in enumerate(zip(y, predict(x), mask)):
            sums[i] += abs(actual-forecast)*SCALES[i]*valid
            counts[i] += valid
    return dict(n=len(examples), energy_mae=sums[0]/counts[0], damage_mae=sums[1]/counts[1],
                stock_mae=sum(sums[2:])/sum(counts[2:]))


def csv_write(path, rows):
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--modules", type=int, choices=(32, 67), default=32)
    parser.add_argument("--intrinsic", type=float, default=0.)
    args = parser.parse_args()
    if not 0 <= args.intrinsic <= 1:
        parser.error("--intrinsic must be between 0 and 1")
    out = args.out
    (out/"worlds").mkdir(parents=True, exist_ok=False)
    genome = ENGINE/"experiments"/"first_survival_v031"/f"trained_{args.modules}.json"
    gene = json.loads(genome.read_text())
    model = TransitionModel(3201)
    development, results, traces, audits = [], [], [], []
    training_rows = []
    worlds = {}
    for seed in (*TRAIN, *HELD_OUT):
        for scenario in SCENARIOS:
            path = out/"worlds"/f"{scenario}_{seed}.json"
            worlds[scenario, seed] = (path, make_world(scenario, seed, path))
    for seed in TRAIN:
        for scenario in SCENARIOS:
            path, layout = worlds[scenario, seed]
            row, transitions, _ = trial(path, scenario, seed, "collect", gene, *layout)
            training_rows.append(row)
            development.extend(transitions)
    train_started = time.process_time()
    model.fit(development, seed=3202)
    training_cpu = time.process_time()-train_started
    (out/"model.json").write_text(json.dumps(dict(hidden=model.hidden, output=model.output)))
    for scenario in SCENARIOS:
        probe = []
        for seed in HELD_OUT:
            path, layout = worlds[scenario, seed]
            for arm in ARMS:
                row, transitions, trace = trial(path, scenario, seed, arm, gene, *layout, model, args.intrinsic)
                results.append(row)
                traces.extend(trace)
                if arm == "original":
                    probe.extend(transitions)
        damaged = [example for example in probe if example[1][1] > 0]
        for subset, sample in (("all", probe), ("damage", damaged)):
            if sample:
                for name, predict in (("persistence", persistence), ("learned", model.predict)):
                    audits.append(dict(scenario=scenario, subset=subset, predictor=name, **errors(sample, predict)))
    summary = []
    for scenario in (*SCENARIOS, "all"):
        for arm in ARMS:
            rows = [r for r in results if r["arm"] == arm and (scenario == "all" or scenario == r["scenario"])]
            summary.append(dict(scenario=scenario, arm=arm, trials=len(rows),
                                successes=sum(r["success"] for r in rows), alive=sum(r["alive"] for r in rows),
                                **{f"mean_{k}": mean(r[k] for r in rows) for k in (
                                    "ticks", "food", "energy_spent", "damage", "coverage", "planning_energy",
                                    "forward_evaluations", "planning_cpu_s", "cpu_s")}))
    for name, rows in (("results", results), ("summary", summary), ("trace", traces),
                       ("prediction_error", audits), ("training", training_rows)):
        csv_write(out/f"{name}.csv", rows)
    (out/"protocol.json").write_text(json.dumps(dict(modules=args.modules, genome_sha256=hashlib.sha256(
        genome.read_bytes()).hexdigest(), train_seeds=TRAIN, held_out_seeds=HELD_OUT,
        max_ticks=TICKS, relocation_after_tick=SHIFT, initial_energy=ENERGY, patch_stock=PATCH_STOCK,
        delayed_damage=9,
        delay_ticks=2, horizon=HORIZON, beam_width=6, goal_food=10, intrinsic=args.intrinsic,
        model_seed=3201, shuffle_seed=3202, epochs=12, training_transitions=len(development),
        training_cpu_s=training_cpu, op_energy=OP_ENERGY,
        worlds={path.name: dict(spawn=layout[0], target=layout[1], old_food=layout[2],
                                sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                for path, layout in worlds.values()}), indent=2))
    print(f"Wrote {len(results)} held-out trials and {len(traces)} trace rows to {out}")


if __name__ == "__main__":
    main()
