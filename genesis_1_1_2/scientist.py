"""Headless, self-selected factorial experiments with the unchanged neural body."""

import argparse
import csv
import hashlib
import json
import random
import sys
import time
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent/"genesis_1_1_1"))
from run_two_roads import MODEL_PATH, load_model
from two_roads import ENGINE, TrialWorld, direction, make_body
from cognition import NeuralPolicy
from model import EAT, REST, State, imagined, inputs, persistence
from inference import CONFIGS, FOOD_WEIGHT, INFO_HORIZON, LAGS, ResidualModel, features

ARMS = ("fixed", "passive", "random", "active", "oracle")
PHASES = ("discovery", "attribution", "changed_rule", "transfer")
PILOT = (4101, 4102, 4103)
DEVELOPMENT = (301, 302, 303)
ROUNDS = (8, 12, 8, 4)
INITIAL = 12.
TRAVEL_ESTIMATE = 5.
OP_ENERGY = .000002
INFO_OPS = 2400
MAX_MODELED_OPS_PER_TICK = 7400
RANDOM_RATE = .25
GOAL = 2.5
AUDIT_LAG = (4, 2)  # Evaluator only. The learner estimates all eligible patterns.
MARK = ({-1: "jade", 1: "ochre"}, {-1: "indigo", 1: "silver"})


@dataclass(frozen=True)
class Law:
    first: int
    second: int
    stock: int

    def outcome(self, config):
        a, b = config
        return 4.5*(a == self.first)+4.*(b == self.second), 5.+3.5*self.stock*a*b


def laws(seed):
    rng = random.Random(seed+101)
    a, b, r = (rng.choice((-1, 1)) for _ in range(3))
    return Law(a, 0, 0), Law(a, b, r), Law(-a, b, -r)


class Terrain:
    """Two visible switches followed by a corridor to a resource with hidden stock."""

    def __init__(self, seed, transfer=False):
        rng = random.Random(seed)
        rotation = rng.randrange(4)
        tail = ([(2, 3), (2, 4), (3, 4), (3, 5), (3, 6), (4, 6)] if transfer else
                [(3, 2), (4, 2), (5, 2), (6, 2), (7, 2)])

        def orient(p):
            x, y = p
            for _ in range(rotation):
                x, y = -y, x
            return x+9, y+9

        self.start, self.join, self.exit = map(orient, ((0, 0), (1, 1), (2, 2)))
        self.tail = tuple(map(orient, tail))
        self.goal = self.tail[-1]
        self.gates = []
        for positions in (((0, 1), (1, 0)), ((1, 2), (2, 1))):
            signs = list((-1, 1))
            rng.shuffle(signs)
            self.gates.append({v: orient(p) for v, p in zip(signs, positions)})
        self.tiles = {(x, y): "water" for y in range(19) for x in range(19)}
        for p in (self.start, *self.tail):
            self.tiles[p] = "land"
        self.tiles[self.join], self.tiles[self.exit] = "join", "exit"
        self.moves = {self.start: list(self.gates[0].values()), self.join: list(self.gates[1].values())}
        for gate, values in enumerate(self.gates):
            for v, p in values.items():
                self.tiles[p] = MARK[gate][v]
                self.moves[p] = [self.join if gate == 0 else self.exit]
        self.moves.update({p: [q] for p, q in zip((self.exit, *self.tail), self.tail)})
        self.moves[self.goal] = []

    def world(self, body, rng):
        world = TrialWorld.__new__(TrialWorld)
        world.rng, world.tick, world.resource_fraction = rng, 0, 0.
        world.width = world.height = 19
        world.tiles, world.food, world.fruit = self.tiles, {}, (0, 0)
        world.body, world.cap_loss = body, 0.
        return world

    def serialize(self):
        return dict(start=self.start, gates=self.gates, join=self.join, exit=self.exit,
                    tail=self.tail, tiles=[[*p, t] for p, t in self.tiles.items() if t != "water"])


def bounded_pattern(tick, history):
    ages, config = [0, 0], [0, 0]
    for when, gate, choice in history:
        age = tick-when
        if 2 <= age <= 4:
            ages[gate], config[gate] = age, choice
    return tuple(ages), tuple(config)


