"""Paired curiosity ablation using the unchanged Cognitive Thirst hypothesis model."""

import argparse
import csv
import hashlib
import json
import random
import sys
import time
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent/"genesis_1_1_4"))
from curiosity import ENGINE, MODEL_PATH, MODEL_OPS, TIME_DISCOUNT, INTERVAL_COST
from gateway import Document, Query, interpret
from hypotheses import (Beliefs, DOCUMENT_LABELS, OPTIONS, OUTCOMES,
                        document_likelihood, means, updated, variance)
from scientist import GOAL, INITIAL, OP_ENERGY, Terrain, direction, load_model, make_body
from cognition import NeuralPolicy
from model import State, inputs

ARMS = ("off", "on", "random", "passive", "oracle")
CASES = ("low_cost", "high_cost", "misleading", "irrelevant", "obsolete", "no_value", "split_delay")
DEVELOPMENT = (11501, 11502, 11503)
HELD_OUT = tuple(range(21501, 21521))
TRIPS = 5
CHANGE_AT = 3
MODEL_TICK = 5
OBS_TICKS = (5, 6, 7, 8)
STRENGTH = 4.
RANDOM_RATE = .25


@dataclass(frozen=True)
class Rule:
    first: int
    second: int
    stock: int
    times: tuple
    magnitude: tuple = (4.5, 4.)

    def consequences(self, choice):
        a, b = choice
        first, second = self.magnitude
        loss = tuple(first*(a==self.first and tick==self.times[0])+
                     second*(b==self.second and tick==self.times[1]) for tick in OBS_TICKS)
        return loss, 5.+3.5*self.stock*a*b


class World(Terrain):
    """Public polarity marks identify the two controls. Surface cue IDs are novel."""

    def __init__(self, seed, case, development):
        super().__init__(seed, transfer=True)
        rng = random.Random(seed+8917)
        regime = "cal" if development else "eval"
        self.cues = {}
        for gate, mapping in enumerate(self.gates):
            for sign, position in mapping.items():
                label = f"{regime}-{gate}-{rng.getrandbits(32):08x}"
                self.tiles[position] = label
                self.cues[label] = (gate, sign)
        # Keep the switches local and replace the corridor with a disjoint family of tails.
        origin = self.start
        a = next(p for p in self.gates[0].values() if p[0]!=origin[0])
        b = next(p for p in self.gates[0].values() if p[1]!=origin[1])
        dx, dy = a[0]-origin[0], b[1]-origin[1]
        shape = ([(3,2),(4,2),(4,3),(4,4),(5,4),(6,4)] if development else
                 [(2,3),(3,3),(4,3),(4,4),(5,4),(5,5),(6,5)])
        if seed % 2:
            shape = [(y,x) for x,y in shape]
        for position in self.tail:
            self.tiles[position] = "water"
            self.moves.pop(position)
        self.tail = tuple((origin[0]+x*dx,origin[1]+y*dy) for x,y in shape)
        self.goal = self.tail[-1]
        self.moves.update({p:[q] for p,q in zip((self.exit,*self.tail),self.tail)})
        self.moves[self.goal] = []
        for position in self.tail:
            self.tiles[position] = "land"
        self.tiles[self.start] = "offline_catalog"
        self.case = case


def scenario(seed, case, development):
    rng = random.Random(seed+5721)
    first, second, stock = (rng.choice((-1,1)) for _ in range(3))
    timing = (6,6) if development else (7,7) if seed%2 else (8,8)
    reference = Rule(first,second,stock,timing)
    price = 3.8 if case=="high_cost" else .32
    rule = reference
    if case == "misleading":
        rule = Rule(-first,second,-stock,timing)
    elif case == "no_value":
        rule = Rule(0,0,0,timing)
    elif case == "split_delay":
        rule = Rule(first,second,stock,(6,8),(2.25,4.))
    later = Rule(-first,-second,-stock,timing) if case=="obsolete" else rule
    records = tuple((*choice,sum(loss),food) for choice in OPTIONS
                    for loss,food in (reference.consequences(choice),))
    if case in ("irrelevant","no_value"):
        doc = Document("115-OPTICS", "gloss", "optics", (), "Reference panel reflectance.")
    else:
        doc = Document(f"115-REFERENCE-{seed}", "transitions", "device", records,
                       "Four reference actuator settings with observed energy loss and stock.")
    return World(seed,case,development),rule,later,doc,price


