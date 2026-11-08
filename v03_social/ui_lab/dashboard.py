"""The laboratory view. Only explicit playback advances the original engine."""
import json,math,time,statistics
from pathlib import Path
import pygame as pg
from main import Camera
from .theme import BG,PANEL,PANEL2,BORDER,TEXT,MUTED,CYAN,VIOLET,GREEN,AMBER,RED,Type,panel,button,sparkline
from .terrain import Earth
from .organisms import Organics
from .telemetry import Telemetry,CHARTS,value
from . import inspector

QUALITIES=('LOW','MEDIUM','HIGH')
LAYERS=('ECOLOGY','RESOURCES','HAZARDS')
MODES={'A_rule':'Rule baseline','B_neural_nonsocial':'Neural / nonsocial','C_social_fixed':'Social / fixed genome','D_social_evolving':'Social / evolving genome'}
HELP=(('SPACE / click Pause','Pause or resume biological time'),('= / -','Double or halve target tick rate'),
    ('Wheel / right or middle drag','Zoom and pan the Earth'),('HOME','Fit the entire Earth'),
    ('Left click / F','Select an organism / follow it'),('[ / I or ]','Collapse population / inspector panels'),
    ('Drag panel borders','Resize the side panels'),('C / click a chart','Show charts / inspect a chart'),
    ('T / L','Cycle terrain layers / toggle labels'),('O','Toggle social links and active neural graph'),
    ('Q / A','Cycle graphics quality / toggle animation'),('Scroll side panels','Inspect additional fields'),
    ('G / R','Switch Laboratory and Genesis / inspect records'),
    ('H or ? / ESC','Help / close overlay or exit'))

