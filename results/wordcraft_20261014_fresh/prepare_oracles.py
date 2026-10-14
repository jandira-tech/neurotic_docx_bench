"""Fixture/oracle orchestration: invokes ONLY the unmodified repository Word CLIs."""
from pathlib import Path
import json,sys,subprocess,shutil,time,os,zipfile,hashlib
import pymupdf
import fixture_reserve as f
OUT=f.OUT;ROOT=f.ROOT;PY=ROOT/'.venv/bin/python'
receipts=[]
def run(driver,folder,args):
 command=[str(PY),str(ROOT/'scripts'/driver),*args,'--log',str(folder/'driver.log')]
 print('RUN',driver,folder.name,flush=True)
 sys.path.insert(0,str(ROOT/'scripts'))
 from word_pdf import WordSession
 session=WordSession();count=session.open_document_count()
 assert count==0,('Word must be empty before a fresh batch; preserve external documents',count)
 session.started_clean=True
 assert session.recycle(), 'Repository WordSession recovery failed'
 if (folder/'driver.out').exists():shutil.copy2(folder/'driver.out',folder/('driver.previous.'+str(time.time_ns())+'.out'))
 with (folder/'driver.out').open('w') as log:p=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
 receipts.append({'command':command,'returncode':p.returncode,'driver_sha256':f.sha(ROOT/'scripts'/driver),'unmodified_driver':True})
 (OUT/'word_driver_invocations.json').write_text(json.dumps(receipts,indent=2)+'\n')
 return p.returncode

def valid(folder,ident,compare=False):
 stem=ident+'__vs__'+ident if compare else ident
 pdf=folder/'pdf'/(stem+'.pdf');docx=folder/'docx'/(stem+'.docx')
 try:
  with pymupdf.open(pdf) as d:assert d.page_count>0
  if compare:
   with zipfile.ZipFile(docx) as z:assert z.testzip() is None;z.read('word/document.xml')
  return pdf,docx
 except Exception:return None

def progress(phase,n,exclusions=0):
 path=OUT/'oracle_eligibility_progress.json';d=json.loads(path.read_text()) if path.exists() else {}
 d[phase+'_references_valid']=n;d[phase+'_word_exclusions']=exclusions;d['vendor_generation_started']=False;d['vendor_scores']=0;d['updated_at']=time.strftime('%Y-%m-%d %H:%M:%S')
 path.write_text(json.dumps(d,indent=2)+'\n');subprocess.run([str(PY),str(OUT/'report.py')],cwd=ROOT,stdout=subprocess.DEVNULL)

def compare():
 initial=f.rows(OUT/'comparisons_initial.csv');chosen={};locations={};used=list(initial);exclusions=[]
 for r in initial:
  for folder in (OUT/'word_compare',OUT/'word_retry_stock'):
   if v:=valid(folder,r['id'],True):chosen[r['id']]=r;locations[r['id']]=v;break
 folders=sorted(OUT.glob('word_reserve_[0-9][0-9]'))
 all_attempts=folders+[p for p in sorted(OUT.glob('word_reserve_*')) if p not in folders and (p/'selection.csv').exists()]
 for folder in all_attempts:
  current=f.rows(folder/'selection.csv');used.extend(current)
  ledger=folder/'replacement_ledger.json'
  if ledger.exists():exclusions.extend(json.loads(ledger.read_text()))
  for r in current:
   if v:=valid(folder,r['id'],True):chosen[r['id']]=r;locations[r['id']]=v
 failed=[r for r in f.rows(folders[-1]/'selection.csv') if r['id'] not in chosen]
 progress('comparison',len(chosen),len(exclusions));print('COMPARE Word eligible',len(chosen),'/ 200',flush=True)
 for round_n in range(len(folders)+1,41):
  if not failed:break
  current,ledger=f.select_replacements(failed,used,round_n);folder=OUT/f'word_reserve_{round_n:02}';folder.mkdir(exist_ok=True);f.stage_comparisons(current,folder)
  for entry in ledger:entry['eligibility_label']='corrupt / rejected by Word';entry['label_scope']='Word oracle eligibility; not proof of malformed OOXML'
  (folder/'replacement_ledger.json').write_text(json.dumps(ledger,indent=2)+'\n')
  # Only the small unresolved reserve subset uses the repository's documented
  # serial fallback, whose recovery handles poisoned Word sessions. The original
  # cohort and full vendor rendering use the repository's monolithic batches.
  run('word_redline.py',folder,['--a',str(folder/'A'),'--b',str(folder/'B'),'--out',str(folder/'pdf'),'--docx-out',str(folder/'docx'),'--emit','both','--no-one-redline-osascript'])
  used.extend(current);exclusions.extend(ledger);failed=[]
  for r in current:
   if v:=valid(folder,r['id'],True):chosen[r['id']]=r;locations[r['id']]=v
   else:failed.append(r)
  progress('comparison',len(chosen),len(exclusions));print('COMPARE Word eligible',len(chosen),'/ 200; failures',len(failed),flush=True)
 assert len(chosen)==200,('Could not create 200 fresh Word comparison references',len(chosen))
 final=list(chosen.values());assert len({(r['base_sha256'],r['next_sha256']) for r in final})==200
 f.writecsv(OUT/'comparisons.csv',final);(OUT/'compare/oracle').mkdir(parents=True,exist_ok=True);(OUT/'compare/oracle_docx').mkdir(exist_ok=True)
 for key,(pdf,docx) in locations.items():shutil.copy2(pdf,OUT/'compare/oracle'/(key+'.pdf'));shutil.copy2(docx,OUT/'compare/oracle_docx'/(key+'.docx'))
 (OUT/'comparison_exclusions.json').write_text(json.dumps(exclusions,indent=2)+'\n')
 return locations

