# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import re,subprocess,collections,sys
pdf=sys.argv[1]; res=collections.defaultdict(list); prev=None
for p in range(1,20):
    out=subprocess.run(['python3','/tmp/conejo/chars.py',pdf,str(p),'0','900'],capture_output=True,text=True).stdout
    if not out.strip() or out==prev: break
    prev=out
    for l in out.splitlines():
        m=re.match(r'(\S+) (\S+) y([\d.]+) (.*)',l)
        if not m or m.group(2)!='12': continue
        r=sorted((float(x),c) for c,x in re.findall(r'(&#x[0-9a-f]+;|\S| )@([\d.]+)',m.group(4)))
        adv=[round(r[i+1][0]-x,3) for i,(x,c) in enumerate(r[:-1]) if c==' ']
        if len(adv)>5: res[m.group(1)].append(min(adv))
for f,v in res.items(): print(f, 'normal',max(v),'floor',min(v), 'ratio',round(min(v)/max(v),3))