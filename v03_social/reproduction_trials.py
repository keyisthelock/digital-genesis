"""Five paired v0.3.2 experiments using saved v0.3.1 founders."""

import argparse
import json
import random
import statistics
import time
from collections import Counter
from pathlib import Path

from experiment_v03 import relocate
from first_survival import ROOT, environment, write_csv, write_json
from neural_survival import fingerprint
from reproduction import ReproductiveSimulation

TRAINED = ROOT / 'experiments/first_survival_v031/trained_32.json'
ARMS = {
    'asexual': ('asexual', .5, .35, True, False),
    'random': ('random', .5, .35, True, False),
    'social': ('social', .5, .35, True, False),
    'random_80': ('random', .8, .35, True, False),
    'scarcity_share': ('social', .5, .28, True, False),
    'scarcity_masked': ('social', .5, .28, False, False),
    'rule_asexual': ('asexual', .5, .35, True, True),
    'rule_random': ('random', .5, .35, True, True),
    'rule_scarcity': ('social', .5, .28, True, True),
}
TRIALS = {
    '1_first_partners': ('asexual', 'random', 'rule_asexual', 'rule_random'),
    '2_bond_or_instinct': ('random', 'social'),
    '3_lonely_world': ('random', 'random_80'),
    '4_moderate_scarcity': ('social', 'scarcity_share', 'scarcity_masked', 'rule_scarcity'),
}
LEDGER_COSTS = ('basal', 'brain', 'movement', 'gateway', 'birth_net', 'removed_energy', 'sharing_loss')


def load_births(path):
    with path.open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream]


def diversity(genes):
    if not genes:
        return 0, None
    vectors = [[weight for module in gene['modules'] for weight in module['out'][0]] for gene in genes]
    return (len({fingerprint(gene) for gene in genes}),
            statistics.mean(statistics.pstdev(column) for column in zip(*vectors)))


def run(path, terrain, seed, ticks, spec, genes, *, bodies=None, frozen=False, phases=None):
    mode, ratio, fraction, sharing, rule = spec
    start = time.process_time()
    sim = ReproductiveSimulation(
        output=path, terrain=terrain, population=10, max_population=24,
        ticks=ticks, seed=seed, modules=32, max_lifespan=3000, resource_fraction=fraction,
        treatment='A_rule' if rule else 'D_social_evolving', neural_pool=None if rule else genes,
        body_pool=bodies, learning=not frozen and not rule, freeze=frozen, reproduce=not frozen,
        reproductive_mode=mode, founder_a_fraction=ratio, allow_sharing=sharing,
        brain_energy_parameter=0 if rule else .000002, brain_energy_op=0 if rule else .00001,
    )
    try:
        starts = [o.position for o in sim.organisms]
        initial_food = sum(sim.world.food.values())
        initial_types = Counter(o.reproductive_type for o in sim.organisms)
        if phases:
            phases(sim)
        else:
            for tick in range(ticks):
                if frozen and tick == ticks // 2:
                    relocate(sim.world)
                if sim.step():
                    break
        metrics = sim.metrics()
        sim.finish_generation(reproduce=False)
        births = load_births(path / 'births.jsonl')
        totals = sim.reproductive_totals
        ledger = sim.ledger
        ledger['sharing_loss'] = sim.totals['sharing_loss']
        residual = ledger['living_energy_change'] - ledger['food_retained'] + sum(ledger[k] for k in LEDGER_COSTS)
        assert abs(residual) < 1e-7
        assert metrics['living'] == 10 + len(births) - metrics['deaths'] and len(births) == metrics['births']
        founders = json.loads((path/'founders.json').read_text())
        known = {entry['id']: (1, entry['type'], entry['genome'], entry['neural'])
                 for entry in founders}
        for event in births:
            parents = event['parent_ids']
            assert event['id'] not in known and all(p in known and p < event['id'] for p in parents)
            assert len(set(parents)) == len(parents) == (1 if mode == 'asexual' else 2)
            assert event['parent_types'] == [known[p][1] for p in parents]
            assert event['generation'] == 1 + max(known[p][0] for p in parents)
            assert event['contributions'] == [40 / len(parents)] * len(parents)
            assert event['child_energy'] == 30
            assert len(parents) == 1 or set(event['parent_types']) == {'A', 'B'}
            for parent, genome in zip(parents, event['parent_genomes']):
                assert genome['body'] == known[parent][2]
                assert genome['neural_sha'] == (fingerprint(known[parent][3]) if known[parent][3] else None)
            if len(parents) == 2 and not rule:
                assert set(event['module_sources']) == {0, 1}
            known[event['id']] = (event['generation'], event['reproductive_type'],
                                  event['genome'], event['neural'])
        living = Counter(o.reproductive_type for o in sim.organisms)
        kids = [o for o in sim.organisms if o.parent_id is not None]
        living_genes = [o.brain.genetic for o in sim.organisms if o.brain]
        n_live, spread_live = diversity(living_genes)
        n_born, spread_born = diversity([b['neural'] for b in births if b['neural']])
        config = dict(seed=seed, initial_food=initial_food, spawns=starts)
        write_json(path/'accounting.json', dict(config=config, ledger=ledger, residual=residual))
        return dict(seed=seed, arm=path.name, mode=mode, policy='rule' if rule else 'trained32',
                    resource_fraction=fraction, sharing=sharing, frozen=frozen, initial_food=initial_food,
                    founder_A=initial_types['A'], founder_B=initial_types['B'],
                    survivors=metrics['living'], surviving_offspring=len(kids), alive_A=living['A'],
                    alive_B=living['B'], births=len(births), extinct=int(not sim.organisms),
                    extinction_tick=metrics['ticks'] if not sim.organisms else None, ticks=metrics['ticks'],
                    mature_ticks=totals['mature_ticks'],
                    births_per_1000_mature_ticks=1000*len(births)/max(1, totals['mature_ticks']),
                    encounters=totals['encounters'], opportunities=totals['opportunities'],
                    ready_pairs=totals['ready_pairs'], successful_pairs=totals['successful_pairs'],
                    unsuccessful_opportunities=totals['opportunities']-totals['successful_pairs'],
                    multi_partner_choices=totals['multi_partner_choices'],
                    first_birth_tick=sim.first_birth_tick, parent_A=totals['parent_A'],
                    parent_B=totals['parent_B'], birth_debit=40*len(births), birth_endowment=30*len(births),
                    lineage_depth=sim.max_generation, living_unique_neural=n_live,
                    birth_unique_neural=n_born, living_weight_dispersion=spread_live,
                    birth_weight_dispersion=spread_born, bond_strength=statistics.mean(
                        [record['bond'] for o in sim.organisms for record in o.social.people.values()] or [0.]),
                    selected_bond=(totals['selected_bond_sum']/totals['successful_pairs']
                                   if totals['successful_pairs'] else None),
                    shares=sim.totals['shares'], food=metrics['food_consumed'],
                    fitness=metrics['average_fitness'], brain_ops=sim.totals['neural_ops'],
                    brain_energy=ledger['brain'], energy_residual=residual, cpu_seconds=time.process_time()-start)
    finally:
        sim.close()