class Scientist:
    def __init__(self, arm, gene, start, prior=None, frozen=False):
        self.arm, self.frozen = arm, frozen
        self.body = make_body(gene, start)
        self.policy = NeuralPolicy()
        self.model = ResidualModel() if prior is None else deepcopy(prior)
        self.base = load_model() if arm in ("passive", "random", "active") else None

    @property
    def learns(self):
        return self.base is not None and not self.frozen

    def forecast(self, config):
        if self.arm == "oracle":
            loss, stock = self.oracle(config)
            return tuple(loss if lag == AUDIT_LAG else 0. for lag in LAGS), stock
        return self.model.forecast(config)

    def predict(self, x):
        self.inference += self.base.cost if self.base else 16
        self.evaluations += 1
        return self.base.predict(x) if self.base else persistence(x)

    def executable_plan(self, plan):
        return plan

    def score(self, state, config, markers):
        a, b = config
        path = [markers[MARK[0][a]], markers["join"], markers[MARK[1][b]], markers["exit"]]
        estimate = 0.
        for p in (*path, path[-1]):
            action = REST if state.position == p else direction(state.position, p)
            state, gain, damage = imagined(state, action, self.predict)
            estimate += gain-.45*damage
        losses, stock = self.forecast(config)
        loss = sum(losses)
        # Resource value and the last stretch use the same prior for all arms.
        value = estimate-loss + FOOD_WEIGHT*stock
        if loss + TRAVEL_ESTIMATE >= self.body.energy:
            value -= 8.
        return value

    def choose(self, body, observations, rng):
        started = time.process_time()
        local = {p: (tile, stock) for p, tile, stock in observations}
        allowed = self.allowed
        before_ops = self.inference+self.info_ops
        body.brain.allowed = allowed
        self.policy.choose(body, observations, rng)
        action = body.last_action
        state = State(body.position, body.energy, (0., 0.), local)
        if self.tick == 1:
            markers = {tile: p for p, (tile, _) in local.items() if tile != "water"}
            utility = {c: self.score(state, c, markers) for c in CONFIGS}
            tie = {c: self.decision_rng.random() for c in CONFIGS}
            original = next(v for v, t in MARK[0].items() if markers[t] == inputs(state, action)[0])
            def best(values):
                return max(CONFIGS, key=lambda c: (round(values[c], 8), c[0] == original, tie[c]))
            self.greedy = best(utility)
            self.planned = self.greedy
            values = {c: 0. for c in CONFIGS}
            if self.arm == "active" and not self.frozen:
                self.info_ops += INFO_OPS
                values = {c: self.model.information(c, utility) for c in CONFIGS}
                score = {c: utility[c]+INFO_HORIZON*values[c]-INFO_OPS*OP_ENERGY for c in CONFIGS}
                self.planned = best(score)
            elif self.arm == "random" and not self.frozen and self.decision_rng.random() < RANDOM_RATE:
                self.planned = self.decision_rng.choice(CONFIGS)
            self.planned = self.executable_plan(self.planned)
            self.candidates = [
                dict(config=c, utility=utility[c], information_value=values[c],
                     decision_value=utility[c]+INFO_HORIZON*values[c],
                     predicted_loss=sum(self.forecast(c)[0]), predicted_stock=self.forecast(c)[1])
                for c in CONFIGS
            ]
            self.experimental = self.planned != self.greedy
            action = direction(body.position, markers[MARK[0][self.planned[0]]])
        elif self.tick == 3:
            tile = MARK[1][self.planned[1]]
            action = direction(body.position, next(p for p, (t, _) in local.items() if t == tile))
        self.destination, x = inputs(state, action)
        self.pattern, self.observed_config = bounded_pattern(self.tick, self.history)
        self.ordinary = 10*self.predict(x)[0]
        self.predicted = 0.
        if self.pattern in LAGS:
            if self.arm == "oracle":
                self.predicted = self.forecast(self.planned)[0][LAGS.index(self.pattern)]
            else:
                self.predicted = max(0., self.model.loss[self.pattern].mean(
                    features(self.observed_config, self.pattern)))
        self.step_compute = (self.inference+self.info_ops-before_ops)*OP_ENERGY
        body.energy -= self.step_compute
        body.last_action = action
        self.decision_cpu += time.process_time()-started
        if action == REST:
            return "rest", body.position
        if action == EAT:
            return "eat", body.position
        body.direction = action
        return "move", self.destination


