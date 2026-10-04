# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
exec(open('mk.py').read().split("for compat in")[0])
import zipfile
def mk2(path, body, compat_xml, extra=''):
    mk(path, body, None)
    z=zipfile.ZipFile(path,'a')
    # rewrite settings: zipfile can't replace; rebuild
    z.close()
    zi=zipfile.ZipFile(path); items={n:zi.read(n) for n in zi.namelist()}; zi.close()
    items['word/settings.xml']=f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings {W}>{extra}<w:compat>{compat_xml}</w:compat></w:settings>'.encode()
    z=zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED)
    for n in ['[Content_Types].xml']+[n for n in items if n!='[Content_Types].xml']: z.writestr(n,items[n])
    z.close()
B=body(False)
ALL='<w:spaceForUL/><w:balanceSingleByteDoubleByteWidth/><w:doNotLeaveBackslashAlone/><w:ulTrailSpace/><w:doNotExpandShiftReturn/><w:adjustLineHeightInTable/><w:useFELayout/>'
import os; os.makedirs('src3',exist_ok=True)
mk2('src3/f_all.docx',B,ALL)
mk2('src3/f_fe.docx',B,'<w:useFELayout/>')
mk2('src3/f_bal.docx',B,'<w:balanceSingleByteDoubleByteWidth/>')
mk2('src3/f_bs.docx',B,'<w:doNotLeaveBackslashAlone/>')
mk2('src3/f_csc.docx',B,'','<w:characterSpacingControl w:val="compressPunctuation"/>')