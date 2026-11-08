import json
import tempfile
import unittest
from pathlib import Path
from evolution import Simulation
from organism import Organism, DEFAULT_GENOME
from knowledge import KnowledgeDrive


class KnowledgeTests(unittest.TestCase):
    def test_survival_priority_goals_and_bounded_associations(self):
        o = Organism(1, 1, (0, 0), dict(DEFAULT_GENOME))
        drive = KnowledgeDrive()
        o.energy = 20
        self.assertEqual(drive.bonus(o, (1, 0), 0), 0)
        o.energy = 90
        self.assertGreater(drive.bonus(o, (1, 0), 0), 0)
        self.assertLess(drive.bonus(o, (1, 0), 2), drive.bonus(o, (1, 0), 0))
        for x in range(80):
            o.position = (x, 0)
            drive.register(o, 5, 0)
            o.visited.add(o.position)
        self.assertEqual(drive.discoveries, 80)
        self.assertLessEqual(len(drive.associations), 64)
        self.assertGreater(drive.goals_completed, 0)
        count = drive.discoveries
        drive.register(o, 5, 0)
        self.assertEqual(drive.discoveries, count)

    def test_automatic_learning_journal_and_inherited_drive(self):
        with tempfile.TemporaryDirectory() as directory:
            sim = Simulation(population=1, output=directory, lifetime=True, knowledge=True)
            try:
                parent = sim.organisms[0]
                child = sim.birth(parent)
                self.assertIsNot(parent.knowledge, child.knowledge)
                self.assertEqual(child.knowledge.discoveries, 0)
                for _ in range(100):
                    sim.step()
                sim.flush()
                events = [json.loads(line) for line in (Path(directory)/'learning.jsonl').read_text().splitlines()]
                self.assertTrue(events)
                self.assertTrue(all(e['organism_id'] == 1 for e in events))
                self.assertIn('ambition', parent.genome)
            finally:
                sim.close()


if __name__ == '__main__':
    unittest.main()
