"""Compatibility layer from Omega's archived controller to the settlement body."""

from collections import Counter, OrderedDict, deque
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import pickle
import random
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/"genesis_1_3_4"))
from social_trial import DeliveryExperiment
from lonely import LocalLife, broadcast
from population import Brain, NeuralPolicy, State, SocialMemory, inputs, fingerprint, OP_ENERGY
from cognition import CognitiveMemory
from cognitive import Lifetime
from organism import WeightedPolicy
from inquiry import CONCEPTS, Question, render
from model import persistence

from settlement import (Action, Body, Settlement, DIRS, SHELTER, WALKABLE, clamp, distance, offset)


SOURCE=ROOT.parent/"genesis_1_3_4/results/pilot_final/13830/combined/final.pkl"
DEV=(14030,14031,14032)
EVAL=tuple(range(14100,14120))
ARMS=("preserved","standard_memory","reference","limited_inquiry")
TICKS=144
FOCUS_TILES={"well","market","field","school","workshop","house"}


def digest(data):
    return sha256(data).hexdigest()


def archive():
    # Frozen selection rule: latest validated episode boundary, standard
    # combined arm, lowest pilot seed, independent of scores.
    data=SOURCE.read_bytes()
    meta=json.loads(SOURCE.with_suffix(".json").read_text())
    if digest(data)!=meta["sha256"] or meta["tick"]!=800:
        raise ValueError("checkpoint verification failed")
    sim=pickle.loads(data)
    body=sim.subject
    if (type(sim)!=DeliveryExperiment or body.id!=1 or not body.alive or
            body.age!=800 or len(body.brain.modules)!=32 or not any(o is body for o in sim.organisms)):
        raise ValueError("checkpoint identity or model mismatch")
    return data,body,sim.model


def cognitive_hashes(core,model):
    return dict(genome=fingerprint(core.brain.genetic), weights=fingerprint([m.p for m in core.brain.modules]),
                recurrent=fingerprint([m.state for m in core.brain.modules]),
                learned_model=fingerprint((model.hidden,model.output)),
                life_memory=digest(pickle.dumps(core.lifetime,protocol=5)),
                social=digest(pickle.dumps(core.social,protocol=5)),
                local_learning=digest(pickle.dumps(core.local_life,protocol=5)),
                brain_map=digest(pickle.dumps(core.brain.memory,protocol=5)))


class Radio:
    def __init__(self,identity,body):
        self.id,self.body=identity,body

    @property
    def energy(self):
        return self.body.energy

    @energy.setter
    def energy(self,value):
        self.body.energy=value

    @property
    def alive(self):
        return self.body.alive

    @property
    def position(self):
        return self.body.position


