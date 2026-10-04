#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Fine-step probes of the Word verdict around 0.12 (waves `punct1`, `short2`).

short1 (6–160 words, no punctuation) puts Word's boundary at 0.10–0.11 of
the longer side's characters; wave7 (200–4800 words, sentences with
periods and capitals) at 0.1207–0.124. Two things differ between them:
length and punctuation. `punct1` separates them: paragraphs of 60–400
words with and without sentence punctuation, kept characters stepped
0.095–0.135 of the longer side in 0.005 steps. `short2` refines the short
end, where a six-letter word is a coarse step: 8–40 words with kept words
of 3–12 letters, one or two of them, so the ratio moves in fine steps.

    probe_fine.py punct1 OUT
    probe_fine.py short2 OUT
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import long_paragraph_probes as lp  # noqa: E402

VOCAB_A = lp.pseudo_vocab(101, 3000, None)
VOCAB_B = [w for w in lp.pseudo_vocab(202, 4000, None) if w not in set(VOCAB_A)][:3000]
assert not set(VOCAB_A) & set(VOCAB_B)


def write(out, name, ta, tb, rows, extra):
    labels = [lp.para("Section one"), lp.para("Clause")]
    tail = [lp.para("End of section")]
    lp.docx(out / "A" / f"{name}.docx", labels + [lp.para(ta)] + tail)
    lp.docx(out / "B" / f"{name}.docx", labels + [lp.para(tb)] + tail)
    rows.append({"name": name, **extra, "chars_a": len(ta), "chars_b": len(tb)})


def punct1(out: Path) -> list[dict]:
    rows = []
    for n in (60, 100, 160, 200, 300, 400):
        for punct in (False, True):
            lp.PUNCT = punct
            lp.VOCAB_A, lp.VOCAB_B = VOCAB_A, VOCAB_B
            for step in range(9):
                target = 0.095 + 0.005 * step
                for seed in (1, 2):
                    rng = random.Random(17000 + n * 7 + punct * 3 + step * 11 + seed)
                    a = lp.prose(VOCAB_A, n, rng)
                    # keep lone words placed evenly; k chosen for the target over
                    # the longer side, counting only letters of kept words
                    chars = sum(len(w) for w in a) + n - 1
                    k = max(1, round(target * chars / 6))
                    b, kept, runs = lp.revise(a, k / n, 1, rng)
                    if kept == 0:
                        continue
                    ta, tb = " ".join(a), " ".join(b)
                    aset = set(a)
                    kept_chars = sum(len(w.strip(".").lower()) for w in b if w in aset)
                    name = f"punct_n{n:03}_{'punct' if punct else 'plain'}_t{target:.3f}_s{seed}"
                    write(out, name, ta, tb, rows, {"n": n, "punct": int(punct), "target": round(target, 3),
                                                     "seed": seed, "k": kept, "runs": runs,
                                                     "kept_chars": kept_chars,
                                                     "ratio": round(kept_chars / max(len(ta), len(tb)), 4)})
    return rows


def short2(out: Path) -> list[dict]:
    rows = []
    lp.PUNCT = False
    by_len = {L: [w for w in VOCAB_A if len(w) == L] for L in range(3, 13)}
    for n in (8, 12, 16, 20, 30, 40):
        for L in (3, 4, 6, 8, 10, 12):
            for k in (1, 2):
                if k >= n - 2:
                    continue
                for seed in (1, 2):
                    rng = random.Random(19000 + n * 13 + L * 7 + k * 3 + seed)
                    pool = by_len.get(L) or []
                    if len(pool) < k:
                        pool = sorted(VOCAB_A, key=lambda w: abs(len(w) - L))[:200]
                    kept = rng.sample(pool, k)
                    a_rest = [w for w in lp.prose(VOCAB_A, n - k, rng) if w not in kept]
                    a_rest += lp.prose([w for w in VOCAB_A if w not in kept], n - k - len(a_rest), rng)
                    b_rest = lp.prose(VOCAB_B, n - k, rng)
                    # kept words evenly inside both sides (never at an edge)
                    def place(rest):
                        o = list(rest)
                        step = (len(o) + 1) / (k + 1)
                        for i, w in enumerate(kept):
                            o.insert(min(len(o) - 1, max(1, round((i + 1) * step) + i)), w)
                        return o
                    a, b = place(a_rest), place(b_rest)
                    assert len(a) == n and len(b) == n
                    ta, tb = " ".join(a), " ".join(b)
                    kept_chars = sum(len(w) for w in kept)
                    name = f"short2_n{n:03}_L{L:02}_k{k}_s{seed}"
                    write(out, name, ta, tb, rows, {"n": n, "L": L, "k": k, "seed": seed,
                                                     "kept_chars": kept_chars,
                                                     "ratio": round(kept_chars / max(len(ta), len(tb)), 4)})
    return rows


def main() -> None:
    mode, out = sys.argv[1], Path(sys.argv[2])
    rows = {"punct1": punct1, "short2": short2}[mode](out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "meta.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} pairs → {out}")


if __name__ == "__main__":
    main()