def convert():
 source=OUT/'conversions.csv';initial=f.rows(source)
 if not (OUT/'conversions_initial.csv').exists():shutil.copy2(source,OUT/'conversions_initial.csv')
 current=initial;used=[];chosen={};locations={};exclusions=[];folder=OUT/'word_convert'
 for round_n in range(0,21):
  if round_n:
   current,ledger=f.select_conversion_replacements(failed,used,round_n);folder=OUT/f'word_convert_reserve_{round_n:02}';folder.mkdir(exist_ok=True);f.stage_conversions(current,folder);exclusions.extend(ledger);(folder/'replacement_ledger.json').write_text(json.dumps(ledger,indent=2)+'\n')
  run('word_pdf.py',folder,['--src',str(folder/'docx'),'--out',str(folder/'pdf')])
  used.extend(current);failed=[]
  for r in current:
   if v:=valid(folder,r['stem']):chosen[r['stem']]=r;locations[r['stem']]=v[0]
   else:failed.append(r)
  progress('conversion',len(chosen),len(exclusions));print('CONVERT Word eligible',len(chosen),'/ 200; failures',len(failed),flush=True)
  if not failed:break
 assert len(chosen)==200,('Could not create 200 fresh Word conversion references',len(chosen))
 final=list(chosen.values());assert len({r['docx_sha256'] for r in final})==200;f.writecsv(source,final);(OUT/'convert/oracle').mkdir(parents=True,exist_ok=True)
 for key,pdf in locations.items():shutil.copy2(pdf,OUT/'convert/oracle'/(key+'.pdf'))
 (OUT/'conversion_exclusions.json').write_text(json.dumps(exclusions,indent=2)+'\n')
 return locations

if __name__=='__main__':
 if len(sys.argv)>1:
  pid=int(sys.argv[1]);print('Waiting for existing standard driver PID',pid,flush=True)
  while True:
   try:os.kill(pid,0)
   except ProcessLookupError:break
   time.sleep(5)
 c=compare();v=convert();provenance=json.loads((OUT/'sample_provenance.json').read_text())
 for name in ('comparisons.csv','conversions.csv'):
  rs=f.rows(OUT/name);kind='comparisons' if name.startswith('comparisons') else 'conversions';provenance[name+'_sha256']=f.sha(OUT/name);provenance['states'][kind]=dict(f.collections.Counter(r['state'] for r in rs));provenance['cells'][kind]=dict(f.collections.Counter(r['state']+'|'+r['source_pool']+'|'+r['page_band'] for r in rs))
 provenance['selection_policy']='Fresh Word-oracle eligibility before any fresh vendor generation; Word failures replaced and logged; no vendor-based replacement';provenance['frozen_at']=time.strftime('%Y-%m-%dT%H:%M:%S%z');(OUT/'sample_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
 oracle={kind:{key:{'sha256':f.sha(OUT/kind/'oracle'/(key+'.pdf')),'fresh_source':str(paths[0] if kind=='compare' else paths)} for key,paths in mapping.items()} for kind,mapping in [('compare',c),('convert',v)]}
 (OUT/'oracle_provenance.json').write_text(json.dumps({'fresh':True,'drivers_unmodified':True,'references':oracle},indent=2)+'\n');(OUT/'ORACLES_READY.json').write_text(json.dumps({'comparisons':200,'conversions':200,'final_manifest_sha256':{name:f.sha(OUT/name) for name in ('comparisons.csv','conversions.csv')},'oracle_provenance_sha256':f.sha(OUT/'oracle_provenance.json')},indent=2)+'\n');print('All 400 fresh Word references ready; final cohort frozen',flush=True)
