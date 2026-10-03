# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Word's WordPerfect justification (`w:wpJustification`, compat 14): how
many characters a justified line may hold past its width, and how they
are compressed.

041ec70002 (Legal, 1in margins = 468pt = 65 Courier New 12 cells,
`jc both`, the WordPerfect compat set): Word's PDF holds 66 and 67
characters on 468pt, every glyph advanced 7.0908 (468/66) instead of
7.2; jubarte wraps at 65 and runs 37 pages to Word's 35. Each probe is
one justified paragraph whose first line naturally holds N characters
(ten five-letter words, then a word of N−60 letters, then more words);
Word keeps the long word on the line, compressed, or wraps it.

Usage: uv run python scripts/probe_wp_justify.py OUTDIR
"""
import json, os, sys, zipfile

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WP_COMPAT = ('<w:wpJustification/><w:noTabHangInd/><w:subFontBySize/><w:suppressBottomSpacing/>'
             '<w:truncateFontHeightsLikeWP6/><w:usePrinterMetrics/><w:wrapTrailSpaces/><w:useWord97LineBreakRules/>')

def text_for(n, shape="ten"):
    tail = ["north", "south", "east", "west", "upper", "lower", "inner", "outer", "first", "last", "wide", "tall"] * 3
    if shape == "ten":
        words = ["alpha", "bravo", "delta", "gamma", "kappa", "omega", "sigma", "theta", "zetas", "yotta"]
        long = "m" * (n - 60)
        return " ".join(words + [long] + tail)
    if shape == "few":  # three 15-letter words, then a word of n-48 letters: 3 spaces on the line
        words = ["abcdefghijklmno", "pqrstuvwxyzabcd", "efghijklmnopqrs"]
        return " ".join(words + ["m" * (n - 48)] + tail)
    if shape == "many":  # 21 two-letter words (62 chars), then a word of n-63 letters: 21 spaces on the line
        words = ["ab", "cd", "ef", "gh", "ij", "kl", "mn", "op", "qr", "st", "uv", "wx", "yz", "ba", "dc", "fe", "hg", "ji", "lk", "nm", "po"]
        return " ".join(words + ["m" * (n - 63)] + tail)
    raise ValueError(shape)

def parts(n, jc="both", compat=WP_COMPAT, mode="14", size=24, font="Courier New", shape="ten", right=1440):
    doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}"><w:body>'
           f'<w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="{jc}"/></w:pPr>'
           f'<w:r><w:t xml:space="preserve">{text_for(n, shape)}</w:t></w:r></w:p>'
           f'<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="{right}" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr></w:body></w:document>')
    styles = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="{W}"><w:docDefaults><w:rPrDefault><w:rPr>'
              f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}"/><w:sz w:val="{size}"/><w:szCs w:val="{size}"/><w:lang w:val="en-US"/></w:rPr></w:rPrDefault>'
              f'<w:pPrDefault><w:pPr/></w:pPrDefault></w:docDefaults>'
              f'<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style></w:styles>')
    settings = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings xmlns:w="{W}"><w:compat>{compat}'
                f'<w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="{mode}"/></w:compat></w:settings>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
          '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
             '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/></Relationships>')
    return {"[Content_Types].xml": ct, "_rels/.rels": rels, "word/document.xml": doc, "word/_rels/document.xml.rels": drels,
            "word/styles.xml": styles, "word/settings.xml": settings}

PROBES = {}
for n in (65, 66, 67, 68, 69, 70, 72, 75):
    PROBES[f"j{n}_wp"] = dict(n=n)
PROBES["j67_wp_left"] = dict(n=67, jc="left")
PROBES["j67_wp_only"] = dict(n=67, compat="<w:wpJustification/>")
PROBES["j67_printer_only"] = dict(n=67, compat="<w:usePrinterMetrics/>")
PROBES["j66_compat15"] = dict(n=66, compat="", mode="15")
PROBES["j67_compat15"] = dict(n=67, compat="", mode="15")
PROBES["j68_compat15"] = dict(n=68, compat="", mode="15")
# 11pt Courier: 6.6pt cells, 70.9 per line; N counts cells past 70
for n in (71, 72, 73, 74):
    PROBES[f"k{n}_wp_11pt"] = dict(n=n, size=22)

# round 2: a quarter of the line's spaces (3 spaces allow 5.4pt, 21 allow 37.8) against a flat share of every advance
PROBES["w66_few_wp"] = dict(n=66, shape="few")       # overflow 7.2: quarter says wrap, 3 % says keep
PROBES["w67_few_wp"] = dict(n=67, shape="few")
PROBES["w67_many_wp"] = dict(n=67, shape="many")     # overflow 14.4 under a 4-letter last word: the word cap says wrap
PROBES["w70_many_wp"] = dict(n=70, shape="many")     # overflow 36 under 37.8 of spaces: quarter keeps, 3 % wraps
PROBES["w72_many_wp"] = dict(n=72, shape="many")     # overflow 50.4: both wrap
PROBES["w66_few_c15"] = dict(n=66, shape="few", compat="", mode="15")
PROBES["w70_many_c15"] = dict(n=70, shape="many", compat="", mode="15")

# round 3: the compression floor between 95.8 % (wraps) and 97.0 % (keeps): Courier 10 (78 cells), 9 (86.7), 13 (60)
PROBES["c10_80"] = dict(n=80, size=20)   # 468/480 = 97.5 %
PROBES["c10_81"] = dict(n=81, size=20)   # 96.3 %
PROBES["c9_90"] = dict(n=90, size=18)    # 96.3 %
PROBES["c13_62"] = dict(n=62, size=26)   # 96.8 %
PROBES["c13_61"] = dict(n=61, size=26)   # 98.4 %

# round 4: the floor sits between 95.82 % (wraps) and 96.3 % (keeps)
PROBES["c14_58"] = dict(n=58, size=28)   # 468/487.2 = 96.06 %
PROBES["c12h_65"] = dict(n=65, size=25)  # 7.5pt cells: 468/487.5 = 96.00 %

# round 5: proportional faces. The first eleven words ("alpha … yotta mmmmmmmmmm") run 456.2pt in Times New
# Roman 12 and 444.85 in Arial 12 (Word 16, left-aligned); the right margin sets the measure to that width
# over 1.03, 1.035, 1.04, 1.045 and 1.05.
for r, right in ((1.03, 1942), (1.035, 1984), (1.04, 2027), (1.045, 2068), (1.05, 2110)):
    PROBES[f"p_tnr_{int(r * 1000)}"] = dict(n=70, font="Times New Roman", right=right)
for r, right in ((1.03, 2162), (1.035, 2203), (1.04, 2246), (1.045, 2286), (1.05, 2326)):
    PROBES[f"p_arial_{int(r * 1000)}"] = dict(n=70, font="Arial", right=right)

def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for fid, spec in PROBES.items():
        with zipfile.ZipFile(os.path.join(out, fid + ".docx"), "w", zipfile.ZIP_DEFLATED) as z:
            for name, data in parts(**spec).items():
                z.writestr(name, data)
    json.dump({k: {kk: vv for kk, vv in v.items() if kk != "compat"} for k, v in PROBES.items()},
              open(os.path.join(out, "manifest.json"), "w"), indent=1)
    print(len(PROBES), "probes")

if __name__ == "__main__":
    main()
