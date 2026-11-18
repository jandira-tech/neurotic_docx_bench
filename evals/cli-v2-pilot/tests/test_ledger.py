#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC

# SPDX-License-Identifier: AGPL-3.0-only

"""Atomic append + read of the JSONL ledger.

The pilot never overwrites a record: every run is appended atomically
while holding an `flock`, then fsynced. A crash mid-write must leave a
prefix of complete lines, never a torn JSON object.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel

from harness.ledger import (
    append_jsonl,
    read_jsonl,
    write_json_atomic,
    write_jsonl_atomic,
)

pytestmark = pytest.mark.integration


class Row(BaseModel):
    n: int


def test_append_then_read_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    n = append_jsonl(path, [Row(n=i) for i in range(5)])
    assert n == 5
    rows = read_jsonl(path)
    assert [r["n"] for r in rows] == [0, 1, 2, 3, 4]


def test_repeated_appends_concatenate(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    append_jsonl(path, [Row(n=1), Row(n=2)])
    append_jsonl(path, [Row(n=3)])
    rows = read_jsonl(path)
    assert [r["n"] for r in rows] == [1, 2, 3]


def test_a_new_ledger_is_readable_only_by_its_owner(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    append_jsonl(path, [Row(n=1)])
    assert path.stat().st_mode & 0o077 == 0


def test_read_jsonl_handles_empty_or_missing(tmp_path: Path) -> None:
    assert read_jsonl(tmp_path / "missing.jsonl") == []
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    assert read_jsonl(empty) == []


def test_write_jsonl_atomic_replaces_in_place(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    append_jsonl(path, [Row(n=1), Row(n=2)])
    write_jsonl_atomic(path, [Row(n=99)])
    assert [r["n"] for r in read_jsonl(path)] == [99]


def test_write_json_atomic_round_trips_payload(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    payload = {"a": 1, "b": [1, 2, 3], "c": {"nested": True}}
    write_json_atomic(path, payload)
    import json

    assert json.loads(path.read_text(encoding="utf-8")) == payload
