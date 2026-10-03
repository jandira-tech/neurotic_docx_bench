#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Word-verdict probes cut from real prose (en-US and pt-BR, public-domain
corpora). A is a stretch of a corpus; B keeps a fraction of A's words in
runs and fills the gaps with other stretches of the SAME corpus, so the
rewrites share the language's vocabulary, stopwords and punctuation. The
true alignment (which A word went where in B) is recorded per pair.

    probe_prose.py OUT --corpus NAME=FILE [...] [--words 200,400,800]
                   [--keep 8..40:2] [--run 2,4,8,16] [--forced-keep-max 24]

--forced-keep-max N also writes a "<name>_t" twin of every pair with keep
≤ N: both sides get the same 150-word tail from the corpus, so a pair Word
would replace whole still shows Word's alignment of the original region.
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


def load_corpus(path: Path) -> list[str]:
    words = []
    for line in path.read_text(encoding="utf-8").splitlines():
        words.extend(line.split())
    return words


def stretch(corpus: list[str], n: int, rng: random.Random, avoid: tuple[int, int] | None = None) -> tuple[list[str], int]:
    """n consecutive corpus words starting at a sentence-ish boundary, outside `avoid`."""
    for _ in range(1000):
        s = rng.randrange(0, len(corpus) - n - 1)
        if avoid and not (s + n <= avoid[0] or s >= avoid[1]):
            continue
        if s == 0 or re.search(r"[.!?:;]$", corpus[s - 1]):
            return corpus[s:s + n], s
    s = rng.randrange(0, len(corpus) - n - 1)
    return corpus[s:s + n], s


def revise(a: list[str], corpus: list[str], a_start: int, keep: float, run: int, rng: random.Random) -> tuple[list[str], list[tuple[int, int]]]:
    """B keeps round(keep·n) of A's words in `run`-word runs, evenly spaced; the
    gaps are fresh stretches of the corpus (never overlapping A). Returns B and
    the true (i_A, j_B) pairs."""
    n = len(a)
    kept = round(keep * n)
    runs = max(kept // run, 1) if kept else 0
    gap_total = n - runs * run
    gaps = [gap_total // (runs + 1)] * (runs + 1)
    for i in range(gap_total - sum(gaps)):
        gaps[i % (runs + 1)] += 1
    b: list[str] = []; pairs = []; pos = 0
    avoid = (a_start, a_start + n)
    for r in range(runs):
        g = gaps[r]
        if g:
            b.extend(stretch(corpus, g, rng, avoid)[0])
        pos += g
        for k in range(run):
            pairs.append((pos + k, len(b) + k))
        b.extend(a[pos:pos + run]); pos += run
    if gaps[-1]:
        b.extend(stretch(corpus, gaps[-1], rng, avoid)[0])
    assert len(b) == n
    return b, pairs


def parse_range(spec: str) -> list[int]:
    if ".." in spec:
        lo, rest = spec.split(".."); hi, step = (rest.split(":") + ["1"])[:2]
        return list(range(int(lo), int(hi) + 1, int(step)))
    return [int(x) for x in spec.split(",")]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--corpus", action="append", required=True, help="NAME=FILE (plain text)")
    ap.add_argument("--words", default="200,400,800")
    ap.add_argument("--keep", default="8..40:2", help="percent; list or lo..hi:step")
    ap.add_argument("--run", default="2,4,8,16")
    ap.add_argument("--forced-keep-max", type=int, default=24)
    ap.add_argument("--tail-words", type=int, default=150)
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()
    out = Path(args.out)
    lp.PUNCT = True
    rows = []; truth = {}
    labels = [lp.para("Section one"), lp.para("Clause")]; end = [lp.para("End of section")]

    def emit(name: str, a: list[str], b: list[str], pairs, **meta) -> None:
        lp.docx(out / "A" / f"{name}.docx", labels + [lp.para(" ".join(a))] + end)
        lp.docx(out / "B" / f"{name}.docx", labels + [lp.para(" ".join(b))] + end)
        rows.append({"name": name, **meta}); truth[name] = {"pairs": pairs, "a_words": len(a), "b_words": len(b), **meta}

    for spec in args.corpus:
        cname, cfile = spec.split("=", 1)
        corpus = load_corpus(Path(cfile))
        rng = random.Random(args.seed + hash(cname) % 1000)
        for n in parse_range(args.words):
            for run in parse_range(args.run):
                for keep in parse_range(args.keep):
                    a, s = stretch(corpus, n, rng)
                    b, pairs = revise(a, corpus, s, keep / 100, run, rng)
                    name = f"{cname}_w{n}_k{keep:02d}_r{run:02d}"
                    meta = dict(corpus=cname, words=n, keep=keep / 100, run=run, forced=False)
                    emit(name, a, b, pairs, **meta)
                    if keep <= args.forced_keep_max:
                        tail, _ = stretch(corpus, args.tail_words, rng, (s, s + n))
                        emit(name + "_t", a + tail, b + tail, pairs + [(len(a) + k, len(b) + k) for k in range(len(tail))], **{**meta, "forced": True})
    with (out / "manifest.csv").open("w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)
    json.dump(truth, (out / "truth.json").open("w"))
    print(f"{len(rows)} probe pairs under {out}")


if __name__ == "__main__":
    main()