def journey(agent, terrain, law, seed, phase, episode, trace, *, start_energy=INITIAL):
    rng = random.Random(seed*1000003 + PHASES.index(phase)*1000+episode)
    agent.decision_rng = random.Random(seed*1777 + PHASES.index(phase)*1000+episode)
    body = agent.body
    body.position, body.energy, body.health, body.alive = terrain.start, start_energy, 100., True
    body.death_cause = None
    agent.history = []
    agent.inference = agent.learning = agent.info_ops = agent.evaluations = 0
    agent.decision_cpu = 0.
    agent.oracle = law.outcome if agent.arm == "oracle" else None
    world = terrain.world(body, rng)
    initial_food, brain_cost = body.acquired, body.brain_cost
    observed_stock = None
    executed = [None, None]
    loss_total = surprise = 0.
    event_at = None
    started = time.process_time()
    for tick in range(1, 22):
        world.advance()
        agent.tick = tick
        here = body.position
        agent.allowed = [direction(here, p) for p in terrain.moves[here]] or [
            EAT if world.food.get(here, 0.) > 1. else REST]
        before_energy, before_brain = body.energy, body.brain_cost
        previous_ops = agent.inference+agent.learning+agent.info_ops
        body.step(world, rng, agent)
        if body.position != here:
            tile = terrain.tiles[body.position]
            for gate, marks in enumerate(MARK):
                for choice, marker in marks.items():
                    if tile == marker:
                        executed[gate] = choice
                        agent.history.append((tick, gate, choice))
        # Hidden environmental rule. Both actions can affect the same later tick.
        if tick == 5:
            if body.alive and None not in executed:
                loss, _ = law.outcome(executed)
                body.energy -= loss
                loss_total += loss
                event_at = tick if loss else None
                body.check_death()
        delta = body.energy-before_energy+(body.brain_cost-before_brain)+agent.step_compute
        update = None
        if agent.pattern in LAGS and before_energy > .75:
            x = features(agent.observed_config, agent.pattern)
            head = agent.model.loss[agent.pattern]
            # Approximate ordinary locomotion with the same measured-physics prior for every arm.
            measured = max(0., -.50-delta)
            if measured < .12:
                measured = 0.
            if abs(measured-agent.predicted) > 2.5:
                surprise += 1
            if agent.learns:
                error, sd = head.update(x, measured)
                agent.learning += 96
                body.energy -= 96*OP_ENERGY
                update = dict(pattern=agent.pattern, residual=error, predictive_sd=sd)
        if body.alive and body.position == terrain.goal and observed_stock is None:
            _, observed_stock = law.outcome(executed)
            world.food[terrain.goal] = observed_stock
            if abs(observed_stock-agent.forecast(agent.planned)[1]) > 2.5:
                surprise += 1
            if agent.learns:
                agent.model.stock.update(features(agent.planned), observed_stock)
                agent.learning += 96
                body.energy -= 96*OP_ENERGY
        body.check_death()
        step_ops = agent.inference+agent.learning+agent.info_ops-previous_ops
        if step_ops > MAX_MODELED_OPS_PER_TICK:
            raise RuntimeError("Shared modeled computation ceiling exceeded")
        body.brain.memory.observe(body.position, world.food.get(body.position, 0.), body.age,
                                  body.brain.genetic["decay"])
        if trace is not None:
            trace.append(dict(seed=seed, phase=phase, arm=agent.arm, episode=episode, tick=tick,
                              before=here, after=body.position, action=body.last_action, energy=body.energy,
                              predicted_delta=agent.ordinary-agent.predicted, actual_delta=delta,
                              model_ops=step_ops, neural_energy=body.brain_cost-before_brain,
                              eligibility=agent.pattern, update=update,
                              candidates=agent.candidates if tick == 1 else [],
                              stock_seen=observed_stock if body.position == terrain.goal else None))
        if not body.alive or body.acquired > initial_food:
            break
    agent.oracle = None
    food = body.acquired-initial_food
    return dict(seed=seed, phase=phase, arm=agent.arm, episode=episode, first=agent.planned[0],
                second=agent.planned[1], greedy_first=agent.greedy[0], greedy_second=agent.greedy[1],
                self_experiment=int(agent.experimental), first_choice_loss=law.outcome(agent.planned)[0],
                loss=loss_total, event_tick=event_at, surprise=int(surprise),
                alive=int(body.alive), success=int(body.alive and food >= GOAL), food=food, ticks=tick,
                stock_seen=observed_stock, end_energy=body.energy,
                energy_spent=start_energy+food-world.cap_loss-body.energy, neural_energy=body.brain_cost-brain_cost,
                model_energy=OP_ENERGY*(agent.inference+agent.learning+agent.info_ops),
                inference_ops=agent.inference, update_ops=agent.learning, information_ops=agent.info_ops,
                evaluations=agent.evaluations, decision_cpu_s=agent.decision_cpu, cpu_s=time.process_time()-started)


