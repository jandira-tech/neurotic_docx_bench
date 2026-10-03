# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import re, sys, zipfile; from pathlib import Path
sys.path.insert(0, str(Path.home() / "temp/T/comment_balloons"))
from ab import read, write
from blocklib import blocks, drop
M = Path.home() / "temp/T/comment_balloons/r2/docx/R2_99_drop_all_unmarked.docx"
OUT = Path.home() / "temp/T/comment_balloons/" / (sys.argv[1] if len(sys.argv) > 1 else "r3") / "docx"
b = read(M); cx = read(M, "word/comments.xml")
print("comment ids:", re.findall(r'<w:comment\b[^>]*w:id="(\d+)"', cx))
def rm_comments(ids):
    d = b
    for i in ids:
        d = re.sub(rf'<w:commentRange(?:Start|End) w:id="{i}"\s*/>', "", d)
        d = re.sub(rf'<w:r(?:\s[^>]*)?>(?:(?!</w:r>).)*<w:commentReference w:id="{i}"\s*/></w:r>', "", d, flags=re.S)
        assert not re.search(rf'<w:comment(?:Reference|RangeStart|RangeEnd) w:id="{i}"', d), i
    c = cx
    for i in ids: c = re.sub(rf'<w:comment\b[^>]*w:id="{i}".*?</w:comment>', "", c, flags=re.S)
    return {"word/document.xml": d, "word/comments.xml": c}
write(M, OUT / "R3_00_control.docx", {})
for tag, ids in (("keep_11_12_296_297", ["4", "5"]), ("keep_4_5_296_297", ["11", "12"]), ("keep_4_5_11_12", ["296", "297"]),
                 ("keep_4_5", ["11", "12", "296", "297"]), ("keep_11_12", ["4", "5", "296", "297"]), ("keep_296_297", ["4", "5", "11", "12"]),
                 ("keep_4", ["5", "11", "12", "296", "297"]), ("keep_11", ["4", "5", "12", "296", "297"])):
    write(M, OUT / f"R3_{tag}.docx", rm_comments(ids))
# strip the extended comment parts
z = zipfile.ZipFile(M); names = z.namelist()
ext = [n for n in names if re.search(r"word/(commentsExtended|commentsIds|commentsExtensible|people)\.xml$", n)]
rels = z.read("word/_rels/document.xml.rels").decode(); ct = z.read("[Content_Types].xml").decode()
for n in ext:
    fn = n.split("/")[-1]
    rels = re.sub(rf'<Relationship\b[^>]*Target="{fn}"[^>]*/>', "", rels)
    ct = re.sub(rf'<Override\b[^>]*PartName="/{n}"[^>]*/>', "", ct)
out = OUT / "R3_no_extended_parts.docx"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zo:
    for it in z.infolist():
        if it.filename in ext: continue
        data = rels.encode() if it.filename == "word/_rels/document.xml.rels" else ct.encode() if it.filename == "[Content_Types].xml" else z.read(it.filename)
        zo.writestr(it, data)
print("stripped", ext)
bl = blocks(b); t = [i for i, x in enumerate(bl) if x[2] == "w:tbl"]
print("tables:", t)
