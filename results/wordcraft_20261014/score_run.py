from pathlib import Path
import csv,json,time,tempfile,hashlib,sys,os
from concurrent.futures import ProcessPoolExecutor,as_completed
import pymupdf
from neurotic_docx_bench.pipeline import score_pdf_pair
from neurotic_docx_bench.content_cache import scorer_fingerprint
OUT=Path.cwd()/'results/wordcraft_20261014'

def one(task):
 ident,oracle,candidate=task
 with tempfile.TemporaryDirectory(prefix='wordcraft-score-') as tmp:
  row=score_pdf_pair(Path(oracle),Path(candidate),Path(tmp),dpi=144,key=ident,cache=None,renderer_id='word-16.115' if 'compare' in candidate else 'wordcraft-0.6.1')
 # each document's rasters are deleted before returning
 row['oracle_sha256']=hashlib.sha256(Path(oracle).read_bytes()).hexdigest();row['candidate_sha256']=hashlib.sha256(Path(candidate).read_bytes()).hexdigest()
 return ident,row

def main():
 phase,tool=sys.argv[1:3];folder=OUT/phase/tool;dest=folder/'scores.json';checkpoint=folder/'scores.checkpoint.jsonl';rows={};failure={}
 if checkpoint.exists():
  for line in checkpoint.read_text().splitlines():
   if line.endswith('}'):
    v=json.loads(line);rows[v['id']]=v['result']
 manifest=list(csv.DictReader(open(OUT/('comparisons.csv' if phase=='compare' else 'conversions.csv'))));tasks=[]
 for r in manifest:
  ident=r['id'] if phase=='compare' else r['stem'];oracle=OUT/phase/'oracle'/f'{ident}.pdf';candidate=folder/'pdf'/f'{ident}.pdf'
  if ident in rows:continue
  if not oracle.exists():failure[ident]={'stage':'oracle','error':'missing Word oracle'};continue
  if not candidate.exists():failure[ident]={'stage':'tool_output','error':'missing candidate PDF'};continue
  try:
   with pymupdf.open(candidate) as doc:assert doc.page_count>0
  except Exception as ex:failure[ident]={'stage':'tool_output','error':str(ex)};continue
  tasks.append((ident,str(oracle),str(candidate)))
 t=time.monotonic();print(phase,tool,'scoring',len(tasks),'remaining,',len(rows),'complete;',len(failure),'missing',flush=True)
 with ProcessPoolExecutor(max_workers=4) as pool:
  futures={pool.submit(one,task):task[0] for task in tasks}
  for i,f in enumerate(as_completed(futures),1):
   ident=futures[f]
   try:
    ident,row=f.result();rows[ident]=row
    with checkpoint.open('a') as out:out.write(json.dumps({'id':ident,'result':row},default=str)+'\n')
   except Exception as ex:failure[ident]={'stage':'score','error':repr(ex)}
   if i%10==0 or i==len(tasks):print(tool,i,'/',len(tasks),'scored',len(rows),'failures',len(failure),f'{time.monotonic()-t:.0f}s',flush=True)
 report={'tool':tool,'phase':phase,'dpi':144,'scorer_fingerprint':scorer_fingerprint(),'scorer_backend':'numpy','requested':200,'scored':len(rows),'rows':rows,'failures':failure,'rasters_deleted':True}
 dest.write_text(json.dumps(report,indent=1,default=str)+'\n');print('saved',dest,flush=True)
if __name__=='__main__':main()