class AuditReplay(Scientist):
    """Independent, nonlearning evaluator for the common conditional test panel."""

    def __init__(self, gene, start, config):
        super().__init__("fixed", gene, start, frozen=True)
        self.config = config

    def executable_plan(self, plan):
        return self.config


def contrasts(table):
    return tuple(sum(config[i]*value for config, value in table.items())/2 for i in range(2))


def forecast_table(agent, law):
    agent.oracle = law.outcome if agent.arm == "oracle" else None
    table = {c: agent.forecast(c) for c in CONFIGS}
    agent.oracle = None
    return table


def attribution(table, law):
    predicted = contrasts({c: sum(v[0]) for c, v in table.items()})
    truth = contrasts({c: law.outcome(c)[0] for c in CONFIGS})
    errors = [abs(p-t) for p, t in zip(predicted, truth)]
    wrong = sum(abs(p) > 1. if not t else p*t <= 0. for p, t in zip(predicted, truth))
    spurious = max(abs(coef) for i, lag in enumerate(LAGS) if lag != AUDIT_LAG
                   for coef in contrasts({c: v[0][i] for c, v in table.items()}))
    interaction = sum(c[0]*c[1]*value[1] for c, value in table.items())/4
    return dict(predicted_a=predicted[0], predicted_b=predicted[1], true_a=truth[0], true_b=truth[1],
                attribution_mae=mean(errors), wrong_attributions=wrong, off_lag_contrast=spurious,
                predicted_stock_interaction=interaction,
                identified=int(max(errors) <= 1.5 and abs(interaction-3.5*law.stock) <= 1.5))


def run_seed(seed, gene, trace):
    terrain = Terrain(seed)
    transfer = Terrain(seed+20000, transfer=True)
    single, both, changed = laws(seed)
    diagnostic = {}
    for phase, law in zip(PHASES, (single, both, changed, both)):
        diagnostic[phase] = {}
        for c in CONFIGS:
            # Separate budget prevents censoring stock in the common prediction test.
            audit = journey(AuditReplay(gene, transfer.start, c), transfer, law, seed,
                            phase, 1, None, start_energy=30.)
            assert audit["stock_seen"] is not None
            diagnostic[phase][c] = (audit["loss"], audit["stock_seen"])
    results, audits = [], []
    for arm in ARMS:
        agent_a = Scientist(arm, gene, terrain.start)
        agent_b = Scientist(arm, gene, terrain.start)
        for phase, law, count in zip(PHASES, (single, both, changed, both), ROUNDS):
            agent = {"discovery": agent_a, "attribution": agent_b, "changed_rule": agent_b}.get(phase)
            ground = terrain
            if phase == "transfer":
                agent = Scientist(arm, gene, transfer.start, prior=transfer_prior, frozen=True)
                ground = transfer
            for episode in range(1, count+1):
                result = journey(agent, ground, law, seed, phase, episode, trace)
                table = forecast_table(agent, law)
                results.append({**result, **attribution(table, law)})
            if phase == "attribution":
                transfer_prior = deepcopy(agent.model)
            for c, (loss, stock) in diagnostic[phase].items():
                losses, predicted_stock = table[c]
                errors = [abs(p-(loss if lag == AUDIT_LAG else 0.)) for p, lag in zip(losses, LAGS)]
                audits.append(dict(seed=seed, phase=phase, arm=arm, first=c[0], second=c[1],
                                   predicted_loss=sum(losses), true_loss=loss, predicted_stock=predicted_stock,
                                   true_stock=stock, loss_mae=abs(sum(losses)-loss),
                                   timing_mae=mean(errors), stock_mae=abs(predicted_stock-stock)))
    oracle = {(r["phase"], r["episode"]): r for r in results if r["arm"] == "oracle"}
    for r in results:
        target = oracle[r["phase"], r["episode"]]
        r["regret"] = target["end_energy"]-r["end_energy"]
    return results, audits, dict(development_shape=terrain.serialize(), transfer_shape=transfer.serialize(),
                                  evaluator_laws=[vars(x) for x in (single,both,changed)])


