#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Does the 0.12 kept-character rule hold on Word's own redlines of real documents?

Every paragraph Word marked word-level or replaced (1×1 blocks) in the bench's
Word redlines: the LCS kept-character ratio of its original vs revised text,
its length, and Word's verdict. Reports agreement with the rule at 0.12 by
length bucket, the best threshold per bucket, and the margin rows.
Usage: real_rule_check.py [GLOB...]  (default: corpus/word/tracking_without_comments/docx/*.docx)
"""
import csv, glob, sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, "/Users/arthrod/T/neurotic_docx_bench/scripts")
import redline_anatomy as ra

MAX_WORDS = 1500


def measure(ta, tb):
    a, b = ra.words(ta), ra.words(tb)
    if not a or not b:
        return None
    pairs = ra.lcs_pairs(a, b)
    mx = max(len(ta), len(tb), 1)
    kept = sum(len(a[i]) for i, _ in pairs if any(ch.isalnum() for ch in a[i]))
    return kept / mx, max(len(a), len(b)), mx


def one(path):
    rows = []
    try:
        paras = ra.paragraphs(Path(path))
        vs = ra.verdicts(paras)
    except Exception as e:  # noqa: BLE001
        return [{"file": Path(path).name, "error": str(e)[:80]}]
    for v in vs:
        if v.verdict == "word-level":
            p = paras[v.index]
            ta, tb = p.text("orig"), p.text("rev")
        elif v.verdict == "replaced" and v.block == "1×1" and v.partner is not None:
            p = paras[v.index]
            ta = p.text("orig")
            if not ta.strip():
                continue  # the inserted twin; the deleted one carries the pair
            tb = paras[v.partner].text("rev")
        else:
            continue
        a, b = ra.words(ta), ra.words(tb)
        if max(len(a), len(b)) > MAX_WORDS or not a or not b:
            continue
        m = measure(ta, tb)
        if m is None:
            continue
        ratio, nwords, chars = m
        rows.append({"file": Path(path).name[:60], "para": v.index, "word": v.verdict,
                     "words": nwords, "chars": chars, "ratio": round(ratio, 4)})
    return rows


def main():
    pats = sys.argv[1:] or ["/Users/arthrod/T/neurotic_docx_bench/corpus/word/tracking_without_comments/docx/*.docx"]
    files = sorted({f for p in pats for f in glob.glob(p)})
    print(f"{len(files)} Word redlines")
    rows = []
    with ProcessPoolExecutor(6) as ex:
        for r in ex.map(one, files, chunksize=4):
            rows.extend(r)
    errs = [r for r in rows if "error" in r]
    rows = [r for r in rows if "error" not in r]
    print(f"{len(rows)} judged paragraphs ({len(errs)} files failed to parse)")
    with open("/tmp/real_rule_rows.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["file", "para", "word", "words", "chars", "ratio"])
        w.writeheader(); w.writerows(rows)
    buckets = [(1, 10), (11, 20), (21, 40), (41, 80), (81, 160), (161, 320), (321, 1500)]

    def agree(rs, t):
        return sum((r["ratio"] >= t) == (r["word"] == "word-level") for r in rs) / len(rs)
    print(f"{'words':>9} {'n':>5} {'wl':>5} {'rep':>5} {'@0.12':>6} {'best':>6} {'thr':>6}  replaced max | word-level min")
    for lo, hi in buckets:
        rs = [r for r in rows if lo <= r["words"] <= hi]
        if not rs:
            continue
        wl = [r for r in rs if r["word"] == "word-level"]
        rep = [r for r in rs if r["word"] == "replaced"]
        best = max((agree(rs, k / 1000), k / 1000) for k in range(0, 400, 5))
        rmax = sorted(r["ratio"] for r in rep)[-3:] if rep else []
        wmin = sorted(r["ratio"] for r in wl)[:3] if wl else []
        print(f"{lo:>4}-{hi:<4} {len(rs):>5} {len(wl):>5} {len(rep):>5} {agree(rs, 0.12):>6.3f} {best[0]:>6.3f} {best[1]:>6.3f}  {rmax} | {wmin}")
    allb = max((agree(rows, k / 1000), k / 1000) for k in range(0, 400, 5))
    print(f"all: n={len(rows)} @0.12 {agree(rows, 0.12):.3f} best {allb[0]:.3f} at {allb[1]}")
    # distribution of word-level ratios below 0.12 and replaced above, by bucket
    print("\nword-level under 0.12 by ratio decile:")
    c = Counter(round(r["ratio"], 2) for r in rows if r["word"] == "word-level" and r["ratio"] < 0.12)
    print(sorted(c.items()))
    print("replaced at/over 0.12 by ratio:")
    c = Counter(round(r["ratio"], 2) for r in rows if r["word"] == "replaced" and r["ratio"] >= 0.12)
    print(sorted(c.items()))


if __name__ == "__main__":
    main()
