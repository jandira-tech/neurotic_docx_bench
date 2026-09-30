"""Move rows that must never be ranked out of the ranked store, with a manifest.

Nothing is deleted: archived lines go to ``results/archive/bench-<date>.jsonl`` and
``results/archive/MANIFEST.md`` records the reason for each one. The report reads the
archive for its History section; the headline never does.
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from neurotic_docx_bench.ledger import policy as pol
from neurotic_docx_bench.ledger import rows as rws
from neurotic_docx_bench.ledger.registry import Registry

DEFAULT_ARCHIVE_DIR = Path("results/archive")
_MANIFEST_HEADER = (
    "# Archived rows\n\n"
    "| archived on | id_run | vendor | benchmark | run timestamp | reason |\n"
    "| --- | --- | --- | --- | --- | --- |\n"
)


class ArchiveResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    kept: int
    archived: int
    archive_path: Path | None
    manifest_path: Path | None


def archive_reasons(
    data: dict, registry: Registry, retractions: Sequence[pol.Retraction]
) -> tuple[str, ...]:
    row = rws.row_from_bench_line(data, registry)
    if row is None:
        return ("unmapped tool",)
    reasons: list[str] = []
    if row.provenance != "stamped":
        reasons.append("legacy provenance")
    if row.holdout_mode == "only":
        reasons.append("holdout-only run")
    r = pol.find_retraction(row, retractions)
    if r is not None:
        reasons.append(f"retracted: {r.reason}")
    return tuple(reasons)


def split_store(
    store: Path,
    archive_dir: Path,
    *,
    registry: Registry,
    retractions: Sequence[pol.Retraction],
    now: datetime,
    dry_run: bool,
) -> ArchiveResult:
    kept: list[str] = []
    moved: list[tuple[str, dict, tuple[str, ...]]] = []
    for raw in Path(store).read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        data = json.loads(raw)
        reasons = archive_reasons(data, registry, retractions)
        if reasons:
            moved.append((raw, data, reasons))
        else:
            kept.append(raw)
    if dry_run or not moved:
        return ArchiveResult(
            kept=len(kept), archived=len(moved), archive_path=None, manifest_path=None
        )
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"bench-{now.strftime('%Y-%m-%d')}.jsonl"
    with archive_path.open("a", encoding="utf-8") as fh:
        fh.writelines(raw + "\n" for raw, _data, _reasons in moved)
    manifest_path = archive_dir / "MANIFEST.md"
    header = "" if manifest_path.is_file() else _MANIFEST_HEADER
    day = now.strftime("%Y-%m-%d")
    with manifest_path.open("a", encoding="utf-8") as fh:
        fh.write(header)
        fh.writelines(
            f"| {day} | {data.get('id_run')} | {data.get('vendor')} | {data.get('benchmark')} | "
            f"{str(data.get('timestamp'))[:19]} | {'; '.join(reasons)} |\n"
            for _raw, data, reasons in moved
        )
    tmp = Path(store).with_suffix(".jsonl.tmp")
    tmp.write_text("".join(line + "\n" for line in kept), encoding="utf-8")
    os.replace(tmp, store)
    return ArchiveResult(
        kept=len(kept),
        archived=len(moved),
        archive_path=archive_path,
        manifest_path=manifest_path,
    )
