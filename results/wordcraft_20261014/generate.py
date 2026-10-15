from pathlib import Path
import csv,json,subprocess,time,zipfile,hashlib,shutil,sys
from lxml import etree as E
import pymupdf
ROOT=Path.cwd();OUT=ROOT/'results/wordcraft_20261014';WORD=ROOT/'corpus/word';WC='/Users/arthrod/.local/bin/wordcraft-cli';JUB=str(ROOT/'src/neurotic_docx_bench/utils/jubarte/jubarte-rust/redline')
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,dest,kind,ident,tool,reused=False):
 t=time.perf_counter_ns();err='';rc=0
 try:
  r=subprocess.run(cmd,capture_output=True,text=True,timeout=120);rc=r.returncode;err=(r.stderr+r.stdout)[-6000:]
 except subprocess.TimeoutExpired as ex:rc=124;err=str(ex)
 elapsed=(time.perf_counter_ns()-t)/1e6
 row={'id':ident,'task':kind,'tool':tool,'command':cmd,'elapsed_ms':elapsed,'returncode':rc,'reused':reused,'stderr_stdout':err,'output':str(dest)}
 if dest.exists():
  try:
   if kind=='compare':
    with zipfile.ZipFile(dest) as z:
     assert z.testzip() is None;root=E.fromstring(z.read('word/document.xml'));row['revisions']={tag:len(root.findall('.//w:'+tag,NS)) for tag in ['ins','del','rPrChange','pPrChange','tblPrChange','trPrChange','tcPrChange']}
   else:
    with pymupdf.open(dest) as pdf:row['pages']=pdf.page_count;assert pdf.page_count>0
   row['output_sha256']=sha(dest)
  except Exception as ex:row['validation_error']=str(ex);rc=1
 else:rc=rc or 1;row['validation_error']='no output'
 row['ok']=rc==0
 with (OUT/'operations.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
 return row

def main():
 phase=sys.argv[1];rows=list(csv.DictReader(open(OUT/('comparisons.csv' if phase=='compare' else 'conversions.csv'))))
 tools=['wordcraft','jubarte-0.11.0','docxodus'] if phase=='compare' else ['wordcraft']
 site=ROOT/'results/site_1011';sitepairs={r['key']:r for r in csv.DictReader(open(site/'docxodus/manifest.csv'))}
 for tool in tools:
  folder=OUT/phase/tool/('docx' if phase=='compare' else 'pdf');folder.mkdir(parents=True,exist_ok=True)
  # Three warmups, excluded from measurement, before each fresh CLI lane.
  if tool!='docxodus':
   for i in range(3):
    if phase=='compare':
     base=WORD/(rows[0]['base']+'.docx');nxt=WORD/(rows[0]['next']+'.docx');dest=OUT/'smoke'/f'warmup-{tool}.docx'
     cmd=[WC,'run','--file',str(base),'--cmd','review.compare='+json.dumps({'path':str(nxt),'author':'Redline','showIn':'original','level':'word','formatting':True,'caseChanges':True,'whiteSpace':True}),'--save',str(dest)] if tool=='wordcraft' else [JUB,str(base),str(nxt),'-o',str(dest),'--force','--quiet']
    else:
     dest=OUT/'smoke'/f'warmup-{tool}.pdf';cmd=[WC,'convert',str(ROOT/rows[0]['docx']),str(dest),'--markup']
    subprocess.run(cmd,capture_output=True,timeout=120)
  for i,row in enumerate(rows,1):
   ident=row['id'] if phase=='compare' else row['stem'];dest=folder/(ident+('.docx' if phase=='compare' else '.pdf'))
   if dest.exists():continue
   reused=False
   if phase=='compare':
    base=WORD/(row['base']+'.docx');nxt=WORD/(row['next']+'.docx')
    assert sha(base)==row['base_sha256'] and sha(nxt)==row['next_sha256']
    if tool=='wordcraft':cmd=[WC,'run','--file',str(base),'--cmd','review.compare='+json.dumps({'path':str(nxt),'author':'Redline','showIn':'original','level':'word','formatting':True,'caseChanges':True,'whiteSpace':True}),'--save',str(dest)]
    elif tool=='jubarte-0.11.0':cmd=[JUB,str(base),str(nxt),'-o',str(dest),'--force','--quiet']
    else:
     old=site/'docxodus/docx'/f'{ident}_docxodus.docx'
     sp=sitepairs.get(ident)
     reusable=sp is not None and sp['base']==row['base'] and sp['next']==row['next'] and old.exists() and sha(site/'word_compare/A'/f'{ident}.docx')==row['base_sha256'] and sha(site/'word_compare/B'/f'{ident}.docx')==row['next_sha256']
     if reusable:
      shutil.copy2(old,dest);cmd=[sys.executable,'-c','pass'];reused=True
      pdf=site/'word_render/docxodus'/f'{ident}_docxodus.pdf'
      if pdf.exists():
       pdfdest=OUT/phase/tool/'pdf'/f'{ident}.pdf';pdfdest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(pdf,pdfdest)
     else:cmd=['node','--import','tsx','scripts/_site1011_docxodus_one.ts',str(base),str(nxt),str(dest)]
   else:
    source=ROOT/row['docx'];assert sha(source)==row['docx_sha256'];cmd=[WC,'convert',str(source),str(dest),'--markup']
   result=run(cmd,dest,phase,ident,tool,reused)
   if i%10==0 or not result['ok']:print(tool,phase,i,'/',len(rows),'ok' if result['ok'] else 'FAILED',f"{result['elapsed_ms']:.0f} ms",flush=True)
if __name__=='__main__':main()
