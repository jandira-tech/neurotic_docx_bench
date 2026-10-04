# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""docxedit.py in.docx out.docx PYEXPR [part] : rewrite a part (default word/document.xml) with a python lambda s: ... (re available)"""
import sys,zipfile,re
src,dst,expr=sys.argv[1:4]; f=eval(expr); part=sys.argv[4] if len(sys.argv)>4 else 'word/document.xml'
zi=zipfile.ZipFile(src); zo=zipfile.ZipFile(dst,'w',zipfile.ZIP_DEFLATED)
for it in zi.infolist():
    b=zi.read(it.filename)
    if it.filename==part:
        old=b.decode(); new=f(old)
        if new==old: sys.exit('docxedit: the edit changed nothing')
        b=new.encode()
    zo.writestr(it,b)
zo.close()
