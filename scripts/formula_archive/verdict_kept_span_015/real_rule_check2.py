#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Which kept-character measure predicts Word's verdict on real documents?

Every paragraph Word marked word-level or replaced (1×1 blocks) in the bench's
Word redlines, with the LCS kept characters of its original vs revised text
(all alphanumeric words, and only the words unique to both sides), the
character count of each side, and Word's verdict. Sweeps thresholds for
kept / max, kept / min, kept / a, kept / b, kept / mean, overall and by the
shorter side's length.
"""
import csv, glob, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, "/Users/arthrod/T/neurotic_docx_bench/scripts")
import redline_anatomy as ra

MAX_WORDS = 1500


def alnum(w):
    return any(ch.isalnum() for ch in w)


def one(path):
    rows = []
    try:
        paras = ra.paragraphs(Path(path))
        vs = ra.verdicts(paras)
    except Exception as e:  # noqa: BLE001
        return [{"file": Path(path).name, "error": str(e)[:80]}]
    changed = [v.verdict not in ("unchanged", "mark-only") for v in vs]
    for v in vs:
        if v.verdict == "word-level":
            p = paras[v.index]
            ta, tb = p.text("orig"), p.text("rev")
            word_kept = sum(len(s.text.strip()) for s in p.segments if s.kind == "eq" and alnum(s.text))
        elif v.verdict == "replaced" and v.block == "1×1" and v.partner is not None:
            p = paras[v.index]
            ta = p.text("orig")
            if not ta.strip():
                continue
            tb = paras[v.partner].text("rev")
            word_kept = 0
        else:
            continue
        a, b = ra.words(ta), ra.words(tb)
        if max(len(a), len(b)) > MAX_WORDS or not a or not b:
            continue
        pairs = ra.lcs_pairs(a, b)
        kept_all = sum(len(a[i]) for i, _ in pairs if alnum(a[i]))
        ca, cb = Counter(a), Counter(b)
        kept_uniq = sum(len(a[i]) for i, _ in pairs if alnum(a[i]) and ca[a[i]] == 1 and cb[a[i]] == 1)
        # region: consecutive changed paragraphs around this one
        lo = hi = v.index
        while lo > 0 and changed[lo - 1]:
            lo -= 1
        while hi + 1 < len(changed) and changed[hi + 1]:
            hi += 1
        rows.append({"file": Path(path).name[:60], "para": v.index, "word": v.verdict,
                     "aw": len(a), "bw": len(b), "chars_a": len(ta), "chars_b": len(tb),
                     "kept_all": kept_all, "kept_uniq": kept_uniq, "word_kept": word_kept,
                     "region": hi - lo + 1})
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
    fields = ["file", "para", "word", "aw", "bw", "chars_a", "chars_b", "kept_all", "kept_uniq", "word_kept", "region"]
    with open("/tmp/real_rule_rows2.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader(); w.writerows(rows)
    analyse(rows)


def analyse(rows):
    dens = {
        "max": lambda r: max(r["chars_a"], r["chars_b"], 1),
        "min": lambda r: max(min(r["chars_a"], r["chars_b"]), 1),
        "a": lambda r: max(r["chars_a"], 1),
        "b": lambda r: max(r["chars_b"], 1),
        "mean": lambda r: max((r["chars_a"] + r["chars_b"]) / 2, 1),
    }

    def agree(rs, key, t):
        return sum((key(r) >= t) == (r["word"] == "word-level") for r in rs) / len(rs)

    def sweep(rs, key):
        return max((agree(rs, key, k / 1000), k / 1000) for k in range(0, 400, 5))

    wl = sum(r["word"] == "word-level" for r in rows)
    print(f"\nword-level {wl}, replaced {len(rows) - wl}; always-word-level baseline {wl / len(rows):.3f}")
    print(f"{'measure':>12} {'@0.12':>6} {'best':>6} {'thr':>6}")
    for m in ("kept_all", "kept_uniq"):
        for d, den in dens.items():
            key = lambda r, m=m, den=den: r[m] / den(r)
            b = sweep(rows, key)
            print(f"{m + '/' + d:>12} {agree(rows, key, 0.12):>6.3f} {b[0]:>6.3f} {b[1]:>6.3f}")
    # by shorter side length, for kept_all/max vs kept_all/min vs kept_uniq/min
    buckets = [(1, 5), (6, 10), (11, 20), (21, 40), (41, 80), (81, 160), (161, 1500)]
    print(f"\n{'min words':>10} {'n':>5} {'wl':>5}  all/max@.12  all/min@.12  uniq/min@.12  best(all/min)  best(uniq/min)")
    for lo, hi in buckets:
        rs = [r for r in rows if lo <= min(r["aw"], r["bw"]) <= hi]
        if not rs:
            continue
        k1 = lambda r: r["kept_all"] / dens["max"](r)
        k2 = lambda r: r["kept_all"] / dens["min"](r)
        k3 = lambda r: r["kept_uniq"] / dens["min"](r)
        b2, b3 = sweep(rs, k2), sweep(rs, k3)
        print(f"{lo:>4}-{hi:<5} {len(rs):>5} {sum(r['word'] == 'word-level' for r in rs):>5}  {agree(rs, k1, 0.12):>10.3f}  {agree(rs, k2, 0.12):>10.3f}  {agree(rs, k3, 0.12):>11.3f}  {b2[0]:.3f}@{b2[1]:<6}  {b3[0]:.3f}@{b3[1]}")
    # by region size
    print(f"\n{'region':>8} {'n':>5} {'wl':>5}  all/max@.12  all/min@.12  best(all/min)")
    for lo, hi in [(1, 1), (2, 2), (3, 5), (6, 20), (21, 100000)]:
        rs = [r for r in rows if lo <= r["region"] <= hi]
        if not rs:
            continue
        k1 = lambda r: r["kept_all"] / dens["max"](r)
        k2 = lambda r: r["kept_all"] / dens["min"](r)
        b2 = sweep(rs, k2)
        print(f"{lo:>3}-{hi:<4} {len(rs):>5} {sum(r['word'] == 'word-level' for r in rs):>5}  {agree(rs, k1, 0.12):>10.3f}  {agree(rs, k2, 0.12):>10.3f}  {b2[0]:.3f}@{b2[1]}")
    # misses of all/min at 0.12
    k2 = lambda r: r["kept_all"] / dens["min"](r)
    miss_wl = [r for r in rows if r["word"] == "word-level" and k2(r) < 0.12]
    miss_rep = [r for r in rows if r["word"] == "replaced" and k2(r) >= 0.12]
    print(f"\nall/min misses: word-level under 0.12: {len(miss_wl)} (word_kept==0: {sum(r['word_kept'] == 0 for r in miss_wl)}), replaced at/over: {len(miss_rep)}")
    print("word-level under 0.12 by ratio:", sorted(Counter(round(k2(r), 2) for r in miss_wl).items()))
    print("replaced at/over 0.12 by ratio:", sorted(Counter(round(k2(r), 2) for r in miss_rep).items()))
    print("replaced at/over 0.12, sample:")
    for r in sorted(miss_rep, key=lambda r: -k2(r))[:12]:
        print(f"  ratio={k2(r):.3f} aw={r['aw']} bw={r['bw']} uniq={r['kept_uniq']} region={r['region']} {r['file']} p{r['para']}")
    print("word-level under 0.12 with Word keeping a word, sample:")
    for r in sorted([r for r in miss_wl if r["word_kept"] > 0], key=lambda r: k2(r))[:12]:
        print(f"  ratio={k2(r):.3f} aw={r['aw']} bw={r['bw']} word_kept={r['word_kept']} region={r['region']} {r['file']} p{r['para']}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--analyse":
        rows = []
        for r in csv.DictReader(open("/tmp/real_rule_rows2.csv")):
            rows.append({k: (int(v) if k not in ("file", "word") else v) for k, v in r.items()})
        analyse(rows)
    else:
        main()
