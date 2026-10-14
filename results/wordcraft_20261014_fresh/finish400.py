"""Stage 2 of the 400+400 run: retries -> freeze -> Word renders of vendor redlines -> scores -> report.

Vendor outputs were generated pre-freeze for every candidate (PREFREEZE=1); the freeze rule never
reads them. Word renders and scores only the frozen rows. Word is driven by the committed drivers
(drivers_ee49054d) through run_word400's exclusive-Word guard.
"""
from pathlib import Path
import subprocess,sys,json,time,csv,shutil,re,os
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];PY=str(ROOT/'.venv/bin/python')
sys.path.insert(0,str(OUT))
from run_word400 import wait_alone,settle,run_chunk,DRIVERS
CMP=['wordcraft','jubarte-0.11.0','jubarte-0.12.0','docxodus-12.6.5'];CNV=['wordcraft','jubarte-0.11.0','jubarte-0.12.0','soffice']

def log(*a):print(time.strftime('%H:%M:%S'),*a,flush=True)
def sh(cmd,out=None,env=None):
 log('RUN',' '.join(map(str,cmd))[:160])
 with (open(out,'w') if out else open(os.devnull,'w')) as fh:
  return subprocess.run(cmd,cwd=ROOT,stdout=fh,stderr=subprocess.STDOUT,env={**os.environ,**(env or {})}).returncode
def waitpid(pattern):
 while subprocess.run(['pgrep','-f',pattern],capture_output=True).stdout.strip():time.sleep(15)

def word_folders(names):
 if names:sh([PY,str(OUT/'run_word400.py'),*names],out=OUT/'word_400'/f'run_{names[0]}.out')

def render(tool,ids):
 """Word renders the frozen redlines of one tool; one fresh-session retry for misses."""
 folder=OUT/'compare'/tool;src=folder/'word_in';pdf=folder/'pdf'
 shutil.rmtree(src,ignore_errors=True);src.mkdir(parents=True);pdf.mkdir(exist_ok=True)
 for i in ids:
  d=folder/'docx'/f'{i}.docx'
  if d.exists() and not (pdf/f'{i}.pdf').exists():shutil.copyfile(d,src/d.name)
 for attempt,(sub,label) in enumerate([(src,'word_pdf'),(folder/'retry','word_pdf_retry')]):
  if attempt:
   miss=[p for p in sorted(src.glob('*.docx')) if not (pdf/(p.stem+'.pdf')).exists()]
   shutil.rmtree(sub,ignore_errors=True);sub.mkdir()
   for p in miss:shutil.copyfile(p,sub/p.name)
   (folder/'render_retry.json').write_text(json.dumps({'first_pass_missing':[p.stem for p in miss]},indent=2)+'\n')
   if not miss:break
  if not any(sub.glob('*.docx')):continue
  out=folder/(label+'_out');cmd=[PY,str(DRIVERS/'word_pdf.py'),'--src',str(sub),'--out',str(out),'--label',tool,'--log',str(folder/(label+'.log'))]
  while True:
   wait_alone();assert settle()
   log('RENDER',tool,label,len(list(sub.glob('*.docx'))))
   rc,hits=run_chunk(folder,cmd)
   if rc is None:shutil.rmtree(out,ignore_errors=True);log('contaminated; redo',tool,label);continue
   rec={'folder':f'compare/{tool}/{label}','command':cmd,'returncode':rc,'driver_sha256':__import__('hashlib').sha256((DRIVERS/'word_pdf.py').read_bytes()).hexdigest(),'driver_commit':'ee49054d','finished':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'exclusive_word':True}
   with (OUT/'word_400'/'driver_invocations.jsonl').open('a') as fh:fh.write(json.dumps(rec)+'\n')
   break
  for p in out.glob('*.pdf') if out.exists() else []:shutil.copyfile(p,pdf/p.name)
 gen={r['doc'] for r in json.loads((folder/'generate_failures.json').read_text())}&set(ids)
 fails=[{'doc':i,'stage':'render','error':'Word could not export this vendor redline in two fresh sessions; see word_pdf.log / word_pdf_retry.log'} for i in ids if i not in gen and not (pdf/f'{i}.pdf').exists()]
 (folder/'render_failures.json').write_text(json.dumps(fails,indent=2)+'\n');log('rendered',tool,len(ids)-len(gen)-len(fails),'/',len(ids),'gen fail',len(gen),'render fail',len(fails))

