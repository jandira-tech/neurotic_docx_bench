# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import re
doc=open('word/document.xml').read(); num=open('word/numbering.xml').read()
seen=set()
for m in re.finditer(r'<w:p[ >].*?</w:p>', doc, re.S):
    p=m.group(0)
    np=re.search(r'<w:numPr>.*?</w:numPr>', p, re.S)
    if not np: continue
    ilvl=re.search(r'w:ilvl w:val="(\d+)"', np.group(0)); nid=re.search(r'w:numId w:val="(\d+)"', np.group(0))
    key=(nid.group(1) if nid else None, ilvl.group(1) if ilvl else None)
    t=''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', p))
    ind=re.search(r'<w:ind [^>]*/>', p); tabs=re.search(r'<w:tabs>.*?</w:tabs>', p, re.S)
    if key not in seen and len(seen)<6:
        seen.add(key); print(key, repr(t[:40]), ind.group(0) if ind else '', (tabs.group(0)[:120] if tabs else ''))
for nid,_ in list(seen):
    m=re.search(r'<w:num w:numId="%s"[^>]*>.*?<w:abstractNumId w:val="(\d+)"/>'%nid, num, re.S)
    if not m: continue
    aid=m.group(1)
    a=re.search(r'<w:abstractNum w:abstractNumId="%s"[^>]*>.*?</w:abstractNum>'%aid, num, re.S).group(0)
    lvl0=re.search(r'<w:lvl w:ilvl="0".*?</w:lvl>', a, re.S).group(0)
    print("numId",nid,"abstract",aid, re.sub(r'\s+',' ',lvl0)[:600])