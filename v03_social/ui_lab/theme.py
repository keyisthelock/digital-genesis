from collections import OrderedDict
import pygame as pg

BG=(9,12,18); PANEL=(18,23,32); PANEL2=(23,31,43); BORDER=(42,54,69)
TEXT=(233,239,245); MUTED=(163,178,194); CYAN=(112,210,216); VIOLET=(173,151,218)
GREEN=(124,183,139); AMBER=(220,174,104); RED=(209,113,107)

class Type:
    def __init__(self):
        self.fonts={};self.cache=OrderedDict()
    def surface(self,text,size=14,color=TEXT,bold=False):
        key=str(text),size,color,bold
        if key not in self.cache:
            if (size,bold) not in self.fonts:self.fonts[size,bold]=pg.font.SysFont('segoeui',size,bold=bold)
            font=self.fonts[size,bold]
            self.cache[key]=font.render(str(text),True,color)
            while len(self.cache)>768:self.cache.popitem(last=False)
        self.cache.move_to_end(key);return self.cache[key]
    def draw(self,s,text,pos,size=14,color=TEXT,bold=False,max_width=None):
        text=str(text);image=self.surface(text,size,color,bold)
        if max_width is not None and image.get_width()>max_width:
            font=self.fonts[size,bold]
            while text and font.size(text+'...')[0]>max_width:text=text[:-1]
            if font.size('...')[0]>max_width:return image.get_height()
            image=self.surface(text+'...',size,color,bold)
        s.blit(image,pos);return image.get_height()

def panel(s,r,color=PANEL,radius=12):
    pg.draw.rect(s,(5,11,18),r.move(0,3),border_radius=radius)
    pg.draw.rect(s,color,r,border_radius=radius);pg.draw.rect(s,BORDER,r,1,border_radius=radius)

def button(s,r,label,type_,active=False):
    hover=r.collidepoint(pg.mouse.get_pos())
    pg.draw.rect(s,(32,62,73) if active else PANEL2 if hover else PANEL,r,border_radius=6)
    pg.draw.rect(s,CYAN if active else BORDER,r,1,border_radius=6)
    image=type_.surface(label,12,CYAN if active else TEXT)
    s.blit(image,image.get_rect(center=r.center))

def sparkline(s,r,series,colors_,type_,title,unit='',expanded=False,ticks=None):
    panel(s,r)
    type_.draw(s,title,(r.x+12,r.y+8),12,TEXT,True,max_width=r.w-24)
    area=pg.Rect(r.x+12,r.y+31,r.w-24,r.h-47)
    values=[v for seq in series for v in seq if v is not None]
    if not values:
        type_.draw(s,'Not available',(area.x,area.y+5),12,MUTED);return
    lo=min(0,min(values));hi=max(values)
    if hi==lo:hi=lo+1
    pg.draw.line(s,BORDER,(area.left,area.bottom),(area.right,area.bottom))
    for seq,color in zip(series,colors_):
        pts=[]
        for i,v in enumerate(seq):
            fraction=(ticks[i]-ticks[0])/max(1,ticks[-1]-ticks[0]) if ticks else i/max(1,len(seq)-1)
            if v is not None:pts.append((area.x+fraction*area.w,area.bottom-(v-lo)/(hi-lo)*area.h))
        if len(pts)>1:pg.draw.lines(s,color,False,pts,2 if expanded else 1)
        elif pts:pg.draw.circle(s,color,pts[0],2)
    last=next((v for v in reversed(series[0]) if v is not None),None)
    if last is not None:type_.draw(s,f'{last:.3g} {unit}',(r.right-80,r.y+9),11,colors_[0])
    if expanded:
        type_.draw(s,f'Range {lo:.3g} to {hi:.3g}; samples in biological tick order',(area.x,r.bottom-18),11,MUTED)