class Gateway:
    def __init__(self, position, document, informative_notice):
        self.position, self.document = position,document
        self.informative_notice = informative_notice
        self.remaining = 1
        self.permit = object()

    def retrieve(self, query, position, permit):
        if (type(query) is not Query or query != Query("transitions","device") or position!=self.position
                or permit is not self.permit or not self.remaining):
            return None
        self.remaining -= 1
        return asdict(self.document)


class Agent:
    def __init__(self, gene, position):
        self.body = make_body(gene,position)
        self.beliefs = Beliefs()
        self.motor = NeuralPolicy()
        self.local_model = load_model()
        self.ops = 0

    def choose(self, body, observations, rng):
        self.motor.choose(body,observations,rng)
        destination = self.destination
        action = 4 if destination==body.position else direction(body.position,destination)
        state = State(body.position,body.energy,(0.,0.),{p:(tile,food) for p,tile,food in observations})
        _,features = inputs(state,action)
        self.local_prediction = self.local_model.predict(features)[0]*10
        self.ops += self.local_model.cost
        body.energy -= OP_ENERGY*self.local_model.cost
        body.last_action = action
        return ("eat" if action==4 else "move"),destination


DOCUMENT_CHANNELS = tuple(document_likelihood(s) for s in DOCUMENT_LABELS)


def options(agent, energy, price, informative_notice):
    """All non-oracle arms compute the same candidate scores."""
    b = agent.beliefs
    utilities = b.utilities(b.weights,energy)
    best = max(utilities)
    spread = variance(b.weights)
    physical = [b.value(b.physical_channels(i,energy),energy,best,spread)[2] for i in range(4)]
    # Measure purchase value with the lower post-purchase energy, before seeing the response.
    purchase_base = max(b.utilities(b.weights,energy-price))
    channels = DOCUMENT_CHANNELS if informative_notice else ((1.,)*len(b.weights),)
    immediate,_,future = b.value(channels,energy-price,purchase_base,spread)
    net = purchase_base-best+immediate-price
    return utilities,physical,net,future


def rank(values, tie):
    return max(range(4),key=lambda i:(round(values[i],9),tie[i]))


def choose(agent, arm, body, gate, price, allowed, rng, rule):
    utilities,physical,net,future = options(agent,body.energy,price,gate.informative_notice)
    tie = [rng.random()+int(choice[0]==agent.neural_first) for choice in OPTIONS]
    greedy = rank(utilities,tie)
    physical_scores = [u+STRENGTH*TIME_DISCOUNT**9*g for u,g in zip(utilities,physical)]
    active = rank(physical_scores,tie)
    selected = greedy
    buy = False
    if arm == "off":
        buy = net>0.
    elif arm == "on":
        selected = active
        buy = net+STRENGTH*TIME_DISCOUNT*future>physical_scores[active]-utilities[greedy]+.005
    elif arm == "random" and rng.random()<RANDOM_RATE:
        buy = rng.random()<.5
        selected = rng.randrange(4)
    elif arm == "oracle":
        def value(index):
            loss,stock = rule.consequences(OPTIONS[index])
            complete = stock>=GOAL and sum(loss)+5.7<body.energy
            return 100.*complete-sum(loss)+stock
        selected = rank([value(i) for i in range(4)],tie)
    requested = bool(buy and allowed and gate.remaining and body.energy>price)
    pre = means(agent.beliefs.weights)
    document = evidence = None
    plan_without = selected
    evidence_changed = False
    if requested:
        query = Query("transitions","device")
        document = gate.retrieve(query,body.position,gate.permit)
        evidence = interpret(query,document)
        body.energy -= price
        same_energy_plan = rank(agent.beliefs.utilities(agent.beliefs.weights,body.energy),tie)
        if evidence is not None:
            agent.beliefs.weights = updated(agent.beliefs.weights,document_likelihood(evidence))
        selected = rank(agent.beliefs.utilities(agent.beliefs.weights,body.energy),tie)
        evidence_changed = selected!=same_energy_plan
    return OPTIONS[selected],dict(purchased=requested,source=document,evidence=evidence,
                                 pre_purchase=pre,post_purchase=means(agent.beliefs.weights),
                                 altered=requested and selected!=plan_without,
                                 evidence_changed=evidence_changed,
                                 candidate_utilities=utilities,physical_information=physical,
                                 immediate_purchase_value=net,future_purchase_value=future,
                                 greedy=OPTIONS[greedy],without_purchase=OPTIONS[plan_without],
                                 physical_test=not requested and selected!=greedy,
                                 paid=price if requested else 0.)


