"""Second truth table over the same 151 docs (balloon counts reused from survey.json)."""
import json, re, zipfile
from collections import Counter
from pathlib import Path
C = Path.home() / "temp/T/neurotic_docx_bench/corpus/word"
def cnt(p, b): return len(re.findall(p, b))
FEATS = {
    "moveTo": lambda b: "<w:moveTo " in b,
    "moveFrom": lambda b: "<w:moveFrom " in b,
    "moveTo_unbalanced": lambda b: cnt(r"<w:moveToRangeStart\b", b) != cnt(r"<w:moveToRangeEnd\b", b),
    "moveFrom_unbalanced": lambda b: cnt(r"<w:moveFromRangeStart\b", b) != cnt(r"<w:moveFromRangeEnd\b", b),
    "moveTo_without_moveFrom": lambda b: "<w:moveTo " in b and "<w:moveFrom " not in b,
    "empty_ins": lambda b: bool(re.search(r"<w:ins\b[^>]*></w:ins>", b)),
    "comment_start_in_tc": lambda b: bool(re.search(r"<w:tc>(?:(?!</w:tc>).)*<w:commentRangeStart", b, re.S)),
    "ref_para_after_tbl": lambda b: bool(re.search(r"</w:tbl>(?:<w:commentRangeEnd[^>]*/>)*<w:p\b[^>]*>(?:(?!</w:p>).)*<w:commentReference", b, re.S)),
    "comment_unbalanced": lambda b: cnt(r"<w:commentRangeStart\b", b) != cnt(r"<w:commentRangeEnd\b", b),
    "ref_without_range": lambda b: cnt(r"<w:commentReference\b", b) > cnt(r"<w:commentRangeStart\b", b),
    "pageBreak_br": lambda b: 'w:type="page"' in b,
    "rsidSect": lambda b: "w:rsidSect=" in b,
    "sectPr_mid": lambda b: b.count("<w:sectPr") > 1,
}
rows = json.load(open("survey.json"))
for r in rows:
    st, stem = r["doc"].split("/")
    z = zipfile.ZipFile(C / st / "docx" / f"{stem}.docx")
    b = z.read("word/document.xml").decode("utf8", "replace")
    s = z.read("word/settings.xml").decode("utf8", "replace") if "word/settings.xml" in z.namelist() else ""
    for k, f in FEATS.items(): r[k] = f(b)
    r["family"] = re.sub(r"^[0-9a-f]{10}_", "", stem)
    r["settings_revisionView"] = "<w:revisionView" in s
    r["settings_trackRevisions"] = "<w:trackRevisions" in s
zero = [r for r in rows if not r["balloons"]]; some = [r for r in rows if r["balloons"]]
print(f"{'feature':26s} zero(n={len(zero)}) some(n={len(some)})")
for k in list(FEATS) + ["settings_revisionView", "settings_trackRevisions"]:
    print(f"{k:26s} {sum(r[k] for r in zero):10d} {sum(r[k] for r in some):10d}")
print("zero families:", Counter(re.sub(r"_\d+$", "_N", r["family"]) for r in zero).most_common(8))
print("some families:", Counter(re.sub(r"_\d+$", "_N", r["family"]) for r in some).most_common(8))
json.dump(rows, open("survey2.json", "w"), indent=1)
