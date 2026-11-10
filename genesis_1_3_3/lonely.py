"""Omega's experiment, using the Dawn lifecycle on the existing Earth world."""

from collections import Counter, deque, OrderedDict
from dataclasses import asdict
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "genesis_1_3_1"))
sys.path.insert(0, str(ROOT.parent / "genesis_1_3_2"))
from unwritten import LEARNED_CONCEPTS
from inquiry import CONCEPTS, Question, render
from revision import Habituation, Model
from population import (DIRECTIONS, OP_ENERGY, Population, State, World, inputs, offset,
                        load_founder)
from communication import broadcast


ARMS = ("neutral", "exclusion", "misinformation", "combined", "stagnation", "identity_swap")
DEV = (13630, 13631, 13632)
EVAL = tuple(range(13700, 13720))
HORIZON = 480
FOCAL = 1
SWAPPED = 2
ONSET = 12
RANGE = 3
PACKET_COST = .18
REFUSAL = .72
DISTORTION = .65


def distance(a, b):
    return sum(abs(x-y) for x, y in zip(a,b))


def policy_probability(seed, donor, recipient, tick, kind, arm):
    """Only an external response policy reads the experimentally assigned ID."""
    target = SWAPPED if arm == "identity_swap" else FOCAL
    selective = random.Random(seed*561 + donor*441).random() < .80
    exposed = tick >= ONSET and selective and donor != target and recipient == target
    if kind == "support":
        return REFUSAL if exposed and arm in ("exclusion","combined","stagnation","identity_swap") else .12
    return DISTORTION if exposed and arm in ("misinformation","combined","stagnation","identity_swap") else .08


class Earth(World):
    store = frozenset()

    def climate(self):
        return self.daylight


class LocalLife:
    def __init__(self):
        self.trust = OrderedDict()
        self.pending = deque(maxlen=12)
        self.model = Model(LEARNED_CONCEPTS)
        self.habit = Habituation()
        self.last_proof = None
        self.progress = None
        self.next_request = 0
        self.last_attempt = 0
        self.received = 0.
        self.unmet = 0.
        self.calibration = Counter()

    def expect(self, peer, kind):
        yes, no = self.trust.get((peer,kind), (2.,1.))
        return yes/(yes+no)

    def observe(self, peer, kind, success):
        key = peer,kind
        yes,no = self.trust.get(key,(2.,1.))
        self.trust[key] = (.96*yes+success,.96*no+1-success)
        self.trust.move_to_end(key)
        if len(self.trust)>32:
            self.trust.popitem(last=False)


