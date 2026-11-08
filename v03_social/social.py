"""Bounded numerical relationships and local loss observations; no emotion claims."""
from collections import OrderedDict,deque
import math

class SocialMemory:
    def __init__(self):
        self.people=OrderedDict();self.groups=OrderedDict();self.loss=0.;self.isolation=0.
        self.events=deque(maxlen=8);self.signal_history=deque(maxlen=32)
        self.encounters=self.formed=self.benefits=self.harms=0
        self.stable=self.group_samples=0;self.previous_group=()
    def bond(self,identity): return self.people.get(identity,dict(bond=0))['bond']
    def encounter(self,identity,tick,outcome=0,position=None):
        p=self.people.get(identity,dict(bond=0.,seen=0,last=tick,given=0.,received=0.))
        before=p['bond'];p['seen']+=1;p['last']=tick
        p['bond']=max(-1,min(1,p['bond']+.004+outcome))
        if position is not None:p['position']=position
        self.formed+=before<.15<=p['bond'];self.encounters+=1
        self.benefits+=outcome>0;self.harms+=outcome<0
        self.people[identity]=p;self.people.move_to_end(identity)
        while len(self.people)>32:self.people.popitem(last=False)
    def advance(self,contacts,tick):
        self.loss*=.985
        nearby={c[0] for c in contacts}
        for identity,position,_ in contacts:self.encounter(identity,tick,position=position)
        for identity,p in list(self.people.items()):
            p['bond']*=.999
            if tick-p['last']>600:del self.people[identity]
        familiar={i for i,p in self.people.items() if p['bond']>=.15}
        self.isolation=len(familiar-nearby)/max(1,len(familiar))
        group=tuple(sorted(familiar & nearby)[:4])
        if group:
            self.stable+=bool(set(group)&set(self.previous_group));self.group_samples+=1
            self.groups[group]=self.groups.get(group,0)+1;self.groups.move_to_end(group)
            while len(self.groups)>8:self.groups.popitem(last=False)
        self.previous_group=group
    def observe_death(self,identity,tick,position):
        strength=self.bond(identity)
        if strength<.15:return False
        self.loss=min(1,self.loss+strength)
        self.events.append(dict(identity=identity,tick=tick,position=position,bond=strength))
        return True
    def signals(self,contacts,position,rng,shuffle=False):
        contacts=contacts[:8]
        ids=[c[0] for c in contacts]
        if shuffle:rng.shuffle(ids)
        ranked=[(self.bond(i),c) for i,c in zip(ids,contacts)]
        if ranked:
            bond,c=max(ranked,key=lambda p:p[0]);dx=(c[1][0]-position[0])/2;dy=(c[1][1]-position[1])/2
            need=1-c[2]/100
        else:
            known=[p for p in self.people.values() if p['bond']>=.15 and 'position' in p]
            if known:
                p=max(known,key=lambda p:p['bond']);bond=p['bond'];need=0.
                dx=max(-1,min(1,(p['position'][0]-position[0])/4));dy=max(-1,min(1,(p['position'][1]-position[1])/4))
            else:bond=dx=dy=need=0.
        values=[dx,dy,bond,need,min(1,len(contacts)/8),self.isolation,self.loss,
            min(1,len(self.groups)/8),float(any(v>=.15 for v,_ in ranked)),min(1,self.encounters/100)]
        if shuffle and self.signal_history:
            past=rng.choice(list(self.signal_history))
            values[5:8]=past[5:8]
        self.signal_history.append(values[:])
        return values
