"""Genesis 1.0.1. Local signals on the existing reproductive ecosystem."""

import csv
import json
import random
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

PREVIOUS = Path(__file__).resolve().parents[1] / 'v03_social'
sys.path.insert(0, str(PREVIOUS))

from communication import SILENCE, SYMBOLS, broadcast
from communication_population import CommunicationPopulation

CHANNELS = ('intact', 'disabled', 'shuffled', 'isolated', 'random_teacher', 'retain')
RANGE = 3
SEND_COST = .035
LATENCY = 2
GATE_COST = .08
EPISODE_BUDGET = 6
OBSERVATION_LIMIT = 24
ARMS = ('resident', 'foster')


def distance(a, b):
    return sum(abs(x-y) for x, y in zip(a, b))


def terrain(path, seed, habitat='basin'):
    """Compact experimental terrains. The evaluation habitats alter resource geometry."""
    rng = random.Random(seed)
    width, height = (13, 11) if habitat=='basin' else (19, 15)
    fruit = (1, 1)
    tiles, food = [], []
    for y in range(height):
        for x in range(width):
            pos = x, y
            border = x in (0, width-1) or y in (0, height-1)
            barrier = habitat == 'causeway' and x == 9 and y not in (3, 7, 11)
            if border or barrier:
                kind = 'water'
            elif pos == fruit:
                kind = 'fruit'
            elif rng.random() < (.30 if habitat == 'islands' and (x+y)%3 else .58):
                kind = 'tree'
                food.append([x, y, rng.uniform(12, 27)])
            else:
                kind = 'land'
            tiles.append([x,y,kind])
    path.write_text(json.dumps(dict(width=width,height=height,fruit=fruit,tiles=tiles,food=food)),
                    encoding='utf-8')
    return path


