"""Small renewable world; no rendering or external services."""
import math
import json
from pathlib import Path

# Stylized equirectangular continents, not geographic survey data.
CONTINENTS = (
    ((.07,.19),(.18,.12),(.29,.20),(.26,.32),(.20,.39),(.23,.48),(.17,.43),(.12,.32)),
    ((.24,.47),(.32,.51),(.34,.64),(.29,.83),(.26,.90),(.24,.72),(.21,.57)),
    ((.34,.08),(.40,.07),(.42,.19),(.37,.25)),
    ((.43,.27),(.49,.18),(.57,.22),(.60,.31),(.54,.37),(.47,.35)),
    ((.45,.37),(.56,.36),(.61,.50),(.56,.69),(.51,.77),(.46,.63),(.42,.46)),
    ((.56,.19),(.70,.12),(.87,.16),(.94,.27),(.88,.39),(.76,.40),(.74,.52),(.67,.44),(.60,.33)),
    ((.76,.65),(.88,.61),(.93,.73),(.86,.82),(.77,.78)),
    ((.80,.45),(.86,.48),(.89,.55),(.83,.56)),
    ((.05,.94),(.28,.90),(.48,.94),(.70,.90),(.95,.94),(.98,1),(.02,1)),
)


def in_polygon(x, y, polygon):
    inside = False
    previous = polygon[-1]
    for current in polygon:
        ax, ay = previous
        bx, by = current
        if (ay > y) != (by > y) and x < (bx-ax)*(y-ay)/(by-ay)+ax:
            inside = not inside
        previous = current
    return inside


class World:
    def __init__(self, rng, width=60, height=40):
        self.rng, self.width, self.height = rng, width, height
        self.tick = 0
        self.resource_fraction = 1.0
        self.tiles = {}
        self.food = {}
        for y in range(height):
            for x in range(width):
                r = rng.random()
                on_land = any(in_polygon((x+.5)/width, (y+.5)/height, p) for p in CONTINENTS)
                tile = 'water' if not on_land else 'hazard' if r < .025 else 'tree' if r < .28 else 'land'
                self.tiles[x, y] = tile
                if tile == 'tree':
                    self.food[x, y] = rng.uniform(8, 25)
        self.land = [p for p, t in self.tiles.items() if t in ('land', 'tree')]
        self.fruit = rng.choice(self.land)
        self.tiles[self.fruit] = 'fruit'
        self.food.pop(self.fruit, None)

    @property
    def daylight(self):
        return getattr(self, 'daylight_scale', 1.) * (.5 + .5 * math.sin(2 * math.pi * self.tick / 240))

    def advance(self):
        self.tick += 1
        rate = (.025 + .11 * self.daylight) * self.resource_fraction
        for p in self.food:
            self.food[p] = min(30, self.food[p] + rate)

    def save(self, path):
        """Save immutable terrain and initial resource amounts for paired runs."""
        Path(path).write_text(json.dumps(dict(width=self.width, height=self.height,
            fruit=self.fruit, tiles=[[x, y, t] for (x, y), t in self.tiles.items()],
            food=[[x, y, v] for (x, y), v in self.food.items()]), sort_keys=True))

    @classmethod
    def load(cls, path, rng):
        data = json.loads(Path(path).read_text())
        world = cls.__new__(cls)
        world.rng, world.tick, world.resource_fraction = rng, 0, 1.0
        world.width, world.height = data['width'], data['height']
        world.tiles = {(x, y): t for x, y, t in data['tiles']}
        world.food = {(x, y): v for x, y, v in data['food']}
        world.fruit = tuple(data['fruit'])
        world.land = [p for p, t in world.tiles.items() if t in ('land', 'tree', 'fruit')]
        return world

    def scarcity(self, fraction):
        """0 = no food; 1 = original abundance. Applied once at initialization."""
        if not 0 <= fraction <= 1:
            raise ValueError('resource fraction must be between 0 and 1')
        self.resource_fraction = fraction
        for p in self.food:
            self.food[p] *= fraction

    def observe(self, position, radius=2):
        x, y = position
        return [(p, self.tiles[p], self.food.get(p, 0))
                for yy in range(max(0, y-radius), min(self.height, y+radius+1))
                for xx in range(max(0, x-radius), min(self.width, x+radius+1))
                for p in [(xx, yy)]]

    def eat(self, p):
        amount = min(10, self.food.get(p, 0))
        if p in self.food:
            self.food[p] -= amount
        return amount
