"""Small sparse recurrent modules. Genotypes and lifetime parameters never alias."""
import copy
import math
from collections import Counter, OrderedDict

GROUPS = ('survival', 'memory', 'exploration', 'social', 'coordination')
LAYOUTS = {8:(2,2,1,2,1),16:(4,3,3,4,2),32:(7,6,6,8,5),67:(15,12,12,18,10)}
INPUTS, ACTIONS, MAX_NODES, MAX_EDGES = 32, 8, 4, 12

def clip(x,lo=-2,hi=2): return max(lo,min(hi,x))

def module_gene(rng,group):
    return dict(group=group,n=2,edges=[[rng.randrange(INPUTS),rng.randrange(2),rng.uniform(-.4,.4)] for _ in range(6)],
        bias=[rng.uniform(-.2,.2) for _ in range(2)],recur=[rng.uniform(-.2,.2) for _ in range(2)],
        out=[[rng.uniform(-.3,.3) for _ in range(ACTIONS+1)] for _ in range(2)])

def new_genome(rng,count):
    if count not in LAYOUTS: raise ValueError('module count must be 8,16,32,67')
    return dict(lr=.012,decay=.008,social_gain=rng.uniform(.2,1),modules=[module_gene(rng,g) for g,k in zip(GROUPS,LAYOUTS[count]) for _ in range(k)])

def mutate(genome,rng,rate=.12):
    g=copy.deepcopy(genome)
    for name,lo,hi in (('lr',.0001,.04),('decay',.001,.05),('social_gain',0,2)):
        if rng.random()<rate: g[name]=clip(g[name]+rng.gauss(0,.01),lo,hi)
    for m in g['modules']:
        for edge in m['edges']:
            if rng.random()<rate: edge[2]=clip(edge[2]+rng.gauss(0,.08))
        for name in ('bias','recur'):
            for i in range(m['n']):
                if rng.random()<rate: m[name][i]=clip(m[name][i]+rng.gauss(0,.08))
        for row in m['out']:
            for i in range(len(row)):
                if rng.random()<rate: row[i]=clip(row[i]+rng.gauss(0,.08))
        if rng.random()<rate*.15:
            if rng.random()<.5 and len(m['edges'])<MAX_EDGES: m['edges'].append([rng.randrange(INPUTS),rng.randrange(m['n']),rng.uniform(-.2,.2)])
            elif len(m['edges'])>2: m['edges'].pop(rng.randrange(len(m['edges'])))
        if rng.random()<rate*.05:
            if rng.random()<.5 and m['n']<MAX_NODES:
                m['n']+=1; m['bias'].append(0.); m['recur'].append(0.)
                m['out'].append([rng.uniform(-.1,.1) for _ in range(ACTIONS+1)])
                if len(m['edges'])<MAX_EDGES: m['edges'].append([rng.randrange(INPUTS),m['n']-1,rng.uniform(-.2,.2)])
            elif m['n']>2:
                m['n']-=1; m['bias'].pop(); m['recur'].pop(); m['out'].pop()
                m['edges']=[e for e in m['edges'] if e[1]<m['n']]
    return g

class TinyModule:
    def __init__(self,gene):
        self.p=copy.deepcopy(gene); self.state=[0.]*gene['n']
    def forward(self,x):
        p=self.p
        z=[p['bias'][j]+p['recur'][j]*self.state[j] for j in range(p['n'])]
        for i,j,w in p['edges']: z[j]+=x[i]*w
        self.state=[math.tanh(v) for v in z]
        y=[sum(h*row[a] for h,row in zip(self.state,p['out'])) for a in range(ACTIONS+1)]
        return y,len(p['edges'])+p['n']*(ACTIONS+3)
    def learn(self,x,hidden,delta,lr):
        p=self.p
        gradients=[(1-h*h)*sum(row[a]*delta[a] for a in range(ACTIONS+1)) for h,row in zip(hidden,p['out'])]
        for row,h in zip(p['out'],hidden):
            for a in range(ACTIONS+1): row[a]=clip(row[a]+lr*delta[a]*h)
        for e in p['edges']: e[2]=clip(e[2]+lr*gradients[e[1]]*x[e[0]])
        for j in range(p['n']): p['bias'][j]=clip(p['bias'][j]+lr*gradients[j])

class CognitiveMemory:
    def __init__(self):
        self.long=OrderedDict(); self.working=OrderedDict(); self.error=0.; self.samples=0
    def estimate(self,p,tick,decay):
        if p not in self.long: return 0.,0.
        amount,confidence,last=self.long[p]
        c=confidence*math.exp(-decay*(tick-last))
        return amount*c,c
    def observe(self,p,amount,tick,decay):
        prediction,confidence=self.estimate(p,tick,decay)
        error=amount-prediction
        if confidence>.1: self.error+=abs(error)/30; self.samples+=1
        # Direct negative evidence replaces an obsolete food expectation immediately.
        old=self.long.get(p,(amount,0,tick))[0]
        estimate=amount if amount<=1 else old+.5*(amount-old)
        self.long[p]=(estimate,min(1,confidence+.3),tick); self.long.move_to_end(p)
        self.working[p]=(amount,tick); self.working.move_to_end(p)
        while len(self.long)>64: self.long.popitem(last=False)
        while len(self.working)>8: self.working.popitem(last=False)
        for q,(_,c,t) in list(self.long.items()):
            if c*math.exp(-decay*(tick-t))<.01: del self.long[q]
        return error/30

