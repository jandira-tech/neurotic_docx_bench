"""Corrected writable fixture staging. Word is invoked only through repository CLIs."""
from pathlib import Path
import json,sys,subprocess,shutil,time,os,csv,stat
import fixture_reserve as f
from prepare_oracles import valid,progress
OUT=f.OUT;ROOT=f.ROOT;PY=ROOT/'.venv/bin/python';receipts=[]
def run_word(driver,folder,args):
 inputs=[p for side in ('A','B','docx') for p in (folder/side).glob('*.docx') if not p.name.startswith('~$')]
 assert inputs and all(p.stat().st_mode&stat.S_IWUSR for p in inputs),'Word inputs must be owner-writable'
 command=[str(PY),str(ROOT/'scripts'/driver),*args,'--log',str(folder/'driver.log')]
 print('RUN unmodified',driver,folder.name,'writable inputs',len(inputs),flush=True)
 with (folder/'driver.out').open('w') as log:proc=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
 receipts.append({'command':command,'returncode':proc.returncode,'driver_sha256':f.sha(ROOT/'scripts'/driver),'unmodified_driver':True,'staging_mode':'0644','input_count':len(inputs)})
 (OUT/'word_driver_invocations_corrected.json').write_text(json.dumps(receipts,indent=2)+'\n')
 return proc.returncode

def comparisons():
 initial=f.rows(OUT/'comparisons_initial.csv');chosen={};locations={};used=list(initial);exclusions=[]
 for r in initial:
  for folder in (OUT/'word_corrected_retry',OUT/'word_compare'):
   if v:=valid(folder,r['id'],True):chosen[r['id']]=r;locations[r['id']]=v;break
 failed=[r for r in initial if r['id'] not in chosen];progress('comparison',len(chosen),0)
 for round_n in range(1,21):
  if not failed:break
  current,ledger=f.select_replacements(failed,used,1000+round_n);folder=OUT/f'word_valid_reserve_{round_n:02}';folder.mkdir(exist_ok=True);f.stage_comparisons(current,folder)
  for e in ledger:e.update({'eligibility_label':'corrupt / rejected by Word','label_scope':'Word rejected after writable staging; not proof of malformed OOXML','evidence':'word_corrected_retry/driver.log' if round_n==1 else f'word_valid_reserve_{round_n-1:02}/driver.log'})
  (folder/'replacement_ledger.json').write_text(json.dumps(ledger,indent=2)+'\n')
  run_word('word_redline.py',folder,['--a',str(folder/'A'),'--b',str(folder/'B'),'--out',str(folder/'pdf'),'--docx-out',str(folder/'docx'),'--emit','both'])
  used.extend(current);exclusions.extend(ledger);failed=[]
  for r in current:
   if v:=valid(folder,r['id'],True):chosen[r['id']]=r;locations[r['id']]=v
   else:failed.append(r)
  progress('comparison',len(chosen),len(exclusions));print('Fresh valid comparison references',len(chosen),'/ 200',flush=True)
 assert len(chosen)==200
 final=list(chosen.values());assert len({(r['base_sha256'],r['next_sha256']) for r in final})==200
 f.writecsv(OUT/'comparisons.csv',final)
 for kind in ('oracle','oracle_docx'):(OUT/'compare'/kind).mkdir(parents=True,exist_ok=True)
 for key,(pdf,docx) in locations.items():shutil.copyfile(pdf,OUT/'compare/oracle'/(key+'.pdf'));shutil.copyfile(docx,OUT/'compare/oracle_docx'/(key+'.docx'))
 (OUT/'comparison_exclusions.json').write_text(json.dumps(exclusions,indent=2)+'\n')
 return final,locations

