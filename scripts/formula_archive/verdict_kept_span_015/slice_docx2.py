# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""slice_docx2.py IN OUT IDX[,IDX..] [--accept-ins] [--rows N] — keep the listed body children (+ sectPr);
--accept-ins unwraps w:ins (keeps content), --rows N keeps only the first N rows of each table."""
import sys, zipfile, re
src, dst, idxs = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split(',')]
accept = '--accept-ins' in sys.argv
rows = int(sys.argv[sys.argv.index('--rows') + 1]) if '--rows' in sys.argv else None
zin = zipfile.ZipFile(src); doc = zin.read('word/document.xml').decode()
m = re.search(r'<w:body>(.*)</w:body>', doc, re.S); body = m.group(1)
tag_re = re.compile(r'<(/?)(w:p|w:tbl|w:sectPr)(\s[^>]*?)?(/?)>'); stack = []; children = []; cur = None
for mt in tag_re.finditer(body):
    closing, name, selfclose = mt.group(1), mt.group(2), mt.group(4)
    if not closing and not selfclose:
        if not stack: cur = mt.start()
        stack.append(name)
    elif not closing and selfclose:
        if not stack: children.append(body[mt.start():mt.end()])
    else:
        stack.pop()
        if not stack: children.append(body[cur:mt.end()])
sect = [c for c in children if c.startswith('<w:sectPr')]
keep = [children[i] for i in idxs]
if rows is not None:
    def trim(c):
        if not c.startswith('<w:tbl'): return c
        parts = re.split(r'(?=<w:tr[ >])', c)
        head, trs = parts[0], parts[1:]
        last = trs[rows - 1] if len(trs) >= rows else trs[-1]
        kept = trs[:rows]
        tail = re.search(r'</w:tbl>\s*$', c).group(0)
        kept[-1] = kept[-1][:kept[-1].rfind('</w:tr>') + len('</w:tr>')]
        return head + ''.join(kept) + tail
    keep = [trim(c) for c in keep]
if accept:
    keep = [re.sub(r'<w:ins\b[^>]*>(.*?)</w:ins>', r'\1', c, flags=re.S) for c in keep]
new = doc[:m.start(1)] + ''.join(keep) + ''.join(sect) + doc[m.end(1):]
zout = zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED)
for item in zin.infolist():
    zout.writestr(item, new.encode() if item.filename == 'word/document.xml' else zin.read(item.filename))
zout.close()