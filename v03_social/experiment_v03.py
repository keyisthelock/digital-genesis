"""Reproducible small social-cognition screening, benchmarks, and held-out transfer."""
import argparse,copy,csv,hashlib,json,random,statistics,sys,time,tracemalloc
from pathlib import Path
from collections import deque,Counter
from social_sim import SocialSimulation,TREATMENTS,near
from world import World

ROOT=Path(__file__).resolve().parent
def write_csv(path,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=keys);w.writeheader();w.writerows(rows)
def component(world):
    remaining={p for p,t in world.tiles.items() if t not in ('water','hazard')};best=[]
    while remaining:
        p=min(remaining);remaining.remove(p);found=[p];queue=deque([p])
        while queue:
            x,y=queue.popleft()
            for q in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                if q in remaining:remaining.remove(q);found.append(q);queue.append(q)
        if len(found)>len(best):best=found
    return sorted(best)
def environment(seed,path,unseen=False):
    rng=random.Random(91000+seed)
    w=World.load(ROOT.parent/'results/v02_terrain.json',rng)
    if unseen:
        land=set();p=(30,20)
        while len(land)<900:
            land.add(p);dx,dy=rng.choice(((1,0),(-1,0),(0,1),(0,-1)))
            p=max(1,min(58,p[0]+dx)),max(1,min(38,p[1]+dy))
        w.tiles={q:'land' if q in land else 'water' for q in w.tiles}
        w.food={q:rng.uniform(8,25) for q in sorted(land) if rng.random()<.28}
        for q in w.food:w.tiles[q]='tree'
        w.fruit=sorted(land)[0];w.tiles[w.fruit]='fruit';w.food.pop(w.fruit,None)
        w.land=sorted(land)
    safe=component(w)
    anchor=max(safe,key=lambda p:sum(v for q,v in w.food.items() if near(p,q,2)))
    nursery=[p for p in safe if near(p,anchor,2)]
    spawns=[rng.choice(nursery) for _ in range(12)]
    w.save(path)
    return dict(seed=seed,terrain=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),spawns=spawns,unseen=unseen)
def relocate(w):
    old=set(w.food);safe=component(w)
    new=[p for p in safe if p not in old and p!=w.fruit]
    new.sort(key=lambda p:(-min(abs(p[0]-q[0])+abs(p[1]-q[1]) for q in old),p))
    if len(new)<len(old):
        new=sorted(p for p,t in w.tiles.items() if t not in ('water','hazard','fruit') and p not in old)
    assert len(new)>=len(old)
    amount=sum(w.food.values());w.food=dict(zip(new[:len(old)],w.food.values()))
    assert abs(sum(w.food.values())-amount)<1e-6
    return old
def pool_of(organisms):return [dict(body=copy.deepcopy(o.genome),neural=copy.deepcopy(o.brain.genetic) if o.brain else None) for o in organisms]