def journey(agent, world, rule, gateway, price, arm, seed, trip, *, allowed=True, forced=None):
    started = time.process_time()
    rng = random.Random(seed*1087+trip)
    body = agent.body
    initial_food, neural_before = body.acquired,body.brain_cost
    initial = 30. if forced is not None else INITIAL
    body.position,body.energy,body.health,body.alive = world.start,initial,100.,True
    body.death_cause = None
    agent.ops = MODEL_OPS
    body.energy -= OP_ENERGY*MODEL_OPS
    habitat = world.world(body,rng)
    body.brain.allowed = [direction(world.start,p) for p in world.moves[world.start]]
    _,proposal = agent.motor.choose(body,habitat.observe(world.start),rng)
    agent.neural_first = world.cues[habitat.tiles[proposal]][1]
    choice,info = choose(agent,arm,body,gateway,price,allowed,rng,rule) if forced is None else (forced,{})
    planning = time.process_time()-started
    if info.get("purchased"):
        habitat.advance()
    losses,stock = rule.consequences(choice)
    observed = [None]*len(OBS_TICKS)
    stock_seen = None
    trace = []
    for tick in range(1,21):
        habitat.advance()
        here = body.position
        destinations = world.moves[here]
        if here in (world.start,world.join):
            gate = int(here==world.join)
            agent.destination = next(p for p in destinations if world.cues[habitat.tiles[p]]==(gate,choice[gate]))
        else:
            agent.destination = destinations[0] if destinations else here
        body.brain.allowed = [direction(here,p) for p in destinations] or [4]
        body.step(habitat,rng,agent)
        if tick in OBS_TICKS and body.alive:
            i = OBS_TICKS.index(tick)
            observed[i] = losses[i]
            body.energy -= losses[i]
            body.check_death()
        if body.alive and body.position==world.goal and stock_seen is None:
            stock_seen = stock
            habitat.food[world.goal] = stock_seen
        body.brain.memory.observe(body.position,habitat.food.get(body.position,0.),body.age,
                                  body.brain.genetic["decay"])
        trace.append(dict(tick=tick,position=body.position,action=body.last_action,
                          motion_forecast=agent.local_prediction,energy=body.energy,
                          observed_loss=observed[OBS_TICKS.index(tick)] if tick in OBS_TICKS else None))
        if not body.alive or body.acquired>initial_food:
            break
    total = sum(v for v in observed if v is not None)
    before_anomaly = agent.beliefs.anomalies
    if arm!="oracle" and forced is None:
        agent.beliefs.observe(choice,total if all(v is not None for v in observed) else None,stock_seen)
    food = body.acquired-initial_food
    return dict(choice=choice,success=int(body.alive and food>=GOAL),alive=int(body.alive),
                food=food,observed_losses=observed,stock_seen=stock_seen,loss=total,
                ticks=tick+int(info.get("purchased",False)),energy=initial+food-habitat.cap_loss-body.energy,
                end_energy=body.energy,neural_energy=body.brain_cost-neural_before,
                model_ops=agent.ops,model_energy=agent.ops*OP_ENERGY,
                anomaly=agent.beliefs.anomalies-before_anomaly,belief=agent.beliefs.description(),
                planning_s=planning,cpu_s=time.process_time()-started,trace=trace,**info)


def errors(forecasts, common):
    amount, trajectory = [], []
    for (predicted_loss,predicted_stock),(losses,stock) in zip(forecasts,common):
        stock_error = abs(predicted_stock-stock)
        amount.append(abs(predicted_loss-sum(losses))+stock_error)
        trajectory.append(stock_error+sum(abs((predicted_loss if tick==MODEL_TICK else 0.)-actual)
                                          for tick,actual in zip(OBS_TICKS,losses)))
    return mean(amount),mean(trajectory)


