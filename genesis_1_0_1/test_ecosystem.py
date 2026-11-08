import json
import tempfile
import unittest
from pathlib import Path

from ecosystem import PREVIOUS, terrain
from experiment import audit, cluster, make, snapshot


class GenesisTests(unittest.TestCase):
    def test_fostering_inherits_genes_and_removal_preserves_world(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            genome=json.loads((PREVIOUS/'experiments/first_survival_v031/trained_32.json').read_text())
            sim=make(root/'run',terrain(root/'terrain.json',31),31,genome,ticks=9)
            try:
                cluster(sim,31)
                teacher_ids={o.id for o in sim.organisms}
                for _ in range(3):
                    sim.step()
                sim.introduce_fosters(families=1,siblings=2)
                fosters=[o for o in sim.organisms if o.id not in teacher_ids]
                self.assertEqual(len(fosters),2)
                self.assertEqual(fosters[0].parent_id,fosters[1].parent_id)
                self.assertTrue(all(o.signal.updates==0 and o.energy==30 for o in fosters))
                self.assertTrue(all(not (sim.ancestry_roots[o.id]&teacher_ids) for o in fosters))
                frozen=snapshot(sim,{o.id for o in fosters})
                old=frozen[0]['receive'][0][0]
                fosters[0].signal.receive[0][0]=.99
                self.assertEqual(frozen[0]['receive'][0][0],old)
                before=dict(sim.world.food)
                tick=sim.world.tick
                sim.teacher_boundary()
                self.assertEqual(sim.world.tick,tick)
                self.assertEqual(sim.world.food,before)
                self.assertEqual(sim.organisms,fosters)
                for _ in range(3):
                    sim.step()
                self.assertAlmostEqual(audit(sim),0.,places=6)
            finally:
                sim.close()

    def test_isolation_masks_cross_group_contact_and_private_energy(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            genome=json.loads((PREVIOUS/'experiments/first_survival_v031/trained_32.json').read_text())
            sim=make(root/'run',terrain(root/'terrain.json',31),31,genome,ticks=3,channel='isolated')
            try:
                a,b=sim.organisms[:2]
                a.position=b.position
                b.energy=92
                sim.sense()
                self.assertIn((b.id,b.position,65.),a.local_contacts)
                sim.introduce_fosters(families=1,siblings=1)
                newcomer=sim.organisms[-1]
                newcomer.position=a.position
                sim.sense()
                self.assertNotIn(newcomer.id,[identity for identity,_,_ in a.local_contacts])
                self.assertFalse(sim.permitted(a,newcomer))
            finally:
                sim.close()


if __name__=='__main__':
    unittest.main()
