# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile
def zedit(src, dst, edits):
    zin=zipfile.ZipFile(src); out=zipfile.ZipFile(dst,'w',zipfile.ZIP_DEFLATED)
    for it in zin.infolist():
        d=zin.read(it.filename)
        if it.filename in edits:
            s=d.decode('utf8'); t=edits[it.filename](s); assert t!=s,(dst,it.filename); d=t.encode('utf8')
        out.writestr(it.filename,d)
    out.close()