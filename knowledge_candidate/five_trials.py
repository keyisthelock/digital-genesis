"""Five offline screening trials. Reuses the existing policies and lifetime mechanics.

python five_trials.py                  # seeds 0,1,2; 3000 ticks
python five_trials.py --seeds 10 --output experiments/five_trials_10seeds
"""
import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import sys
from collections import Counter, deque
from pathlib import Path
from evolution import Simulation
from world import World

ROOT = Path(__file__).resolve().parent
TREATMENTS = ('cautious_knowledge', 'evolving', 'evolving_without_knowledge', 'baseline')
ARCHIVE = ROOT/'results/updated_overnight'


def neighbors(p):
    x, y = p
    return ((x-1,y),(x+1,y),(x,y-1),(x,y+1))


def largest_safe(world):
    remaining = {p for p,t in world.tiles.items() if t not in ('water','hazard')}
    best = set()
    while remaining:
        start = min(remaining)
        component, queue = {start}, deque([start])
        remaining.remove(start)
        while queue:
            for p in neighbors(queue.popleft()):
                if p in remaining:
                    remaining.remove(p)
                    component.add(p)
                    queue.append(p)
        if len(component) > len(best):
            best = component
    return sorted(best)


def distance(a,b):
    return abs(a[0]-b[0])+abs(a[1]-b[1])


def prepare_world(case, seed):
    rng = random.Random(88000+seed)
    world = World.load(ROOT.parent/'results/v02_terrain.json', rng)
    if case == 4:
        # One connected landmass from a seeded random walk, not new brain mechanics.
        land, p = set(), (30,20)
        while len(land) < 900:
            x,y = p
            land.update((xx,yy) for xx in range(max(1,x-1),min(59,x+2))
                        for yy in range(max(1,y-1),min(39,y+2)))
            dx,dy = rng.choice(((-1,0),(1,0),(0,-1),(0,1)))
            p = max(2,min(57,x+dx)), max(2,min(37,y+dy))
        world.tiles = {p: ('land' if p in land else 'water') for p in world.tiles}
        world.food = {p:rng.uniform(8,25) for p in sorted(land) if rng.random()<.28}
        for p in world.food:
            world.tiles[p] = 'tree'
        world.fruit = sorted(land)[0]
        world.tiles[world.fruit] = 'fruit'
        world.food.pop(world.fruit,None)
        world.land = sorted(land)
    if case == 2:
        hazards = [p for p,t in world.tiles.items() if t=='hazard']
        safe = largest_safe(world)
        near = [p for p in safe if p != world.fruit and min(distance(p,h) for h in hazards)<=2]
        far = [p for p in world.land if p not in set(near) and p != world.fruit]
        rng.shuffle(near)
        rng.shuffle(far)
        n = len(world.food)
        near = near[:min(len(near),int(.7*n))]
        far = far[:n-len(near)]
        total = sum(world.food.values())
        world.food = {p:total*.7/len(near) for p in near}
        world.food.update({p:total*.3/len(far) for p in far})
        # Safe food adjacent to hazards is in a connected hazard-free component.
        assert set(near) <= set(safe)
        assert math.isclose(sum(world.food.values()),total,rel_tol=1e-12)
    safe = largest_safe(world)
    spawns = [rng.choice(safe) for _ in range(30)]
    if case == 5:
        anchor = rng.choice(safe)
        nursery = [p for p in safe if distance(p,anchor)<=3]
        spawns = [rng.choice(nursery) for _ in range(30)]
        gate = max(safe,key=lambda p:(min(distance(p,s) for s in spawns),p))
        assert min(distance(gate,s) for s in spawns)>=10
        world.tiles[world.fruit] = 'land'
        world.fruit = gate
        world.tiles[gate] = 'fruit'
        displaced = [(p,v) for p,v in world.food.items() if distance(p,gate)<=3]
        destinations = [p for p in safe if p not in world.food and distance(p,gate)>3]
        assert len(destinations)>=len(displaced)
        for (p,v),q in zip(displaced,destinations):
            del world.food[p]
            world.food[q] = v
        assert gate not in world.food
    return world, spawns


