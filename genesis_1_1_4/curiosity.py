"""CPU-only Cognitive Thirst pilot, using the archived Scientist simulator."""

import argparse
import csv
import hashlib
import json
import random
import sys
import time
from copy import deepcopy
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/"genesis_1_1_2"))
from scientist import (AUDIT_LAG, ENGINE, MODEL_PATH, AuditReplay, Law, Scientist, Terrain, journey,
                       LAGS, OP_ENERGY)
from gateway import LIBRARY, Library, Query, interpret
from hypotheses import (Beliefs, DOCUMENT_LABELS, OPTIONS, OUTCOMES, SOURCE_RELIABILITY,
                        document_likelihood, means, updated, variance)

ARMS = ("fixed","passive","random","active","curiosity","curiosity_no_gateway","curiosity_gateway","oracle")
CASES = ("unknown_mechanism","false_clue","forbidden_library","changing_law","unseen_world","useless_answer")
DEV = (401,402,403)
PILOT = (8101,8102,8103)
ROUNDS = (8,8,8,8,4,8)
METER_COST = .43
GATE_COST = .64
INTERVAL_COST = .18
MODEL_OPS = 2400
TIME_DISCOUNT = .96
EXPECTED_PHYSICAL_TICKS = 9


class Curious(Scientist):
    def __init__(self, label, gene, start, strength, prior=None, frozen=False):
        super().__init__("passive",gene,start,prior.model if prior else None,frozen=frozen)
        self.label = label
        self.strength = strength
        self.beliefs = deepcopy(prior.beliefs) if prior else Beliefs()
        self.available = None
        self.library = self.permit = self.context = self.meter_sample = None
        self.event = None
        self.unavailable_topics = set()

    def forecast(self, config):
        i = OPTIONS.index(config)
        loss, stock = (sum(p*o[i][j] for p,o in zip(self.beliefs.weights,OUTCOMES)) for j in range(2))
        return tuple(loss if lag==AUDIT_LAG else 0. for lag in LAGS),stock

    def choose(self, body, observations, rng):
        if self.tick == 1:
            self.available = next(tile for position,tile,_ in observations if position==body.position)
        move = super().choose(body,observations,rng)
        if self.pattern in LAGS:
            self.predicted = self.forecast(self.planned)[0][LAGS.index(self.pattern)]
        return move

    def executable_plan(self, default):
        if self.frozen:
            forecast = means(self.beliefs.weights)
            current = self.beliefs.description()
            self.event = dict(kind="exploit",question=None,before=current,pre_prediction=forecast,
                              proposed=[],selected_plan=default,no_purchase_plan=default,
                              exploratory_departure=0,purchased_evidence=None,retrieved=None,
                              information_cost=0.,information_ticks=0,post_information_prediction=forecast,
                              posterior_after_information=current)
            return default
        self.info_ops += MODEL_OPS
        b = self.beliefs
        energy = self.body.energy
        utilities = b.utilities(b.weights,energy)
        # Preserve the neural tie break among equally useful plans.
        best = max(range(4),key=lambda i:(round(utilities[i],9),OPTIONS[i]==default))
        uncertainty = variance(b.weights)
        baseline = max(utilities)
        proposals = []
        for i, config in enumerate(OPTIONS):
            gain,resolution,score = b.value(b.physical_channels(i,energy),energy,baseline,uncertainty)
            proposals.append(dict(kind="physical",config=config,decision_gain=gain,predictive_gain=resolution,
                                  net=utilities[i]-baseline+self.strength*TIME_DISCOUNT**EXPECTED_PHYSICAL_TICKS*score))
        if self.available=="meter" and self.label!="curiosity" and self.meter_sample is not None:
            r = b.meter_reliability()
            channels = [b.label_likelihood(sign,r) for sign in (-1,1)]
            gain,resolution,score = b.value(channels,energy,baseline,uncertainty)
            proposals.append(dict(kind="observe",decision_gain=gain,predictive_gain=resolution,
                                  net=self.strength*TIME_DISCOUNT*score+gain-METER_COST-INTERVAL_COST))
        topic = ("transitions",self.context)
        if (self.available=="gateway" and self.permit is not None and topic not in self.unavailable_topics
                and not self.library.requests):
            channels = [document_likelihood(signs) for signs in DOCUMENT_LABELS]
            gain,resolution,score = b.value(channels,energy,baseline,uncertainty)
            proposals.append(dict(kind="request",decision_gain=gain,predictive_gain=resolution,
                                  net=self.strength*TIME_DISCOUNT*score+gain-GATE_COST-INTERVAL_COST))
        selected = max(proposals,key=lambda item:item["net"])
        kind = selected["kind"] if selected["net"]>.005 else "exploit"
        evidence, document, question, cost = None,None,None,0.
        before = means(b.weights)
        prior = b.description()
        choice = OPTIONS[best]
        if kind == "physical":
            choice = selected["config"]
            question = dict(category="distinguish_predictions", settings=choice, alternatives=prior["hypotheses"][:2])
        elif kind == "observe":
            evidence = self.meter_sample
            question = dict(category="test_indicator",topic="first",context="local meter")
            b.weights = updated(b.weights,b.label_likelihood(evidence,b.meter_reliability()))
            cost = METER_COST+INTERVAL_COST
        elif kind == "request":
            query = Query(*topic)
            question = dict(category="missing_transition_evidence",topic=query.topic,context=query.context)
            document = self.library.retrieve(query,self.body.position,self.permit)
            evidence = interpret(query,document)
            self.unavailable_topics.add(topic)
            if evidence is not None:
                b.weights = updated(b.weights,document_likelihood(evidence))
            cost = GATE_COST+INTERVAL_COST
        if cost:
            self.body.energy -= cost
            utilities = b.utilities(b.weights,self.body.energy)
            choice = OPTIONS[max(range(4),key=lambda i:(round(utilities[i],9),OPTIONS[i]==default))]
        self.event = dict(kind=kind, question=question, before=prior, pre_prediction=before,
                          proposed=proposals, selected_plan=choice, no_purchase_plan=OPTIONS[best],
                          exploratory_departure=int(kind=="physical" and choice!=OPTIONS[best]),
                          purchased_evidence=evidence, retrieved=document, information_cost=cost,
                          information_ticks=int(bool(cost)), post_information_prediction=means(b.weights),
                          posterior_after_information=b.description())
        return choice


