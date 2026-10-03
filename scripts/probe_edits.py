#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Realistic edits on real prose (en-US / pt-BR): B is A after a mix of
word substitutions, clause insertions, sentence deletions, sentence
rewrites and sentence moves, at a chosen intensity. The true alignment is
recorded per pair (moved sentences are recorded as moves, not as kept).

    probe_edits.py OUT --corpus NAME=FILE [...] [--words 150,400,800]
                   [--intensity 5..60:5] [--moves 0,1,2] [--seed N]

intensity = percent of A's words touched by substitutions / deletions /
rewrites (insertions add on top). Every pair is also written as a "_t"
twin with an identical 150-word tail.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import long_paragraph_probes as lp  # noqa: E402
from probe_prose import load_corpus, parse_range, stretch  # noqa: E402


def sentences(words: list[str]) -> list[list[str]]:
    out, cur = [], []
    for w in words:
        cur.append(w)
        if re.search(r"[.!?]$", w) and len(cur) >= 4:
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return out


def edit(a: list[str], corpus: list[str], a_start: int, intensity: float, moves: int, rng: random.Random):
    """Returns B, true kept pairs (i_A, j_B) and the list of moved sentence spans."""
    sents = sentences(a)
    n = len(a); budget = round(intensity * n)
    avoid = (a_start, a_start + n)
    # plan sentence-level operations: delete / rewrite whole sentences until ~60 % of the budget, the rest as word substitutions
    ops = {}  # sentence index → ("del" | "rewrite")
    order = list(range(len(sents))); rng.shuffle(order)
    spent = 0
    for si in order:
        if spent >= budget * 0.6 or len(ops) >= max(1, len(sents) - 1):
            break
        ops[si] = rng.choice(["del", "rewrite", "rewrite"]); spent += len(sents[si])
    # word substitutions on the remaining sentences
    subs = set()
    cand = [(si, k) for si, s in enumerate(sents) if si not in ops for k in range(len(s))]
    rng.shuffle(cand)
    for si, k in cand:
        if spent >= budget:
            break
        subs.add((si, k)); spent += 1
    # insertions: one clause (6–14 words) after ~every 4th surviving sentence
    inserts = {si for si in range(len(sents)) if si not in ops and rng.random() < 0.25}
    # moves: pick sentences not otherwise touched, move each to a different slot
    movable = [si for si in range(len(sents)) if si not in ops and si not in inserts and not any(s == si for s, _ in subs)]
    rng.shuffle(movable)
    moved = movable[:moves]
    # build B
    a_pos = [0]
    for s in sents:
        a_pos.append(a_pos[-1] + len(s))
    b: list[str] = []; pairs = []; moved_spans = []
    seq = [si for si in range(len(sents)) if si not in moved]
    for si in moved:  # reinsert each moved sentence at a random other slot
        slot = rng.randrange(0, len(seq) + 1)
        seq.insert(slot, si)
    for si in seq:
        s = sents[si]
        if si in moved:
            moved_spans.append((a_pos[si], a_pos[si + 1], len(b), len(b) + len(s)))
            b.extend(s); continue
        op = ops.get(si)
        if op == "del":
            continue
        if op == "rewrite":
            b.extend(stretch(corpus, len(s), rng, avoid)[0]); continue
        for k, w in enumerate(s):
            if (si, k) in subs:
                b.append(stretch(corpus, 1, rng, avoid)[0][0])
            else:
                pairs.append((a_pos[si] + k, len(b))); b.append(w)
        if si in inserts:
            b.extend(stretch(corpus, rng.randint(6, 14), rng, avoid)[0])
    return b, pairs, moved_spans


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--corpus", action="append", required=True)
    ap.add_argument("--words", default="150,400,800")
    ap.add_argument("--intensity", default="5..60:5")
    ap.add_argument("--moves", default="0,1,2")
    ap.add_argument("--tail-words", type=int, default=150)
    ap.add_argument("--seed", type=int, default=3031)
    args = ap.parse_args()
    out = Path(args.out); lp.PUNCT = True
    rows = []; truth = {}
    labels = [lp.para("Section one"), lp.para("Clause")]; end = [lp.para("End of section")]

    def emit(name, a, b, pairs, moved, **meta):
        lp.docx(out / "A" / f"{name}.docx", labels + [lp.para(" ".join(a))] + end)
        lp.docx(out / "B" / f"{name}.docx", labels + [lp.para(" ".join(b))] + end)
        rows.append({"name": name, **meta}); truth[name] = {"pairs": pairs, "moved": moved, "a_words": len(a), "b_words": len(b), **meta}

    for spec in args.corpus:
        cname, cfile = spec.split("=", 1); corpus = load_corpus(Path(cfile))
        rng = random.Random(args.seed + hash(cname) % 1000)
        for n in parse_range(args.words):
            for mv in parse_range(args.moves):
                for inten in parse_range(args.intensity):
                    a, s = stretch(corpus, n, rng)
                    b, pairs, moved = edit(a, corpus, s, inten / 100, mv, rng)
                    name = f"{cname}_e{n}_i{inten:02d}_m{mv}"
                    meta = dict(corpus=cname, words=n, intensity=inten / 100, moves=mv, forced=False, keep=round(len(pairs) / n, 3), run=0)
                    emit(name, a, b, pairs, moved, **meta)
                    tail, _ = stretch(corpus, args.tail_words, rng, (s, s + n))
                    emit(name + "_t", a + tail, b + tail, pairs + [(len(a) + k, len(b) + k) for k in range(len(tail))], moved, **{**meta, "forced": True})
    with (out / "manifest.csv").open("w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)
    json.dump(truth, (out / "truth.json").open("w"))
    print(f"{len(rows)} probe pairs under {out}")


if __name__ == "__main__":
    main()
