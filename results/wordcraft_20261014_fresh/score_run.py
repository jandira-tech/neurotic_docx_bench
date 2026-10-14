from pathlib import Path
import csv,json,time,tempfile,hashlib,sys,os
# Scoring runs on Apple-silicon MPS (the torch port of the scorer kernels, tests/test_kernels.py);
# BENCH_DEVICE=cpu is an explicit override. Every row records its backend; early NumPy rows are kept.
os.environ.setdefault('BENCH_DEVICE','mps')
from concurrent.futures import ProcessPoolExecutor,as_completed
import pymupdf
from neurotic_docx_bench.pipeline import score_pdf_pair
from neurotic_docx_bench.content_cache import scorer_fingerprint
from neurotic_docx_bench import kernels
OUT=Path(__file__).resolve().parent

def one(task):
 ident,oracle,candidate=task
 with tempfile.TemporaryDirectory(prefix='wordcraft-score-') as tmp:
  row=score_pdf_pair(Path(oracle),Path(candidate),Path(tmp),dpi=144,key=ident,cache=None,renderer_id='word-16.115' if 'compare' in candidate else 'oracle:microsoft_word-16.115')
 # each document's rasters are deleted before returning
 row['scorer_backend']=kernels.backend_id()
 row['oracle_sha256']=hashlib.sha256(Path(oracle).read_bytes()).hexdigest();row['candidate_sha256']=hashlib.sha256(Path(candidate).read_bytes()).hexdigest()
 return ident,row

def main():
 phase,tool=sys.argv[1:3];folder=OUT/phase/tool;dest=folder/'scores.json';checkpoint=folder/'scores.checkpoint.jsonl';rows={};failure={}
 if checkpoint.exists():
  for line in checkpoint.read_text().splitlines():
   if line.endswith('}'):
    v=json.loads(line);rows[v['id']]=v['result']
 # rows from the early pass were scored on NumPy before the switch to MPS; they are kept, not re-scored
 for v in rows.values():v.setdefault('scorer_backend','numpy')
 prefreeze=os.environ.get('PREFREEZE')=='1'
 if prefreeze:
  # Score candidates whose fresh Word oracle already exists, before the 400 are frozen.
  sys.path.insert(0,str(OUT));import build400
  manifest=list(csv.DictReader(open(OUT/'word_400'/f'candidates_{phase}.csv')))
  got={k:v[0][0] for k,v in build400.results(phase).items()}
  if phase=='compare':got.update({k:v[0] for k,v in build400.cohort1_locations().items()})
  manifest=[r for r in manifest if (r['id'] if phase=='compare' else r['stem']) in got]
 else:
  manifest=list(csv.DictReader(open(OUT/('comparisons.csv' if phase=='compare' else 'conversions.csv'))))
  ids={r['id'] if phase=='compare' else r['stem'] for r in manifest}
  # keep only checkpoint rows of the frozen manifest, scored against the very oracle file frozen
  rows={k:v for k,v in rows.items() if k in ids and v.get('oracle_sha256')==hashlib.sha256((OUT/phase/'oracle'/f'{k}.pdf').read_bytes()).hexdigest()}
 tasks=[]
 for r in manifest:
  ident=r['id'] if phase=='compare' else r['stem'];oracle=Path(got[ident]) if prefreeze else OUT/phase/'oracle'/f'{ident}.pdf';candidate=folder/'pdf'/f'{ident}.pdf'
  if ident in rows:continue
  if not oracle.exists():failure[ident]={'stage':'oracle','error':'missing Word oracle'};continue
  if not candidate.exists():
   if not prefreeze:failure[ident]={'stage':'tool_output','error':'missing candidate PDF'}
   continue
  try:
   with pymupdf.open(candidate) as doc:assert doc.page_count>0
  except Exception as ex:failure[ident]={'stage':'tool_output','error':str(ex)};continue
  tasks.append((ident,str(oracle),str(candidate)))
 t=time.monotonic();print(phase,tool,'scoring',len(tasks),'remaining,',len(rows),'complete;',len(failure),'missing',flush=True)
 with ProcessPoolExecutor(max_workers=(jobs:=int(os.environ.get('SCORE_WORKERS','6'))),initializer=kernels.worker_init,initargs=(jobs,)) as pool:
  futures={pool.submit(one,task):task[0] for task in tasks}
  for i,f in enumerate(as_completed(futures),1):
   ident=futures[f]
   try:
    ident,row=f.result();rows[ident]=row
    with checkpoint.open('a') as out:out.write(json.dumps({'id':ident,'result':row},default=str)+'\n')
   except Exception as ex:failure[ident]={'stage':'score','error':repr(ex)}
   if i%10==0 or i==len(tasks):print(tool,i,'/',len(tasks),'scored',len(rows),'failures',len(failure),f'{time.monotonic()-t:.0f}s',flush=True)
 report={'tool':tool,'phase':phase,'dpi':144,'scorer_fingerprint':scorer_fingerprint(),'scorer_backend':kernels.backend_id(),'scorer_backend_rows':dict(__import__('collections').Counter(v['scorer_backend'] for v in rows.values())),'requested':len(manifest),'scored':len(rows),'rows':rows,'failures':failure,'rasters_deleted':True}
 if prefreeze:print('prefreeze scoring pass done:',len(rows),'checkpointed',flush=True);return
 dest.write_text(json.dumps(report,indent=1,default=str)+'\n');print('saved',dest,flush=True)
if __name__=='__main__':main()
