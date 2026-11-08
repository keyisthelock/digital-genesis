import random
import tempfile
import unittest
from pathlib import Path
from evolution import Simulation
from organism import DEFAULT_GENOME
from world import World


class RestPolicy:
    def choose(self, organism, observations, rng):
        return 'rest', organism.position


class LifetimeTests(unittest.TestCase):
    def test_scarcity_produces_natural_starvation(self):
        with tempfile.TemporaryDirectory() as directory:
            sim = Simulation(population=4, output=directory, lifetime=True, resource_fraction=0)
            try:
                for _ in range(500):
                    sim.step()
                self.assertGreater(sim.starvations, 0)
                self.assertEqual(sim.world.food, {p: 0 for p in sim.world.food})
                self.assertLessEqual(len(sim.organisms), sim.max_population)
            finally:
                sim.close()

    def test_maturity_energy_conservation_mutation_and_cap(self):
        with tempfile.TemporaryDirectory() as directory:
            sim = Simulation(population=1, max_population=2, output=directory,
                lifetime=True, maturity_age=2, mutation_rate=1)
            try:
                sim.policy = RestPolicy()
                parent = sim.organisms[0]
                parent.energy = 100
                self.assertLess(parent.growth, 1)
                sim.step()
                self.assertEqual(sim.total_births, 0)
                energy_before = parent.energy
                sim.step()
                self.assertEqual(sim.total_births, 1)
                child = sim.organisms[1]
                self.assertEqual(parent.growth, 1)
                self.assertEqual(child.age, 0)
                self.assertFalse(child.mature)
                self.assertEqual(child.energy, 30)
                self.assertLess(parent.energy, energy_before-40)
                self.assertLess(parent.energy+child.energy, energy_before)
                self.assertEqual(child.parent_id, parent.id)
                self.assertEqual(child.generation, parent.generation+1)
                self.assertNotEqual(child.genome, parent.genome)
                parent.energy = 100
                parent.last_birth_age = -10000
                sim.step()
                self.assertEqual(len(sim.organisms), 2)
                self.assertEqual(sim.total_births, 1)
                sim.finish_generation()
                self.assertIs(sim.organisms[0], parent)
            finally:
                sim.close()

    def test_baseline_fixed_genome_and_no_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            sim = Simulation(population=1, output=directory, lifetime=True,
                baseline=True, maturity_age=0, mutation_rate=1)
            try:
                sim.policy = RestPolicy()
                sim.organisms[0].energy = 100
                sim.step()
                self.assertEqual(sim.total_births, 1)
                self.assertTrue(all(o.genome == DEFAULT_GENOME for o in sim.organisms))
            finally:
                sim.close()

    def test_saved_terrain_and_lifetime_repeatability(self):
        with tempfile.TemporaryDirectory() as directory:
            terrain = Path(directory)/'terrain.json'
            World(random.Random(42)).save(terrain)
            a = World.load(terrain, random.Random(1))
            b = World.load(terrain, random.Random(99))
            self.assertEqual(a.tiles, b.tiles)
            self.assertEqual(a.food, b.food)
            self.assertEqual(a.fruit, b.fruit)
            expected = None
            for repeat in range(2):
                sim = Simulation(population=4, output=Path(directory)/str(repeat),
                    terrain=terrain, lifetime=True, resource_fraction=.2, seed=3)
                try:
                    initial = (dict(sim.world.tiles), dict(sim.world.food),
                               [o.position for o in sim.organisms])
                    for _ in range(250):
                        sim.step()
                    result = initial, sim.metrics(), [(o.id, o.genome) for o in sim.organisms]
                    if expected is not None:
                        self.assertEqual(result, expected)
                    expected = result
                finally:
                    sim.close()


if __name__ == '__main__':
    unittest.main()
