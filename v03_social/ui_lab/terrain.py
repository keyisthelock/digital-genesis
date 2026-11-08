"""Procedural texture inside existing cells. Never edits tiles, food, RNG or navigation."""
import math,random
from collections import deque
import pygame as pg
from .theme import CYAN,AMBER,VIOLET

class Earth:
    def __init__(self):
        self.base=None;self.signature=None;self.view=None;self.view_key=None;self.waves=[]
        self.night=None;self.night_alpha=None;self.hazards=[]
    def build(self,world,quality):
        tile_size={'LOW':12,'MEDIUM':24,'HIGH':32}[quality]
        self.tile_size=tile_size
        self.base=pg.Surface((world.width*tile_size,world.height*tile_size)).convert()
        rng=random.Random(27491) # Independent cosmetic RNG; no access to world.rng.
        self.waves=[]
        self.hazards=[p for p,tile in world.tiles.items() if tile=='hazard']
        depth={p:0 for p,tile in world.tiles.items() if tile!='water'}
        frontier=deque(depth)
        while frontier:
            x,y=frontier.popleft()
            if depth[x,y]>=8:continue
            for near in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if near not in depth and world.tiles.get(near)=='water':
                    depth[near]=depth[x,y]+1
                    frontier.append(near)
        for (x,y),tile in world.tiles.items():
            t=tile_size;r=pg.Rect(x*t,y*t,t,t);variation=rng.randrange(-3,4)
            if tile=='water':
                shelf=9-depth.get((x,y),9)
                color=(10+shelf//2,24+shelf*3,42+shelf*4+variation)
                pg.draw.rect(self.base,color,r)
                if quality!='LOW' and shelf in (3,6,8):
                    pg.draw.arc(self.base,(color[0]+6,color[1]+9,color[2]+11),r.inflate(t//2,-t//3),.2,2.8)
                if (x*13+y*17)%47==0:self.waves.append((x+.5,y+.5,(x+y)%6))
            else:
                latitude=abs((y+.5)/world.height-.5)*2
                ridge=math.sin(x*.36+y*.51)+.55*math.cos(y*.84-x*.23)
                # This palette is decorative and derived from cell coordinates.
                if latitude>.83:base=(107,132,137)
                elif ridge>1.06:base=(104,105,89)
                elif latitude<.56 and ridge<-.47:base=(131,111,76)
                else:base=(58,91,72)
                if tile=='tree':base=(38,74,57)
                if tile=='hazard':base=(106,71,58)
                color=tuple(c+variation for c in base)
                pg.draw.rect(self.base,color,r)
                if quality!='LOW':
                    for _ in range(9 if quality=='MEDIUM' else 17):
                        a,b=rng.randrange(t),rng.randrange(t)
                        pg.draw.line(self.base,tuple(min(255,c+9) for c in color),(r.x+a,r.y+b),(r.x+a+1,r.y+b),1)
                    if tile=='land':
                        contour=tuple(c+11 for c in color)
                        for offset in (.25,.52,.77):
                            points=[(r.x+f*t,r.y+t*(offset+.08*math.sin(x+y+f*5))) for f in (.12,.34,.58,.86)]
                            pg.draw.aalines(self.base,contour,False,points)
                if tile=='tree':
                    for dx,dy in ((.28,.35),(.66,.68),(.65,.2)):
                        pg.draw.circle(self.base,(23,49,43),(int(r.x+dx*t),int(r.y+dy*t)),max(2,t//6))
                        pg.draw.circle(self.base,(60,98,72),(int(r.x+dx*t-1),int(r.y+dy*t-1)),max(1,t//9))
                for dx,dy,edge in ((-1,0,'left'),(1,0,'right'),(0,-1,'top'),(0,1,'bottom')):
                    if world.tiles.get((x+dx,y+dy))=='water':
                        if edge=='left':a,b=r.topleft,r.bottomleft
                        elif edge=='right':a,b=(r.right-1,r.top),(r.right-1,r.bottom)
                        elif edge=='top':a,b=r.topleft,r.topright
                        else:a,b=(r.left,r.bottom-1),(r.right,r.bottom-1)
                        pg.draw.line(self.base,(114,150,134),a,b,max(1,t//14))
        # Geographical reference grid, visually subtle and unrelated to physics.
        for x in range(0,world.width,10):pg.draw.line(self.base,(35,54,66),(x*tile_size,0),(x*tile_size,self.base.get_height()),1)
        for y in range(0,world.height,10):pg.draw.line(self.base,(35,54,66),(0,y*tile_size),(self.base.get_width(),y*tile_size),1)
        self.view_key=None
    def draw(self,screen,world,camera,rect,quality,layer,seconds,animated):
        signature=(quality,tuple(world.tiles.items()))
        if signature!=self.signature:self.build(world,quality);self.signature=signature
        key=(rect.size,round(camera.scale,4),round(camera.x),round(camera.y),quality)
        if key!=self.view_key:
            self.view=pg.Surface(rect.size).convert();self.view.fill((10,24,37))
            scale=camera.scale;t=self.tile_size
            x0=max(0,math.floor(-camera.x/scale));y0=max(0,math.floor(-camera.y/scale))
            x1=min(world.width,math.ceil((rect.w-camera.x)/scale));y1=min(world.height,math.ceil((rect.h-camera.y)/scale))
            if x1>x0 and y1>y0:
                source=pg.Rect(x0*t,y0*t,(x1-x0)*t,(y1-y0)*t)
                size=max(1,round((x1-x0)*scale)),max(1,round((y1-y0)*scale))
                transform=pg.transform.scale if quality=='LOW' else pg.transform.smoothscale
                image=transform(self.base.subsurface(source),size)
                self.view.blit(image,(round(camera.x+x0*scale),round(camera.y+y0*scale)))
            self.view_key=key
        screen.blit(self.view,rect)
        screen.set_clip(rect)
        def point(p):return (round(rect.x+camera.x+(p[0]+.5)*camera.scale),round(rect.y+camera.y+(p[1]+.5)*camera.scale))
        if animated and quality!='LOW':
            for x,y,phase in self.waves[:64]:
                px,py=point((x-.5,y-.5));length=max(2,camera.scale*.3)
                if rect.collidepoint(px,py):
                    shift=math.sin(seconds*.55+phase)*3
                    pg.draw.line(screen,(41,80,95),(px-length,py+shift),(px+length,py+shift-1),1)
        for p,amount in world.food.items():
            if amount<=1:continue
            xy=point(p)
            if not rect.collidepoint(xy):continue
            radius=max(1,min(5,round(camera.scale*.12+amount/20)))
            if layer=='RESOURCES':
                heat=pg.Surface((max(2,round(camera.scale)),)*2,pg.SRCALPHA)
                heat.fill((120,192,116,min(130,round(amount*4))))
                screen.blit(heat,(xy[0]-heat.get_width()/2,xy[1]-heat.get_height()/2))
            pg.draw.circle(screen,(141,190,119),xy,radius)
            if camera.scale>20:
                pg.draw.circle(screen,(49,79,57),xy,radius+2,1)
                pg.draw.circle(screen,(219,231,176),(xy[0]-1,xy[1]-1),max(1,radius//3))
        for p in self.hazards:
            xy=point(p)
            if rect.collidepoint(xy):
                radius=max(2,round(camera.scale*.23))
                pg.draw.polygon(screen,AMBER,[(xy[0],xy[1]-radius),(xy[0]+radius,xy[1]+radius),(xy[0]-radius,xy[1]+radius)],1)
                if radius>=5:pg.draw.line(screen,AMBER,(xy[0],xy[1]-1),(xy[0],xy[1]+radius//2),1)
                if layer=='HAZARDS':pg.draw.circle(screen,(162,112,76),xy,max(5,round(camera.scale*.6)),1)
        xy=point(world.fruit);r=max(4,round(camera.scale*.3))
        pg.draw.polygon(screen,VIOLET,[(xy[0],xy[1]-r),(xy[0]+r,xy[1]),(xy[0],xy[1]+r),(xy[0]-r,xy[1])],2)
        # Lighting uses only the measured global daylight signal.
        alpha=round((1-world.daylight)*78)
        if self.night is None or self.night.get_size()!=rect.size:
            self.night=pg.Surface(rect.size,pg.SRCALPHA);self.night_alpha=None
        if alpha!=self.night_alpha:self.night.fill((6,14,28,alpha));self.night_alpha=alpha
        screen.blit(self.night,rect);screen.set_clip(None)