class HumanTrial:
    def __init__(self,seed,arm,core,model,stagnation=False):
        self.seed,self.arm=seed,arm
        self.world=Settlement(seed)
        self.body=Body(self.world.spawn)
        self.core,self.model=deepcopy((core,model))
        self.frozen_model=deepcopy(model)
        self.stagnation=stagnation
        self.advanced=arm in ("preserved","standard_memory")
        self.neural=arm!="reference"
        self.original=cognitive_hashes(self.core,self.model)
        self.legacy=(self.core.position,self.core.memory,self.core.visited,self.core.brain.memory,self.core.social,
                     tuple(self.core.local_life.pending),self.core.pending_question)
        if arm=="standard_memory" or arm=="reference":
            self.legacy=None
            self.core.lifetime=Lifetime()
            self.core.local_life=LocalLife()
        self.core.memory=OrderedDict()
        self.core.brain.memory=CognitiveMemory()
        self.core.social=SocialMemory()
        self.core.local_life.pending.clear()
        self.core.pending_question=None
        self.core.visited=set()
        self.core.interacted=False
        self.known=OrderedDict()
        self.hints=deque(maxlen=8)
        self.queue=deque(maxlen=12)
        self.rng=random.Random(seed+172)
        self.metrics=Counter()
        self.events=[]
        self.skills=Counter()
        self.recent=deque(maxlen=16)
        self.neural_policy=NeuralPolicy() if self.neural else WeightedPolicy()
        self.next_inquiry=0
        self.finalized=False

    def log(self,kind,**data):
        self.events.append(dict(tick=self.world.tick,kind=kind,**data))

    def sync(self):
        b,c=self.body,self.core
        c.position,c.energy,c.health,c.direction=b.position,b.energy,b.health,b.facing
        c.pain=min(12.,(100-b.health)/5)
        c.alive,c.death_cause=b.alive,b.cause

    def perceive(self):
        b,c=self.body,self.core
        local=self.world.local(b)
        peers=self.world.nearby(b)
        # Legacy peer IDs cannot be associated with these residents. Only
        # direction, distance and ordinary perceptual cues enter the adapter.
        c.local_contacts=[(r.id,r.body.position,50. if r.body.fatigue<60. else 30.) for r in peers]
        c.social.advance(c.local_contacts,c.age)
        for p,cell in local.items():
            self.known[p]=dict(cell,tick=self.world.tick)
            self.known.move_to_end(p)
        while len(self.known)>64:
            self.known.popitem(last=False)
        for item in tuple(self.hints):
            peer,tile,p,rid=item
            if p in local:
                correct=local[p]["tile"]==tile
                life=c.local_life
                prior=life.expect(peer,"hint")
                life.observe(peer,"hint",correct)
                self.metrics["checked_hints"]+=1
                self.log("verification",peer=peer,target=p,expected=tile,actual=local[p]["tile"],valid=correct,
                         prior=prior,updated=life.expect(peer,"hint"),question_id=rid)
                self.hints.remove(item)
        return local,peers

    def legacy_view(self,local):
        return {p:("water" if cell["tile"] not in WALKABLE else
                   "fruit" if cell["tile"]=="school" else
                   "hazard" if cell["tile"]=="hazard" else "land",
                   min(30.,cell["stock"]) if cell["tile"] in ("market","field") else 0.)
                for p,cell in local.items()}

    def context(self,local,peers,action):
        b=self.body
        p=action.target if action.target is not None else b.position
        cell=local.get(p,{})
        checks=(bool(peers),self.world.daylight>.28,bool(b.holding),b.water>18.,len(peers)>1,
                p in self.core.visited,b.fatigue<78.,b.energy>=35.,cell.get("tile") in SHELTER)
        return tuple(1 if x else -1 for x in checks)

    def needs(self):
        b=self.body
        return dict(well=(100-b.water)/33.,market=(100-b.energy)/39.+.15*(not b.provisions),
                    field=(100-b.energy)/43.,house=b.fatigue/49.+max(0.,36.5-b.temperature),
                    workshop=.37+.40*(not b.holding)+.6*(b.coins<2),
                    school=.41)

    def candidates(self,local,peers):
        b=self.body
        need=self.needs()
        tired=b.fatigue/100
        sheltered=local[b.position]["tile"] in SHELTER
        options=[(Action("rest"), .13 + .33*tired + 2.3*max(0.,tired-.40)
                  + .18*sheltered*max(0.,tired-.20))]
        options.append((Action("turn",direction=(b.facing+1)%4),.21 if len(local)<10 else -.14))
        known={p:cell for p,cell in self.known.items() if cell["tile"] in FOCUS_TILES}
        for peer,tile,p,_ in self.hints:
            if p not in known and self.core.local_life.expect(peer,"hint")>.5:
                known[p]=dict(tile=tile)
        occupied={r.body.position for r in peers}
        for direction,d in enumerate(DIRS):
            p=offset(b.position,d)
            if p not in local or local[p]["tile"] not in WALKABLE or p in occupied:
                continue
            pull=max((need[cell["tile"]]/(1+.35*distance(p,q)) for q,cell in known.items()
                      if distance(p,q)<distance(b.position,q)), default=0.)
            visibility=.23*(p not in self.core.visited)
            options.append((Action("walk",p,direction),.26+pull+visibility-.50*tired))
        if b.provisions and b.energy<88.:
            options.append((Action("eat"),.32+need["market"]*.96))
        for p,cell in local.items():
            if distance(b.position,p)>1:
                continue
            tile,stock=cell["tile"],cell["stock"]
            if tile=="well" and stock>3 and b.water<92.:
                options.append((Action("drink",p),.42+need["well"]*.96))
            if tile=="field" and stock>3 and b.energy<86.:
                options.append((Action("eat",p),.26+need["field"]*.91))
            if tile=="market" and stock>4 and b.coins and b.provisions<2:
                options.append((Action("trade",p),.17+need["market"]*.63-.23*b.provisions))
            if tile=="workshop" and cell["tool"] and not b.holding:
                options.append((Action("grasp",p),.82+.19*(b.coins<3)))
            if tile in ("workshop","field"):
                options.append((Action("work",p),.20+.78*(b.coins<3)+.28*(b.holding is not None)-.39*tired))
            if tile=="school" and self.world.tick>=self.next_inquiry:
                for topic in ("workshop","well"):
                    if not self.core.lifetime.confidence("settlement:"+topic,self.core.age)>.40:
                        options.append((Action("read",p,topic=topic),.42+.11*need[topic]))
            if tile in ("workshop","well") and self.world.tick>=self.next_inquiry:
                options.append((Action("inspect",p,topic=tile),.23+.14*(p not in self.core.visited)))
        if self.world.tick>=self.next_inquiry and b.energy>15.:
            for peer in peers:
                for topic in ("well","workshop","market"):
                    known_near=any(cell["tile"]==topic and distance(b.position,p)<=3 for p,cell in known.items())
                    if not known_near:
                        trust=self.core.local_life.expect(peer.id,"hint")
                        options.append((Action("ask",peer=peer.id,topic=topic),.30+.31*need[topic]+.20*trust))
                if self.recent and distance(b.position,peer.body.position)<=1:
                    options.append((Action("report",peer=peer.id,topic=self.recent[-1][0]),.22+.22*self.core.social.bond(peer.id)))
                if b.provisions>1 and b.energy>73. and distance(b.position,peer.body.position)<=1:
                    options.append((Action("cooperate",peer=peer.id),.22+.16*self.core.social.bond(peer.id)))
        return options

    def code(self,action):
        return action.direction if action.kind=="walk" else {
            "eat":4,"rest":5,"cooperate":6,"turn":5}.get(action.kind,7)

    def forecast(self,action,local,model):
        b=self.body
        view=self.legacy_view(local)
        _,features=inputs(State(b.position,b.energy,(b.fatigue/100,1-b.water/100),view),self.code(action)
                          if self.code(action)!=6 else 5)
        result=model.predict(features) if self.neural else persistence(features)
        return result,features

    def choose(self,local,peers):
        self.sync()
        c,b=self.core,self.body
        old=self.legacy_view(local)
        proposed,destination=self.neural_policy.choose(c,[(p,*cell) for p,cell in old.items()],self.rng)
        b.energy=c.energy
        alias={"walk":"move","cooperate":"share","inspect":"investigate","read":"investigate"}
        decorated=[]
        top=self.candidates(local,peers)
        life=c.local_life
        for option,value in top:
            typed=option.kind in ("ask","inspect","read","work")
            ctx=self.context(local,peers,option)
            info=gain=0.
            if typed and self.advanced:
                # Contrast a legal, observable manipulation with the current
                # context. No transition oracle is supplied to the ranker.
                proposed_context=list(ctx)
                proposed_context[2]=-ctx[2]
                info,gain=life.model.query_value(tuple(proposed_context),ctx,.90,1.)
                value+=.21*info+.27*gain
                if self.stagnation and value>.25 and info>0.:
                    value+=.12*life.habit.level*info
            if (proposed==alias.get(option.kind,option.kind) and
                    (option.kind!="walk" or option.target==destination)):
                value+=.27
            decorated.append((value+self.rng.random()*.07,option,ctx,info,gain))
        finalists=sorted(decorated,key=lambda r:r[0],reverse=True)[:4]
        ranked=[]
        for value,option,ctx,info,gain in finalists:
            forecast,features=self.forecast(option,local,self.model)
            ranked.append((value+.045*forecast[0]*10,option,ctx,info,gain,forecast,features))
        self.metrics["forecast_ops"]+=len(ranked)*self.model.cost
        b.energy-=len(ranked)*self.model.cost*OP_ENERGY
        return max(ranked,key=lambda r:r[0])

    def frame(self,action,context,info,gain):
        model=self.core.local_life.model
        terms,_=model.strongest_rule()
        # Only currently observable conditions enter a structured question.
        active=[i for i,v in enumerate(context) if v==1 and i not in terms]
        if active and len(terms)<3:
            terms=(*terms,active[0])
        names=("audible peer","daylight","tool in hand","adequate hydration","multiple nearby peers",
               "visited object","low fatigue","adequate energy","shelter")
        q=Question(action.topic or "local outcome","predicts",tuple(names[i] for i in terms),
                   context,{"ask":"peer","read":"reference"}.get(action.kind,"physical"),info,gain)
        return asdict(q),render(q)

    def communicate(self,action,peers):
        person=next((r for r in peers if r.id==action.peer),None)
        if person is None or not person.body.alive:
            return False
        if action.kind=="cooperate":
            if not self.body.provisions or distance(self.body.position,person.body.position)>1:
                return False
            self.body.provisions-=1
            person.body.provisions+=1
            self.core.social.encounter(person.id,self.core.age,.04)
            self.metrics["transfers"]+=1
            return True
        report=self.recent[-1] if action.kind=="report" and self.recent else None
        payload=(self.world.tick,action.kind,action.topic,report)
        symbol,_=self.core.communication.transmit(int(action.kind=="report"),self.core.social_rng,.13)
        packet,cost=broadcast(Radio(1,self.body),Radio(person.id,person.body),symbol,self.world.tick,
                              distance_limit=3,cost=.18,latency=1)
        self.metrics["message_energy"]+=cost
        if packet and len(self.queue)<self.queue.maxlen:
            self.queue.append((packet,payload))
            self.log("message_sent",recipient=person.id,symbol=symbol,request_id=payload[0],
                     topic=action.topic,observation=report)
            return True
        self.log("transport_failed",recipient=person.id,request_id=payload[0])
        return False

    def deliver(self):
        world=self.world
        people={r.id:r for r in world.residents}
        for _ in range(len(self.queue)):
            packet,payload=self.queue.popleft()
            if packet.arrives_at>world.tick:
                self.queue.append((packet,payload))
                continue
            peer=people.get(packet.receiver if packet.sender==1 else packet.sender)
            rid=payload[0]
            if peer is None or not peer.body.alive or distance(self.body.position,peer.body.position)>3:
                self.log("transport_failed",peer=peer.id if peer else None,request_id=rid)
                continue
            if packet.sender!=1:
                _,tile,target=payload
                self.hints.append((peer.id,tile,target,rid))
                self.metrics["received_hints"]+=1
                self.log("answer",peer=peer.id,topic=tile,target=target,request_id=rid,symbol=packet.symbol)
                continue
            _,kind,topic,report=payload
            peer.remember(world.local(peer.body))
            self.log("message_observed",peer=peer.id,request_id=rid,observation=report)
            if kind=="report":
                continue
            known=[p for p,(tile,_) in peer.memory.items() if tile==topic]
            if not known or peer.body.energy<27.:
                self.log("declined",peer=peer.id,request_id=rid,reason="unobserved or unavailable")
                continue
            target=min(known,key=lambda p:distance(peer.body.position,p))
            answer,_=broadcast(Radio(peer.id,peer.body),Radio(1,self.body),packet.symbol,world.tick,
                               distance_limit=3,cost=.18,latency=1)
            if answer and len(self.queue)<self.queue.maxlen:
                self.queue.append((answer,(rid,topic,target)))

    def step(self):
        if not self.body.alive:
            return None
        world,b,c=self.world,self.body,self.core
        self.events.clear()
        world.advance()
        self.deliver()
        self.sync()
        local,peers=self.perceive()
        before_energy,before_health=b.energy,b.health
        ops=c.local_life.model.operations
        _,action,context,info,gain,prediction,features=self.choose(local,peers)
        frame=None
        if action.kind in ("ask","inspect","read"):
            self.next_inquiry=world.tick+8
            self.metrics["inquiries"]+=1
            if self.advanced:
                structure,sentence=self.frame(action,context,info,gain)
                frame=dict(structure=structure,rendered=sentence)
                self.metrics["structured"]+=1
                self.log("question",request_id=world.tick,**frame)
        evidence=world.act(b,action,{r.body.position for r in world.residents if r.body.alive})
        if action.kind in ("ask","report","cooperate") and b.alive:
            evidence["success"]=self.communicate(action,peers)
        actual=(b.energy-before_energy)/10.
        harm=(before_health-b.health)/12.
        immutable=self.frozen_model.predict(features)[0]
        error=abs(actual-prediction[0])*10.
        self.metrics["error"]+=error
        self.metrics["frozen_error"]+=abs(actual-immutable)*10.
        self.metrics["energy_spent"]+=max(0.,before_energy-b.energy)
        self.metrics["successful_"+action.kind]+=evidence["success"]
        self.metrics["action_"+action.kind]+=1
        if action.kind in ("work","grasp","read","drink","inspect"):
            self.skills[action.kind]+=evidence["success"]
            c.lifetime.episodes.append((c.age,action.kind,action.target,bool(evidence["success"])))
            if evidence["evidence"]:
                if action.topic:
                    c.lifetime.remember("settlement:"+action.topic,evidence["evidence"],c.age,.76)
                self.log("evidence",action=action.kind,target=action.target,observed=evidence["evidence"])
            if action.topic:
                self.recent.append((action.topic,evidence["evidence"]))
            if self.advanced:
                learner=c.local_life.model
                learner.record(context,1 if evidence["success"] else -1,world.tick%4!=0)
                review=learner.review(True) if world.tick%6==0 else None
                if review:
                    self.metrics["retained"]+=review["status"]=="retained"
                    self.log("revision",review=review)
        if self.neural:
            self.model.update(features,[actual,max(0.,harm),0.,0.,0.,0.,0.],[1,1,0,0,0,0,0],rate=.009)
            self.metrics["forecast_ops"]+=self.model.cost*3
            b.energy-=self.model.cost*3*OP_ENERGY
            # A proposal rejected by the affordance ranker did not cause the
            # observed motor result. Update only its forecast head in that case.
            motor_credit=c.last_action==self.code(action) and action.kind in ("walk","eat","rest")
            reward=clamp(actual-harm,-1.,1.) if motor_credit else c.brain.reward_baseline
            Brain.learn(c.brain,reward,self.world.stock.get(b.position,0.)
                        if self.world.tiles[b.position] in ("market","field") else 0.)
            c.brain.memory.observe(b.position,self.legacy_view(world.local(b))[b.position][1],c.age,c.brain.genetic["decay"])
        query_ops=c.local_life.model.operations-ops
        self.metrics["inquiry_ops"]+=query_ops
        b.energy-=query_ops*OP_ENERGY
        if b.energy<=0. and b.alive:
            b.alive,b.cause=False,"energy depletion"
        c.local_life.habit.update((local[next(p for p in local if local[p]["distance"]==0)]["tile"],action.kind),
                                  max(0.,1.-error/5.),None,bool(evidence["evidence"]),min(1.,info),error>3.)
        self.sync()
        c.visited.add(b.position)
        c.age+=1
        c.memory[b.position]=(self.legacy_view(world.local(b))[b.position][1],c.pain)
        c.memory.move_to_end(b.position)
        if len(c.memory)>64:
            c.memory.popitem(last=False)
        for resident in world.residents:
            occupied={r.body.position for r in world.residents if r is not resident and r.body.alive}
            world.resident_step(resident,occupied|{b.position})
        return dict(tick=world.tick,age=c.age,body=asdict(b),action=asdict(action),outcome=evidence,
                    prediction=prediction[0]*10.,observed_energy_delta=actual*10.,error=error,
                    curiosity=info,stagnation=c.local_life.habit.level,question=frame,
                    perception=[dict(position=p,**cell) for p,cell in local.items()],
                    nearby=[dict(id=r.id,name=r.name,position=r.body.position) for r in peers],
                    skill_observations=dict(self.skills),memory_entries=len(c.memory),
                    hypothesis=c.local_life.model.describe(),events=list(self.events))