class Experiment(Population):
    def __init__(self, seed):
        gene, model = load_founder()
        super().__init__("aegean", "reference", seed, gene, model, HORIZON)
        self.world = Earth(random.Random(seed))
        self.world.share_energy = self.share
        # Same food-bearing neighborhood for all arms. No resources or tiles
        # are modified. The selected spawn is independent of pilot outcomes.
        center = random.Random(seed+13).choice(sorted(self.world.food))
        sites = sorted(self.world.land, key=lambda p:(distance(p,center),p))
        for body,p in zip(self.organisms,sites):
            body.position = p
        self.subject = self.organisms[0]
        self.policy_arm = "neutral"
        self.messages = deque(maxlen=48)
        self.used_donors = set()
        self.focal_stats = Counter()
        self.last_decision = {}
        self.recent_life = deque(maxlen=24)

    def born(self, position, parent=None):
        body = super().born(position, parent)
        body.local_life = LocalLife()
        return body

    def attention(self, body, other, p, uncertainty):
        life = body.local_life
        return (1 if life.expect(other, "hint") >= .6 else -1,
                1 if self.world.daylight >= .5 else -1,
                1 if body.energy < 60 else -1,
                1 if self.world.tick-life.last_attempt > 24 else -1,
                1 if distance(body.position,p) <= 1 else -1,
                1 if body.social.bond(other)>=.15 else -1,
                1 if uncertainty>.55 else -1,
                1 if body.energy < 78 else -1,
                1 if body.pain>0 else -1)

    def draw(self, donor, kind):
        return random.Random(self.seed*91471 + self.world.tick*21691 + donor*3571 + (kind=="hint")).random()

    def record(self, body, event, **fields):
        if body.id in (FOCAL, SWAPPED):
            self.log(event, id=body.id, **fields)

    def share(self, donor):
        if donor.id in self.used_donors:
            return
        recipient = next((o for o in self.organisms if o.id == donor.share_target and o.alive), None)
        if recipient is None or distance(donor.position,recipient.position)>1 or donor.energy<=10.2:
            return
        prior = recipient.energy
        super().share(donor)
        amount = recipient.energy-prior
        if amount>0:
            self.used_donors.add(donor.id)
            self.record(recipient,"transfer_received",peer=donor.id,amount=amount)
            self.record(donor,"transfer_given",peer=recipient.id,amount=amount)

    def transmit(self, sender, receiver, kind, value, data):
        symbol, _ = sender.communication.transmit(int(value), sender.social_rng, .13)
        packet, cost = broadcast(sender,receiver,symbol,self.world.tick,distance_limit=RANGE,cost=PACKET_COST,latency=1)
        if cost:
            self.counts["message_energy"] += cost
            if sender.id == FOCAL:
                self.focal_stats["message_energy"] += cost
        if packet is None or len(self.messages) == self.messages.maxlen:
            return False
        self.messages.append((packet,kind,data))
        self.record(sender,"packet_sent",peer=receiver.id,channel=kind,symbol=symbol,arrival=packet.arrives_at)
        return True

    def deliver(self):
        alive = {o.id:o for o in self.organisms if o.alive}
        while self.messages and self.messages[0][0].arrives_at<=self.world.tick:
            packet,kind,data = self.messages.popleft()
            sender,receiver = alive.get(packet.sender),alive.get(packet.receiver)
            if sender is None or receiver is None or distance(sender.position,receiver.position)>RANGE:
                continue
            if kind == "reply":
                self.accept(receiver,sender,packet,data)
                continue
            question, focus, context, prediction, issued = data
            probability = policy_probability(self.seed,receiver.id,sender.id,self.world.tick,kind,self.policy_arm)
            modified = self.draw(receiver.id,kind)<probability
            eligibility = (distance(receiver.position,sender.position)<=1 and receiver.energy>13.4
                           and receiver.id not in self.used_donors and sender.energy<100.)
            if kind=="support":
                energy = sender.energy
                if eligibility and not modified:
                    old_target = getattr(receiver,"share_target",None)
                    receiver.share_target = sender.id
                    self.share(receiver)
                    receiver.share_target = old_target
                value = sender.energy>energy
            else:
                seen = {p:stock for p,_,stock in self.world.observe(receiver.position)}
                eligibility = focus in seen
                value = (seen[focus]>2.) != modified if eligibility else None
            self.record(sender,"response_opportunity",peer=receiver.id,channel=kind,eligible=eligibility,
                        assigned=modified,probability=probability,value=value)
            self.transmit(receiver,sender,"reply",bool(value), (kind,question,focus,context,prediction,issued,value))

    def accept(self, receiver, sender, packet, data):
        kind,question,focus,context,prediction,issued,value = data
        life = receiver.local_life
        self.record(receiver,"answer",peer=sender.id,channel=kind,question_id=issued,value=value,symbol=packet.symbol)
        if value is None:
            return
        if kind=="support":
            before_ops = life.model.operations
            observed_prediction = life.model.forecast(context)
            loss,mismatch = life.model.record(context,1 if value else -1,
                                             update=life.calibration["support"]%4 != 3)
            if life.calibration["support"]%4 == 3:
                life.progress = life.last_proof-loss if life.last_proof is not None else None
                life.last_proof = loss
            review = life.model.review(True)
            if review:
                self.record(receiver,"revision",peer=sender.id,question_id=issued,review=review)
            receiver.energy -= (life.model.operations-before_ops)*OP_ENERGY
            receiver.check_death()
            self.proof(receiver,sender.id,kind,prediction,value)
            receiver.lifetime.episodes.append((self.world.tick,"response",sender.id,bool(value)))
            receiver.lifetime.remember(f"support:{sender.id}",value,self.world.tick,life.expect(sender.id,kind))
            life.unmet = .85*life.unmet + .15*(not value)
            receiver.social.encounter(sender.id,self.world.tick,.04 if value else -.035)
            self.record(receiver,"model_feedback",peer=sender.id,question_id=issued,before=observed_prediction,
                        after=life.model.forecast(context),mismatch=mismatch)
        else:
            life.pending.append((sender.id,focus,bool(value),prediction,self.world.tick,issued))
            receiver.lifetime.remember(f"food:{focus}",(sender.id,bool(value)),self.world.tick,prediction)

    def proof(self, body, peer, kind, prediction, success):
        life = body.local_life
        loss = (prediction-success)**2
        life.observe(peer,kind,success)
        life.calibration[kind] += 1
        life.calibration["brier"] += loss
        life.calibration["correct"] += (prediction>=.5)==success
        self.record(body,"verified",peer=peer,channel=kind,prediction=prediction,outcome=bool(success),
                    updated=life.expect(peer,kind),error=loss)

    def choose(self, body, observations, ignored_rng):
        rng = random.Random(self.seed*29101 + body.id*17749 + self.world.tick*967)
        self.motor.choose(body,observations,rng)
        original = body.last_action
        visible = {p:(tile,food) for p,tile,food in observations}
        life = body.local_life
        for pending in tuple(life.pending):
            peer,pos,claim,predicted,tick,issued = pending
            age = self.world.tick-tick
            # Only near-term verification is accepted. Resource depletion can
            # still change the answer between the two observations.
            if age<=4 and pos in visible:
                self.proof(body,peer,"hint",predicted,(visible[pos][1]>2.)==claim)
                self.record(body,"hint_verified",peer=peer,question_id=issued,position=pos,
                            claimed=claim,observed=visible[pos][1],age=age)
                life.pending.remove(pending)
            elif age>4:
                life.pending.remove(pending)
        food = visible[body.position][1]
        candidates = [(5,body.position,-.30)]
        if food>1. and body.energy<94.:
            candidates.append((4,body.position,min(food,10.)*.32))
        for code,direction in enumerate(DIRECTIONS):
            p = offset(body.position,direction)
            tile,stock = visible.get(p,("water",0.))
            if tile=="water":
                continue
            adjacent = max(visible.get(offset(p,d),("",0.))[1] for d in DIRECTIONS)
            value = .14*min(18.,stock)+.035*min(18.,adjacent)+.20*(p not in body.memory)-4.*(tile=="hazard")
            for peer,pos,claim,trust,tick,issued in life.pending:
                if claim and trust>.5 and distance(p,pos)<distance(body.position,pos):
                    value += .35*(2*trust-1)
            candidates.append((code,p,value))
        if original==6:
            candidates.append((6,body.position,.40 if body.energy>80 else -.6))
        code,pos,value = max(candidates,key=lambda v:v[2]+.32*(v[0]==original)+rng.random()*.10)
        curiosity, opportunity = self.consider(body,visible,value)
        if opportunity is not None:
            code,pos = 5,body.position
        elif code==6:
            self.share(body)
        _,features = inputs(State(body.position,body.energy,(0.,0.),visible),code if code!=6 else 5)
        own = self.model.predict(features)[0]*10+body.lifetime.self_bias[code]
        body.energy -= self.model.cost*OP_ENERGY
        self.counts["world_model_ops"] += self.model.cost
        self.plan = original,code,pos,own
        body.last_action = code
        if body.id==FOCAL:
            self.last_decision = dict(proposed=original,action=code,planned=pos,predicted_delta=own,
                                      curiosity=curiosity,question_id=opportunity,
                                      visible_food=[(p,round(stock,4)) for p,(_,stock) in visible.items() if stock>0.])
        life.habit.update((visible[body.position][0],code), max(0.,1.-abs(body.lifetime.self_bias[code])/5.),
                          life.progress, life.progress is not None and life.progress>.12,
                          min(1.,curiosity), abs(body.lifetime.self_bias[code])>1.)
        life.progress = None
        return ("move" if code<4 else "eat" if code==4 else "share" if code==6 else "rest"),pos

    def consider(self, body, visible, current_value):
        life = body.local_life
        tick = self.world.tick
        if body.energy<13. or tick<life.next_request or not body.local_contacts:
            return 0.,None
        options = []
        before_ops = life.model.operations
        for peer,p,energy in body.local_contacts[:4]:
            d = distance(body.position,p)
            if d<=1 and energy>13.4 and body.energy<86.:
                options.append((peer,p,"support"))
            if d<=RANGE and d>0:
                frontier = [offset(p,(dx*2,dy*2)) for dx,dy in DIRECTIONS]
                frontier = [f for f in frontier if f not in visible and
                            0<=f[0]<self.world.width and 0<=f[1]<self.world.height]
                if frontier:
                    options.append((peer,min(frontier,key=lambda q:(distance(body.position,q),q)),"hint"))
        ranked = []
        for peer,p,kind in options:
            prediction = life.expect(peer,kind)
            uncertainty = 1-abs(2*prediction-1)
            context = self.attention(body,peer,p,uncertainty)
            if kind=="support":
                forecast = life.model.forecast(context)
                uncertainty = (uncertainty+1-max(forecast))*.5
                prediction = (prediction+forecast[2])*.5 if life.calibration["support"] else prediction
                benefit = .95*prediction + .35*uncertainty
                cost = .23
                if body.energy<45.:
                    benefit += .36*prediction
            else:
                benefit = .62*uncertainty + .32*prediction
                cost = .23+.035*distance(body.position,p)
            advantage = benefit-cost-max(-.05,current_value)
            adjustment = (.22*life.habit.level*uncertainty
                          if self.policy_arm=="stagnation" and body.id==FOCAL and advantage>0 else 0.)
            ranked.append((advantage+adjustment, peer,p,kind,prediction,uncertainty,context,advantage))
            life.model.operations += 52 + len(life.model.weights)
        charge = (life.model.operations-before_ops)*OP_ENERGY
        body.energy -= charge
        if not ranked:
            return 0.,None
        score,peer,p,kind,prediction,uncertainty,context,advantage = max(ranked,key=lambda item:item[0])
        if score<=0.:
            return uncertainty,None
        contact = next((o for o in self.organisms if o.id==peer and o.alive),None)
        if contact is None:
            return uncertainty,None
        # Select grounded conditions where the strongest learned rule and
        # observed setting overlap, then preserve the whole intervention.
        terms, _ = life.model.strongest_rule()
        question = Question("cooperation" if kind=="support" else "local food",
                            "predicts",tuple(CONCEPTS[i] for i in terms),context,"peer",uncertainty,advantage)
        identity = f"{body.id}:{tick}"
        if not self.transmit(body,contact,kind,False,(question,p,context,prediction,identity)):
            return uncertainty,None
        life.next_request = tick+10
        life.last_attempt = tick
        self.record(body,"question",peer=peer,channel=kind,question_id=identity,structure=asdict(question),
                    rendering=render(question),prediction=prediction,position=body.position,target=p,
                    energy=body.energy,current_value=current_value,prior_evidence=list(body.lifetime.episodes)[-4:],
                    applied_stagnation=self.policy_arm=="stagnation" and body.id==FOCAL,raw_advantage=advantage)
        return uncertainty,identity

    def step(self):
        subject = self.subject
        was_alive = subject.alive
        before_energy = subject.energy
        previous = len(self.events)
        self.used_donors.clear()
        super().step()
        if was_alive:
            life = subject.local_life
            snapshot = dict(tick=self.world.tick,id=subject.id,age=subject.age,alive=subject.alive,
                            cause=subject.death_cause,energy=subject.energy,health=subject.health,
                            position=subject.position,food=subject.acquired,visited=len(subject.visited),
                            offspring=subject.offspring,model=life.model.describe(),
                            stagnation=life.habit.level,calculated_unmet_expectation=life.unmet,
                            trust=[dict(peer=i,kind=k,p=life.expect(i,k)) for i,k in life.trust],
                            neural_ops=subject.brain.ops,neural_energy=subject.brain_cost,
                            inquiry_ops=life.model.operations,actual_delta=subject.energy-before_energy,
                            **self.last_decision)
            self.recent_life.append(snapshot)
            self.log("life", snapshot=snapshot)
        return self.events[previous:]
