"""A bounded archive-to-settlement prediction bridge and matched task episodes."""

from collections import deque
from dataclasses import asdict, dataclass
import json
import random

from memory_audit import ROOT
from embodied import HumanTrial
from inquiry import Question, render
from organism import WeightedPolicy
from settlement import Action, Body, Settlement, WALKABLE, DIRS, distance, offset

EARTH = ROOT.parent / "genesis_1_3_4/results/pilot_final/13830/combined/chronology.json"
EARLIER = ROOT.parent / "genesis_1_3_3/results/primary/13700/combined/chronology.json"
DEV = (14130, 14131, 14132)
EVAL = tuple(range(14200, 14220))
ARMS = ("preserved", "standardized", "relevant_removed", "shuffled", "reference")
TASKS = ("capacity", "effort", "claim")
HELDOUT_PER_TASK = 6
PRACTICE = 9
MAX_RECORDS = 72
READ_COST = .62
INSPECT_COST = .78
DECISION_CHARGE = .025


@dataclass(frozen=True)
class Observation:
    property: str
    cue: int
    condition: int


@dataclass(frozen=True)
class Memory:
    id: str
    observed: Observation
    success: int
    archive: str
    tick: int
    evidence: dict


def memory_bank():
    """Use only recorded actions, local observations and verified messages."""
    events = []
    for source in (EARLIER, EARTH):
        old = json.loads(source.read_text(encoding="utf-8"))
        name = "earth_133" if source == EARLIER else "earth_134"
        for before, now in zip(old, old[1:]):
            tick = now["tick"]
            action = now["action"]
            visible = {tuple(p): stock for p,stock in now["visible_food"]}
            pos = tuple(before["position"])
            if action == 4 and pos in visible:
                collected = now["food"] - before["food"]
                events.append(Memory(f"{name}:{tick}:food", Observation("availability", int(visible[pos] >= 4), 1),
                                     int(collected >= 4), name, tick, dict(stock=visible[pos], collected=collected)))
            # Overlapping visible records provide a predictive relation about
            # stock persistence. Missing tiles never count as zero stock.
            later = {tuple(p): stock for p,stock in now["visible_food"]}
            earlier = {tuple(p): stock for p,stock in before["visible_food"]}
            if tick % 7 == 0 and earlier.keys() & later.keys():
                p = min(earlier.keys() & later.keys(), key=lambda q:(distance(pos,q),q))
                events.append(Memory(f"{name}:{tick}:stock", Observation("availability", int(earlier[p] >= 4), 0),
                                     int(later[p] >= 4),name,tick,dict(before=earlier[p],after=later[p],position=p)))
            if action in (0,1,2,3,5) and not now["question_id"] and before["offspring"] == now["offspring"]:
                cost = -now["actual_delta"]
                if .05 < cost < 1.5:
                    events.append(Memory(f"{name}:{tick}:energy", Observation("energy budget", int(action < 4), 0),
                                         int(cost <= .36),name,tick,dict(action=action,energy_cost=cost)))
            for e in now.get("events", ()):
                if e["kind"] == "hint_verified" and e.get("id") == 1:
                    events.append(Memory(f"{name}:{tick}:{e['question_id']}", Observation("reported availability",
                                         int(e["claimed"]),int(e["age"] >= 3)), int(e["observed"] > 2.),
                                         name,tick,dict(claim=e["claimed"],observed=e["observed"],
                                                        lag=e["age"],question_id=e["question_id"])))
    bank = []
    for property in ("availability","energy budget","reported availability"):
        for cue in (0,1):
            samples = [e for e in events if (e.observed.property,e.observed.cue)==(property,cue)]
            bank.extend(samples[-12:])
    return tuple(bank[:MAX_RECORDS])


def shuffled(bank, seed):
    """Break cue/outcome alignment while preserving each property and outcome mix."""
    rng = random.Random(seed + 971)
    out = []
    for property in sorted({m.observed.property for m in bank}):
        group = [m for m in bank if m.observed.property == property]
        observed = [m.observed for m in group]
        rng.shuffle(observed)
        out.extend(Memory(m.id, cue, m.success, m.archive, m.tick, m.evidence) for m,cue in zip(group,observed))
    return tuple(out)


class Predictor:
    def __init__(self, bank):
        self.bank = bank
        self.local = deque(maxlen=24)
        self.document = deque(maxlen=16)

    def predict(self, observed, arm, excluded=None):
        scores = []
        for m in self.bank:
            similarity = int(m.observed.property == observed.property) * (
                1. if m.observed.cue == observed.cue else 0.
            ) * (1. if m.observed.condition == observed.condition else .65)
            enabled = arm not in ("standardized","reference","relevant_removed") and m.id != excluded
            if similarity and enabled:
                scores.append((m, similarity))
        # A conservative finite prior caps any advantage from duplicate events.
        raw = sum(w for _,w in scores)
        scale = min(1., 3. / max(1., raw))
        positive = .9 + scale * sum(m.success*w for m,w in scores)
        total = 1.8 + scale * raw
        for obs, outcome in self.local:
            if (obs.property,obs.cue) == (observed.property,observed.cue):
                positive += outcome
                total += 1
        return positive / total, [(m.id, round(w*scale,5)) for m,w in scores]

    @property
    def book_reliability(self):
        return (.7*3 + sum(self.document)) / (3 + len(self.document))


