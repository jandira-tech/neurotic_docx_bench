"""Run the repository Word compare driver on its failed fixtures, with two explicit
operational workarounds: a 2s post-open readiness delay and fresh PDF export from
that same still-open comparison object. This changes no input or compare option.
"""
from pathlib import Path
import sys,hashlib,json,csv,shutil
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
import word_redline as m
import pymupdf
OUT=Path(__file__).resolve().parent
need=[r for r in csv.DictReader(open(OUT/'comparisons.csv')) if not (OUT/'word_compare/pdf'/f"{r['id']}__vs__{r['id']}.pdf").exists()]
for r in need:
 for group in ['A','B']:
  dest=OUT/'word_retry_inline'/group/f"{r['id']}.docx";dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(OUT/'word_compare'/group/dest.name,dest)
base=m._COMPARE_BATCH
assert base.count('open POSIX file baseP')==1
assert base.count('save as cmpDoc file name outP file format format document')==1
patched=base.replace('open POSIX file baseP','open POSIX file baseP\n                delay 2')
patched=patched.replace('save as cmpDoc file name outP file format format document','save as cmpDoc file name outP file format format document\n                set pdfP to (text 1 thru -6 of outP) & ".pdf"\n                save as cmpDoc file name pdfP file format format PDF')
m._COMPARE_BATCH=patched;m._COMPARE_BATCH_KEEP_OPEN=m._keep_open(patched)
original=m.run_batch_with_resume
calls=[]
def driver(script,rows,*args,**kwargs):
 label=kwargs.get('label','');calls.append({'label':label,'n':len(rows),'script_sha256':hashlib.sha256(script.encode()).hexdigest()})
 if label==' pdf':
  ready={};missing=[]
  for row in rows:
   pdf=Path(row[2])
   try:
    with pymupdf.open(pdf) as d:assert d.page_count>0
    ready[row[0]]=(True,'fresh PDF exported from live Word comparison object')
   except Exception:missing.append(row)
  if missing:ready.update(original(script,missing,*args,**kwargs))
  return ready
 return original(script,rows,*args,**kwargs)
m.run_batch_with_resume=driver
(OUT/'word_retry_inline').mkdir(exist_ok=True)
(OUT/'word_retry_inline/script.applescript').write_text(patched)
(OUT/'word_retry_inline/manifest.json').write_text(json.dumps(need,indent=2)+'\n')
try:
 m.app(['--a',str(OUT/'word_retry_inline/A'),'--b',str(OUT/'word_retry_inline/B'),'--out',str(OUT/'word_retry_inline/pdf'),'--docx-out',str(OUT/'word_retry_inline/docx'),'--emit','both','--do-not-close','--log',str(OUT/'word_retry_inline/driver.log')])
finally:
 (OUT/'word_retry_inline/provenance.json').write_text(json.dumps({'input_files_unchanged':True,'compare_options_unchanged':True,'readiness_delay_seconds':2,'pdf_export_from_same_live_comparison':True,'calls':calls,'sha256':hashlib.sha256(patched.encode()).hexdigest()},indent=2)+'\n')
