# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile, re, glob, os, fitz
ROM={'i','ii','iii','iv','v','vi','vii','viii','ix','x'}
def roman(s):
    s=s.strip().rstrip('.').lower(); return s in ROM
for stem,numids in (("3ceabcb9e4",["5"]),("62780fc256",["45","46","26","30"]),("9453196efa",["26"]),("1fef0faeb8",["18"])):
    docx=glob.glob(f"corpus/word/clean/docx/{stem}*.docx")[0]; pdf=glob.glob(f"corpus/word/clean/pdf/{stem}*.pdf")
    if not pdf: print(stem,"no word pdf"); continue
    z=zipfile.ZipFile(docx); doc=z.read('word/document.xml').decode('utf8','ignore'); num=z.read('word/numbering.xml').decode('utf8','ignore')
    mar=re.search(r'<w:pgMar [^>]*w:left="(\d+)"', doc); ml=int(mar.group(1))/20 if mar else 72
    d=fitz.open(pdf[0])
    for nid in numids:
        aid=re.search(r'<w:num w:numId="%s"[^>]*>\s*<w:abstractNumId w:val="(\d+)"/>'%nid, num).group(1)
        a=re.search(r'<w:abstractNum w:abstractNumId="%s".*?</w:abstractNum>'%aid, num, re.S).group(0)
        lvl=re.search(r'<w:lvl w:ilvl="0".*?</w:lvl>', a, re.S).group(0)
        ind=re.search(r'<w:ind [^>]*/>', lvl); fmt=re.search(r'numFmt w:val="([^"]*)"', lvl).group(1)
        tabs=re.findall(r'<w:tab [^>]*/>', lvl)
        paras=[m.group(0) for m in re.finditer(r'<w:p[ >].*?</w:p>', doc, re.S) if 'w:numId w:val="%s"'%nid in m.group(0) and 'w:ilvl w:val="0"' in m.group(0)]
        if not paras: continue
        p=paras[0]; t=''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', p)).strip()
        pind=re.search(r'<w:ind [^>]*/>', re.search(r'<w:pPr>.*?</w:pPr>',p,re.S).group(0) if '<w:pPr>' in p else '')
        found=None
        for pi,page in enumerate(d):
            for b in page.get_text("dict")["blocks"]:
                for l in b.get("lines",[]):
                    lt="".join(s["text"] for s in l["spans"])
                    if t[:12] and t[:12] in lt or (fmt=='bullet' and t[:12] in lt):
                        # label = first span or preceding line on same baseline
                        found=(pi+1, [(round(s["bbox"][0],2),round(s["bbox"][2],2),s["text"][:14]) for s in l["spans"][:3]])
                        break
                if found: break
            if found: break
        print(stem, "numId",nid, fmt, ind.group(0) if ind else 'NO IND', "para ind:", pind.group(0) if pind else '-', "tabs:", tabs[:1], "margin", ml)
        print("    text:", repr(t[:30]), "word:", found)