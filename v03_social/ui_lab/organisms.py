import math
from copy import deepcopy
from collections import OrderedDict,deque
import pygame as pg
from .theme import CYAN,AMBER,VIOLET

class Organics:
    def __init__(self):
        self.cache=OrderedDict();self.motion={};self.flashes={};self.effects=deque(maxlen=96)
        self.links=deque(maxlen=32)
        self.events=deque(maxlen=240)
        self.deceased=OrderedDict()
    def observe(self,before,sim,seconds):
        previous={o.id:(o,p,health,given) for o,p,health,given in before}
        current={o.id:o for o in sim.organisms if o.alive}
        for identity,(o,p,health,given) in previous.items():
            self.motion[identity]=(p,o.position,seconds)
            if o.health<health:self.flashes[identity]=seconds+.5
            if not o.alive:
                self.effects.append(('death',o.position,seconds,identity))
                self.events.append((sim.world.tick,identity,'death: '+str(o.death_cause)))
                self.deceased[identity]=(sim.world.tick,deepcopy(o))
                if len(self.deceased)>24:self.deceased.popitem(last=False)
            social=getattr(o,'social',None)
            if social:
                for partner,record in social.people.items():
                    transferred=record['given']-given.get(partner,0)
                    if transferred>0:
                        if partner in current:self.links.append((o.position,current[partner].position,seconds))
                        self.events.append((sim.world.tick,identity,f'Shared {transferred:.1f} energy with #{partner}'))
                        self.events.append((sim.world.tick,partner,f'Received {transferred:.1f} energy from #{identity}'))
        for o in current.values():
            if o.id not in previous:
                parents=getattr(o,'reproductive_record',{}).get(
                    'parent_ids', () if o.parent_id is None else (o.parent_id,))
                family=' + '.join(f'#{parent}' for parent in parents)
                self.effects.append(('birth',o.position,seconds,o.id))
                self.events.append((sim.world.tick,o.id,f'Birth from {family}' if parents else 'Birth'))
                for parent in parents:self.events.append((sim.world.tick,parent,f'Offspring #{o.id} born'))
        self.motion={i:v for i,v in self.motion.items() if i in current}
        self.flashes={i:t for i,t in self.flashes.items() if t>seconds}
    def position(self,o,seconds,speed,animate):
        old,new,start=self.motion.get(o.id,(o.position,o.position,seconds))
        factor=min(1,max(0,(seconds-start)/min(.22,1/max(1,speed)))) if animate else 1
        factor=factor*factor*(3-2*factor)
        return old[0]+(new[0]-old[0])*factor,old[1]+(new[1]-old[1])*factor
    def sprite(self,o,radius,phase,quality,selected,damage):
        radius=max(3,int(radius));energy=max(0,min(4,int(o.energy/25)))
        health=max(0,min(4,int(o.health/25)))
        loss=getattr(getattr(o,'social',None),'loss',0)>.15
        direction=getattr(o,'direction',0)%4
        key=radius,phase,quality,selected,damage,energy,health,loss,o.id%7,direction
        if key in self.cache:self.cache.move_to_end(key);return self.cache[key]
        pad=8;size=2*(radius+pad);s=pg.Surface((size,size),pg.SRCALPHA);cx=cy=size/2
        if selected:
            for add,alpha in ((7,12),(4,22),(2,30)):pg.draw.circle(s,(*CYAN,alpha),(cx,cy),radius+add)
        color=(122+energy*10,132+energy*10+health*7,144+energy*10+health*4)
        if loss:color=(141+energy*7,143+energy*8,165+energy*9)
        edge=(224,147,106) if damage else (163+energy*9,211,197)
        points=[];count=10 if quality=='LOW' else 14 if quality=='MEDIUM' else 18
        theta=direction*math.pi/2-math.pi/2
        for i in range(count):
            a=2*math.pi*i/count
            deform=1+.12*math.sin(a*3+phase*.5+o.id%7)+.055*math.cos(a*5-phase*.4)
            stretch=1+.07*math.cos(a-theta)
            points.append((cx+radius*deform*stretch*math.cos(a),cy+radius*deform*math.sin(a)))
        pg.draw.polygon(s,(*color,88),points)
        if radius>=7:pg.draw.polygon(s,(*color,48),[(cx+(x-cx)*.87,cy+(y-cy)*.87) for x,y in points],1)
        pg.draw.circle(s,(*color,100),(cx,cy),max(2,round(radius*.7)))
        pg.draw.aalines(s,(*edge,220),True,points)
        if radius>=7 and quality!='LOW':
            for i in range(4):
                a=o.id+i*2.3;d=radius*.45
                pg.draw.circle(s,(191,219,190,95),(cx+math.sin(a)*d,cy+math.cos(a)*d),max(1,radius//12))
        nucleus=(round(cx+radius*.19*math.cos(theta)+radius*.06*math.sin(phase*math.pi/6)),round(cy+radius*.19*math.sin(theta)))
        pg.draw.circle(s,(77,111,128,230),nucleus,max(2,round(radius*.25)))
        pg.draw.circle(s,(182,194,208,170),(nucleus[0]-1,nucleus[1]-1),max(1,round(radius*.09)))
        self.cache[key]=s
        while len(self.cache)>256:self.cache.popitem(last=False)
        return s
    def draw(self,screen,sim,camera,rect,seconds,speed,animate,quality,selected,labels,overlay,type_):
        screen.set_clip(rect);hit=[]
        def point(p):return rect.x+camera.x+(p[0]+.5)*camera.scale,rect.y+camera.y+(p[1]+.5)*camera.scale
        if overlay and selected is not None and selected.alive:
            people=getattr(getattr(selected,'social',None),'people',{})
            for o in sim.organisms:
                strength=people.get(o.id,{}).get('bond',0)
                if strength>=.15:
                    pg.draw.line(screen,(97,106,134),point(selected.position),point(o.position),1)
        if animate and overlay:
            for a,b,start in self.links:
                if seconds-start<.7:
                    p1,p2=point(a),point(b);pg.draw.line(screen,(99,187,175),p1,p2,1)
                    f=(seconds-start)/.7;pg.draw.circle(screen,CYAN,(p1[0]+(p2[0]-p1[0])*f,p1[1]+(p2[1]-p1[1])*f),2)
        for o in sim.organisms:
            if not o.alive:continue
            position=self.position(o,seconds,speed,animate);xy=point(position)
            r=max(3,camera.scale*.39*o.growth)
            if not rect.inflate(30,30).collidepoint(xy):continue
            is_selected=selected is o
            if camera.scale<9 and not is_selected:
                pg.draw.circle(screen,(155,198,180),xy,2)
            else:
                resting=getattr(o,'last_action',None)==5
                frequency=.7 if resting else .6+max(0,o.energy)/100
                phase=int(seconds*frequency*9+o.id)%12 if animate else 0
                image=self.sprite(o,r,phase,quality,is_selected,self.flashes.get(o.id,0)>seconds)
                screen.blit(image,image.get_rect(center=xy))
            hit.append((o,xy,max(8,r+3)))
            if labels or is_selected:type_.draw(screen,f'{o.id}',(xy[0]+r+4,xy[1]-10),11,CYAN if is_selected else (173,189,199))
        if animate:
            for kind,p,start,identity in self.effects:
                age=seconds-start
                if age>1.1:continue
                xy=point(p);r=max(3,camera.scale*.4)*(1+age)
                effect=pg.Surface((int(r*4+8),)*2,pg.SRCALPHA);center=effect.get_rect().center
                color=(119,155,158) if kind=='death' else (144,205,171)
                pg.draw.circle(effect,(*color,round(120*(1-age/1.1))),center,max(1,int(r)),1)
                if kind=='death':
                    pg.draw.circle(effect,(*color,round(45*(1-age/1.1))),center,max(2,int(r*.65)))
                    for n in range(4):pg.draw.circle(effect,(*color,round(90*(1-age/1.1))),(center[0]+math.sin(n*1.6)*r,center[1]+math.cos(n*1.6)*r),1)
                else:
                    for side in (-1,1):
                        pg.draw.circle(effect,(*color,round(90*(1-age/1.1))),(center[0]+side*r*age*.65,center[1]),max(2,int(r*.43)),1)
                screen.blit(effect,effect.get_rect(center=xy))
        screen.set_clip(None);return hit