def common_observations(gene, world, rule, seed):
    observations = []
    for choice in OPTIONS:
        row = journey(Agent(gene,world.start),world,rule,None,0.,"oracle",seed,1,forced=choice)
        observations.append((row["observed_losses"],row["stock_seen"]))
    return observations


def evaluate(seed,gene,development):
    rows,records,audits,worlds = [],[],[],{}
    for case in CASES:
        world,first,later,document,cost = scenario(seed,case,development)
        price = cost+INTERVAL_COST
        worlds[case] = dict(terrain=world.serialize(), cues=world.cues,
                            initial_rule=asdict(first), later_rule=asdict(later),
                            document=asdict(document), price=price)
        common = {rule:common_observations(gene,world,rule,seed) for rule in (first,later)}
        minima = {rule:tuple(min(errors(o,obs)[i] for o in OUTCOMES) for i in (0,1))
                  for rule,obs in common.items()}
        for arm in ARMS:
            agent = Agent(gene,world.start)
            gateway = Gateway(world.start,document,case!="no_value")
            for trip in range(1,TRIPS+1):
                rule = first if trip<=CHANGE_AT else later
                previous = deepcopy(agent) if gateway.remaining and arm in ("on","off","random") else None
                row = journey(agent,world,rule,gateway,price,arm,seed,trip)
                denied = None
                if row["purchased"]:
                    clone_gate = Gateway(world.start,document,case!="no_value")
                    cf = journey(previous,world,rule,clone_gate,price,arm,seed,trip,allowed=False)
                    denied = {k:cf[k] for k in ("choice","success","end_energy","loss","stock_seen","energy")}
                obs = common[rule]
                prior = row["pre_purchase"]
                post_doc = row["post_purchase"]
                post_trip = means(agent.beliefs.weights)
                if arm == "oracle":
                    prior = post_doc = post_trip = [(sum(loss),stock) for loss,stock in obs]
                pre_error,_ = errors(prior,obs)
                doc_error,_ = errors(post_doc,obs)
                total_error,timing_error = errors(post_trip,obs)
                if arm == "oracle":
                    timing_error = 0.
                loss_floor,timing_floor = minima[rule]
                costs = row["paid"]
                key = dict(seed=seed,case=case,arm=arm,trip=trip,changed=int(first!=rule))
                rows.append(dict(**key,**{k:row[k] for k in (
                    "success","alive","purchased","altered","evidence_changed","physical_test","paid",
                    "energy","neural_energy","model_ops","model_energy","planning_s","cpu_s","ticks","anomaly")},
                    wasted=int(bool(denied and (row["evidence"] is None or
                        (row["success"]<=denied["success"] and row["end_energy"]<=denied["end_energy"])))),
                    denied_success=denied["success"] if denied else None,
                    denied_energy_delta=row["end_energy"]-denied["end_energy"] if denied else None,
                    document_gain=pre_error-doc_error, error_per_information_energy=(pre_error-doc_error)/costs if costs else None,
                    aggregate_mae=total_error, timing_mae=timing_error,
                    minimum_hypothesis_aggregate_mae=loss_floor, minimum_hypothesis_timing_mae=timing_floor))
                records.append(dict(**key,**row,denied=denied))
                for choice,forecast,(losses,stock) in zip(OPTIONS,post_trip,obs):
                    predicted = losses if arm=="oracle" else tuple(forecast[0] if t==MODEL_TICK else 0.
                                                                   for t in OBS_TICKS)
                    audits.append(dict(**key,choice=choice,observed_losses=losses,observed_stock=stock,
                                       forecast_losses=predicted,forecast_stock=forecast[1]))
    return rows,records,audits,worlds


def bootstrap(diffs):
    rng = random.Random(558)
    samples = sorted(mean(rng.choices(diffs,k=len(diffs))) for _ in range(5000))
    return samples[125],samples[4874]


