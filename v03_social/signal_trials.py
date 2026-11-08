"""Offline survival task with a learned two-symbol channel and matched controls."""

import argparse
import random
from pathlib import Path

from first_survival import write_csv, write_json
from organism import DEFAULT_GENOME, Organism

TRAIN_SEEDS = (16100, 16101, 16102)
ARENAS = (
    ('whiteout crossing', 17100, 10, 13),
    ('ash channels', 17200, 9, 15),
)
ARMS = ('learned', 'shuffled', 'blocked', 'untrained', 'perfect')
ROUNDS = 48
MOVE_COST = 3


def pair():
    return [Organism(i, 1, (0, 0), dict(DEFAULT_GENOME)) for i in (1, 2)]


def act(values, rng, epsilon=0.):
    if rng.random() < epsilon or values[0] == values[1]:
        return rng.randrange(2)
    return int(values[1] > values[0])


def cues(rng, rounds):
    result = [i % 2 for i in range(rounds)]
    rng.shuffle(result)
    return result


def cross(organisms, correct, food, danger):
    receiver_before = organisms[-1].energy
    for organism in organisms:
        organism.energy -= MOVE_COST
        if correct:
            organism.energy = min(100, organism.energy + food)
            organism.acquired += food
        else:
            organism.energy -= danger
        organism.age += 1
        organism.check_death()
    return max(-1., min(1., (organisms[-1].energy - receiver_before) / 18))


def train(seed):
    rng = random.Random(seed)
    sender = [[0., 0.], [0., 0.]]
    receiver = [[0., 0.], [0., 0.]]
    training = []
    for episode in range(48):
        organisms = pair()
        correct = seen = 0
        epsilon = .32 if episode < 16 else .12
        for cue in cues(rng, 24):
            token = act(sender[cue], rng, epsilon)
            route = act(receiver[token], rng, epsilon)
            reward = cross(organisms, route == cue, 10 if episode % 2 == 0 else 9,
                           10 if episode % 2 == 0 else 12)
            sender[cue][token] += .24 * (reward - sender[cue][token])
            receiver[token][route] += .24 * (reward - receiver[token][route])
            correct += route == cue
            seen += 1
            if not organisms[-1].alive:
                break
        training.append(dict(seed=seed, episode=episode, exposures=seen, correct=correct,
                             alive=int(organisms[-1].alive)))
    return sender, receiver, training


def evaluate(seed, arena, arm, sender, receiver):
    name, env_seed, food, danger = arena
    cue_rng = random.Random(env_seed + seed)
    action_rng = random.Random(80000 + seed)
    safe_routes = cues(cue_rng, ROUNDS)
    unrelated = safe_routes[:]
    random.Random(env_seed + seed + 7).shuffle(unrelated)
    organisms = pair()
    events = []
    correct = 0
    for i, cue in enumerate(safe_routes):
        token = act(sender[cue], action_rng)
        if arm == 'shuffled':
            token = act(sender[unrelated[i]], action_rng)
        elif arm == 'blocked':
            token = 0
        if arm == 'untrained':
            route = action_rng.randrange(2)
        elif arm == 'perfect':
            token = route = cue
        else:
            route = act(receiver[token], action_rng)
        correct += route == cue
        reward = cross(organisms, route == cue, food, danger)
        events.append(dict(seed=seed, arena=name, arm=arm, round=i+1, cue=cue, token=token,
                           route=route, correct=int(route == cue), energy=organisms[-1].energy,
                           alive=int(organisms[-1].alive), reward=reward))
        if not organisms[-1].alive:
            break
    return dict(seed=seed, arena=name, arm=arm, rounds=len(events), correct=correct,
                route_accuracy=correct/len(events), survivors=sum(o.alive for o in organisms),
                extinction_round=None if organisms[-1].alive else len(events),
                final_energy=organisms[-1].energy, food=organisms[-1].acquired), events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True)
    write_json(out/'protocol.json', dict(train_seeds=TRAIN_SEEDS, arenas=ARENAS, rounds=ROUNDS,
        movement_cost=MOVE_COST, reward='receiver energy change divided by 18, clipped to [-1,1]',
        learning_rate=.24, channel='one bit; sender sees safe route, receiver sees only token',
        control='fixed trained tables with independent shuffled cues or a constant token'))
    rows, events, training = [], [], []
    for seed in TRAIN_SEEDS:
        sender, receiver, samples = train(seed)
        training.extend(samples)
        write_json(out/f'weights_{seed}.json', dict(sender=sender, receiver=receiver))
        for arena in ARENAS:
            for arm in ARMS:
                row, trace = evaluate(seed, arena, arm, sender, receiver)
                rows.append(row)
                events.extend(trace)
    write_csv(out/'results.csv', rows)
    write_csv(out/'decisions.csv', events)
    write_csv(out/'training.csv', training)


if __name__ == '__main__':
    main()
