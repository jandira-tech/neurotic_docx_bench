from pathlib import Path
import json,csv,subprocess,time,hashlib,zipfile,sys,tempfile,math,statistics,os
from lxml import etree as E
import pymupdf
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];TOOLS=json.load(open(OUT/'tools.json'));WC=TOOLS['wordcraft-cli']['path'];WORD=ROOT/'corpus/word'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def command(phase,tool,row,dest):
 if phase=='compare':
  base=WORD/(row['base']+'.docx');nxt=WORD/(row['next']+'.docx');assert sha(base)==row['base_sha256'] and sha(nxt)==row['next_sha256']
  if tool in ('wordcraft','wordcraft-0.7.0'):return [WC if tool=='wordcraft' else TOOLS[tool]['path'],'run','--file',str(base),'--cmd','review.compare='+json.dumps({'path':str(nxt),'author':'Redline','showIn':'original','level':'word','formatting':True,'caseChanges':True,'whiteSpace':True}),'--save',str(dest)]
  if tool.startswith('jubarte-'):return [TOOLS[tool]['path'],str(base),str(nxt),'-o',str(dest),'--force','--quiet']
  if tool=='docxodus-12.6.5':return ['node','--import','tsx','scripts/_site1011_docxodus_one.ts',str(base),str(nxt),str(dest)]
  return NEW_COMPARE[tool](base,nxt,dest)
 source=ROOT/row['docx'];assert sha(source)==row['docx_sha256']
 if tool in ('wordcraft','wordcraft-0.7.0'):return [WC if tool=='wordcraft' else TOOLS[tool]['path'],'convert',str(source),str(dest),'--markup']
 if tool in NEW_CONVERT:
  from neurotic_docx_bench.docx_to_pdf import convert_command
  return convert_command(NEW_CONVERT[tool],source,dest,binary=Path(TOOLS[tool]['path']))
 if tool.startswith('jubarte-'):return [TOOLS[tool]['path'],'convert',str(source),'-o',str(dest),'--force','--revisions','word']
 from neurotic_docx_bench.render.soffice import find_soffice
 return [str(find_soffice()),'-env:UserInstallation=file://'+str(OUT/'lo_profiles'/dest.stem),'--headless','--norestore','--nofirststartwizard','--convert-to','pdf','--outdir',str(dest.parent),str(source)]

# Tools added after the first eight lanes (2026-10-14, newest releases): the top three non-jubarte
# tools of every past results table, plus wordcraft 0.7.0 and docxodus 13.0.0. Each runs through the
# bench's own adapter for that tool; versions come from this folder's bin/ installs (tools.json).
ONE_TS=str(OUT/'one_redline.ts');ENG=ROOT/'src/neurotic_docx_bench/utils'
NEW_COMPARE={
 'docxodus-13.0.0':lambda b,n,d:['node','--import','tsx',ONE_TS,'docxodus',str(ENG/'docxodus'),str(b),str(n),str(d)],
 'folio-0.60.0':lambda b,n,d:['node','--import','tsx',ONE_TS,'folio','',str(b),str(n),str(d)],
 'stemma-0.5.0':lambda b,n,d:['node','--import','tsx',ONE_TS,'stemma',str(ENG/'stemma'),str(b),str(n),str(d)],
 'stemma-0.6.0':lambda b,n,d:['node','--import','tsx',ONE_TS,'stemma',str(OUT/'bin/cargo/stemma-cli-0.6.0/bin'),str(b),str(n),str(d)],
 'superdoc-2.20.0':lambda b,n,d:[str(OUT/'bin/superdoc-venv/bin/python'),str(OUT/'superdoc_one.py'),str(b),str(n),str(d)],
}
NEW_ENV={'DOCXODUS_NODE_MODULES':str(OUT/'bin/npm/docxodus-13.0.0/node_modules'),'FOLIO_MODULE_ROOT':str(OUT/'bin/npm/folio-0.60.0/node_modules')}
NEW_CONVERT={'office2pdf-0.8.1':'office2pdf','pdfitdown-4.2.0':'pdfitdown','rdocx-0.16.0':'rdocx','docxide-pdf-0.18.4':'docxide-pdf','libreoffice_convert_rust-0.1.0':'libreoffice_convert_rust','pymupdf-pro-1.28.2':'pymupdf-pro'}
# PyMuPDF Pro runs unlicensed (first 3 pages only), so it is measured only on the conversions whose
# fresh Word oracle has at most 3 pages; the report scores it on that subset alone.
LE3_ONLY={'pymupdf-pro-1.28.2'}
def le3(row):
 with pymupdf.open(OUT/'convert'/'oracle'/(row['stem']+'.pdf')) as d:return d.page_count<=3

