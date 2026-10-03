# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Affine-cost alignment: cost = inserted + deleted words + c · matched runs.
Does its matched set reproduce Word's? Does its cost/L separate Word's verdicts?"""
import sys
from pathlib import Path

sys.path.insert(0, "/Users/arthrod/T/neurotic_docx_bench/scripts")
sys.path.insert(0, "/tmp")
from redline_anatomy import paragraphs, words  # noqa: E402
from aligners import word_pairs  # noqa: E402

INF = float("inf")


def affine_align(a, b, c):
    """Min-cost alignment. States per cell: M (last op was a match), G (last op was a gap).
    Match allowed only when a[i]==b[j]; opening a run from a gap costs c; gap tokens cost 1.
    Returns (cost, matched pairs)."""
    n, m = len(a), len(b)
    # DP over rows; store full tables for backtrace (n,m ≤ ~1200 → ~1.5M cells × 2)
    M = [[INF] * (m + 1) for _ in range(n + 1)]
    G = [[INF] * (m + 1) for _ in range(n + 1)]
    bM = [[0] * (m + 1) for _ in range(n + 1)]  # 1 = came from M, 2 = from G
    bG = [[0] * (m + 1) for _ in range(n + 1)]  # bits: 1 = from M via a[i] del, 2 = from G via del, 4 = from M via b[j] ins, 8 = from G via ins
    G[0][0] = 0
    for i in range(1, n + 1):
        G[i][0] = i; bG[i][0] = 2
    for j in range(1, m + 1):
        G[0][j] = j; bG[0][j] = 8
    for i in range(1, n + 1):
        ai = a[i - 1]
        Mi, Gi, Mp, Gp = M[i], G[i], M[i - 1], G[i - 1]
        bMi, bGi = bM[i], bG[i]
        for j in range(1, m + 1):
            if ai == b[j - 1]:
                fm, fg = Mp[j - 1], Gp[j - 1] + c
                if fm <= fg:
                    Mi[j] = fm; bMi[j] = 1
                else:
                    Mi[j] = fg; bMi[j] = 2
            # gap: delete a[i] (from (i-1,j)) or insert b[j] (from (i,j-1))
            best, bits = INF, 0
            v = Mp[j] + 1
            if v < best: best, bits = v, 1
            v = Gp[j] + 1
            if v < best: best, bits = v, 2
            v = Mi[j - 1] + 1
            if v < best: best, bits = v, 4
            v = Gi[j - 1] + 1
            if v < best: best, bits = v, 8
            Gi[j] = best; bGi[j] = bits
    # backtrace
    i, j = n, m
    state = "M" if M[n][m] <= G[n][m] else "G"
    cost = min(M[n][m], G[n][m])
    pairs = set()
    while i > 0 or j > 0:
        if state == "M":
            pairs.add((i - 1, j - 1))
            prev = bM[i][j]
            i -= 1; j -= 1
            state = "M" if prev == 1 else "G"
        else:
            bits = bG[i][j]
            if bits == 1: i -= 1; state = "M"
            elif bits == 2: i -= 1; state = "G"
            elif bits == 4: j -= 1; state = "M"
            else: j -= 1; state = "G"
    return cost, pairs


def runs_of(pairs):
    s = set(pairs)
    return sum(1 for i, j in s if (i - 1, j - 1) not in s)


if __name__ == "__main__":
    base = Path("/Users/arthrod/temp/T/jubarte-redlines/jubarte-app/_scratch/redline-traversal-flow")
    c55 = [p.text("rev") for p in paragraphs(base / "inputs/55_Traversal_cover_letter.docx")]
    c56 = [p.text("rev") for p in paragraphs(base / "inputs/56_Flow_cover_letter.docx")]
    m55 = [p.text("rev") for p in paragraphs(base / "inputs/55_Traversal_metadata.docx")]
    m56 = [p.text("rev") for p in paragraphs(base / "inputs/56_Flow_metadata.docx")]
    wl = paragraphs(base / "word-docx/2_c55-v-c56__word.docx")
    wm = paragraphs(base / "word-docx/3_m55-v-m56__word.docx")
    cases = [
        ("letters p5", c55[5], c56[5], "word", wl[5]),
        ("meta p14", m55[14], m56[14], "word", wm[17]),
        ("meta p12", m55[12], m56[12], "word", wm[15]),
        ("meta p3", m55[3], m56[3], "REPL", None),
        ("meta p6", m55[6], m56[6], "REPL", None),
        ("meta p9", m55[9], m56[9], "REPL", None),
    ]
    cs = [float(x) for x in (sys.argv[1:] or ["1", "1.6", "2", "3", "4", "6"])]
    for name, A, B, v, R in cases:
        a = [w.lower() for w in words(A)]; b = [w.lower() for w in words(B)]; L = max(len(a), len(b))
        wp = word_pairs(R, A) if R is not None else None
        line = f"{name:11} {v:5} L={L:5}"
        for c in cs:
            cost, pairs = affine_align(a, b, c)
            s = f" | c={c:g}: cost/L={cost / L:.3f} kept={len(pairs):3} runs={runs_of(pairs):3}"
            if wp is not None:
                inter = len(pairs & wp)
                s += f" P={inter / max(len(pairs), 1):.2f} R={inter / max(len(wp), 1):.2f}"
            line += s
        print(line, flush=True)
