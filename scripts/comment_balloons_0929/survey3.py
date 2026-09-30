"""Rule from round 5: a comment whose commentRangeEnd has no text before it in its container
(body level, or first in a paragraph before any w:t) gets no balloon."""
import json, re, zipfile
from pathlib import Path
from lxml import etree
C = Path.home() / "temp/T/neurotic_docx_bench/corpus/word"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
def dead_ends(xml: bytes) -> tuple[int, int]:
    root = etree.fromstring(xml)
    dead = total = 0
    for e in root.iter(f"{W}commentRangeEnd"):
        total += 1
        par = e.getparent()
        while par is not None and par.tag not in (f"{W}p", f"{W}body", f"{W}tc", f"{W}tbl", f"{W}tr"):
            par = par.getparent()
        if par is None or par.tag != f"{W}p":
            dead += 1
            continue
        before = False
        for x in par.iter():
            if x is e: break
            if x.tag == f"{W}t" and (x.text or ""):
                before = True
        dead += not before
    return dead, total
rows = json.load(open("survey2.json"))
for r in rows:
    st, stem = r["doc"].split("/")
    r["dead_ends"], r["ends"] = dead_ends(zipfile.ZipFile(C / st / "docx" / f"{stem}.docx").read("word/document.xml"))
zero = [r for r in rows if not r["balloons"]]; some = [r for r in rows if r["balloons"]]
print("zero-balloon docs:", len(zero), " with every end dead:", sum(r["dead_ends"] == r["ends"] for r in zero), " with any dead:", sum(r["dead_ends"] > 0 for r in zero))
print("some-balloon docs:", len(some), " with every end dead:", sum(r["dead_ends"] == r["ends"] for r in some), " with any dead:", sum(r["dead_ends"] > 0 for r in some))
print("balloons vs live ends (some group): exact", sum(r["balloons"] == r["ends"] - r["dead_ends"] for r in some), "of", len(some))
for r in zero:
    if r["dead_ends"] != r["ends"]: print("  zero but live ends:", r["doc"], r["dead_ends"], "/", r["ends"])
for r in some:
    if r["balloons"] != r["ends"] - r["dead_ends"]: print("  some mismatch:", r["doc"], "balloons", r["balloons"], "live", r["ends"] - r["dead_ends"], "of", r["ends"])
json.dump(rows, open("survey3.json", "w"), indent=1)
