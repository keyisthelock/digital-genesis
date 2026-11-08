import tempfile
import unittest
from pathlib import Path
from checkpoint import load_snapshot, save_snapshot
from experiment import atomic_replace
from evolution import Simulation
from knowledge import KnowledgeDrive
from knowledge_cautious import CautiousKnowledgeDrive
from organism import Organism, DEFAULT_GENOME


class UpdateTests(unittest.TestCase):
    def test_cautious_drive_protects_reserves_and_avoids_risk_bonus(self):
        o = Organism(1, 1, (0, 0), dict(DEFAULT_GENOME))
        o.energy = 70
        original, cautious = KnowledgeDrive(), CautiousKnowledgeDrive()
        self.assertGreater(original.bonus(o, (1, 0), 0), 0)
        self.assertEqual(cautious.bonus(o, (1, 0), 0), 0)
        o.energy = 95
        self.assertGreater(cautious.bonus(o, (1, 0), 0), 0)
        self.assertLess(cautious.bonus(o, (1, 0), 0), original.bonus(o, (1, 0), 0))
        self.assertEqual(cautious.bonus(o, (1, 0), 1), 0)

    def test_snapshot_recovers_exact_rng_world_and_lifetime_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sim = Simulation(population=3, output=root/'original', lifetime=True,
                knowledge=True, knowledge_variant='cautious')
            restored = []
            try:
                for _ in range(100):
                    sim.step()
                snapshot = root/'checkpoint.pkl'
                save_snapshot(snapshot, [(0, 'cautious_knowledge', sim)], dict(completed_ticks=100), atomic_replace)
                manifest, restored = load_snapshot(snapshot, root/'restored')
                clone = restored[0][2]
                self.assertEqual(manifest['completed_ticks'], 100)
                for _ in range(80):
                    sim.step()
                    clone.step()
                self.assertEqual(sim.metrics(), clone.metrics())
                self.assertEqual(sim.rng.getstate(), clone.rng.getstate())
                self.assertEqual(sim.world.food, clone.world.food)
                self.assertEqual(sim.organisms, clone.organisms)
                snapshot.write_bytes(snapshot.read_bytes()+b'corrupt')
                with self.assertRaises(ValueError):
                    load_snapshot(snapshot, root/'invalid')
            finally:
                sim.close()
                for _, _, clone in restored:
                    clone.close()
