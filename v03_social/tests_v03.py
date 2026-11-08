import copy,random,tempfile,unittest
from pathlib import Path
from cognition import Brain,CognitiveMemory,new_genome,mutate,LAYOUTS,NeuralPolicy
from social import SocialMemory
from social_sim import SocialSimulation
from evolution import Simulation

class CriticalMechanics(unittest.TestCase):
    def sim(self,folder,**kw):
        return SocialSimulation(population=3,ticks=60,seed=7,output=folder,max_population=8,max_lifespan=3000,resource_fraction=.35,modules=8,**kw)
    def test_exact_layout_and_sparse_numerical_activity(self):
        for count,layout in LAYOUTS.items():
            b=Brain(new_genome(random.Random(2),count));self.assertEqual(len(b.modules),count)
            self.assertEqual(tuple(len(b.groups[g]) for g in b.groups),layout)
            _,ops=b.decide([.3]*32,[0,4,5],random.Random(3),0,True)
            self.assertEqual(len(set(b.active)),3);self.assertGreater(ops,0);self.assertLessEqual(ops,168)
    def test_learning_is_distinct_from_inherited_parameters(self):
        b=Brain(new_genome(random.Random(2),8));original=copy.deepcopy(b.genetic)
        b.decide([.5]*32,[0,4,5],random.Random(3),0,False)
        active=b.active[0];old=copy.deepcopy(b.modules[active].p)
        b.learn(1,25)
        self.assertNotEqual(old,b.modules[active].p);self.assertEqual(original,b.genetic)
        self.assertEqual(Brain(b.genetic).modules[active].p,original['modules'][active])
    def test_weight_and_structural_mutation_bounds(self):
        rng=random.Random(3);g=new_genome(rng,8);start=copy.deepcopy(g)
        for _ in range(60):g=mutate(g,rng,1)
        self.assertNotEqual(g,start);self.assertEqual(len(g['modules']),8)
        for m in g['modules']:
            self.assertTrue(2<=m['n']<=4);self.assertLessEqual(len(m['edges']),12)
            self.assertTrue(all(0<=e[1]<m['n'] and abs(e[2])<=2 for e in m['edges']))
    def test_memory_decay_negative_evidence_and_capacity(self):
        m=CognitiveMemory();m.observe((0,0),25,0,.01)
        self.assertLess(m.estimate((0,0),100,.01)[0],m.estimate((0,0),0,.01)[0])
        m.observe((0,0),0,1,.01);self.assertEqual(m.estimate((0,0),1,.01)[0],0)
        for n in range(100):m.observe((n,0),10,n,.01)
        self.assertLessEqual(len(m.long),64);self.assertLessEqual(len(m.working),8)
    def test_relationship_outcomes_and_bounded_loss(self):
        s=SocialMemory();self.assertEqual(s.bond(1),0)
        s.encounter(1,0,.5);strong=s.bond(1);s.encounter(1,1,-.3)
        self.assertLess(s.bond(1),strong);self.assertTrue(s.observe_death(1,2,(0,0)))
        old=s.loss
        for n in range(100):s.advance([],n)
        self.assertLess(s.loss,old);self.assertLessEqual(len(s.events),8)
        self.assertFalse(s.observe_death(999,101,(0,0)))
    def test_sharing_cost_and_local_death_observation(self):
        with tempfile.TemporaryDirectory() as folder:
            s=self.sim(folder)
            try:
                a,b,c=s.organisms;a.position=b.position=(10,10);c.position=(50,30)
                a.energy=50;b.energy=20;a.share_target=b.id
                total=a.energy+b.energy;s.share(a)
                self.assertAlmostEqual(a.energy+b.energy,total-.2)
                b.social.encounter(a.id,0,.5);c.social.encounter(a.id,0,.5)
                a.health=0;s.step()
                self.assertGreater(b.social.loss,0);self.assertEqual(c.social.loss,0)
            finally:s.close()
    def test_neural_inheritance_fixed_and_evolving(self):
        with tempfile.TemporaryDirectory() as folder:
            s=self.sim(Path(folder)/'fixed',treatment='C_social_fixed')
            d=self.sim(Path(folder)/'evolving')
            try:
                parent=s.organisms[0];child=s.birth(parent)
                self.assertEqual(parent.brain.genetic,child.brain.genetic)
                self.assertIsNot(parent.brain.genetic,child.brain.genetic)
                parent=d.organisms[0];child=d.birth(parent)
                self.assertNotEqual(parent.brain.genetic,child.brain.genetic)
            finally:s.close();d.close()
    def test_reproducibility_and_social_ablation(self):
        with tempfile.TemporaryDirectory() as folder:
            signatures=[]
            for n in range(2):
                s=self.sim(Path(folder)/str(n),treatment='B_neural_nonsocial')
                try:
                    for _ in range(30):s.step()
                    self.assertTrue(all(s.totals[k]==0 for k in ('shares','bonded_loss_events')))
                    self.assertTrue(all(not(o.brain.use.keys() & set(o.brain.groups['social'])) for o in s.organisms))
                    signatures.append((s.metrics(),s.extra_metrics(),[(o.position,o.energy,o.brain.modules[0].p) for o in s.organisms]))
                finally:s.close()
            self.assertEqual(signatures[0],signatures[1])
    def test_shuffled_local_social_signals(self):
        a=SocialMemory();b=SocialMemory()
        for s in (a,b):s.encounter(1,0,.8);s.encounter(2,0,-.8)
        contacts=[(1,(1,0),20),(2,(-1,0),80)]
        normal=a.signals(contacts,(0,0),random.Random(1),False)
        shuffled=b.signals(contacts,(0,0),random.Random(1),True)
        self.assertNotEqual(normal,shuffled);self.assertEqual(normal[4],shuffled[4])
    def test_rule_control_matches_preserved_v02_mechanics(self):
        with tempfile.TemporaryDirectory() as folder:
            a=self.sim(Path(folder)/'v03',treatment='A_rule')
            b=Simulation(population=3,ticks=60,seed=7,output=Path(folder)/'v02',max_population=8,max_lifespan=3000,resource_fraction=.35,lifetime=True)
            try:
                for _ in range(30):a.step();b.step()
                self.assertEqual(a.metrics(),b.metrics())
                self.assertEqual([(o.position,o.energy,o.genome) for o in a.organisms],[(o.position,o.energy,o.genome) for o in b.organisms])
            finally:a.close();b.close()

if __name__=='__main__':unittest.main()
