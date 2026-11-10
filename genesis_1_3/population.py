"""Matched regional populations built on the existing neural and energy mechanics."""

from collections import Counter, deque
from dataclasses import asdict
from hashlib import sha256
import json
from math import sin, tau
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/"genesis_1_1_5"))
from ablation import ENGINE, OPTIONS, OP_ENERGY, MODEL_OPS, TIME_DISCOUNT
from cognition import Brain, NeuralPolicy, clip, mutate
from communication import Communication, broadcast, founder_genome, inherited_genome
from hypotheses import Beliefs, HYPOTHESES, means, outcomes, updated, variance
from model import DIRECTIONS, State, TransitionModel, inputs, offset
from neural_survival import SurvivalBrain
from organism import DEFAULT_GENOME, Organism
from social import SocialMemory
from world import World

from cognitive import FOUNDATION, Frame, Lifetime, Query, retrieve

REGIONS = ("aegean","indus","nile","yellow_river")
ARMS = ("reference","cognitive")
PHASES = ("stability","uncertainty","social_knowledge","novelty","self_model")
POPULATION = 8
CAP = 12
QUESTION_LIMIT = 128  # Per population and phase, including nonverbal inquiries.
PACKET_LIMIT = 256    # Per population and phase, including delivery records.
CHILD_ENERGY = 34.
CONDITIONS = ("switch_a","switch_b","joint")


def fingerprint(value):
    return sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def load_founder():
    path = ROOT/"founder"
    manifest = json.loads((ROOT.parent/"genesis_1_1_5"/"protocol.timing.lock.json").read_text())
    for name in ("trained_32.json","model.json"):
        if sha256((path/name).read_bytes()).hexdigest()!=manifest["inputs"][name]:
            raise ValueError(f"founder archive hash mismatch: {name}")
    gene = json.loads((path/"trained_32.json").read_text())
    if len(gene["modules"])!=32:
        raise ValueError("expected the verified 32-module founder")
    saved = json.loads((path/"model.json").read_text())
    model = TransitionModel(3201)
    model.hidden,model.output = saved["hidden"],saved["output"]
    return gene,model


