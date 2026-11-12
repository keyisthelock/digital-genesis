"""Homer's private journal, extending the supplied SQLite starter."""
import json
from pathlib import Path
import re
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
STARTER = ROOT / "HOMER_01_Starter_Pack"
sys.path.insert(0, str(STARTER))
from homer_memory import LifeMemory, utc_now


class Journal(LifeMemory):
    """Only lived events belong here. Heritage stays in the separate identity file."""

    def __init__(self, path):
        super().__init__(path)
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS identity_state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE UNIQUE INDEX IF NOT EXISTS homer_activation ON events(event_type)
                WHERE subject='homer' AND event_type='activation';
        """)
        with self.conn:
            self.conn.execute("BEGIN IMMEDIATE")
            marker = self.conn.execute("SELECT value FROM identity_state WHERE key='activation'").fetchone()
            if not marker:
                self.conn.execute(
                    "INSERT OR IGNORE INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (str(uuid4()), "homer", utc_now(), utc_now(), "activation",
                     "HOMER-01 activated.", "system_event", "local-bootstrap",
                     "observed", "[]", '{"agent":"HOMER-01","confidence":1.0,"links":[]}'))
                self.conn.execute("INSERT INTO identity_state VALUES ('activation','created')")

    def remember(self, **kwargs):
        if kwargs.get("subject") != "homer":
            raise ValueError("Creator heritage belongs in the separate identity file")
        return super().remember(**kwargs)

    def event(self, event_id):
        cursor = self.conn.execute("SELECT * FROM events WHERE subject='homer' AND event_id=?", (event_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        result = dict(zip((c[0] for c in cursor.description), row))
        for key in ("metadata", "emotional_tags"):
            result[key] = json.loads(result[key])
        return result

    def review(self):
        ids = self.conn.execute("SELECT event_id FROM events WHERE subject='homer' ORDER BY recorded_at, rowid")
        return [self.event(row[0]) for row in ids]

    def correct(self, event_id, note):
        if self.event(event_id) is None:
            raise ValueError("Unknown lived event")
        return self.remember(subject="homer", event_type="correction", summary=note,
                             source_type="user_message", source_ref="operator-review",
                             certainty="reported", metadata={"agent": "HOMER-01", "confidence": .6,
                                                            "links": [event_id]})

    def retrieve(self, query, *, encoder=None, limit=4):
        if exact := self.event(query):
            candidates = [exact]
        else:
            words = set(re.findall(r"[a-z0-9]{3,}", query.lower()))
            if encoder:
                candidates = encoder(query, self.recent(limit=100))[:limit]
            else:
                candidates = self.recent(limit=100)
                scored = [(len(words & set(re.findall(r"[a-z0-9]{3,}", e["summary"].lower()))), e)
                          for e in candidates]
                candidates = [e for score, e in sorted(scored, key=lambda x: (
                    x[0], x[1]["metadata"].get("priority", 0.0)), reverse=True) if score][:limit]
        # Include attached corrections in the returned record without changing history.
        fixes = [e for e in self.recent(limit=100) if e["event_type"] == "correction"]
        for event in candidates:
            event["corrections"] = [e for e in fixes if event["event_id"] in e["metadata"].get("links", [])][:2]
        return candidates


def local_encoder(path):
    """Load only a user-supplied local MiniLM directory; no remote fallback."""
    path = Path(path).resolve(strict=True)
    if not path.is_dir() or not (path / "modules.json").is_file():
        raise ValueError("Expected an existing SentenceTransformer directory")
    from sentence_transformers import SentenceTransformer
    encoder = SentenceTransformer(str(path), device="cpu", local_files_only=True, trust_remote_code=False)
    if encoder.get_sentence_embedding_dimension() != 384:
        raise ValueError("Expected a 384-dimensional MiniLM encoder")

    def rank(query, events):
        if not events:
            return []
        q, *matrix = encoder.encode([query, *(e["summary"] for e in events)], normalize_embeddings=True)
        ranked = [(float(q @ row), event) for row, event in zip(matrix, events)]
        return [event for score, event in sorted(ranked, key=lambda item: item[0], reverse=True) if score >= .35]
    return rank
