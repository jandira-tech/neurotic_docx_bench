# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile, re, glob, json
for i in ['07b195a037','e1c745d784','16e531d5a8']:
    p=glob.glob(f'corpus/word/*/docx/{i}*.docx')[0]
    d=zipfile.ZipFile(p).read('word/document.xml').decode()
    k=d.find('<w:gridCol/>')
    if k<0: k=re.search(r'<w:gridCol(?![^>]*w:w=)[^>]*/>', d).start()
    s=d.rfind('<w:tbl>',0,k); e=d.find('</w:tbl>',k)
    t=d[s:e]
    print(i, p.split('/')[2], 'tblPr:', re.search(r'<w:tblPr.*?</w:tblPr>|<w:tblPr/>', t, re.S).group(0)[:300] if re.search(r'<w:tblPr', t) else None)
    print('  grid:', re.search(r'<w:tblGrid>.*?</w:tblGrid>', t, re.S).group(0)[:200])
    print('  tcW count:', t.count('<w:tcW'), 'tcPr sample:', (re.search(r'<w:tcPr>.*?</w:tcPr>', t, re.S) or re.search(r'<w:tcPr/>', t)) and (re.search(r'<w:tcPr>.*?</w:tcPr>', t, re.S) or re.search(r'<w:tcPr/>', t)).group(0)[:200])
sample=open('/tmp/pdf-300/list.txt').read()
for i in ['07b195a037','16e531d5a8','1c41ab317c','6b2515b2e1','97ec0fecd2','ef7870f9f4','e1c745d784','0edc50c464','0a1badc333','43432ba9ab','cbb3bab843','6d510ca476','715d3d2b67','a4dedaa05a','eb6c0a6b3d']:
    insample = i in sample
    sc=None
    if insample:
        for line in open('/tmp/pdf-300/work-pdf3/jubarte/scores.checkpoint.jsonl'):
            if i in line: sc=round(json.loads(line)['result']['overall_score'],1)
    print(i, 'in sample' if insample else '-', sc)