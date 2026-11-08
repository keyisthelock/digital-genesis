import tempfile
import unittest
from pathlib import Path
from evolution import Simulation
from main import Camera


class SimulationTests(unittest.TestCase):
    def test_zoom_anchor_and_map_bounds(self):
        camera = Camera(60, 40)
        position = camera.tile_at(440, 320)
        camera.zoom(2, (440, 320))
        self.assertEqual(camera.tile_at(440, 320), position)
        camera.zoom(.0001, (440, 320))
        self.assertEqual(camera.scale, camera.minimum)
        camera.x = -100000
        camera.clamp()
        self.assertGreaterEqual(camera.x, min(0, 880-60*camera.scale))

    def test_reproducibility(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            for folder in (a, b):
                sim = Simulation(population=8, ticks=25, output=folder)
                for g in range(3):
                    for _ in range(25):
                        sim.step()
                    sim.finish_generation(reproduce=g < 2)
                sim.close()
            for name in ('generations.csv', 'ancestry.jsonl', 'fruit_events.jsonl', 'selected_genomes.json'):
                self.assertEqual((Path(a)/name).read_bytes(), (Path(b)/name).read_bytes())

    def test_energy_death_mutation_and_transition(self):
        with tempfile.TemporaryDirectory() as folder:
            sim = Simulation(population=4, ticks=2, mutation_rate=1, output=folder)
            try:
                old = sim.organisms[:]
                old[1].position = next(p for p, tile in sim.world.tiles.items() if tile == 'land')
                before = old[1].energy
                victim = old[0]
                victim.energy = .001
                sim.step()
                self.assertLess(old[1].energy, before)
                self.assertFalse(victim.alive)
                self.assertGreaterEqual(sim.total_deaths, 1)
                sim.step()
                row = sim.finish_generation()
                self.assertEqual(row['population'], 4)
                self.assertEqual(sim.generation, 2)
                self.assertEqual(sim.tick, 0)
                self.assertFalse(victim.alive)
                parents = {o.id: o for o in old}
                for child in sim.organisms:
                    self.assertNotIn(child.id, parents)
                    self.assertIn(child.parent_id, parents)
                    self.assertNotEqual(child.genome, parents[child.parent_id].genome)
            finally:
                sim.close()

    def test_local_observations_memory_and_fruit(self):
        with tempfile.TemporaryDirectory() as folder:
            sim = Simulation(population=1, output=folder)
            try:
                o = sim.organisms[0]
                o.position = sim.world.fruit
                sim.step()
                self.assertTrue(o.discovered)
                self.assertTrue(o.interacted)
                self.assertEqual(sim.discoveries, 1)
                self.assertLessEqual(len(sim.world.observe(o.position)), 25)
                o.energy = 0
                sim.step()
                age = o.age
                sim.step()
                self.assertEqual(o.age, age)
            finally:
                sim.close()


if __name__ == '__main__':
    unittest.main()