def main():
 log('waiting for the first Word runner');waitpid('run_word400.py')
 # 1. retries: alias-named conversions (path length) + session-level compare failures
 alias=[p.name for p in sorted((OUT/'word_400').glob('aliasretry1_convert_*'))]
 out=subprocess.run([PY,str(OUT/'build400.py'),'retry','1','compare'],cwd=OUT,capture_output=True,text=True).stdout
 retry=[Path(l).name for l in out.splitlines() if l.startswith('/') and 'compare' in l]
 log('retry folders',alias+retry);word_folders(alias+retry)
 sh([PY,str(OUT/'build400.py'),'status'],out=OUT/'word_400'/'status_after_retry.json')
 # second alias round only if conversions are still short
 rc=subprocess.run([PY,str(OUT/'build400.py'),'freeze'],cwd=OUT,capture_output=True,text=True)
 if rc.returncode:
  log('freeze short after retry 1:',rc.stderr[-400:])
  out=subprocess.run([PY,str(OUT/'build400.py'),'retry_alias','2'],cwd=OUT,capture_output=True,text=True).stdout
  word_folders([Path(l).name for l in out.splitlines() if l.startswith('/')])
  rc=subprocess.run([PY,str(OUT/'build400.py'),'freeze'],cwd=OUT,capture_output=True,text=True)
  if rc.returncode:log('FREEZE FAILED',rc.stderr[-2000:]);sys.exit(2)
 (OUT/'freeze.out').write_text(rc.stdout);log('frozen',rc.stdout[-600:])
 subprocess.run([PY,str(OUT/'report.py')],cwd=ROOT,stdout=subprocess.DEVNULL)
 # 2. conversion scores (no Word needed) run alongside the compare renders
 waitpid('score_prefreeze_loop.sh');waitpid('score_run.py convert')
 conv=subprocess.Popen(['/bin/zsh','-c',' && '.join(f'BENCH_DEVICE=mps {PY} {OUT}/score_run.py convert {t} > {OUT}/score_convert_{t}.out 2>&1' for t in CNV)],cwd=ROOT)
 # 3. compare: Word renders frozen rows tool by tool; a tool waits only for its own generation
 # (generate_fresh writes generate_failures.json when a tool finishes; docxodus is last and slowest)
 ids=[r['id'] for r in csv.DictReader(open(OUT/'comparisons.csv'))]
 scorers=[]
 for t in CMP:
  if t=='docxodus-12.6.5':waitpid('generate_fresh.py compare')
  while not (OUT/'compare'/t/'generate_failures.json').exists():time.sleep(30)
  render(t,ids)
  scorers.append(subprocess.Popen([PY,str(OUT/'score_run.py'),'compare',t],cwd=ROOT,stdout=open(OUT/f'score_compare_{t}.out','w'),stderr=subprocess.STDOUT,env={**os.environ,'SCORE_WORKERS':'4','BENCH_DEVICE':'mps'}))
  while sum(p.poll() is None for p in scorers)>1:time.sleep(20)
 for p in scorers:p.wait()
 conv.wait();log('scores done')
 sh([PY,str(OUT/'report.py'),'--final'],out=OUT/'final_report.out')
 sh([PY,str(OUT/'persist_fresh.py')],out=OUT/'persist_fresh.out')
 (OUT/'BENCHMARK_COMPLETE.json').write_text(json.dumps({'completed_at':time.strftime('%Y-%m-%dT%H:%M:%S%z')},indent=2)+'\n');log('COMPLETE')
if __name__=='__main__':main()
