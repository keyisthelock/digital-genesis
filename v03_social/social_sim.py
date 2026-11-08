"""Thin v0.3 extension of the preserved energy-funded reproduction lifecycle."""
import copy,json,random
from collections import Counter,deque
from cognition import Brain,NeuralPolicy,new_genome,mutate,clip
from social import SocialMemory
from evolution import Simulation
from organism import WeightedPolicy

TREATMENTS=('A_rule','B_neural_nonsocial','C_social_fixed','D_social_evolving')
def near(a,b,r=2):return max(abs(a[0]-b[0]),abs(a[1]-b[1]))<=r

class TrackedRule:
    def __init__(self):self.policy=WeightedPolicy()
    def choose(self,o,observations,rng):
        action,p=self.policy.choose(o,observations,rng)
        o.last_action={'eat':4,'rest':5,'investigate':7,'turn':8}.get(action,0)
        return action,p

class SocialSimulation(Simulation):
    def __init__(self,*args,treatment='D_social_evolving',modules=67,shuffled=False,
                 learning=True,brain_energy_parameter=.000002,brain_energy_op=.00001,
                 neural_pool=None,body_pool=None,freeze=False,cooperative=False,**kwargs):
        if treatment not in TREATMENTS:raise ValueError('invalid treatment')
        if brain_energy_parameter<0 or brain_energy_op<0:raise ValueError('negative brain cost')
        self.treatment,self.module_count,self.shuffled=treatment,modules,shuffled
        self.neural_learning=learning;self.seed_value=kwargs.get('seed',42)
        self.brain_energy_parameter,self.brain_energy_op=brain_energy_parameter,brain_energy_op
        self.neural_pool=neural_pool;self.body_pool=body_pool;self.freeze=freeze;self.cooperative=cooperative
        self.totals=Counter();self.module_use=Counter();self.pending_loss=[];self.late_pool=deque(maxlen=8)
        self.coverage=set()
        self.social_on=treatment in ('C_social_fixed','D_social_evolving')
        kwargs.update(lifetime=True,knowledge=False)
        if treatment=='C_social_fixed' or freeze:kwargs['mutation_rate']=0
        super().__init__(*args,**kwargs)
        self.policy=TrackedRule() if treatment=='A_rule' else NeuralPolicy()
        self.social_log=(self.output/'social_events.jsonl').open('w')
        self.cognitive_log=(self.output/'cognition.jsonl').open('w')
        self.world.share_energy=self.share
        if cooperative:
            original_eat=self.world.eat
            def cooperative_eat(p):
                # Identical physical gate for every treatment; no bonus energy.
                if sum(o.alive and near(o.position,p,1) for o in self.organisms)<2:
                    self.totals['blocked_food_access']+=1;return 0.
                return original_eat(p)
            self.world.eat=cooperative_eat
        self.sense()
    def birth(self,parent=None):
        o=super().birth(parent)
        if parent is None and self.body_pool:o.genome=copy.deepcopy(self.body_pool[(o.id-1)%len(self.body_pool)])
        rng=random.Random(self.seed_value*1000003+o.id*9176)
        o.brain=None
        if self.treatment!='A_rule':
            if parent:gene=parent.brain.genetic
            elif self.neural_pool:gene=self.neural_pool[(o.id-1)%len(self.neural_pool)]
            else:gene=new_genome(rng,self.module_count)
            if parent and not self.freeze and self.treatment!='C_social_fixed':gene=mutate(gene,rng)
            o.brain=Brain(gene,self.social_on,self.neural_learning)
        o.social=SocialMemory();o.local_contacts=[];o.shuffled=self.shuffled
        o.social_rng=random.Random(self.seed_value*919+o.id)
        o.last_action=5;o.share_target=None;o.brain_cost=0.
        o.brain_energy_parameter=self.brain_energy_parameter;o.brain_energy_op=self.brain_energy_op
        o.behavior=deque(maxlen=20)
        return o
    def sense(self):
        grid={}
        for o in self.organisms:
            if o.alive:grid.setdefault(o.position,[]).append(o)
        for o in self.organisms:
            contacts=[]
            x,y=o.position
            for yy in range(y-2,y+3):
                for xx in range(x-2,x+3):
                    contacts.extend((v.id,v.position,v.energy) for v in grid.get((xx,yy),()) if v.id!=o.id)
            o.local_contacts=sorted(contacts,key=lambda c:c[0])[:8]
        return grid
    def log_event(self,**event):
        payload=dict(tick=self.world.tick);payload.update(event)
        self.social_log.write(json.dumps(payload)+'\n')
    def share(self,donor):
        recipient=next((o for o in self.organisms if o.id==donor.share_target and o.alive),None)
        if recipient is None or not near(donor.position,recipient.position,1) or donor.energy<=10:return
        amount=min(3.,max(0,100-recipient.energy),donor.energy-10)
        if amount<=0:return
        donor.energy-=amount+.2;recipient.energy+=amount
        donor.social.encounter(recipient.id,self.world.tick,.02)
        recipient.social.encounter(donor.id,self.world.tick,.08*amount)
        donor.social.people[recipient.id]['given']+=amount
        recipient.social.people[donor.id]['received']+=amount
        self.totals['shares']+=1;self.totals['energy_transferred']+=amount;self.totals['sharing_loss']+=.2
        self.log_event(event='share',donor=donor.id,recipient=recipient.id,amount=amount,cost=amount+.2)
    def record(self,o):
        super().record(o)
        if hasattr(self,'cognitive_log'):
            b=o.brain
            self.cognitive_log.write(json.dumps(dict(id=o.id,parent=o.parent_id,age=o.age,alive=o.alive,
                offspring=o.offspring,bonds={str(i):p['bond'] for i,p in o.social.people.items()},
                loss=o.social.loss,isolation=o.social.isolation,brain_cost=o.brain_cost,
                modules=len(b.modules) if b else 0,ops=b.ops if b else 0,updates=b.updates if b else 0,
                neural_use=dict(b.use) if b else {}))+'\n')
    def step(self):
        self.sense()
        before=self.organisms[:]
        old={o.id:(o.energy,o.health,o.acquired,o.position,o.brain.ops if o.brain else 0,o.brain_cost) for o in before}
        for o in before:
            if self.social_on:o.social.advance(o.local_contacts,self.world.tick)
        finished=super().step()
        for o in before:
            energy,health,food,position,ops,cost=old[o.id]
            damage=max(0,health-o.health);gain=o.acquired-food
            row=dict(move=int(position!=o.position),share=int(o.last_action==6),hazard=int(damage>0),food=gain)
            self.coverage.add(o.position)
            o.behavior.append(row)
            self.totals['moves']+=row['move'];self.totals['hazard_ticks']+=row['hazard'];self.totals['damage']+=damage
            self.totals['action_'+str(o.last_action)]+=1
            self.totals['brain_energy']+=o.brain_cost-cost
            self.totals['isolation_sum']+=o.social.isolation;self.totals['isolation_samples']+=1
            if o.brain:
                b=o.brain
                b.memory.observe(o.position,self.world.food.get(o.position,0),o.age,b.genetic['decay'])
                b.learn(clip((o.energy-energy)/10-damage/48,-1,1),self.world.food.get(o.position,0))
                self.totals['prediction_squared_error']+=b.last_error*b.last_error
                self.totals['prediction_samples']+=1
                suffix='first' if b.predictions<=50 else 'later'
                self.totals['prediction_'+suffix+'_error']+=b.last_error*b.last_error
                self.totals['prediction_'+suffix+'_samples']+=1
                self.totals['learning_updates']+=int(b.learning)
                self.totals['complexity_sum']+=b.complexity
                self.totals['neural_ops']+=b.ops-ops
                self.totals['neural_decisions']+=1
                self.module_use.update(b.active)
            if self.social_on and gain>0:
                # Locally observed competition; no global attribution of intent.
                for other in before:
                    if other.id!=o.id and other.position==o.position and other.alive:
                        other.social.encounter(o.id,self.world.tick,-.02)
            if not o.alive:
                self.late_pool.append(dict(body=copy.deepcopy(o.genome),neural=copy.deepcopy(o.brain.genetic) if o.brain else None))
                for observer in self.organisms:
                    if observer.id!=o.id and self.social_on and near(observer.position,o.position):
                        self.totals['death_observations']+=1
                        if observer.social.observe_death(o.id,self.world.tick,o.position):
                            self.totals['bonded_loss_events']+=1
                            self.pending_loss.append(dict(observer=observer.id,deceased=o.id,tick=self.world.tick,
                                before=list(observer.behavior),after=[]))
                            self.log_event(event='bonded_loss',observer=observer.id,deceased=o.id,bond=observer.social.bond(o.id))
        alive={o.id:o for o in self.organisms}
        for event in self.pending_loss[:]:
            o=alive.get(event['observer'])
            if o and self.world.tick>event['tick']:event['after'].append(dict(o.behavior[-1]))
            if len(event['after'])>=20 or o is None:
                self.log_event(event='loss_behavior_window',**event,censored=len(event['after'])<20)
                self.pending_loss.remove(event)
        # At most one outstanding window per observer/death within the bounded population.
        if len(self.pending_loss)>self.max_population*8:
            for event in self.pending_loss[:-self.max_population*8]:self.log_event(event='loss_behavior_window',**event,censored=True,capacity_limited=True)
            self.pending_loss=self.pending_loss[-self.max_population*8:]
        return finished or not self.organisms
    def extra_metrics(self):
        neural=[o.brain for o in self.organisms if o.brain]
        # Lifetime totals for dead organisms are accumulated at final collection by the runner.
        social=[o.social for o in self.organisms]
        return dict(**self.totals,module_utilization=len(self.module_use)/self.module_count if self.treatment!='A_rule' else 0,
            mean_complexity=sum(b.complexity for b in neural)/max(1,len(neural)),
            living_strong_bonds=sum(p['bond']>=.15 for s in social for p in s.people.values()),
            living_reciprocal_bonds=sum(p['given']>0 and p['received']>0 for s in social for p in s.people.values()),
            group_stability=sum(s.stable for s in social)/max(1,sum(s.group_samples for s in social)))
    def inspect(self,o):
        b=o.brain
        if b is None:return ['Rule baseline',f'ID {o.id} | parent {o.parent_id}',f'Energy {o.energy:.1f} Age {o.age}']
        confidence=sum(b.memory.estimate(p,o.age,b.genetic['decay'])[1] for p in b.memory.long)/max(1,len(b.memory.long))
        return [f'ID {o.id} / lineage {o.generation}',f'Parent {o.parent_id} kids {o.offspring}',f'Energy {o.energy:.1f} age {o.age}',
            f'Modules {len(b.modules)} active {b.active}',f'Params+ops size {b.complexity}',f'Ops {b.ops} cost {o.brain_cost:.2f}',
            f'Memory {len(b.memory.long)} conf {confidence:.2f}',f'Prediction MSE {b.squared_error/max(1,b.predictions):.3f}',
            f'Learning updates {b.updates}',f'Bonds {sum(p["bond"]>=.15 for p in o.social.people.values())}',
            f'Familiar {list(o.social.people)[-4:]}',f'Isolation {o.social.isolation:.2f}',f'Loss {o.social.loss:.2f}',
            f'Recent deaths {len(o.social.events)}','Top bonds:']+[f' {i}: {p["bond"]:.2f}' for i,p in sorted(o.social.people.items(),key=lambda z:-z[1]['bond'])[:3]]
    def close(self):
        if hasattr(self,'social_log') and not self.social_log.closed:
            for event in self.pending_loss:self.log_event(event='loss_behavior_window',**event,censored=True)
            self.social_log.close();self.cognitive_log.close()
        super().close()
