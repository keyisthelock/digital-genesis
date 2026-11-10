"""Fictional preindustrial settlement, local sensing, and CPU motor primitives."""

from collections import OrderedDict
from dataclasses import dataclass, field
import math
import random

BASE=100
WIDTH,HEIGHT=17,13
DIRS=((0,-1),(1,0),(0,1),(-1,0))
LIMITS={"neck":(-45,45),"torso":(-20,20),"left_arm":(-70,80),"right_arm":(-70,80),
        "left_hand":(0,65),"right_hand":(0,65),"left_leg":(-40,45),"right_leg":(-40,45),
        "left_foot":(-25,30),"right_foot":(-25,30)}
SHELTER={"house","workshop","school","market"}
WALKABLE={"road","meadow","bridge","house","workshop","school","market","well","field","wood"}
NAMES={"market":"Market","school":"Reading room","well":"Village well","workshop":"Workshop",
       "house":"Cottage","field":"Smallholding","wood":"Wood lot","river":"River","bridge":"Footbridge"}
BOOKS={"workshop":("A fitted hand tool is needed for the bench.", "tool"),
       "well":("A bucket from the well replenishes drinking water.", "water")}


def offset(p,d):
    return p[0]+d[0],p[1]+d[1]


def distance(a,b):
    return abs(a[0]-b[0])+abs(a[1]-b[1])


def clamp(value,lo=0.,hi=100.):
    return max(lo,min(hi,value))


@dataclass(frozen=True)
class Action:
    kind: str
    target: tuple | None = None
    direction: int | None = None
    peer: int | None = None
    topic: str | None = None


@dataclass
class Body:
    position: tuple
    facing: int = 1
    energy: float = 72.
    water: float = 68.
    fatigue: float = 22.
    temperature: float = 36.8
    health: float = 100.
    coins: int = 3
    provisions: int = 1
    holding: str | None = None
    alive: bool = True
    cause: str | None = None
    gait: int = 0
    joints: dict = field(default_factory=lambda:{k:0 for k in LIMITS})
    feedback: str = "arrival"

    def pose(self, changes):
        self.joints={joint:clamp(changes.get(joint,0),*limit) for joint,limit in LIMITS.items()}


@dataclass
class Resident:
    id: int
    name: str
    occupation: str
    body: Body
    home: tuple
    station: tuple
    memory: OrderedDict = field(default_factory=OrderedDict)

    def remember(self, cells):
        for p,cell in cells.items():
            self.memory[p]=(cell["tile"],cell["stock"])
            self.memory.move_to_end(p)
        while len(self.memory)>28:
            self.memory.popitem(last=False)


