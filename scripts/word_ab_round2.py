#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["loguru", "rich", "typer"]
# ///
"""Round 2+ of the Word driver A/B: combo variants with an inter-variant health gate.

Round 1 (out/ab, out/ab_redline) established the base line; this runner iterates
on top of it — the a/b/a/b loop. Two things round 1 taught the harness:

- A variant can finish with Word degraded (alive, answering nothing) and the
  next variant dies in ``warm()``. Every variant here runs behind
  ``ensure_healthy_word``: responsive Word passes through; an unresponsive one
  gets the kill ladder and a fresh launch; a cold machine is left for preflight.
- The fixture set's true composition: 34 expected failures (30 staged broken +
  4 hidden crashers at staged indices 001/034/052/072) and 66 expected ok. A
  row with ok < 66 has lost healthy documents and cannot win, whatever its wall.

Combo variants are built directly on the SIG+C1 base (crash signal on, crash
limit 1); adjust BASE here if round 1 crowns a different base. Standard round-1
variants (``crash1``, ``merp_kill``) can be rerun by name for the rows round 1
lost to the wedged-Word boundary.

    uv run scripts/word_ab_round2.py run --mode convert
    uv run scripts/word_ab_round2.py run --mode redline -v r2_fast
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Annotated

import typer
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))  # must precede the imports below

import word_ab as wab
import word_pdf as wp
import word_ab_redline as wabr

# The base the combos iterate on — set from round 1's winner before launching.
BASE: dict[str, dict[str, object]] = {
    "watchdogs": {"kill_pass_on_crash": True},
    "convert": {"crash_limit": 1},
}

R2_VARIANTS: dict[str, wab.Variant] = {
    "r2_control": wab.Variant("r2_control", "SIG+C1 base alone: round-1 winner variance check", **{k: dict(v) for k, v in BASE.items()}),
    "r2_fast": wab.Variant("r2_fast", "base + watchdogs poll 0.25 s (MERP sighted sooner)", **{**{k: dict(v) for k, v in BASE.items()}, "watchdogs": {**BASE["watchdogs"], "poll": 0.25}}),  # type: ignore[arg-type]
    "r2_fast_p1": wab.Variant("r2_fast_p1", "r2_fast + progress watcher polls 1 s", **{**{k: dict(v) for k, v in BASE.items()}, "watchdogs": {**BASE["watchdogs"], "poll": 0.25}, "progress": {"poll": 1.0}}),  # type: ignore[arg-type]
    "r2_grace5": wab.Variant("r2_grace5", "base + answer_grace 5 s (close-all verdict sooner)", **{**{k: dict(v) for k, v in BASE.items()}, "session": {"answer_grace": 5.0}}),
    "r2_ae60": wab.Variant("r2_ae60", "base + AppleEvent timeout 60 s (a wedge costs 60, not 240)", **{**{k: dict(v) for k, v in BASE.items()}, "ae_timeout": 60}),
    "r2_quiet": wab.Variant("r2_quiet", "base + open with confirm conversions false add to recent files false", **{**{k: dict(v) for k, v in BASE.items()}, "open_line": "open (POSIX file inP) confirm conversions false add to recent files false"}),
    "r2_keepopen": wab.Variant("r2_keepopen", "base + close only theDoc per item, not every document (fewer AppleEvents on the happy path)", **{**{k: dict(v) for k, v in BASE.items()}, "convert": {**BASE["convert"], "close_documents": False}}),  # type: ignore[dict-item]
    "r2_poll2": wab.Variant("r2_poll2", "base + watchdogs poll every 2 s (half the osascript poll forks; detection pays for it)", **{**{k: dict(v) for k, v in BASE.items()}, "watchdogs": {**BASE["watchdogs"], "poll": 2.0}}),  # type: ignore[arg-type]
    "r2_max": wab.Variant("r2_max", "every knob at once: fast + p1 + grace5 + ae60 + quiet", **{
        **{k: dict(v) for k, v in BASE.items()},
        "watchdogs": {**BASE["watchdogs"], "poll": 0.25},
        "progress": {"poll": 1.0},
        "session": {"answer_grace": 5.0},
        "ae_timeout": 60,
        "open_line": "open (POSIX file inP) confirm conversions false add to recent files false",
    }),
}
# Round 3: round 2's keepopen proved the close-all overhead (~300 s per 100 docs) but
# lost its queue to the 3-pass stall budget ("never reached"); these test whether a
# bigger budget keeps the speed without the loss, and repeat the crash1-vs-control
# head-to-head (SIG's value on a mixed set was within cross-run variance).
R2_VARIANTS.update({
    "r3_keepopen_mp8": wab.Variant("r3_keepopen_mp8", "SIG+C1 + close only theDoc + max_passes 8", **{
        **{k: dict(v) for k, v in BASE.items()},
        "convert": {**BASE["convert"], "close_documents": False, "max_passes": 8}}),  # type: ignore[dict-item]
    "r3_c1_mp8": wab.Variant("r3_c1_mp8", "SIG+C1 + max_passes 8 (isolate the budget knob)", **{
        **{k: dict(v) for k, v in BASE.items()},
        "convert": {**BASE["convert"], "max_passes": 8}}),  # type: ignore[dict-item]
    "r3_crash1_rep1": wab.Variant("r3_crash1_rep1", "repeat of crash1: no crash signal, crash limit 1", convert={"crash_limit": 1}, watchdogs={"kill_pass_on_crash": False}),
    "r3_crash1_rep2": wab.Variant("r3_crash1_rep2", "repeat of crash1: no crash signal, crash limit 1", convert={"crash_limit": 1}, watchdogs={"kill_pass_on_crash": False}),
    "r3_control_rep1": wab.Variant("r3_control_rep1", "repeat of r2_control: SIG+C1", **{k: dict(v) for k, v in BASE.items()}),
    "r3_control_rep2": wab.Variant("r3_control_rep2", "repeat of r2_control: SIG+C1", **{k: dict(v) for k, v in BASE.items()}),
    "r3_crash1_quiet": wab.Variant("r3_crash1_quiet", "no crash signal + crash limit 1 + quiet open (round-2 redline winner minus the signal)", convert={"crash_limit": 1}, watchdogs={"kill_pass_on_crash": False}, open_line="open (POSIX file inP) confirm conversions false add to recent files false"),
})
# Round 4 (2026-11-03, adversarial re-check of the "plateau"): the round-2/3 redline
# spread (410-830 s on one config) decomposes, in the DEBUG logs, into repair-prompt
# stalls on sessions where the 1-s watchdog probe never sees Word's dialog at all
# (says<=8, compare pass 445-731 s) versus sessions where it sees and declines each
# one (says 18-20, compare pass 230-340 s). Two consequences:
# - `open_line` patches only `wp._EXPORT_BATCH*` (the PDF-export tail), never the
#   compare script (`open POSIX file baseP`), so r2_quiet's compare-pass advantage
#   over r2_control was session health, not the quiet open.
# - the tunable cost of a blind session is the nudge path that rescues each prompt:
#   first look at 10 s, then every 15 s, 2 s per press, with 34 fired / 19 pressed
#   in the worst run. r4_rescue keeps SIG+C1 and attacks exactly that: first look
#   at 7 s, then every 10 s, 5 s per press, batch-log poll 2 s, stall reports off
#   (120 s) so their System Events probes stop congesting the blind channel, and
#   the watchdog's own press waits 8 s instead of 3 so fewer prompts fall through.
#   In conversion the median item is 4-5 s (not 2.6 s), so nudge_after stays 10 there.
R2_VARIANTS.update({
    "r4_plain": wab.Variant("r4_plain", "SIG+C1 alone: the round-1 redline champion config (328.9 s), rerun as a today-session reference", **{k: dict(v) for k, v in BASE.items()}),
    "r4_rescue": wab.Variant("r4_rescue", "SIG+C1 + blind-session rescue: nudge 7 s / every 10 s / 5 s presses, batch poll 2 s, stall reports 120 s, watchdog press wait 8 s", **{
        **{k: dict(v) for k, v in BASE.items()},
        "progress": {"poll": 2.0, "stall_after": 120.0, "nudge_after": 7.0, "nudge_every": 10.0, "nudge_wait": 5.0},
        "watchdogs": {**BASE["watchdogs"], "wait": 8.0},
    }),
    "r4_rescue_q": wab.Variant("r4_rescue_q", "r4_rescue + quiet open (the quiet only reaches the PDF tail; kept to stack every proven-neutral knob)", **{
        **{k: dict(v) for k, v in BASE.items()},
        "progress": {"poll": 2.0, "stall_after": 120.0, "nudge_after": 7.0, "nudge_every": 10.0, "nudge_wait": 5.0},
        "watchdogs": {**BASE["watchdogs"], "wait": 8.0},
        "open_line": "open (POSIX file inP) confirm conversions false add to recent files false",
    }),
    "r4_c_rescue": wab.Variant("r4_c_rescue", "SIG+C1 + the rescue knobs at conversion cadence (nudge_after stays 10: median conversion item is 4-5 s)", **{
        **{k: dict(v) for k, v in BASE.items()},
        "progress": {"poll": 2.0, "stall_after": 120.0, "nudge_every": 10.0, "nudge_wait": 5.0},
        "watchdogs": {**BASE["watchdogs"], "wait": 8.0},
    }),
})
ORDER = ["crash1", "merp_kill", "r2_control", "r2_keepopen", "r2_poll2", "r2_fast", "r2_ae60", "r2_quiet", "r2_max"]
R3_ORDER = ["r3_crash1_rep1", "r3_control_rep1", "r3_keepopen_mp8", "r3_c1_mp8", "r3_crash1_rep2", "r3_control_rep2"]
EXPECTED_OK = 66  # 100 - 30 staged broken - 4 hidden crashers (001/034/052/072)

app = typer.Typer(add_completion=False)


def resolve(name: str) -> wab.Variant:
    variant = R2_VARIANTS.get(name) or wab.BY_NAME.get(name)
    if variant is None:
        raise typer.BadParameter(f"unknown variant {name!r}; known: {ORDER}")
    return variant


def ensure_healthy_word() -> None:
    """No variant starts against a degraded Word (round-1 lesson: crash1/merp_kill died here)."""
    session = wp.WordSession()
    if not session._alive():
        logger.info("[gate] Word not running; preflight will launch it")
        return
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if session.responsive():
            logger.info("[gate] Word answers; carrying on")
            return
        time.sleep(2)
    logger.warning("[gate] Word alive but not answering for 20 s; kill ladder then relaunch")
    for cmd in (["pkill", "-x", wp.WORD_PROC], ["pkill", "-9", "-x", wp.WORD_PROC]):
        logger.warning(f"[gate] running: {wp.shown(cmd)}")
        subprocess.run(cmd, capture_output=True, check=False)
        for _ in range(6):
            if not session._alive():
                break
            time.sleep(0.5)
        if not session._alive():
            break
    if not session.warm():
        raise RuntimeError("[gate] Word would not come back after the kill ladder")


@app.command()
def run(
    mode: Annotated[str, typer.Option("--mode", help="convert | redline")] = "convert",
    variant: Annotated[list[str] | None, typer.Option("--variant", "-v")] = None,
    root: Annotated[Path | None, typer.Option()] = None,
    log_dir: Annotated[Path | None, typer.Option()] = None,
) -> None:
    """Run variants (health-gated) on the round-1 fixture sets, appending to this round's results."""
    if mode not in ("convert", "redline"):
        raise typer.BadParameter("--mode must be convert or redline")
    root = root or (Path("out/ab_round2") if mode == "convert" else Path("out/ab_redline_round2"))
    log_dir = log_dir or root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.remove()
    console_id = logger.add(wp.make_console_sink(), colorize=True, level="INFO")
    names = variant or ORDER
    unknown = [n for n in names if n not in R2_VARIANTS and n not in wab.BY_NAME]
    if unknown:
        raise typer.BadParameter(f"unknown variant(s): {unknown}; known: {sorted(set(ORDER) | set(wab.BY_NAME))}")
    src = Path("out/ab/mixed100/docx") if mode == "convert" else None
    if mode == "convert" and not (src and src.is_dir()):
        raise typer.BadParameter(f"no fixture set at {src}; stage first")
    results_path = root / "results.jsonl"
    for name in names:
        v = resolve(name)
        log = log_dir / f"{mode}_{name}.log"
        sink_id = logger.add(str(log), level="DEBUG")
        try:
            logger.info(f"[r2] ===== {name} on {'mixed100' if mode == 'convert' else 'mixed100_pairs'} ({mode}): {v.about}")
            ensure_healthy_word()
            if mode == "convert":
                result = wab.run_variant(v, src, root / "runs" / name, fixture_set="mixed100")
            else:
                result = wabr.run_variant(v, Path("out/ab_redline/a"), Path("out/ab_redline/b"), root / "runs" / name, fixture_set="mixed100_pairs")
            summary = result.summary()
            verdict = "OK-COUNT GOOD" if summary["ok"] >= EXPECTED_OK else f"LOST OUTPUTS (ok={summary['ok']} < {EXPECTED_OK})"
            with results_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({**summary, "mode": mode, "crash_detail": [c.__dict__ for c in result.crashes]}) + "\n")
            logger.info(f"[r2] {name}: {json.dumps(summary)} | {verdict}")
        except Exception as exc:
            logger.error(f"[r2] {name} FAILED to run: {exc}")
            with results_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"variant": name, "mode": mode, "error": str(exc)}) + "\n")
        finally:
            logger.remove(sink_id)  # drop this variant's file sink only; console stays


if __name__ == "__main__":
    app()
