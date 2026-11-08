"""Exact samples in biological tick order, never interpolated for analysis."""
from collections import deque,OrderedDict

CHARTS=(
    (('Population',('living',),'org'),('Births / deaths',('births','deaths'),'events'),('Mean / best living fitness',('fitness','best'),'score')),
    (('Mean living energy',('energy',),'energy'),('Food remaining',('food',),'units'),('Living / ever born',('survival',),'%')),
    (('Mean living brain complexity',('complexity',),'params'),('Cumulative prediction error',('mse',),'MSE'),('Energy sharing',('shares',),'events')))

class Telemetry:
    def __init__(self):
        self.history=deque(maxlen=240);self.parents=OrderedDict();self.family=OrderedDict();self.extinctions=0
        self.last={};self.last_tick=-1;self.last_living=None
    @staticmethod
    def read(sim):
        living=[o for o in sim.organisms if o.alive];n=len(living)
        brains=[o.brain for o in living if getattr(o,'brain',None) is not None]
        totals=getattr(sim,'totals',{});pred=totals.get('prediction_samples',0)
        births=getattr(sim,'total_births',None);deaths=getattr(sim,'total_deaths',None)
        ever=sim.size+births if sim.lifetime and births is not None else None
        return dict(living=n,births=births,deaths=deaths,food=sum(sim.world.food.values()),
            energy=sum(o.energy for o in living)/n if n else None,
            fitness=sum(o.fitness for o in living)/n if n else None,best=max((o.fitness for o in living),default=None),
            survival=100*n/ever if ever else None,
            complexity=sum(b.complexity for b in brains)/len(brains) if brains else None,
            mse=totals.get('prediction_squared_error',0)/pred if pred else None,
            shares=totals.get('shares',0) if getattr(sim,'social_on',False) else None,
            type_a=sum(getattr(o,'reproductive_type',None)=='A' for o in living),
            type_b=sum(getattr(o,'reproductive_type',None)=='B' for o in living))
    def sample(self,sim,force=False):
        n=sum(o.alive for o in sim.organisms);tick=sim.world.tick
        if self.last_living and n==0:self.extinctions+=1
        self.last_living=n
        for o in sim.organisms:
            if o.id not in self.parents:
                self.parents[o.id]=o.parent_id
                self.family[o.id]=tuple(getattr(o,'reproductive_record',{}).get(
                    'parent_ids', () if o.parent_id is None else (o.parent_id,)))
                while len(self.parents)>4096:self.parents.popitem(last=False)
                while len(self.family)>4096:self.family.popitem(last=False)
        changed=(self.last.get('living')!=n or self.last.get('births')!=getattr(sim,'total_births',None) or self.last.get('deaths')!=getattr(sim,'total_deaths',None))
        if force or changed or tick-self.last_tick>=5:
            self.last=self.read(sim);self.last['extinctions']=self.extinctions;self.last_tick=tick
            if self.history and self.history[-1][0]==tick:self.history[-1]=(tick,self.last)
            else:self.history.append((tick,self.last))
    def series(self,keys):return [[m[k] for _,m in self.history] for k in keys]
    def ancestry(self,o):
        ids=[o.id];p=o.parent_id
        while p is not None and p not in ids and len(ids)<7:
            ids.append(p)
            if p not in self.parents:return ' > '.join(map(str,ids))+' > ...'
            p=self.parents[p]
        return ' > '.join(map(str,ids))+(' > ...' if p is not None else '')

def value(v,places=1):return 'Not available' if v is None else f'{v:,.{places}f}'
