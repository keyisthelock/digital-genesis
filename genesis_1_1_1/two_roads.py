"""Isolated Two Roads environment, using the existing World and Organism."""

import random
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "genesis_1_1"))
from experiment import ENGINE, TrialWorld, Organism, DEFAULT_GENOME, SurvivalBrain, SocialMemory
from model import DIRECTIONS, offset

ENERGY = 38.
PENALTY = 12.
LOW_PENALTY = 5.
HORIZON = 5
DELAYS = (2, 3, 4)


@dataclass
class Roads:
    width: int
    height: int
    tiles: dict
    fork: tuple
    starts: tuple
    paths: dict
    goal: tuple
    risky: int
    delay: int

    def public(self):
        return {
            "width": self.width, "height": self.height, "fork": self.fork, "starts": self.starts,
            "tiles": [[*p, tile] for p, tile in self.tiles.items()],
            "paths": self.paths, "goal": self.goal,
        }

    def world(self, rng, body):
        world = TrialWorld.__new__(TrialWorld)
        world.rng, world.tick, world.resource_fraction = rng, 0, 0.
        world.width, world.height, world.tiles = self.width, self.height, self.tiles
        world.food, world.fruit, world.land = {self.goal: 10.}, (0, 0), list(self.tiles)
        world.cap_loss, world.body = 0., body
        return world


def generate(seed, alternate=False, cues=False):
    rng = random.Random(seed)
    risky = rng.randrange(2)
    delay = rng.choice(DELAYS)
    if cues:
        delay = 3
    length = rng.choice((8, 9, 10)) if alternate else rng.choice((6, 7))
    bend = rng.choice((1, 2)) if alternate else 1
    rotate = rng.randrange(4) if alternate else rng.choice((0, 2))
    center = (11, 11)

    def orient(x, y):
        for _ in range(rotate):
            x, y = -y, x
        return center[0]+x, center[1]+y

    def path(side):
        points = [(0, side)]
        points += [(x, side) for x in range(1, length-3)]
        if bend == 2:
            points.append((length-4, 2*side))
        points += [(x, bend*side) for x in range(length-3, length+1)]
        points += [(length, y*side) for y in range(bend-1, -1, -1)]
        return tuple(orient(x, y) for x, y in points)

    paths = {i: path(s) for i, s in enumerate((-1, 1))}
    starts = (orient(-1, 0), orient(-2, 0))
    fork, goal = orient(0, 0), orient(length, 0)
    width = height = 23
    tiles = {(x, y): "water" for y in range(height) for x in range(width)}
    for point in (*starts, fork, *paths[0], *paths[1]):
        tiles[point] = "land"
    if cues:
        for i, points in paths.items():
            tiles[points[0]] = "amber" if i == risky else "blue"
    return Roads(width, height, tiles, fork, starts, paths, goal, risky, delay)


class ConstrainedBrain(SurvivalBrain):
    """Retain the neural policy while applying the same corridor action mask to every arm."""

    def decide(self, features, valid, rng, tick, context):
        return super().decide(features, sorted(set(valid) & set(self.allowed)), rng, tick, context)


def make_body(gene, start):
    body = Organism(1, 0, start, DEFAULT_GENOME.copy(), energy=ENERGY, max_lifespan=5000)
    body.brain = ConstrainedBrain(gene, social=False, learning=False)
    body.local_contacts = []
    body.social = SocialMemory()
    body.brain_energy_parameter, body.brain_energy_op = .000002, .00001
    body.brain_cost = 0.
    return body


def direction(p, q):
    return DIRECTIONS.index((q[0]-p[0], q[1]-p[1]))


def next_visible(local, position, previous):
    return [offset(position, d) for d in DIRECTIONS
            if offset(position, d) != previous and local.get(offset(position, d), ("water", 0))[0] != "water"]
