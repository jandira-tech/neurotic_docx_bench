# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""Durable queue and publication outbox. SQLite(':memory:') is the test fake."""

import json
import sqlite3
import threading
import uuid
from functools import wraps
from typing import Any


def synchronized(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with self.lock:
            return method(self, *args, **kwargs)

    return wrapped


class State:
    def __init__(self, database: str, id_factory=uuid.uuid7):
        self.id_factory = id_factory
        self.lock = threading.RLock()
        self.db = sqlite3.connect(database, timeout=30, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS queue (
            sequence INTEGER PRIMARY KEY, row_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued', document_json TEXT);
        CREATE TABLE IF NOT EXISTS outbox (
            id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL,
            acknowledged INTEGER NOT NULL DEFAULT 0);
        """)
        self.db.commit()

    @synchronized
    def get(self, key: str, default: Any = None) -> Any:
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    @synchronized
    def set(self, key: str, value: Any) -> None:
        with self.db:
            self.db.execute(
                "INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, json.dumps(value)),
            )

    @synchronized
    def enqueue(self, rows: list[dict], sampler: dict, prefetched_group: int | None = None) -> None:
        # The sampler cursor and queue additions commit together; a crash cannot duplicate draws.
        with self.db:
            sequence = self.db.execute("SELECT COALESCE(MAX(sequence),0) FROM queue").fetchone()[0]
            sequence = max(sequence, self.get("completed", 0))
            self.db.executemany(
                "INSERT INTO queue(sequence,row_json) VALUES (?,?)",
                [
                    (sequence + i + 1, json.dumps({**row, "review_id": str(self.id_factory())}))
                    for i, row in enumerate(rows)
                ],
            )
            self.db.execute(
                "INSERT INTO meta VALUES ('sampler',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (json.dumps(sampler),),
            )
            if prefetched_group is not None:
                self.db.execute(
                    "INSERT INTO meta VALUES ('prefetched_group',?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (json.dumps(prefetched_group),),
                )

    @synchronized
    def queued_download(self) -> tuple[int, dict] | None:
        row = self.db.execute(
            "SELECT sequence,row_json FROM queue WHERE status='queued' ORDER BY sequence LIMIT 1"
        )
        item = row.fetchone()
        return (item[0], json.loads(item[1])) if item else None

    @synchronized
    def downloaded(self, sequence: int, document: dict) -> None:
        with self.db:
            self.db.execute(
                "UPDATE queue SET document_json=?,status='ready' WHERE sequence=?",
                (json.dumps(document), sequence),
            )

    @synchronized
    def next(self) -> tuple[int, dict] | None:
        # Do not skip a queued fixture whose download has not finished yet.
        row = self.db.execute(
            "SELECT sequence,status,document_json FROM queue ORDER BY sequence LIMIT 1"
        ).fetchone()
        return (row[0], json.loads(row[2])) if row and row[1] == "ready" else None

    @synchronized
    def depth(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM queue").fetchone()[0]

    @synchronized
    def finish(self, sequence: int, result: dict, previous: dict) -> None:
        with self.db:
            self.db.execute(
                "INSERT INTO outbox(id,kind,payload) VALUES (?,?,?) ON CONFLICT(id) DO NOTHING",
                (result["id"], "result", json.dumps(result)),
            )
            for key, value in (("completed", sequence), ("previous", previous)):
                self.db.execute(
                    "INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, json.dumps(value)),
                )
            self.db.execute("DELETE FROM queue WHERE sequence=?", (sequence,))

    @synchronized
    def put_outbox(self, identifier: str, kind: str, payload: dict) -> None:
        with self.db:
            self.db.execute(
                "INSERT INTO outbox(id,kind,payload) VALUES (?,?,?) ON CONFLICT(id) DO NOTHING",
                (identifier, kind, json.dumps(payload)),
            )

    @synchronized
    def pending(self) -> list[dict]:
        return [
            dict(row) | {"payload": json.loads(row["payload"])}
            for row in self.db.execute("SELECT * FROM outbox WHERE acknowledged=0 ORDER BY rowid")
        ]

    @synchronized
    def acknowledge(self, identifier: str) -> None:
        with self.db:
            self.db.execute("UPDATE outbox SET acknowledged=1 WHERE id=?", (identifier,))

    @synchronized
    def batch_results(self, first: int, last: int) -> list[dict]:
        return [
            json.loads(row[0])
            for row in self.db.execute(
                "SELECT payload FROM outbox WHERE kind='result' AND "
                "CAST(json_extract(payload,'$.sequence') AS INTEGER) BETWEEN ? AND ? ORDER BY rowid",
                (first, last),
            )
        ]

    @synchronized
    def prune_batch(self, first: int, last: int) -> None:
        with self.db:
            self.db.execute(
                "DELETE FROM outbox WHERE acknowledged=1 AND kind='result' AND "
                "CAST(json_extract(payload,'$.sequence') AS INTEGER) BETWEEN ? AND ?",
                (first, last),
            )
            self.db.execute(
                "DELETE FROM outbox WHERE acknowledged=1 AND kind='batch' AND "
                "CAST(json_extract(payload,'$.last_sequence') AS INTEGER)<=?",
                (last,),
            )

    @synchronized
    def close(self) -> None:
        self.db.close()