class Laboratory:
    def __init__(self,sim,generations,speed,follow=None,quality='MEDIUM',animate=True,benchmark_seconds=0,screen=None,paused=False):
        self.sim=sim;self.generations=generations;self.speed=speed;self.follow_source=Path(follow) if follow else None
        self.quality=quality.upper();self.animate=animate;self.benchmark_seconds=benchmark_seconds
        self.paused=paused;self.running=True;self.finished=False;self.follow=False;self.labels=False;self.overlay=False
        self.seconds=0.;self.accumulator=0.;self.target_tick=0;self.next_refresh=0.
        self.frame_rate=0.;self.left=220.;self.right=300.;self.chart_h=184.
        self.left_target=220;self.right_target=300;self.left_saved=220;self.right_saved=300
        self.chart_target=184;self.stats_scroll=0;self.inspector_scroll=0;self.inspector_max_scroll=0;self.stats_max_scroll=0
        self.chart_group=0;self.inspector_tab=0;self.layer=0;self.expanded=None;self.help=False
        self.dragging=None;self.camera=None;self.zoom_target=None;self.zoom_anchor=(0,0)
        self.telemetry=Telemetry();self.telemetry.sample(sim,True)
        self.organics=Organics();self.earth=Earth();self.type=Type()
        self.selected=next((o for o in sim.organisms if o.alive),None)
        self.hits=[];self.buttons=[];self.chart_rects=[];self.chart_surface=None;self.chart_cache_key=None;self.chart_refresh=-1
        self.screen=screen;self.note='';self.note_until=0.
        self.genesis=False
        self.record_view=None
        self.preserved=None
        self.neural_cache=None
        self.neural_choice=0
    def note_for(self,message):self.note=message;self.note_until=self.seconds+2.3
    def layout(self,dt=0):
        w,h=self.screen.get_size();ease=min(1,dt*14) if self.animate and self.quality!='LOW' else 1
        targets=(('left',self.left_target),('right',self.right_target),('chart_h',self.chart_target))
        for name,target in targets:
            if self.genesis:target=0
            cur=getattr(self,name);result=cur+(target-cur)*ease
            setattr(self,name,target if abs(target-result)<1 else result)
        l=min(round(self.left),max(0,(w-500)//2));r=min(round(self.right),max(0,w-l-475))
        top=79;bottom=h-31-round(self.chart_h);height=max(260,bottom-top-10)
        self.stats_rect=pg.Rect(12,top,l,height);self.inspector_rect=pg.Rect(w-r-12,top,r,height)
        x=12+l+(10 if l else 0);right=w-r-12-(10 if r else 0)
        self.map_panel=pg.Rect(x,top,right-x,height)
        self.map_rect=self.map_panel.inflate(-12,-12);self.map_rect.y+=32;self.map_rect.h-=57
        self.timeline_rect=pg.Rect(12,self.map_panel.bottom+9,w-24,max(0,h-self.map_panel.bottom-39))
        if self.camera is None:
            self.camera=Camera(self.sim.world.width,self.sim.world.height,self.map_rect.size)
            self.zoom_target=self.camera.scale
        elif self.camera.viewport!=self.map_rect.size:
            old=self.camera;cx=(old.viewport[0]/2-old.x)/old.scale;cy=(old.viewport[1]/2-old.y)/old.scale
            new=Camera(old.width,old.height,self.map_rect.size);new.scale=new.minimum*old.scale/old.minimum
            new.x=new.viewport[0]/2-cx*new.scale;new.y=new.viewport[1]/2-cy*new.scale;new.clamp()
            self.camera=new;self.zoom_target=new.scale
    def step(self):
        before=[(o,o.position,o.health,{i:p['given'] for i,p in getattr(getattr(o,'social',None),'people',{}).items()}) for o in self.sim.organisms if o.alive]
        done=self.sim.step()
        self.organics.observe(before,self.sim,self.seconds)
        if self.selected is not None and not self.selected.alive and self.follow:
            record=self.organics.deceased.get(self.selected.id)
            if record:
                self.selected=record[1]
                self.note_for(f'Specimen #{self.selected.id} died. Open Records for its final state.')
            self.follow=False
        self.telemetry.sample(self.sim,force=done)
        if done:
            self.finished=self.sim.generation>=self.generations
            self.sim.finish_generation(reproduce=not self.finished)
            if not self.finished:
                before_replacement=self.selected
                self.selected=next((o for o in self.sim.organisms if o.alive),None)
                if before_replacement and before_replacement.id in self.organics.deceased:
                    self.selected=self.organics.deceased[before_replacement.id][1]
                self.telemetry.sample(self.sim,True)
            return self.finished
        return False
    def advance(self,dt):
        self.seconds+=dt
        if self.follow_source and self.seconds>=self.next_refresh:
            try:self.target_tick=json.loads((self.follow_source/'experiment.json').read_text())['completed_ticks']
            except (OSError,ValueError,KeyError):pass
            self.next_refresh=self.seconds+1
        if self.paused or self.finished:return
        self.accumulator=min(self.accumulator+dt*self.speed,32)
        steps=0
        while self.accumulator>=1 and steps<16:
            if self.follow_source and self.sim.world.tick>=self.target_tick:self.accumulator=0;break
            self.accumulator-=1;steps+=1
            if self.step():break
    def reset_camera(self):
        self.camera=Camera(self.sim.world.width,self.sim.world.height,self.map_rect.size)
        self.zoom_target=self.camera.scale;self.follow=False;self.note_for('Whole Earth fitted')
    def toggle(self,action):
        if action=='pause':
            self.paused=not self.paused
            if self.paused:self.telemetry.sample(self.sim,True)
            self.note_for('Paused' if self.paused else 'Resumed')
        elif action=='faster':self.speed=min(1000,self.speed*2);self.note_for(f'Target {self.speed:g} ticks/s')
        elif action=='slower':self.speed=max(1,self.speed/2);self.note_for(f'Target {self.speed:g} ticks/s')
        elif action=='left':self.left_target=0 if self.left_target else self.left_saved
        elif action=='right':self.right_target=0 if self.right_target else self.right_saved
        elif action=='charts':self.chart_target=0 if self.chart_target else 184
        elif action=='quality':self.quality=QUALITIES[(QUALITIES.index(self.quality)+1)%3];self.note_for('Graphics '+self.quality)
        elif action=='animate':self.animate=not self.animate;self.note_for('Animation on' if self.animate else 'Animation off')
        elif action=='labels':self.labels=not self.labels;self.note_for('Organism labels '+('on' if self.labels else 'off'))
        elif action=='overlay':self.overlay=not self.overlay;self.note_for('Scientific overlays '+('on' if self.overlay else 'off'))
        elif action=='layer':self.layer=(self.layer+1)%len(LAYERS);self.note_for('Layer '+LAYERS[self.layer])
        elif action=='follow':self.follow=bool(self.selected and self.selected.alive and not self.follow);self.note_for('Follow on' if self.follow else 'Follow off')
        elif action=='genesis':
            self.genesis=not self.genesis
            self.note_for('Genesis observer' if self.genesis else 'Laboratory')
        elif action=='fit':self.reset_camera()
        elif action=='records':
            self.help=False
            self.expanded=None
            self.record_view='recent'
        elif action=='preserved':
            path=Path(__file__).resolve().parents[2]/'knowledge_candidate/experiments/five_trials_10seeds/conserved_amoeba/organism_state.json'
            try:self.preserved=json.loads(path.read_text(encoding='utf-8'))
            except (OSError,ValueError):self.preserved=None
            self.record_view='preserved'
        elif action.startswith('event_'):self.record_view=int(action[6:])
        elif action.startswith('deceased_'):
            record=self.organics.deceased.get(int(action[9:]))
            if record:
                self.selected=record[1]
                self.inspector_tab=3
                self.inspector_scroll=0
                self.follow=False
                self.genesis=False
                self.right_target=self.right_saved
                self.record_view=None
        elif action=='module':self.neural_choice+=1
        elif action=='help':self.help=not self.help
        elif action=='close':self.expanded=None;self.help=False;self.record_view=None
        elif action.startswith('chart_'):self.chart_group=int(action[-1])
        elif action.startswith('inspector_'):self.inspector_tab=int(action[-1]);self.inspector_scroll=0
    def event(self,e):
        if e.type==pg.QUIT:self.running=False;return
        if e.type==pg.VIDEORESIZE:
            self.screen=pg.display.set_mode((max(1000,e.w),max(680,e.h)),pg.RESIZABLE);self.layout(1);return
        if e.type==pg.KEYDOWN:
            if e.key==pg.K_ESCAPE:
                if self.expanded is not None or self.help or self.record_view is not None:self.toggle('close')
                else:self.running=False
            elif e.key==pg.K_HOME:self.reset_camera()
            else:
                keys={pg.K_SPACE:'pause',pg.K_EQUALS:'faster',pg.K_PLUS:'faster',pg.K_KP_PLUS:'faster',pg.K_MINUS:'slower',pg.K_KP_MINUS:'slower',
                    pg.K_LEFTBRACKET:'left',pg.K_RIGHTBRACKET:'right',pg.K_i:'right',pg.K_c:'charts',pg.K_q:'quality',pg.K_a:'animate',
                    pg.K_l:'labels',pg.K_o:'overlay',pg.K_t:'layer',pg.K_f:'follow',pg.K_h:'help',pg.K_QUESTION:'help',
                    pg.K_g:'genesis',pg.K_r:'records'}
                if e.key in keys:self.toggle(keys[e.key])
        if e.type==pg.MOUSEWHEEL:
            pos=getattr(e,'pos',pg.mouse.get_pos())
            if self.map_rect.collidepoint(pos) and not self.help and self.expanded is None and self.record_view is None:
                self.zoom_anchor=pos[0]-self.map_rect.x,pos[1]-self.map_rect.y
                self.zoom_target=max(self.camera.minimum,min(self.camera.minimum*8,self.zoom_target*1.25**e.y))
                if not self.animate:self.camera.zoom(self.zoom_target/self.camera.scale,self.zoom_anchor)
            elif self.stats_rect.collidepoint(pos):self.stats_scroll=max(0,min(self.stats_max_scroll,self.stats_scroll-37*e.y))
            elif self.inspector_rect.collidepoint(pos):self.inspector_scroll=max(0,min(self.inspector_max_scroll,self.inspector_scroll-37*e.y))
        if e.type==pg.MOUSEBUTTONDOWN:
            if e.button==1:
                for r,action in reversed(self.buttons):
                    if r.collidepoint(e.pos):self.toggle(action);return
                if self.help or self.expanded is not None or self.record_view is not None:return
                for i,r in enumerate(self.chart_rects):
                    if r.collidepoint(e.pos):self.expanded=(self.chart_group,i);return
                if self.stats_rect.w and abs(e.pos[0]-self.stats_rect.right-4)<6 and self.stats_rect.top<=e.pos[1]<=self.stats_rect.bottom:self.dragging='left';return
                if self.inspector_rect.w and abs(e.pos[0]-self.inspector_rect.left+4)<6 and self.inspector_rect.top<=e.pos[1]<=self.inspector_rect.bottom:self.dragging='right';return
                if self.map_rect.collidepoint(e.pos):
                    hits=[(math.dist(e.pos,p),o) for o,p,r in self.hits if math.dist(e.pos,p)<=r]
                    if hits:
                        self.selected=min(hits,key=lambda x:x[0])[1]
                        self.inspector_scroll=0
                        self.neural_choice=0
                        self.follow=False
            elif e.button in (2,3) and self.record_view is None and not self.help and self.expanded is None and self.map_rect.collidepoint(e.pos):
                self.dragging='map';self.follow=False
        if e.type==pg.MOUSEBUTTONUP:self.dragging=None
        if e.type==pg.MOUSEMOTION and self.dragging:
            if self.dragging=='map':self.camera.x+=e.rel[0];self.camera.y+=e.rel[1];self.camera.clamp()
            elif self.dragging=='left':self.left_saved=self.left_target=max(158,min(330,self.left_target+e.rel[0]))
            else:self.right_saved=self.right_target=max(202,min(405,self.right_target-e.rel[0]))
    def view_camera(self,dt):
        if abs(self.zoom_target-self.camera.scale)>.005:
            target=self.camera.scale+(self.zoom_target-self.camera.scale)*(min(1,dt*16) if self.animate else 1)
            self.camera.zoom(target/self.camera.scale,self.zoom_anchor)
        if self.follow and self.selected and self.selected.alive:
            x,y=self.organics.position(self.selected,self.seconds,self.speed,self.animate)
            blend=min(1,dt*6) if self.animate else 1
            self.camera.x+=(self.map_rect.w/2-(x+.5)*self.camera.scale-self.camera.x)*blend
            self.camera.y+=(self.map_rect.h/2-(y+.5)*self.camera.scale-self.camera.y)*blend
            self.camera.clamp()
    def widget(self,rect,label,action,active=False):
        button(self.screen,rect,label,self.type,active);self.buttons.append((rect,action))
    def top(self):
        s=self.screen;t=self.type;w=s.get_width()
        pg.draw.rect(s,(13,18,27),(0,0,w,68));pg.draw.line(s,BORDER,(0,67),(w,67))
        pg.draw.circle(s,(24,65,77),(29,34),16);pg.draw.circle(s,CYAN,(29,34),15,1)
        pg.draw.ellipse(s,CYAN,(20,26,18,16),1);pg.draw.circle(s,CYAN,(29,34),4)
        t.draw(s,'DIGITAL GENESIS',(54,10),24,TEXT,True)
        t.draw(s,'Artificial Life Research Laboratory',(55,40),13,MUTED)
        mode='Checkpoint replay' if self.follow_source else MODES.get(getattr(self.sim,'treatment',''),'Legacy simulation')
        status='COMPLETE' if self.finished else 'PAUSED' if self.paused else 'REPLAY' if self.follow_source else 'RUNNING'
        x=309;t.draw(s,mode,(x,12),14,TEXT,True,max_width=220)
        gen=f'Gen {self.sim.generation}  /  Tick {self.sim.world.tick:,}'
        if self.follow_source:gen+=f' / {self.target_tick:,}'
        t.draw(s,gen,(x,36),13,MUTED,max_width=max(150,w-810))
        if w>=1320:
            t.draw(s,'EXPERIMENT',(562,13),11,CYAN,True)
            t.draw(s,Path(self.sim.output).name,(562,36),12,MUTED,max_width=max(120,w-1160))
        cluster=[('Play' if self.paused else 'Pause','pause',56,self.paused),('-','slower',28,False),('+','faster',28,False),
            ('[','left',27,bool(self.left_target)),('I','right',27,bool(self.right_target)),('C','charts',27,bool(self.chart_target)),
            ('Q','quality',27,False),('?','help',27,self.help),
            ('Records','records',59,False),('Genesis' if not self.genesis else 'Laboratory','genesis',80,self.genesis)]
        xpos=w-12-sum(a[2]+5 for a in cluster)
        if w>=1130:
            t.draw(s,status,(xpos-131,13),12,AMBER if self.paused else GREEN,True)
            t.draw(s,f'{self.speed:g} ticks/s  |  {self.frame_rate:.0f} FPS',(xpos-131,36),12,MUTED)
        for label,action,ww,on in cluster:
            self.widget(pg.Rect(xpos,19,ww,30),label,action,on);xpos+=ww+5
    def stats(self):
        r=self.stats_rect;s=self.screen;t=self.type;d=self.telemetry.last
        if r.w<90:return
        panel(s,r);x=r.x+13;w=r.w-26;t.draw(s,'POPULATION OBSERVATORY',(x,r.y+13),12,CYAN,True,max_width=w)
        clip=pg.Rect(x,r.y+39,w,r.h-48);s.set_clip(clip);y=clip.y-self.stats_scroll;start=y
        panel(s,pg.Rect(x,y,w,74),PANEL2,8)
        t.draw(s,'LIVING ORGANISMS',(x+10,y+7),11,MUTED,True,max_width=w-20)
        t.draw(s,str(d['living']),(x+10,y+24),31,TEXT,True)
        t.draw(s,f'Cap {self.sim.max_population}',(x+w-69,y+45),11,MUTED);y+=83
        if hasattr(self.sim,'reproductive_mode'):
            t.draw(s,f'Type A {d["type_a"]}   /   Type B {d["type_b"]}',(x,y),12,TEXT,max_width=w);y+=24
            births=getattr(self.sim,'recent_births',())
            if births:
                latest=births[-1]
                t.draw(s,f'Latest birth #{latest["id"]} at tick {latest["tick"]}',(x,y),12,TEXT,max_width=w);y+=24
        for label,key,places in (('Births','births',0),('Deaths','deaths',0),('Extinctions observed','extinctions',0),
                                  ('Mean living energy','energy',1),('Mean living fitness','fitness',2),('Food remaining','food',1)):
            t.draw(s,label,(x,y),12,MUTED,max_width=w-56)
            val=value(d[key],places);text=t.surface(val,12,TEXT,True)
            t.draw(s,val,(max(x+55,x+w-text.get_width()),y),12,TEXT,True,max_width=w-50);y+=26
        pg.draw.line(s,BORDER,(x,y),(x+w,y));y+=10
        t.draw(s,'ACTIVE CONFIGURATION',(x,y),11,CYAN,True,max_width=w);y+=23
        config=(f'Run: {Path(self.sim.output).name}',f'Seed: {getattr(self.sim,"seed_value","Not available")}',
                f'Founders: {self.sim.size} / cap {self.sim.max_population}',f'Body mutation: {self.sim.rate:.0%}',
                f'Resource fraction: {self.sim.world.resource_fraction:.0%}',f'Lifetime reproduction: {"on" if self.sim.lifetime else "off"}',
                f'Maturity: {self.sim.maturity_age} ticks',f'Sampled tick: {self.telemetry.last_tick}')
        if hasattr(self.sim,'reproductive_mode'):
            config+=(f'Reproduction: {self.sim.reproductive_mode}',
                     f'Type A birth chance: {self.sim.type_a_probability:.0%}',
                     f'Partner distance: {self.sim.interaction_distance} tiles')
        for v in config:t.draw(s,v,(x,y),12,TEXT,max_width=w);y+=20
        self.stats_max_scroll=max(0,y-start-clip.h);s.set_clip(None)
    def map(self):
        s=self.screen;t=self.type;r=self.map_panel
        panel(s,r);t.draw(s,'GENESIS  /  OBSERVER' if self.genesis else 'EARTH OBSERVATION',(r.x+12,r.y+9),12,CYAN,True)
        info=f'{LAYERS[self.layer]}   |   {self.camera.scale/self.camera.minimum:.2f}x   |   {self.quality}'
        if self.follow:info+='   |   FOLLOW'
        t.draw(s,info,(r.x+157,r.y+10),11,MUTED,max_width=r.w-283)
        self.widget(pg.Rect(r.right-114,r.y+5,43,24),'Fit','fit')
        self.widget(pg.Rect(r.right-66,r.y+5,57,24),'Follow','follow',self.follow)
        self.earth.draw(s,self.sim.world,self.camera,self.map_rect,self.quality,LAYERS[self.layer],self.seconds,self.animate)
        self.hits=self.organics.draw(s,self.sim,self.camera,self.map_rect,self.seconds,self.speed,self.animate,self.quality,self.selected,self.labels,self.overlay,t)
        x=r.x+12;y=r.bottom-21
        for label,color in (('Food',(145,191,111)),('Hazard',AMBER),('Inert gateway',VIOLET)):
            pg.draw.circle(s,color,(x+4,y+7),3);t.draw(s,label,(x+12,y),11,MUTED);x+=64 if label!='Hazard' else 74
        if self.genesis and self.selected is not None:
            record=self.organics.deceased.get(self.selected.id)
            message=(f'Specimen #{self.selected.id}  /  final record at tick {record[0]:,}' if record
                     else f'Specimen #{self.selected.id}  /  age {self.selected.age:,}  /  energy {self.selected.energy:.1f}')
            t.draw(s,message,(x+55,y),12,TEXT,max_width=r.right-x-64)
        elif r.w>540:t.draw(s,'Illustrative terrain relief',(r.right-155,y),11,MUTED)
        mouse=pg.mouse.get_pos()
        if self.map_rect.collidepoint(mouse) and not self.help and self.expanded is None:
            tile=self.camera.tile_at(mouse[0]-self.map_rect.x,mouse[1]-self.map_rect.y)
            kind=self.sim.world.tiles.get(tile)
            if kind:
                o=next((o for o,p,rr in self.hits if math.dist(mouse,p)<=rr),None)
                text=f'ID {o.id} / energy {o.energy:.1f}' if o else f'Tile {tile[0]}, {tile[1]}  |  {kind}  |  food {self.sim.world.food.get(tile,0):.1f}'
                image=t.surface(text,11,TEXT);rr=pg.Rect(min(mouse[0]+12,self.map_rect.right-image.get_width()-17),min(mouse[1]+13,self.map_rect.bottom-24),image.get_width()+14,22)
                panel(s,rr,PANEL2,5);s.blit(image,(rr.x+7,rr.y+3))
    def timeline(self):
        self.chart_rects=[];r=self.timeline_rect;s=self.screen;t=self.type
        if r.h<100:return
        panel(s,r);t.draw(s,'LIVE TELEMETRY',(r.x+12,r.y+10),12,CYAN,True)
        x=r.x+123
        for i,name in enumerate(('Population','Resources','Cognition')):
            self.widget(pg.Rect(x,r.y+7,89,25),name,f'chart_{i}',self.chart_group==i);x+=94
        ticks=self.telemetry.history
        t.draw(s,f'Tick {ticks[0][0]:,} to {ticks[-1][0]:,}   |   {len(ticks)} samples',(r.right-236,r.y+10),12,MUTED)
        w=(r.w-36)//3;h=r.h-67
        key=(w,h,self.chart_group)
        if self.chart_surface is None or key!=self.chart_cache_key or self.seconds>=self.chart_refresh:
            surface=pg.Surface((r.w-18,h)).convert();surface.fill(PANEL)
            for i,(name,keys,unit) in enumerate(CHARTS[self.chart_group]):
                chart=pg.Rect(i*(w+6),0,w,h)
                tick_axis=[tick for tick,_ in ticks]
                sparkline(surface,chart,self.telemetry.series(keys),(CYAN,VIOLET),t,name,unit,ticks=tick_axis)
                prev=0
                for j,(_,d) in enumerate(ticks):
                    if d['extinctions']>prev and j:
                        xx=chart.x+12+(chart.w-24)*(tick_axis[j]-tick_axis[0])/max(1,tick_axis[-1]-tick_axis[0])
                        pg.draw.line(surface,RED,(xx,31),(xx,h-14),1)
                    prev=d['extinctions']
            self.chart_surface=surface;self.chart_cache_key=key;self.chart_refresh=self.seconds+.25
        s.blit(self.chart_surface,(r.x+9,r.y+38))
        for i in range(3):self.chart_rects.append(pg.Rect(r.x+9+i*(w+6),r.y+38,w,h))
        y=r.bottom-21;start=r.x+12;end=r.right-12
        pg.draw.line(s,BORDER,(start,y),(end,y),3)
        first=ticks[0][0]
        last=self.sim.world.tick
        event_positions={}
        for tick,identity,message in self.organics.events:
            if tick<first or (self.selected and identity!=self.selected.id):continue
            pixel=int(start+(end-start)*(tick-first)/max(1,last-first))
            event_positions[pixel//14]=(pixel,tick,message)
        for pixel,tick,message in list(event_positions.values())[-24:]:
            pg.draw.circle(s,AMBER if message.startswith('death') else CYAN,(pixel,y),4)
            self.buttons.append((pg.Rect(pixel-6,y-6,12,12),f'event_{tick}'))
        t.draw(s,'Biological time  /  select a marker for recorded events  /  red line: extinction',(start,y+5),10,MUTED)
    def records(self,rect):
        screen=self.screen
        t=self.type
        x=rect.x+20
        y=rect.y+60
        self.widget(pg.Rect(x,rect.y+15,95,27),'Recent events','records',self.record_view=='recent')
        self.widget(pg.Rect(x+102,rect.y+15,115,27),'Preserved #36','preserved',self.record_view=='preserved')
        if self.record_view=='preserved':
            state=self.preserved
            if state is None:
                t.draw(screen,'Preserved observation unavailable',(x,y),15,MUTED)
                return
            t.draw(screen,'Organism 36  /  conserved v0.2 observation',(x,y),18,CYAN,True)
            for label,key in (('Parent','parent_id'),('Lineage generation','lineage_generation'),('Observed age','age'),
                              ('Energy','energy'),('Health','health'),('Offspring','offspring'),('Food acquired','food_acquired')):
                y+=32
                observed=state.get(key)
                t.draw(screen,f'{label}  /  {value(observed,2) if isinstance(observed,float) else observed if observed is not None else "Unavailable"}',(x,y),15,TEXT)
            return
        tick=self.record_view if isinstance(self.record_view,int) else None
        title=f'Events at tick {tick:,}' if tick is not None else 'Recent observed events'
        t.draw(screen,title,(x,y),18,CYAN,True)
        events=[event for event in self.organics.events if tick is None or event[0]==tick]
        if tick is not None and self.selected:
            events=[event for event in events if event[1]==self.selected.id]
        for event_tick,identity,message in reversed(events[-7:]):
            y+=27
            t.draw(screen,f'{event_tick:>5,}   #{identity}   {message}',(x,y),14,TEXT,max_width=rect.w-40)
        if not events:
            y+=27
            t.draw(screen,'No matching events in the session buffer',(x,y),14,MUTED)
        y=rect.y+293
        t.draw(screen,'FINAL STATES  /  THIS SESSION',(x,y),12,CYAN,True)
        for i,(identity,(death_tick,_)) in enumerate(list(self.organics.deceased.items())[-12:][::-1]):
            width=(rect.w-50)//4
            self.widget(pg.Rect(x+i%4*width,y+25+i//4*32,width-5,26),
                        f'#{identity}  /  tick {death_tick:,}',f'deceased_{identity}')
    def modal(self):
        if not self.help and self.expanded is None and self.record_view is None:return
        s=self.screen;t=self.type;shade=pg.Surface(s.get_size(),pg.SRCALPHA);shade.fill((5,9,16,185));s.blit(shade,(0,0))
        w=min(800,s.get_width()-70);h=510 if self.help else min(440,s.get_height()-100)
        rect=pg.Rect(0,0,w,h);rect.center=s.get_rect().center;panel(s,rect)
        self.buttons=[];self.widget(pg.Rect(rect.right-63,rect.y+11,49,27),'Close','close')
        if self.help:
            t.draw(s,'Laboratory controls',(rect.x+22,rect.y+15),20,TEXT,True)
            for i,(key,desc) in enumerate(HELP):
                y=rect.y+58+i*31
                t.draw(s,key,(rect.x+22,y),13,CYAN,max_width=230);t.draw(s,desc,(rect.x+258,y),14,TEXT,max_width=w-280)
        elif self.record_view is not None:
            self.records(rect)
        else:
            group,i=self.expanded;name,keys,unit=CHARTS[group][i]
            sparkline(s,pg.Rect(rect.x+13,rect.y+46,w-26,h-65),self.telemetry.series(keys),(CYAN,VIOLET),t,name,unit,True,ticks=[tick for tick,_ in self.telemetry.history])
            t.draw(s,'Recorded samples; no simulated interpolation',(rect.x+15,rect.y+13),14,MUTED)
    def render(self,dt=0):
        self.layout(dt);self.view_camera(dt)
        s=self.screen;s.fill(BG);self.buttons=[]
        self.top();self.stats();self.map()
        if self.inspector_rect.w>=140:inspector.draw(s,self.inspector_rect,self)
        self.timeline()
        status=self.note if self.seconds<self.note_until else 'OFFLINE   /   CPU RENDERING   /   Measured state and derived telemetry'
        self.type.draw(s,status,(14,s.get_height()-24),11,MUTED,max_width=s.get_width()-28)
        self.modal()
    def run(self):
        if self.screen is None:
            pg.init();dw,dh=pg.display.get_desktop_sizes()[0]
            self.screen=pg.display.set_mode((min(1480,dw-36),min(900,dh-84)),pg.RESIZABLE)
            pg.display.set_caption('Digital Genesis | Artificial Life Research Laboratory')
            style_caption()
        clock=pg.time.Clock();self.layout(1);start=time.perf_counter();cpu=time.process_time();frames=[];start_tick=self.sim.world.tick
        try:
            while self.running:
                dt=clock.tick(60 if self.quality=='HIGH' else 30)/1000
                self.frame_rate=clock.get_fps()
                for event in pg.event.get():self.event(event)
                if not self.running:break
                self.advance(min(.15,dt));self.render(min(.15,dt));pg.display.flip()
                elapsed=time.perf_counter()-start
                if self.benchmark_seconds and elapsed>=1:frames.append(dt)
                if self.benchmark_seconds and elapsed>=self.benchmark_seconds:break
            if self.benchmark_seconds:
                elapsed=time.perf_counter()-start;cpu_s=time.process_time()-cpu
                stats=dict(quality=self.quality,window=list(self.screen.get_size()),frames_after_warmup=len(frames),
                    mean_fps=1/statistics.mean(frames) if frames else None,
                    frame_ms_p95=1000*sorted(frames)[min(len(frames)-1,math.floor(len(frames)*.95))] if frames else None,
                    wall_seconds=elapsed,cpu_seconds=cpu_s,cpu_percent_of_one_core=100*cpu_s/elapsed,
                    biological_ticks=self.sim.world.tick-start_tick,peak_working_set_mb=peak_working_set())
                (Path(self.sim.output)/'ui_benchmark.json').write_text(json.dumps(stats,indent=2));print(json.dumps(stats),flush=True)
        finally:pg.quit()
        return False

def style_caption():
    """Apply a restrained native caption where Windows supports DWM colors."""
    try:
        import ctypes
        hwnd=pg.display.get_wm_info().get('window')
        if not hwnd:return
        set_attribute=ctypes.windll.dwmapi.DwmSetWindowAttribute
        set_attribute.argtypes=(ctypes.c_void_p,ctypes.c_uint,ctypes.c_void_p,ctypes.c_uint)
        for attribute,rgb in ((34,(42,54,69)),(35,(13,18,27)),(36,(233,239,245))):
            red,green,blue=rgb
            color=ctypes.c_uint(red|(green<<8)|(blue<<16))
            set_attribute(hwnd,attribute,ctypes.byref(color),ctypes.sizeof(color))
    except (AttributeError,OSError):
        pass

def peak_working_set():
    try:
        import ctypes
        class Counters(ctypes.Structure):
            _fields_=[('cb',ctypes.c_ulong),('faults',ctypes.c_ulong)]+[(n,ctypes.c_size_t) for n in ('peak','working','p1','p2','p3','p4','page','peak_page')]
        counters=Counters();counters.cb=ctypes.sizeof(counters)
        process=ctypes.windll.kernel32.GetCurrentProcess;process.restype=ctypes.c_void_p
        read=ctypes.windll.psapi.GetProcessMemoryInfo
        read.argtypes=(ctypes.c_void_p,ctypes.POINTER(Counters),ctypes.c_ulong)
        if read(process(),ctypes.byref(counters),counters.cb):return counters.peak/1024**2
    except (AttributeError,OSError):pass
    return None
