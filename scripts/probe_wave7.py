#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Wave 7 of the Word-verdict probes, three questions in one run:

  a. ambiguity — clean disjoint text plus a controlled density of shared
     stopwords in the rewritten gaps (0/5/10/20/35 % of gap words on both
     sides from one 12-word set). How much of the kept fraction does Word's
     alignment lose to ambiguity, and does the verdict follow the clean kept
     fraction or the LCS one?
  b. length — 200, 300, 600, 1200, 2400 words at r=4 and r=16, kept fraction
     from floor−6 % to floor+8 % in 1 % steps (floor from the fitted law), so
     the length term's shape can be read off.
  c. the noisy 1600-word 2-word-run cells (and 800/r=2), with a 3000-word
     vocabulary so 2-word runs are unique.

A 400-word r=4 strip bridges to wave 4 (300-word vocabulary there).

    probe_wave7.py OUT
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
STOP = "the and of to a in that for is on with as".split()
LAW = (0.1020, 0.0440, 0.0058)


def floor_keep(n: int, run: int, chars_per_word: float) -> float:
    """Kept fraction at which the law's floor is met, by fixed point."""
    k = 0.2
    for _ in range(50):
        chars = n * chars_per_word
        runs = k * n / run
        k = LAW[0] + LAW[1] * runs / 100 + LAW[2] * chars / 1000
    # the law counts kept characters without their spaces; `keep` counts words
    return k * chars_per_word / (chars_per_word - 1)


def sprinkle(words: list[str], kept_mask: list[bool], density: float, rng: random.Random) -> list[str]:
    out = list(words)
    for i, w in enumerate(words):
        if not kept_mask[i] and rng.random() < density:
            out[i] = rng.choice(STOP)
    return out


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "probes/wave7")
    rows: list[dict] = []
    labels = [lp.para("Section one"), lp.para("Clause")]
    tail = [lp.para("End of section")]

    def emit(name: str, a: list[str], b: list[str], group: str, **meta) -> None:
        lp.docx(out / "A" / f"{name}.docx", labels + [lp.para(" ".join(a))] + tail)
        lp.docx(out / "B" / f"{name}.docx", labels + [lp.para(" ".join(b))] + tail)
        rows.append({"name": name, "group": group, **meta})

    # a. ambiguity
    for density in (0.0, 0.05, 0.10, 0.20, 0.35):
        for keep in range(16, 32, 2):
            rng = random.Random(700 + keep)
            a = lp.prose(lp.VOCAB_A, 400, rng)
            b, kept, runs = lp.revise(a, keep / 100, 4, rng)
            aset = set(a)
            bmask = [w in aset for w in b]
            # kept words in A are those B kept; mark them by value (vocabularies are disjoint, so value identifies)
            kept_vals = {w for w, m in zip(b, bmask) if m}
            amask = [w in kept_vals for w in a]
            srng = random.Random(900 + keep + int(density * 100))
            a2 = sprinkle(a, amask, density, srng)
            b2 = sprinkle(b, bmask, density, srng)
            emit(f"amb{int(density * 100):02d}_k{keep}_r4", a2, b2, "ambiguity", density=density, keep=keep / 100, run=4, words=400)

    # b. length shape (+ 400 bridge)
    sample = lp.prose(lp.VOCAB_A, 2000, random.Random(1))
    cpw = sum(len(w) + 1 for w in sample) / len(sample)
    for n in (200, 300, 400, 600, 1200, 2400):
        for run in ((4, 16) if n != 400 else (4,)):
            k0 = floor_keep(n, run, cpw)
            keeps = sorted({round(k0 * 100) + d for d in range(-6, 9)})
            for keep in keeps:
                if keep < 4:
                    continue
                rng = random.Random(800 + n + run + keep)
                a = lp.prose(lp.VOCAB_A, n, rng)
                b, kept, runs = lp.revise(a, keep / 100, run, rng)
                emit(f"len{n}_k{keep:02d}_r{run:02d}", a, b, "length", keep=keep / 100, run=run, words=n)

    # c. 1600/r2 and 800/r2 with the big vocabulary
    for n, keeps in ((1600, range(26, 46, 2)), (800, range(18, 32, 2))):
        for keep in keeps:
            rng = random.Random(850 + n + keep)
            a = lp.prose(lp.VOCAB_A, n, rng)
            b, kept, runs = lp.revise(a, keep / 100, 2, rng)
            emit(f"big{n}_k{keep:02d}_r02", a, b, "r2-bigvocab", keep=keep / 100, run=2, words=n)

    with (out / "manifest.csv").open("w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=["name", "group", "density", "keep", "run", "words"])
        wr.writeheader()
        wr.writerows(rows)
    print(f"{len(rows)} probe pairs under {out} (chars/word {cpw:.2f})")


if __name__ == "__main__":
    main()
