# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Word's endnote area at the end of a document: where the separator and
the first note land under the last body line.

9134397db6_endnotes_sample (A4, Normal = Times New Roman 12 without
spacing, Endnote style 10pt hanging 339, an endnote separator note of a
bare `w:separator` run): Word paints the body baseline at 67.92, the
separator rule at 88.80–89.28 with its paragraph mark at baseline 91.92,
and the first note at 114.00. The variants change one thing each (the
note size, the separator run, the body, the note's spacing before, the
same notes as footnotes) so the terms of that geometry can be read off.

Usage: uv run python scripts/probe_endnote_sep.py OUTDIR
"""
import json, os, sys, zipfile

SRC = "corpus/word/clean/docx/9134397db6_endnotes_sample.docx"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

def edit(parts, fn):
    parts = dict(parts)
    fn(parts)
    return parts

def sub1(parts, name, old, new):
    s = parts[name]
    assert s.count(old) == 1, (name, old, s.count(old))
    parts[name] = s.replace(old, new)

NOTE_SZ = '<w:rPr><w:sz w:val="20" /><w:szCs w:val="20" /></w:rPr></w:style></w:styles>'
SEP_RUN = '<w:endnote w:id="0" w:type="separator"><w:p><w:r><w:separator /></w:r></w:p></w:endnote>'
NOTE_PPR = '<w:pPr><w:suppressLineNumbers /><w:ind w:hanging="339" w:left="339" w:right="0" /></w:pPr>'
BODY_END = '</w:p><w:sectPr>'
NORMAL_PPR = '<w:pPr><w:widowControl w:val="false" /><w:tabs><w:tab w:leader="none" w:pos="709" w:val="left" /></w:tabs><w:suppressAutoHyphens w:val="true" /></w:pPr>'

def to_footnotes(p):
    en = p.pop("word/endnotes.xml")
    p["word/footnotes.xml"] = (en.replace("w:endnotes", "w:footnotes").replace("<w:endnote ", "<w:footnote ")
                               .replace("</w:endnote>", "</w:footnote>").replace("w:endnoteRef", "w:footnoteRef"))
    p["word/document.xml"] = p["word/document.xml"].replace("w:endnoteReference", "w:footnoteReference").replace("w:endnotePr", "w:footnotePr")
    p["word/settings.xml"] = p["word/settings.xml"].replace("w:endnotePr", "w:footnotePr").replace("<w:endnote ", "<w:footnote ")
    p["[Content_Types].xml"] = p["[Content_Types].xml"].replace("/word/endnotes.xml", "/word/footnotes.xml").replace("wordprocessingml.endnotes+xml", "wordprocessingml.footnotes+xml")
    p["word/_rels/document.xml.rels"] = p["word/_rels/document.xml.rels"].replace('relationships/endnotes" Target="endnotes.xml"', 'relationships/footnotes" Target="footnotes.xml"')

PROBES = {
    "e0_as_is": lambda p: None,
    # the note text at 12pt and at 8pt: does the separator move with it?
    "e1_note_sz24": lambda p: sub1(p, "word/styles.xml", NOTE_SZ, NOTE_SZ.replace('"20"', '"24"')),
    "e2_note_sz16": lambda p: sub1(p, "word/styles.xml", NOTE_SZ, NOTE_SZ.replace('"20"', '"16"')),
    # the separator run at 20pt and its paragraph mark at 20pt
    "e3_sep_run_40": lambda p: sub1(p, "word/endnotes.xml", SEP_RUN, SEP_RUN.replace('<w:r><w:separator />', '<w:r><w:rPr><w:sz w:val="40"/></w:rPr><w:separator />')),
    "e4_sep_mark_40": lambda p: sub1(p, "word/endnotes.xml", SEP_RUN, SEP_RUN.replace('<w:p><w:r>', '<w:p><w:pPr><w:rPr><w:sz w:val="40"/></w:rPr></w:pPr><w:r>')),
    # the separator paragraph's spacing before / after
    "e5_sep_before_200": lambda p: sub1(p, "word/endnotes.xml", SEP_RUN, SEP_RUN.replace('<w:p><w:r>', '<w:p><w:pPr><w:spacing w:before="200"/></w:pPr><w:r>')),
    "e6_sep_after_200": lambda p: sub1(p, "word/endnotes.xml", SEP_RUN, SEP_RUN.replace('<w:p><w:r>', '<w:p><w:pPr><w:spacing w:after="200"/></w:pPr><w:r>')),
    # the first note's spacing before, the body paragraph's spacing after
    "e7_note_before_200": lambda p: sub1(p, "word/styles.xml", NOTE_PPR, NOTE_PPR.replace('<w:suppressLineNumbers />', '<w:suppressLineNumbers /><w:spacing w:before="200"/>')),
    "e8_body_after_200": lambda p: sub1(p, "word/styles.xml", NORMAL_PPR, NORMAL_PPR.replace('</w:pPr>', '<w:spacing w:after="200"/></w:pPr>')),
    # a second body paragraph after the references
    "e9_second_para": lambda p: sub1(p, "word/document.xml", BODY_END, '</w:p><w:p><w:pPr><w:pStyle w:val="style0" /></w:pPr><w:r><w:t>Second</w:t></w:r></w:p><w:sectPr>'),
    # the same notes as footnotes: the page-bottom geometry with the same fonts
    "f0_footnotes": to_footnotes,
}

def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    with zipfile.ZipFile(SRC) as z:
        base = {n: z.read(n).decode("utf-8") for n in z.namelist()}
    for fid, fn in PROBES.items():
        parts = edit(base, fn)
        with zipfile.ZipFile(os.path.join(out, fid + ".docx"), "w", zipfile.ZIP_DEFLATED) as z:
            for name, data in parts.items():
                z.writestr(name, data)
    json.dump(list(PROBES), open(os.path.join(out, "manifest.json"), "w"), indent=1)
    print(len(PROBES), "probes")

if __name__ == "__main__":
    main()
