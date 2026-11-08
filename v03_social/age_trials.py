"""Paired million-year environmental transitions on the existing ecology."""

import argparse
import json
import random
from pathlib import Path

from experiment_v03 import relocate
from first_survival import environment, write_csv, write_json
from reproduction_trials import ARMS, TRAINED, run

YEARS_PER_TICK = 500
AGE_TICKS = 250
AGES = (
    ('Temperate start', .35, 1., False, 0.),
    ('Cooling', .31, .85, False, 0.),
    ('Ice age', .26, .68, False, 0.),
    ('Deglaciation', .34, .92, True, 0.),
    ('Warm forest', .43, 1., False, 0.),
    ('Volcanic disturbance', .34, .85, False, .018),
    ('Dry age', .28, .98, False, 0.),
    ('Temperate recovery', .37, 1., True, 0.),
)
WEIGHTS = dict(persistence=.5, food_rate=.3, birth_rate=.2)


def timeline(sim, dynamic, refuges=False, resource_floor=.35):
    rows = []
    world = sim.world
    original = dict(world.tiles)
    for index, (name, resource, light, move_food, hazard_fraction) in enumerate(AGES):
        if refuges:
            resource = max(resource_floor, resource)
            light = max(.90, light)
        before = sim.metrics()
        reached = bool(sim.organisms)
        if reached and dynamic:
            world.resource_fraction = resource
            world.daylight_scale = light
            world.tiles.update(original)
            if move_food:
                old_food = list(world.food.items())
                relocate(world)
                if refuges:
                    world.food = dict(old if i % 2 == 0 else moved
                                      for i, (old, moved) in enumerate(zip(old_food, world.food.items())))
            if hazard_fraction:
                safe = [p for p in world.land if p != world.fruit and p not in world.food]
                rng = random.Random(sim.seed_value * 101 + index)
                for p in rng.sample(safe, round(len(safe) * hazard_fraction)):
                    world.tiles[p] = 'hazard'
        if reached:
            for _ in range(AGE_TICKS):
                if sim.step():
                    break
        after = sim.metrics()
        span = after['ticks'] - before['ticks']
        rows.append(dict(phase=name, dynamic=dynamic, scheduled_from_year=index*AGE_TICKS*YEARS_PER_TICK,
                         scheduled_to_year=(index+1)*AGE_TICKS*YEARS_PER_TICK, reached=int(reached),
                         actual_to_year=after['ticks']*YEARS_PER_TICK, ticks_exposed=span,
                         resource_fraction=resource if dynamic else .35, daylight_scale=light if dynamic else 1.,
                         alive_start=before['living'], alive_end=after['living'],
                         births=after['births']-before['births'], deaths=after['deaths']-before['deaths'],
                         food=after['food_consumed']-before['food_consumed'],
                         organism_ticks=after['organism_ticks']-before['organism_ticks']))
    write_csv(sim.output/'ages.csv', rows)
    return rows


def read_ages(path):
    import csv
    with path.open(newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seeds', type=int, choices=range(1, 21), default=3)
    parser.add_argument('--refuges', action='store_true', help='Run buffered transitions as an exploratory treatment')
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True)
    genes = [json.loads(TRAINED.read_text())]
    ticks = len(AGES)*AGE_TICKS
    write_json(out/'protocol.json', dict(ages=AGES, ticks_per_age=AGE_TICKS, seeds=args.seeds,
        years_per_tick=YEARS_PER_TICK, adaptation_weights=WEIGHTS,
        adaptation_components=dict(persistence='fraction of horizon with living organisms',
            food_rate='food energy per organism-tick, scaled by 0.5',
            birth_rate='births per mature organism-tick, scaled by 0.004'),
        stock='regrowth changes without adding or removing food at phase boundaries',
        refuges=args.refuges, refuge_settings=dict(regrowth_floor=.35, daylight_floor=.90,
                                                   retained_patch_fraction=.5)))
    rows, phases, contrasts = [], [], []
    for i in range(args.seeds):
        seed = 14100 + i
        terrain = environment(out, seed)
        for arm in ('asexual', 'social', 'rule_asexual'):
            pair = {}
            for dynamic in ((True,) if args.refuges else (False, True)):
                path = out/f'{seed}_{arm}_{"ages" if dynamic else "static"}'
                row = run(path, terrain, seed, ticks, ARMS[arm], genes,
                          phases=lambda sim: timeline(sim, dynamic, args.refuges))
                age_rows = read_ages(path/'ages.csv')
                organism_ticks = sum(int(r['organism_ticks']) for r in age_rows)
                components = dict(persistence=row['ticks']/ticks,
                    food_rate=min(1, row['food']/max(1, organism_ticks)/.5),
                    birth_rate=min(1, row['births']/max(1, row['mature_ticks'])/.004))
                score = sum(WEIGHTS[k]*components[k] for k in WEIGHTS)
                pair[dynamic] = score
                rows.append(dict(treatment=arm, dynamic=dynamic, adaptation_score=score,
                                 completed_million=int(row['ticks']==ticks and row['survivors']>0), **row))
                phases.extend(dict(seed=seed, treatment=arm, **r) for r in age_rows)
            if not args.refuges:
                contrasts.append(dict(seed=seed, treatment=arm, static_score=pair[False],
                                      ages_score=pair[True], change=pair[True]-pair[False]))
        write_csv(out/'results.csv', rows)
        write_csv(out/'ages.csv', phases)
        if contrasts:
            write_csv(out/'adaptation_contrast.csv', contrasts)
        print(f'Age seed {seed} complete', flush=True)


if __name__ == '__main__':
    main()