def relocate_food(world):
    old = set(world.food)
    safe = [p for p,t in world.tiles.items() if t not in ('hazard','water','fruit') and p not in old]
    safe.sort(key=lambda p:(-min(distance(p,q) for q in old),p))
    assert len(safe)>=len(old)
    amounts = list(world.food.values())
    total = sum(amounts)
    world.food = dict(zip(safe[:len(amounts)],amounts))
    assert not old.intersection(world.food)
    assert math.isclose(sum(world.food.values()),total,rel_tol=1e-12)
    return old


class ObservedPolicy:
    def __init__(self, policy, memory):
        self.policy, self.memory, self.actions = policy, memory, {}

    def choose(self,o,observations,rng):
        if self.memory:
            result = self.policy.choose(o,observations,rng)
        else:
            # Ablate decision access, retain private coverage for fitness/logging.
            memory, visited = o.memory, o.visited
            o.memory, o.visited = {}, set()
            try:
                result = self.policy.choose(o,observations,rng)
            finally:
                o.memory, o.visited = memory, visited
        self.actions[o.id] = result[0]
        return result


class TrialSimulation(Simulation):
    def __init__(self,*args,genomes=None,**kwargs):
        self.genomes = genomes
        super().__init__(*args,**kwargs)

    def birth(self,parent=None):
        o = super().birth(parent)
        if self.genomes:
            # Case 4 freezes each evaluated pool, including the baseline arm.
            source = (self.genomes[(o.id-1)%len(self.genomes)] if parent is None
                      else parent.genome)
            o.genome = dict(source)
            if o.knowledge:
                o.knowledge.ambition = o.genome.get('ambition',.8)
        return o


def archived_genomes(seed,mode,epoch):
    folder = ARCHIVE/f'seed_{seed}_{mode}'
    path = folder/('ancestry.jsonl' if epoch=='early' else 'births.jsonl')
    if not path.exists():
        return None, dict(reason='missing archived genome file',source=str(path))
    found = {}
    if epoch=='early':
        with path.open() as stream:
            for line in stream:
                r = json.loads(line)
                if r['parent_id'] is None:
                    found[r['id']] = r
                if len(found)==30:
                    break
        records = [found[k] for k in sorted(found)]
    else:
        with path.open() as stream:
            records = list(deque((json.loads(line) for line in stream),maxlen=30))
    if not records:
        return None, dict(reason='no recorded genomes',source=str(path))
    return [r['genome'] for r in records], dict(source=str(path),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        ids=[r['id'] for r in records], lineage_generations=[r['generation'] for r in records],
        genomes=[r['genome'] for r in records])


