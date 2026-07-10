"""Run provenance: git sha, timestamps, config hash, baseline ref for the JSONL line."""

from __future__ import annotations

import hashlib
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path


def git_sha(short: bool = True) -> str:
    """Current git commit sha (short by default); 'unknown' outside a repo."""
    try:
        args = ["git", "rev-parse", "--short" if short else "HEAD", "HEAD"]
        if not short:
            args = ["git", "rev-parse", "HEAD"]
        out = subprocess.run(args, capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def run_id(now: datetime | None = None) -> str:
    """Human/file-friendly run id, e.g. ``2026-07-05_14-32`` (matches PLAN §4)."""
    now = now or datetime.now()
    return now.strftime("%Y-%m-%d_%H-%M")


def run_ts(now: datetime | None = None) -> str:
    """ISO-8601 UTC timestamp, e.g. ``2026-07-05T14:32:11Z``."""
    now = now or datetime.now(UTC)
    return now.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_uuid7(now: datetime | None = None) -> uuid.UUID:
    """A fresh UUIDv7 (Python 3.14 native, time-ordered) for the ``Results.id_run`` field.

    Distinct from :func:`run_id` (a human-friendly folder name) and the legacy
    ``uuid7`` string field on schema-v3 lines — this is the canonical run identifier
    on schema-v4 ``Results`` lines.
    """
    return uuid.uuid7()


def config_hash(path: Path) -> str:
    """Short stable hash of a config file's bytes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]


def baseline_ref(source_of_truth: Path, sha: str | None = None) -> str:
    """`<path>@<sha>` reference to the committed oracle used as baseline."""
    return f"{source_of_truth}@{sha or git_sha()}"