class Ecosystem(CommunicationPopulation):
    """Use real world stock for two-latch food opportunities beside moving organisms."""

    def __init__(self, *, channel='intact', plastic=True, send_cost=SEND_COST, radius=RANGE,
                 observe=True, **kwargs):
        if channel not in CHANNELS or send_cost < 0 or radius < 0:
            raise ValueError('invalid channel, cost or range')
        self.channel, self.plastic, self.observe = channel, plastic, observe
        self.send_cost, self.radius = send_cost, radius
        self.origin, self.ancestry_roots = {}, {}
        self.genesis_counts = Counter()
        self.phase_counts = defaultdict(Counter)
        self.signal_counts = Counter()
        self.observed = Counter()
        self.pending = []
        self.receipts = []
        self.history = deque(maxlen=96)
        self.phase = 'establish'
        self.totals_by_origin = Counter()
        self.removed = self.introduced = 0
        super().__init__(**kwargs)
        self.scheduler = random.Random(self.seed_value*101 + 17)
        self.cues = random.Random(self.seed_value*103 + 19)
        self.noise = random.Random(self.seed_value*107 + 23)
        self.interactions = (self.output/'interactions.csv').open('w', newline='', encoding='utf-8')
        self.events_csv = csv.writer(self.interactions)
        self.events_csv.writerow(['tick','phase','scout','receiver','scout_origin','receiver_origin',
            'unrelated','marker','symbol_sent','symbol_received','choice','outcome','food','observer',
            'sent_tick','delivery_tick','feedback_due_tick'])
        self.population_log = (self.output/'population.csv').open('w', newline='', encoding='utf-8')
        self.population_csv = csv.writer(self.population_log)
        self.population_csv.writerow(['tick','phase','residents','fosters','births','natural_deaths','removed',
                                      'message_energy','neural_operations'])
        self.ancestry_log = (self.output/'genesis_ancestry.jsonl').open('w', encoding='utf-8')
        for body in self.organisms:
            self.note_ancestry(body, 'founder')

    def birth(self, parent=None):
        body = super().birth(parent)
        self.origin[body.id] = 'resident'
        self.ancestry_roots[body.id] = {body.id}
        self.prepare(body)
        return body

    def child(self, parents):
        body, sources, scalars = super().child(parents)
        self.origin[body.id] = self.origin[parents[0].id]
        self.ancestry_roots[body.id] = set().union(*(self.ancestry_roots[p.id] for p in parents))
        self.prepare(body)
        if hasattr(self, 'ancestry_log') and not getattr(self, 'fostering', False):
            self.note_ancestry(body, 'birth')
            self.totals_by_origin[self.phase,self.origin[body.id],'births'] += 1
        return body,sources,scalars

    def prepare(self, body):
        body.signal_rng = random.Random(self.seed_value*1879+body.id)

    def note_ancestry(self, body, event):
        record = dict(tick=self.world.tick, event=event, id=body.id, origin=self.origin[body.id],
                      generation=body.generation, roots=sorted(self.ancestry_roots[body.id]),
                      **body.reproductive_record)
        record['communication_genome'] = body.signal.genome
        self.ancestry_log.write(json.dumps(record)+'\n')

    def sense(self):
        grid = super().sense()
        # IDs and locations are observable. The legacy energy feature receives
        # the same neutral placeholder for every neighbour.
        for body in self.organisms:
            body.local_contacts = [(identity,position,65.) for identity,position,_ in body.local_contacts
                if self.phase=='establish' or self.channel!='isolated'
                or self.origin[identity]==self.origin[body.id]]
        return grid

    def introduce_fosters(self, families=4, siblings=3):
        if len(self.organisms)+families*siblings > self.max_population:
            raise ValueError('foster introduction exceeds population cap')
        self.fostering = True
        # External donor energy pays for the incoming cohort. Donors never
        # enter the world and have never encountered the residents.
        for _ in range(families):
            donor = self.birth()
            donor.energy = self.reproduction_cost*siblings
            self.origin[donor.id] = 'external'
            self.note_ancestry(donor, 'external_donor')
            for _ in range(siblings):
                body,_,_ = self.child((donor,))
                donor.energy -= self.reproduction_cost
                self.origin[body.id] = 'foster'
                body.position = self.world.rng.choice([p for p in self.world.land if
                    abs(p[0]-self.world.width//2)+abs(p[1]-self.world.height//2)<=4])
                self.organisms.append(body)
                self.note_ancestry(body, 'cross_foster')
                self.max_generation = max(self.max_generation,body.generation)
                self.introduced += 1
                self.genesis_counts['imported_energy'] += body.energy
                self.genesis_counts['external_parent_debit'] += self.reproduction_cost
        self.fostering = False
        self.phase = 'contact'

    def teacher_boundary(self):
        if self.channel != 'retain':
            kept=[]
            for body in self.organisms:
                if self.origin[body.id] == 'foster':
                    kept.append(body)
                else:
                    self.note_ancestry(body,'teacher_removal')
                    self.record(body)
                    self.archived_fitness += body.fitness
                    self.archived_food += body.acquired
                    self.genesis_counts['removed_energy'] += body.energy
                    self.removed += 1
            self.organisms=kept
        self.phase = 'after'

    def permitted(self, a, b):
        if self.phase == 'establish':
            return True
        return self.channel != 'disabled' and (
            self.channel != 'isolated' or self.origin[a.id] == self.origin[b.id])

    def gate(self, body):
        x,y=body.position
        local = (body.position, (x-1,y), (x+1,y), (x,y-1), (x,y+1))
        return next((p for p in local if self.world.food.get(p,0.)>=2.),None)

    def launch(self, living, occupied):
        candidates = list(living.values())
        self.scheduler.shuffle(candidates)
        launched=0
        for receiver in candidates:
            if receiver.id in occupied or receiver.energy <= GATE_COST:
                continue
            site=self.gate(receiver)
            if site is None:
                continue
            neighbours=[scout for scout in candidates if scout.id != receiver.id
                        and scout.id not in occupied and scout.energy > self.send_cost
                        and distance(scout.position,receiver.position)<=self.radius]
            if not neighbours:
                continue
            scout=self.scheduler.choice(neighbours)
            marker=self.cues.randrange(2)
            # A local instrument presents a marker to the scout alone.
            # The receiver's policy is never passed this value.
            token,decision=scout.signal.transmit(marker,scout.signal_rng,.15 if self.plastic else 0.)
            packet,fee=broadcast(scout,receiver,token,self.world.tick,
                                 distance_limit=self.radius,cost=self.send_cost,latency=LATENCY)
            if packet is None:
                continue
            self.genesis_counts['message_energy']+=fee
            self.ledger['living_energy_change']-=fee
            visible=self.permitted(scout,receiver)
            displayed=token
            clean=True
            if self.phase!='establish' and self.channel=='shuffled':
                displayed=self.noise.choice(self.history) if self.history else self.noise.randrange(SYMBOLS)
                clean=False
            elif self.phase!='establish' and self.channel=='random_teacher' and self.origin[scout.id]=='resident':
                displayed=self.noise.randrange(SYMBOLS)
                clean=False
            self.history.append(token)
            self.pending.append((packet,marker,decision,displayed,clean,visible,site,self.phase))
            occupied.update((scout.id,receiver.id))
            launched+=1
            if launched>=EPISODE_BUDGET:
                break

    def settle(self,living):
        tick=self.world.tick
        for due,body,decision,reward in self.receipts:
            assert due<=tick
            if body.id in living:
                body.signal.learn(decision,reward)
        self.receipts.clear()
        waiting=[]
        for packet,marker,send_decision,displayed,clean,visible,site,phase in self.pending:
            if packet.arrives_at>tick:
                waiting.append((packet,marker,send_decision,displayed,clean,visible,site,phase))
                continue
            scout,receiver=living.get(packet.sender),living.get(packet.receiver)
            if (scout is None or receiver is None or receiver.energy<=GATE_COST
                    or distance(receiver.position,site)>2 or self.world.food.get(site,0.)<2.):
                self.genesis_counts['expired']+=1
                continue
            delivered=visible and distance(scout.position,receiver.position)<=self.radius
            symbol=displayed if delivered else SILENCE
            before=receiver.energy
            receiver.energy-=GATE_COST
            route,decision=receiver.signal.respond(0,symbol,(0.,0.),receiver.signal_rng,.15 if self.plastic else 0.)
            success=route==marker
            amount=self.original_eat(site) if success else 0.
            retained=min(amount,100-receiver.energy)
            receiver.energy+=retained
            receiver.acquired+=amount
            self.ledger['food_retained']+=retained
            self.ledger['living_energy_change']+=receiver.energy-before
            self.genesis_counts['gate_energy']+=GATE_COST
            origins=self.origin[scout.id],self.origin[receiver.id]
            counts=self.phase_counts[phase,*origins]
            counts.update(attempts=1,correct=int(success),delivered=int(delivered))
            counts['food']+=amount
            unrelated=not (self.ancestry_roots[scout.id]&self.ancestry_roots[receiver.id])
            counts['unrelated_delivered']+=int(delivered and unrelated)
            counts['intergenerational_delivered']+=int(delivered and scout.generation!=receiver.generation)
            self.signal_counts[phase,scout.id,receiver.id,marker,symbol,route]+=1
            observer=None
            if self.plastic:
                reward=1. if success else -1.
                self.receipts.append((tick+1,receiver,decision,reward))
                if delivered and clean:
                    self.receipts.append((tick+1,scout,send_decision,reward))
                if success and delivered and self.observe:
                    observers=[o for o in living.values() if o.id not in (scout.id,receiver.id)
                        and (phase=='establish' or self.origin[o.id]=='foster')
                        and self.observed[o.id]<OBSERVATION_LIMIT
                        and distance(o.position,receiver.position)<=1
                        and distance(o.position,scout.position)<=self.radius and self.permitted(scout,o)]
                    if observers:
                        witness=self.scheduler.choice(observers)
                        # Only the public token and successful latch action are observed.
                        self.receipts.append((tick+1,witness,(witness.signal.receive[symbol],route),.6))
                        self.observed[witness.id]+=1
                        counts['observational_updates']+=1
                        observer=witness.id
            self.events_csv.writerow([tick,phase,scout.id,receiver.id,*origins,int(unrelated),marker,
                packet.symbol,symbol,route,int(success),amount,observer,packet.sent_at,
                tick if delivered else None,tick+1 if self.plastic else None])
        self.pending=waiting

    def step(self):
        before={o.id:o for o in self.organisms}
        done=super().step()
        living={o.id:o for o in self.organisms}
        for identity in before.keys()-living.keys():
            self.totals_by_origin[self.phase,self.origin[identity],'deaths']+=1
        if living:
            self.settle(living)
            busy={identity for packet,*_ in self.pending for identity in (packet.sender,packet.receiver)}
            self.launch(living,busy)
        if self.world.tick%20==0 or done:
            counts=Counter(self.origin[o.id] for o in self.organisms)
            self.population_csv.writerow([self.world.tick,self.phase,*[counts[k] for k in ARMS],
                self.total_births,self.total_deaths,self.removed,self.genesis_counts['message_energy'],
                self.totals['neural_ops']])
        return done

    def close(self):
        for stream in (self.interactions,self.population_log,self.ancestry_log):
            stream.close()
        super().close()
