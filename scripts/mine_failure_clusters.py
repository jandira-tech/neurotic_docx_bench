#!/usr/bin/env python3
"""Rank OOXML feature/revision tags by how many mean-points a fix could recover.

Plan reference: ``plans/agent-execution-plan.md`` Chapter 4.5 step 2.

The 90/90 campaign is won in the sub-70 tail, not by polishing 93→96. This joins
a vendor's per-document scores with the corpus coverage tags and answers one
question per tag: *if every failing document carrying this tag were lifted to the
target, how much would the vendor's overall mean move?*

    recoverable(tag) = Σ  (target − score_d) / n_total
                       d carrying tag, score_d < threshold

Dividing by ``n_total`` — every scored document, not just the tagged ones — is
what makes the number directly comparable to the headline mean. A tag on 4
documents cannot recover more than a few points no matter how badly they score,
and the ranking says so.

``recoverable`` alone is not enough to aim at. It is a mass measure, so a tag
carried by almost every pair floats to the top by ubiquity: ``rev_ins`` sits on
740 of 763 documents, and "documents containing insertions fail" is a restatement
of "documents fail", not a lead. ``lift`` is the discriminating column —

    lift(tag) = (failing_tagged / tagged) / (failing_total / n_total)

lift 1.0 means the tag is exactly as likely to fail as the corpus average and
carries no information; a universal tag is pinned at 1.0 by construction. Read
the two together: ``recoverable`` says how much a fix is worth, ``lift`` says
whether the tag actually points at anything.

Tags are not disjoint: one document usually carries several, so the columns sum
to more than the total gap. Treat the ranking as "where to look first", not as
an additive budget.

Usage::

    uv run python scripts/mine_failure_clusters.py --vendor jubarte-rust
    uv run python scripts/mine_failure_clusters.py --vendor jubarte-rust --threshold 50 --top 15
    uv run python scripts/mine_failure_clusters.py --scores runs/x/scores.json --json out.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSONL = REPO_ROOT / "results" / "bench.jsonl"
DEFAULT_TAGS = [
    REPO_ROOT / "corpus" / "word_based" / "coverage_tags.json",
    REPO_ROOT / "corpus" / "word_redlines_superdoc" / "coverage_tags.json",
]


class Cluster(NamedTuple):
    tag: str
    n_tagged: int
    n_failing: int
    median_failing: float
    recoverable: float
    fail_rate: float
    lift: float


def load_tags(paths: list[Path]) -> dict[str, set[str]]:
    """Merge coverage files into ``{pair_key_lower: {tag, ...}}``.

    Keys are lower-cased because scorer keys are: ``pipeline.redline_key`` lower-cases,
    so a coverage file that preserves case would join zero rows and the miner would
    silently report "no tags" instead of failing.
    """
    merged: dict[str, set[str]] = {}
    for path in paths:
        if not path.is_file():
            continue
        data = json.loads(path.read_text())
        for key, entry in (data.get("pairs") or {}).items():
            tags = set(entry.get("features") or []) | set(entry.get("revisions") or [])
            merged.setdefault(key.lower(), set()).update(tags)
    return merged


def latest_scores(jsonl_path: Path, vendor: str, benchmark: str = "script_redlines") -> dict[str, float]:
    """Per-document scores from the most recent matching line (by file order)."""
    found: dict[str, float] | None = None
    with jsonl_path.open() as handle:
        for raw in handle:
            raw = raw.strip()
            if not raw:
                continue
            try:
                line = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if line.get("vendor") != vendor or line.get("benchmark") != benchmark:
                continue
            # Only `holdout_mode == "only"` lines are the sealed n=20 view. `"excluded"`
            # is the NORMAL headline run and must be mined; treating any truthy value as
            # holdout silently skipped every current run and mined a stale 164-doc line.
            if line.get("holdout_mode") == "only":
                continue
            scores = line.get("scores")
            if isinstance(scores, dict) and scores:
                found = {str(k).lower(): float(v) for k, v in scores.items()}
    if found is None:
        raise SystemExit(f"no {benchmark} line with per-doc scores for vendor {vendor!r} in {jsonl_path}")
    return found


def mine(
    scores: dict[str, float],
    tags_by_key: dict[str, set[str]],
    *,
    threshold: float = 70.0,
    target: float = 90.0,
) -> tuple[list[Cluster], list[str]]:
    """Rank tags by recoverable mean-points. Returns (clusters, untagged failing keys)."""
    n_total = len(scores)
    if not n_total:
        return [], []

    # Base rate of failure across the whole corpus — the yardstick `lift` divides by.
    base_rate = sum(1 for s in scores.values() if s < threshold) / n_total

    per_tag: dict[str, list[float]] = {}
    per_tag_failing: dict[str, list[float]] = {}
    untagged_failing: list[str] = []

    for key, score in scores.items():
        tags = tags_by_key.get(key, set())
        failing = score < threshold
        if failing and not tags:
            untagged_failing.append(key)
        for tag in tags:
            per_tag.setdefault(tag, []).append(score)
            if failing:
                per_tag_failing.setdefault(tag, []).append(score)

    clusters = [
        Cluster(
            tag=tag,
            n_tagged=len(per_tag[tag]),
            n_failing=len(failing_scores),
            median_failing=statistics.median(failing_scores),
            # Only the shortfall below `target` is recoverable; a doc already above it
            # contributes nothing even if it is below `threshold` (target < threshold).
            recoverable=sum(max(0.0, target - s) for s in failing_scores) / n_total,
            fail_rate=len(failing_scores) / len(per_tag[tag]),
            # base_rate is 0 only when nothing failed, in which case per_tag_failing is
            # empty and this expression is never reached — the guard is for safety.
            lift=(len(failing_scores) / len(per_tag[tag]) / base_rate) if base_rate else 0.0,
        )
        for tag, failing_scores in per_tag_failing.items()
    ]
    clusters.sort(key=lambda c: (-c.recoverable, -c.n_failing, c.tag))
    return clusters, sorted(untagged_failing)


def format_table(clusters: list[Cluster], top: int) -> str:
    rows = clusters[:top]
    if not rows:
        return "  (no failing documents carry any tag)"
    width = max(len(c.tag) for c in rows)
    out = [f"  {'tag'.ljust(width)}  tagged  failing  median  recoverable  fail%   lift"]
    out += [
        f"  {c.tag.ljust(width)}  {c.n_tagged:6}  {c.n_failing:7}  {c.median_failing:6.1f}  "
        f"{c.recoverable:+10.2f}  {c.fail_rate * 100:5.1f}  {c.lift:5.2f}"
        for c in rows
    ]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vendor", default="jubarte-rust")
    parser.add_argument("--benchmark", default="script_redlines")
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--scores", type=Path, help="flat {key: score} JSON instead of --jsonl")
    parser.add_argument("--tags", type=Path, nargs="*", default=DEFAULT_TAGS)
    parser.add_argument("--threshold", type=float, default=70.0, help="a doc below this is 'failing'")
    parser.add_argument("--target", type=float, default=90.0, help="score a fix is assumed to reach")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--json", type=Path, help="also write the full ranking here")
    args = parser.parse_args(argv)

    if args.scores:
        raw = json.loads(args.scores.read_text())
        scores = {str(k).lower(): float(v) for k, v in raw.items()}
    else:
        scores = latest_scores(args.jsonl, args.vendor, args.benchmark)

    tags_by_key = load_tags(list(args.tags))
    joined = sum(1 for k in scores if k in tags_by_key)
    clusters, untagged = mine(scores, tags_by_key, threshold=args.threshold, target=args.target)

    failing = [s for s in scores.values() if s < args.threshold]
    gap = sum(max(0.0, args.target - s) for s in failing) / len(scores)

    print(f"vendor      {args.vendor}  ({args.benchmark})")
    print(f"documents   {len(scores)} scored, {joined} joined to coverage tags ({len(scores) - joined} unjoined)")
    print(f"failing     {len(failing)} below {args.threshold:g}")
    print(f"total gap   {gap:+.2f} mean points if every failing doc reached {args.target:g}")
    print()
    print(format_table(clusters, args.top))
    if untagged:
        print(f"\n  {len(untagged)} failing document(s) carry NO tag — invisible to this ranking:")
        for key in untagged[:10]:
            print(f"    {key}  {scores[key]:.1f}")
        if len(untagged) > 10:
            print(f"    … and {len(untagged) - 10} more")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(
                {
                    "vendor": args.vendor,
                    "benchmark": args.benchmark,
                    "threshold": args.threshold,
                    "target": args.target,
                    "n_scored": len(scores),
                    "n_joined": joined,
                    "total_gap": gap,
                    "clusters": [c._asdict() for c in clusters],
                    "untagged_failing": untagged,
                },
                indent="\t",
            )
            + "\n",
        )
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
