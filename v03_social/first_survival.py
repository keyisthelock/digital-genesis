"""Reproducible CPU screening for Digital Genesis v0.3.1."""

import argparse
import copy
import csv
import json
import random
import time
from pathlib import Path

from cognition import LAYOUTS, new_genome
from neural_survival import AuditedSimulation, SurvivalBrain, fingerprint
from world import World

ROOT = Path(__file__).resolve().parent
STAGES = ((3101, .90, True), (3102, .60, False), (3103, .35, False))
HOLDOUTS = (9101, 9102)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def environment(output, seed, safe=False):
    world = World(random.Random(seed))
    if safe:
        world.tiles = {pos: 'land' if tile == 'hazard' else tile for pos, tile in world.tiles.items()}
    path = output / f'terrain_{seed}.json'
    world.save(path)
    return path


def run(output, *, mode, size, seed, terrain, ticks, fraction=.35, gene=None,
        learning=True, spawns=None, allow_sharing=True, trace_ids=(), runtime=None,
        export_runtime=False, export_lineage=False, charge_brain=True, freeze=False):
    no_network = mode in ('teacher', 'random', 'rule')
    config = dict(
        mode=mode, modules=size, seed=seed, terrain=terrain, ticks=ticks,
        output=output, population=12, max_population=24, max_lifespan=3000,
        maturity_age=100, resource_fraction=fraction, learning=learning and not no_network,
        treatment='A_rule' if mode == 'rule' else 'D_social_evolving',
        neural_pool=(gene if isinstance(gene, list) else [gene]) if gene else None,
        allow_sharing=allow_sharing, trace_ids=trace_ids, runtime=runtime, freeze=freeze,
        brain_energy_parameter=.000002 if charge_brain and not no_network else 0.,
        brain_energy_op=.00001 if charge_brain and not no_network else 0.,
    )
    start = time.process_time()
    sim = AuditedSimulation(**config)
    try:
        if spawns:
            for organism, position in zip(sim.organisms, spawns):
                organism.position = tuple(position)
        initial_food = sum(sim.world.food.values())
        initial_spawns = [o.position for o in sim.organisms]
        for _ in range(ticks):
            if sim.step():
                break
        metrics = sim.metrics()
        extras = sim.extra_metrics()
        ledger = sim.ledger
        ledger['sharing_loss'] = sim.totals['sharing_loss']
        ledger['food_cap_loss'] = metrics['food_consumed'] - ledger['food_retained']
        costs = sum(ledger[key] for key in ('basal', 'brain', 'movement', 'gateway',
                                           'birth_net', 'removed_energy', 'sharing_loss'))
        residual = ledger['living_energy_change'] - ledger['food_retained'] + costs
        assert abs(residual) < 1e-7, residual
        row = dict(
            condition=output.name, seed=seed, modules=0 if no_network else size,
            learning=sim.neural_learning, resource_fraction=fraction,
            initial_food=initial_food, ticks=metrics['ticks'], survivors=metrics['living'],
            deaths=metrics['deaths'], starvation_deaths=metrics['starvation_deaths'],
            births=metrics['births'], max_generation=sim.max_generation,
            living_descendants=sum(o.parent_id is not None for o in sim.organisms),
            peak_mature_energy=sim.peak_mature_energy,
            food=metrics['food_consumed'], food_retained=ledger['food_retained'],
            food_per_organism_tick=metrics['food_consumed'] / metrics['organism_ticks'],
            organism_ticks=metrics['organism_ticks'], brain_energy=ledger['brain'],
            brain_ops=extras.get('neural_ops', 0),
            mean_decision_complexity=(extras.get('complexity_sum', 0) /
                                      max(1, extras.get('neural_decisions', 0))) if not no_network else 0.,
            active_module_fraction=extras['module_utilization'] if not no_network else None,
            learning_updates=extras.get('learning_updates', 0),
            early_prediction_mse=extras['prediction_first_error'] / extras['prediction_first_samples']
            if extras.get('prediction_first_samples') and not no_network else None,
            later_prediction_mse=extras['prediction_later_error'] / extras['prediction_later_samples']
            if extras.get('prediction_later_samples') and not no_network else None,
            food_opportunities=ledger['food_opportunities'], eat_when_available=ledger['eat_when_available'],
            mean_eat_probability=ledger['eat_probability_sum'] / ledger['eat_probability_samples']
            if ledger['eat_probability_samples'] else None,
            mean_legal_probability_range=ledger['probability_range_sum'] / ledger['probability_samples']
            if ledger['probability_samples'] else None,
            corrected_rewards=ledger['reward_changed'],
            shares=sim.totals['shares'], sharing_loss=ledger['sharing_loss'],
            mutation_events=sum(m['parent_genotype'] != m['child_genotype'] for m in sim.mutations),
            energy_residual=residual, cpu_seconds=time.process_time() - start,
        )
        write_json(output / 'diagnostics.json', dict(
            result=row, selected_actions=sim.actions, energy=ledger, trajectory=sim.trajectory,
            spawns=initial_spawns, mutations=sim.mutations,
        ))
        if export_runtime:
            write_json(output / 'runtime.json', {
                id_: [module.p for module in brain.modules]
                for id_, brain in sim.founders.items()
            })
        if sim.first_child and (export_runtime or export_lineage):
            write_json(output / 'first_child.json', sim.first_child)
        if mode != 'teacher':
            sim.finish_generation(reproduce=False)
        return row, sim.examples
    finally:
        sim.close()


