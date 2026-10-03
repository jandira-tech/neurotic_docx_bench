# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
exec(open('mk3.py').read().split("cx='<w:compat")[0])
import os
os.makedirs('src12',exist_ok=True)
B=sq('both')
BAL='<w:balanceSingleByteDoubleByteWidth/>'
cx15='<w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/>'
TL='<w:themeFontLang w:val="en-US" w:eastAsia="zh-CN"/>'
mk2('src12/j15_ctrl.docx',B,cx15,'')
mk2('src12/j15_bal_zh.docx',B,BAL+cx15,TL)
mk2('src12/j15_bal_zh_cp.docx',B,BAL+cx15,'<w:characterSpacingControl w:val="compressPunctuation"/>'+TL)
mk2('src12/j15_zh.docx',B,cx15,TL)