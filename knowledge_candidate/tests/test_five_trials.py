import tempfile
import unittest
from pathlib import Path
from five_trials import prepare_world, relocate_food, largest_safe, run_trial, distance


class TrialTests(unittest.TestCase):
    def test_scenario_invariants(self):
        normal,_ = prepare_world(1,0)
        danger,_ = prepare_world(2,0)
        self.assertAlmostEqual(sum(normal.food.values()),sum(danger.food.values()))
        self.assertEqual(len(normal.food),len(danger.food))
        old,total,count = set(normal.food),sum(normal.food.values()),len(normal.food)
        relocate_food(normal)
        self.assertFalse(old.intersection(normal.food))
        self.assertAlmostEqual(sum(normal.food.values()),total)
        self.assertEqual(len(normal.food),count)
        unknown,_ = prepare_world(4,0)
        self.assertEqual(len(largest_safe(unknown)),len(unknown.land))
        gate,spawns = prepare_world(5,0)
        self.assertGreaterEqual(min(distance(gate.fruit,p) for p in spawns),10)
        self.assertGreater(min(distance(gate.fruit,p) for p in gate.food),3)

    def test_short_trial_repeats_exactly_and_accounts_energy(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            world,spawns=prepare_world(3,1)
            terrain=root/'terrain.json'
            world.save(terrain)
            a=run_trial(3,1,'cautious_knowledge',terrain,spawns,root/'a',100)
            b=run_trial(3,1,'cautious_knowledge',terrain,spawns,root/'b',100)
            self.assertEqual(a,b)
            self.assertEqual(a['food_changed'],1)
            self.assertGreater(a['energy_spent'],0)
            self.assertEqual(a['reproductive_energy_debit'],40*a['births'])
