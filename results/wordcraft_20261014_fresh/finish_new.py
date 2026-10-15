"""Stage 3: the lanes added on 2026-10-14 (newest releases) on the same frozen 400+400.

Compare lanes: wait for generation, Word-render (same render() and one fresh-session retry as the
original lanes), score on MPS. Convert lanes: wait for generation (the cargo-built converters are
generated here once their builds finish), score. Then the final report and the result stores."""
import subprocess,time,json,os,csv,sys
from finish400 import render,log,sh,OUT,ROOT,PY
import lanes
ids=[r['id'] for r in csv.DictReader(open(OUT/'comparisons.csv'))]
NEW_CMP=[t for t in lanes.COMPARE if t not in ('wordcraft','jubarte-0.11.0','jubarte-0.12.0','docxodus-12.6.5')]
NEW_CNV=[t for t in lanes.CONVERT if t not in ('wordcraft','jubarte-0.11.0','jubarte-0.12.0','soffice')]
CARGO=['office2pdf-0.8.1','pdfitdown-4.2.0','rdocx-0.16.0','docxide-pdf-0.18.4','libreoffice_convert_rust-0.1.0']
def running(kind,t):
 out=subprocess.run(['ps','-axo','command='],capture_output=True,text=True).stdout
 return any(l.startswith(PY) and l.endswith(f'score_run.py {kind} {t}') for l in out.splitlines())
def scorer_count():
 # distinct scorer commands: pool workers can carry the parent's command line
 return len({l.strip() for l in subprocess.run(['ps','-axo','command='],capture_output=True,text=True).stdout.splitlines() if l.startswith(PY) and '/wordcraft_20261014_fresh/score_run.py ' in l})
import threading
queue=[];LOCK=threading.Lock()
def pump_forever():
 while True:
  with LOCK:pump()
  time.sleep(30)
def pump():
 """Start queued scorers, at most two at a time; never blocks the Word renders."""
 while queue and scorer_count()<2:
  kind,t=queue.pop(0)
  if (OUT/kind/t/'scores.json').exists() or running(kind,t):continue
  log('SCORE',kind,t)
  subprocess.Popen([PY,str(OUT/'score_run.py'),kind,t],cwd=ROOT,stdout=open(OUT/f'score_{kind}_{t}.out','a'),stderr=subprocess.STDOUT,env={**os.environ,'SCORE_WORKERS':'3','BENCH_DEVICE':'mps'});time.sleep(5)
def generated(kind,t):return (OUT/kind/t/'generate_failures.json').exists()
def rendered(t):return (OUT/'compare'/t/'render_failures.json').exists()
def main():
 # restartable: a lane is rendered once render_failures.json exists, scored once scores.json exists
 tools=json.loads((OUT/'tools.json').read_text())
 for t in NEW_CNV:
  if generated('convert',t):queue.append(('convert',t))
 for t in NEW_CMP:
  if rendered(t):queue.append(('compare',t))
 threading.Thread(target=pump_forever,daemon=True).start()
 while True:
  todo=[t for t in NEW_CMP if not rendered(t) and generated('compare',t)]
  if todo:
   render(todo[0],ids)
   with LOCK:queue.insert(0,('compare',todo[0]))
   continue
  with LOCK:idle=not queue and scorer_count()==0
  if all(rendered(t) for t in NEW_CMP) and idle:break
  time.sleep(30)
 missing=[(k,t) for k,ts in (('compare',NEW_CMP),('convert',NEW_CNV)) for t in ts if not (OUT/k/t/'scores.json').exists()]
 if missing:log('MISSING SCORES',missing);sys.exit(2)
 log('scores done')
 sh([PY,str(OUT/'report.py'),'--final'],out=OUT/'final_report.out');sh([PY,str(OUT/'persist_fresh.py')],out=OUT/'persist_fresh.out')
 (OUT/'BENCHMARK_EXTENDED_COMPLETE.json').write_text(json.dumps({'completed_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'lanes':lanes.LANES},indent=2)+'\n');log('COMPLETE')
if __name__=='__main__':main()