@dataclass(frozen=True)
class Option:
    position: tuple
    label: str
    observed: Observation


@dataclass(frozen=True)
class Book:
    position: tuple
    name: str
    entries: tuple


class Scene:
    def __init__(self, seed, task, practice):
        rng = random.Random(seed)
        self.world = Settlement(seed)
        location = {"capacity":"market","effort":"workshop","claim":"school"}[task]
        self.start = next(p for p,tile in self.world.sites.items() if tile == location)
        nearby = [offset(self.start,d) for d in DIRS if self.world.tiles.get(offset(self.start,d)) in WALKABLE]
        rng.shuffle(nearby)
        cue = rng.randrange(2)
        cues = (cue, 1-cue)
        high_success = task != "effort"
        # Seeded perturbations sometimes invert a cue. Only the evaluator sees
        # this bit. Markings describe prior observations, not live outcomes.
        usual = rng.random() < {"capacity":.79,"effort":.76,"claim":.57}[task]
        good_cue = int(high_success) if usual else int(not high_success)
        self.success = tuple(int(c == good_cue) for c in cues)
        condition = rng.randrange(2)  # Visible casing or marking texture.
        # A shared cover sometimes obscures the distinguishing local mark.
        # This presentation leaves the book and inspection as optional evidence.
        visible_cues = (cue,cue) if condition and rng.random()<.50 else cues
        property = {"capacity":"availability","effort":"energy budget","claim":"reported availability"}[task]
        names = {("capacity",True):("reed basket","pine tray"),("capacity",False):("tin drawer","oak crate"),
                 ("effort",True):("short crank","iron wheel"),("effort",False):("gear press","pulley lever"),
                 ("claim",True):("chalk tag","ink tag"),("claim",False):("dated receipt","folded bill")}[task,practice]
        self.options = tuple(Option(p,n,Observation(property,c,condition)) for p,n,c in zip(nearby,names,visible_cues))
        self.task = task
        self.body = Body(self.start, energy=67.,water=59.,fatigue=26.,
                         holding="hand tool" if task=="effort" else None)
        entries = tuple((i, expected if rng.random()<.73 else 1-expected)
                        for i,expected in enumerate(self.success) if rng.random()<.83)
        self.book = Book(self.start,"Workshop folio" if practice else "Village register",entries)
        # An enclosed cover is visibly harder to inspect than exposed parts.
        self.inspect_reliability = .64 if condition else .82
        self.signals = tuple(x if rng.random()<self.inspect_reliability else 1-x for x in self.success)
        self.world.tick = 5
        for i,option in enumerate(self.options):
            if task == "effort":
                self.world.tiles[option.position] = "workshop"
            else:
                self.world.tools[option.position] = self.success[i]

    def evidence(self, choice):
        if choice == "read":
            if distance(self.body.position,self.book.position)>1 or self.world.daylight<=.16:
                return (), "unreadable"
            # The existing motor's reach and grasp pose also apply to books
            # in market stalls and workshops, where 1.4's school gate did not.
            result = self.world.act(self.body,Action("inspect",self.book.position))
            self.body.energy -= READ_COST
            self.world.advance()
            return self.book.entries if result["success"] else (), "folio opened"
        index = int(choice)
        result = self.world.act(self.body,Action("inspect",self.options[index].position))
        self.body.energy -= INSPECT_COST
        self.world.advance()
        return ((index,self.signals[index]),) if result["success"] else (), "mechanism inspected"

    def commit(self, index):
        before = self.body.energy
        if index is None:
            result = self.world.act(self.body,Action("rest"))
            return 0,dict(rested=True,energy_cost=before-self.body.energy,delay=0,motor=result)
        option = self.options[index]
        result = self.world.act(self.body,Action("work" if self.task=="effort" else "grasp",option.position))
        delayed = 0.
        if self.task == "effort":
            for _ in range(2):
                self.world.advance()
                self.world.act(self.body,Action("rest"))
            delayed = .19 if self.success[index] else 1.37
            self.body.energy -= delayed
        passed = result["success"] and (self.task != "effort" or delayed <= .55)
        return int(passed),dict(energy_cost=before-self.body.energy,delay=2 if self.task=="effort" else 0,
                                delayed_cost=delayed,motor=result)


def posterior(p, reading, reliability):
    a = p*(reliability if reading else 1-reliability)
    b = (1-p)*(1-reliability if reading else reliability)
    return a/(a+b)


