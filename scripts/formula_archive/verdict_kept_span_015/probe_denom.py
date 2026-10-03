#!/usr/bin/env -S uv run --script
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Denominator probes of the Word verdict (wave `denom1`).

Which side's characters does Word's 0.12 divide the kept characters by? The
symmetric probes could not say; 39 asymmetric cells said the longer side
(38 replaced). This wave asks the same question with fine steps: long side
`n` words, short side `n / asym` words, and `k` kept words chosen so the
kept characters over the LONGER side land on `ratio_max` targets straddling
0.12 (0.09 … 0.14); the kept over the SHORTER side is then `asym` times
larger. Both directions (A long or B long), lone kept words (run 1) and runs
of 4 for the longer paragraphs. A cell with ratio_max < 0.12 ≤ ratio_min
separates the two readings.

    probe_denom.py OUT        (writes OUT/A, OUT/B, OUT/meta.csv)
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import long_paragraph_probes as lp  # noqa: E402

lp.PUNCT = False
lp.VOCAB_A = lp.pseudo_vocab(101, 3000, None)
lp.VOCAB_B = [w for w in lp.pseudo_vocab(202, 4000, None) if w not in set(lp.VOCAB_A)][:3000]
assert not set(lp.VOCAB_A) & set(lp.VOCAB_B)

LONG = [120, 200, 300, 400, 600]
ASYM = [1.1, 1.25, 1.5, 2.0, 3.0]
RATIO_MAX = [0.09, 0.10, 0.11, 0.115, 0.125, 0.13, 0.14]


def spread(short: list[str], kept: list[list[str]]) -> list[str]:
    """`short` with the kept runs inserted at evenly spaced positions, in order."""
    out = list(short)
    k = len(kept)
    step = (len(out) + 1) / (k + 1)
    off = 0
    for i, run in enumerate(kept):
        at = min(len(out), round((i + 1) * step) + off)
        out[at:at] = run
        off += len(run)
    return out


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "probes/denom1")
    rows: list[dict] = []
    labels = [lp.para("Section one"), lp.para("Clause")]
    tail = [lp.para("End of section")]
    seen: set[tuple] = set()
    for n in LONG:
        for asym in ASYM:
            m = round(n / asym)
            for rmax in RATIO_MAX:
                for run in (1, 4):
                    if run == 4 and n < 300:
                        continue
                    # words average 6 letters; the long side has ~7n-1 characters
                    k = max(run, round(rmax * (7 * n - 1) / 6))
                    k -= k % run
                    if k < run or k > m - 2:
                        continue
                    for direction in ("ab", "ba"):
                        key = (n, m, k, run, direction)
                        if key in seen:
                            continue
                        seen.add(key)
                        rng = random.Random(11000 + n * 13 + m * 7 + k * 3 + run + (direction == "ba"))
                        long_side = lp.prose(lp.VOCAB_A, n, rng)
                        runs = k // run
                        idx = [round((i + 1) * (n - run) / (runs + 1)) for i in range(runs)]
                        kept = [long_side[i:i + run] for i in idx]
                        short_side = spread(lp.prose(lp.VOCAB_B, m - k, rng), kept)
                        assert len(short_side) == m, (len(short_side), m)
                        a, b = (long_side, short_side) if direction == "ab" else (short_side, long_side)
                        ta, tb = " ".join(a), " ".join(b)
                        name = f"denom_n{n:03}_x{asym:.2f}_k{k:03}_r{run}_{direction}"
                        lp.docx(out / "A" / f"{name}.docx", labels + [lp.para(ta)] + tail)
                        lp.docx(out / "B" / f"{name}.docx", labels + [lp.para(tb)] + tail)
                        kept_chars = sum(len(w) for r in kept for w in r)
                        rows.append({"name": name, "n": n, "m": m, "asym": asym, "k": k, "run": run,
                                     "direction": direction, "chars_a": len(ta), "chars_b": len(tb),
                                     "kept_chars": kept_chars,
                                     "ratio_min": round(kept_chars / min(len(ta), len(tb)), 4),
                                     "ratio_max": round(kept_chars / max(len(ta), len(tb)), 4)})
    out.mkdir(parents=True, exist_ok=True)
    with (out / "meta.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} pairs → {out}")


if __name__ == "__main__":
    main()