class Region(World):
    def __init__(self, region, seed):
        self.width,self.height = 18,12
        self.rng = random.Random(seed)
        self.tick = 0
        self.resource_fraction = 1.
        self.fruit = (8,5)
        self.stations = {(7,5),(10,6),(12,4)}
        self.store = {(6,4),(9,6)}
        self.tiles,self.food = {},{}
        for y in range(self.height):
            for x in range(self.width):
                p = (x,y)
                border = x in (0,17) or y in (0,11)
                water = (x<4 if region=="aegean" else x in (5,6) if region=="indus" else
                         x==4 if region=="nile" else y==8+(x//6)%2)
                crossing = y in (4,7) if region!="yellow_river" else x in (6,12)
                terrain = "water" if border or water and not crossing else "land"
                if terrain=="land" and self.rng.random()<.012:
                    terrain = "hazard"
                if p in self.stations:
                    terrain = "station"
                elif p in self.store:
                    terrain = "store"
                elif p==self.fruit:
                    terrain = "fruit"
                self.tiles[p] = terrain
                if terrain in ("station","store") or terrain=="land" and self.rng.random()<.38:
                    self.food[p] = 10.+self.rng.random()*12.
        self.land = [p for p,tile in self.tiles.items() if tile not in ("water","hazard")]
        self.season_offset = REGIONS.index(region)*100

    def climate(self):
        return .5+.5*sin(tau*(self.tick+self.season_offset)/320.)

    def advance(self):
        self.tick += 1
        rate = .22+.14*self.climate()
        for pos,stock in self.food.items():
            self.food[pos] = min(30.,stock+(.32 if pos in self.store else rate))


class Population:
    def __init__(self, region, arm, seed, gene, model, phase_ticks, frozen=False):
        self.region,self.arm,self.seed,self.phase_ticks = region,arm,seed,phase_ticks
        self.world = Region(region,seed)
        self.rng = random.Random(seed+723)
        self.motor = NeuralPolicy()
        self.model,self.gene,self.frozen = model,gene,frozen
        self.counts,self.phase_counts = Counter(),Counter()
        self.events,self.packets = [],deque(maxlen=CAP*2)
        self.births,self.population_peak,self.generation,self.next_id = 0,0,0,1
        self.organisms = []
        self.comm_gene = founder_genome(random.Random(3213))
        self.first_gene,self.latest_gene = gene,gene
        start = sorted(self.world.land,key=lambda p:(abs(p[0]-8)+abs(p[1]-5),p))
        for pos in start[:POPULATION]:
            self.organisms.append(self.born(pos))
        self.population_peak = len(self.organisms)
        self.world.share_energy = self.share

    def born(self, position, parent=None):
        identity = self.next_id
        self.next_id += 1
        rng = random.Random(self.seed*9176+identity*1000003)
        genome = mutate(parent.brain.genetic,rng) if parent else self.gene
        generation = parent.generation+1 if parent else 0
        body = Organism(identity,generation,position,DEFAULT_GENOME.copy(),parent.id if parent else None,
                        energy=CHILD_ENERGY if parent else 68.,maturity_age=100,max_lifespan=2300)
        body.brain = SurvivalBrain(genome,social=True,learning=not self.frozen)
        body.social,body.local_contacts = SocialMemory(),[]
        body.shuffled,body.social_rng = False,random.Random(self.seed+identity*79)
        body.brain_cost,body.brain_energy_parameter,body.brain_energy_op = 0.,.000002,.00001
        body.last_action = 5
        body.lifetime = Lifetime(self.arm=="cognitive")
        communication = inherited_genome([parent.communication.genome],rng) if parent else self.comm_gene
        body.communication = Communication(communication)
        self.events.append(dict(kind="birth",tick=self.world.tick,id=identity,parent=body.parent_id,
                                generation=generation,genome=genome,communication=communication))
        if parent:
            self.births += 1
            if generation>self.generation:
                self.latest_gene,self.generation = genome,generation
        return body

    def phase(self):
        return min(len(PHASES)-1,max(0,self.world.tick-1)//self.phase_ticks)

    def rule(self):
        rng = random.Random(self.seed*997)
        first,second,stock = (rng.choice((-1,1)) for _ in range(3))
        return ((first,0,stock),(first,second,stock),(-first,second,stock),
                (-first,-second,-stock),(first,-second,-stock))[self.phase()]

    def share(self, donor):
        target = next((o for o in self.organisms if o.id==donor.share_target and o.alive),None)
        if target is None or donor.energy<=10.2 or sum(abs(a-b) for a,b in zip(donor.position,target.position))>1:
            return
        amount = min(3.,target.hunger*100,donor.energy-10.2)
        if amount<=0.:
            return
        donor.energy -= amount+.2
        target.energy += amount
        donor.social.encounter(target.id,self.world.tick,.02)
        target.social.encounter(donor.id,self.world.tick,.08*amount)
        self.counts["shares"] += 1

    def log(self, kind, **fields):
        self.events.append(dict(kind=kind,tick=self.world.tick,phase=PHASES[self.phase()],**fields))

    def send(self, sender, receiver, act, sign, dimension, reply_to=None):
        key = (self.phase(),"packets")
        if self.phase_counts[key]>=PACKET_LIMIT:
            return False
        cue = int(sign==1)
        symbol,_ = sender.communication.transmit(cue,sender.social_rng,.13)
        packet,cost = broadcast(sender,receiver,symbol,self.world.tick,distance_limit=3,cost=.18,latency=1)
        if packet is None:
            return False
        frame = Frame(act,"station","stock" if dimension==2 else "loss","future" if act=="question" else "past",
                      act=="question" and sign==0,CONDITIONS[dimension],"predicts" if act=="question" else "observed",
                      2 if act=="question" else 1,symbol)
        if len(self.packets)==self.packets.maxlen:
            self.counts["packet_queue_dropped"] += 1
        question = f"{sender.id}:{self.world.tick}" if act=="question" else reply_to
        self.packets.append((packet,frame,cue,self.phase(),question))
        self.phase_counts[key] += 1
        self.counts[f"sent_{act}"] += 1
        self.counts["message_energy"] += cost
        self.log("symbol",sender=sender.id,receiver=receiver.id,frame=asdict(frame),cost=cost,question_id=question)
        return True

    def deliver(self):
        alive = {o.id:o for o in self.organisms}
        while self.packets and self.packets[0][0].arrives_at<=self.world.tick:
            packet,frame,cue,phase,question = self.packets.popleft()
            receiver,sender = alive.get(packet.receiver),alive.get(packet.sender)
            if receiver is None or sender is None or phase!=self.phase():
                self.counts["packet_expired"] += 1
                continue
            self.counts["packets_delivered"] += 1
            dimension = CONDITIONS.index(frame.condition)
            if frame.act=="question":
                response,certainty = receiver.lifetime.best()
                if certainty>.65 and response[dimension] and receiver.lifetime.phase==phase:
                    self.send(receiver,sender,"answer",response[dimension],dimension,reply_to=question)
            else:
                decoded,_ = receiver.communication.respond(0,frame.symbol,(0.,0.),receiver.social_rng,.13)
                sign = 1 if decoded else -1
                belief = receiver.lifetime.beliefs
                prior = means(belief.weights)
                old_values = belief.utilities(belief.weights,receiver.energy)
                # Retain the unassisted posterior for independent later validation.
                unassisted = belief.weights
                belief.weights = updated(belief.weights,tuple(.66 if h[dimension]==sign else .5
                                                              if not h[dimension] else .34 for h in HYPOTHESES))
                receiver.lifetime.feedback = (packet.sender,cue,frame.symbol,decoded,sign,unassisted,
                                               self.world.tick+180,phase,dimension)
                receiver.lifetime.episodes.append((self.world.tick,"social",packet.sender,dimension,sign))
                self.counts["social_plan_revisions"] += int(max(range(4),key=old_values.__getitem__)
                    != max(range(4),key=belief.utilities(belief.weights,receiver.energy).__getitem__))
                self.log("social_evidence",id=receiver.id,sender=sender.id,sign=sign,
                         before=prior,after=means(belief.weights),frame=asdict(frame),question_id=question)

    def inquiry(self, body, visible):
        life = body.lifetime
        phase = self.phase()
        budget = (phase,"questions")
        if self.frozen or self.phase_counts[budget]>=QUESTION_LIMIT or life.cooldown>self.world.tick or body.energy<43:
            return None
        station = body.position in self.world.stations
        at_library = self.arm=="cognitive" and body.position==self.world.fruit
        if not station and not at_library:
            return None
        belief = life.beliefs
        energy = body.energy
        utilities = belief.utilities(belief.weights,energy)
        best = max(utilities)
        spread = variance(belief.weights)
        gains = [belief.value(belief.physical_channels(i,energy),energy,best,spread)[2] for i in range(4)]
        self.counts["inquiry_ops"] += MODEL_OPS
        body.energy -= OP_ENERGY*MODEL_OPS
        scores = [u-best+4.*TIME_DISCOUNT**9*g for u,g in zip(utilities,gains)]
        index = max(range(4),key=scores.__getitem__)
        kind,topic,peer = None,None,None
        if at_library and spread>2.:
            topics = {"experiment":.18*spread,"geography":1.3*abs(self.world.climate()-.5)}
            unseen = [k for k in topics if life.confidence(f"query:{k}",self.world.tick)<.30 and topics[k]>.45]
            if unseen:
                kind,topic = "library",max(unseen,key=topics.__getitem__)
        elif station and scores[index]>.7:
            kind = "trial"
            if self.arm=="cognitive" and phase>=2 and spread>2. and (self.world.tick+body.id)%3==0:
                peer = next((o for o in self.organisms if o.id!=body.id and o.alive and
                             sum(abs(a-b) for a,b in zip(o.position,body.position))<=3),None)
                dimension = max(range(3),key=lambda i:1.-abs(sum(p*h[i] for p,h in zip(belief.weights,HYPOTHESES))))
                if peer and self.send(body,peer,"question",life.best()[0][dimension],dimension):
                    kind = "peer"
        if kind is None:
            return None
        self.phase_counts[budget] += 1
        self.counts[f"inquiry_{kind}"] += 1
        life.cooldown = self.world.tick+40
        return dict(channel=kind,topic=topic,peer=peer.id if peer else None,settings=OPTIONS[index],
                    hypothesis=life.best(),uncertainty=spread,trigger=dict(position=body.position,
                    tile=visible[body.position][0],climate=self.world.climate()),before=means(belief.weights),
                    predicted_information=gains[index],operations=MODEL_OPS,energy=OP_ENERGY*MODEL_OPS)

    def choose(self, body, observations, rng):
        proposed,destination = self.motor.choose(body,observations,rng)
        original = body.last_action
        visible = {p:(tile,food) for p,tile,food in observations}
        candidates = [(5,body.position,-.3)]
        food = visible[body.position][1]
        if food>1. and body.energy<94.:
            candidates.append((4,body.position,min(food,10.)*.32))
        for a,d in enumerate(DIRECTIONS):
            p = offset(body.position,d)
            tile,stock = visible.get(p,("water",0.))
            if tile!="water":
                adjacent = max(visible.get(offset(p,e),("",0.))[1] for e in DIRECTIONS)
                value = .14*min(18.,stock)+.035*min(18.,adjacent)+.20*(p not in body.memory)-4.*(tile=="hazard")
                if (self.arm=="cognitive" and tile=="store"
                        and body.lifetime.confidence("query:geography",self.world.tick)>.30):
                    value += .07
                candidates.append((a,p,value))
        if original==6:
            candidates.append((6,destination,.40 if body.energy>80. else -.6))
        code,pos,_ = max(candidates,key=lambda v:v[2]+.32*(v[0]==original)+rng.random()*.10)
        self.current_inquiry = self.inquiry(body,visible)
        if self.current_inquiry and self.current_inquiry["channel"]!="peer":
            code,pos = 5,body.position
        state = State(body.position,body.energy,(0.,0.),visible)
        _,features = inputs(state,code if code!=6 else 5)
        own = self.model.predict(features)[0]*10+body.lifetime.self_bias[code]
        body.energy -= self.model.cost*OP_ENERGY
        self.counts["world_model_ops"] += self.model.cost
        self.plan = (original,code,pos,own)
        body.last_action = code
        return ("move" if code<4 else "eat" if code==4 else "share" if code==6 else "rest"),pos

    def resolve_inquiry(self, body, lookup):
        life = body.lifetime
        phase = self.phase()
        evidence = None
        if body.alive and lookup["channel"]=="library":
            evidence = retrieve(Query(lookup["topic"],"foundation"),body.position,self.world.fruit,
                                self.arm=="cognitive")
            body.energy -= .45
            lookup["energy"] += .45
            if evidence:
                life.documents[lookup["topic"]] = evidence
                life.remember(f"query:{lookup['topic']}",evidence["relation"],self.world.tick,1.)
                self.counts["library_retrievals"] += 1
        elif body.alive and lookup["channel"]=="trial":
            choice = lookup["settings"]
            loss,stock = outcomes(self.rule(),choice)
            available = self.world.food.get(body.position,0.)
            gained = min(available,stock,max(0.,100.-body.energy))
            self.world.food[body.position] -= gained
            body.energy += gained-loss-.55
            body.acquired += gained
            lookup["energy"] += loss+.55
            plausibility = life.beliefs.observe(choice,loss,stock)
            evidence = dict(loss=loss,stock_reading=stock,food_transferred=gained,plausibility=plausibility)
            life.phase = phase
            hypothesis,confidence = life.best()
            if confidence>.70:
                label = f"station:{phase}:{hypothesis}"
                if label not in life.semantic:
                    self.counts["new_associations"] += 1
                    self.log("association",id=body.id,concept=label,hypothesis=hypothesis,confidence=confidence)
                life.remember(label,hypothesis,self.world.tick,confidence)
            life.episodes.append((self.world.tick,"trial",choice,loss,stock,plausibility))
            self.counts["trials"] += 1
            self.counts["belief_anomalies"] += int(plausibility<.12)
            if life.feedback:
                sender,cue,symbol,decoded,sign,weights,expires,source_phase,dimension = life.feedback
                if expires>=self.world.tick and source_phase==phase:
                    check = Beliefs()
                    check.weights = weights
                    check.observe(choice,loss,stock)
                    estimate = sum(p*h[dimension] for p,h in zip(check.weights,HYPOTHESES))
                    if abs(estimate)>.8:
                        correct = int(estimate*sign>0.)
                        self.counts["social_validated"] += 1
                        self.counts["social_correct"] += correct
                        body.communication.learn((body.communication.receive[symbol],decoded),1. if correct else -1.)
                        source = next((o for o in self.organisms if o.id==sender),None)
                        if source is not None:
                            source.communication.learn((source.communication.send[cue],symbol),1. if correct else -1.)
                        self.log("social_validation",id=body.id,sender=sender,correct=correct)
                        life.feedback = None
        elif lookup["channel"]=="peer":
            lookup["energy"] += .18
        body.check_death()
        question_id = f"{body.id}:{self.world.tick}"
        self.log("inquiry",question_id=question_id,id=body.id,parent=body.parent_id,generation=body.generation,
                 **lookup,evidence=evidence,after=means(life.beliefs.weights),action=self.plan[1])
        body.pending_question = question_id if body.alive else None

    def step(self):
        self.world.advance()
        self.deliver()
        for body in self.organisms:
            if not body.alive:
                continue
            body.local_contacts = [(o.id,o.position,o.energy) for o in self.organisms if o is not body and o.alive
                                   and max(abs(a-b) for a,b in zip(o.position,body.position))<=2][:8]
            body.social.advance(body.local_contacts,self.world.tick)
            energy,health,food,before = body.energy,body.health,body.acquired,body.brain_cost
            prior_question = getattr(body,"pending_question",None)
            body.pending_question = None
            self.current_inquiry = None
            body.step(self.world,self.rng,self)
            proposed,selected,destination,prediction = self.plan
            ordinary = body.energy-energy
            if self.current_inquiry:
                ordinary += self.current_inquiry["energy"]  # Inquiry planning is charged separately.
            error = abs(ordinary-prediction)
            self.counts["self_error_sum"] += error
            self.counts["self_count"] += 1
            self.counts["action_override"] += int(proposed!=selected)
            if not self.frozen:
                body.lifetime.self_bias[selected] = clip(body.lifetime.self_bias[selected]+.04*(ordinary-prediction),-4.,4.)
            body.brain.memory.observe(body.position,self.world.food.get(body.position,0.),body.age,body.brain.genetic["decay"])
            Brain.learn(body.brain,clip(ordinary/10-(health-body.health)/48,-1,1),self.world.food.get(body.position,0.))
            external = 0.
            external_key = 2*int(destination in self.world.store)+int(self.world.climate()<.12)
            external_prediction = body.lifetime.external_bias[external_key]
            if body.alive and self.phase()==4 and body.position in self.world.store and self.world.climate()<.12:
                external = .7
                body.energy -= external
                body.check_death()
                self.counts["external_pulses"] += 1
                self.counts["external_loss"] += external
            if body.alive or external:
                self.counts["external_error_sum"] += abs(external-external_prediction)
                self.counts["external_predictions"] += 1
                if not self.frozen:
                    body.lifetime.external_bias[external_key] += .07*(external-external_prediction)
            if self.current_inquiry:
                self.resolve_inquiry(body,self.current_inquiry)
            if prior_question:
                self.log("followup",question_id=prior_question,id=body.id,proposed=proposed,selected=selected,
                         destination=destination,actual=body.position,predicted_energy_delta=prediction,
                         observed_energy_delta=ordinary,predicted_external_loss=external_prediction,
                         external_loss=external,energy=body.energy,alive=body.alive)
            self.counts["food"] += body.acquired-food
            self.counts["neural_energy"] += body.brain_cost-before
            self.counts["ticks_alive"] += 1
            if not body.alive:
                self.counts["deaths"] += 1
                self.log("death",id=body.id,generation=body.generation,cause=body.death_cause)
        self.organisms = [o for o in self.organisms if o.alive]
        if not self.frozen:
            candidates = self.organisms[:]
            self.rng.shuffle(candidates)
            for parent in candidates:
                if len(self.organisms)>=CAP:
                    break
                if parent.mature and parent.energy>=87. and parent.age-parent.last_birth_age>=140:
                    parent.energy -= CHILD_ENERGY
                    parent.last_birth_age = parent.age
                    parent.offspring += 1
                    self.organisms.append(self.born(parent.position,parent))
        self.population_peak = max(self.population_peak,len(self.organisms))

    def metrics(self):
        return dict(region=self.region,arm=self.arm,tick=self.world.tick,phase=PHASES[self.phase()],
                    alive=len(self.organisms),births=self.births,max_generation=self.generation,
                    peak=self.population_peak,**self.counts)
