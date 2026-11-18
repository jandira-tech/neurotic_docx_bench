#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC

# SPDX-License-Identifier: AGPL-3.0-only

"""The one-row-per-run JSONL ledger.

Appends are atomic: one line per record, written while holding an exclusive
`flock` on the ledger file, then fsynced, so a cancelled pilot leaves a
prefix of complete records rather than a torn line. Whole-file artifacts
(the grade ledger, the config) are replaced atomically via `os.replace`.
"""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel


def append_jsonl(path: Path, records: Iterable[BaseModel]) -> int:
    """Append each record as one JSON line, atomically per line."""

    payload = b""
    count = 0
    for record in records:
        line = json.dumps(
            record.model_dump(mode="json", exclude_none=True),
            ensure_ascii=False,
            sort_keys=True,
        )
        payload += line.encode("utf-8") + b"\n"
        count += 1
    if not payload:
        return 0

    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        offset = 0
        while offset < len(payload):
            offset += os.write(fd, payload[offset:])
        os.fsync(fd)
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
    return count


def write_jsonl_atomic(path: Path, records: Iterable[BaseModel]) -> int:
    """Rewrite the whole ledger via a temp file and `os.replace`."""

    records = list(records)
    tmp_fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as handle:
            for record in records:
                handle.write(
                    json.dumps(
                        record.model_dump(mode="json", exclude_none=True),
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
                handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise
    return len(records)


def read_jsonl(path: Path) -> list[dict]:
    """Read every JSON line; a torn trailing line (crash) stops the read."""

    rows: list[dict] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{number}: damaged ledger line ({exc}); "
                    "the run that wrote it may have been killed mid-append"
                ) from exc
    return rows


def write_json_atomic(path: Path, payload: dict) -> None:
    tmp_fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise
