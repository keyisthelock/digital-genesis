"""Local transition model and a bounded lookahead search."""

import math
import random
from dataclasses import dataclass

DIRECTIONS=((0,-1),(1,0),(0,1),(-1,0))
NEAR=((0,0),*DIRECTIONS)
EAT,REST,FRUIT=4,5,7
INPUTS=14
OUTPUTS=7
HIDDEN=10


def offset(position, delta):
    return position[0]+delta[0],position[1]+delta[1]


def legal(position, local):
    moves=[i for i,d in enumerate(DIRECTIONS)
           if local.get(offset(position,d),('water',0))[0]!='water']
    if local.get(position,('',0))[1]>1:
        moves.append(EAT)
    return moves+[REST]


@dataclass
class State:
    position: tuple
    energy: float
    exposures: tuple
    local: dict


def inputs(state, action):
    p=offset(state.position,DIRECTIONS[action]) if action<4 else state.position
    known=[state.local.get(offset(p,d),('unknown',0)) for d in NEAR]
    stock=[food/30 for _,food in known]
    x=stock+[float(known[0][0]=='hazard'),float(known[0][0]=='unknown'),
             min(1,max(0,(100-state.energy)/10)),*state.exposures,
             float(action<4),float(action==EAT),float(action==REST),float(action==FRUIT)]
    return p,x


def persistence(x):
    """Approximate visible physics, without fitting any parameters."""
    stock=x[:5]
    gain=min(stock[0]*30,10,x[7]*10) if x[11] else 0.
    change=(gain-.18-.32*x[10]-.20*x[13])/10
    return [change,x[5],max(0,stock[0]-min(10,stock[0]*30)*x[11]/30),*stock[1:]]


class TransitionModel:
    """One shared nonlinear hidden layer learns residuals over persistence."""
    cost=(INPUTS+1)*HIDDEN+(HIDDEN+1)*OUTPUTS

    def __init__(self, seed):
        rng=random.Random(seed)
        self.hidden=[[rng.uniform(-.15,.15) for _ in range(INPUTS+1)] for _ in range(HIDDEN)]
        self.output=[[0.]*(HIDDEN+1) for _ in range(OUTPUTS)]

    def forward(self,x):
        z=[math.tanh(sum(a*b for a,b in zip(row,x))+row[-1]) for row in self.hidden]
        guess=[p+sum(a*b for a,b in zip(row,z))+row[-1]
               for p,row in zip(persistence(x),self.output)]
        return z,guess

    def predict(self,x):
        y=self.forward(x)[1]
        return [max(-1.,min(1.,y[0])),max(0.,min(2.,y[1])),
                *(max(0.,min(1.,value)) for value in y[2:])]

    def fit(self, examples, seed, epochs=12):
        rng=random.Random(seed)
        order=list(range(len(examples)))
        for epoch in range(epochs):
            rng.shuffle(order)
            rate=.024/(1+.08*epoch)
            for i in order:
                self.update(*examples[i],rate=rate)

    def update(self,x,target,mask,rate=.024):
        hidden,output=self.forward(x)
        error=[(actual-guess)*valid for actual,guess,valid in zip(target,output,mask)]
        gradient=[sum(row[j]*e for row,e in zip(self.output,error))*(1-z*z)
                  for j,z in enumerate(hidden)]
        for row,e in zip(self.output,error):
            for j,z in enumerate(hidden):
                row[j]+=rate*e*z
            row[-1]+=rate*e
        for row,e in zip(self.hidden,gradient):
            for j,v in enumerate(x):
                row[j]+=rate*e*v
            row[-1]+=rate*e


def imagined(state, action, predict):
    p,x=inputs(state,action)
    y=predict(x)
    patch=state.local.copy()
    for d,value in zip(NEAR,y[2:]):
        q=offset(p,d)
        if q in patch and patch[q][1]>0:
            patch[q]=(patch[q][0],30*value)
    successor=State(p,min(100,state.energy+10*y[0]),(float(patch[p][0]=='hazard'),state.exposures[0]),patch)
    return successor,10*y[0],12*y[1]


def choose(state, predict, horizon, policy_action, visits, action_cost=0., bonus=None, width=6):
    """Beam search over observed traversable cells. Unknown space is not filled in."""
    beam=[(0.,state,None,frozenset((state.position,)))]
    evaluations=0
    for depth in range(horizon):
        candidates=[]
        for score,current,first,seen in beam:
            for action in legal(current.position,current.local):
                nxt,gain,damage=imagined(current,action,predict)
                evaluations+=1
                first_action=action if first is None else first
                novelty=0.
                if nxt.position not in seen:
                    novelty=.64/(1+visits.get(nxt.position,0))
                bias=.035 if depth==0 and action==policy_action else 0.
                progress=bonus.get(action,0.) if bonus and depth==0 else 0.
                utility=gain-.45*damage+novelty+bias+progress
                nxt.energy-=action_cost
                if nxt.energy<=0:
                    utility-=30
                candidates.append((score+.94**depth*utility,nxt,first_action,seen|{nxt.position}))
        candidates.sort(key=lambda item:item[0],reverse=True)
        beam=candidates[:width]
    return beam[0][2],evaluations
