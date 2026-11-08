"""Bounded local memory and a replaceable policy interface."""
from collections import OrderedDict
from dataclasses import dataclass, field

DEFAULT_GENOME = dict(food=2.5, curiosity=1.1, caution=2.5, rest=.6, persistence=.4)
DIRECTIONS = ((0, -1), (1, 0), (0, 1), (-1, 0))


class WeightedPolicy:
    def choose(self, organism, observations, rng):
        """Return (action, destination); receives only local observations."""
        o = organism
        visible = {p: (tile, food) for p, tile, food in observations}
        if o.energy < 85 and visible[o.position][1] > 1:
            return 'eat', o.position
        if visible[o.position][0] == 'fruit' and not o.interacted:
            return 'investigate', o.position
        if o.pain == 0 and o.energy > 25 and rng.random() < o.genome['rest'] * .08:
            return 'rest', o.position
        best = None
        for direction, (dx, dy) in enumerate(DIRECTIONS):
            p = o.position[0]+dx, o.position[1]+dy
            if p not in visible or visible[p][0] == 'water':
                continue
            tile, food = visible[p]
            remembered = o.memory.get(p, (0, 0))
            risk = (tile == 'hazard') + remembered[1] / 10
            # Nearby food is sensed; remote remembered food only guides direction.
            attraction = food / 10
            for q, (_, amount) in visible.items():
                if amount > 2:
                    attraction += .08 * amount / (1 + abs(q[0]-p[0]) + abs(q[1]-p[1]))
            for q, (amount, danger) in o.memory.items():
                if amount > 0 and not danger:
                    attraction += .015 * amount / (1 + abs(q[0]-p[0]) + abs(q[1]-p[1]))
            score = (o.genome['food'] * o.hunger * attraction
                     + o.genome['curiosity'] * (p not in o.memory)
                     - o.genome['caution'] * risk * (1 + o.pain / 10)
                     + o.genome['persistence'] * (direction == o.direction)
                     + rng.uniform(-.8, .8))
            if best is None or score > best[0]:
                best = score, p, direction
        if best is None:
            return 'turn', o.position
        o.direction = best[2]
        return 'move', best[1]


@dataclass
class Organism:
    id: int
    generation: int
    position: tuple
    genome: dict
    parent_id: int | None = None
    max_lifespan: int = 600
    direction: int = 0
    energy: float = 65
    health: float = 100
    age: int = 0
    pain: float = 0
    acquired: float = 0
    alive: bool = True
    discovered: bool = False
    interacted: bool = False
    memory: OrderedDict = field(default_factory=OrderedDict)
    visited: set = field(default_factory=set)
    maturity_age: int = 0
    last_birth_age: int = -1000000
    offspring: int = 0
    death_cause: str | None = None

    @property
    def growth(self):
        return 1.0 if self.maturity_age == 0 else min(1.0, .35 + .65*self.age/self.maturity_age)

    @property
    def mature(self):
        return self.age >= self.maturity_age

    def check_death(self):
        if self.energy <= 0:
            self.death_cause = 'starvation'
        elif self.health <= 0:
            self.death_cause = 'damage'
        elif self.age >= self.max_lifespan:
            self.death_cause = 'age'
        if self.death_cause:
            self.alive = False

    @property
    def hunger(self):
        return max(0, 1 - self.energy / 100)

    @property
    def fear(self):
        return sum(v[1] > 0 for v in self.memory.values()) / max(1, len(self.memory))

    @property
    def fitness(self):
        return self.age * .1 + self.acquired * .5 + len(self.visited) * .8

    def step(self, world, rng, policy):
        if not self.alive:
            return []
        observations = world.observe(self.position)
        events = []
        if not self.discovered and any(t == 'fruit' for _, t, _ in observations):
            self.discovered = True
            events.append('discovery')
        action, destination = policy.choose(self, observations, rng)
        self.pain *= .7
        self.age += 1
        self.energy -= .14 + .08 * (1-world.daylight) + .04*(1-self.growth)
        if self.energy <= 0 or self.health <= 0:
            self.check_death()
            return events
        if action == 'move':
            self.position = destination
            self.energy -= .32
        elif action == 'eat':
            gain = world.eat(self.position)
            self.acquired += gain
            self.energy = min(100, self.energy + gain)
        elif action == 'investigate':
            self.interacted = True
            self.energy -= .2
            events.append('interaction')
        elif action == 'turn':
            self.direction = (self.direction+1) % 4
        if world.tiles[self.position] == 'hazard':
            self.pain = 12
            self.health -= 12
        self.visited.add(self.position)
        self.memory[self.position] = (world.food.get(self.position, 0), self.pain)
        self.memory.move_to_end(self.position)
        if len(self.memory) > 64:
            self.memory.popitem(last=False)
        self.check_death()
        return events
