# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import subprocess, sys
def p(t, line, extra=''):
    return f'<w:p><w:pPr>{extra}<w:spacing w:before="0" w:after="0" w:line="{int(line*20)}" w:lineRule="exact"/></w:pPr><w:r><w:t>{t}</w:t></w:r></w:p>'
fill=''.join(p(f'Line {i}', 20) for i in range(31))
def bdr(space, sz): return f'<w:pBdr><w:bottom w:val="single" w:sz="{sz}" w:space="{space}" w:color="auto"/></w:pBdr>'
V={
 'b1': p('Bordered', 26, bdr(1,6)),
 'b2': p('Bordered', 26, bdr(4,6)),
 'b3': p('Bordered', 27.5, bdr(1,6)),
 'b4': p('Bordered', 27.5),
 'b5': p('Bordered', 27.5, bdr(1,6)) + p('Grouped', 20, bdr(1,6)),
 'b6': p('Bordered', 26, bdr(1,24)),
}
for k,v in V.items():
    body = fill + v + p('After', 20)
    subprocess.run([sys.executable, '/Users/arthrod/temp/T/jubarte-loop/mkdocx.py', f'src/{k}.docx', body, '--compat', '15'], check=True)