def summarize(rows):
    table,paired = [],[]
    for case in ("all",*CASES):
        group = [r for r in rows if case=="all" or r["case"]==case]
        for arm in ARMS:
            sample = [r for r in group if r["arm"]==arm]
            total_cpu = sum(r["cpu_s"] for r in sample)
            total_ops = sum(r["model_ops"] for r in sample)
            completed = sum(r["success"] for r in sample)
            table.append(dict(case=case,arm=arm,n=len(sample),completed=completed,
                              **{k:sum(r[k] for r in sample) for k in (
                                  "alive","purchased","altered","evidence_changed","physical_test","wasted","anomaly")},
                              **{k:mean(r[k] for r in sample) for k in (
                                  "aggregate_mae","timing_mae","energy","cpu_s","model_ops","model_energy","neural_energy")},
                              completions_per_cpu_second=completed/total_cpu if total_cpu else None,
                              completions_per_million_modeled_ops=1e6*completed/total_ops))
        for metric in ("success","aggregate_mae","timing_mae","energy"):
            diffs = []
            for seed in sorted({r["seed"] for r in group}):
                sub = [r for r in group if r["seed"]==seed]
                diffs.append(mean(r[metric] for r in sub if r["arm"]=="on")-
                             mean(r[metric] for r in sub if r["arm"]=="off"))
            low,high = bootstrap(diffs)
            paired.append(dict(case=case,metric=metric,n_seeds=len(diffs),difference=mean(diffs),low=low,high=high,
                               seeds_on_higher=sum(x>0 for x in diffs),seeds_off_higher=sum(x<0 for x in diffs)))
    return table,paired


def protocol():
    tracked = (Path(__file__),ROOT.parent/"genesis_1_1_4"/"hypotheses.py",
               ROOT.parent/"genesis_1_1_4"/"gateway.py",ROOT.parent/"genesis_1_1_4"/"curiosity.py",
               ROOT.parent/"genesis_1_1_2"/"scientist.py",ROOT.parent/"genesis_1_1"/"model.py",
               ROOT.parent/"genesis_1_1_1"/"two_roads.py",ENGINE/"cognition.py",
               ENGINE/"neural_survival.py",ENGINE/"organism.py",ENGINE/"world.py",MODEL_PATH,GENOME)
    return dict(primary="mean paired seed task-completion rate: ON minus OFF, equally weighted cases",
                interval="95% percentile bootstrap of independent seed differences, 5000 draws",
                development=DEVELOPMENT,evaluation=HELD_OUT,cases=CASES,arms=ARMS,trips=TRIPS,
                change_after=CHANGE_AT,observation_ticks=OBS_TICKS,hypothesis_loss_tick=MODEL_TICK,
                curiosity_strength=STRENGTH,random_rate=RANDOM_RATE,modeled_decision_operations=MODEL_OPS,
                inputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked})


GENOME = ENGINE/"experiments"/"first_survival_v031"/"trained_32.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--development",action="store_true")
    mode.add_argument("--lock",type=Path)
    mode.add_argument("--evaluate",type=Path)
    parser.add_argument("--out",type=Path)
    args = parser.parse_args()
    manifest = json.dumps(protocol(),indent=2)+"\n"
    if args.lock:
        with args.lock.open("x",encoding="utf-8",newline="\n") as f:
            f.write(manifest)
        return
    if not args.out:
        parser.error("--out is required for a run")
    if args.evaluate and args.evaluate.read_text(encoding="utf-8")!=manifest:
        parser.error("The current protocol or inputs differ from the lock")
    args.out.mkdir(parents=True,exist_ok=False)
    gene = json.loads(GENOME.read_text())
    rows,records,audits,worlds = [],[],[],{}
    for seed in DEVELOPMENT if args.development else HELD_OUT:
        summary,trace,common,worlds[seed] = evaluate(seed,gene,args.development)
        rows.extend(summary)
        records.extend(trace)
        audits.extend(common)
    table,paired = summarize(rows)
    for filename,items in (("journeys",rows),("summary",table),("paired",paired)):
        with (args.out/f"{filename}.csv").open("w",encoding="utf-8",newline="") as f:
            writer = csv.DictWriter(f,fieldnames=list(items[0]))
            writer.writeheader()
            writer.writerows(items)
    for filename,items in (("decisions",records),("common_audit",audits)):
        with (args.out/f"{filename}.jsonl").open("w",encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item)+"\n")
    (args.out/"worlds.json").write_text(json.dumps(worlds),encoding="utf-8")
    (args.out/"protocol.json").write_text(manifest,encoding="utf-8")
    print(f"{len(rows)} journeys and {len(audits)} forecasts across {len(worlds)} paired seeds")


if __name__=="__main__":
    main()
