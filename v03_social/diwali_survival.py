"""Short CPU curriculum and paired evaluation for the Diwali research session."""

import argparse
import json
import random
from pathlib import Path

from cognition import LAYOUTS, new_genome
from first_survival import ROOT, environment, run, write_csv, write_json

STAGES = (
    ('A', 4201, .90, True, False, 70),
    ('B', 4202, .90, True, True, 70),
    ('C', 4203, .60, False, True, 90),
    ('D', 4204, .35, False, True, 220),
)
HOLDOUTS = (9201, 9202, 9203)
LINEAGE_SEEDS = (9301, 9302, 9303)
TICKS = 360


def runtime(path):
    return {int(k): v for k, v in json.loads(path.read_text()).items()}


def diagnose(out):
    old = ROOT / 'experiments/social_screen'
    rows = []
    for sharing in (False, True):
        for seed in range(3):
            case = old / f'case_1_seed_{seed}_D_social_evolving_shuffle_0_new'
            config = json.loads((case / 'v03_config.json').read_text())
            row, _ = run(out / f'legacy_{seed}_share_{int(sharing)}', mode='legacy',
                         size=67, seed=seed, terrain=old / f'terrain_{seed}.json',
                         ticks=1500, spawns=config['environment']['spawns'],
                         allow_sharing=sharing, trace_ids=(1, 2, 3))
            rows.append(row)
    write_csv(out / 'diagnosis.csv', rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    if not (out / 'diagnosis.csv').exists():
        diagnose(out)
    if (out / 'protocol.json').exists():
        parser.error('choose a fresh output directory')
    write_json(out / 'protocol.json', dict(
        stages=[dict(stage=stage, seed=seed, resource_fraction=fraction, hazards=not safe,
                     brain_charge=charge, ticks=ticks)
                for stage, seed, fraction, safe, charge, ticks in STAGES],
        holdout_seeds=HOLDOUTS, lineage_seeds=LINEAGE_SEEDS, holdout_ticks=TICKS,
        lineage_ticks=240, population=12, cap=24, holdout_resource_fraction=.35,
        sharing_control_modules=32,
        first_lineage='first archived birth by size, then training stage, then held-out seed and arm',
    ))
    genomes = {size: [new_genome(random.Random(37001 + size * 100 + i), size)
                     for i in range(12)] for size in LAYOUTS}
    write_json(out / 'founder_genomes.json', genomes)
    trained = {}
    training = []
    lineages = {}
    for stage, seed, fraction, safe, charge, ticks in STAGES:
        terrain = environment(out, seed, safe)
        for size, gene in genomes.items():
            path = out / f'curriculum_{stage}_{size}'
            row, _ = run(path, mode='candidate', size=size, seed=seed, terrain=terrain,
                         ticks=ticks, fraction=fraction, gene=gene, allow_sharing=False,
                         runtime=trained.get(size), export_runtime=True, charge_brain=charge)
            training.append(row)
            trained[size] = runtime(path / 'runtime.json')
            if (path / 'first_child.json').exists():
                lineages.setdefault(size, path)
        print(f'Curriculum stage {stage} complete', flush=True)
    write_csv(out / 'curriculum.csv', training)

    held = []
    for seed in HOLDOUTS:
        terrain = environment(out, seed)
        row, _ = run(out / f'{seed}_rule', mode='rule', size=32, seed=seed, terrain=terrain,
                     ticks=TICKS, learning=False, allow_sharing=False)
        held.append(row)
        row, _ = run(out / f'{seed}_random32', mode='random_compute', size=32, seed=seed,
                     terrain=terrain, ticks=TICKS, gene=genomes[32], learning=False,
                     allow_sharing=False)
        held.append(row)
        for size, gene in genomes.items():
            arms = [('cold_off', False, False, None), ('cold_on', True, False, None),
                    ('curriculum_on', True, False, trained[size])]
            if size == 32:
                arms += [('cold_on_share', True, True, None),
                         ('curriculum_on_share', True, True, trained[size])]
            for arm, learn, share, weights in arms:
                path = out / f'{seed}_{size}_{arm}'
                row, _ = run(path, mode='candidate', size=size, seed=seed, terrain=terrain,
                             ticks=TICKS, gene=gene, learning=learn, allow_sharing=share,
                             runtime=weights, export_lineage=True)
                held.append(row)
                if (path / 'first_child.json').exists():
                    lineages.setdefault(size, path)
        write_csv(out / 'held_out.csv', held)
        print(f'Held-out seed {seed} complete', flush=True)

    if lineages:
        size = min(lineages)
        source = lineages[size]
        pair = json.loads((source / 'first_child.json').read_text())
        write_json(out / 'lineage_pair.json', dict(source=source.name, modules=size, **pair))
        rows = []
        for seed in LINEAGE_SEEDS:
            terrain = environment(out, seed)
            for arm in ('founder', 'descendant'):
                row, _ = run(out / f'{seed}_{arm}', mode='candidate', size=size, seed=seed,
                             terrain=terrain, ticks=240, gene=pair[arm], learning=False,
                             allow_sharing=False, freeze=True)
                rows.append(row)
        write_csv(out / 'lineage.csv', rows)


if __name__ == '__main__':
    main()
