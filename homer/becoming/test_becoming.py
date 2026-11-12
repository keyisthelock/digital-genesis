from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from ..journal import Journal
from .curriculum import generate, score
from .evolve import task_splits
from .knowledge import Knowledge
from .provenance import CHECKPOINT, archive_hashes
from .runner import ROOT, GoalManager, episode, packet


class BecomingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)

    def test_journal_recall_changes_method_without_answer_leakage(self):
        (self.path/"HOMER_LEARNING_TRACES").mkdir()
        for mode in ("memory","memory_off"):
            episode(self.path,mode,skills=("slope",),rounds=2)
        traces={}
        for mode in ("memory","memory_off"):
            traces[mode]=[json.loads(line) for line in
                          (self.path/"HOMER_LEARNING_TRACES"/f"{mode}.jsonl").read_text().splitlines()]
        a,b=traces.values()
        self.assertEqual([r["observation"] for r in a],[r["observation"] for r in b])
        self.assertEqual([r["passed"] for r in a],[False,True])
        self.assertEqual([r["passed"] for r in b],[False,False])
        self.assertEqual(a[1]["memory_ids"],[a[0]["journal_event"]])
        journal=Journal(self.path/"memory"/"life.sqlite3")
        self.addCleanup(journal.close)
        self.assertEqual(journal.event(a[1]["journal_event"])["metadata"]["links"],a[1]["memory_ids"])
        self.assertTrue(all(r["origin"]=="bounded_method_policy" for r in a+b))

    def test_goal_filters_permissions_and_budget(self):
        cfg=json.loads((ROOT/"HOMER_PERSONALITY_V2.json").read_text())
        goals=GoalManager(cfg)
        t=generate("slope",1)
        self.assertIsNone(goals.select([replace(t,risk=.1),replace(t,cost=2)],{}, {},1)[0])
        self.assertEqual(goals.select([t],{t.skill:0},{},1)[0],t)
        self.assertEqual(goals.select([t],{t.skill:2},{},1),(None,{"abandoned":["slope"]}))

    def test_data_program_and_numeric_guard(self):
        t=generate("dedup_program",3)
        self.assertEqual(score(t,["keep_first"]),(True,"program_tests_passed"))
        self.assertEqual(score(t,["run_python"]),(False,"program_rejected"))
        self.assertFalse(score(generate("slope",3),"1e999999999")[0])

    def test_sources_keep_revision_and_confidence(self):
        db=Knowledge(self.path/"knowledge.sqlite3")
        self.addCleanup(db.close)
        db.ingest(id="old",topic="x",chapter="y",text="Unsupported statement.",provenance="original",confidence=.2)
        db.ingest(id="new",topic="x",chapter="y",text="Corrected statement.",provenance="review",supersedes="old")
        docs=db.retrieve("x","statement")
        self.assertEqual([r["id"] for r in docs],["new"])
        self.assertEqual(docs[0]["supersedes"],"old")

    def test_splits_disjoint_and_packets_lack_answers_or_hidden_cases(self):
        groups=task_splits()
        signatures=[json.dumps(t.packet(),sort_keys=True) for ts in groups.values() for t in ts]
        self.assertEqual(len(signatures),len(set(signatures)))
        t=generate("dedup_program",2)
        public=packet(t,[],[])
        self.assertNotIn("expected",public)
        self.assertNotIn("hidden_cases",public["data"])
        self.assertNotIn(t.key,json.dumps(public))
        self.assertIn(archive_hashes()["omega"], (None, CHECKPOINT))