class Brain:
    def __init__(self,genome,social=True,learning=True):
        self.genetic=copy.deepcopy(genome)
        self.modules=[TinyModule(g) for g in genome['modules']]
        self.groups={g:[i for i,m in enumerate(genome['modules']) if m['group']==g] for g in GROUPS}
        self.social_enabled,self.learning=social,learning
        self.memory=CognitiveMemory(); self.use=Counter(); self.active=[]
        self.ops=self.decisions=self.updates=0; self.reward_baseline=0.
        self.squared_error=0.; self.predictions=0; self.last_error=0.; self.last_reward=0.
        self.first_error=self.last_error_sum=0.; self.first_n=self.last_n=0
        self.cache=None
    @property
    def complexity(self):
        return sum(len(m.p['edges'])+m.p['n']*(ACTIONS+3) for m in self.modules)
    def decide(self,x,valid,rng,tick,context):
        relevant='social' if self.social_enabled and context else 'memory' if self.memory.long else 'exploration'
        groups=('survival','coordination',relevant)
        self.active=[self.groups[g][(tick+self.decisions)%len(self.groups[g])] for g in groups]
        scores=[0.]*(ACTIONS+1); caches=[]; cost=0
        for i in self.active:
            values,ops=self.modules[i].forward(x);cost+=ops
            self.use[i]+=1;caches.append((i,self.modules[i].state[:]))
            scores=[a+b/3 for a,b in zip(scores,values)]
        assert cost<=3*(MAX_EDGES+MAX_NODES*(ACTIONS+3))
        exps={a:math.exp(clip(scores[a],-4,4)) for a in valid}; total=sum(exps.values())
        probs={a:v/total for a,v in exps.items()}
        action=rng.choices(list(probs),weights=list(probs.values()),k=1)[0]
        prediction=clip(.5+scores[-1],0,1)
        self.cache=(x,caches,probs,action,prediction)
        self.ops+=cost;self.decisions+=1
        return action,cost
    def learn(self,reward,food):
        if self.cache is None: return
        x,caches,probs,action,prediction=self.cache
        error=clip(food/30,0,1)-prediction
        self.squared_error+=error*error;self.predictions+=1
        if self.predictions<=50: self.first_error+=error*error;self.first_n+=1
        else: self.last_error_sum+=error*error;self.last_n+=1
        self.last_error=error;self.last_reward=reward
        advantage=clip(reward-self.reward_baseline,-1,1)
        self.reward_baseline=.95*self.reward_baseline+.05*reward
        if self.learning:
            delta=[advantage*((1 if a==action else 0)-probs.get(a,0)) for a in range(ACTIONS)]+[error]
            for i,h in caches: self.modules[i].learn(x,h,delta,self.genetic['lr']/3)
            self.updates+=1
        self.cache=None

class NeuralPolicy:
    """The organism supplies local observations; social context is bounded by simulation sensing."""
    def choose(self,o,observations,rng):
        b=o.brain; visible={p:(tile,food) for p,tile,food in observations}
        x=[0.]*INPUTS
        x[:6]=[o.energy/100,o.hunger,o.health/100,o.pain/12,o.growth,min(1,o.age/3000)]
        dirs=((0,-1),(1,0),(0,1),(-1,0)); valid=[5]
        for a,(dx,dy) in enumerate(dirs):
            p=o.position[0]+dx,o.position[1]+dy
            if p in visible and visible[p][0]!='water': valid.append(a)
            x[6+a]=sum(food/(30*(1+abs(q[0]-p[0])+abs(q[1]-p[1]))) for q,(_,food) in visible.items())/5
            x[10+a]=float(visible.get(p,('water',0))[0] in ('hazard','water'))
            x[14+a]=sum(b.memory.estimate(q,o.age,b.genetic['decay'])[0]/(30*(1+abs(q[0]-p[0])+abs(q[1]-p[1]))) for q in b.memory.long)/8
        tile,food=visible[o.position];x[18]=food/30
        if food>1: valid.append(4)
        if tile=='fruit' and not o.interacted: valid.append(7)
        x[19]=b.memory.estimate(o.position,o.age,b.genetic['decay'])[1]
        x[20]=b.last_error;x[21]=b.last_reward
        contacts=o.local_contacts
        signals=o.social.signals(contacts,o.position,o.social_rng,o.shuffled) if b.social_enabled else [0.]*10
        x[22:]=[v*b.genetic['social_gain'] for v in signals]
        o.share_target=None
        if b.social_enabled:
            adjacent=[c for c in contacts if abs(c[1][0]-o.position[0])+abs(c[1][1]-o.position[1])<=1]
            if adjacent and o.energy>10:
                # Target choice also uses numerical outcomes; no parent bonus.
                target=max(adjacent,key=lambda c:o.social.bond(c[0])+(100-c[2])/100)
                o.share_target=target[0];valid.append(6)
        a,ops=b.decide(x,sorted(valid),rng,o.age,bool(contacts or o.social.loss or o.social.isolation))
        o.last_action=a
        o.energy-=o.brain_energy_parameter*b.complexity+o.brain_energy_op*ops
        o.brain_cost+=o.brain_energy_parameter*b.complexity+o.brain_energy_op*ops
        if a<4:
            dx,dy=dirs[a];o.direction=a
            return 'move',(o.position[0]+dx,o.position[1]+dy)
        return ('eat','rest','share','investigate')[a-4],o.position