def transfer(out, seed, ticks, birth_logs, *, rule=False):
    pools = {mode: load_births(log) for mode, log in birth_logs.items()}
    policy = 'rule' if rule else 'trained32'
    rows = []
    # Each cohort has the same size. Early and late birth IDs cannot overlap.
    cohort_size = min(3, *(len(pool)//2 for pool in pools.values()))
    if cohort_size == 0:
        return rows, dict(seed=seed, policy=policy, status='insufficient disjoint birth cohorts',
                          asexual_births=len(pools['asexual']), paired_births=len(next(
                              pool for mode, pool in pools.items() if mode != 'asexual')))
    eval_seed = seed + 12100
    terrain = environment(out, eval_seed)
    selection = {}
    for mode, pool in pools.items():
        for epoch, cohort in (('early', pool[:cohort_size]), ('late', pool[-cohort_size:])):
            name = f'{eval_seed}_heldout_{policy}_{mode}_{epoch}'
            selection[name] = [dict(id=b['id'], tick=b['tick'], generation=b['generation']) for b in cohort]
            row = run(out/name, terrain, eval_seed, ticks, (mode, .5, .35, True, rule),
                      [b['neural'] for b in cohort], bodies=[b['genome'] for b in cohort], frozen=True)
            rows.append(dict(trial='5_next_generation', source_seed=seed, epoch=epoch,
                             cohort_size=cohort_size, **row))
    write_json(out/f'{eval_seed}_{policy}_cohorts.json', selection)
    return rows, dict(seed=seed, policy=policy, status='evaluated',
                      asexual_births=len(pools['asexual']), paired_births=len(next(
                          pool for mode, pool in pools.items() if mode != 'asexual')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seeds', type=int, choices=range(1, 21), default=3)
    parser.add_argument('--ticks', type=int, default=1500)
    parser.add_argument('--holdout-ticks', type=int, default=500)
    args = parser.parse_args()
    if args.ticks < 1 or args.holdout_ticks < 2:
        parser.error('tick budgets must be positive and holdouts need at least two ticks')
    out = args.output
    out.mkdir(parents=True, exist_ok=False)
    genome = json.loads(TRAINED.read_text())
    write_json(out/'protocol.json', dict(seeds=list(range(args.seeds)), ticks=args.ticks,
        holdout_ticks=args.holdout_ticks, trained_sha=fingerprint(genome), arms=ARMS, trials=TRIALS,
        training_ecology_seed_offset=11100, holdout_ecology_seed_offset=12100,
        transfer_modes={'trained32': ['asexual', 'social'], 'rule': ['asexual', 'random']},
        heldout_relocation_fraction=.5,
        offspring_type_A=.5, compatibility_distance=2))
    results, heldout, exposure = [], [], []
    for i in range(args.seeds):
        seed = 11100 + i
        terrain = environment(out, seed)
        paired = {}
        for arm, spec in ARMS.items():
            paired[arm] = run(out/f'{seed}_{arm}', terrain, seed, args.ticks, spec, [genome])
        for trial, arms in TRIALS.items():
            results.extend(dict(trial=trial, treatment=arm, **paired[arm]) for arm in arms)
        for rule in (False, True):
            modes = ('asexual', 'random' if rule else 'social')
            prefix = 'rule_' if rule else ''
            rows, status = transfer(out, i, args.holdout_ticks, {
                mode: out/f'{seed}_{prefix}{mode}'/'births.jsonl' for mode in modes
            }, rule=rule)
            heldout.extend(rows)
            exposure.append(status)
        write_csv(out/'results.csv', results)
        write_csv(out/'transfer_exposure.csv', exposure)
        if heldout:
            write_csv(out/'held_out.csv', heldout)
        print(f'Seed {seed} complete: {status}', flush=True)


if __name__ == '__main__':
    main()
