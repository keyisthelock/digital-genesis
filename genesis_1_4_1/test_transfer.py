import unittest

from memory_audit import SOURCE, verified_checkpoint
from transfer import ARMS, Predictor, Scene, memory_bank, run_task, shuffled


class TransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,cls.saved=verified_checkpoint(SOURCE)
        cls.bank=memory_bank()

    def test_identity_and_archived_event_provenance(self):
        self.assertEqual((self.saved.core.id,self.saved.core.age),(1,944))
        self.assertGreater(len(self.bank),20)
        self.assertEqual(len({m.id for m in self.bank}),len(self.bank))
        self.assertEqual({m.observed.property for m in self.bank},
                         {"availability","energy budget","reported availability"})
        self.assertTrue(all(m.tick>0 and m.evidence for m in self.bank))

    def test_ablation_shares_sensory_and_motor_budget(self):
        learner=Predictor(self.bank)
        results=[run_task(self.saved,learner,arm,7031,"effort") for arm in ARMS]
        self.assertTrue(all(r["options"]==results[0]["options"] for r in results))
        self.assertTrue(all(r["neural_ops"]==results[0]["neural_ops"] for r in results))
        self.assertTrue(all(r["comparison_slots"]==results[0]["comparison_slots"] for r in results))
        self.assertGreater(results[0]["retrieved"],0)
        self.assertEqual(results[1]["retrieved"],0)
        self.assertEqual(results[2]["retrieved"],0)
        self.assertFalse(learner.local)

    def test_book_cost_reach_and_inaccurate_entries(self):
        cases=[Scene(seed,"claim",False) for seed in range(20)]
        self.assertTrue(any(any(y!=s.success[i] for i,y in s.book.entries) for s in cases))
        self.assertTrue(any(len(s.book.entries)<2 for s in cases))
        s=cases[0]
        before=s.body.energy
        got,state=s.evidence("read")
        self.assertEqual(got,s.book.entries)
        self.assertEqual(state,"folio opened")
        self.assertLess(s.body.energy,before)
        self.assertEqual(s.world.tick,6)
        s.body.position=(100,100)
        self.assertEqual(s.evidence("read"),((),"unreadable"))

    def test_delayed_physical_result(self):
        a,b=Scene(42,"effort",False),Scene(42,"effort",False)
        ok,x=a.commit(a.success.index(1))
        fail,y=b.commit(b.success.index(0))
        self.assertEqual((ok,fail),(1,0))
        self.assertEqual((x["delay"],y["delay"]),(2,2))
        self.assertLess(x["energy_cost"],y["energy_cost"])

    def test_replay_and_shuffling(self):
        left=shuffled(self.bank,31)
        self.assertEqual(left,shuffled(self.bank,31))
        self.assertEqual(sorted((m.id,m.success) for m in left),sorted((m.id,m.success) for m in self.bank))
        self.assertNotEqual({m.id:m.observed for m in left},{m.id:m.observed for m in self.bank})
        args=(self.saved,Predictor(self.bank),"preserved",7345,"claim")
        self.assertEqual(run_task(*args),run_task(*args))


if __name__=="__main__":
    unittest.main()
