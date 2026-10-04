# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import sys, zipfile, re
src, dst, mode = sys.argv[1], sys.argv[2], sys.argv[3]
z = zipfile.ZipFile(src); doc = z.read('word/document.xml').decode()
if mode == 'unlink':      doc = re.sub(r'<w:hyperlink[^>]*>(.*?)</w:hyperlink>', r'\1', doc, flags=re.S)
if mode == 'nolrpb':      doc = re.sub(r'<w:r>(?:<w:rPr>.*?</w:rPr>)?<w:lastRenderedPageBreak ?/></w:r>', '', doc, flags=re.S)
if mode == 'nocnf':       doc = re.sub(r'<w:cnfStyle [^>]*/>', '', doc)
if mode == 'nomarkins':   doc = re.sub(r'<w:rPr><w:ins [^>]*/></w:rPr>', '', doc)
if mode == 'nomarkins2':  doc = re.sub(r'<w:ins w:id="\d+" w:author="[^"]*" w:date="[^"]*" w16du:dateUtc="[^"]*" ?/>', '', doc)
if mode == 'noinstr':     doc = re.sub(r'<w:r><w:instrText[^>]*>.*?</w:instrText></w:r>', '', doc, flags=re.S)
if mode == 'nofld':       doc = re.sub(r'<w:r>(?:<w:rPr>.*?</w:rPr>)?<w:fldChar [^>]*/></w:r>', '', doc, flags=re.S); doc = re.sub(r'<w:r><w:instrText[^>]*>.*?</w:instrText></w:r>', '', doc, flags=re.S)
if mode == 'tbl2plain':
    body = re.search(r'<w:body>(.*)</w:body>', doc, re.S)
    tbls = re.findall(r'<w:tbl>.*?</w:tbl>', body.group(1), re.S)
    t2 = tbls[-1]; t2n = re.sub(r'<w:ins\b[^>]*>(.*?)</w:ins>', r'\1', t2, flags=re.S); t2n = re.sub(r'<w:rPr><w:ins [^>]*/></w:rPr>', '', t2n)
    doc = doc.replace(t2, t2n)
out = zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED)
for it in z.infolist(): out.writestr(it, doc.encode() if it.filename == 'word/document.xml' else z.read(it.filename))
out.close()