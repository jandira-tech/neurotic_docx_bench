# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Which alignment reproduces Word's matched word pairs?"""
import difflib
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "/Users/arthrod/T/neurotic_docx_bench/scripts")
from redline_anatomy import paragraphs, words  # noqa: E402


def word_pairs(R, A_text):
    """Word's matched (i, j) word pairs from the redline paragraph."""
    i = j = 0
    pairs = set()
    for s in R.segments:
        n = len(words(s.text))
        if s.kind == "eq":
            for k in range(n):
                pairs.add((i + k, j + k))
            i += n
            j += n
        elif s.kind in ("del", "moveFrom"):
            i += n
        else:
            j += n
    return pairs


def greedy_lcr(a, b):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return {(bl.a + k, bl.b + k) for bl in sm.get_matching_blocks() for k in range(bl.size)}


def lcs_dp(a, b):
    n, m = len(a), len(b)
    L = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            L[i][j] = L[i + 1][j + 1] + 1 if a[i] == b[j] else max(L[i + 1][j], L[i][j + 1])
    i = j = 0
    out = set()
    while i < n and j < m:
        if a[i] == b[j]:
            out.add((i, j)); i += 1; j += 1
        elif L[i + 1][j] >= L[i][j + 1]:
            i += 1
        else:
            j += 1
    return out


def patience(a, b, lo1=0, lo2=0, out=None):
    """Patience diff: unique common words anchor, LIS, recurse; gaps fall to LCS."""
    if out is None:
        out = set()
    if not a or not b:
        return out
    ca, cb = defaultdict(list), defaultdict(list)
    for i, x in enumerate(a):
        ca[x].append(i)
    for j, y in enumerate(b):
        cb[y].append(j)
    uniq = [(ca[x][0], cb[x][0]) for x in ca if len(ca[x]) == 1 and len(cb.get(x, ())) == 1]
    uniq.sort()
    if not uniq:
        for i, j in lcs_dp(a, b):
            out.add((lo1 + i, lo2 + j))
        return out
    # longest increasing subsequence on j
    import bisect
    tails, back, idx = [], [], []
    for k, (_, j) in enumerate(uniq):
        p = bisect.bisect_left(tails, j)
        if p == len(tails):
            tails.append(j); idx.append(k)
        else:
            tails[p] = j; idx[p] = k
        back.append(idx[p - 1] if p else -1)
    chain = []
    k = idx[-1]
    while k != -1:
        chain.append(uniq[k]); k = back[k]
    chain.reverse()
    pi = pj = 0
    for i, j in chain:
        patience(a[pi:i], b[pj:j], lo1 + pi, lo2 + pj, out)
        # extend the anchor into a run both ways
        out.add((lo1 + i, lo2 + j))
        pi, pj = i + 1, j + 1
    patience(a[pi:], b[pj:], lo1 + pi, lo2 + pj, out)
    return out


def left_greedy(a, b, window=None):
    """Scan A; match a[i] to the nearest later b[j]; never go back."""
    out = set()
    j = 0
    for i, x in enumerate(a):
        lim = len(b) if window is None else min(len(b), j + window)
        for k in range(j, lim):
            if b[k] == x:
                out.add((i, k)); j = k + 1
                break
    return out


def min_run(pairs, k):
    """Keep only matched pairs that sit in a diagonal run of ≥ k."""
    s = set(pairs)
    keep = set()
    for i, j in s:
        if (i - 1, j - 1) in s:
            continue
        n = 0
        while (i + n, j + n) in s:
            n += 1
        if n >= k:
            keep.update((i + t, j + t) for t in range(n))
    return keep


def report(label, A, B, R):
    a, b = [w.lower() for w in words(A)], [w.lower() for w in words(B)]
    wp = word_pairs(R, A)
    print(f"{label}: A={len(a)} B={len(b)} Word matched {len(wp)}")
    cands = {
        "greedy LCR": greedy_lcr(a, b),
        "LCS": lcs_dp(a, b),
        "patience": patience(a, b),
        "left-greedy": left_greedy(a, b),
        "left-greedy w40": left_greedy(a, b, 40),
    }
    for k in (2, 3):
        cands[f"greedy LCR runs≥{k}"] = min_run(cands["greedy LCR"], k)
        cands[f"LCS runs≥{k}"] = min_run(cands["LCS"], k)
    for name, c in cands.items():
        inter = len(c & wp)
        print(f"   {name:20} matched={len(c):4}  precision={inter / max(len(c), 1):.3f} recall={inter / max(len(wp), 1):.3f}")


if __name__ == "__main__":
    base = Path("/Users/arthrod/temp/T/jubarte-redlines/jubarte-app/_scratch/redline-traversal-flow")
    cases = [
        ("letters p5", base / "inputs/55_Traversal_cover_letter.docx", base / "inputs/56_Flow_cover_letter.docx", base / "word-docx/2_c55-v-c56__word.docx", 5, 5),
        ("metadata p14", base / "inputs/55_Traversal_metadata.docx", base / "inputs/56_Flow_metadata.docx", base / "word-docx/3_m55-v-m56__word.docx", 14, 17),
        ("metadata p12", base / "inputs/55_Traversal_metadata.docx", base / "inputs/56_Flow_metadata.docx", base / "word-docx/3_m55-v-m56__word.docx", 12, 15),
        ("w800_k40_r04", base / "probes/wave2all/A/w800_k40_r04.docx", base / "probes/wave2all/B/w800_k40_r04.docx", base / "probes/wave2all/word/w800_k40_r04__vs__w800_k40_r04.docx", 2, 2),
        ("w400_k20_r16", base / "probes/wave1/A/w400_k20_r16.docx", base / "probes/wave1/B/w400_k20_r16.docx", base / "probes/wave1/word/w400_k20_r16__vs__w400_k20_r16.docx", 2, 2),
    ]
    for label, pa, pb, pr, ia, ir in cases:
        A = paragraphs(pa)[ia].text("rev")
        B = paragraphs(pb)[ia].text("rev")
        R = paragraphs(pr)[ir]
        assert R.text("orig") == A, label
        report(label, A, B, R)
