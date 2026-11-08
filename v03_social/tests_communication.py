import random
import tempfile
import unittest

from cognition import new_genome
from communication import Communication, SILENCE, broadcast, founder_genome, inherited_genome
from communication_population import CommunicationPopulation
from communication_trials import apply_feedback, make_pair, resolve


class CommunicationTests(unittest.TestCase):
    def test_range_and_energy(self):
        a, b = make_pair(new_genome(random.Random(1),32),2,0)
        message, fee = broadcast(a,b,3,17,distance_limit=2,cost=.125,latency=2)
        self.assertEqual((message.sender,message.receiver,message.symbol,message.arrives_at),(0,1,3,19))
        self.assertEqual((a.energy,b.energy,fee),(64.875,65.,.125))
        b.position=(5,0)
        message, fee=broadcast(a,b,3,21,distance_limit=2,cost=.125,latency=2)
        self.assertIsNone(message)
        self.assertEqual((a.energy,fee),(64.75,.125))

    def test_feedback_is_delayed_and_weights_are_private(self):
        a, b = make_pair(new_genome(random.Random(1),32),2,0)
        before_b=b.signal.genome
        pending=[]
        row=resolve([a,b],'A',(0,1),0,0,True,'intact',.035,2,pending,0)
        self.assertEqual((row['arrived_at'],row['outcome_at'],row['feedback_due']),(2,4,6))
        self.assertEqual((a.signal.updates,b.signal.updates),(0,0))
        apply_feedback(pending,6)
        self.assertEqual((a.signal.updates,b.signal.updates),(1,1))
        snapshot=[list(weights) for weights in b.signal.send]
        a.signal.send[0][0]=.99
        self.assertEqual(b.signal.send,snapshot)
        self.assertEqual(b.signal.genome,before_b)

    def test_blocked_receiver_gets_only_silence(self):
        a, b = make_pair(new_genome(random.Random(1),32),2,0)
        pending=[]
        row=resolve([a,b],'E',(1,0),0,0,False,'blocked',.035,2,pending,0)
        self.assertEqual((row['received'],row['delivered'],row['message_energy']),(str(SILENCE),0,.035))
        apply_feedback(pending,6)
        self.assertEqual((a.signal.updates,b.signal.updates),(0,1))

    def test_inherited_parameters_exclude_parent_runtime_weights(self):
        seed=4
        with tempfile.TemporaryDirectory() as folder:
            sim=CommunicationPopulation(output=folder,population=2,max_population=3,seed=seed,
                modules=32,reproductive_mode='social',founder_a_fraction=.5,communication_mutation=1)
            try:
                for body in sim.organisms:
                    body.age=150
                    body.energy=96
                    body.position=sim.world.land[0]
                    body.signal.send[0][0]=100
                sim.transitions={}
                child,=sim.reproduce_lifetime(sim.organisms)
                ids=child.reproductive_record['parent_ids']
                parents=[next(o.signal.genome for o in sim.organisms if o.id==i) for i in ids]
                expected=inherited_genome(parents,random.Random(seed*1717+child.id),1)
                self.assertEqual(child.signal.genome,expected)
                self.assertEqual(child.signal.send,Communication(expected).send)
                self.assertEqual(child.signal.updates,0)
                self.assertTrue(all(abs(v)<=1 for table in expected for row in table for v in row))
            finally:
                sim.close()

    def test_seeded_founders_have_four_independent_symbols(self):
        genome=founder_genome(random.Random(73))
        a=Communication(genome)
        b=Communication(genome)
        self.assertEqual(len(a.send[0]),4)
        a.send[0][0]=.99
        self.assertEqual(b.send[0][0],genome[0][0][0])
        self.assertEqual(a.genome,genome)


if __name__=='__main__':
    unittest.main()
