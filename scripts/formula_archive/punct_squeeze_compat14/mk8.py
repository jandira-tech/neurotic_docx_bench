# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
exec(open('mk3.py').read().split("cx='<w:compat")[0])
import os
os.makedirs('src11',exist_ok=True)
CSC='<w:characterSpacingControl w:val="compressPunctuation"/>'
B=sq('left')
BAL='<w:balanceSingleByteDoubleByteWidth/>'
for lang in ['zh-CN','zh-TW','ja-JP','ko-KR','en-US']:
    mk2(f'src11/b_{lang}.docx',B,BAL,CSC+f'<w:themeFontLang w:val="en-US" w:eastAsia="{lang}"/>')
mk2('src11/b_runzh.docx',B.replace('<w:sz w:val="24"/>','<w:sz w:val="24"/><w:lang w:val="en-US" w:eastAsia="zh-CN"/>'),BAL,CSC)
mk2('src11/n_zh_nobal.docx',B,'',CSC+'<w:themeFontLang w:val="en-US" w:eastAsia="zh-CN"/>')
mk2('src11/d_zh_bal_dnc.docx',B,BAL,'<w:characterSpacingControl w:val="doNotCompress"/><w:themeFontLang w:val="en-US" w:eastAsia="zh-CN"/>')