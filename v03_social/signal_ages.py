"""Learn and test a group signal during the same million-year ecological run."""

import argparse
import json
import random
from collections import Counter
from pathlib import Path

from age_trials import AGE_TICKS, AGES, YEARS_PER_TICK, timeline
from first_survival import environment, write_csv, write_json
from reproduction_trials import ARMS, TRAINED, run
from signal_trials import act

FREEZE_TICK = 6 * AGE_TICKS
ARMS_SIGNAL = ('learned', 'shuffled', 'blocked')
RESOURCE_FLOOR = .60


class FoodGate:
    """A gate on existing food, with an abstract channel inside the cohort."""

    def __init__(self, sim, arm):
        self.sim = sim
        self.arm = arm
        self.eat = sim.original_eat
        self.cues = random.Random(sim.seed_value * 29)
        self.actions = random.Random(sim.seed_value * 31)
        self.noise = random.Random(sim.seed_value * 43)
        self.sender = [[0., 0.], [0., 0.]]
        self.receiver = [[0., 0.], [0., 0.]]
        self.totals = Counter()
        self.frozen_routes = Counter()
        self.by_age = {}

    def __call__(self, position):
        # Never intercept an empty patch or grant food when nobody can signal.
        sim = self.sim
        if sim.world.food.get(position, 0.) <= 1:
            return self.eat(position)
        # The scenario requires a distinct living observer within the cohort.
        if not any(o.alive and o is not sim.actor for o in sim.organisms):
            return 0.
        learning = sim.world.tick <= FREEZE_TICK
        phase = 'training' if learning else 'frozen'
        cue = self.cues.randrange(2)
        epsilon = .22 if learning else 0.
        token = act(self.sender[cue], self.actions, epsilon)
        if not learning and self.arm == 'shuffled':
            token = act(self.sender[self.noise.randrange(2)], self.actions)
        elif not learning and self.arm == 'blocked':
            token = 0
        route = act(self.receiver[token], self.actions, epsilon)
        correct = route == cue
        amount = self.eat(position) if correct else 0.
        if learning:
            retained = min(amount, max(0., 100-sim.actor.energy))
            reward = retained/10 - .25
            self.sender[cue][token] += .24 * (reward-self.sender[cue][token])
            self.receiver[token][route] += .24 * (reward-self.receiver[token][route])
        else:
            self.frozen_routes[cue, token, route] += 1
        self.totals[phase+'_attempts'] += 1
        self.totals[phase+'_correct'] += correct
        self.totals[phase+'_food'] += amount
        age = min(len(AGES)-1, (sim.world.tick-1)//AGE_TICKS)
        age_counts = self.by_age.setdefault(age, Counter())
        age_counts['attempts'] += 1
        age_counts['correct'] += correct
        age_counts['food'] += amount
        return amount


def schedule(sim, arm):
    gate = FoodGate(sim, arm)
    sim.original_eat = gate
    timeline(sim, True, True, RESOURCE_FLOOR)
    write_json(sim.output/'communication.json', dict(
        totals=gate.totals, sender=gate.sender, receiver=gate.receiver,
        frozen_routes=[dict(cue=c, token=t, route=r, count=n)
                       for (c,t,r), n in sorted(gate.frozen_routes.items())],
        by_age=gate.by_age))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seeds', type=int, choices=range(1, 21), default=3)
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True)
    genes = [json.loads(TRAINED.read_text())]
    ticks = len(AGES)*AGE_TICKS
    write_json(out/'protocol.json', dict(
        ages=AGES, ticks_per_age=AGE_TICKS, years_per_tick=YEARS_PER_TICK,
        freeze_tick=FREEZE_TICK, resource_floor=RESOURCE_FLOOR,
        learning_rate=.24, epsilon=.22, arms=ARMS_SIGNAL,
        weights='two group-level action value tables, initialized to zero',
        food='no added food on correct actions; consume only existing patch stock',
        learning='reward equals retained food divided by 10 minus 0.25 per gate attempt',
        cues='independent random binary gate state revealed to sender only',
        controls='all arms learn identically before freeze; control channels modified only afterward'))
    results = []
    for i in range(args.seeds):
        seed = 18100+i
        terrain = environment(out, seed)
        for treatment in ('asexual', 'rule_asexual'):
            for arm in ARMS_SIGNAL:
                spec = (*ARMS[treatment][:2], RESOURCE_FLOOR, *ARMS[treatment][3:])
                path = out/f'{seed}_{treatment}_{arm}'
                row = run(path, terrain, seed, ticks, spec, genes, phases=lambda sim: schedule(sim, arm))
                details = json.loads((path/'communication.json').read_text())
                counts = details['totals']
                attempts = counts.get('frozen_attempts', 0)
                correct = counts.get('frozen_correct', 0)
                results.append(dict(treatment=treatment, channel=arm,
                                    reached_million=int(row['ticks']==ticks and row['survivors']>0),
                                    training_attempts=counts.get('training_attempts', 0),
                                    training_correct=counts.get('training_correct', 0),
                                    frozen_attempts=attempts, frozen_correct=correct,
                                    frozen_accuracy=correct/attempts if attempts else None, **row))
        write_csv(out/'results.csv', results)
        print(f'Combined age and signal seed {seed} complete', flush=True)


if __name__ == '__main__':
    main()
