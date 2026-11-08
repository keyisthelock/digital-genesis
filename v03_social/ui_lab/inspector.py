import pygame as pg
from .theme import panel,button,PANEL2,TEXT,MUTED,CYAN,GREEN,AMBER,VIOLET,RED,BORDER
from .telemetry import value

ACTIONS=('Move north','Move east','Move south','Move west','Eat','Rest','Share','Inspect gateway','Turn')

def action_label(o,treatment):
    action=getattr(o,'last_action',None)
    if o.age==0 or not isinstance(action,int) or not 0<=action<len(ACTIONS):return 'Not available'
    # TrackedRule records all movement as 0, not the neural north action.
    return 'Move' if action==0 and treatment=='A_rule' else ACTIONS[action]

def network(screen,rect,brain,type_,index):
    """One active module's actual input edges, recurrent nodes and readouts."""
    panel(screen,rect,PANEL2,8)
    if not brain.active:return type_.draw(screen,'Not available',(rect.x+10,rect.y+8),12,MUTED)
    m=brain.modules[index];p=m.p
    type_.draw(screen,f'Module {index} / {p["group"]}',(rect.x+10,rect.y+7),12,CYAN,True)
    inputs=sorted({i for i,_,_ in p['edges']})
    def ys(n):return [rect.y+32+i*(rect.h-42)/max(1,n-1) for i in range(n)]
    src={i:(rect.x+27,y) for i,y in zip(inputs,ys(len(inputs)))}
    middle=[(rect.centerx,y) for y in ys(p['n'])];out=[(rect.right-32,y) for y in ys(9)]
    for i,j,w in p['edges']:pg.draw.line(screen,(68,120,118) if w>=0 else (101,84,129),src[i],middle[j],1)
    for j,row in enumerate(p['out']):
        for k,w in enumerate(row):pg.draw.line(screen,(54,91,95) if w>=0 else (83,72,111),middle[j],out[k],1)
    for i,xy in src.items():
        pg.draw.circle(screen,CYAN,xy,2);type_.draw(screen,str(i),(rect.x+7,xy[1]-7),9,MUTED)
    for j,xy in enumerate(middle):
        activation=m.state[j]
        pg.draw.circle(screen,VIOLET,xy,4+round(abs(activation)*4))
        type_.draw(screen,f'{activation:+.2f}',(xy[0]+9,xy[1]-8),10,TEXT)
    for j,xy in enumerate(out):
        pg.draw.circle(screen,GREEN,xy,2);type_.draw(screen,str(j) if j<8 else 'pred',(xy[0]+5,xy[1]-7),9,MUTED)

