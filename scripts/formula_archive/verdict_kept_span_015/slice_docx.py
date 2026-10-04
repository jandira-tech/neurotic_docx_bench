# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""slice_docx.py IN OUT START END — keep body children [START, END) plus sectPr."""
import sys, zipfile, re, shutil
src, dst, start, end = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
zin = zipfile.ZipFile(src)
doc = zin.read('word/document.xml').decode()
m = re.search(r'<w:body>(.*)</w:body>', doc, re.S)
body = m.group(1)
# split top-level children: w:p, w:tbl, w:sectPr, bookmark/ comment markers at top level
tokens = []
i = 0
depth_tags = ('w:p', 'w:tbl')
pos = 0
children = []
# simple top-level tokenizer using a stack
tag_re = re.compile(r'<(/?)(w:p|w:tbl|w:sectPr)(\s[^>]*?)?(/?)>')
stack = []
cur_start = None
for mt in tag_re.finditer(body):
    closing, name, attrs, selfclose = mt.group(1), mt.group(2), mt.group(3), mt.group(4)
    if not closing and not selfclose:
        if not stack:
            cur_start = mt.start()
        stack.append(name)
    elif not closing and selfclose:
        if not stack:
            children.append(body[mt.start():mt.end()])
    else:
        stack.pop()
        if not stack:
            children.append(body[cur_start:mt.end()])
sect = [c for c in children if c.startswith('<w:sectPr')]
keep = [c for c in children if not c.startswith('<w:sectPr')][start:end]
new = doc[:m.start(1)] + ''.join(keep) + ''.join(sect) + doc[m.end(1):]
zout = zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED)
for item in zin.infolist():
    data = new.encode() if item.filename == 'word/document.xml' else zin.read(item.filename)
    zout.writestr(item, data)
zout.close()
print(f"{len(children)} children → kept {len(keep)}")