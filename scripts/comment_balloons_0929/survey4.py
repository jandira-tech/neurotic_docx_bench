"""Predict each doc's balloon count: one per comment referenced in the body, unless its
commentRangeEnd is dead (body level, or first in its paragraph before any w:t/w:delText)."""
import json, re, zipfile
from pathlib import Path
from lxml import etree
C = Path.home() / "temp/T/neurotic_docx_bench/corpus/word"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
TEXT = tuple(f"{W}{t}" for t in ("t", "delText", "drawing", "pict", "object", "sym", "tab", "commentReference"))
def predict(xml: bytes) -> tuple[int, int, int]:
    # Strict documents use the purl.oclc.org namespace; match on local names
    xml = xml.replace(b"http://purl.oclc.org/ooxml/wordprocessingml/main", b"http://schemas.openxmlformats.org/wordprocessingml/2006/main")
    root = etree.fromstring(xml)
    refs = {e.get(f"{W}id") for e in root.iter(f"{W}commentReference")}
    dead = set()
    for e in root.iter(f"{W}commentRangeEnd"):
        par = e.getparent()
        while par is not None and par.tag not in (f"{W}p", f"{W}body", f"{W}tc"):
            par = par.getparent()
        live = False
        if par is not None and par.tag == f"{W}p":
            for x in par.iter():
                if x is e: break
                if x.tag in TEXT and (x.text or x.tag not in (f"{W}t", f"{W}delText")): live = True
        if not live: dead.add(e.get(f"{W}id"))
    return len(refs - dead), len(refs), len(refs & dead)
rows = json.load(open("survey3.json"))
exact = 0
for r in rows:
    st, stem = r["doc"].split("/")
    r["predicted"], r["referenced"], r["dead_referenced"] = predict(zipfile.ZipFile(C / st / "docx" / f"{stem}.docx").read("word/document.xml"))
    exact += r["predicted"] == r["balloons"]
    if r["predicted"] != r["balloons"]:
        print(f"  miss {r['doc']}: balloons {r['balloons']} predicted {r['predicted']} (referenced {r['referenced']}, dead {r['dead_referenced']})")
zero = [r for r in rows if not r["balloons"]]
print(f"exact count {exact}/{len(rows)};  zero-balloon docs predicted zero: {sum(r['predicted'] == 0 for r in zero)}/{len(zero)};"
      f"  docs with balloons predicted >0: {sum(r['predicted'] > 0 for r in rows if r['balloons'])}/{sum(1 for r in rows if r['balloons'])}")
json.dump(rows, open("survey4.json", "w"), indent=1)
