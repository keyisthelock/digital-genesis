"""Paired cultural transmission experiment and continuous ecosystem entry point."""

import argparse
import json
import math
import random
import time
from collections import Counter
from pathlib import Path

from ecosystem import CHANNELS, PREVIOUS, RANGE, Ecosystem, terrain
from first_survival import write_csv, write_json
from neural_survival import fingerprint

PILOT = (10111,10112,10113)
CALIBRATION = (10073,)
HOLDOUT = ((90101,'causeway'),(90102,'islands'))
LEDGER = ('basal','brain','movement','gateway','birth_net','removed_energy','sharing_loss')
REGROWTH_MULTIPLIER = 4


def make(path, map_path, seed, genome, *, ticks, channel='intact', population=16,
         plastic=True, reproduce=True, neural_pool=None, body_pool=None, radius=RANGE):
    sim=Ecosystem(output=path, terrain=map_path, seed=seed, ticks=ticks, population=population,
                     max_population=max(28,population), modules=len(genome['modules']),
                     learning=False, neural_pool=neural_pool or [genome], body_pool=body_pool,
                     resource_fraction=.85, max_lifespan=2500, reproduce=reproduce,
                     channel=channel, plastic=plastic, radius=radius)
    sim.world.resource_fraction *= REGROWTH_MULTIPLIER
    return sim


