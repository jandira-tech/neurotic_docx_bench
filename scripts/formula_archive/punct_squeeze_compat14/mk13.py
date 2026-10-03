# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
exec(open('mk3.py').read().split("cx='<w:compat")[0])
import os
os.makedirs('src13',exist_ok=True)
cx='<w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="14"/>'
CSC='<w:characterSpacingControl w:val="compressPunctuation"/>'
base=sq('left')
old='<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="24"/>'
assert old in base
V={'b_eafont':'<w:rFonts w:ascii="Times New Roman" w:eastAsia="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="24"/>',
   'c_ealang':old+'<w:lang w:val="en-US" w:eastAsia="en-US"/>',
   'd_both':'<w:rFonts w:ascii="Times New Roman" w:eastAsia="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/><w:sz w:val="24"/><w:lang w:val="en-US" w:eastAsia="en-US" w:bidi="ar-SA"/>',
   'e_calibri':'<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="24"/>',
   'f_eafont_simsun':'<w:rFonts w:ascii="Times New Roman" w:eastAsia="SimSun" w:hAnsi="Times New Roman"/><w:sz w:val="24"/>',
   'g_ealang_zh':old+'<w:lang w:val="en-US" w:eastAsia="zh-CN"/>'}
for k,v in V.items(): mk2(f'src13/{k}.docx',base.replace(old,v),cx,CSC)
mk2('src13/a_ctrl.docx',base,cx,CSC)
mk2('src13/z_dnc.docx',base,cx,'<w:characterSpacingControl w:val="doNotCompress"/>')