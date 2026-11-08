"""Paired, offline v0.2 comparisons; standard library only."""
import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from evolution import Simulation
from world import World


def atomic_replace(source, destination):
    """Windows readers can briefly prevent replacement; retry without losing data."""
    for attempt in range(60):
        try:
            source.replace(destination)
            return
        except PermissionError:
            if attempt == 59:
                raise
            time.sleep(.05)


def write_summary(output, simulations, terrain_hash):
    rows = [dict(seed=seed, treatment=mode, terrain_sha256=terrain_hash, **sim.metrics())
            for seed, mode, sim in simulations]
    # Compact time series for observing trends instead of only terminal values.
    history = output/'history.csv'
    with history.open('a', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        if history.stat().st_size == 0:
            writer.writeheader()
        writer.writerows(rows)
    temporary = output/'summary.tmp'
    with temporary.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    atomic_replace(temporary, output/'comparison.csv')
    comparisons = []
    for metric in ('living', 'founder_survival', 'survival_fraction', 'average_observed_lifespan', 'organism_ticks', 'births',
                   'starvation_deaths', 'food_efficiency', 'average_fitness'):
        by_seed = {}
        for row in rows:
            by_seed.setdefault(row['seed'], {})[row['treatment']] = row[metric]
        differences = [p['evolving']-p['baseline'] for p in by_seed.values()
                       if p['evolving'] is not None and p['baseline'] is not None]
        comparisons.append(dict(metric=metric, valid_pairs=len(differences),
            evolving_mean=statistics.mean([r[metric] for r in rows if r['treatment']=='evolving' and r[metric] is not None])
                if any(r[metric] is not None for r in rows if r['treatment']=='evolving') else None,
            baseline_mean=statistics.mean([r[metric] for r in rows if r['treatment']=='baseline' and r[metric] is not None])
                if any(r[metric] is not None for r in rows if r['treatment']=='baseline') else None,
            paired_mean_difference=statistics.mean(differences) if differences else None,
            paired_difference_sd=statistics.stdev(differences) if len(differences)>1 else None))
    with (output/'paired_summary.tmp').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(comparisons[0]))
        writer.writeheader()
        writer.writerows(comparisons)
    atomic_replace(output/'paired_summary.tmp', output/'paired_summary.csv')
    if any(mode == 'evolving_without_knowledge' for _, mode, _ in simulations):
        contrast = []
        for metric in ('living', 'births', 'organism_ticks', 'food_efficiency', 'average_fitness'):
            differences = []
            for seed in range(10):
                pair = {r['treatment']: r for r in rows if r['seed'] == seed}
                a, b = pair['evolving'][metric], pair['evolving_without_knowledge'][metric]
                if a is not None and b is not None:
                    differences.append(a-b)
            contrast.append(dict(metric=metric, valid_pairs=len(differences),
                knowledge_minus_ordinary_mean=statistics.mean(differences) if differences else None,
                paired_difference_sd=statistics.stdev(differences) if len(differences)>1 else None))
        with (output/'knowledge_contrast.tmp').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(contrast[0]))
            writer.writeheader()
            writer.writerows(contrast)
        atomic_replace(output/'knowledge_contrast.tmp', output/'knowledge_contrast.csv')
    if any(mode == 'cautious_knowledge' for _, mode, _ in simulations):
        contrast = []
        for control in ('evolving', 'evolving_without_knowledge', 'baseline'):
            for metric in ('living', 'births', 'organism_ticks', 'food_efficiency', 'average_fitness'):
                pairs = []
                for seed in range(10):
                    case = {r['treatment']: r for r in rows if r['seed']==seed}
                    a, b = case['cautious_knowledge'][metric], case[control][metric]
                    if a is not None and b is not None:
                        pairs.append(a-b)
                contrast.append(dict(control=control, metric=metric, valid_pairs=len(pairs),
                    cautious_minus_control=statistics.mean(pairs) if pairs else None,
                    paired_difference_sd=statistics.stdev(pairs) if len(pairs)>1 else None))
        with (output/'cautious_contrast.tmp').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(contrast[0]))
            writer.writeheader()
            writer.writerows(contrast)
        atomic_replace(output/'cautious_contrast.tmp', output/'cautious_contrast.csv')
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='results/v02_comparison')
    parser.add_argument('--terrain', default='results/v02_terrain.json')
    parser.add_argument('--ticks', type=int, default=1200)
    parser.add_argument('--population', type=int, default=20)
    parser.add_argument('--max-population', type=int, default=60)
    parser.add_argument('--resource-fraction', type=float, default=.2)
    parser.add_argument('--max-lifespan', type=int, default=1200)
    parser.add_argument('--maturity-age', type=int, default=60)
    parser.add_argument('--knowledge', action='store_true', help='Enable intrinsic motivation in evolving treatment only')
    parser.add_argument('--resume-from', help='Reconstruct and verify the last saved checkpoint of an interrupted run')
    parser.add_argument('--resume-snapshot', help='Exact local state snapshot generated by this project')
    parser.add_argument('--cautious', action='store_true', help='Add a fourth treatment with conservative exploration')
    parser.add_argument('--hours', type=float, default=0, help='Optional wall-time limit, including throttling')
    parser.add_argument('--duty', type=float, default=.25, help='Approximate CPU duty fraction, not a hard OS limit')
    args = parser.parse_args()
    if (args.ticks < 1 or args.population < 1 or args.max_population < args.population
            or not 0 <= args.resource_fraction <= 1 or args.max_lifespan < 1
            or args.maturity_age < 0 or not math.isfinite(args.hours) or args.hours < 0
            or not 0 < args.duty <= 1):
        parser.error('invalid experiment parameters')
    output, terrain = Path(args.output), Path(args.terrain)
    output.mkdir(parents=True, exist_ok=True)
    if (output/'experiment.json').exists():
        parser.error('experiment output already exists; choose a new directory')
    terrain.parent.mkdir(parents=True, exist_ok=True)
    if not terrain.exists():
        World(random.Random(42)).save(terrain)
    digest = hashlib.sha256(terrain.read_bytes()).hexdigest()
    source = Path(args.resume_from) if args.resume_from else None
    if args.resume_from and args.resume_snapshot:
        parser.error('choose one resume method')
    previous = json.loads((source/'experiment.json').read_text()) if source else None
    resume_tick = previous['completed_ticks'] if previous else 0
    saved_rows = list(csv.DictReader((source/'comparison.csv').open())) if source else []
    if previous:
        if digest != previous['terrain_sha256']:
            parser.error('resume terrain hash mismatch')
        for key in ('population', 'max_population', 'resource_fraction', 'max_lifespan', 'maturity_age', 'knowledge'):
            if getattr(args, key) != previous['parameters'][key]:
                parser.error('resume parameter mismatch: '+key)
        if args.cautious != previous['parameters'].get('cautious', False):
            parser.error('resume cautious-treatment mismatch')
        if any(int(r['ticks']) != resume_tick for r in saved_rows):
            parser.error('resume checkpoint tick mismatch')
    manifest = dict(version='0.2+knowledge', seeds=list(range(10)), terrain_sha256=digest,
        parameters=vars(args), status='running', completed_ticks=0,
        started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    manifest_path = output/'experiment.json'
    if previous:
        manifest.update(started_utc=previous['started_utc'], resumed_from=str(source),
                        resume_tick=resume_tick, replay_verified=False, status='recovering')
    manifest_path.write_text(json.dumps(manifest, indent=2))
    control_path = output/'control.json'
    control_path.write_text(json.dumps(dict(duty=args.duty)))
    simulations = []
    started = time.monotonic()
    if previous:
        started -= (datetime.now(timezone.utc)-datetime.fromisoformat(previous['started_utc'].replace('Z', '+00:00'))).total_seconds()
    reason = 'tick_limit'
    try:
        if args.resume_snapshot:
            from checkpoint import load_snapshot
            previous_snapshot, simulations = load_snapshot(args.resume_snapshot, output)
            if previous_snapshot['terrain_sha256'] != digest:
                raise ValueError('snapshot terrain mismatch')
            for key in ('population', 'max_population', 'resource_fraction', 'max_lifespan', 'maturity_age', 'knowledge', 'cautious'):
                if previous_snapshot['parameters'].get(key, False) != getattr(args, key):
                    raise ValueError('snapshot parameter mismatch: '+key)
            manifest.update(started_utc=previous_snapshot['started_utc'],
                completed_ticks=previous_snapshot['completed_ticks'], snapshot_verified=True,
                resumed_from=args.resume_snapshot)
            started = time.monotonic()-(datetime.now(timezone.utc)-datetime.fromisoformat(manifest['started_utc'].replace('Z', '+00:00'))).total_seconds()
        modes = ['evolving', 'baseline']
        if args.knowledge:
            modes.append('evolving_without_knowledge')
        if args.cautious:
            if not args.knowledge:
                raise ValueError('--cautious requires --knowledge')
            modes.append('cautious_knowledge')
        for seed in ([] if simulations else range(10)):
            for mode in modes:
                sim = Simulation(population=args.population, ticks=400, seed=seed,
                    output=output/f'seed_{seed}_{mode}', max_lifespan=args.max_lifespan,
                    lifetime=True, baseline=mode=='baseline', resource_fraction=args.resource_fraction,
                    max_population=args.max_population, maturity_age=args.maturity_age, terrain=terrain,
                    knowledge=args.knowledge and mode in ('evolving', 'cautious_knowledge'),
                    knowledge_variant='cautious' if mode=='cautious_knowledge' else 'original')
                simulations.append((seed, mode, sim))
        completed = manifest['completed_ticks']
        while completed < args.ticks:
            batch_started = time.monotonic()
            batch = min(25, args.ticks-completed)
            # Every pair advances the exact same number of ticks before checking time.
            for _, _, sim in simulations:
                for _ in range(batch):
                    if sim.step():
                        sim.finish_generation()
            completed += batch
            if previous and completed == resume_tick:
                for row in saved_rows:
                    sim = next(s for seed, mode, s in simulations if seed == int(row['seed']) and mode == row['treatment'])
                    for key, value in sim.metrics().items():
                        if value is None:
                            assert row[key] == '', (key, row[key])
                        else:
                            assert math.isclose(float(row[key]), value, rel_tol=1e-12, abs_tol=1e-9), (key, row[key], value)
                manifest['replay_verified'] = True
                manifest['status'] = 'running'
            if completed % 100 == 0 or completed == args.ticks:
                write_summary(output, simulations, digest)
                for _, _, sim in simulations:
                    sim.flush()
                manifest['completed_ticks'] = completed
                manifest_path.write_text(json.dumps(manifest, indent=2))
            if completed % 1000 == 0:
                from checkpoint import save_snapshot
                save_snapshot(output/'checkpoint.pkl', simulations, manifest, atomic_replace)
            if not any(sim.organisms for _, _, sim in simulations):
                reason = 'all_populations_extinct'
                break
            if completed >= resume_tick and args.hours and time.monotonic()-started >= args.hours*3600:
                reason = 'wall_time_limit'
                break
            elapsed = time.monotonic()-batch_started
            try:
                requested = float(json.loads(control_path.read_text())['duty'])
                if math.isfinite(requested) and .05 <= requested <= 1:
                    args.duty = requested
                    manifest['parameters']['duty'] = requested
            except (OSError, ValueError, KeyError):
                pass
            rest = 0 if completed < resume_tick else elapsed*(1/args.duty-1)
            while rest > 0:
                pause = min(1, rest)
                time.sleep(pause)
                rest -= pause
                if args.hours and time.monotonic()-started >= args.hours*3600:
                    break
        write_summary(output, simulations, digest)
        for _, _, sim in simulations:
            for o in sim.organisms:
                sim.record(o)
        manifest.update(status='complete', reason=reason, completed_ticks=completed,
                        elapsed_seconds=time.monotonic()-started)
    except BaseException as error:
        manifest.update(status='failed', error=str(error), elapsed_seconds=time.monotonic()-started)
        raise
    finally:
        for _, _, sim in simulations:
            sim.close()
        manifest_path.write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
