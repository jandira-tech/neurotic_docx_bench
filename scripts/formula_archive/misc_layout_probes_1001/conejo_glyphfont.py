# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import subprocess,sys,re,html
def chars(pdf):
    out=subprocess.run(['mutool','draw','-q','-F','stext','-o','-',pdf],capture_output=True,text=True).stdout
    font=None; res=[]
    for line in out.splitlines():
        m=re.search(r'<font name="([^"]+)"',line)
        if m: font=m.group(1)
        m=re.search(r'<char c="([^"]*)" x="([\d.]+)"',line)
        if m: res.append((html.unescape(m.group(1)),font.split('-')[0][:8],round(float(m.group(2)),2)))
    return res
for n in sys.argv[2:]:
    w=chars(f'{sys.argv[1]}_w/{n}.pdf'); j=chars(f'{sys.argv[1]}_j/{n}.pdf')
    print('##',n)
    print(' W',' '.join(f'{c}:{f}@{x}' for c,f,x in w if c.strip() or True)[:300])
    print(' J',' '.join(f'{c}:{f}@{x}' for c,f,x in j)[:300])