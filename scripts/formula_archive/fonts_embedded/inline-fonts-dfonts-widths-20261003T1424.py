# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import fitz,os
d="/Applications/Microsoft Word.app/Contents/Resources/DFonts/"
for f in ["Calibri.ttf","times.ttf","arial.ttf","tahoma.ttf","verdana.ttf","georgia.ttf","Cambria.ttc"]:
    p=d+f
    if not os.path.exists(p): print(f,"missing"); continue
    try:
        fo=fitz.Font(fontfile=p); s=fo.text_length(" ",fontsize=12); print(f, "space@12 =",round(s,3), "em share",round(s/12,3))
    except Exception as e: print(f,"ERR",e)