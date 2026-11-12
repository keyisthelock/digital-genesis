"""Homer-01 local, provenance-preserving life-memory journal (standard library only).

Creator heritage comes from homer_identity.json; it is NOT written as Homer's life.
All Homer episode memories must derive from real observed events or explicit messages.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    subject TEXT NOT NULL CHECK(subject IN ('homer', 'creator')),
    occurred_at TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    event_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    certainty TEXT NOT NULL CHECK(certainty IN ('observed', 'reported', 'inferred')),
    emotional_tags TEXT NOT NULL,
    metadata TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_events_subject_time ON events(subject, occurred_at);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LifeMemory:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def remember(self, *, subject: str, event_type: str, summary: str,
                 source_type: str, source_ref: str, certainty: str,
                 occurred_at: str | None = None, emotional_tags: list[str] | None = None,
                 metadata: dict | None = None) -> str:
        """Write an attributable event. No memory is auto-invented by a language model."""
        if subject not in ('homer', 'creator'):
            raise ValueError('Unknown subject')
        if certainty not in ('observed', 'reported', 'inferred'):
            raise ValueError('Unknown certainty')
        if not summary.strip() or not source_ref.strip():
            raise ValueError('Memories need a summary and a source reference')
        if subject == 'homer' and source_type not in ('simulator', 'user_message', 'agent_action', 'system_event'):
            raise ValueError('Homer autobiographical events require verifiable source types')
        event_id = str(uuid4())
        self.conn.execute(
            'INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            (event_id, subject, occurred_at or utc_now(), utc_now(), event_type,
             summary, source_type, source_ref, certainty,
             json.dumps(emotional_tags or []), json.dumps(metadata or {}))
        )
        self.conn.commit()
        return event_id

    def recent(self, subject: str = 'homer', limit: int = 10) -> list[dict]:
        if subject not in ('homer', 'creator'):
            raise ValueError('Unknown subject')
        columns = ('event_id','subject','occurred_at','recorded_at','event_type',
                   'summary','source_type','source_ref','certainty','emotional_tags','metadata')
        rows = self.conn.execute(
            'SELECT * FROM events WHERE subject=? ORDER BY occurred_at DESC LIMIT ?',
            (subject, max(0, min(limit, 100))))
        output = []
        for row in rows:
            event = dict(zip(columns, row))
            event['emotional_tags'] = json.loads(event['emotional_tags'])
            event['metadata'] = json.loads(event['metadata'])
            output.append(event)
        return output

    def search(self, query: str, subject: str = 'homer', limit: int = 10) -> list[dict]:
        """Bootstrap keyword fallback; replace with opt-in MiniLM embeddings for semantic search."""
        tokens = {w.lower().strip('.,!?') for w in query.split() if len(w.strip('.,!?')) > 2}
        results = self.recent(subject=subject, limit=100)
        scored = [(sum(token in e['summary'].lower() for token in tokens), e) for e in results]
        return [e for score, e in sorted(scored, key=lambda pair: pair[0], reverse=True)
                if score > 0][:limit]

    def forget(self, event_id: str, subject: str = 'homer') -> bool:
        cur = self.conn.execute('DELETE FROM events WHERE event_id=? AND subject=?', (event_id, subject))
        self.conn.commit()
        return cur.rowcount > 0

    def close(self):
        self.conn.close()


def create_first_memory(db_path: str | Path) -> str:
    store = LifeMemory(db_path)
    try:
        if store.recent('homer', limit=1):
            return 'Existing journal preserved; no new initialization event added.'
        event_id = store.remember(
            subject='homer', event_type='activation',
            summary='Homer-01 journal initialized. No prior personal experience is assumed.',
            source_type='system_event', source_ref='local-bootstrap', certainty='observed',
            emotional_tags=['curiosity'])
        return event_id
    finally:
        store.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default='homer_life.sqlite3')
    args = parser.parse_args()
    print(create_first_memory(args.db))
