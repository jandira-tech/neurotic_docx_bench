# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Island statistics of tracked-change docx files, from the XML only.

For each paragraph: segments (eq/ins/del, text). Reports ins/del segment
counts and the word-lengths of equal islands that sit BETWEEN two revisions
inside one paragraph, which is where a comparer's granularity rule shows.
"""
import re
import statistics
import sys
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def segs(path):
    x = zipfile.ZipFile(path).read("word/document.xml")
    body = ET.fromstring(x).find(W + "body")
    out = []
    for p in body.iter(W + "p"):
        cur = []

        def walk(el, kind):
            for ch in el:
                tag = ch.tag
                if tag == W + "ins" or tag == W + "moveTo":
                    walk(ch, "ins")
                elif tag == W + "del" or tag == W + "moveFrom":
                    walk(ch, "del")
                elif tag == W + "r":
                    for rc in ch:
                        if rc.tag in (W + "t", W + "delText"):
                            cur.append((kind, rc.text or ""))
                        elif rc.tag in (W + "br", W + "tab", W + "cr"):
                            cur.append((kind, " "))
                elif tag == W + "pPr":
                    pass
                else:
                    walk(ch, kind)

        walk(p, "eq")
        m = []
        for k, t in cur:
            if m and m[-1][0] == k:
                m[-1] = (k, m[-1][1] + t)
            else:
                m.append((k, t))
        out.append(m)
    return out


def words(t):
    return re.findall(r"[\w']+", t)


def report(path):
    paras = segs(path)
    ins = dele = 0
    islands = []
    rev_lens = []
    for m in paras:
        for i, (k, t) in enumerate(m):
            if k == "ins":
                ins += 1
                rev_lens.append(len(words(t)))
            elif k == "del":
                dele += 1
                rev_lens.append(len(words(t)))
            elif 0 < i < len(m) - 1:
                islands.append(len(words(t)))
    name = path.split("/")[-1]
    if islands:
        isl = (
            f"islands={len(islands)} min={min(islands)} med={statistics.median(islands)} "
            f"<=1w={sum(1 for x in islands if x <= 1)} <=2w={sum(1 for x in islands if x <= 2)} "
            f"<=3w={sum(1 for x in islands if x <= 3)}"
        )
    else:
        isl = "islands=0"
    rv = f"rev med={statistics.median(rev_lens) if rev_lens else 0} max={max(rev_lens) if rev_lens else 0}"
    print(f"{name:48} ins={ins:3} del={dele:3}  {isl}  {rv}")
    return paras


if __name__ == "__main__":
    for p in sys.argv[1:]:
        report(p)
