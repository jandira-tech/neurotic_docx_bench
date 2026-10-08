# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
os.makedirs('src5',exist_ok=True)
for cm in (12,14,15):
    cx=f'<w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="{cm}"/>'
    mk2(f'src5/h{cm}_cp.docx',B,cx,'<w:characterSpacingControl w:val="compressPunctuation"/>')
    mk2(f'src5/h{cm}_dnc.docx',B,cx,'<w:characterSpacingControl w:val="doNotCompress"/>')