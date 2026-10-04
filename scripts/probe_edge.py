#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Edge probes of the Word verdict (wave `edge1`): does a shared word at the
start or end of a paragraph keep the paragraph word-level under 0.12?

Word's redlines of the bench corpus keep a lone shared word of short
paragraphs under 0.12 of the longer side in 45 isolated pairs; in 33 of them
the kept word starts or ends one of the two paragraphs. Every earlier probe
spaced its kept words evenly, never at an edge. This wave keeps one word
(or two) of `n` words, the rest rewritten from a disjoint vocabulary, with
the kept word at a chosen position on each side:

    first-both   first word of A and of B
    first-a      first word of A, middle of B
    first-b      middle of A, first word of B
    last-both    last word of A and of B
    last-a       last word of A, middle of B
    mid-both     middle of A and of B (the control)
    ends-both    two words: the first and the last of both sides

    probe_edge.py OUT        (writes OUT/A, OUT/B, OUT/meta.csv)
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

LENGTHS = [12, 20, 40, 80, 160, 300]
POSITIONS = ["first-both", "first-a", "first-b", "last-both", "last-a", "mid-both", "ends-both"]


def place(words: list[str], kept: list[str], where: str) -> list[str]:
    out = list(words)
    if where == "first":
        return kept + out
    if where == "last":
        return out + kept
    if where == "ends":
        return [kept[0]] + out + [kept[1]]
    mid = len(out) // 2
    return out[:mid] + kept + out[mid:]


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "probes/edge1")
    rows: list[dict] = []
    labels = [lp.para("Section one"), lp.para("Clause")]
    tail = [lp.para("End of section")]
    for n in LENGTHS:
        for pos in POSITIONS:
            for seed in (1, 2):
                rng = random.Random(13000 + n * 17 + POSITIONS.index(pos) * 5 + seed)
                nk = 2 if pos == "ends-both" else 1
                kept = [rng.choice(lp.VOCAB_A) for _ in range(nk)]
                while len(set(kept)) < nk:
                    kept = [rng.choice(lp.VOCAB_A) for _ in range(nk)]
                a_rest = [w for w in lp.prose(lp.VOCAB_A, n - nk, rng) if w not in kept]
                b_rest = lp.prose(lp.VOCAB_B, n - nk, rng)
                a_rest += lp.prose([w for w in lp.VOCAB_A if w not in kept], n - nk - len(a_rest), rng)
                if pos == "ends-both":
                    wa = wb = "ends"
                else:
                    side, who = pos.split("-")
                    wa = side if who in ("both", "a") else "mid"
                    wb = side if who in ("both", "b") else "mid"
                a = place(a_rest, kept, wa)
                b = place(b_rest, kept, wb)
                assert len(a) == n and len(b) == n, (len(a), len(b), n)
                ta, tb = " ".join(a), " ".join(b)
                name = f"edge_n{n:03}_{pos}_s{seed}"
                lp.docx(out / "A" / f"{name}.docx", labels + [lp.para(ta)] + tail)
                lp.docx(out / "B" / f"{name}.docx", labels + [lp.para(tb)] + tail)
                kept_chars = sum(len(w) for w in kept)
                rows.append({"name": name, "n": n, "pos": pos, "seed": seed, "k": nk,
                             "chars_a": len(ta), "chars_b": len(tb), "kept_chars": kept_chars,
                             "ratio": round(kept_chars / max(len(ta), len(tb)), 4)})
    out.mkdir(parents=True, exist_ok=True)
    with (out / "meta.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} pairs → {out}")


if __name__ == "__main__":
    main()
