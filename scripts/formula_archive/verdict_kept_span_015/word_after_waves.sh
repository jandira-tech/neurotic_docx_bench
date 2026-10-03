#!/usr/bin/env -S uv run --script
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Short-paragraph probes of the Word verdict (wave `short1`).

The 783 probes behind the 0.12 rule judged paragraphs of 200–4800 words.
Two bench fixtures show Word keeping a lone word of a short paragraph under
that ratio (font_color × font_family: 7 words, 0.096; document_100 ×
double_spacing_bold: 12 words, 0.114). This wave asks where the boundary
sits from 6 to 160 words: `k` kept words as lone words (run 1) or pairs
(run 2), evenly spaced, the rest rewritten from a disjoint vocabulary;
group `dot` adds a sentence-final period kept on both sides.

    probe_short.py OUT        (writes OUT/A, OUT/B, OUT/meta.csv)
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

LENGTHS = [6, 8, 10, 12, 16, 20, 30, 40, 60, 80, 120, 160]


def kept_values(n: int) -> list[int]:
    top = max(1, round(0.3 * n))
    ks = list(range(1, top + 1))
    if len(ks) > 10:
        step = (len(ks) - 1) / 9
        ks = sorted({ks[round(i * step)] for i in range(10)})
    return ks


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "probes/short1")
    rows: list[dict] = []
    labels = [lp.para("Section one"), lp.para("Clause")]
    tail = [lp.para("End of section")]
    for group in ("plain", "dot"):
        for n in LENGTHS:
            for k in kept_values(n):
                for run in (1, 2):
                    if run > k:
                        continue
                    rng = random.Random(9000 + n * 31 + k * 7 + run)
                    a = lp.prose(lp.VOCAB_A, n, rng)
                    b, kept, runs = lp.revise(a, k / n, run, rng)
                    if kept != k:
                        continue
                    ta, tb = " ".join(a), " ".join(b)
                    if group == "dot":
                        ta, tb = ta + ".", tb + "."
                    name = f"{group}_n{n:03}_k{k:02}_r{run}"
                    lp.docx(out / "A" / f"{name}.docx", labels + [lp.para(ta)] + tail)
                    lp.docx(out / "B" / f"{name}.docx", labels + [lp.para(tb)] + tail)
                    aset = set(a)
                    kept_chars = sum(len(w) for w in b if w in aset) + (1 if group == "dot" else 0)
                    mx = max(len(ta), len(tb))
                    rows.append({"name": name, "group": group, "n": n, "k": k, "run": run, "runs": runs,
                                 "chars_a": len(ta), "chars_b": len(tb), "kept_chars": kept_chars,
                                 "ratio": round(kept_chars / mx, 4)})
    out.mkdir(parents=True, exist_ok=True)
    with (out / "meta.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} pairs → {out}")


if __name__ == "__main__":
    main()