def train(output):
    trainers = {size: SurvivalBrain(new_genome(random.Random(731 + size), size)) for size in LAYOUTS}
    progress = []
    for stage, (seed, fraction, safe) in enumerate(STAGES, 1):
        terrain = environment(output, seed, safe)
        _, examples = run(output / f'teacher_{stage}', mode='teacher', size=8, seed=seed,
                          terrain=terrain, ticks=160, fraction=fraction)
        assert examples
        for size, brain in trainers.items():
            for epoch in range(4):
                order = list(range(len(examples)))
                random.Random(seed + epoch).shuffle(order)
                loss = sum(brain.imitate(*examples[index]) for index in order)
                progress.append(dict(stage=stage, size=size, epoch=epoch + 1,
                                     examples=len(examples), mean_training_nll=loss / len(examples)))
    genes = {}
    for size, brain in trainers.items():
        genes[size] = copy.deepcopy(brain.genetic)
        genes[size]['modules'] = [copy.deepcopy(module.p) for module in brain.modules]
        write_json(output / f'trained_{size}.json', genes[size])
    write_csv(output / 'curriculum.csv', progress)
    return genes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ticks', type=int, default=420)
    parser.add_argument('--diagnose-only', action='store_true')
    args = parser.parse_args()
    if args.ticks < 1:
        parser.error('ticks must be positive')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    old = ROOT / 'experiments/social_screen'
    config = json.loads((old / 'case_1_seed_0_D_social_evolving_shuffle_0_new/v03_config.json').read_text())
    diagnostic, _ = run(output / 'legacy_replay', mode='legacy', size=67, seed=0,
                        terrain=old / 'terrain_0.json', ticks=1500, spawns=config['environment']['spawns'])
    print('Archived case replay:', diagnostic, flush=True)
    if args.diagnose_only:
        return
    genes = train(output)
    write_json(output / 'protocol.json', dict(
        training_stages=STAGES, holdout_seeds=HOLDOUTS, ticks=args.ticks,
        founder_genotypes={size: fingerprint(gene) for size, gene in genes.items()},
        conditions=['cold_off', 'cold_on', 'trained_off', 'trained_on', 'random', 'rule'],
        resource_fraction=.35, population=12, cap=24,
    ))
    results = []
    for seed in HOLDOUTS:
        terrain = environment(output, seed)
        for mode in ('random', 'rule'):
            row, _ = run(output / f'{seed}_{mode}', mode=mode, size=8, seed=seed,
                         terrain=terrain, ticks=args.ticks, learning=False)
            results.append(row)
        for size in LAYOUTS:
            for trained in (False, True):
                for learning in (False, True):
                    arm = ('trained' if trained else 'cold') + ('_on' if learning else '_off')
                    row, _ = run(output / f'{seed}_{size}_{arm}', mode='candidate', size=size,
                                 seed=seed, terrain=terrain, ticks=args.ticks,
                                 learning=learning, gene=genes[size] if trained else None)
                    results.append(row)
            print(f'Held-out seed {seed}, {size} modules complete', flush=True)
        write_csv(output / 'held_out.csv', results)


if __name__ == '__main__':
    main()
