# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
exec(open('mk3.py').read().split("cx='<w:compat")[0])
import os
os.makedirs('src16',exist_ok=True)
cx='<w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="14"/>'
CSC='<w:characterSpacingControl w:val="compressPunctuation"/>'
def cs(n): return f'<w:compatSetting w:name="{n}" w:uri="http://schemas.microsoft.com/office/word" w:val="1"/>'
B=sq('left')
for n in ['enableOpenTypeFeatures','overrideTableStyleFontSizeAndJustification','doNotFlipMirrorIndents','useWord2013TrackBottomHyphenation']:
    mk2(f'src16/{n}.docx',B,cx+cs(n),CSC)