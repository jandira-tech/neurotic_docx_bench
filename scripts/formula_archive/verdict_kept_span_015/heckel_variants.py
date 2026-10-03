# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import sys, bisect
sys.path.insert(0, "/tmp"); sys.path.insert(0, "/Users/arthrod/T/neurotic_docx_bench/scripts")
import redline_anatomy as ra
from aligners import word_pairs, lcs_dp
from collections import Counter
from pathlib import Path

def heckel_v(a, b, resolve="lis", recurse=True, extend_first=True, lo1=0, lo2=0, out=None):
    """Heckel with a choice of crossing resolution: 'lis' (longest chain), 'a-first' (scan A, keep a link
    only if its B index exceeds the last kept), 'b-first' (same scanning B), 'none' (keep all, even crossing)."""
    if out is None: out = set()
    ca, cb = Counter(a), Counter(b)
    pos_b = {w: j for j, w in enumerate(b) if cb[w] == 1}
    la = [None]*len(a); lb = [None]*len(b)
    for i, w in enumerate(a):
        if ca[w] == 1 and w in pos_b: la[i] = pos_b[w]; lb[pos_b[w]] = i
    anchors = [i for i, j in enumerate(la) if j is not None]
    def extend():
        for i in [i for i, j in enumerate(la) if j is not None]:
            j = la[i]; k = 1
            while i+k < len(a) and j+k < len(b) and la[i+k] is None and lb[j+k] is None and a[i+k] == b[j+k]:
                la[i+k] = j+k; lb[j+k] = i+k; k += 1
        for i in [i for i, j in reversed(list(enumerate(la))) if j is not None]:
            j = la[i]; k = 1
            while i-k >= 0 and j-k >= 0 and la[i-k] is None and lb[j-k] is None and a[i-k] == b[j-k]:
                la[i-k] = j-k; lb[j-k] = i-k; k += 1
    if extend_first: extend()
    pairs = [(i, j) for i, j in enumerate(la) if j is not None]
    if resolve == "lis":
        tails, idx, back = [], [], [None]*len(pairs)
        for n, (i, j) in enumerate(pairs):
            p = bisect.bisect_left(tails, j)
            if p == len(tails): tails.append(j); idx.append(n)
            else: tails[p] = j; idx[p] = n
            back[n] = idx[p-1] if p else None
        mono = []; n = idx[-1] if idx else None
        while n is not None: mono.append(pairs[n]); n = back[n]
        mono.reverse()
    elif resolve == "a-first":
        mono = []; last = -1
        for i, j in pairs:
            if j > last: mono.append((i, j)); last = j
    elif resolve == "b-first":
        mono = []; last = -1
        for i, j in sorted(pairs, key=lambda p: p[1]):
            if i > last: mono.append((i, j)); last = i
        mono.sort()
    else:
        mono = pairs
    if not extend_first:
        # extension after resolution
        la = [None]*len(a); lb = [None]*len(b)
        for i, j in mono: la[i] = j; lb[j] = i
        extend()
        pairs = [(i, j) for i, j in enumerate(la) if j is not None]
        mono = []; last = -1
        for i, j in pairs:
            if j > last: mono.append((i, j)); last = j
    for i, j in mono: out.add((lo1+i, lo2+j))
    if recurse and mono:
        bounds = [(-1, -1)] + mono + [(len(a), len(b))]
        for (i0, j0), (i1, j1) in zip(bounds, bounds[1:]):
            if i1-i0 > 1 and j1-j0 > 1:
                heckel_v(a[i0+1:i1], b[j0+1:j1], resolve, True, extend_first, lo1+i0+1, lo2+j0+1, out)
    return out

base = Path("/Users/arthrod/temp/T/jubarte-redlines/jubarte-app/_scratch/redline-traversal-flow")
cases = [("w1600_k28 v300", "probes/wave4/A/w1600_k28_r04_dj_np.docx", "probes/wave4/B/w1600_k28_r04_dj_np.docx", "probes/wave4/word/w1600_k28_r04_dj_np__vs__w1600_k28_r04_dj_np.docx", 2),
         ("w1600_k32 v300", "probes/wave4/A/w1600_k32_r04_dj_np.docx", "probes/wave4/B/w1600_k32_r04_dj_np.docx", "probes/wave4/word/w1600_k32_r04_dj_np__vs__w1600_k32_r04_dj_np.docx", 2),
         ("w800_k35 eng", "probes/wave2all/A/w800_k35_r04.docx", "probes/wave2all/B/w800_k35_r04.docx", "probes/wave2all/word/w800_k35_r04__vs__w800_k35_r04.docx", 2),
         ("amb35_k22", "probes/wave7/A/amb35_k22_r4.docx", "probes/wave7/B/amb35_k22_r4.docx", "probes/wave7/word/amb35_k22_r4__vs__amb35_k22_r4.docx", 2),
         ("letters p5", "inputs/55_Traversal_cover_letter.docx", "inputs/56_Flow_cover_letter.docx", "word-docx/2_c55-v-c56__word.docx", 5),
         ("metadata p14", "inputs/55_Traversal_metadata.docx", "inputs/56_Flow_metadata.docx", "word-docx/3_m55-v-m56__word.docx", 14)]
variants = [("lis+rec", dict(resolve="lis")), ("a-first+rec", dict(resolve="a-first")), ("b-first+rec", dict(resolve="b-first")),
            ("a-first, extend after", dict(resolve="a-first", extend_first=False)), ("lis, no rec", dict(resolve="lis", recurse=False)), ("a-first, no rec", dict(resolve="a-first", recurse=False))]
if __name__ == "__main__":
    for label, pa, pb, pr, idx in cases:
        A = ra.paragraphs(base/pa)[idx].text("rev"); B = ra.paragraphs(base/pb)[idx].text("rev")
        R = next(p for p in ra.paragraphs(base/pr) if p.text("orig") == A)
        a, b = ra.words(A), ra.words(B); wp = word_pairs(R, A)
        print(f"{label}: Word matched {len(wp)}")
        for name, kw in variants:
            c = heckel_v(a, b, **kw); inter = len(c & wp)
            print(f"   {name:22} matched={len(c):4} precision={inter/max(len(c),1):.3f} recall={inter/max(len(wp),1):.3f} exact={'YES' if c == wp else 'no'}")