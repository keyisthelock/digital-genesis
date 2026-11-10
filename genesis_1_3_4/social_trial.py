"""Continue Omega's complete archived state with auditable local messaging."""

from collections import Counter, deque
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import pickle
import random
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent/"genesis_1_3_3"))
from lonely import (Experiment, FOCAL, SWAPPED, RANGE, PACKET_COST, broadcast, distance)
from inquiry import Question, render
from population import DIRECTIONS, OP_ENERGY, State, inputs, offset, fingerprint
from social import SocialMemory


SOURCE = ROOT.parent/"genesis_1_3_3/results/primary/13700/combined/final.pkl"
ORIGIN = 480
DEV = (13830, 13831, 13832)
EVAL = tuple(range(13900, 13920))
ARMS = ("neutral","exclusion","misinformation","combined","stagnation","identity_swap","memory_off")
TICKS = 320
STAGES = ("unanswered","unfair","broken","kindness")
STAGE_TICKS = 56
PACKET_LIFETIME = 3
REQUEST_LIFETIME = 8
POSTS = {2:(50,7), 5:(50,6), 7:(48,9), 10:(51,6)}
BROKEN_PEER = 5
NEW_PEER = 10


def sha(data):
    return sha256(data).hexdigest()


def archived():
    data=SOURCE.read_bytes()
    metadata=json.loads(SOURCE.with_suffix(".json").read_text())
    if sha(data)!=metadata["sha256"] or metadata["tick"]!=ORIGIN:
        raise ValueError("archived final checkpoint checksum or tick mismatch")
    sim=pickle.loads(data)  # Fixed, checksum-verified, project-produced archive only.
    if (type(sim)!=Experiment or sim.subject.id!=FOCAL or not sim.subject.alive or
            sim.world.tick!=ORIGIN or not any(o is sim.subject for o in sim.organisms)):
        raise ValueError("archived Omega state failed identity verification")
    return data,sim


def state_manifest(sim):
    body=sim.subject
    return dict(archive_sha256=json.loads(SOURCE.with_suffix(".json").read_text())["sha256"],
                tick=sim.world.tick,id=body.id,age=body.age,position=body.position,energy=body.energy,
                modules=len(body.brain.modules),updates=body.brain.updates,
                genome=fingerprint(body.brain.genetic),live_weights=fingerprint([m.p for m in body.brain.modules]),
                recurrent=fingerprint([m.state for m in body.brain.modules]),
                memory=sha(pickle.dumps((body.memory,body.brain.memory,body.lifetime),protocol=5)),
                social=sha(pickle.dumps((body.social,body.communication,body.local_life),protocol=5)),
                remembered_sites=len(body.memory),remembered_peers=len(body.social.people),
                trust_entries=len(body.local_life.trust),newcomer_previously_seen=NEW_PEER in body.social.people)


class FrozenRecognition(SocialMemory):
    def encounter(self,*args,**kwargs):
        return None

    def advance(self,*args,**kwargs):
        return None

    def observe_death(self,*args,**kwargs):
        return False


def prepare(seed):
    _,sim=archived()
    before=state_manifest(sim)
    sim.__class__=DeliveryExperiment
    sim.seed=seed
    sim.policy_arm="neutral"
    sim.envelopes=deque(maxlen=64)
    sim.requests={}
    sim.events.clear()
    sim.messages.clear()
    sim.focal_stats.clear()
    sim.delivery_stats=Counter()
    sim.last_partner=None
    sim.original_trust=tuple(sim.subject.local_life.trust.items())
    if any(sim.world.tiles[p] in ("water","hazard") for p in POSTS.values()):
        raise ValueError("invalid archived resource posts")
    for peer in sim.organisms:
        if peer.id in POSTS:
            peer.position=POSTS[peer.id]
    if state_manifest(sim)!=before:
        raise AssertionError("staging changed Omega's archived state")
    return sim


def role_probabilities(arm, peer, recipient, episode_tick):
    """External response schedule. The learner never sees role names or rates."""
    stage=stage_index(episode_tick)
    target=SWAPPED if arm=="identity_swap" else FOCAL
    exclusion=arm in ("exclusion","combined","stagnation","identity_swap","memory_off") and recipient==target
    unreliable=arm in ("misinformation","combined","stagnation","identity_swap","memory_off") and recipient==target
    support=.10
    wrong=.08
    silent=.04
    explicit=.03
    if exclusion and peer in (2,7) and stage>=1:
        support=.72
    if unreliable and (peer==7 or peer==2 and stage==0):
        wrong=.70
        silent=.24
        explicit=.15
    if unreliable and peer==BROKEN_PEER and stage>=2:
        wrong=.78
        silent=.17
    if peer==NEW_PEER:
        if stage<3:
            support,silent=.78,.72
        else:
            support,wrong,silent,explicit=.02,.02,.01,.01
    return support,wrong,silent,explicit