def context_for(seed):
    return random.Random(seed+582).choice(("ember","glass"))


def scene_laws(seed):
    rng = random.Random(seed+52)
    a,b,s,c,f = (rng.choice((-1,1)) for _ in range(5))
    reference = (-1,1,1) if context_for(seed)=="ember" else (1,-1,-1)
    related = Law(*(v if rng.random()<SOURCE_RELIABILITY else -v for v in reference))
    return (Law(a,b,s),Law(c,b,s),related,Law(-a,b,-s),Law(a,b,s),Law(f,b,-s))


def as_forecasts(agent):
    return [tuple((sum(loss),stock)) for loss,stock in (agent.forecast(c) for c in OPTIONS)]


def error(table, truth):
    return mean(abs(a-c)+abs(b-d) for (a,b),(c,d) in zip(table,truth))


def audit(gene, terrain, law, seed):
    table = []
    for c in OPTIONS:
        replay = AuditReplay(gene,terrain.start,c)
        r = journey(replay,terrain,law,seed,"transfer",1,None,start_energy=30.)
        table.append((r["loss"],r["stock_seen"]))
    return table


def evaluate(seed,gene,strength,trace):
    laws = scene_laws(seed)
    main = Terrain(seed)
    worlds = [main,Terrain(seed+1),Terrain(seed+2),main,Terrain(seed+30000,transfer=True),Terrain(seed+3)]
    for index,tile in ((1,"meter"),(2,"gateway"),(5,"gateway")):
        worlds[index].tiles[worlds[index].start]=tile
    truth = [audit(gene,Terrain(seed+40000,transfer=True),law,seed) for law in laws]
    rows,events,audits = [],[],[]
    for arm in ARMS:
        prior_a = saved = None
        for ix,(case,world,law,count) in enumerate(zip(CASES,worlds,laws,ROUNDS)):
            mode = arm.startswith("curiosity")
            prior = saved if ix==4 else None
            frozen = ix==4
            if ix==3:
                agent = prior_a
            elif mode:
                agent = Curious(arm,gene,world.start,strength,prior,frozen)
            else:
                agent = Scientist(arm,gene,world.start,prior.model if prior else None,frozen=frozen)
            context = context_for(seed)
            if ix==5:
                context = "ember" if seed%2 else "glass"
            # The case C manufacturer's family tag is observable at the gateway.
            library = Library(world.start,context,arm=="curiosity_gateway" and ix in (2,5),stale_catalog=ix==5)
            for episode in range(1,count+1):
                before = len(trace)
                pre = as_forecasts(agent) if arm!="oracle" else truth[ix]
                meter = random.Random(seed*3943+episode*7+ix).choice((-1,1))
                if mode:
                    agent.event = None
                    agent.library, agent.permit, agent.context = library,library.permit(),context
                    agent.meter_sample = meter
                clone = deepcopy(agent) if mode and agent.permit is not None and not library.requests else None
                result = journey(agent,world,law,seed,"attribution",episode,trace)
                for item in trace[before:]:
                    item["arm"],item["case"] = arm,case
                event = agent.event if mode else None
                observed_loss = result["loss"] if result["ticks"]>=5 else None
                plausibility = None
                if mode and not frozen:
                    plausibility = agent.beliefs.observe((result["first"],result["second"]),observed_loss,result["stock_seen"])
                    if ix==1:
                        agent.beliefs.calibrate_meter(meter)
                post = as_forecasts(agent) if arm!="oracle" else truth[ix]
                chosen = (result["first"],result["second"])
                source = event["retrieved"] if event else None
                useful = bool(source and event["purchased_evidence"] is not None)
                counterfactual = None
                if clone is not None and event["kind"]=="request":
                    clone.permit = None
                    no_access = journey(clone,world,law,seed,"attribution",episode,None)
                    counterfactual = {k:no_access[k] for k in ("first","second","success","alive","loss",
                                                               "food","energy_spent","end_energy","ticks")}
                prediction_change = (error(event["pre_prediction"],truth[ix])-
                                     error(event["post_information_prediction"],truth[ix])) if event else 0.
                utility_gain = 0.
                if event:
                    def net(choice):
                        loss, stock = truth[ix][OPTIONS.index(tuple(choice))]
                        return -loss+.90*stock-(8. if loss+5.>=12. else 0.)
                    utility_gain = net(chosen)-net(event["no_purchase_plan"])
                    events.append(dict(seed=seed,case=case,arm=arm,episode=episode,**event,
                                       physically_observed=dict(loss=observed_loss,stock=result["stock_seen"]),
                                       plausibility=plausibility,posterior_after_outcome=agent.beliefs.description(),
                                       post_outcome_prediction=post,downstream_utility_change=utility_gain,
                                       gateway_denied_counterfactual=counterfactual,end_energy=result["end_energy"],
                                       audit_error_improvement=prediction_change,success=result["success"],
                                       modeled_operations=result["inference_ops"]+result["information_ops"]+result["update_ops"],
                                       modeled_energy=result["model_energy"],spent=result["energy_spent"]))
                rows.append(dict(**{k:v for k,v in result.items() if k not in ("arm","phase","ticks")},
                                 case=case,arm=arm,ticks=result["ticks"]+(event["information_ticks"] if event else 0),
                                 investigation=event["kind"] if event else "physical" if result["self_experiment"] else "exploit",
                                 retrieval=int(bool(source)),relevant=int(useful),prediction_change=prediction_change,
                                 downstream_utility_change=utility_gain,information_cost=event["information_cost"] if event else 0.,
                                 exploratory_departure=event["exploratory_departure"] if event else result["self_experiment"],
                                 audit_pre=error(pre,truth[ix]),audit_post=error(post,truth[ix]),
                                 anomaly=int(plausibility is not None and plausibility<.12),
                                 identified=int(error(post,truth[ix])<.9)))
            for choice,(predicted,observed) in zip(OPTIONS,zip(post,truth[ix])):
                audits.append(dict(seed=seed,case=case,arm=arm,first=choice[0],second=choice[1],
                                   predicted_loss=predicted[0],predicted_stock=predicted[1],
                                   observed_loss=observed[0],observed_stock=observed[1]))
            if ix==0:
                prior_a = agent
                saved = deepcopy(agent)
    environments = {case:dict(terrain=world.serialize(),evaluator_law=vars(law),
                              reference_context=context_for(seed) if ix==2 else
                              ("ember" if seed%2 else "glass") if ix==5 else None)
                    for ix,(case,world,law) in enumerate(zip(CASES,worlds,laws))}
    return rows,events,audits,environments


