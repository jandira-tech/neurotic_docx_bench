# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""lineagree.py BIN K stems... : share of Word text lines found verbatim in ours (Latin docs only)."""
import sys,subprocess,os,re
binp,k,*stems=sys.argv[1:]
G='/Users/arthrod/temp/T/neurotic_docx_bench/grok_run'
tot=hit=0
def lines(pdf):
    t=subprocess.run(['pdftotext',pdf,'-'],capture_output=True,text=True).stdout
    return [re.sub(r'\s+',' ',l).strip() for l in t.splitlines() if len(l.strip())>15]
for s in stems:
    env=dict(os.environ,JSQ=k)
    subprocess.run([binp,'convert',f'{G}/fixtures_500/{s}.docx','-o','/tmp/la.pdf','--force'],env=env,capture_output=True)
    w=lines(f'{G}/fixtures_500_pdf/{s}.pdf'); o=set(lines('/tmp/la.pdf'))
    if not w: continue
    # skip docs whose extraction is garbled (non-WinAnsi): require overlap at k baseline
    tot+=len(w); hit+=sum(1 for l in w if l in o)
print(k,hit,tot,round(hit/max(tot,1),4))
