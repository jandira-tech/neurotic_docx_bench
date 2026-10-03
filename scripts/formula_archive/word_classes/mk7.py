# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
exec(open('mk2.py').read().split("B=body(False)")[0])
import os,re,zipfile,html
os.makedirs('src10',exist_ok=True)
doc=open('/tmp/conejo/probe_496/x/word/document.xml',encoding='utf-8').read()
i=doc.find("durvalumab':ab,ti"); p0=doc.rfind('<w:p ',0,i); p1=doc.find('</w:p>',i)+6
para=doc[p0:p1]
text=''.join(html.unescape(t) for t in re.findall(r'<w:t(?: [^>]*)?>([^<]*)</w:t>',para))
print(repr(text[:200]))
def mkA4(path, body, settings):
    mk2(path, body, '', settings)
    zi=zipfile.ZipFile(path); items={n:zi.read(n) for n in zi.namelist()}; zi.close()
    d=items['word/document.xml'].decode().replace('<w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="720" w:right="1440" w:bottom="720" w:left="1440"','<w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="720" w:right="720" w:bottom="720" w:left="720"')
    items['word/document.xml']=d.encode()
    z=zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED)
    for n in ['[Content_Types].xml']+[n for n in items if n!='[Content_Types].xml']: z.writestr(n,items[n])
    z.close()
CSC='<w:characterSpacingControl w:val="compressPunctuation"/>'
from xml.sax.saxutils import escape
mkA4('src10/y1_onerun.docx', f'<w:p><w:pPr><w:spacing w:after="0"/></w:pPr>{r(escape(text))}</w:p>', CSC)
mkA4('src10/y2_runs.docx', para, CSC)