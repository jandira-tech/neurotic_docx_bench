#!/usr/bin/env python3
"""Worst-first queue for docx→PDF work, from a release's conversion evidence.

Reads the engine's release_info/ conversion sample and results (the 600
documents a release was scored on), counts the pages of Word's PDF, jubarte's
and LibreOffice's, and writes:

- control50.txt  — 50 documents, drawn seeded and state-balanced, that are
  never diagnosed or tuned against. They only tell whether a change moved
  documents nobody looked at.
- queue.tsv      — the other 550, ranked: a page count that differs from
  Word's first (largest relative difference first), then documents
  LibreOffice beats (largest gap first), then the lowest scores.
- prediction.json — the prediction this ranking rests on, stated before it is
  measured, and its measurement: "a document whose page count differs from
  Word's scores lower than one whose page count matches". The median
  difference is reported with a percentile bootstrap interval, on the queue
  and on the control separately; a prediction that holds on one and not the
  other is not a rule.

usage (from the bench root):
  python3 scripts/release_conv_queue.py ENGINE_DIR VERSION OUT_DIR [--seed N]
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import random
import statistics
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPS = 2000


def pages(path: Path) -> int | None:
    """Page count by pdfinfo; None for a file that is absent or unreadable."""
    if not path.is_file():
        return None
    out = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True)
    for line in out.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    return None


def median_gap(a: list[float], b: list[float], rng: random.Random) -> dict:
    """median(a) − median(b) with a percentile bootstrap 95% interval."""
    if len(a) < 5 or len(b) < 5:
        return {"n_a": len(a), "n_b": len(b), "too_few": True}
    point = statistics.median(a) - statistics.median(b)
    draws = sorted(
        statistics.median(rng.choices(a, k=len(a))) - statistics.median(rng.choices(b, k=len(b)))
        for _ in range(REPS)
    )
    return {
        "n_a": len(a),
        "n_b": len(b),
        "median_a": round(statistics.median(a), 2),
        "median_b": round(statistics.median(b), 2),
        "gap": round(point, 2),
        "ci95": [round(draws[int(0.025 * REPS)], 2), round(draws[int(0.975 * REPS) - 1], 2)],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("engine_dir", type=Path)
    ap.add_argument("version")
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--seed", type=int, default=20261003)
    ap.add_argument("--control", type=int, default=50)
    args = ap.parse_args()

    info = args.engine_dir / "release_info"
    sample = glob.glob(str(info / f"sample_conversion_{args.version}_*.csv"))
    results = glob.glob(str(info / f"results_conversion_{args.version}_*.json"))
    if len(sample) != 1 or len(results) != 1:
        sys.exit(f"{info} does not hold exactly one conversion sample and one results file of {args.version}")
    with open(sample[0], newline="") as f:
        rows = list(csv.DictReader(f))
    tools = json.load(open(results[0]))["tools"]
    ours, theirs = tools["jubarte"]["per_document"], tools["soffice"]["per_document"]

    root = Path.cwd()
    jobs = [(r["stem"], k, root / r[k]) for r in rows for k in ("word_pdf", "jubarte_pdf", "soffice_pdf") if r[k]]
    with ThreadPoolExecutor(8) as pool:
        counted = dict(zip(((s, k) for s, k, _ in jobs), pool.map(lambda j: pages(j[2]), jobs)))

    docs = []
    for r in rows:
        stem = r["stem"]
        word = counted.get((stem, "word_pdf"))
        mine = counted.get((stem, "jubarte_pdf"))
        delta = None if word is None or mine is None else mine - word
        docs.append({
            "stem": stem,
            "state": r["state"],
            "jubarte": ours.get(stem, 0.0),
            "soffice": theirs.get(stem, 0.0),
            "word_pages": word,
            "jubarte_pages": mine,
            "soffice_pages": counted.get((stem, "soffice_pdf")),
            "page_delta": delta,
        })

    # The control: the same share of every state, drawn before anything is ranked.
    rng = random.Random(args.seed)
    by_state: dict[str, list[dict]] = {}
    for d in sorted(docs, key=lambda d: d["stem"]):
        by_state.setdefault(d["state"], []).append(d)
    control: list[dict] = []
    for state in sorted(by_state):
        share = round(args.control * len(by_state[state]) / len(docs))
        control += rng.sample(by_state[state], share)
    held = {d["stem"] for d in control}
    queue = [d for d in docs if d["stem"] not in held]

    def rank(d: dict) -> tuple:
        delta, word = d["page_delta"], d["word_pages"] or 1
        if delta:  # a page count that is not Word's
            return (0, -abs(delta) / word, d["jubarte"])
        if d["soffice"] > d["jubarte"]:  # the competitor is closer to Word
            return (1, d["jubarte"] - d["soffice"], d["jubarte"])
        return (2, d["jubarte"], 0.0)

    queue.sort(key=rank)

    def test(group: list[dict]) -> dict:
        known = [d for d in group if d["page_delta"] is not None]
        off = [d["jubarte"] for d in known if d["page_delta"] != 0]
        on = [d["jubarte"] for d in known if d["page_delta"] == 0]
        return median_gap(on, off, random.Random(42))

    prediction = {
        "stated": "a document whose page count differs from Word's scores lower than one whose page count matches (median of matching minus median of differing is above zero, interval and all)",
        "version": args.version,
        "seed": args.seed,
        "queue": test(queue),
        "control": test(control),
        "page_mismatch": {
            "queue": sum(1 for d in queue if d["page_delta"]),
            "control": sum(1 for d in control if d["page_delta"]),
        },
        "soffice_ahead": {
            "queue": sum(1 for d in queue if d["soffice"] > d["jubarte"]),
            "control": sum(1 for d in control if d["soffice"] > d["jubarte"]),
        },
    }
    for name in ("queue", "control"):
        t = prediction[name]
        t["holds"] = bool(not t.get("too_few") and t["ci95"][0] > 0)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "control50.txt").write_text("".join(d["stem"] + "\n" for d in sorted(control, key=lambda d: d["stem"])))
    cols = ["rank", "stem", "state", "jubarte", "soffice", "word_pages", "jubarte_pages", "soffice_pages", "page_delta"]
    with open(args.out_dir / "queue.tsv", "w", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(cols)
        for i, d in enumerate(queue, 1):
            w.writerow([i] + [round(d[c], 2) if isinstance(d[c], float) else ("" if d[c] is None else d[c]) for c in cols[1:]])
    (args.out_dir / "prediction.json").write_text(json.dumps(prediction, indent=1) + "\n")
    print(json.dumps(prediction, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