def run_trial(case,seed,mode,terrain,spawns,output,ticks=3000,memory=True,epoch='founder',genomes=None):
    sim = TrialSimulation(population=30,ticks=ticks,seed=seed,output=output,
        max_lifespan=3000,lifetime=True,baseline=mode=='baseline',
        resource_fraction=.12 if case==1 else .35,max_population=100,maturity_age=100,
        terrain=terrain,knowledge=mode in ('cautious_knowledge','evolving'),
        knowledge_variant='cautious' if mode=='cautious_knowledge' else 'original',
        mutation_rate=0 if case==4 else .2,genomes=genomes)
    for o,p in zip(sim.organisms,spawns):
        o.position = tuple(p)
    policy = ObservedPolicy(sim.policy,memory)
    sim.policy = policy
    counters = Counter()
    covered, fruit_visitors, discovered_at = set(),set(),{}
    old_food, failures = set(),Counter()
    action_counts, intake = Counter(),[]
    window = min(500,max(10,ticks//6))
    pre_rate, recovery = None,None
    previous_window_recovered = False
    changed = False
    extinction = None
    try:
        for tick in range(1,ticks+1):
            if case==3 and tick==ticks//2+1:
                pre = intake[-window:]
                pre_rate = sum(x[0] for x in pre)/max(1,sum(x[1] for x in pre))
                old_food = relocate_food(sim.world)
                changed = True
            before = [(o,o.position,o.energy,o.health,o.acquired,o.age,o.offspring,
                       o.discovered,dict(o.memory)) for o in sim.organisms]
            policy.actions.clear()
            sim.step()
            tick_food = 0
            for o,p,energy,health,acquired,age,kids,discovered,mem in before:
                action = policy.actions.get(o.id,'none')
                action_counts[action] += 1
                amount = o.acquired-acquired
                tick_food += amount
                basal = .14+.08*(1-sim.world.daylight)+.04*(1-o.growth)
                executed = energy-basal>0 and health>0
                action_cost = (.32 if action=='move' else .2 if action=='investigate' else 0) if executed else 0
                counters['energy_spent'] += basal+action_cost+40*(o.offspring-kids)
                counters['reproductive_energy_debit'] += 40*(o.offspring-kids)
                counters['food_acquired'] += amount
                counters['damage'] += max(0,health-o.health)
                if health>o.health:
                    counters['hazard_encounters'] += 1
                    counters['hazard_first_half' if tick<=ticks//2 else 'hazard_second_half'] += 1
                moved = o.position != p
                counters['moves'] += moved
                counters['moves_first_half' if tick<=ticks//2 else 'moves_second_half'] += moved
                counters['exploration_distance'] += distance(p,o.position)
                covered.add(o.position)
                if moved and sim.world.tiles[o.position]=='hazard':
                    counters['hazard_entries'] += 1
                    counters['known_hazard_entries'] += mem.get(o.position,(0,0))[1]>0
                if not o.alive:
                    counters['death_'+str(o.death_cause)] += 1
                    counters['deaths_within_100_ticks_of_discovery'] += o.id in discovered_at and tick-discovered_at[o.id]<=100
                if changed and moved and o.position in old_food and sim.world.food.get(o.position,0)<=1:
                    key = o.id,o.position
                    failures[key] += 1
                    counters['empty_old_patch_visits'] += 1
                    counters['repeated_failed_visits'] += failures[key]>1
                    counters['stale_memory_visits'] += mem.get(o.position,(0,0))[0]>2
                if o.discovered and not discovered:
                    discovered_at[o.id] = tick
                if o.position==sim.world.fruit and moved:
                    counters['gateway_entries'] += 1
                    counters['gateway_repeat_entries'] += o.id in fruit_visitors
                    fruit_visitors.add(o.id)
            intake.append((tick_food,len(before)))
            if case==3 and changed and tick>=ticks//2+window and (tick-ticks//2)%window==0:
                recent = intake[-window:]
                rate = sum(x[0] for x in recent)/max(1,sum(x[1] for x in recent))
                recovered = pre_rate is not None and pre_rate>0 and rate>=.9*pre_rate
                if recovered and previous_window_recovered and recovery is None:
                    recovery = tick-ticks//2
                previous_window_recovered = recovered
            if not sim.organisms:
                extinction = tick
                break
        metrics = sim.metrics()
        half = ticks//2
        pre_intake,post_intake = intake[:half],intake[half:]
        result = dict(case=case,seed=seed,treatment=mode,memory='enabled' if memory else 'disabled',
            genome_epoch=epoch,status='complete',ticks=sim.world.tick,survivors=len(sim.organisms),
            extinct=int(extinction is not None),extinction_tick=extinction,births=sim.total_births,
            mean_observed_lifespan=metrics['average_observed_lifespan'],
            food_acquired=counters['food_acquired'],energy_spent=counters['energy_spent'],
            reproductive_energy_debit=counters['reproductive_energy_debit'],
            hazard_encounters=counters['hazard_encounters'],hazard_entries=counters['hazard_entries'],
            known_hazard_entries=counters['known_hazard_entries'],damage=counters['damage'],
            damage_deaths=counters['death_damage'],starvation_deaths=counters['death_starvation'],
            hazard_rate_first_half=counters['hazard_first_half']/max(1,counters['moves_first_half']),
            hazard_rate_second_half=counters['hazard_second_half']/max(1,counters['moves_second_half']),
            exploration_coverage=len(covered)/len([t for t in sim.world.tiles.values() if t!='water']),
            exploration_distance=counters['exploration_distance'],fitness=metrics['average_fitness'],
            food_changed=int(changed),food_before=sum(x[0] for x in pre_intake),food_after=sum(x[0] for x in post_intake),
            intake_per_organism_tick_before=sum(x[0] for x in pre_intake)/max(1,sum(x[1] for x in pre_intake)),
            intake_per_organism_tick_after=sum(x[0] for x in post_intake)/max(1,sum(x[1] for x in post_intake)) if post_intake else None,
            recovery_ticks=recovery,empty_old_patch_visits=counters['empty_old_patch_visits'],
            repeated_failed_visits=counters['repeated_failed_visits'],stale_memory_visits=counters['stale_memory_visits'],
            first_discovery_tick=min(discovered_at.values()) if discovered_at else None,
            discoverers=len(discovered_at),gateway_entries=counters['gateway_entries'],
            gateway_repeat_entries=counters['gateway_repeat_entries'],
            deaths_within_100_ticks_of_discovery=counters['deaths_within_100_ticks_of_discovery'])
        for o in sim.organisms:
            sim.record(o)
        sim.finish_generation(reproduce=False)
        (Path(output)/'actions.json').write_text(json.dumps(action_counts,sort_keys=True))
        return result
    finally:
        sim.close()


def write_csv(path,rows):
    with path.open('w',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds',type=int,default=3)
    parser.add_argument('--ticks',type=int,default=3000)
    parser.add_argument('--output',type=Path,default=ROOT/'experiments/five_trials')
    args = parser.parse_args()
    if not 1<=args.seeds<=10 or args.ticks<20:
        parser.error('seeds must be 1..10; ticks >=20')
    if args.output.exists() and (args.output/'results.csv').exists():
        # Resume the requested screening in place; preserve completed rows and logs.
        existing = list(csv.DictReader((args.output/'results.csv').open(encoding='utf-8')))
        integer_fields={'case','seed','ticks','survivors','extinct','extinction_tick','births','hazard_encounters',
            'hazard_entries','known_hazard_entries','damage','damage_deaths','starvation_deaths','food_changed',
            'recovery_ticks','empty_old_patch_visits','repeated_failed_visits','stale_memory_visits',
            'first_discovery_tick','discoverers','gateway_entries','gateway_repeat_entries',
            'deaths_within_100_ticks_of_discovery'}
        for row in existing:
            for key,value in tuple(row.items()):
                if value=='': row[key]=None
                elif key in integer_fields: row[key]=int(value)
                elif key not in {'treatment','memory','genome_epoch','status'}: row[key]=float(value)
    else:
        existing = []
    args.output.mkdir(parents=True,exist_ok=True)
    config = dict(seeds=list(range(args.seeds)),ticks=args.ticks,population=30,max_population=100,
        lifespan=3000,maturity=100,mutation_rate=.2,mutation_strength=.25,
        terrain_seeds='88000 + paired seed',treatments=list(TREATMENTS),
        resource_fraction='0.12 in case 1; 0.35 otherwise',environments=[],genome_sources={},
        memory_ablation='decision access to episodic locations/visited set removed; pain/local sensing retained',
        python=sys.version,status='running')
    config_path=args.output/'experiment_config.json'
    if config_path.exists():
        old_config=json.loads(config_path.read_text(encoding='utf-8'))
        config['environments']=old_config.get('environments',[])
        config['genome_sources']=old_config.get('genome_sources',{})
    config_path.write_text(json.dumps(config,indent=2))
    rows=list(existing)
    completed={(int(r['case']),int(r['seed']),r['treatment'],r['memory'],r['genome_epoch']) for r in existing}
    for case in range(1,6):
        for seed in range(args.seeds):
            world,spawns = prepare_world(case,seed)
            terrain = args.output/f'case_{case}_seed_{seed}_terrain.json'
            world.save(terrain)
            environment=dict(case=case,seed=seed,path=terrain.name,
                sha256=hashlib.sha256(terrain.read_bytes()).hexdigest(),spawns=spawns,
                initial_food_unscaled=sum(world.food.values()),patches=len(world.food),
                gateway=world.fruit)
            config['environments']=[e for e in config['environments'] if (e['case'],e['seed'])!=(case,seed)]
            config['environments'].append(environment)
            for mode in TREATMENTS:
                for epoch in (('early','late') if case==4 else ('founder',)):
                    pool=None
                    if case==4:
                        pool,provenance=archived_genomes(seed,mode,epoch)
                        config['genome_sources'][f'{seed}_{mode}_{epoch}']=provenance
                        if pool is None:
                            print('SKIPPED missing genomes',seed,mode,epoch,flush=True)
                            continue
                    for memory in ((True,False) if case in (2,3) and mode in ('cautious_knowledge','evolving') else (True,)):
                        key=(case,seed,mode,'enabled' if memory else 'disabled',epoch)
                        if key in completed:
                            continue
                        output = args.output/f'case_{case}_seed_{seed}_{mode}_{epoch}_memory_{int(memory)}'
                        rows.append(run_trial(case,seed,mode,terrain,spawns,output,args.ticks,memory,epoch,pool))
                        completed.add(key)
            write_csv(args.output/'results.csv',rows)
            (args.output/'experiment_config.json').write_text(json.dumps(config,indent=2))
            print(f'Case {case} seed {seed}: completed ({len(rows)} trials)',flush=True)
    summaries=[]
    keys=sorted({(r['case'],r['treatment'],r['memory'],r['genome_epoch']) for r in rows})
    for case,mode,memory,epoch in keys:
        group=[r for r in rows if (r['case'],r['treatment'],r['memory'],r['genome_epoch'])==(case,mode,memory,epoch)]
        s=dict(case=case,treatment=mode,memory=memory,genome_epoch=epoch,trials=len(group),
            extinctions=sum(r['extinct'] for r in group))
        for metric in ('survivors','births','mean_observed_lifespan','food_acquired','energy_spent',
                       'hazard_encounters','damage','damage_deaths','exploration_coverage','fitness',
                       'food_before','food_after','recovery_ticks','repeated_failed_visits','discoverers','gateway_repeat_entries'):
            values=[r[metric] for r in group if r[metric] is not None]
            s['mean_'+metric]=statistics.mean(values) if values else None
        summaries.append(s)
    write_csv(args.output/'summary.csv',summaries)
    config['status']='complete'
    config['trial_count']=len(rows)
    (args.output/'experiment_config.json').write_text(json.dumps(config,indent=2))
    write_report(args.output,rows,summaries,config)
    # Mechanical consistency checks on the written, parseable CSV.
    loaded=list(csv.DictReader((args.output/'results.csv').open()))
    assert len(loaded)==len(rows) and all(0<=int(r['survivors'])<=100 for r in loaded)
    assert all(r['ticks']<=args.ticks and 30+r['births']-r['survivors']>=0 for r in rows)


def write_report(output,rows,summaries,config):
    text=['# Five experimental trials - screening report',
        f"Seeds {config['seeds']}; up to {config['ticks']} ticks; {len(rows)} independent trials. No archived data was changed.",
        'Means below are across paired seeds, not statistically conclusive. Fitness is secondary.',
        '| Case | Treatment | Memory | Genome pool | Survivors | Births | Extinctions | Food | Energy spent | Hazards | Coverage | Fitness |',
        '|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for s in summaries:
        text.append(f"| {s['case']} | {s['treatment']} | {s['memory']} | {s['genome_epoch']} | {s['mean_survivors']:.2f} | {s['mean_births']:.2f} | {s['extinctions']}/{s['trials']} | {s['mean_food_acquired']:.1f} | {s['mean_energy_spent']:.1f} | {s['mean_hazard_encounters']:.1f} | {s['mean_exploration_coverage']:.1%} | {s['mean_fitness']:.2f} |")
    text += ['','## Paired survival comparisons','Differences are cautious knowledge minus each control at the same seed and genome epoch.']
    for case in range(1,6):
        for epoch in (('early','late') if case==4 else ('founder',)):
            for control in TREATMENTS[1:]:
                diffs=[]
                for seed in config['seeds']:
                    pair={r['treatment']:r for r in rows if r['case']==case and r['seed']==seed and r['memory']=='enabled' and r['genome_epoch']==epoch}
                    if 'cautious_knowledge' in pair and control in pair:
                        diffs.append(pair['cautious_knowledge']['survivors']-pair[control]['survivors'])
                if diffs:
                    text.append(f'- Case {case}, {epoch}, versus {control}: mean difference {statistics.mean(diffs):+.2f}; individual differences {diffs}.')
    text += ['','## Scenario outcomes']
    for case in range(1,6):
        group=[r for r in rows if r['case']==case and r['memory']=='enabled']
        text.append(f'\n### Case {case}')
        if case==1:
            text.append(f"Famine: {sum(r['extinct'] for r in group)}/{len(group)} populations went extinct; {sum(r['starvation_deaths'] for r in group)} starvation deaths. Low food and regeneration were both scaled to 0.12. There is no normal-food counterfactual in this screen, so scarcity adaptation is not established.")
        if case==2:
            text.append(f"Danger: {sum(r['hazard_encounters'] for r in group)} harmful tile-ticks, {sum(r['damage_deaths'] for r in group)} damage deaths, {sum(r['known_hazard_entries'] for r in group)} entries into remembered harmful locations. Early/late hazard-per-move rates are in results.csv. Food amount and patch count were preserved; 70% of food amount was concentrated within two tiles of hazards on connected safe land. Safe routes require no hazard crossing. Existing visible-hazard penalties are programmed avoidance, not proof of acquired learning.")
        if case==3:
            changed=[r for r in group if r['food_changed']]
            recovered=[r['recovery_ticks'] for r in changed if r['recovery_ticks'] is not None]
            text.append(f"Changing world: {len(changed)}/{len(group)} populations survived to relocation; {len(recovered)} met the recovery rule. Recovery times: {recovered}. Rule: food acquired per organism-tick reaches 90% of the last pre-change window in two consecutive non-overlapping post-change windows. Window size is min(500, ticks/6). No recovery is blank, not zero. Resources and patch count are exactly preserved at relocation; renewable capacities are unchanged. Empty old-patch visits: {sum(r['empty_old_patch_visits'] for r in changed)}; repeated failed visits: {sum(r['repeated_failed_visits'] for r in changed)}.")
        if case==4:
            for mode in TREATMENTS:
                diffs=[]
                for seed in config['seeds']:
                    p={r['genome_epoch']:r for r in group if r['seed']==seed and r['treatment']==mode}
                    if 'early' in p and 'late' in p:
                        diffs.append(p['late']['survivors']-p['early']['survivors'])
                text.append(f'- {mode}: paired late-minus-early survivor differences {diffs}.')
            text.append('Early pools are archived founders; late pools are the last up to 30 actual birth records per treatment/seed, not selected champions. Sources, IDs, lineage depths, file hashes and exact genomes are saved in experiment_config.json. Pools smaller than 30 are replicated round-robin to form equal-sized founder populations. All mutation is disabled in this case. Ecological differential reproduction still occurs; no fitness-weighted selection is added. These pools are subject to survivor/lineage sampling bias and are not representative of all late organisms. Unseen seeded landmass configurations are connected; hazards are absent here to isolate transfer to new land and food geometry.')
        if case==5:
            first=[r['first_discovery_tick'] for r in group if r['first_discovery_tick'] is not None]
            text.append(f"Gateway: {sum(r['discoverers'] for r in group)} individual discoverers, {sum(r['gateway_repeat_entries'] for r in group)} repeat entries; first discovery ticks {first}. Deaths within 100 ticks of discovery: {sum(r['deaths_within_100_ticks_of_discovery'] for r in group)}. This is an association, not a causal survival effect. The gateway is on connected land, at least ten tiles from initial clustered spawns, with no food within three tiles. Food removed around it was relocated without changing amount or patch count. Distance from ordinary food routes is approximated by this food-free buffer; actual future routes cannot be guaranteed. Brains receive only their existing local observation; no coordinates or reward are added. No network access exists.")
    text += ['','## Memory ablations']
    for case in (2,3):
        for mode in TREATMENTS[:2]:
            differences=[]
            for seed in config['seeds']:
                pair={r['memory']:r for r in rows if r['case']==case and r['seed']==seed and r['treatment']==mode}
                differences.append(pair['enabled']['survivors']-pair['disabled']['survivors'])
            text.append(f'- Case {case}, {mode}: memory-enabled minus disabled survivors {differences}.')
    text += ['','## Interpretation, unusual behaviours and limitations',
        '- Survival, births, extinction timing, acquired food, energy costs and actual actions are observed. No narrative about presumed feelings is inferred. Adaptation requires repeatable survival/reproduction or held-out transfer advantages, not fitness alone.',
        '- Visible hazard avoidance and local food seeking are programmed policy responses. Memory ablations remove decision access to episodic locations and visited places; immediate pain, local hazard sensing and internal logging remain. This tests decision memory, not a completely memory-free organism.',
        '- Hazard encounters count damaging tile-ticks, including repeated damage while stationary; hazard entries count movements onto hazards. Hazard/move rates may exceed one when resting in danger. Zero moves uses denominator one. Coverage is the union of visited passable tiles divided by all nonwater tiles; disconnected continents and initial placement constrain its ceiling.',
        '- Energy spent includes basal/action costs and the full 40-unit parent reproduction debit, including the 30 units transferred to a child; it is not purely dissipated energy. Raw food collection can include energy-cap waste. Starting energy is an endowment. Health can fall below zero on the last hit; measured damage records the full hit.',
        '- Existing policy danger memory uses a decaying pain signal and has no timestamp-based food forgetting. Outdated-location visits are measured but do not prove erroneous beliefs. Parents and children can overlap; spatial crowding has no cost. These inherited simplifications were not rewritten.',
        '- There are only three paired seeds and one 3000-tick screen. Extinction shortens exposure; total damage/intake comparisons are not exposure-adjusted by themselves. The live resource field persists; births change sampling. Observed lifespan is right-censored. Paired means are descriptive; no significance or intelligence claims are made.',
        '- Food relocation, hazard concentration and clustered gateway spawns deliberately change their scenarios; scenarios should not be ranked as if all starting conditions were identical. Treatments within a scenario have identical terrain, resources and spawns.',
        '- Failed or missing archive pools must be reported, never synthesized; inspect genome_sources for provenance. Archive hashes identify files used; this runner never writes under results/updated_overnight.',
        '', '## Next experiment',
        'Predefine a primary held-out survival/offspring endpoint, expand to ten paired seeds, add a normal-food famine control and an unshifted-world change control, and compare fixed early/late genomes with and without decision memory on multiple unseen terrains. Use action-specific exposure and net energy intake to separate programmed caution from beneficial lifetime learning.',
        '', 'Repeat all trials: `python five_trials.py --seeds 10 --output experiments/five_trials_10seeds`.',
        'No new simulation starts automatically. Source code and archived six-hour data remain preserved.']
    (output/'REPORT.md').write_text('\n\n'.join(text[:3])+'\n'+'\n'.join(text[3:]),encoding='utf-8')


if __name__=='__main__':
    main()
