# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import subprocess, sys
T='<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="24"/></w:rPr>'
def tp(t): return f'<w:p><w:r>{T}<w:t>{t}</w:t></w:r></w:p>'
def rect(w,h,extra=''): return ('<w:pict xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">'
   f'<v:rect id="Horizontal Line 1" style="width:{w}pt;height:{h}pt;visibility:visible;mso-position-horizontal:absolute;mso-position-horizontal-relative:char;mso-position-vertical:absolute;mso-position-vertical-relative:line;v-text-anchor:top" filled="f"{extra}/></w:pict>')
V={
 'k1': ('', rect(540,20,' strokeweight="4pt"')),
 'k2': ('', rect(540,20,' stroked="f"')),
 'k3': ('<w:r><w:t>Xgj</w:t></w:r>', rect(200,20)),
 'k4': ('<w:r><w:t>Xgj</w:t></w:r>', rect(200,1.1)),
 'k5': ('', rect(540,6)),
 'k6': ('', rect(540,20,' strokeweight="0.25pt"')),
}
for k,(pre,r) in V.items():
    body = tp('Above Fredericksburg gjpq') + f'<w:p>{pre}<w:r>{r}</w:r><w:r><w:t>Yq</w:t></w:r></w:p>' + tp('Below Experienced gjpq') + tp('Second line after')
    subprocess.run([sys.executable, '/Users/arthrod/temp/T/jubarte-loop/mkdocx.py', f'src2/{k}.docx', body, 'styles.xml', '--compat', '15'], check=True)