#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Compare two kept-character measures against Word's paragraph verdicts.

For every labelled paragraph pair (rows of a jub_eval CSV): LCS over the
tokens, then
  nospace : chars of the matched word tokens
  spaces  : chars of every matched token, plus the space before/after a
            matched token when both sides have one there (runs' inner and
            flanking spaces)
Each over max(chars_A, chars_B) with spaces. Sweeps the threshold for both and
prints the agreement with Word, then the margin rows."""
import csv, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, "/Users/arthrod/T/neurotic_docx_bench/scripts")
import redline_anatomy as ra

ROOT = Path("/Users/arthrod/temp/T/jubarte-redlines/jubarte-app/_scratch/redline-traversal-flow/probes")
rows = list(csv.DictReader(open(sys.argv[1] if len(sys.argv) > 1 else "/tmp/jub_after3.csv")))
cache = {}
def texts(s, n):
    if (s, n) not in cache:
        A = ra.paragraphs(ROOT / s / "A" / f"{n}.docx"); B = ra.paragraphs(ROOT / s / "B" / f"{n}.docx")
        cache[(s, n)] = (A, B)
    return cache[(s, n)]

def measures(ta, tb):
    a, b = ra.words(ta), ra.words(tb)
    pairs = set(ra.lcs_pairs(a, b))
    mx = max(len(ta), len(tb), 1)
    nospace = sum(len(a[i]) for i, _ in pairs if any(ch.isalnum() for ch in a[i]))
    # spaces: a token boundary carries a space when the text has one there;
    # approximate: a space precedes every token but the first, except
    # punctuation tokens.
    def spaced(toks):
        return [k > 0 and any(ch.isalnum() for ch in toks[k]) for k in range(len(toks))]
    sa, sb = spaced(a), spaced(b)
    with_sp = sum(len(a[i]) for i, _ in pairs)
    counted = set()
    for i, j in pairs:
        # leading space of this match
        if sa[i] and sb[j] and (i, j) not in counted:
            with_sp += 1; counted.add((i, j))
        # trailing space = leading space of the next token on both sides
        if i + 1 < len(a) and j + 1 < len(b) and sa[i + 1] and sb[j + 1] and (i + 1, j + 1) not in counted:
            with_sp += 1; counted.add((i + 1, j + 1))
    return nospace / mx, with_sp / mx

out = []
for r in rows:
    if r["word"] not in ("word-level", "replaced") or not r["para"].startswith("a"):
        continue
    ai = int(r["para"][1:]); A, B = texts(r["set"], r["name"])
    if len(A) == len(B):
        bi = ai
    else:
        pp = dict(ra.pair_paragraphs(A, B)); bi = pp.get(ai)
        if bi is None:
            continue
    ta, tb = A[ai].text("orig"), B[bi].text("orig")
    n, s = measures(ta, tb)
    out.append({"set": r["set"], "name": r["name"], "para": r["para"], "word": r["word"], "nospace": n, "spaces": s})

print(f"{len(out)} paragraphs with a Word verdict")
def agree(key, t):
    return sum((r[key] >= t) == (r["word"] == "word-level") for r in out) / len(out)
print("thr    nospace  spaces")
for k in range(80, 201, 5):
    t = k / 1000
    print(f"{t:.3f}  {agree('nospace', t):.3f}   {agree('spaces', t):.3f}")
for key in ("nospace", "spaces"):
    best = max((agree(key, k / 1000), k / 1000) for k in range(80, 201, 1))
    print(key, "best", best)
# the band each measure must thread: highest replaced, lowest word-level
for key in ("nospace", "spaces"):
    rep = sorted(r[key] for r in out if r["word"] == "replaced")
    wl = sorted(r[key] for r in out if r["word"] == "word-level")
    print(f"{key}: replaced top5 {[round(x,3) for x in rep[-5:]]}  word-level bottom5 {[round(x,3) for x in wl[:5]]}")
