"""Focused regressions for the v0.3.2 reproductive phase."""

import copy
import json
import random
import tempfile
import unittest
from pathlib import Path

from cognition import new_genome
from reproduction import ReproductiveSimulation, recombine


class ReproductionTests(unittest.TestCase):
    def setup_sim(self, root, mode='random', cap=4):
        sim = ReproductiveSimulation(
            output=root, population=2, max_population=cap, seed=17,
            modules=8, reproductive_mode=mode, founder_a_fraction=.5,
            allow_sharing=False, resource_fraction=.35,
        )
        self.addCleanup(sim.close)
        sim.transitions = {}
        a, b = sim.organisms
        for parent in (a, b):
            parent.age = 150
            parent.energy = 90
            parent.position = sim.world.land[0]
        return sim, a, b

    def test_requirements_and_cooldown(self):
        with tempfile.TemporaryDirectory() as folder:
            sim, a, b = self.setup_sim(folder)
            kind = b.reproductive_type
            b.reproductive_type = a.reproductive_type
            self.assertEqual(sim.reproduce_lifetime(sim.organisms), [])
            b.reproductive_type = kind
            b.position = (a.position[0]+3, a.position[1])
            self.assertEqual(sim.reproduce_lifetime(sim.organisms), [])
            b.position = a.position
            b.age = 99
            self.assertEqual(sim.reproduce_lifetime(sim.organisms), [])
            b.age = a.age
            b.energy = 84.99
            self.assertEqual(sim.reproduce_lifetime(sim.organisms), [])
            b.energy = 90
            child, = sim.reproduce_lifetime(sim.organisms)
            self.assertEqual((a.energy, b.energy, child.energy), (70, 70, 30))
            self.assertEqual({a.id, b.id}, set(child.reproductive_record['parent_ids']))
            a.energy = b.energy = 100
            self.assertEqual(sim.reproduce_lifetime(sim.organisms), [])
            sim.close()

    def test_cap_and_asexual_energy(self):
        with tempfile.TemporaryDirectory() as folder:
            sim, a, b = self.setup_sim(Path(folder)/'asexual', 'asexual', cap=3)
            child, = sim.reproduce_lifetime(sim.organisms)
            self.assertEqual(sorted((a.energy,b.energy)), [50,90])
            self.assertEqual(child.energy, 30)
            self.assertEqual(len(child.reproductive_record['parent_ids']), 1)
            sim.close()
            capped, _, _ = self.setup_sim(Path(folder)/'capped', cap=2)
            self.assertEqual(capped.reproduce_lifetime(capped.organisms), [])
            capped.close()

    def test_seeded_genetic_ancestry_and_clean_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = [Path(folder)/str(i) for i in range(2)]
            for path in paths:
                sim, a, b = self.setup_sim(path, 'social')
                inherited = copy.deepcopy(a.brain.genetic)
                a.brain.modules[0].p['out'][0][0] = 123
                a.brain.modules[0].state[0] = 1
                a.brain.memory.observe(a.position, 9, a.age, a.brain.genetic['decay'])
                a.social.encounter(b.id, 0, .2)
                child, = sim.reproduce_lifetime(sim.organisms)
                self.assertEqual(a.brain.genetic, inherited)
                self.assertEqual(child.generation, 2)
                self.assertFalse(child.brain.memory.long)
                self.assertFalse(child.social.people)
                self.assertTrue(all(abs(w)<=2 for m in child.brain.genetic['modules']
                                    for row in m['out'] for w in row))
                sim.close()
                birth = json.loads((path/'births.jsonl').read_text())
                self.assertEqual(birth['contributions'], [20, 20])
                self.assertEqual(set(birth['module_sources']), {0, 1})
            for file in ('births.jsonl', 'partners.jsonl', 'founders.json'):
                self.assertEqual((paths[0]/file).read_bytes(), (paths[1]/file).read_bytes())

    def test_crossover_preserves_valid_sparse_modules(self):
        a, b = (new_genome(random.Random(seed), 8) for seed in (4, 5))
        child, sources, scalars = recombine(a, b, random.Random(7))
        self.assertEqual(set(sources), {0, 1})
        for i, source in enumerate(sources):
            self.assertEqual(child['modules'][i], (a,b)[source]['modules'][i])
            self.assertIsNot(child['modules'][i], (a,b)[source]['modules'][i])
        self.assertEqual(child['lr'], (a,b)[scalars['lr']]['lr'])
        with self.assertRaises(ValueError):
            recombine(a, new_genome(random.Random(7), 16), random.Random(7))

    def test_single_partner_choice_does_not_change_genetics(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = [Path(folder)/mode for mode in ('random','social')]
            for path in paths:
                sim, _, _ = self.setup_sim(path, path.name)
                self.assertEqual(len(sim.reproduce_lifetime(sim.organisms)), 1)
                sim.close()
            self.assertEqual((paths[0]/'births.jsonl').read_bytes(),
                             (paths[1]/'births.jsonl').read_bytes())


if __name__ == '__main__':
    unittest.main()
