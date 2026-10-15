"""folio-cli 0.5.1 `compare -o` vs the bench's folio-core 0.60.0 lane vs Word 16.115, on 3 complex pairs.
Structural only (no render): revision counts, normalized part equality, and accept-all / reject-all
text fidelity against the next / base documents (word-level difflib ratio)."""
import csv,zipfile,re,difflib,sys,json
from pathlib import Path
from lxml import etree
P=Path(__file__).resolve().parent;OUT=P.parent;C=OUT.parents[1]/'corpus/word'
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
rows={r['id']:r for r in csv.DictReader(open(OUT/'comparisons.csv'))}
def doc(p):return etree.fromstring(zipfile.ZipFile(p).read('word/document.xml'))
def counts(t):
 c={k:len(t.findall('.//'+W+k)) for k in ('ins','del','moveFrom','moveTo','rPrChange','pPrChange','tblPrChange','trPrChange','tcPrChange','sectPrChange')}
 return c
def text(t,mode):
 """mode: plain | accept | reject — paragraph text, words joined."""
 drop={'accept':(W+'del',W+'moveFrom'),'reject':(W+'ins',W+'moveTo'),'plain':()}[mode]
 out=[]
 for el in t.iter(W+'t',W+'delText',W+'tab',W+'p'):
  if any(a.tag in drop for a in el.iterancestors()):continue
  if el.tag==W+'p':
   # a paragraph whose mark is deleted (accept) / inserted (reject) merges with the next
   rpr=el.find(W+'pPr/'+W+'rPr');mark=None if rpr is None else (rpr.find(W+'del') if mode=='accept' else rpr.find(W+'ins') if mode=='reject' else None)
   if mark is None:out.append('\n')
  elif el.tag==W+'tab':out.append(' ')
  else:out.append(el.text or '')
 return ''.join(out).split()
def ratio(a,b):return difflib.SequenceMatcher(None,a,b,autojunk=False).ratio()
def norm(p):
 z=zipfile.ZipFile(p);d={}
 for n in sorted(z.namelist()):
  b=z.read(n)
  if n.endswith('.xml') or n.endswith('.rels'):b=re.sub(rb'w:date="[^"]*"|w:rsid\w*="[^"]*"|<dcterms:modified[^<]*</dcterms:modified>|<dcterms:created[^<]*</dcterms:created>',b'',b)
  d[n]=b
 return d
res=[]
for id in sys.argv[1:]:
 r=rows[id];base=doc(C/(r['base']+'.docx'));nxt=doc(C/(r['next']+'.docx'))
 B,N=text(base,'plain'),text(nxt,'plain')
 cands={'word-16.115':OUT/'compare/oracle_docx'/f'{id}.docx','folio-cli-0.5.1':P/'cli'/f'{id}.docx','folio-core-0.60.0 (rerun)':P/'core'/f'{id}.docx','folio-core-0.60.0 (bench lane)':OUT/'compare/folio-0.60.0/docx'/f'{id}.docx'}
 nc,nl=norm(cands['folio-cli-0.5.1']),norm(cands['folio-core-0.60.0 (bench lane)'])
 diffparts=[n for n in set(nc)|set(nl) if nc.get(n)!=nl.get(n)]
 print(f'\n## {id}  base words={len(B)} next words={len(N)}  cli vs lane differing parts (after dropping dates/rsids): {diffparts or "none"}')
 for name,p in cands.items():
  t=doc(p);c=counts(t);A,R=text(t,'accept'),text(t,'reject')
  row={'id':id,'tool':name,'ins':c['ins'],'del':c['del'],'move':c['moveFrom']+c['moveTo'],'fmt':sum(v for k,v in c.items() if 'Change' in k),'accept_vs_next':round(ratio(A,N),4),'reject_vs_base':round(ratio(R,B),4),'bytes':p.stat().st_size}
  res.append(row);print(row)
json.dump(res,open(P/'analysis.json','w'),indent=1)