def conversions():
 initial=f.rows(OUT/'conversions.csv');current=initial;used=[];chosen={};locations={};exclusions=[];folder=OUT/'word_convert'
 if not (OUT/'conversions_initial.csv').exists():shutil.copyfile(OUT/'conversions.csv',OUT/'conversions_initial.csv')
 for round_n in range(21):
  if round_n:
   current,ledger=f.select_conversion_replacements(failed,used,1000+round_n);folder=OUT/f'word_valid_convert_reserve_{round_n:02}';folder.mkdir(exist_ok=True);f.stage_conversions(current,folder);exclusions.extend(ledger);(folder/'replacement_ledger.json').write_text(json.dumps(ledger,indent=2)+'\n')
  run_word('word_pdf.py',folder,['--src',str(folder/'docx'),'--out',str(folder/'pdf')])
  used.extend(current);failed=[]
  for r in current:
   if v:=valid(folder,r['stem']):chosen[r['stem']]=r;locations[r['stem']]=v[0]
   else:failed.append(r)
  progress('conversion',len(chosen),len(exclusions));print('Fresh valid conversion references',len(chosen),'/ 200',flush=True)
  if not failed:break
 assert len(chosen)==200
 final=list(chosen.values());assert len({r['docx_sha256'] for r in final})==200;f.writecsv(OUT/'conversions.csv',final);(OUT/'convert/oracle').mkdir(parents=True,exist_ok=True)
 for key,pdf in locations.items():shutil.copyfile(pdf,OUT/'convert/oracle'/(key+'.pdf'))
 (OUT/'conversion_exclusions.json').write_text(json.dumps(exclusions,indent=2)+'\n')
 return final,locations

if __name__=='__main__':
 if len(sys.argv)>1:
  pid=int(sys.argv[1]);print('Waiting for corrected writable Word retry',pid,flush=True)
  while True:
   try:os.kill(pid,0)
   except ProcessLookupError:break
   time.sleep(5)
 c,cloc=comparisons();v,vloc=conversions();prov=json.loads((OUT/'sample_provenance.json').read_text())
 for name,rs in [('comparisons.csv',c),('conversions.csv',v)]:
  kind='comparisons' if name.startswith('comparisons') else 'conversions';prov[name+'_sha256']=f.sha(OUT/name);prov['states'][kind]=dict(f.collections.Counter(r['state'] for r in rs));prov['cells'][kind]=dict(f.collections.Counter(r['state']+'|'+r['source_pool']+'|'+r['page_band'] for r in rs))
 needed={'word/'+r[key]+'.docx' for r in c for key in ('base','next')}|{r['docx'].removeprefix('corpus/') for r in v}
 prov['manifest_hashes']={rel:f.MAN[rel] for rel in sorted(needed)};prov['input_staging_mode']='0644';prov['permission_audit']='permission_audit.json; permissions_fixed.json';prov['prior_permission_exclusions_withdrawn']=True;prov['selection_policy']='Fresh Word eligibility with writable byte-identical inputs; replacements only for genuine Word failures, before any vendor generation';prov['frozen_at']=time.strftime('%Y-%m-%dT%H:%M:%S%z');(OUT/'sample_provenance.json').write_text(json.dumps(prov,indent=2)+'\n')
 refs={kind:{key:{'sha256':f.sha(OUT/kind/'oracle'/(key+'.pdf')),'fresh_source':str(paths[0] if kind=='compare' else paths)} for key,paths in mapping.items()} for kind,mapping in [('compare',cloc),('convert',vloc)]}
 (OUT/'oracle_provenance.json').write_text(json.dumps({'fresh':True,'drivers_unmodified':True,'input_mode':'0644','references':refs},indent=2)+'\n');(OUT/'ORACLES_READY.json').write_text(json.dumps({'comparisons':200,'conversions':200,'final_manifest_sha256':{name:f.sha(OUT/name) for name in ('comparisons.csv','conversions.csv')},'oracle_provenance_sha256':f.sha(OUT/'oracle_provenance.json')},indent=2)+'\n');print('READY: 200 comparison and 200 conversion references; cohort frozen',flush=True)
