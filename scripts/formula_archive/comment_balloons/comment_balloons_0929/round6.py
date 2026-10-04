# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Round 6: an empty comment range (its start and end adjacent, or with an empty run
between) followed by its reference. Corpus 6ef6726c28 has a balloon for that shape;
the 0929 probe with an empty w:t run between said dead. Which is it, and what matters?"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "temp/T/comment_balloons"))
from ab import read, write
M = Path.home() / "temp/T/comment_balloons/r3b/docx/R3_keep_4.docx"
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/r6/docx")
b = read(M)
head, body = b.split("<w:body>", 1)
tail = "<w:sectPr" + body.rsplit("<w:sectPr", 1)[1]
S, E = '<w:commentRangeStart w:id="4"/>', '<w:commentRangeEnd w:id="4"/>'
REF = re.search(r'<w:r><w:rPr><w:rStyle w:val="CommentReference"/>.*?<w:commentReference w:id="4"/></w:r>', body, re.S).group(0)
PLAINREF = '<w:r><w:commentReference w:id="4"/></w:r>'
def r(t): return f'<w:r><w:t xml:space="preserve">{t}</w:t></w:r>'
def p(*xs): return "<w:p>" + "".join(xs) + "</w:p>"
PPR = '<w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
P1 = r("First paragraph, commented.")
P2 = r("Second paragraph.")
S9 = '<w:commentRangeStart w:id="9"/>'
V = {
    "R6_00_one_para": p(S, P1, E, REF) + p(P2),                       # positive control (R5_00)
    "R6_01_empty_range_ref": p(P1) + p(S, E, REF) + p(P2),            # 6ef6726c28's shape
    "R6_02_empty_t_between": p(P1) + p(S, r(""), E, REF) + p(P2),     # the 0929 probe (said dead)
    "R6_03_empty_range_plainref": p(P1) + p(S, E, PLAINREF) + p(P2),
    "R6_04_sibling_start": p(P1) + p(S9, S, E, REF) + p(P2),          # a stray start of another comment first
    "R6_05_ppr_empty_range": p(P1) + p(PPR, S, E, REF) + p(P2),
    "R6_06_empty_range_ref_text": p(P1) + p(S, E, REF, P2),
    "R6_07_empty_range_last": p(P1) + p(P2) + p(S, E, REF),           # last paragraph, as in 6ef6726c28
    "R6_08_end_first_dead_control": p(S, P1) + p(E, REF, P2),         # R5_04, dead control
    "R6_09_empty_t_plainref": p(P1) + p(S, r(""), E, PLAINREF) + p(P2),
}
OUT.mkdir(parents=True, exist_ok=True)
for name, v in V.items():
    write(M, OUT / f"{name}.docx", {"word/document.xml": head + "<w:body>" + v + tail})
    print(name)
