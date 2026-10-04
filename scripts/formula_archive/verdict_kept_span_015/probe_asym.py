#!/usr/bin/env -S uv run --script
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Asymmetric-length probes of the Word verdict (wave `asym1`).

Every earlier probe revised a paragraph into one of the same length, so the
kept characters over the longer side and over the shorter side were the same
number. Word's redlines of real documents (bench corpus, 2026-10-03) keep a
lone word of a short paragraph against a long one at 0.01 of the longer side,
and the two bench counter-examples to the 0.12 rule sit at 0.121 and 0.131 of
the shorter side. This wave separates the two denominators: A has `n` words,
B has `n / asym` words (or the reverse, direction `ba`), and `k` words of A
are kept in B, spread evenly, everything else rewritten from a disjoint
vocabulary. `ratio_min` and `ratio_max` are the kept characters over the
shorter and the longer side (spaces included in the sides).

    probe_asym.py OUT        (writes OUT/A, OUT/B, OUT/meta.csv)
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

LONG = [24, 60, 160, 400]
ASYM = [2, 4, 8]
RATIO_MIN = [0.06, 0.10, 0.14, 0.20, 0.30, 0.45]


def spread(short: list[str], kept: list[str], rng: random.Random) -> list[str]:
    """`short` with `kept` inserted at evenly spaced positions, in order."""
    out = list(short)
    k = len(kept)
    step = (len(out) + 1) / (k + 1)
    for i, w in enumerate(kept):
        out.insert(min(len(out), round((i + 1) * step) + i), w)
    return out


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "probes/asym1")
    rows: list[dict] = []
    labels = [lp.para("Section one"), lp.para("Clause")]
    tail = [lp.para("End of section")]
    seen: set[tuple] = set()
    for n in LONG:
        for asym in ASYM:
            m = n // asym
            if m < 3:
                continue
            for rmin in RATIO_MIN:
                # kept words of ~6 letters; the short side has m words and m-1 spaces
                k = max(1, round(rmin * (7 * m - 1) / 6))
                if k > m - 2:
                    continue
                for direction in ("ab", "ba"):
                    key = (n, asym, k, direction)
                    if key in seen:
                        continue
                    seen.add(key)
                    rng = random.Random(7000 + n * 13 + asym * 101 + k * 7 + (direction == "ba"))
                    long_side = lp.prose(lp.VOCAB_A, n, rng)
                    # kept words: evenly spaced words of the long side, in order
                    idx = [round((i + 1) * (n - 1) / (k + 1)) for i in range(k)]
                    kept = [long_side[i] for i in idx]
                    short_side = spread(lp.prose(lp.VOCAB_B, m - k, rng), kept, rng)
                    assert len(short_side) == m, (len(short_side), m)
                    a, b = (long_side, short_side) if direction == "ab" else (short_side, long_side)
                    ta, tb = " ".join(a), " ".join(b)
                    name = f"asym_n{n:03}_x{asym}_k{k:02}_{direction}"
                    lp.docx(out / "A" / f"{name}.docx", labels + [lp.para(ta)] + tail)
                    lp.docx(out / "B" / f"{name}.docx", labels + [lp.para(tb)] + tail)
                    kept_chars = sum(len(w) for w in kept)
                    rows.append({"name": name, "n": n, "m": m, "asym": asym, "k": k, "direction": direction,
                                 "chars_a": len(ta), "chars_b": len(tb), "kept_chars": kept_chars,
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
