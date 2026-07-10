"""Generate tracked-change redlines with the NATIVE SuperDoc SDK (Python).

For each base→next pair in the corpus manifest, run SuperDoc's Document Engine diff
workflow (capture → compare → apply(changeMode='tracked') → save) to produce
``<base>_<next>_<tool>_redline.docx`` — the same identity the Python bench matches against
the Word oracle. Reference: https://docs.superdoc.dev (Compare documents).

Usage:
  uv run python scripts/generate_superdoc_redlines.py --out $RUN_DIR/docx --tool superdoc \
    [--manifest corpus/word_based/centralized_mapping.csv] \
    [--source-dir corpus/word_based/docx_source] [--status ok] [--limit N]
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from superdoc import AsyncSuperDocClient

_PER_PAIR_TIMEOUT_S = 120
# Upper bound on a single session.close({}) in the finally blocks of
# generate_one. A stuck SuperDoc backend close must not outlive the pair
# timeout (which cancels the body) and stall the batch.
_CLOSE_TIMEOUT_S = 10


@dataclass
class Pair:
    base: str
    next: str
    redline_docx: str = ""
    redline_docx_word: str = ""


def output_names(pair: Pair, tool: str) -> list[str]:
    """Output filenames for a pair — always the single canonical
    ``<base>_<next>_<tool>_redline.docx`` name, regardless of which oracle DOCX variant
    (``redline_docx`` / ``redline_docx_word``) the manifest carries for this pair. The
    oracle PDF is always named ``<base>_<next>_redline.pdf`` (never ``..._word_redline.pdf``),
    so deriving the candidate name from the oracle *DOCX* filename (which sometimes carries
    a ``_word`` infix) produced a candidate key that never matched the oracle PDF key —
    silently dropping ~43/207 pairs from every tool's score.
    """
    return [f"{pair.base}_{pair.next}_{tool}_redline.docx"]


def parse_manifest(csv_path: Path, statuses: set[str]) -> list[Pair]:
    """Return [Pair, ...] for rows whose batch_status is wanted."""
    pairs: list[Pair] = []
    with Path(csv_path).open(newline="") as fh:
        for row in csv.DictReader(fh):
            base = (row.get("base") or "").strip()
            nxt = (row.get("next") or "").strip()
            status = (row.get("batch_status") or "").strip()
            if not base or not nxt:
                continue
            # Only filter when the manifest actually carries a status (older schema); the
            # current manifest dropped batch_status, so an empty status means "include".
            if statuses and status and status not in statuses:
                continue
            pairs.append(Pair(
                base=base,
                next=nxt,
                redline_docx=(row.get("redline_docx") or "").strip(),
                redline_docx_word=(row.get("redline_docx_word") or "").strip(),
            ))
    return pairs


async def generate_one(
    client: AsyncSuperDocClient, base_path: Path, next_path: Path, out_path: Path, idx: int,
) -> None:
    """Doc1 (base) + Doc2 (next) → Doc3 (base with next's edits as tracked changes).

    Both opened sessions are closed in ``finally`` blocks so that a failure at any step
    (``diff.apply`` throws on complex markup, ``save`` hangs, etc.) never leaks a session
    into the shared ``AsyncSuperDocClient`` — leaked sessions make ``__aexit__`` hang.

    The close() calls are themselves wrapped in a short timeout: when
    ``asyncio.wait_for`` cancels this coroutine on timeout, the ``finally`` runs but
    ``await session.close({})`` is itself an awaitable that can hang on a stuck
    SuperDoc backend. Without this guard the close could outlive the
    ``_PER_PAIR_TIMEOUT_S`` deadline and stall the whole batch.
    """
    async def _close(session) -> None:
        try:
            await asyncio.wait_for(session.close({}), timeout=_CLOSE_TIMEOUT_S)
        except (TimeoutError, Exception):
            # Best-effort: a hung close must not propagate and mask the original
            # error, nor stall the batch. The session may leak; run_batch records
            # the pair as failed. __aexit__ on the client reaps what it can.
            pass

    base = await client.open({"sessionId": f"base{idx}", "doc": str(base_path)})
    try:
        target = await client.open({"sessionId": f"target{idx}", "doc": str(next_path)})
        try:
            snapshot = await target.diff.capture({})
        finally:
            await _close(target)
        diff = await base.diff.compare({"targetSnapshot": snapshot})
        await base.diff.apply({"diff": diff, "changeMode": "tracked"})
        await base.save({"out": str(out_path), "force": True})
    finally:
        await _close(base)


async def run_batch(
    *,
    out: Path,
    manifest: Path,
    source_dir: Path,
    statuses: set[str],
    limit: int | None,
    tool: str,
    author: str,
    force: bool,
) -> tuple[int, list[dict], dict[str, int]]:
    out.mkdir(parents=True, exist_ok=True)
    pairs = parse_manifest(manifest, statuses)
    if limit:
        pairs = pairs[:limit]
    ok = 0
    failed: list[dict] = []
    timings: dict[str, int] = {}
    async with AsyncSuperDocClient(user={"name": author, "email": "bench@example.com"}) as client:
        for idx, pair in enumerate(pairs):
            doc = f"{pair.base}_{pair.next}"
            out_names = output_names(pair, tool)
            out_paths = [out / n for n in out_names]
            if not force and all(p.exists() for p in out_paths):
                ok += len(out_paths)
                continue
            base_path = source_dir / f"{pair.base}.docx"
            next_path = source_dir / f"{pair.next}.docx"
            if not base_path.exists() or not next_path.exists():
                failed.append({"doc": doc, "stage": "missing_source", "error": "source docx not found"})
                continue
            try:
                t0 = time.perf_counter_ns()
                await asyncio.wait_for(
                    generate_one(client, base_path, next_path, out_paths[0], idx),
                    timeout=_PER_PAIR_TIMEOUT_S,
                )
                elapsed_ns = time.perf_counter_ns() - t0
                for p in out_paths[1:]:
                    shutil.copy2(out_paths[0], p)
                for name in out_names:
                    timings[name.replace(".docx", "")] = elapsed_ns
                ok += len(out_paths)
            except TimeoutError:
                failed.append({"doc": doc, "stage": "generate", "error": f"timeout after {_PER_PAIR_TIMEOUT_S}s"})
            except Exception as exc:  # one bad pair must not stop the batch
                failed.append({"doc": doc, "stage": "generate", "error": str(exc)})
    return ok, failed, timings


def main(argv: list[str] | None = None) -> int:
    import os

    p = argparse.ArgumentParser(description="SuperDoc native redline generator")
    default_out = os.path.join(os.environ["RUN_DIR"], "docx") if os.environ.get("RUN_DIR") else "out/docx"
    p.add_argument("--out", default=default_out)
    p.add_argument("--manifest", default="corpus/word_based/centralized_mapping.csv")
    p.add_argument("--source-dir", default="corpus/word_based/docx_source")
    p.add_argument("--status", default="ok")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--tool", default="superdoc")
    p.add_argument("--author", default="superdoc")
    p.add_argument("--force", action="store_true")
    args = p.parse_args(argv)

    ok, failed, timings = asyncio.run(
        run_batch(
            out=Path(args.out),
            manifest=Path(args.manifest),
            source_dir=Path(args.source_dir),
            statuses=set(args.status.split(",")) if args.status else set(),
            limit=args.limit,
            tool=args.tool,
            author=args.author,
            force=args.force,
        ),
    )
    # Persist which docs didn't work to $RUN_DIR/generate_failures.json so the bench can
    # fold it into the JSONL line (out is $RUN_DIR/docx → parent is $RUN_DIR).
    out_dir = Path(args.out)
    (out_dir.parent / "generate_failures.json").write_text(json.dumps(failed, indent=2))
    (out_dir.parent / "generate_timings.json").write_text(json.dumps(timings))
    print(f"[superdoc] wrote {ok} redline(s) → {args.out}")
    if failed:
        print(f"[superdoc] {len(failed)} pair(s) skipped (SuperDoc engine couldn't handle them):")
        for f in failed[:10]:
            print(f"  {f['doc']} [{f['stage']}]: {f['error']}")
    # Partial success is fine — the produced redlines still get scored; only a total
    # wipeout (nothing generated) is a hard failure that should abort the run.
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
