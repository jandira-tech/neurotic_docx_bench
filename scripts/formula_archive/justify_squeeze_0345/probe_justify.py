# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Word probes for the justified-line squeeze (compatibilityMode 15).

Each probe is one justified paragraph on a 468pt measure whose first line,
set naturally, ends `over` points past the measure when its last word `W`
is kept: Word either narrows the spaces and keeps `W` on line 1 or wraps
it. Variables: `over` (0.5..12pt), the number of spaces on the line, the
width of `W`, the face (Calibri 11 / Times New Roman 12).

Usage: uv run python scripts/probe_justify.py OUTDIR  (writes OUTDIR/*.docx
and OUTDIR/manifest.json; then scripts/word_pdf.py --src OUTDIR --out PDFDIR)
"""
import json, os, sys, zipfile, itertools, random
import fitz

FONTS = {
    "Calibri": ("/Applications/Microsoft Word.app/Contents/Resources/DFonts/Calibri.ttf", 11.0),
    "Times New Roman": ("/Applications/Microsoft Word.app/Contents/Resources/DFonts/times.ttf", 12.0),
}
MEASURE = 468.0
VOCAB = ("lorem ipsum dolor amet consectetur adipiscing elit sed eiusmod tempor incididunt labore dolore "
         "magna aliqua enim minim veniam quis nostrud exercitation ullamco laboris nisi aliquip commodo").split()
LAST = {"short": "ad", "mid": "tempor", "long": "consectetur"}

def width(font, size, text):
    return font.text_length(text, fontsize=size)

def fine_word(font, size, target):
    """A word of l/i/t/m letters within 0.03pt of `target` (>= 4pt)."""
    best = None
    letters = "litmno"
    for n in range(1, 14):
        for combo in itertools.product(letters, repeat=min(n, 4)):
            w = "".join(combo) * (n // 4 + 1)
            w = w[:n]
            d = abs(width(font, size, w) - target)
            if best is None or d < best[0]:
                best = (d, w)
        if best[0] < 0.03:
            break
    return best[1]

def build(face, over, nspaces, last_kind, rng):
    path, size = FONTS[face]
    font = fitz.Font(fontfile=path)
    space = width(font, size, " ")
    last = LAST[last_kind]
    # line 1: (nspaces - 1) vocabulary words + fine word + last word = MEASURE + over
    words = [rng.choice(VOCAB) for _ in range(nspaces - 2)]
    while True:
        base = sum(width(font, size, w) for w in words) + (nspaces - 1) * space + width(font, size, last)
        slack = MEASURE + over - base
        if 4.0 <= slack <= 40.0:
            break
        if slack < 4.0:
            words.pop()
            words.append(rng.choice([w for w in VOCAB if len(w) <= 4]))
            if sum(width(font, size, w) for w in words) + (nspaces - 1) * space + width(font, size, last) > MEASURE + over - 4:
                words.pop()
        else:
            words[rng.randrange(len(words))] = rng.choice([w for w in VOCAB if len(w) >= 8])
    fine = fine_word(font, size, slack)
    line1 = words + [fine, last]
    natural = sum(width(font, size, w) for w in line1) + (len(line1) - 1) * space
    tail = " ".join(rng.choice(VOCAB) for _ in range(14))
    text = " ".join(line1) + " " + tail
    return text, natural, len(line1) - 1, width(font, size, last), space

def docx(text, face, size):
    body = (f'<w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr>'
            f'<w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>')
    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}"><w:body>{body}'
           f'<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr></w:body></w:document>')
    styles = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="{W}"><w:docDefaults><w:rPrDefault><w:rPr>'
              f'<w:rFonts w:ascii="{face}" w:hAnsi="{face}" w:cs="{face}"/><w:sz w:val="{int(size*2)}"/><w:szCs w:val="{int(size*2)}"/><w:lang w:val="en-US"/></w:rPr></w:rPrDefault>'
              f'<w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
              f'<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style></w:styles>')
    settings = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings xmlns:w="{W}"><w:compat>'
                f'<w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat></w:settings>')
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
    return {"[Content_Types].xml": ct, "_rels/.rels": rels, "word/document.xml": doc, "word/_rels/document.xml.rels": drels, "word/styles.xml": styles, "word/settings.xml": settings}

def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    rng = random.Random(7)
    manifest = []
    overs = [0.5, 1, 1.5, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12]
    for face, nsp, kind, over in itertools.product(FONTS, (10, 18), LAST, overs):
        text, natural, spaces, last_w, space = build(face, over, nsp, kind, rng)
        fid = f"j_{face[0].lower()}_s{nsp}_{kind}_o{str(over).replace('.', 'p')}"
        parts = docx(text, face, FONTS[face][1])
        with zipfile.ZipFile(os.path.join(out, fid + ".docx"), "w", zipfile.ZIP_DEFLATED) as z:
            for name, data in parts.items():
                z.writestr(name, data)
        manifest.append(dict(id=fid, face=face, size=FONTS[face][1], nspaces=spaces, last=LAST[kind], last_w=round(last_w, 2), space=round(space, 3), over=round(natural - MEASURE, 3), text=text))
    json.dump(manifest, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    print(len(manifest), "probes")

if __name__ == "__main__":
    main()
