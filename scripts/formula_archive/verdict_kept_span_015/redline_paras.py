# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Per-paragraph revision shape of a redline, and contiguity of the input pair."""
import difflib
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, "/tmp")
import redline_stats as rs  # noqa: E402

W = rs.W


def per_para(path):
    print("==", path.split("/")[-1])
    for n, m in enumerate(rs.segs(path)):
        ins = sum(1 for k, _ in m if k == "ins")
        dele = sum(1 for k, _ in m if k == "del")
        if not ins and not dele:
            continue
        a = sum(len(rs.words(t)) for k, t in m if k != "ins")
        b = sum(len(rs.words(t)) for k, t in m if k != "del")
        isl = [len(rs.words(t)) for i, (k, t) in enumerate(m) if k == "eq" and 0 < i < len(m) - 1]
        kind = "WHOLE" if len(m) == 1 or all(k != "eq" for k, _ in m) else "word-level"
        print(f"  p{n:<3} A={a:4}w B={b:4}w ins={ins:3} del={dele:3} islands={len(isl):3} 1w={sum(1 for x in isl if x == 1):3}  {kind}")


def input_paras(path):
    body = ET.fromstring(zipfile.ZipFile(path).read("word/document.xml")).find(W + "body")
    out = []
    for p in body.findall(W + "p"):
        t = "".join((e.text or "") + ("\n" if e.tag == W + "br" else "") for e in p.iter() if e.tag in (W + "t", W + "br"))
        out.append([w.lower() for w in re.findall(r"[\w']+", t)])
    return out


def contiguity(a, b, label):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    blocks = [bl for bl in sm.get_matching_blocks() if bl.size]
    longest = max((bl.size for bl in blocks), default=0)
    cov = lambda k: sum(bl.size for bl in blocks if bl.size >= k) / max(len(a), 1)
    units = 2 * max(len(a), len(b))  # ≈ words + separators, what jubarte's max_len counts
    print(
        f"  {label:14} A={len(a):4}w B={len(b):4}w longest-run={longest:3}w ({longest/units:.3f} of window; gate needs 0.02 ⇒ ≥{-(-0.02*units//1):.0f}w)"
        f"  cov≥5w={cov(5):.2f} cov≥3w={cov(3):.2f} cov≥1w={cov(1):.2f}  greedy-blocks={len(blocks)} 1w-blocks={sum(1 for bl in blocks if bl.size == 1)}"
    )


if __name__ == "__main__":
    root = sys.argv[1]
    for f in sys.argv[2:]:
        per_para(f)
    c55, c56 = input_paras(f"{root}/inputs/55_Traversal_cover_letter.docx"), input_paras(f"{root}/inputs/56_Flow_cover_letter.docx")
    m55, m56 = input_paras(f"{root}/inputs/55_Traversal_metadata.docx"), input_paras(f"{root}/inputs/56_Flow_metadata.docx")
    print("== contiguity of the input paragraph pairs")
    contiguity(c55[5], c56[5], "letters p5")
    for i in (3, 6, 9, 12, 14):
        contiguity(m55[i], m56[i], f"metadata p{i}")
    contiguity(c55[5], m55[14], "c55p5×m55p14")
