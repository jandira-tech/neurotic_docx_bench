# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Variants of 75252a6bb0 (its first-page header: a 75pt picture paragraph,
an empty bold paragraph, an empty Header paragraph; Word's title baseline
170.3, 15.0 under the header's last mark) — the synthetic shape
(`probe_header_push.py` h5/h12) puts the title 35.0 under that mark.
Each variant removes one thing from the document to find the term.

Usage: uv run python scripts/probe_header_752.py OUTDIR
"""
import json, os, re, sys, zipfile

SRC = "corpus/word/tracking_without_comments/docx/75252a6bb0_015e4665fb2bcc025f24e7b451197933975b68ae37052ca7.docx"

def sub1(p, name, old, new, count=1):
    s = p[name]
    assert s.count(old) == count, (name, old[:60], s.count(old))
    p[name] = s.replace(old, new)

P3 = '<w:p w14:paraId="7B82D2A2" w14:textId="77777777" w:rsidR="003C3D27" w:rsidRDefault="003C3D27"><w:pPr><w:pStyle w:val="Header"/></w:pPr></w:p>'
P2 = '<w:p w14:paraId="686EBE2E" w14:textId="77777777" w:rsidR="004D5F80" w:rsidRPr="00F4697D" w:rsidRDefault="004D5F80" w:rsidP="004D5F80"><w:pPr><w:rPr><w:b/></w:rPr></w:pPr></w:p>'

def drop_p3(p): sub1(p, "word/header2.xml", P3, "")
def drop_p2(p): sub1(p, "word/header2.xml", P2, "")
def drop_jc_right(p): sub1(p, "word/header2.xml", '<w:jc w:val="right"/>', "")
def drop_contextual(p): sub1(p, "word/styles.xml", '<w:spacing w:before="240" w:after="240"/><w:contextualSpacing/><w:outlineLvl w:val="0"/>', '<w:spacing w:before="240" w:after="240"/><w:outlineLvl w:val="0"/>')
def drop_docgrid(p): sub1(p, "word/document.xml", '<w:docGrid w:linePitch="360"/>', "", count=p["word/document.xml"].count('<w:docGrid w:linePitch="360"/>'))
def drop_titlepg(p): sub1(p, "word/document.xml", '<w:titlePg/>', "", count=p["word/document.xml"].count('<w:titlePg/>'))
def plain_title(p):
    d = p["word/document.xml"]
    i = d.index("<w:body>") + len("<w:body>")
    j = d.index("</w:p>", i) + len("</w:p>")
    p["word/document.xml"] = d[:i] + '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Title</w:t></w:r></w:p>' + d[j:]
def drop_sdt_toc(p):
    d = p["word/document.xml"]
    i = d.index("<w:sdt>"); j = d.index("</w:sdt>", i) + len("</w:sdt>")
    p["word/document.xml"] = d[:i] + d[j:]

PROBES = {
    "v0_as_is": lambda p: None,
    "v1_no_p3": drop_p3,
    "v2_no_p2": drop_p2,
    "v3_no_jc_right": drop_jc_right,
    "v4_no_contextual": drop_contextual,
    "v5_no_docgrid": drop_docgrid,
    "v6_no_titlepg": drop_titlepg,
    "v7_plain_title": plain_title,
    "v8_no_toc_sdt": drop_sdt_toc,
}

def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    with zipfile.ZipFile(SRC) as z:
        names = z.namelist()
        raw = {n: z.read(n) for n in names}
    for fid, fn in PROBES.items():
        parts = {n: (b.decode("utf-8") if n.endswith((".xml", ".rels")) else b) for n, b in raw.items()}
        fn(parts)
        with zipfile.ZipFile(os.path.join(out, fid + ".docx"), "w", zipfile.ZIP_DEFLATED) as z:
            for n in names:
                z.writestr(n, parts[n])
    json.dump(list(PROBES), open(os.path.join(out, "manifest.json"), "w"), indent=1)
    print(len(PROBES), "probes")

if __name__ == "__main__":
    main()