def run_case(output,env,treatment,modules,ticks,case=1,shuffle=False,pool=None,epoch='new',trace_memory=False):
    folder=output/f'case_{case}_seed_{env["seed"]}_{treatment}_shuffle_{int(shuffle)}_{epoch}'
    start_wall=time.perf_counter();start_cpu=time.process_time()
    if trace_memory:tracemalloc.start()
    sim=SocialSimulation(population=12,ticks=ticks,seed=env['seed'],output=folder,
        terrain=env['terrain'],resource_fraction=.35,max_lifespan=3000,max_population=24,maturity_age=100,
        modules=modules,treatment=treatment,shuffled=shuffle,cooperative=case==3,freeze=case==6,
        learning=case!=6,neural_pool=[p['neural'] for p in pool] if pool and pool[0]['neural'] else None,
        body_pool=[p['body'] for p in pool] if pool else None)
    for o,p in zip(sim.organisms,env['spawns']):o.position=tuple(p)
    initial=pool_of(sim.organisms);extinction=None;intervention=0;eligible=0;rejoined=0
    old_patches=set();failed=Counter();intake=[];pre_rate=None;recovery=None;last_good=False
    home=None;familiar_ids=set();formed=encounters=0
    prediction_before_change=[];prediction_after_change=[]
    try:
        for tick in range(1,ticks+1):
            sim.sense()
            if case==2 and tick==ticks//2+1:
                old_patches=relocate(sim.world)
                pre=intake[-min(100,len(intake)):];pre_rate=sum(a for a,n in pre)/max(1,sum(n for a,n in pre))
                intervention=1
            if case==4 and tick==min(80,ticks//3):
                focal=next((o for o in sim.organisms if o.id==1),None)
                if focal:
                    familiar_ids={i for i,p in focal.social.people.items() if p['bond']>=.15}
                    eligible=int(bool(familiar_ids));home=focal.position
                    safe=component(sim.world);focal.position=max(safe,key=lambda p:abs(p[0]-home[0])+abs(p[1]-home[1]))
                    intervention=1;sim.log_event(event='separation',organism=1,familiar_ids=sorted(familiar_ids),home=home,destination=focal.position)
            if case==4 and tick==min(140,2*ticks//3) and home is not None:
                focal=next((o for o in sim.organisms if o.id==1),None)
                if focal:
                    focal.position=home;sim.sense()
                    rejoined=int(bool(familiar_ids & {c[0] for c in focal.local_contacts}))
                    sim.log_event(event='reunion',organism=1,familiar_seen=rejoined)
            if case==5 and tick==min(100,ticks//2):
                target=next((o for o in sim.organisms if o.id==2),None)
                if target:
                    eligible=int(any(o.social.bond(target.id)>=.15 and near(o.position,target.position) for o in sim.organisms if o.id!=target.id))
                    target.health=0;intervention=1
                    sim.log_event(event='controlled_death',organism=2,bonded_observer_present=eligible)
            previous=sim.organisms[:]
            ages={o.id:(o.acquired,o.social.formed,o.social.encounters,o.position) for o in previous}
            stopped=sim.step()
            food=sum(o.acquired-ages[o.id][0] for o in previous)
            intake.append((food,len(previous)))
            for o in previous:
                formed+=o.social.formed-ages[o.id][1];encounters+=o.social.encounters-ages[o.id][2]
                if old_patches and o.position!=ages[o.id][3] and o.position in old_patches and sim.world.food.get(o.position,0)<=1:failed[o.id,o.position]+=1
            if old_patches and tick>ticks//2 and (tick-ticks//2)%100==0:
                window=intake[-100:];rate=sum(a for a,n in window)/max(1,sum(n for a,n in window))
                good=pre_rate is not None and pre_rate>0 and rate>=.9*pre_rate
                if good and last_good and recovery is None:recovery=tick-ticks//2
                last_good=good
            if stopped:
                if not sim.organisms:extinction=tick
                break
        late=pool_of(sim.organisms[-8:]) or list(sim.late_pool)
        m=sim.metrics();extra=sim.extra_metrics()
        social=[o.social for o in sim.organisms]
        pre,post=intake[:ticks//2],intake[ticks//2:]
        row=dict(case=case,seed=env['seed'],treatment=treatment,shuffled=int(shuffle),genome_epoch=epoch,
            modules=0 if treatment=='A_rule' else modules,ticks=sim.world.tick,survivors=m['living'],births=m['births'],
            deaths=m['deaths'],extinct=int(extinction is not None),extinction_tick=extinction,
            food=m['food_consumed'],lifespan=m['average_observed_lifespan'],fitness=m['average_fitness'],
            exploration=sim.archived_fitness*0, # overwritten from exact coverage accumulator below
            encounters=encounters,bond_threshold_crossings=formed,
            living_strong_bonds=extra['living_strong_bonds'],living_reciprocal_bonds=extra['living_reciprocal_bonds'],group_stability=extra['group_stability'],
            shares=extra.get('shares',0),energy_transferred=extra.get('energy_transferred',0),sharing_loss=extra.get('sharing_loss',0),
            hazard_ticks=extra.get('hazard_ticks',0),brain_energy=extra.get('brain_energy',0),
            neural_ops=extra.get('neural_ops',0),neural_decisions=extra.get('neural_decisions',0),module_utilization=extra['module_utilization'],
            complexity=extra.get('complexity_sum',0)/max(1,extra.get('neural_decisions',0)),
            prediction_mse=extra.get('prediction_squared_error',0)/extra['prediction_samples'] if extra.get('prediction_samples') else None,
            prediction_first50_mse=extra.get('prediction_first_error',0)/extra['prediction_first_samples'] if extra.get('prediction_first_samples') else None,
            prediction_later_mse=extra.get('prediction_later_error',0)/extra['prediction_later_samples'] if extra.get('prediction_later_samples') else None,
            learning_updates=extra.get('learning_updates',0),blocked_access=extra.get('blocked_food_access',0),
            isolation=extra.get('isolation_sum',0)/max(1,extra.get('isolation_samples',0)),
            death_observations=extra.get('death_observations',0),bonded_loss_events=extra.get('bonded_loss_events',0),
            intervention_applied=intervention,intervention_socially_eligible=eligible,reunion_familiar_seen=rejoined,
            repeated_failed_visits=sum(max(0,n-1) for n in failed.values()),recovery_ticks=recovery,
            food_per_tick_before=sum(a for a,n in pre)/max(1,sum(n for a,n in pre)),
            food_per_tick_after=sum(a for a,n in post)/sum(n for a,n in post) if post else None)
        row['exploration']=len(sim.coverage)/sum(t!='water' for t in sim.world.tiles.values())
        sim.finish_generation(reproduce=False)
        (folder/'v03_config.json').write_text(json.dumps(dict(case=case,seed=env['seed'],treatment=treatment,modules=modules,shuffle=shuffle,
            environment=env,population=12,max_population=24,ticks=ticks,brain_parameter_cost=.000002,brain_op_cost=.00001,
            learning=case!=6,freeze_genomes=case==6),indent=2))
        if case==1:
            (folder/'transfer_genomes.json').write_text(json.dumps(dict(early=initial,late=late),separators=(',',':')))
        return row,initial,late
    finally:
        sim.close()
        row_wall=time.perf_counter()-start_wall;row_cpu=time.process_time()-start_cpu
        if 'row' in locals():row.update(wall_seconds=row_wall,cpu_seconds=row_cpu)
        if trace_memory:
            _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
            if 'row' in locals():row['python_peak_mb']=peak/1024**2

def report(output,rows,summary,config):
    lines=['# Digital Genesis v0.3 - Social Mind prototype',
        f"Actual screening: {config['modules']} modules per neural organism; target 67 implemented. Seeds {config['seeds']}; up to {config['ticks']} ticks; {len(rows)} population runs. No archived files were modified.",
        '## Results (means across paired seeds)',
        '|Task|Treatment|Shuffled|Pool|Survivors|Births|Extinctions|Prediction MSE|Shares|Loss events|',
        '|---|---|---|---|---:|---:|---:|---:|---:|---:|']
    for s in summary:
        pred=f"{s['prediction_mse']:.4f}" if s['prediction_mse'] is not None else 'N/A'
        lines.append(f"|{s['case']}|{s['treatment']}|{s['shuffled']}|{s['genome_epoch']}|{s['survivors']:.2f}|{s['births']:.2f}|{s['extinctions']}|{pred}|{s['shares']:.1f}|{s['bonded_loss_events']:.1f}|")
    lines+=['','Task 1: familiar resources. Task 2: food relocation at midpoint. Task 3: food access requires two physically nearby organisms. Task 4: founder 1 moved away at tick 80 and returned at 140 if still alive. Task 5: founder 2 is killed at tick 100 if alive; only local witnesses with existing bonds receive a loss signal. Task 6: unseen connected land/food geometry, frozen recorded early/late genomes, no lifetime learning or mutation.',
        '## Paired comparisons: D minus controls (survivors, births)']
    for case in range(1,6):
        for control in TREATMENTS[:-1]:
            ds=[];bs=[]
            for seed in config['seeds']:
                p={r['treatment']:r for r in rows if r['case']==case and r['seed']==seed and not r['shuffled']}
                ds.append(p['D_social_evolving']['survivors']-p[control]['survivors']);bs.append(p['D_social_evolving']['births']-p[control]['births'])
            lines.append(f'- Task {case} vs {control}: survivor differences {ds}; birth differences {bs}.')
    lines+=['','## Social signal controls']
    for case in range(1,6):
        for treatment in TREATMENTS[2:]:
            diffs=[]
            for seed in config['seeds']:
                p={r['shuffled']:r for r in rows if r['case']==case and r['seed']==seed and r['treatment']==treatment}
                diffs.append(p[0]['survivors']-p[1]['survivors'])
            lines.append(f'- Task {case}, {treatment}: true minus shuffled survivor differences {diffs}.')
    lines+=['','## Held-out transfer: late minus early genomes']
    for treatment in TREATMENTS:
        ds=[];bs=[]
        for seed in config['seeds']:
            p={r['genome_epoch']:r for r in rows if r['case']==6 and r['seed']==seed and r['treatment']==treatment}
            ds.append(p['late']['survivors']-p['early']['survivors']);bs.append(p['late']['births']-p['early']['births'])
        lines.append(f'- {treatment}: survivors {ds}; births {bs}.')
    lines+=['','## Actual observed behaviour']
    for case in range(1,6):
        group=[r for r in rows if r['case']==case and not r['shuffled']]
        lines.append(f"- Task {case}: {sum(r['shares'] for r in group)} sharing actions; {sum(r['bond_threshold_crossings'] for r in group)} bond-threshold crossings; {sum(r['hazard_ticks'] for r in group)} damaging tile-ticks; {sum(r['repeated_failed_visits'] for r in group)} repeated empty old-food visits; {sum(r['bonded_loss_events'] for r in group)} observed bonded-loss events. Socially eligible interventions {sum(r['intervention_socially_eligible'] for r in group)}; applied {sum(r['intervention_applied'] for r in group)}.")
    windows=[]
    for path in sorted(output.glob('case_*/social_events.jsonl')):
        for line in path.read_text().splitlines():
            e=json.loads(line)
            if e['event']=='loss_behavior_window':
                def rate(key,window):return sum(v[key] for v in window)/len(window) if window else None
                windows.append(dict(trial=path.parent.name,observer=e['observer'],deceased=e['deceased'],tick=e['tick'],
                    before_n=len(e['before']),after_n=len(e['after']),censored=e['censored'],
                    move_before=rate('move',e['before']),move_after=rate('move',e['after']),
                    share_before=rate('share',e['before']),share_after=rate('share',e['after']),
                    hazard_before=rate('hazard',e['before']),hazard_after=rate('hazard',e['after'])))
    if windows:write_csv(output/'loss_behavior.csv',windows)
    else:(output/'loss_behavior.csv').write_text('trial,observer,deceased,tick,before_n,after_n,censored\n')
    complete=[w for w in windows if w['before_n']==20 and w['after_n']==20 and not w['censored']]
    lines.append(f"Loss behaviour: {len(windows)} logged windows, {len(complete)} complete 20-before/20-after windows. These are descriptive within-organism observations, with survival/selection confounding. See loss_behavior.csv and social_events.jsonl for individual evidence.")
    if complete:
        lines.append('Mean post-minus-pre action rates: '+', '.join(f"{key} {statistics.mean(w[key+'_after']-w[key+'_before'] for w in complete):+.4f}" for key in ('move','share','hazard'))+'.')
    lines+=['','## Mechanisms and limits',
        '- Real sparse tanh recurrent networks, randomly initialized. Three context-selected modules per decision. Neural multiply-add costs and active indices are recorded; feature construction, sensing, logging and Python overhead are included in CPU measurements but not neural operation counts.',
        '- Capacity bounds: 8/16/32/67 modules; 2-4 neurons/module; at most 12 input connections/module; one recurrent self-connection/neuron and nine readouts (eight actions plus food predictor). 67 groups: 15 survival, 12 memory, 12 exploration, 18 social, 10 coordination. Genetic weights are deep copies; lifetime updates never enter offspring. Weight, connection, neuron, learning-rate, memory-decay and social-gain mutation are bounded. Lifetime learning uses a local one-step policy-gradient-style rule and food prediction error, without backpropagation through recurrent time.',
        '- Simulated brain cost: 0.000002 per stored complexity unit plus 0.00001 per active neural operation each decision. All neural sizes use the same maximum 168 neural operations per decision. Sizes were benchmarked under the same 12-founder, 24-cap, 100-tick task; full screening uses the reported size only. Rule A has no artificial brain cost and is the copied v0.2 ordinary rule policy, rerun under these matched initial conditions. It is not a reuse of six-hour results as if they were matched v0.3 trials.',
        '- Sharing transfers up to 3 energy at an additional 0.2 energy loss. Repeated local encounters weakly increase familiarity; observed help increases numerical bonds, observed food competition reduces them. These update rules and the cooperative food gate are designed mechanisms, not evolved discoveries. No parent bond is assigned automatically. Local recognition is capped at eight contacts/tick, relationship memory at 32 people, group signatures at eight, food associations at 64, working memory at eight, and recent loss events at eight.',
        '- Loss is triggered only for locally observed deaths with bond >=0.15; bounded at one and multiplied by 0.985 each living tick. The neural policy receives this signal and may ignore it. Loss locations are historical observations. No emotional dialogue or subjective state is claimed.',
        '- The shuffled controls permute identity-to-outcome associations within the currently sensed neighborhood and replay historical isolation/loss/group signals from a bounded own-history buffer. With zero or one neighbor they are weak controls. Physical interactions and actual costs remain real. B removes social inputs, social activation, sharing choices and relationship updates; B therefore tests a social-system ablation, not only removal of a signal.',
        '- The new memory system decays confidence over time, replaces stale associations after negative evidence, and separates eight working locations from 64 longer-term associations. First-50 versus later prediction MSE is exposure-dependent and cannot by itself demonstrate learning. The screening does not include a neural learning-off ablation; transfer freezes learning but also changes terrain. No causal lifetime-learning advantage is established.',
        '- Founder spawns are clustered near food to permit encounters. Treatment pairs share exact terrain, spawns and initial neural genotypes; behavioral RNG paths diverge after different decisions. C disables genetic mutation of neural and old scalar traits; learned parameters remain plastic. D and B retain the original energy-funded reproduction. No fitness-weighted generation replacement is added.',
        '- Social interventions use preselected founder IDs and fixed times. Extinction or no existing bond can make the intended task unavailable. Such cases are counted, never assigned fabricated bonds. Before/after loss and separation results are conditional on opportunity and survival; the intervention is not a complete randomized causal estimate.',
        '- Held-out pools are actual founder or last living/recently dead genomes from Task 1, not champions. Up to eight late genomes are repeated round-robin. All lifetime state resets and all mutation/learning is disabled for transfer. Survivor and lineage sampling bias remains. Unseen worlds change connected land/food geometry and omit hazards; transfer to new hazard ecology remains untested.',
        '- Relationship reciprocity and group stability columns describe living organisms at endpoint, creating survivor bias. Bond-threshold crossings can count re-formation. Action counts record selections that may be preempted by starvation. Journals contain aggregate actions, individual cognitive summaries, sharing events and loss windows, not full position trajectories for all organisms.',
        '- This prototype does not infer subjective love, belonging, grief, consciousness, or intelligence. Three seeds and 1500 ticks are a screening study. Benefits require repeatable survival/reproduction and held-out evidence against relevant controls; higher fitness, clusters, and larger brains alone are insufficient.',
        '', '## Performance',
        f"Screen CPU seconds total {sum(r['cpu_seconds'] for r in rows):.3f}; wall seconds summed across runs {sum(r['wall_seconds'] for r in rows):.3f}. Benchmark Python allocation peaks and CPU times are in benchmark.csv; these are not total process RAM. All runs are sequential and CPU-only.",
        '', '## Next experiment',
        'Add matched neural learning-off and time-shuffled nonsocial-memory controls; preregister a primary survival/offspring endpoint; extend paired seeds only after populations survive long enough to reproduce and experience the intervention. Assess trained versus untrained policies on multiple held-out land/hazard maps, and test costly sharing with/without the cooperative gate. Do not tune on the final held-out maps.',
        '', '## Commands',
        'Visual: `python run_v03.py --modules 67 --treatment D_social_evolving --speed 20`',
        'Headless: `python run_v03.py --headless --modules 67 --ticks 1500 --output results/headless_new`',
        '10-seed expansion (separate output): `python experiment_v03.py --seeds 10 --ticks 1500 --modules 67 --output experiments/social_10seeds`',
        'Capacity controls: use `--modules 8`, `16`, or `32` with the same seeds/ticks/output budget. No expansion starts automatically.']
    (output/'REPORT.md').write_text('\n\n'.join(lines[:2])+'\n'+'\n'.join(lines[2:]),encoding='utf-8')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--seeds',type=int,default=3)
    p.add_argument('--ticks',type=int,default=1500);p.add_argument('--modules',type=int,choices=(8,16,32,67),default=67)
    p.add_argument('--output',type=Path,default=ROOT/'experiments/social_screen')
    args=p.parse_args()
    if args.seeds<1 or args.seeds>10 or args.ticks<150:p.error('seeds 1..10; ticks >=150')
    if args.output.exists() and any(args.output.iterdir()):p.error('output must be empty')
    args.output.mkdir(parents=True,exist_ok=True)
    envs=[environment(seed,args.output/f'terrain_{seed}.json') for seed in range(args.seeds)]
    unseen=[environment(seed,args.output/f'unseen_{seed}.json',True) for seed in range(args.seeds)]
    benchmark=[]
    for count in (8,16,32,67):
        row,_,_=run_case(args.output/'benchmark',envs[0],'D_social_evolving',count,100,trace_memory=True,epoch=str(count))
        benchmark.append(dict(modules=count,cpu_seconds=row['cpu_seconds'],wall_seconds=row['wall_seconds'],python_peak_mb=row['python_peak_mb'],
            neural_ops=row['neural_ops'],ticks=row['ticks'],decision_budget=168))
    write_csv(args.output/'benchmark.csv',benchmark)
    desired=next(r for r in benchmark if r['modules']==args.modules)
    actual=8 if desired['cpu_seconds']/100>.1 or desired['python_peak_mb']>128 else args.modules
    config=dict(version='0.3',status='running',seeds=list(range(args.seeds)),ticks=args.ticks,target_modules=67,requested_modules=args.modules,modules=actual,
        module_budget='3 active; 168 max neural multiply-add units/decision',fallback_reason='100ms/tick or 128MB traced Python peak exceeded' if actual!=args.modules else None,
        treatments=list(TREATMENTS),shuffled_controls=list(TREATMENTS[2:]),environments=envs,unseen=unseen,
        population=12,cap=24,resource_fraction=.35,maturity=100,lifespan=3000,brain_parameter_cost=.000002,brain_op_cost=.00001,
        inherited_neural_mutation_rate=.12,old_scalar_mutation_rate=.2,python=sys.version)
    (args.output/'experiment_config.json').write_text(json.dumps(config,indent=2))
    rows=[]
    for case in range(1,6):
        for env in envs:
            for treatment in TREATMENTS:
                for shuffled in ((False,True) if treatment in TREATMENTS[2:] else (False,)):
                    row,early,late=run_case(args.output,env,treatment,actual,args.ticks,case,shuffled)
                    rows.append(row)
                    if case==1 and not shuffled:
                        for epoch,pool in (('early',early),('late',late)):
                            if not pool:raise ValueError('missing actual transfer pool')
                            transfer,_,_=run_case(args.output,unseen[env['seed']],treatment,actual,args.ticks,6,pool=pool,epoch=epoch)
                            rows.append(transfer)
            write_csv(args.output/'results.csv',rows)
            print(f'Task {case}, seed {env["seed"]}: {len(rows)} runs complete',flush=True)
    summary=[]
    for key in sorted({(r['case'],r['treatment'],r['shuffled'],r['genome_epoch']) for r in rows}):
        group=[r for r in rows if (r['case'],r['treatment'],r['shuffled'],r['genome_epoch'])==key]
        s=dict(zip(('case','treatment','shuffled','genome_epoch'),key));s['runs']=len(group);s['extinctions']=sum(r['extinct'] for r in group)
        for metric in ('survivors','births','food','fitness','exploration','prediction_mse','shares','bonded_loss_events','neural_ops','brain_energy','complexity'):
            values=[r[metric] for r in group if r[metric] is not None];s[metric]=statistics.mean(values) if values else None
        summary.append(s)
    write_csv(args.output/'summary.csv',summary)
    assert len(rows)==args.seeds*38 and all(12+r['births']-r['deaths']==r['survivors'] for r in rows)
    assert len(list(csv.DictReader((args.output/'results.csv').open())))==len(rows)
    for env in envs+unseen:assert hashlib.sha256(Path(env['terrain']).read_bytes()).hexdigest()==env['sha256']
    config.update(status='complete',runs=len(rows));(args.output/'experiment_config.json').write_text(json.dumps(config,indent=2))
    report(args.output,rows,summary,config)
    print(json.dumps(dict(status='complete',modules=actual,runs=len(rows),cpu_seconds=sum(r['cpu_seconds'] for r in rows))))

if __name__=='__main__':main()