def invoke(cmd,output,phase,tool,ident,save_as=None):
 t=time.perf_counter_ns();rc=0;error=''
 try:
  p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=120 if phase=='compare' else 180,env={**os.environ,**NEW_ENV});rc=p.returncode;error=(p.stderr+p.stdout)[-6000:]
 except subprocess.TimeoutExpired as ex:rc=124;error=str(ex)
 elapsed=(time.perf_counter_ns()-t)/1e6
 row={'id':ident,'task':phase,'tool':tool,'prefreeze':os.environ.get('PREFREEZE')=='1','word_batch_concurrent':bool(subprocess.run(['pgrep','-f','word_(pdf|redline)\\.py'],capture_output=True).stdout.strip()),'command':cmd,'elapsed_ms':elapsed,'returncode':rc,'stderr_stdout':error,'reused':False,'output':str(output),'ok':rc==0 and output.exists()}
 if row['ok']:
  try:
   if phase=='compare':
    with zipfile.ZipFile(output) as z:assert z.testzip() is None;root=E.fromstring(z.read('word/document.xml'));row['revisions']={tag:len(root.findall('.//w:'+tag,NS)) for tag in ['ins','del','rPrChange','pPrChange','tblPrChange','trPrChange','tcPrChange']}
   else:
    with pymupdf.open(output) as pdf:assert pdf.page_count>0;row['pages']=pdf.page_count
   row['output_sha256']=sha(output)
   if save_as is not None:
    output.replace(save_as);row['output']=str(save_as)
  except Exception as ex:row['ok']=False;row['validation_error']=str(ex)
 else:row['validation_error']='nonzero exit or missing output'
 with (OUT/'operations.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
 return row

def main():
 phase=sys.argv[1];tools=sys.argv[2:] or (['wordcraft','jubarte-0.11.0','jubarte-0.12.0','docxodus-12.6.5'] if phase=='compare' else ['wordcraft','jubarte-0.11.0','jubarte-0.12.0','soffice'])
 # PREFREEZE=1: generate for every frozen *candidate* (word_400/candidates_*.csv) while Word
 # oracles are still being made. The freeze rule is fixed and never reads vendor output;
 # candidates that do not make the final 400 are simply not scored.
 prefreeze=os.environ.get('PREFREEZE')=='1'
 if prefreeze:manifest=OUT/'word_400'/('candidates_compare.csv' if phase=='compare' else 'candidates_convert.csv')
 else:
  assert (OUT/'ORACLES_READY.json').exists(), 'Freeze the Word-eligible cohort before vendor generation'
  manifest=OUT/('comparisons.csv' if phase=='compare' else 'conversions.csv')
 allrows=list(csv.DictReader(open(manifest)))
 for tool in tools:
  rows=[r for r in allrows if le3(r)] if tool in LE3_ONLY else allrows
  folder=OUT/phase/tool/('docx' if phase=='compare' else 'pdf');folder.mkdir(parents=True,exist_ok=True);fail=[]
  prior={}
  if (OUT/'operations.jsonl').exists():
   for line in (OUT/'operations.jsonl').read_text().splitlines():
    rec=json.loads(line)
    if rec['task']==phase and rec['tool']==tool:prior[rec['id']]=rec
  # Warm the entire process path three times; do not include those samples.
  with tempfile.TemporaryDirectory(prefix='wordcraft-cli-warmup-') as tmp:
   for i in range(3):
    dest=Path(tmp)/('warmup.docx' if phase=='compare' else 'warmup.pdf');cmd=command(phase,tool,rows[0],dest)
    try:subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=120 if phase=='compare' else 180,env={**os.environ,**NEW_ENV})
    except subprocess.TimeoutExpired:print('Excluded warmup timeout',tool,i,flush=True)
  for i,r in enumerate(rows,1):
   ident=r['id'] if phase=='compare' else r['stem'];dest=folder/(ident+('.docx' if phase=='compare' else '.pdf'))
   if ident in prior:
    rec=prior[ident]
    if rec['ok']:
     assert dest.exists() and sha(dest)==rec['output_sha256'], ('Resumed output hash mismatch',ident)
    else:fail.append({'doc':ident,'stage':'generate','error':rec['stderr_stdout'] or rec.get('validation_error','failure'),'returncode':rec['returncode']})
    continue
   assert not dest.exists(), ('Unrecorded output must not be silently reused',dest)
   cmd=command(phase,tool,r,dest)
   if tool=='soffice':
    # soffice names its PDF after the input stem; preserve the task's state prefix.
    raw=folder/(Path(r['docx']).stem+'.pdf');result=invoke(cmd,raw,phase,tool,ident,save_as=dest)
   else:result=invoke(cmd,dest,phase,tool,ident)
   if not result['ok']:fail.append({'doc':ident,'stage':'generate','error':result['stderr_stdout'] or result.get('validation_error','failure'),'returncode':result['returncode']})
   if i%10==0 or not result['ok']:print(tool,phase,i,'/',len(rows),'ok' if result['ok'] else 'FAILED',f"{result['elapsed_ms']:.0f} ms",flush=True)
  (OUT/phase/tool/'generate_failures.json').write_text(json.dumps(fail,indent=2)+'\n');print(tool,'finished',len(rows)-len(fail),'/',len(rows),flush=True)
if __name__=='__main__':main()
