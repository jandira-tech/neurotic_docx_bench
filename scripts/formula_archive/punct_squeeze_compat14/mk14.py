# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
exec(open('mk3.py').read().split("cx='<w:compat")[0])
import os,re
os.makedirs('src14',exist_ok=True)
cx='<w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="14"/>'
CSC='<w:characterSpacingControl w:val="compressPunctuation"/>'
DNC='<w:characterSpacingControl w:val="doNotCompress"/>'
base=sq('left')
old='<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="24"/>'
cal=base.replace(old,'<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="24"/>')
n=[0]
def wrap(m):
    n[0]+=1; return f'<w:ins w:id="{n[0]}" w:author="A" w:date="2026-01-01T00:00:00Z">{m.group(0)}</w:ins>'
ins=re.sub(r'<w:r>.*?</w:r>',wrap,base)
mk2('src14/e_calibri_cp.docx',cal,cx,CSC); mk2('src14/e_calibri_dnc.docx',cal,cx,DNC)
mk2('src14/h_ins_cp.docx',ins,cx,CSC); mk2('src14/h_ins_dnc.docx',ins,cx,DNC)