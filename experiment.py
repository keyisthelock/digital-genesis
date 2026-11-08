"""Paired, offline v0.2 comparisons; standard library only."""
import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import time
from pathlib import Path
from evolution import Simulation
from world import World


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
    temporary.replace(output/'comparison.csv')
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
    (output/'paired_summary.tmp').replace(output/'paired_summary.csv')
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
    manifest = dict(version='0.2', seeds=list(range(10)), terrain_sha256=digest,
        parameters=vars(args), status='running', completed_ticks=0,
        started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    manifest_path = output/'experiment.json'
    manifest_path.write_text(json.dumps(manifest, indent=2))
    simulations = []
    started = time.monotonic()
    reason = 'tick_limit'
    try:
        for seed in range(10):
            for mode in ('evolving', 'baseline'):
                sim = Simulation(population=args.population, ticks=400, seed=seed,
                    output=output/f'seed_{seed}_{mode}', max_lifespan=args.max_lifespan,
                    lifetime=True, baseline=mode=='baseline', resource_fraction=args.resource_fraction,
                    max_population=args.max_population, maturity_age=args.maturity_age, terrain=terrain)
                simulations.append((seed, mode, sim))
        completed = 0
        while completed < args.ticks:
            batch_started = time.monotonic()
            batch = min(25, args.ticks-completed)
            # Every pair advances the exact same number of ticks before checking time.
            for _, _, sim in simulations:
                for _ in range(batch):
                    if sim.step():
                        sim.finish_generation()
            completed += batch
            if completed % 100 == 0 or completed == args.ticks:
                write_summary(output, simulations, digest)
                for _, _, sim in simulations:
                    sim.flush()
                manifest['completed_ticks'] = completed
                manifest_path.write_text(json.dumps(manifest, indent=2))
            if not any(sim.organisms for _, _, sim in simulations):
                reason = 'all_populations_extinct'
                break
            if args.hours and time.monotonic()-started >= args.hours*3600:
                reason = 'wall_time_limit'
                break
            elapsed = time.monotonic()-batch_started
            rest = elapsed*(1/args.duty-1)
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
        manifest.update(status='failed', error=str(error))
        raise
    finally:
        for _, _, sim in simulations:
            sim.close()
        manifest_path.write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