def summaries(rows):
    table,paired = [],[]
    for case in CASES:
        group = [r for r in rows if r["case"]==case]
        for arm in ARMS:
            sample = [r for r in group if r["arm"]==arm]
            final = [r for r in sample if r["episode"]==max(x["episode"] for x in sample)]
            table.append(dict(case=case,arm=arm,n=len(sample),
                              **{k:sum(r[k] for r in sample) for k in ("success","alive","retrieval","relevant","anomaly","exploratory_departure")},
                              **{k:sum(r["investigation"]==k for r in sample) for k in ("physical","observe","request")},
                              identified=sum(r["identified"] for r in final),final_error=mean(r["audit_post"] for r in final),
                              **{k:mean(r[k] for r in sample) for k in ("energy_spent","model_energy","information_cost",
                                  "prediction_change","downstream_utility_change","decision_cpu_s","cpu_s")}))
        for control in ("passive","active","curiosity_no_gateway"):
            seeds = sorted({r["seed"] for r in group})
            for metric in ("success","audit_post","energy_spent"):
                diffs = []
                for seed in seeds:
                    def sample(arm):
                        return mean(r[metric] for r in group if r["seed"]==seed and r["arm"]==arm)
                    diffs.append(sample("curiosity_gateway")-sample(control))
                rng = random.Random(51)
                values = sorted(mean(rng.choices(diffs,k=len(diffs))) for _ in range(2000))
                paired.append(dict(case=case,control=control,metric=metric,seeds=len(seeds),
                                   difference=mean(diffs),low=values[50],high=values[1949]))
    return table,paired


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--development",action="store_true")
    p.add_argument("--seeds",type=int,default=3)
    p.add_argument("--curiosity",type=float,default=4.)
    p.add_argument("--modules",type=int,choices=(32,67),default=32)
    args=p.parse_args()
    if args.seeds!=3 and args.seeds<20 or not 0<=args.curiosity<=8:
        p.error("Use 3 or 20+ seeds and curiosity strength in [0,8]")
    seeds=DEV if args.development else PILOT if args.seeds==3 else tuple(range(9100,9100+args.seeds))
    args.out.mkdir(parents=True,exist_ok=False)
    genome=ENGINE/"experiments"/"first_survival_v031"/f"trained_{args.modules}.json"
    gene=json.loads(genome.read_text(encoding="utf-8"))
    rows,events,audits,trace,worlds=[],[],[],[],{}
    for seed in seeds:
        new,queries,common,worlds[seed]=evaluate(seed,gene,args.curiosity,trace)
        rows.extend(new)
        events.extend(queries)
        audits.extend(common)
    summary,paired=summaries(rows)
    for name,records in (("journeys",rows),("summary",summary),("paired",paired),("audit",audits)):
        with (args.out/f"{name}.csv").open("w",newline="",encoding="utf-8") as f:
            writer=csv.DictWriter(f,fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    for name,records in (("inquiries",events),("trace",trace)):
        with (args.out/f"{name}.jsonl").open("w",encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record)+"\n")
    (args.out/"protocol.json").write_text(json.dumps(dict(
        seeds=seeds,development=DEV,rounds=dict(zip(CASES,ROUNDS)),curiosity=args.curiosity,modules=args.modules,
        gateway="offline, one retrieval per case, scoped reference observations",
        modeled_reference_reliability=SOURCE_RELIABILITY,
        time_discount=TIME_DISCOUNT,estimated_physical_observation_ticks=EXPECTED_PHYSICAL_TICKS,
        costs=dict(meter=METER_COST,gateway=GATE_COST,interval=INTERVAL_COST,planning_ops=MODEL_OPS),
        sources=[vars(item) for item in LIBRARY], genome=hashlib.sha256(genome.read_bytes()).hexdigest(),
        local_model=hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()),indent=2),encoding="utf-8")
    (args.out/"worlds.json").write_text(json.dumps(worlds),encoding="utf-8")
    print(f"{len(rows)} journeys, {len(events)} inquiry records, {len(audits)} common forecasts")


if __name__=="__main__":
    main()