def cluster(sim, seed):
    rng=random.Random(seed*173+11)
    hub=(sim.world.width//2,sim.world.height//2)
    spots=[p for p in sim.world.land if abs(p[0]-hub[0])+abs(p[1]-hub[1])<=4]
    for body in sim.organisms:
        body.position=rng.choice(spots)


def advance(sim, target, *, keep_clock=False):
    while sim.world.tick < target and (sim.organisms or keep_clock):
        sim.step()


def audit(sim):
    counts=sim.genesis_counts
    sim.ledger['sharing_loss']=sim.totals['sharing_loss']
    residual=sim.ledger['living_energy_change']-sim.ledger['food_retained']+sum(sim.ledger[k] for k in LEDGER)
    residual+=counts['message_energy']+counts['gate_energy']
    assert abs(residual)<1e-6, residual
    assert sim.size+sim.total_births+sim.introduced-sim.total_deaths-sim.removed==len(sim.organisms)
    write_json(sim.output/'energy.json',dict(ledger=sim.ledger,communication=counts,residual=residual))
    return residual


def phase_rows(sim, seed, arm):
    rows=[]
    for phase in ('establish','contact','after'):
        for scout in ('resident','foster'):
            for receiver in ('resident','foster'):
                c=sim.phase_counts[phase,scout,receiver]
                rows.append(dict(seed=seed,arm=arm,phase=phase,scout=scout,receiver=receiver,
                    attempts=c['attempts'],correct=c['correct'],delivered=c['delivered'],
                    unrelated_delivered=c['unrelated_delivered'],
                    intergenerational_delivered=c['intergenerational_delivered'],
                    observational_updates=c['observational_updates'],food=c['food'],
                    receiver_births=sim.totals_by_origin[phase,receiver,'births'],
                    receiver_deaths=sim.totals_by_origin[phase,receiver,'deaths']))
    return rows


def snapshot(sim, introduced_ids):
    return [dict(id=o.id, generation=o.generation, communication=o.signal.genome,
                 send=[row[:] for row in o.signal.send], receive=[row[:] for row in o.signal.receive],
                 updates=o.signal.updates,
                 neural=o.brain.genetic, body=o.genome,
                 roots=sorted(sim.ancestry_roots[o.id]))
            for o in sim.organisms if o.id in introduced_ids]


def stability(before, after):
    earlier={body['id']:body for body in before}
    rows=[]
    for body in after:
        previous=earlier[body['id']]
        for role, limit in (('send',2),('receive',4)):
            for cue,(old,new) in enumerate(zip(previous[role][:limit],body[role][:limit])):
                old_choice=max(range(len(old)),key=old.__getitem__)
                new_choice=max(range(len(new)),key=new.__getitem__)
                rows.append(dict(id=body['id'],role=role,cue=cue,before=old_choice,after=new_choice,
                                 unchanged=int(old_choice==new_choice)))
    return rows


def summarize(sim, seed, arm, start, **extras):
    metrics=sim.metrics()
    return dict(seed=seed,arm=arm,ticks=sim.world.tick,survivors=metrics['living'],
                births=metrics['births'],deaths=metrics['deaths'],introduced=sim.introduced,
                removed=sim.removed,max_generation=sim.max_generation,food=metrics['food_consumed'],
                message_energy=sim.genesis_counts['message_energy'],gate_energy=sim.genesis_counts['gate_energy'],
                neural_energy=sim.ledger['brain'],neural_ops=sim.totals['neural_ops'],
                expired_messages=sim.genesis_counts['expired'],cpu_seconds=time.process_time()-start,
                energy_residual=audit(sim),**extras)


def run(path, map_path, seed, genome, arm, schedule, radius):
    start=time.process_time()
    intro,removal,end=schedule
    sim=make(path,map_path,seed,genome,ticks=end,channel=arm,radius=radius)
    try:
        cluster(sim,seed)
        original=set(sim.origin)
        advance(sim,intro,keep_clock=True)
        sim.max_population=40
        prior=set(sim.origin)
        sim.introduce_fosters()
        introduced_ids={o.id for o in sim.organisms if o.id not in prior}
        inherited=snapshot(sim,introduced_ids)
        write_json(path/'introduced.json',inherited)
        advance(sim,removal,keep_clock=True)
        before=snapshot(sim,introduced_ids)
        before_residents=sum(sim.origin[o.id]=='resident' for o in sim.organisms)
        sim.teacher_boundary()
        advance(sim,end)
        after=snapshot(sim,introduced_ids)
        result=summarize(sim,seed,arm,start,
            residents_before_removal=before_residents,
            resident_survivors=sum(sim.origin[o.id]=='resident' for o in sim.organisms),
            original_teacher_survivors=sum(o.id in original for o in sim.organisms),
            foster_survivors=sum(sim.origin[o.id]=='foster' for o in sim.organisms),
            surviving_introduced=len(after),post_population_extinct=int(not sim.organisms))
        write_json(path/'learner_snapshots.json',dict(before=before,after=after))
        stable=stability(before,after)
        if stable:
            write_csv(path/'stability.csv',stable)
        write_csv(path/'conventions.csv',[
            dict(phase=phase,scout=scout,receiver=receiver,marker=marker,symbol=symbol,route=route,count=count)
            for (phase,scout,receiver,marker,symbol,route),count in sorted(sim.signal_counts.items())
        ] or [dict(phase='',scout='',receiver='',marker='',symbol='',route='',count=0)])
        sim.finish_generation(reproduce=False)
        return result,phase_rows(sim,seed,arm),after,inherited
    finally:
        sim.close()


def heldout(path,map_path,eval_seed,seed,arm,panel,variant,ticks,radius):
    if len(panel)<2:
        return dict(seed=seed,arm=arm,eval_seed=eval_seed,variant=variant,panel=len(panel),
                    evaluated=0,attempts=0,correct=0,delivered=0,unrelated=0,survivors=0,
                    food=0.,cpu_seconds=0.)
    start=time.process_time()
    sim=make(path,map_path,eval_seed, panel[0]['neural'],ticks=ticks,
             channel='disabled' if variant=='blocked' else 'intact',population=len(panel),
             plastic=False,reproduce=False,neural_pool=[o['neural'] for o in panel],
             body_pool=[o['body'] for o in panel],radius=radius)
    try:
        from communication import Communication
        cluster(sim,eval_seed)
        for body,saved in zip(sim.organisms,panel):
            body.signal=Communication(saved['communication'])
            sim.ancestry_roots[body.id]=set(saved['roots'])
            if variant!='germline':
                body.signal.send=[list(row) for row in saved['send']]
                body.signal.receive=[list(row) for row in saved['receive']]
        sim.phase='after'
        advance(sim,ticks)
        c=sim.phase_counts['after','resident','resident']
        audit(sim)
        return dict(seed=seed,arm=arm,eval_seed=eval_seed,variant=variant,panel=len(panel),
                    evaluated=1,attempts=c['attempts'],correct=c['correct'],delivered=c['delivered'],
                    unrelated=c['unrelated_delivered'],survivors=len(sim.organisms),
                    food=sim.metrics()['food_consumed'],cpu_seconds=time.process_time()-start)
    finally:
        sim.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--modules',type=int,choices=(32,67),default=32)
    parser.add_argument('--calibration',action='store_true')
    parser.add_argument('--seeds',type=int,choices=range(3,51),default=3)
    parser.add_argument('--ecosystem-ticks',type=int)
    parser.add_argument('--radius',type=int,default=RANGE)
    args=parser.parse_args()
    if args.radius<0 or (args.ecosystem_ticks is not None and args.ecosystem_ticks<1):
        parser.error('radius must be nonnegative and ecosystem tick count positive')
    out=args.output
    out.mkdir(parents=True)
    genome=json.loads((PREVIOUS/'experiments/first_survival_v031'/f'trained_{args.modules}.json').read_text())
    if args.ecosystem_ticks:
        start=time.process_time()
        seed=PILOT[0]
        map_path=terrain(out/'terrain.json',seed)
        sim=make(out/'world',map_path,seed,genome,ticks=args.ecosystem_ticks,radius=args.radius)
        try:
            cluster(sim,seed)
            advance(sim,args.ecosystem_ticks)
            write_csv(out/'results.csv',[summarize(sim,seed,'ecosystem',start)])
            sim.finish_generation(reproduce=False)
        finally:
            sim.close()
        return
    seeds=CALIBRATION if args.calibration else PILOT if args.seeds==3 else tuple(range(10200,10200+args.seeds))
    arms=('intact','retain','disabled') if args.calibration else CHANNELS
    schedule=(105,190,285) if args.calibration else (250,460,660)
    evaluation=() if args.calibration else HOLDOUT
    write_json(out/'protocol.json',dict(seeds=seeds,arms=arms,schedule=schedule,heldout=evaluation,
        modules=args.modules,genome_sha=fingerprint(genome),radius=args.radius,
        initial_resource_fraction=.85,regrowth_multiplier=REGROWTH_MULTIPLIER,
        genetic_controls='same cross-foster cohorts and frozen germline counterfactual',
        neural_weights='legacy trained neural policy with runtime neural plasticity frozen',
        experimental_gate='two physical latch choices for existing food; marker visible only to local scout'))
    results,phases,transfer=[],[],[]
    maps={seed:terrain(out/f'holdout_{seed}.json',seed,kind) for seed,kind in evaluation}
    for seed in seeds:
        map_path=terrain(out/f'training_{seed}.json',seed)
        fingerprints=set()
        for arm in arms:
            path=out/f'{seed}_{arm}'
            row,counts,panel,introduced=run(path,map_path,seed,genome,arm,schedule,args.radius)
            fingerprints.add(fingerprint(introduced))
            results.append(row)
            phases.extend(counts)
            for eval_seed,eval_path in maps.items():
                for variant in ('lived','germline','blocked'):
                    transfer.append(heldout(path/f'{eval_seed}_{variant}',eval_path,eval_seed,seed,arm,panel,
                                           variant,100,args.radius))
            print(f'{seed} {arm}: {row["foster_survivors"]} fosters, {row["resident_survivors"]} residents',flush=True)
        assert len(fingerprints)==1, 'introduced cohorts were not genetically matched'
        write_csv(out/'results.csv',results)
        write_csv(out/'transmission.csv',phases)
        if transfer:
            write_csv(out/'heldout.csv',transfer)


if __name__=='__main__':
    main()
