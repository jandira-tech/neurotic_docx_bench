"""Run the frozen fresh cohort. All Word rendering calls the repository CLI directly."""
from pathlib import Path
import subprocess,sys,json,time,os,signal,hashlib,csv,re,threading,shutil
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_word400 import wait_alone,settle
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];PY=ROOT/'.venv/bin/python'
def run(name,cmd,require_success=True):
 print('START',name,flush=True)
 with (OUT/(name+'.out')).open('w') as log:proc=subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
 (OUT/'active_step.json').write_text(json.dumps({'step':name,'pid':proc.pid,'command':cmd,'started_at':time.strftime('%Y-%m-%dT%H:%M:%S%z')},indent=2)+'\n')
 rc=proc.wait();print('END',name,'exit',rc,flush=True)
 if require_success and rc:raise RuntimeError((name,'exit',rc))
 return rc

def refresh():subprocess.run([str(PY),str(OUT/'report.py')],cwd=ROOT,stdout=subprocess.DEVNULL,check=True)

def main():
 print('Waiting for all fresh Word references and frozen corrected writable cohort',flush=True)
 while not (OUT/'ORACLES_READY.json').exists():time.sleep(5)
 ready=json.loads((OUT/'ORACLES_READY.json').read_text());N={'compare':ready['comparisons'],'convert':ready['conversions']}
 assert N=={'compare':len(list(csv.DictReader((OUT/'comparisons.csv').open()))),'convert':len(list(csv.DictReader((OUT/'conversions.csv').open())))}
 tools=json.loads((OUT/'tools.json').read_text())
 for key in ('wordcraft-cli','jubarte-0.11.0','jubarte-0.12.0'):
  assert hashlib.sha256(Path(tools[key]['path']).read_bytes()).hexdigest()==tools[key]['sha256']
 comparison_tools=['wordcraft','jubarte-0.11.0','jubarte-0.12.0','docxodus-12.6.5'];conversion_tools=['wordcraft','jubarte-0.11.0','jubarte-0.12.0','soffice']
 for phase,tools_in in [('compare',comparison_tools),('convert',conversion_tools)]:
  for tool in tools_in:
   run('generate_'+phase+'_'+tool,[str(PY),str(OUT/'generate_fresh.py'),phase,tool]);refresh()
 print('Timed generation complete: scoring may now overlap Word rendering',flush=True)
 score_jobs=[]
 for tool in comparison_tools:
  folder=OUT/'compare'/tool
  wait_alone();assert settle()
  run('word_pdf_'+tool,[str(PY),str(OUT/'drivers_ee49054d'/'word_pdf.py'),'--src',str(folder/'docx'),'--out',str(folder/'pdf'),'--label',tool,'--log',str(folder/'word_pdf.log')],require_success=False)
  # One retry, in a fresh settled Word session, for every redline still without a PDF.
  # Same rule for every tool; a file Word cannot export twice stays a render failure.
  missing=[p for p in sorted((folder/'docx').glob('*.docx')) if not (folder/'pdf'/(p.stem+'.pdf')).exists()]
  if missing:
   retry=folder/'retry';(retry/'docx').mkdir(parents=True,exist_ok=True)
   for p in missing:shutil.copyfile(p,retry/'docx'/p.name)
   wait_alone();assert settle()
   run('word_pdf_retry_'+tool,[str(PY),str(OUT/'drivers_ee49054d'/'word_pdf.py'),'--src',str(retry/'docx'),'--out',str(retry/'pdf'),'--label',tool,'--log',str(retry/'word_pdf.log')],require_success=False)
   for pdf in (retry/'pdf').glob('*.pdf') if (retry/'pdf').exists() else []:shutil.copyfile(pdf,folder/'pdf'/pdf.name)
   (folder/'render_retry.json').write_text(json.dumps({'first_pass_missing':[p.stem for p in missing],'recovered_on_retry':sorted(p.stem for p in (retry/'pdf').glob('*.pdf')) if (retry/'pdf').exists() else []},indent=2)+'\n')
  rs=list(csv.DictReader((OUT/'comparisons.csv').open()));known_gen={r['doc'] for r in json.loads((folder/'generate_failures.json').read_text())};errors={}
  logs=[folder/'word_pdf.log',folder/'retry'/'word_pdf.log']
  for line in [l for log in logs if log.exists() for l in log.read_text().splitlines()]:
   match=re.search(r'FAIL: ([0-9a-f]{10})\.docx (?:—|:) (.*)',line)
   if match:errors[match.group(1)]=match.group(2)
  failures=[{'doc':r['id'],'stage':'render','error':errors.get(r['id'],'Word could not export this vendor redline in two sessions; see word_pdf.log and retry/word_pdf.log')} for r in rs if r['id'] not in known_gen and not (folder/'pdf'/(r['id']+'.pdf')).exists()]
  (folder/'render_failures.json').write_text(json.dumps(failures,indent=2)+'\n')
  # Only one scoring pool at a time to limit memory and raster disk use.
  if score_jobs:
   prior,handle=score_jobs.pop(0);assert prior.wait()==0;handle.close();refresh()
  handle=(OUT/('score_compare_'+tool+'.out')).open('w');job=subprocess.Popen([str(PY),str(OUT/'score_run.py'),'compare',tool],cwd=ROOT,stdout=handle,stderr=subprocess.STDOUT);score_jobs.append((job,handle));refresh()
 for job,handle in score_jobs:assert job.wait()==0;handle.close();refresh()
 for tool in conversion_tools:
  run('score_convert_'+tool,[str(PY),str(OUT/'score_run.py'),'convert',tool]);refresh()
 run('final_report',[str(PY),str(OUT/'report.py'),'--final']);run('persist_fresh',[str(PY),str(OUT/'persist_fresh.py')])
 (OUT/'BENCHMARK_COMPLETE.json').write_text(json.dumps({'comparisons':N['compare'],'conversions':N['convert'],'tools_per_task':4,'completed_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'report_sha256':hashlib.sha256((OUT/'REPORT.json').read_bytes()).hexdigest()},indent=2)+'\n');print('First fresh cohort complete; ready for Markdown regeneration and main publication',flush=True)
if __name__=='__main__':main()
