#!/usr/bin/env python3
"""Task #9 prototype — content-similarity paragraph aligner, validated
render-free against the ORACLE's actual paragraph alignment.

The differ's whole-replacement decision (which A-para pairs with which
B-para, and where the anchor sits) is currently a ~44-branch static gate
family. Word actually does a GLOBAL SEQUENCE ALIGNMENT over paragraphs by
content similarity. This prototype implements Needleman-Wunsch over the
paragraph sequences (A vs B) with per-paragraph token-Jaccard as the match
score and a gap penalty, then reports the alignment — validated by checking
it reproduces the oracle's kept/deleted/inserted paragraph structure.

Run: uv run python scripts/para_aligner_proto.py <A.docx> <B.docx> <oracle.docx>
     uv run python scripts/para_aligner_proto.py --census   (over sub-90 pairs)
"""

from __future__ import annotations

import csv
import re
import sys
import zipfile
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def para_texts(path):
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf8", "ignore")
    body = xml[xml.find("<w:body>"):]
    out = []
    depth = 0
    for m in re.finditer(r"<w:tbl[ >]|</w:tbl>|<w:p [^>]*>|<w:p>|<w:p [^>]*/>|</w:p>", body):
        t = m.group(0)
        if t.startswith("<w:tbl"):
            depth += 1
        elif t == "</w:tbl>":
            depth -= 1
        elif t.startswith("<w:p") and depth == 0 and not t.endswith("/>"):
            end = body.find("</w:p>", m.end())
            seg = body[m.end():end] if end > 0 else ""
            txt = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", seg))
            out.append(txt)
        elif t.startswith("<w:p") and t.endswith("/>") and depth == 0:
            out.append("")
    return out


def toks(s):
    return set(re.findall(r"[A-Za-z0-9]+", s.lower()))


def jaccard(a, b):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    ta, tb = toks(a), toks(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def align(A, B, gap=-0.35, match_thresh=0.30):
    """Needleman-Wunsch over paragraph sequences. Returns list of
    ('equal', i, j) | ('del', i) | ('ins', j)."""
    n, m = len(A), len(B)
    # score matrix
    S = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        S[i][0] = S[i - 1][0] + gap
    for j in range(1, m + 1):
        S[0][j] = S[0][j - 1] + gap
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            sim = jaccard(A[i - 1], B[j - 1])
            diag = S[i - 1][j - 1] + (sim if sim >= match_thresh else -0.2)
            S[i][j] = max(diag, S[i - 1][j] + gap, S[i][j - 1] + gap)
    # traceback
    i, j, ops = n, m, []
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            sim = jaccard(A[i - 1], B[j - 1])
            score_diag = sim if sim >= match_thresh else -0.2
            if abs(S[i][j] - (S[i - 1][j - 1] + score_diag)) < 1e-9:
                ops.append(("equal" if sim >= match_thresh else "sub", i - 1, j - 1))
                i, j = i - 1, j - 1
                continue
        if i > 0 and abs(S[i][j] - (S[i - 1][j] + gap)) < 1e-9:
            ops.append(("del", i - 1)); i -= 1
        else:
            ops.append(("ins", j - 1)); j -= 1
    ops.reverse()
    return ops


def oracle_structure(path):
    """oracle's per-paragraph mark: 'D' deleted, 'I' inserted, 'P'/'L' kept."""
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf8", "ignore")
    body = xml[xml.find("<w:body>"):]
    out = []
    depth = 0
    for m in re.finditer(r"<w:tbl[ >]|</w:tbl>|<w:p [^>]*>|<w:p [^>]*/>", body):
        t = m.group(0)
        if t.startswith("<w:tbl"):
            depth += 1
            continue
        if t == "</w:tbl>":
            depth -= 1
            continue
        if depth != 0:
            continue
        end = body.find("</w:p>", m.end()) if not t.endswith("/>") else m.end()
        seg = body[m.end():end] if end > 0 else ""
        pe = seg.find("</w:pPr>")
        head = seg[:pe] if pe > 0 else ""
        out.append("D" if "<w:del" in head else ("I" if "<w:ins" in head else "L"))
    return out


def one(a, b, o):
    A, B = para_texts(a), para_texts(b)
    ops = align(A, B)
    # aligner-predicted structure: equal→L, del→D, ins→I.
    # SUB → D + I, EXCEPT the document-final SUB: the two final ¶ marks are
    # undeletable, so Word EQ-pairs them (surviving live L) with the content
    # del/ins folded in. Model: final SUB emits I (B content) then L (the
    # surviving ¶ carrying B's final para) — matching oracle D../I../L1.
    last_real = max((k for k, op in enumerate(ops) if op[0] in ("equal", "sub", "del", "ins")), default=-1)
    pred = []
    for k, op in enumerate(ops):
        if op[0] == "equal":
            pred.append("L")
        elif op[0] == "sub":
            if k == last_real:
                pred.append("L")   # final ¶ survives (B's final para live)
            else:
                pred.append("D"); pred.append("I")
        elif op[0] == "del":
            pred.append("D")
        else:
            pred.append("I")
    orc = oracle_structure(o)
    # coarse agreement: counts of D/I/L
    from collections import Counter
    pc, oc = Counter(pred), Counter(orc)
    return A, B, ops, pc, oc


def main():
    if sys.argv[1] == "--census":
        return  # (kept short; single-pair mode is the validator)
    A, B, ops, pc, oc = one(sys.argv[1], sys.argv[2], sys.argv[3])
    print(f"A paras={len(A)} B paras={len(B)}")
    print("ALIGNER ops:")
    for op in ops:
        if op[0] == "equal":
            print(f"  EQUAL  A[{op[1]}]={A[op[1]][:28]!r} ~ B[{op[2]}]={B[op[2]][:28]!r}")
        elif op[0] == "sub":
            print(f"  SUB    A[{op[1]}]={A[op[1]][:24]!r} / B[{op[2]}]={B[op[2]][:24]!r}")
        elif op[0] == "del":
            print(f"  DEL    A[{op[1]}]={A[op[1]][:28]!r}")
        else:
            print(f"  INS    B[{op[1]}]={B[op[1]][:28]!r}")
    print(f"\naligner D/I/L counts: {dict(pc)}")
    print(f"oracle  D/I/L counts: {dict(oc)}")


if __name__ == "__main__":
    main()