def draw(screen,rect,lab):
    t=lab.type;panel(screen,rect);margin=14;x=rect.x+margin;w=rect.w-2*margin
    if rect.w<140:return
    t.draw(screen,'ORGANISM INSPECTOR',(x,rect.y+13),12,CYAN,True)
    o=lab.selected
    if o is None:
        t.draw(screen,'Select an organism on Earth.',(x,rect.y+47),14,MUTED,max_width=w);return
    for i,name in enumerate(('State','Mind','Social','History')):
        r=pg.Rect(x+i*w//4,rect.y+38,w//4-4,28)
        button(screen,r,name,t,lab.inspector_tab==i);lab.buttons.append((r,f'inspector_{i}'))
    clip=pg.Rect(x,rect.y+76,w,rect.h-86);screen.set_clip(clip)
    y=clip.y-lab.inspector_scroll;start=y
    def line(label,v,color=TEXT):
        nonlocal y
        t.draw(screen,label,(x,y),11,MUTED,max_width=w)
        t.draw(screen,v,(x,y+15),14,color,max_width=w);y+=37
    def heading(s):
        nonlocal y
        t.draw(screen,s,(x,y),11,CYAN,True,max_width=w);y+=20
    def bar(label,val,color):
        nonlocal y
        t.draw(screen,f'{label}  {val:.1f}',(x,y),13,TEXT,max_width=w)
        pg.draw.rect(screen,BORDER,(x,y+21,w,5),border_radius=3)
        pg.draw.rect(screen,color,(x,y+21,int(w*max(0,min(1,val/100))),5),border_radius=3);y+=34
    if lab.inspector_tab==0:
        img=lab.organics.sprite(o,29,int(lab.seconds*6)%12 if lab.animate and o.alive else 0,lab.quality,True,False)
        screen.blit(img,(x,y));t.draw(screen,f'Specimen {o.id:03d}',(x+78,y+11),18,TEXT,True,max_width=w-78)
        t.draw(screen,'Alive' if o.alive else f'Dead: {o.death_cause}',(x+78,y+38),12,GREEN if o.alive else RED,max_width=w-78);y+=79
        bar('Energy',o.energy,CYAN);bar('Health',o.health,GREEN)
        line('AGE / MAX LIFESPAN',f'{o.age} / {o.max_lifespan} ticks')
        if hasattr(o,'reproductive_type'):
            parents=o.reproductive_record['parent_ids']
            line('REPRODUCTIVE TYPE',o.reproductive_type)
            line('LINEAGE / PARENTS / OFFSPRING',f'{o.generation} / {" + ".join(map(str,parents)) or "founder"} / {o.offspring}')
        else:
            line('LINEAGE / PARENT / OFFSPRING',f'{o.generation} / {o.parent_id if o.parent_id is not None else "founder"} / {o.offspring}')
            line('OBSERVED ANCESTRY',lab.telemetry.ancestry(o))
        line('HUNGER / DAMAGE SIGNAL',f'{o.hunger:.2f} / {o.pain:.2f}')
        line('LAST SELECTED ACTION',action_label(o,getattr(lab.sim,'treatment',None)))
        line('FOOD ACQUIRED / TILES VISITED',f'{o.acquired:.2f} units / {len(o.visited)}')
        line('TILE / GROWTH',f'{o.position} / {o.growth:.0%}')
        heading('OBSERVED EVENTS')
        events=[f'Tick {tick}: {e}' for tick,i,e in lab.organics.events if i==o.id][-4:]
        for item in events or ['None observed in this view']:
            t.draw(screen,item,(x,y),12,MUTED,max_width=w);y+=19
    elif lab.inspector_tab==1:
        b=getattr(o,'brain',None)
        if b is None:
            line('NEURAL STATE','Not available');line('POLICY','Rule baseline');line('RULE MEMORY LOCATIONS',str(len(o.memory)))
        else:
            line('BRAIN SIZE / ACTIVE MODULES',f'{len(b.modules)} / {", ".join(map(str,b.active)) or "Not available"}')
            line('STORED COMPLEXITY / NEURAL OPERATIONS',f'{b.complexity:,} params / {b.ops:,} ops')
            line('SIMULATED BRAIN ENERGY COST',f'{o.brain_cost:.3f} energy')
            line('PREDICTION ERROR / UPDATES',f'{value(b.squared_error/b.predictions if b.predictions else None,4)} MSE / {b.updates}')
            confidence=[b.memory.estimate(p,o.age,b.genetic['decay'])[1] for p in b.memory.long]
            line('MEAN ASSOCIATION CONFIDENCE',value(sum(confidence)/len(confidence) if confidence else None,3))
            line('LONG-TERM / WORKING LOCATIONS',f'{len(b.memory.long)} / {len(b.memory.working)}')
            if b.active:
                key=(o.id,w,lab.neural_choice)
                cache=lab.neural_cache
                if cache is None or cache[0]!=key or lab.seconds-cache[1]>=.2:
                    index=b.active[lab.neural_choice%len(b.active)]
                    surface=pg.Surface((w,152)).convert()
                    surface.fill(PANEL2)
                    network(surface,surface.get_rect(),b,t,index)
                    lab.neural_cache=(key,lab.seconds,surface)
                screen.blit(lab.neural_cache[2],(x,y))
                y+=159
                if clip.contains(pg.Rect(x,y,w,25)):
                    lab.widget(pg.Rect(x,y,w,25),'Cycle active module','module')
                y+=32
            else:line('CONNECTIVITY VIEW','Not available')
    elif lab.inspector_tab==2:
        if hasattr(o,'reproductive_type'):
            heading('RECORDED MATING INTERACTIONS')
            interactions=[e for e in lab.sim.recent_partners if o.id in (e['initiator'],e['partner'])]
            for event in interactions[-4:]:
                other=event['partner'] if event['initiator']==o.id else event['initiator']
                line(f'TICK {event["tick"]} / PARTNER #{other}',
                     f'Child #{event["child"]} · bond {event["bond"]:+.2f}')
            if not interactions:
                line('PARTNER HISTORY','No mating recorded')
        s=getattr(o,'social',None)
        if s is None or not getattr(lab.sim,'social_on',False):line('SOCIAL MEMORY','Not available')
        else:
            line('KNOWN IDS / RECURRING GROUPS',f'{len(s.people)} / {len(s.groups)}')
            line('ISOLATION / OBSERVED LOSS SIGNAL',f'{s.isolation:.3f} / {s.loss:.3f}',VIOLET)
            heading('NUMERICAL BONDS / ENERGY GIVEN & RECEIVED')
            for identity,p in sorted(s.people.items(),key=lambda z:-z[1]['bond'])[:6]:
                t.draw(screen,f'#{identity}  {p["bond"]:+.2f}   {p["given"]:.1f} / {p["received"]:.1f}',(x,y),13,TEXT,max_width=w);y+=22
            if not s.people:t.draw(screen,'No encounters recorded',(x,y),12,MUTED);y+=22
            heading('OBSERVED GROUP MEMBERSHIPS')
            for members,count in list(s.groups.items())[-4:][::-1]:
                t.draw(screen,f'{", ".join(map(str,members))}  /  {count} samples',(x,y),12,MUTED,max_width=w)
                y+=20
            if not s.groups:
                t.draw(screen,'No group samples recorded',(x,y),12,MUTED)
                y+=20
            heading('RECENT BONDED DEATH OBSERVATIONS')
            for event in list(s.events)[-4:] or [None]:
                message=f'Tick {event["tick"]}: ID {event["identity"]}, bond {event["bond"]:.2f}' if event else 'None recorded'
                t.draw(screen,message,(x,y),12,MUTED,max_width=w);y+=20
    else:
        record=lab.organics.deceased.get(o.id)
        line('SPECIMEN RECORD',f'#{o.id}  /  age {o.age:,} ticks')
        if record:line('OBSERVED DEATH',f'Tick {record[0]:,}  /  {o.death_cause}',AMBER)
        heading('OBSERVED FAMILY TREE')
        if hasattr(o,'reproductive_type'):
            pending=[o.id]
            seen=set()
            while pending and len(seen)<12:
                identity=pending.pop(0)
                if identity in seen:
                    continue
                seen.add(identity)
                parents=lab.telemetry.family.get(identity)
                if parents is None:
                    line(f'#{identity}','Outside the session history')
                elif not parents:
                    line(f'#{identity}','Founder')
                else:
                    anchors=[x+w//2] if len(parents)==1 else [x+w//4,x+3*w//4]
                    t.draw(screen,f'#{identity}',(x+w//2-12,y),13,TEXT,max_width=w//2)
                    for parent,anchor in zip(parents,anchors):
                        pg.draw.line(screen,BORDER,(x+w//2,y+16),(anchor,y+30))
                        t.draw(screen,f'#{parent}',(anchor-12,y+32),12,CYAN,max_width=w//4)
                    y+=55
                    pending.extend(parents)
        else:
            lineage=lab.telemetry.ancestry(o).split(' > ')
            for depth,identity in enumerate(reversed(lineage)):
                offset=min(depth*10,40)
                if depth:
                    pg.draw.line(screen,BORDER,(x+offset-6,y-6),(x+offset-6,y+7))
                    pg.draw.line(screen,BORDER,(x+offset-6,y+7),(x+offset,y+7))
                t.draw(screen,identity if identity=='...' else f'#{identity}',(x+offset,y),14,TEXT,max_width=w-offset)
                y+=21
        children=[str(identity) for identity,parents in lab.telemetry.family.items() if o.id in parents]
        line('OBSERVED OFFSPRING IDS',', '.join(children[-12:]) or 'None in session history')
        heading('RECORDED LIFE EVENTS')
        events=[(tick,message) for tick,identity,message in lab.organics.events if identity==o.id]
        if not events:
            t.draw(screen,'No events in the session buffer',(x,y),12,MUTED)
            y+=20
        for tick,message in events[-18:][::-1]:
            t.draw(screen,f'{tick:,}  /  {message}',(x,y),12,TEXT,max_width=w)
            y+=20
    lab.inspector_max_scroll=max(0,y-start-clip.h);screen.set_clip(None)
