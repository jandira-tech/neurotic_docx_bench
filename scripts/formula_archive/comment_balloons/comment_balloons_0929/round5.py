# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Round 5: plain paragraphs, one comment. Where do the range end and the reference sit?"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "temp/T/comment_balloons"))
from ab import read, write
M = Path.home() / "temp/T/comment_balloons/r3b/docx/R3_keep_4.docx"
OUT = Path.home() / "temp/T/comment_balloons/r5/docx"
b = read(M)
head, body = b.split("<w:body>", 1)
tail = "<w:sectPr" + body.rsplit("<w:sectPr", 1)[1]
S, E = '<w:commentRangeStart w:id="4"/>', '<w:commentRangeEnd w:id="4"/>'
REF = re.search(r'<w:r><w:rPr><w:rStyle w:val="CommentReference"/>.*?<w:commentReference w:id="4"/></w:r>', body, re.S).group(0)
def r(t): return f'<w:r><w:t xml:space="preserve">{t}</w:t></w:r>'
def p(*xs): return "<w:p>" + "".join(xs) + "</w:p>"
P1 = r("First paragraph, commented.")
P2 = r("Second paragraph.")
V = {
    # the whole comment inside one paragraph (positive control)
    "R5_00_one_para": p(S, P1, E, REF) + p(P2),
    # end in P1, the reference alone at the start of P2
    "R5_01_end_p1_ref_p2_start": p(S, P1, E) + p(REF, P2),
    # end at body level between P1 and P2, reference at the start of P2 (the corpus layout)
    "R5_02_end_body_ref_p2_start": p(S, P1) + E + p(REF, P2),
    # end at body level, reference alone in its own paragraph (exactly the corpus layout)
    "R5_03_end_body_ref_own_para": p(S, P1) + E + p(REF) + p(P2),
    # end and reference both at the start of P2
    "R5_04_end_ref_p2_start": p(S, P1) + p(E, REF, P2),
    # end and reference at the END of P2 (a range spanning two paragraphs, the usual shape)
    "R5_05_span_end_ref_p2_end": p(S, P1) + p(P2, E, REF),
    # end in P1, reference at the end of P2
    "R5_06_end_p1_ref_p2_end": p(S, P1, E) + p(P2, REF),
    # start at body level before P1, end and reference at the end of P1
    "R5_07_start_body": S + p(P1, E, REF) + p(P2),
    # end at body level, reference at the end of P2 (after text)
    "R5_08_end_body_ref_p2_end": p(S, P1) + E + p(P2, REF),
    # the corpus layout but with a text run before the reference in its paragraph
    "R5_09_end_body_text_then_ref": p(S, P1) + E + p(r("x"), REF) + p(P2),
}
for name, v in V.items():
    assert v.count(S) == v.count(E) == v.count("<w:commentReference ") == 1
    write(M, OUT / f"{name}.docx", {"word/document.xml": head + "<w:body>" + v + tail})
    print(name)
