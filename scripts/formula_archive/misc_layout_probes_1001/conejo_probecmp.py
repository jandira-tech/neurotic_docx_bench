# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import fitz,sys,subprocess,os
def get(path):
    r={}
    for p in fitz.open(path):
        for b in p.get_text('dict')['blocks']:
            for l in b.get('lines',[]):
                for s in l['spans']:
                    t=s['text'].strip()
                    if t.startswith('P') and t[1:3].isdigit(): r[int(t[1:3])]=s['font']
    return r
bad=0;tot=0
for d,doc,lab in [('my5','a_n1','names_a.txt'),('my5','b_n3','names_b.txt'),('my6','a_bare','labels.txt'),('my6','b_1fef','labels.txt'),('my7','a_fwd','labels.txt'),('my7','b_rev','labels.txt')]:
    os.makedirs(f'{d}/jub2',exist_ok=True)
    subprocess.run(['/Users/arthrod/temp/T/jubarte-redlines/target/release/jubarte','convert',f'{d}/src/{doc}.docx','-o',f'{d}/jub2/{doc}.pdf','--revisions','word','--force'],capture_output=True)
    L=open(f'{d}/{lab}').read().split('\n'); w,j=get(f'{d}/word/{doc}.pdf'),get(f'{d}/jub2/{doc}.pdf')
    for i,n in enumerate(L):
        tot+=1
        if w.get(i)!=j.get(i): bad+=1; print(f'{d}/{doc} {n:26} W={w.get(i)} J={j.get(i)}')
print('mismatch',bad,'of',tot)