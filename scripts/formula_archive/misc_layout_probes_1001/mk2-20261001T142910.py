# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
os.makedirs('src4',exist_ok=True)
for v in ['doNotCompress','compressPunctuation','compressPunctuationAndJapaneseKana']:
    mk2(f'src4/g_{v}.docx',B,'',f'<w:characterSpacingControl w:val="{v}"/>')
mk2('src4/g_cpk_split.docx',body(True),'','<w:characterSpacingControl w:val="compressPunctuation"/>')
mk2('src4/g_cp_kara.docx',body(True,('-Karaman-','Kepenekci,')),'','<w:characterSpacingControl w:val="compressPunctuation"/>')