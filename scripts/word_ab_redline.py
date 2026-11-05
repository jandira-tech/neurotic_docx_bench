#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["loguru", "rich", "typer"]
# ///
"""A/B the redline driver on a fixed pair set — the redline half of word_ab.py.

Same variants, same ``applied()`` overrides, same measurement (wall, detect /
recover / resume per crash, nudges, ok/failed/skipped), but the work under test
is ``word_redline.redline_folders`` over the staged ``a/`` and ``b/`` folders
(one base + one next per ``pNNN`` key) instead of ``convert_folder``.

Usage:
    uv run scripts/word_ab_redline.py run -v baseline -v current
    uv run scripts/word_ab_redline.py report
"""

from __future__ import annotations

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))  # must precede the imports below

import word_ab as wab
import word_pdf as wp
import word_redline as wr

RL_ROOT = Path("out/ab_redline")
REDLINE_KWARGS = {"crash_limit", "one_osascript"}  # Variant.convert keys redline_folders takes

app = typer.Typer(add_completion=False)


def run_variant(variant: wab.Variant, a: Path, b: Path, out_dir: Path, *, fixture_set: str) -> wab.RunResult:
    """One measured ``redline_folders`` run under ``variant``, into a fresh ``out_dir``."""
    import shutil

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    records: list[wab.Record] = []
    handler = wab._capture(records)
    session = wp.WordSession()
    started_at = datetime.now(UTC).isoformat(timespec="seconds")
    try:
        with wab.applied(variant, session):
            problem = wr.redline_preflight(session, allow_open_docs=False, close_documents=True)
            if problem:
                raise RuntimeError(problem)
            kwargs: dict[str, object] = {
                "timeout": 300.0,
                "pdf_timeout": 180.0,
                "session": session,
                "close_documents": True,
            }
            kwargs.update({k: v for k, v in variant.convert.items() if k in REDLINE_KWARGS})
            started = time.monotonic()
            with wp.Watchdogs(**variant.watchdogs), wab.BatchLogWatcher() as watcher:  # type: ignore[arg-type]
                results = wr.redline_folders(a, b, out_dir, emit=wr.Emit.PDF, **kwargs)  # type: ignore[arg-type]
            wall = time.monotonic() - started
    finally:
        logger.remove(handler)
    crashes = wab.crashes_from(records, watcher.growth)
    nudges = sum(1 for r in records if wab._NUDGE.search(r.message))
    return wab.RunResult(
        variant=variant.name,
        fixture_set=fixture_set,
        started_at=started_at,
        wall_s=wall,
        documents=len(results),
        ok=sum(1 for r in results if r.ok and not r.skipped),
        failed=sum(1 for r in results if not r.ok),
        skipped=sum(1 for r in results if r.skipped),
        crashes=crashes,
        nudges=nudges,
        notes="",
    )


@app.command()
def run(
    fixture_set: Annotated[str, typer.Option("--set")] = "mixed100_pairs",
    variant: Annotated[list[str] | None, typer.Option("--variant", "-v")] = None,
    root: Annotated[Path, typer.Option()] = RL_ROOT,
    log: Annotated[Path | None, typer.Option()] = None,
) -> None:
    """Run the chosen variants on the staged pair set, one after another, appending to results.jsonl."""
    logger.remove()
    logger.add(wp.make_console_sink(), colorize=True, level="INFO")
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        logger.add(str(log), level="DEBUG")
    names = variant or [v.name for v in wab.VARIANTS]
    unknown = [n for n in names if n not in wab.BY_NAME]
    if unknown:
        raise typer.BadParameter(f"unknown variant(s): {unknown}; known: {sorted(wab.BY_NAME)}")
    a, b = root / "a", root / "b"
    if not (a.is_dir() and b.is_dir()):
        raise typer.BadParameter(f"no staged pairs at {a} / {b}; run word_ab_mixed_stage.py first")
    results_path = root / "results.jsonl"
    for name in names:
        v = wab.BY_NAME[name]
        logger.info(f"[ab] ===== {v.name} on {fixture_set} (redline): {v.about}")
        result = run_variant(v, a, b, root / "runs" / fixture_set / v.name, fixture_set=fixture_set)
        summary = result.summary()
        with results_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**summary, "crash_detail": [c.__dict__ for c in result.crashes]}) + "\n")
        logger.info(f"[ab] {v.name}: {json.dumps(summary)}")


@app.command()
def report(root: Annotated[Path, typer.Option()] = RL_ROOT) -> None:
    """Write AB_REPORT.md from this root's results.jsonl."""
    lines = [json.loads(ln) for ln in (root / "results.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    summaries = [{k: v for k, v in ln.items() if k != "crash_detail"} for ln in lines]
    (root / "AB_REPORT.md").write_text(wab.render_report(summaries, None), encoding="utf-8")
    typer.echo(wab.render_report(summaries, None))


if __name__ == "__main__":
    app()
