"""Separate local knowledge store, with provenance and revision tracking."""
from hashlib import sha256
import math
import re
import sqlite3

from .curriculum import NOTES


def tokens(text):
    return set(re.findall(r"[a-z0-9]{3,}",text.lower()))


class Knowledge:
    def __init__(self,path):
        self.db=sqlite3.connect(path)
        self.db.row_factory=sqlite3.Row
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS docs(id TEXT PRIMARY KEY, topic TEXT, chapter TEXT,
            text TEXT, provenance TEXT, confidence REAL, supersedes TEXT, digest TEXT);
        """)

    def ingest(self, *, id, topic, chapter, text, provenance, confidence=1., supersedes=None):
        if not all(x and x.strip() for x in (id,topic,chapter,text,provenance)) or not 0<=confidence<=1:
            raise ValueError("Source, scope and confidence required")
        with self.db:
            if supersedes and not self.db.execute("SELECT 1 FROM docs WHERE id=? AND topic=?", (supersedes,topic)).fetchone():
                raise ValueError("Unknown source in this topic")
            self.db.execute("INSERT INTO docs VALUES(?,?,?,?,?,?,?,?)",
                            (id,topic,chapter,text,provenance,confidence,supersedes,sha256(text.encode()).hexdigest()))

    def seed(self):
        for key,(chapter,text) in NOTES.items():
            if self.db.execute("SELECT 1 FROM docs WHERE id=?",("lesson-"+key,)).fetchone():
                continue
            src=("homer/autonomy/HOMER_AUTONOMY_REPORT.md, Measured results" if key=="history"
                 else "Digital Genesis 1.8 original educational note")
            self.ingest(id="lesson-"+key,topic=key,chapter=chapter,text=text,provenance=src)

    def retrieve(self, topic, query, limit=2):
        q=tokens(query)
        docs=list(self.db.execute("""SELECT * FROM docs d WHERE NOT EXISTS
                    (SELECT 1 FROM docs newer WHERE newer.supersedes=d.id) ORDER BY d.id"""))
        candidates=[]
        for row in docs:
            words=tokens(row["text"])
            overlap=len(q & words)/math.sqrt(max(1,len(q)*len(words)))
            relevance=(1. if topic==row["topic"] else 0.)+overlap
            if relevance:
                candidates.append((relevance,dict(row)))
        return [r for _,r in sorted(candidates,key=lambda x:x[0],reverse=True)[:limit]]

    def close(self):
        self.db.close()
