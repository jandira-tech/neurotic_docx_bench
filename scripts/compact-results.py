#!/usr/bin/env python3
"""Move superseded per-doc payloads out of ``results/bench.jsonl`` into gzipped detail files.

Plan reference: ``plans/agent-execution-plan.md`` Chapter 1.5.

``results/bench.jsonl`` is append-only and reached 103 MB over 203 lines. 90% of that is
``per_doc`` and 6.5% ``timings`` — payloads that only the line's *own* run ever needed.
This does NOT rewrite history: for every line that has been superseded by a newer line
with the same identity, the heavy payloads move verbatim into
``results/detail/<id_run>.json.gz`` and the line keeps a ``detail:`` stub pointing at
them. Nothing is discarded; ``hydrate()`` reconstructs the original line.

Identity is ``(vendor, benchmark, tool_version, holdout_mode)``. Holdout is part of it
because a sealed-set line is not superseded by a full-corpus line of the same pin — they
describe different document sets, and the holdout line is still the current view of its
own set.

What stays inline, and why:

- ``scores`` — the per-doc payload that export/gate/accept-scores actually consume, and
  only ~3% of the file. Moving it would put every ranking behind a decompress for almost
  no saving. Keeping it inline is also why RESULTS.md is byte-identical after compaction
  by construction rather than by luck.
- Lines with no ``id_run`` (legacy schema). A detail file needs a unique name; inventing
  one risks collisions that would overwrite one line's payload with another's.

Usage::

    uv run python scripts/compact-results.py --dry-run
    uv run python scripts/compact-results.py
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
from pathlib import Path
from typing import Any, NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSONL = REPO_ROOT / "results" / "bench.jsonl"
DEFAULT_DETAIL = REPO_ROOT / "results" / "detail"

#: Payloads moved out of superseded lines. `scores` is deliberately NOT here.
HEAVY_FIELDS = ("per_doc", "timings")


class Stats(NamedTuple):
    total: int
    compacted: int
    skipped_no_id: int
    bytes_before: int
    bytes_after: int


def _identity(line: dict) -> tuple[str, str, str, str]:
    return (
        str(line.get("vendor") or line.get("tool") or ""),
        str(line.get("benchmark") or line.get("stage") or ""),
        str(line.get("tool_version") or ""),
        # A holdout-only line is a different view, not an older one.
        str(line.get("holdout_mode") or ""),
    )


def hydrate(line: dict, *, root: Path | None = None) -> dict:
    """Return ``line`` with any stubbed payloads read back from its detail file.

    A line with no ``detail`` stub is returned unchanged, so callers can hydrate
    unconditionally without caring whether compaction has run.
    """
    stub = line.get("detail")
    if not stub:
        return line
    path = Path(root or REPO_ROOT) / str(stub)
    if not path.is_file():
        return line
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        payload = json.load(fh)
    merged = dict(line)
    merged.update(payload)
    merged.pop("detail", None)
    return merged


def _write_detail(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # mtime=0: the archive must be reproducible, so re-running the compactor on the same
    # input cannot produce a different file and show up as a spurious diff.
    with gzip.GzipFile(filename="", mode="wb", fileobj=path.open("wb"), mtime=0) as gz:
        gz.write(json.dumps(payload, sort_keys=True).encode("utf-8"))


def compact(
    jsonl_path: Path,
    *,
    detail_dir: Path | None = None,
    root: Path | None = None,
    dry_run: bool = False,
) -> Stats:
    """Compact superseded lines in ``jsonl_path``. Returns what changed.

    ``root`` anchors the ``detail:`` stub. It must be the SAME anchor ``hydrate`` uses
    (the repo root), otherwise the stub is written relative to one directory and read
    relative to another — a mismatch that no test catches if it threads its own root
    through both sides, which is precisely how the first version of this passed.
    """
    jsonl_path = Path(jsonl_path)
    root = Path(root) if root is not None else REPO_ROOT
    detail_dir = Path(detail_dir) if detail_dir is not None else DEFAULT_DETAIL

    raw_lines = [ln for ln in jsonl_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    parsed: list[dict | None] = []
    for ln in raw_lines:
        try:
            parsed.append(json.loads(ln))
        except json.JSONDecodeError:
            parsed.append(None)  # unparseable lines pass through untouched

    # Last index per identity — those keep their payload inline.
    latest: dict[tuple[str, str, str, str], int] = {}
    for i, line in enumerate(parsed):
        if line is not None:
            latest[_identity(line)] = i

    bytes_before = jsonl_path.stat().st_size
    out: list[str] = []
    compacted = skipped_no_id = 0

    for i, (line, raw) in enumerate(zip(parsed, raw_lines, strict=True)):
        if line is None or latest.get(_identity(line)) == i:
            out.append(raw)
            continue
        payload = {f: line[f] for f in HEAVY_FIELDS if f in line}
        if not payload:
            out.append(raw)  # already compacted, or never had payloads → idempotent
            continue
        run_id = line.get("id_run")
        if not run_id:
            skipped_no_id += 1
            out.append(raw)
            continue

        try:
            rel = Path(detail_dir).resolve().relative_to(Path(root).resolve())
        except ValueError as exc:  # detail dir outside the root → stub would be unreadable
            raise ValueError(
                f"detail_dir {detail_dir} is not under root {root}; the `detail:` stub is "
                f"stored root-relative and could not be resolved back",
            ) from exc
        target = Path(detail_dir) / f"{run_id}.json.gz"
        if not dry_run:
            _write_detail(target, payload)
        slim = {k: v for k, v in line.items() if k not in HEAVY_FIELDS}
        slim["detail"] = (rel / f"{run_id}.json.gz").as_posix()
        out.append(json.dumps(slim))
        compacted += 1

    text = "\n".join(out) + "\n"
    if not dry_run:
        # Atomic replace: a crash mid-write must not truncate the results file.
        tmp = jsonl_path.with_name(jsonl_path.name + ".compact.tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, jsonl_path)
        bytes_after = jsonl_path.stat().st_size
    else:
        bytes_after = len(text.encode("utf-8"))

    return Stats(
        total=len(raw_lines),
        compacted=compacted,
        skipped_no_id=skipped_no_id,
        bytes_before=bytes_before,
        bytes_after=bytes_after,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--detail-dir", type=Path, default=DEFAULT_DETAIL)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    stats = compact(args.jsonl, detail_dir=args.detail_dir, dry_run=args.dry_run)
    saved = stats.bytes_before - stats.bytes_after
    print(f"{'(dry run) ' if args.dry_run else ''}{args.jsonl}")
    print(f"  lines              {stats.total}")
    print(f"  compacted          {stats.compacted}")
    print(f"  kept (no id_run)   {stats.skipped_no_id}")
    print(f"  size               {stats.bytes_before / 1e6:.2f} MB → {stats.bytes_after / 1e6:.2f} MB "
          f"({saved / 1e6:+.2f} MB, {100 * saved / stats.bytes_before if stats.bytes_before else 0:.1f}% smaller)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