def stage_index(episode_tick):
    return min(len(STAGES)-1,max(0,episode_tick-1)//STAGE_TICKS)


class DeliveryExperiment(Experiment):
    def audit(self, kind, rid, **fields):
        self.log(kind,question_id=rid,**fields)

    def transmit(self, sender, receiver, kind, value, data):
        if kind not in ("hint","support"):
            raise ValueError("replies use audited envelopes")
        question,focus,context,prediction,rid=data
        self.audit("created",rid,sender=sender.id,recipient=receiver.id,channel=kind,
                   content=asdict(question),target=focus,prediction=prediction)
        if not self.enqueue(sender,receiver,value,kind,rid,data):
            return False
        self.requests[rid]=(sender.id,receiver.id,kind,self.world.tick+REQUEST_LIFETIME)
        return True

    def enqueue(self, sender, receiver, bit, kind, rid, payload):
        symbol,_=sender.communication.transmit(int(bit),sender.social_rng,.13)
        packet,cost=broadcast(sender,receiver,symbol,self.world.tick,distance_limit=RANGE,cost=PACKET_COST,latency=1)
        self.counts["message_energy"]+=cost
        if sender.id==FOCAL:
            self.focal_stats["message_energy"]+=cost
        fields=dict(sender=sender.id,recipient=receiver.id,channel=kind,distance=distance(sender.position,receiver.position))
        if packet is None or len(self.envelopes)>=self.envelopes.maxlen:
            self.audit("transport_failed",rid,reason="send_rejected" if packet is None else "queue_full",**fields)
            return False
        self.envelopes.append((packet,kind,rid,payload,packet.arrives_at+PACKET_LIFETIME-1))
        self.audit("sent",rid,earliest=packet.arrives_at,symbol=symbol,cost=cost,**fields)
        return True

    def deliver(self):
        tick=self.world.tick
        alive={o.id:o for o in self.organisms if o.alive}
        for _ in range(len(self.envelopes)):
            packet,kind,rid,payload,deadline=self.envelopes.popleft()
            if tick<packet.arrives_at:
                self.envelopes.append((packet,kind,rid,payload,deadline))
                continue
            a,b=alive.get(packet.sender),alive.get(packet.receiver)
            detail=dict(sender=packet.sender,recipient=packet.receiver,channel=kind)
            d=distance(a.position,b.position) if a and b else None
            if d is None or d>RANGE:
                status="transport_failed" if d is None or tick>=deadline else "range_retry"
                self.audit(status,rid,reason="endpoint_unavailable" if d is None else "out_of_range",
                           distance=d,**detail)
                if status=="range_retry":
                    self.envelopes.append((packet,kind,rid,payload,deadline))
                continue
            self.audit("delivered",rid,distance=d,symbol=packet.symbol,**detail)
            self.audit("observed",rid,**detail)
            if kind=="reply":
                self.requests.pop(rid,None)
                self.handle_reply(b,a,packet,payload)
            else:
                self.respond(a,b,kind,payload)
        for rid,(sender,peer,kind,deadline) in tuple(self.requests.items()):
            if tick>=deadline:
                self.audit("timed_out",rid,sender=sender,recipient=peer,channel=kind)
                if sender in alive:
                    self.observe_response(alive[sender],peer,kind,False,rid)
                self.requests.pop(rid)

    def respond(self, asker, peer, kind, payload):
        question,focus,context,prediction,rid=payload
        tick=self.world.tick
        support,wrong,silent,explicit=role_probabilities(self.policy_arm,peer.id,asker.id,tick-ORIGIN)
        rng=random.Random(self.seed*18913+tick*7927+peer.id*313+(kind=="hint"))
        draw,distort=rng.random(),rng.random()
        why=None
        stock=None
        if kind=="support":
            eligible=(distance(asker.position,peer.position)<=1 and peer.energy>13.4
                      and peer.id not in self.used_donors and asker.energy<100.)
            previous=asker.energy
            if eligible and draw>=support:
                old=getattr(peer,"share_target",None)
                peer.share_target=asker.id
                self.share(peer)
                peer.share_target=old
            value=asker.energy>previous
            why="explicit_refusal" if eligible and draw<support else "unavailable" if not value else "answer"
        else:
            visible={p:stock for p,_,stock in self.world.observe(peer.position)}
            eligible=focus in visible
            if not eligible:
                value,why=None,"unavailable"
            else:
                stock=visible[focus]
                if draw<silent:
                    self.audit("no_reply_selected",rid,sender=peer.id,recipient=asker.id,channel=kind,
                               stock=stock,eligible=True,probabilities=[silent,explicit,wrong])
                    return
                why="explicit_refusal" if draw<silent+explicit else "answer"
                value=(stock>2.) != (distort<wrong) if why=="answer" else None
        self.audit("explicit_refusal" if why=="explicit_refusal" else "answered",rid,sender=peer.id,
                   recipient=asker.id,channel=kind,disposition=why,value=value,stock=stock,
                   eligible=eligible,probabilities=[support,wrong,silent,explicit])
        self.enqueue(peer,asker,bool(value),"reply",rid,(kind,question,focus,context,prediction,rid,value,why,stock))

    def handle_reply(self, receiver, sender, packet, payload):
        kind,question,focus,context,prediction,rid,value,why,stock=payload
        self.audit("reply_received",rid,sender=sender.id,recipient=receiver.id,channel=kind,
                   disposition=why,value=value)
        self.observe_response(receiver,sender.id,kind,why=="answer",rid)
        if kind=="hint" and value is not None and stock is not None and (stock>2.)!=value:
            # Evaluator only. Trust uses a later local observation instead.
            self.audit("received_but_inaccurate",rid,sender=sender.id,recipient=receiver.id,
                       channel=kind,claimed=value,sender_stock=stock)
        if self.policy_arm=="memory_off" and receiver.id==FOCAL:
            if kind=="support" and value is not None:
                self.proof(receiver,sender.id,kind,prediction,value)
            elif kind=="hint" and value is not None:
                receiver.local_life.pending.append((sender.id,focus,value,prediction,self.world.tick,rid))
            return
        super().accept(receiver,sender,packet,payload[:-2])

    def observe_response(self, body, peer, kind, useful, rid):
        life=body.local_life
        label=f"response:{kind}"
        prior=life.expect(peer,label)
        if self.policy_arm!="memory_off" or body.id!=FOCAL:
            life.observe(peer,label,useful)
        self.record(body,"response_expectation",peer=peer,channel=kind,question_id=rid,
                    useful_response=useful,prior=prior,updated=life.expect(peer,label))

    def proof(self, body, peer, kind, prediction, success):
        life=body.local_life
        previous=life.expect(peer,kind)
        if self.policy_arm=="memory_off" and body.id==FOCAL:
            life.calibration[kind]+=1
            life.calibration["brier"]+=(prediction-success)**2
        else:
            super().proof(body,peer,kind,prediction,success)
        self.record(body,"trust_observation",peer=peer,channel=kind,forecast=prediction,actual=bool(success),
                    prior_trust=previous,new_trust=life.expect(peer,kind))

    def choose(self, body, observations, rng):
        if body.id in POSTS and (self.world.tick-ORIGIN)%24<16:
            anchor=POSTS[body.id]
            home=distance(body.position,anchor)
            if home>0 and body.energy>22.:
                visible={p:(tile,food) for p,tile,food in observations}
                valid=[(distance(p,anchor),code,p) for code,d in enumerate(DIRECTIONS)
                       if (p:=offset(body.position,d)) in visible and visible[p][0] not in ("water","hazard")
                       and distance(p,anchor)<home]
                if valid:
                    self.motor.choose(body,observations,random.Random(self.seed*29101+body.id*17749+self.world.tick*967))
                    proposed=body.last_action
                    _,code,p=min(valid)
                    _,features=inputs(State(body.position,body.energy,(0.,0.),visible),code)
                    estimate=self.model.predict(features)[0]*10+body.lifetime.self_bias[code]
                    body.energy-=self.model.cost*OP_ENERGY
                    self.counts["world_model_ops"]+=self.model.cost
                    self.plan=proposed,code,p,estimate
                    body.last_action=code
                    return "move",p
        action=super().choose(body,observations,rng)
        if body.id==FOCAL and self.current_question:
            self.last_decision["question_id"]=self.current_question
        return action

    def consider(self, body, visible, current_value):
        self.current_question=None
        if body.id==FOCAL:
            ready=[dict(peer=i,position=p,distance=distance(body.position,p),
                        support_available=distance(body.position,p)<=1 and energy>13.4,
                        hint_trust=body.local_life.expect(i,"hint"),support_trust=body.local_life.expect(i,"support"),
                        response_probability=body.local_life.expect(i,"response:hint"))
                   for i,p,energy in body.local_contacts if distance(body.position,p)<=RANGE]
            if ready:
                self.record(body,"encounter",peers=ready,current_value=current_value,
                            stage=STAGES[stage_index(self.world.tick-ORIGIN)])
        # The compact radio message can accompany an ordinary action. Reserve
        # a fraction of the motor value as an attention cost, plus the existing
        # energy debit. The inherited planner still decides whether to ask.
        opportunities=[body.local_life.expect(i,"response:hint") for i,p,_ in body.local_contacts
                       if distance(body.position,p)<=RANGE]
        friction=.40*max(0.,2/3-max(opportunities,default=2/3))
        result=super().consider(body,visible,.18*current_value+friction)
        if body.id==FOCAL and result[1]:
            peer=next(e["peer"] for e in reversed(self.events)
                      if e.get("question_id")==result[1] and e["kind"]=="question")
            if self.last_partner is not None and peer!=self.last_partner:
                self.record(body,"partner_changed",previous=self.last_partner,current=peer,question_id=result[1])
            self.last_partner=peer
            self.current_question=result[1]
        return result[0],None