class Settlement:
    def __init__(self, seed):
        rng=random.Random(seed)
        self.tick=0
        self.variant=seed%3
        self.temperature_offset=rng.uniform(-1.4,1.4)
        self.shift=(seed//3)%2
        raw={(x,y):"meadow" for x in range(WIDTH) for y in range(HEIGHT)}
        for y in range(HEIGHT):
            raw[8,y]="river"
            raw[2,y]="road"
            raw[12,y]="road"
        for x in range(WIDTH):
            raw[x,6]="bridge" if x==8 else "road"
        raw[8,3]="bridge"
        sites={(2,5):"house",(3,7):"house",(11,8):"house",(4,6):"market",
               (6,5+self.shift):"well",(5,4):"school",(7,6):"workshop",
               (13,5):"field",(14,5):"field",(13,4):"field",(12,9):"well",
               (1,3):"wood",(6,3):"wood",(15,8):"wood",(14,9):"hazard"}
        raw.update(sites)
        for p in ((4,3),(4,4),(4,5),(10,3),(10,4),(10,5),(3,10),(4,10)):
            raw[p]="wall"
        # Mirror layouts across seeds. The transform is invisible to policies.
        def at(p):
            x,y=p
            return BASE+(WIDTH-1-x if self.variant==1 else x),BASE+(HEIGHT-1-y if self.variant==2 else y)
        self.tiles={at(p):tile for p,tile in raw.items()}
        self.sites={at(p):tile for p,tile in sites.items()}
        self.stock={p:(16.+rng.random()*4 if tile in ("market","field") else 38.)
                    for p,tile in self.sites.items() if tile in ("market","field","well")}
        self.tools={p:2 for p,tile in self.sites.items() if tile=="workshop"}
        self.spawn=at((3,6))
        self.residents=[]
        roles=(("Alder","grower",(2,5),(13,5)),("Bess","seller",(3,7),(4,6)),
               ("Cora","maker",(11,8),(7,6)),("Dale","reader",(2,5),(5,4)))
        for i,(name,job,home,site) in enumerate(roles,101):
            b=Body(at(site),coins=4,provisions=2,holding="hand tool" if job=="maker" else None)
            self.residents.append(Resident(i,name,job,b,at(home),at(site)))

    @property
    def daylight(self):
        return .5+.5*math.sin(math.tau*(self.tick+7)/48)

    @property
    def ambient(self):
        return 13+7*self.daylight + (2 if self.tick//96%2==0 else -4) + self.temperature_offset

    def local(self,body):
        p=body.position
        dx,dy=DIRS[body.facing]
        radius=3 if self.daylight>.20 else 2
        result={}
        for y in range(p[1]-radius,p[1]+radius+1):
            for x in range(p[0]-radius,p[0]+radius+1):
                q=(x,y)
                if q not in self.tiles or distance(p,q)>radius:
                    continue
                if distance(p,q)>1 and (x-p[0])*dx+(y-p[1])*dy<0:
                    continue
                steps=max(abs(x-p[0]),abs(y-p[1]))
                if any(self.tiles.get((round(p[0]+(x-p[0])*i/steps),
                                       round(p[1]+(y-p[1])*i/steps)))=="wall" for i in range(1,steps)):
                    continue
                tile=self.tiles[q]
                result[q]=dict(tile=tile,name=NAMES.get(tile,tile),distance=distance(p,q),
                               stock=round(self.stock.get(q,0.),4),tool=self.tools.get(q,0)>0)
        return result

    def nearby(self,body):
        return [r for r in self.residents if r.body is not body and r.body.alive and
                distance(r.body.position,body.position)<=2]

    def advance(self):
        self.tick+=1
        for p,stock in self.stock.items():
            tile=self.tiles[p]
            rate=.65 if tile=="well" else .19 if tile=="field" else .10
            self.stock[p]=min(42. if tile=="well" else 24.,stock+rate)

    def act(self,body,action,people=()):
        """Apply the same collision, reach and exertion rules to every person."""
        kind=action.kind
        target=action.target if action.target is not None else body.position
        tile=self.tiles.get(target,"wall")
        reachable=distance(body.position,target)<=1
        fatigue,effort,success=.20,.16,True
        touch=kind
        evidence=None
        if kind=="walk":
            effort,fatigue=.62,1.35
            if distance(body.position,target)!=1 or tile not in WALKABLE or target in people:
                touch,success="collision",False
            elif body.fatigue>=93 or body.water<=3:
                touch,success="exertion limit",False
            else:
                body.position=target
                body.facing=action.direction
                body.gait=1-body.gait
            stride=26 if body.gait else -26
            body.pose({"torso":4,"left_leg":stride,"right_leg":-stride,"left_foot":stride/2,
                       "right_foot":-stride/2,"left_arm":-stride*.55,"right_arm":stride*.55})
        elif kind=="turn":
            body.facing=action.direction
            body.pose({"neck":30,"torso":8})
        elif kind=="drink":
            amount=min(24.,100-body.water,self.stock.get(target,0.)) if reachable and tile=="well" else 0.
            body.water+=amount
            if amount:
                self.stock[target]-=amount
            success=amount>0
            body.pose({"right_arm":58,"right_hand":48,"neck":-10})
        elif kind=="eat":
            if body.provisions:
                body.provisions-=1
                body.energy+=17.
            elif reachable and tile=="field" and self.stock.get(target,0.)>=3.:
                self.stock[target]-=3.
                body.energy+=11.
            else:
                success=False
            body.pose({"right_arm":65,"right_hand":55})
        elif kind=="trade":
            success=reachable and tile=="market" and body.coins>0 and self.stock.get(target,0.)>=4.
            if success:
                body.coins-=1
                body.provisions+=1
                self.stock[target]-=4.
            body.pose({"right_arm":42,"right_hand":35})
        elif kind=="grasp":
            success=reachable and body.holding is None and self.tools.get(target,0)>0
            if success:
                body.holding="hand tool"
                self.tools[target]-=1
            body.pose({"right_arm":52,"right_hand":61})
        elif kind=="work":
            effort,fatigue=1.25,4.8
            success=(reachable and body.water>18. and body.fatigue<78. and
                     (tile=="field" and self.daylight>.18 or
                      tile=="workshop" and body.holding=="hand tool" and self.daylight>.28))
            if success:
                body.coins+=1
                if tile=="field":
                    self.stock[target]=min(24.,self.stock[target]+2.)
            body.pose({"left_arm":43,"right_arm":55,"right_hand":61,"torso":12})
        elif kind in ("inspect","read"):
            success=reachable and (kind=="inspect" or tile=="school" and self.daylight>.16)
            if success:
                evidence=BOOKS.get(action.topic) if kind=="read" else (tile, self.tools.get(target,0), self.stock.get(target,0.))
            body.pose({"neck":-20,"right_arm":36,"right_hand":35})
        elif kind=="rest":
            fatigue=-8. if self.tiles[body.position] in SHELTER else -4.
            effort=.05
            body.pose({"torso":-12,"left_leg":28,"right_leg":28})
        elif kind in ("ask","report","cooperate"):
            effort=.24
            body.pose({"neck":12,"left_arm":20,"right_arm":35,"right_hand":20})
        else:
            raise ValueError(kind)
        body.feedback=touch if success else touch+" failed"
        self.metabolize(body,effort,fatigue)
        return dict(success=bool(success),touch=body.feedback,evidence=evidence)

    def metabolize(self,body,effort,fatigue):
        sheltered=self.tiles[body.position] in SHELTER
        ideal=36.8 if sheltered else 34.5+.10*self.ambient
        body.temperature+=.11*(ideal-body.temperature)+.05*effort
        body.energy=clamp(body.energy-.26-effort-.13*(body.temperature<36.))
        body.water=clamp(body.water-.34-.34*effort)
        body.fatigue=clamp(body.fatigue+fatigue+.2*(body.water<22.))
        harm=.9*(body.water<=5)+.9*(body.energy<=4)+.35*(body.temperature<35.7)
        body.health=clamp(body.health-harm+(.17 if sheltered and body.fatigue<38. and harm==0 else 0.))
        if body.health<=0 or body.energy<=0 or body.water<=0:
            body.alive=False
            body.cause="dehydration" if body.water<=0 else "energy depletion" if body.energy<=0 else "injury/exposure"

    def resident_step(self,resident,occupied):
        b=resident.body
        if not b.alive:
            return
        visible=self.local(b)
        resident.remember(visible)
        wells=[p for p,(tile,_) in resident.memory.items() if tile=="well"]
        if b.water<43 and wells:
            goal=min(wells,key=lambda p:distance(p,b.position))
            action=Action("drink",goal) if distance(goal,b.position)<=1 else None
        elif b.energy<64 and b.provisions:
            goal=b.position
            action=Action("eat")
        else:
            goal=resident.home if self.daylight<.21 or b.fatigue>63 else resident.station
            action=Action("rest") if distance(goal,b.position)<=1 else None
            if action and goal==resident.station and resident.occupation in ("grower","maker") and b.fatigue<60:
                action=Action("work",goal)
        if action is None:
            ways=[(distance(p,goal),i,p) for i,d in enumerate(DIRS)
                  if (p:=offset(b.position,d)) in visible and visible[p]["tile"] in WALKABLE and p not in occupied]
            if ways and min(ways)[0]<distance(b.position,goal):
                _,i,p=min(ways)
                action=Action("walk",p,i)
            else:
                action=Action("rest")
        self.act(b,action,occupied)
