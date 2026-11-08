"""Individual communication weights and short-range messages for v0.3.3."""

from dataclasses import dataclass
from math import isfinite

from cognition import clip

SYMBOLS = 4
SILENCE = SYMBOLS
LEARNING_RATE = .20


def founder_genome(rng):
    # Identical initialization distributions for all symbols and routes.
    return (tuple(tuple(rng.uniform(-.015, .015) for _ in range(SYMBOLS)) for _ in range(2)),
            tuple(tuple(rng.uniform(-.015, .015) for _ in range(2)) for _ in range(2*(SYMBOLS+1))))


def inherited_genome(parents, rng, mutation_rate=.08):
    if not parents or not 0 <= mutation_rate <= 1:
        raise ValueError('invalid parents or mutation rate')
    def inherit(table, row, column):
        value = rng.choice(parents)[table][row][column]
        return clip(value + rng.gauss(0, .04), -1, 1) if rng.random() < mutation_rate else value

    return tuple(tuple(tuple(inherit(table, row, column) for column in range(len(values)))
                       for row, values in enumerate(rows))
                 for table, rows in enumerate(parents[0]))


def choose(values, rng, epsilon):
    if rng.random() < epsilon:
        return rng.randrange(len(values))
    best = max(values)
    return rng.choice([i for i, value in enumerate(values) if value == best])


class Communication:
    def __init__(self, genome):
        self.genome = tuple(tuple(tuple(row) for row in table) for table in genome)
        self.send, self.receive = [[list(row) for row in table] for table in self.genome]
        self.updates = 0

    def transmit(self, cue, rng, epsilon):
        symbol = choose(self.send[cue], rng, epsilon)
        return symbol, (self.send[cue], symbol)

    def respond(self, own_cue, symbol, neural_scores, rng, epsilon):
        row = self.receive[own_cue*(SYMBOLS+1)+symbol]
        route = choose([value + score for value, score in zip(row, neural_scores)], rng, epsilon)
        return route, (row, route)

    def learn(self, decision, reward):
        row, action = decision
        row[action] += LEARNING_RATE * (clip(reward, -1, 1) - row[action])
        self.updates += 1


@dataclass(frozen=True)
class Message:
    sender: int
    receiver: int
    symbol: int
    sent_at: int
    arrives_at: int


def broadcast(sender, receiver, symbol, tick, *, distance_limit, cost, latency):
    if (not isinstance(symbol, int) or not 0 <= symbol < SYMBOLS or not isfinite(cost)
            or cost < 0 or latency < 1 or distance_limit < 0):
        raise ValueError('invalid message configuration')
    if sender is receiver or not sender.alive or not receiver.alive or sender.energy <= cost:
        return None, 0.
    sender.energy -= cost
    distance = sum(abs(a-b) for a,b in zip(sender.position, receiver.position))
    if distance > distance_limit:
        return None, cost
    return Message(sender.id, receiver.id, symbol, tick, tick+latency), cost
