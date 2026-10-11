# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Balloon model v2 over the 151 docs.

A comment gets a balloon iff it is referenced in the body and its range end is live:
no commentRangeEnd, or one with content before it in its own paragraph (text, deleted
text, a drawing/object/symbol/tab, or another comment's reference mark). A reply
(commentsExtended paraIdParent) takes its parent's fate when THREADS is on.
"""
import json, re, sys, zipfile
from pathlib import Path
from lxml import etree
C = Path.home() / "temp/T/neurotic_docx_bench/corpus/word"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
W14 = "{http://schemas.microsoft.com/office/word/2010/wordml}"
W15 = "{http://schemas.microsoft.com/office/word/2012/wordml}"
CONTENT = tuple(f"{W}{t}" for t in ("t", "delText", "drawing", "pict", "object", "sym", "tab", "commentReference"))
STRICT = b"http://purl.oclc.org/ooxml/wordprocessingml/main"
def xml(z, n):
    return etree.fromstring(z.read(n).replace(STRICT, W[1:-1].encode())) if n in z.namelist() else None
def parents(z) -> dict[str, str]:
    cx, ex = xml(z, "word/comments.xml"), xml(z, "word/commentsExtended.xml")
    if cx is None or ex is None: return {}
    para = {}
    for c in cx.iter(f"{W}comment"):
        ps = list(c.iter(f"{W}p"))
        if ps and ps[-1].get(f"{W14}paraId"): para[ps[-1].get(f"{W14}paraId")] = c.get(f"{W}id")
    out = {}
    for e in ex.iter(f"{W15}commentEx"):
        kid, par = para.get(e.get(f"{W15}paraId")), para.get(e.get(f"{W15}paraIdParent"))
        if kid and par: out[kid] = par
    return out
def predict(z, threads: bool) -> int:
    root = xml(z, "word/document.xml")
    refs = {e.get(f"{W}id") for e in root.iter(f"{W}commentReference")}
    dead = set()
    for e in root.iter(f"{W}commentRangeEnd"):
        par = e.getparent()
        while par is not None and par.tag not in (f"{W}p", f"{W}body", f"{W}tc"): par = par.getparent()
        live = False
        if par is not None and par.tag == f"{W}p":
            for x in par.iter():
                if x is e: break
                if x.tag in CONTENT and (x.text or x.tag not in (f"{W}t", f"{W}delText")): live = True
        if not live: dead.add(e.get(f"{W}id"))
    up = parents(z) if threads else {}
    def alive(i, seen=()):
        if i in dead: return False
        return alive(up[i], seen + (i,)) if i in up and up[i] not in seen else True
    return sum(alive(i) for i in refs)
rows = json.load(open("survey4.json"))
for threads in (False, True):
    exact, misses = 0, []
    for r in rows:
        st, stem = r["doc"].split("/")
        p = predict(zipfile.ZipFile(C / st / "docx" / f"{stem}.docx"), threads)
        exact += p == r["balloons"]
        if p != r["balloons"]: misses.append(f"  {r['doc']}: balloons {r['balloons']} predicted {p}")
        r[f"pred_threads_{threads}"] = p
    zero = [r for r in rows if not r["balloons"]]
    print(f"threads={threads}: exact {exact}/{len(rows)}; zero predicted zero {sum(r[f'pred_threads_{threads}'] == 0 for r in zero)}/{len(zero)}")
    print("\n".join(misses[:12]))
json.dump(rows, open("survey5.json", "w"), indent=1)
