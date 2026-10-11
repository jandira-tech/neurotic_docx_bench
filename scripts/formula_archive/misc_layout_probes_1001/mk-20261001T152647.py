# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile,re
src='/tmp/conejo/3f52/src_fixed.docx'
import os,subprocess
X='/tmp/conejo/3f52/x'
items={}
for root,_,fs in os.walk(X):
    for f in fs:
        p=os.path.join(root,f); items[os.path.relpath(p,X)]=open(p,'rb').read()
doc=items['word/document.xml'].decode()
head=doc[:doc.find('<w:body>')+len('<w:body>')]
sect=re.findall(r'<w:sectPr[ >].*?</w:sectPr>',doc,re.S)[-1]
# drop sectPrChange for simplicity
sect=re.sub(r'<w:sectPrChange.*?</w:sectPrChange>','',sect,flags=re.S)
def sq11(jc,ppr_extra='',rpr=''):
    out=''
    for j in range(20,46):
        txt='ab '*28+'i'*j+' tail'
        out+=f'<w:p><w:pPr>{ppr_extra}<w:spacing w:after="0"/><w:jc w:val="{jc}"/></w:pPr><w:r><w:rPr>{rpr}<w:sz w:val="22"/></w:rPr><w:t xml:space="preserve">{txt}</w:t></w:r></w:p>'
    return out
def build(name, body, settings=None, styles=None):
    it=dict(items); it['word/document.xml']=(head+body+sect+'</w:body></w:document>').encode()
    if settings is not None: it['word/settings.xml']=settings.encode()
    if styles is not None: it['word/styles.xml']=styles.encode()
    z=zipfile.ZipFile(f'src/{name}.docx','w',zipfile.ZIP_DEFLATED)
    z.writestr('[Content_Types].xml',it.pop('[Content_Types].xml'))
    for k,v in it.items(): z.writestr(k,v)
    z.close()
W='xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
mine_cp=f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings {W}><w:characterSpacingControl w:val="compressPunctuation"/><w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="14"/></w:compat></w:settings>'
mine_dnc=mine_cp.replace('compressPunctuation','doNotCompress')
build('t0_real', sq11('both'))
build('t1_mysettings', sq11('both'), settings=mine_cp)
build('t1_mysettings_dnc', sq11('both'), settings=mine_dnc)
orig_set=items['word/settings.xml'].decode()
build('t2_real_dnc', sq11('both'), settings=orig_set.replace('compressPunctuation','doNotCompress'))