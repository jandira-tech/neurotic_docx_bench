# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Round 4: single comment (R3_keep_4, 0 balloons). Table / reference layout vs tracked changes."""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "temp/T/comment_balloons"))
from ab import read, write
M = Path.home() / "temp/T/comment_balloons/r3b/docx/R3_keep_4.docx"
OUT = Path.home() / "temp/T/comment_balloons/r4/docx"
b = read(M)
head, body = b.split("<w:body>", 1)
body, tail = body.rsplit("<w:sectPr", 1)
tail = "<w:sectPr" + tail
tbl = re.search(r"<w:tbl>.*?</w:tbl>", body, re.S).group(0)
after = body[body.index("</w:tbl>") + len("</w:tbl>"):]
START, END = '<w:commentRangeStart w:id="4"/>', '<w:commentRangeEnd w:id="4"/>'
REF_RUN = re.search(r'<w:r><w:rPr><w:rStyle w:val="CommentReference"/>.*?<w:commentReference w:id="4"/></w:r>', body, re.S).group(0)
cell_p = re.search(r"<w:p\b[^>]*>(?:(?!</w:p>).)*</w:p>", tbl, re.S).group(0)
assert START in tbl and END in after and REF_RUN in after

def doc(new_body): return head + "<w:body>" + new_body + tail
def check(x):
    for m in ("commentRangeStart", "commentRangeEnd", "commentReference"):
        assert x.count(f'<w:{m} w:id="4"/>') == 1, m
    return x
def accept(x):
    x = re.sub(r"<w:rPr>(<w:(?:ins|moveTo)\b[^>]*/>)</w:rPr>", "", x)
    x = re.sub(r"<w:(?:ins|moveTo)\b[^>]*/>", "", x)
    x = re.sub(r"<w:(?:moveToRangeStart|moveToRangeEnd)\b[^>]*/>", "", x)
    x = re.sub(r"<w:(ins|moveTo)\b[^>]*>(.*?)</w:\1>", r"\2", x, flags=re.S)
    assert "<w:ins" not in x and "<w:moveTo" not in x, x[:200]
    return x

V = {}
V["R4_00_control"] = body
# the range starts before the table, at body level, instead of inside the cell
V["R4_01_start_before_tbl"] = START + body.replace(START, "", 1)
# the whole comment inside the cell paragraph: range end + reference run move into it
x = body.replace(END, "", 1).replace(REF_RUN, "", 1)
x = x.replace(cell_p, cell_p.replace("</w:p>", END + REF_RUN + "</w:p>"), 1)
V["R4_02_all_in_cell"] = x
# no table: the cell paragraph stands in the body
V["R4_03_unwrap_table"] = body.replace(tbl, cell_p, 1)
# every tracked change accepted by hand
V["R4_04_accept_tracked"] = accept(body)
# only the table and the reference paragraph
ref_p = re.search(r"<w:p\b[^>]*>(?:(?!</w:p>).)*<w:commentReference w:id=\"4\"/>(?:(?!</w:p>).)*</w:p>", body, re.S).group(0)
V["R4_05_tbl_and_ref_only"] = tbl + END + ref_p
# no page break in the reference paragraph
V["R4_06_no_pagebreak"] = body.replace('<w:r><w:br w:type="page"/></w:r>', "", 1)
# positive-control candidate: one plain paragraph holding the whole comment
V["R4_07_simple_para"] = ('<w:p><w:r><w:t xml:space="preserve">before </w:t></w:r>' + START + "<w:r><w:t>commented text</w:t></w:r>" + END
                          + REF_RUN + "</w:p>")
# the simple paragraph followed by the original body without its comment
V["R4_08_simple_then_rest"] = V["R4_07_simple_para"] + body.replace(START, "").replace(END, "").replace(REF_RUN, "")
# the original body, tracked changes accepted AND the table unwrapped
V["R4_09_unwrap_and_accept"] = accept(V["R4_03_unwrap_table"])
for name, v in V.items():
    write(M, OUT / f"{name}.docx", {"word/document.xml": doc(check(v))})
    print(name, len(v))