def summarize(rows, audits):
    summary, paired, milestones = [], [], []
    for phase in PHASES:
        phase_rows = [r for r in rows if r["phase"] == phase]
        for arm in ARMS:
            group = [r for r in phase_rows if r["arm"] == arm]
            common = [r for r in audits if r["phase"] == phase and r["arm"] == arm]
            summary.append(dict(phase=phase, arm=arm, journeys=len(group),
                                first_choice_success=sum(r["success"] for r in group if r["episode"] == 1),
                                first_choices=sum(r["episode"] == 1 for r in group),
                                **{k: sum(r[k] for r in group) for k in ("success", "alive", "self_experiment")},
                                **{k: mean(r[k] for r in group) for k in (
                                    "loss", "regret", "energy_spent", "food", "neural_energy", "model_energy",
                                    "inference_ops", "update_ops", "information_ops", "evaluations", "cpu_s",
                                    "wrong_attributions", "off_lag_contrast")},
                                decision_cpu_ms=1000*sum(r["decision_cpu_s"] for r in group)/sum(r["ticks"] for r in group),
                                **{k: mean(r[k] for r in common) for k in ("loss_mae", "stock_mae", "timing_mae")}))
            for seed in sorted({r["seed"] for r in group}):
                sample = [r for r in group if r["seed"] == seed]
                identification = next((r for r in sample if r["identified"]), None)
                upto = identification["episode"] if identification else 0
                milestones.append(dict(phase=phase, arm=arm, seed=seed, first_choice_success=sample[0]["success"],
                                       first_identification_journey=upto or None,
                                       ticks_to_identification=sum(r["ticks"] for r in sample[:upto]) if upto else None,
                                       experiments_to_identification=sum(r["self_experiment"] for r in sample[:upto]) if upto else None,
                                       first_surprise=next((r["episode"] for r in sample if r["surprise"]), None),
                                       unique_configurations=len({(r["first"], r["second"]) for r in sample})))
        seeds = sorted({r["seed"] for r in phase_rows})
        for baseline in ("fixed", "passive", "random"):
            for metric in ("success", "alive", "regret"):
                diffs = []
                for seed in seeds:
                    per_seed = [r for r in phase_rows if r["seed"] == seed]
                    diffs.append(mean(r[metric] for r in per_seed if r["arm"] == "active") -
                                 mean(r[metric] for r in per_seed if r["arm"] == baseline))
                rng = random.Random(83)
                bootstrap = sorted(mean(rng.choices(diffs, k=len(diffs))) for _ in range(2000))
                paired.append(dict(phase=phase, metric=metric, contrast=f"active-minus-{baseline}",
                                   mean=mean(diffs), low=bootstrap[50], high=bootstrap[1949], seeds=len(seeds)))
    return summary, paired, milestones


def csv_write(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--development", action="store_true")
    args = parser.parse_args()
    if args.seeds != 3 and args.seeds < 20:
        parser.error("Use three pilot seeds or at least 20 held-out seeds")
    seeds = DEVELOPMENT if args.development else PILOT if args.seeds == 3 else tuple(range(5100,5100+args.seeds))
    gene_path = ENGINE/"experiments"/"first_survival_v031"/"trained_32.json"
    gene = json.loads(gene_path.read_text(encoding="utf-8"))
    args.out.mkdir(parents=True, exist_ok=False)
    rows, audits, trace, worlds = [], [], [], {}
    for seed in seeds:
        per_seed, panel, world = run_seed(seed, gene, trace)
        rows.extend(per_seed)
        audits.extend(panel)
        worlds[seed] = world
    summary, paired, milestones = summarize(rows, audits)
    for name, data in (("journeys", rows), ("summary", summary), ("paired", paired), ("audit", audits),
                       ("milestones", milestones)):
        csv_write(args.out/f"{name}.csv", data)
    with (args.out/"trace.jsonl").open("w", encoding="utf-8") as file:
        for record in trace:
            file.write(json.dumps(record)+"\n")
    (args.out/"worlds.json").write_text(json.dumps(worlds), encoding="utf-8")
    (args.out/"protocol.json").write_text(json.dumps(dict(
        seeds=seeds, development_seeds=DEVELOPMENT, phases=dict(zip(PHASES, ROUNDS)), arms=ARMS,
        initial_energy=INITIAL, task_food_threshold=GOAL, info_horizon=INFO_HORIZON,
        random_rate=RANDOM_RATE, information_ops=INFO_OPS, operation_energy=OP_ENERGY,
        max_modeled_ops_per_tick=MAX_MODELED_OPS_PER_TICK,
        transfer="pre-change attribution heads copied and frozen; new body, geometry and cue coordinates",
        common_audit="separate forced diagnostic replay; records do not enter any learner",
        hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (gene_path,MODEL_PATH)}
    ), indent=2), encoding="utf-8")
    print(f"{len(rows)} journeys, {len(audits)} common forecast comparisons, {len(trace)} traced decisions")


if __name__ == "__main__":
    main()