def value_of_check(probs, indices, reliability):
    distribution=[(1.,list(probs))]
    for i in indices:
        expanded=[]
        for mass, values in distribution:
            for reading in (0,1):
                likelihood=values[i]*reliability+(1-values[i])*(1-reliability)
                weight=likelihood if reading else 1-likelihood
                update=values[:]
                update[i]=posterior(values[i],reading,reliability)
                expanded.append((mass*weight,update))
        distribution=expanded
    return max(0.,sum(mass*max(values) for mass,values in distribution)-max(probs))


def motor_hint(saved, scene, seed, arm):
    # Same archived weights and recurrent state in every neural arm. A fresh
    # private clone prevents held-out episodes from training one another.
    agent = HumanTrial(seed,"preserved",saved.core,saved.model)
    agent.body = scene.body
    agent.sync()
    local=agent.legacy_view(scene.world.local(scene.body))
    view=[(p,*v) for p,v in local.items()]
    rng=random.Random(seed+193)
    first=agent.core.brain.ops
    action,target=agent.neural_policy.choose(agent.core,view,rng)
    if arm == "reference":
        action,target=WeightedPolicy().choose(agent.core,view,random.Random(seed+193))
    scene.body.energy=agent.core.energy
    bias = [(.025 if action == "move" and target == o.position else 0.) for o in scene.options]
    return bias,agent.core.brain.ops-first


def run_task(saved, predictor, arm, seed, task, practice=False, excluded=None):
    scene=Scene(seed,task,practice)
    body=scene.body
    before_energy=body.energy
    bias,neural_ops=motor_hint(saved,scene,seed,arm)
    retrieved=[predictor.predict(o.observed,arm,excluded) for o in scene.options]
    priors=[p for p,_ in retrieved]
    updated=priors[:]
    scores=lambda values:[v+b for v,b in zip(values,bias)]
    best=lambda values:max(range(2),key=scores(values).__getitem__)
    original_choice=best(priors)
    # Book entries are concealed until a physical read. The cover reveals
    # what objects the catalogue may cover, not the count or values of claims.
    book_value=value_of_check(priors,(0,1),predictor.book_reliability)*.83-READ_COST*.063
    candidates=[("read",book_value),*((str(i),value_of_check(priors,(i,),scene.inspect_reliability)-INSPECT_COST*.063)
                                      for i in range(2)),("act",0.)]
    option,info=max(candidates,key=lambda item:item[1])
    evidence, feedback = (),None
    question=None
    if option!="act":
        observed=scene.options[original_choice].observed
        conditions=("high marking" if observed.cue else "low marking",
                    "covered mechanism" if observed.condition else "exposed mechanism")
        q=Question(observed.property,"predicts",
                   conditions,tuple(o.observed.cue for o in scene.options),
                   "reference" if option=="read" else "physical",info, max(priors))
        question=dict(structure=asdict(q),rendering=render(q))
        evidence, feedback=scene.evidence(option)
        for i,value in evidence:
            updated[i]=posterior(updated[i],value,predictor.book_reliability
                                 if option=="read" else scene.inspect_reliability)
    choice=best(updated) if body.energy>9. else None
    body.energy-=DECISION_CHARGE
    success,outcome=scene.commit(choice)
    seen=[]
    if choice is not None:
        for i,value in evidence:
            if i==choice:
                seen.append(int(value==success))
        if practice:
            predictor.local.append((scene.options[choice].observed,success))
            if option=="read":
                predictor.document.extend(seen)
    old_error=sum((p-y)**2 for p,y in zip(priors,scene.success))/2
    new_error=sum((p-y)**2 for p,y in zip(updated,scene.success))/2
    changed = choice != original_choice
    improved_choice = success > scene.success[original_choice]
    improved_forecast = new_error+.005 < old_error
    return dict(task=task,scene_seed=seed,arm=arm,practice=practice,success=success,
                energy_spent=before_energy-body.energy,neural_ops=neural_ops,
                comparison_slots=2*len(predictor.bank),decision_charge=DECISION_CHARGE,
                prior_brier=old_error,posterior_brier=new_error,opportunity=option,read=int(option=="read"),
                inspection=int(option not in ("act","read")),verified=len(seen),confirmed=sum(seen),
                changed_after_information=int(option!="act" and changed),
                useful=int(option!="act" and (improved_choice or improved_forecast)),
                unnecessary=int(option!="act" and not changed and not improved_forecast),
                retrieved=sum(len(m) for _,m in retrieved),options=[asdict(o) for o in scene.options],
                settlement_position=scene.start,layout=scene.world.variant,body=asdict(body),
                book=dict(name=scene.book.name,position=scene.book.position,opened=option=="read",feedback=feedback),
                candidates=dict(cognition=[(scene.options[i].label,v) for i,v in enumerate(scores(priors))],
                                investigation=candidates),
                prior=priors,posterior=updated,original_choice=original_choice,choice=choice,
                outcome=outcome,evidence=evidence,retrieved_records=[m for _,m in retrieved],
                question=question,added_local_memory=bool(practice and choice is not None))
