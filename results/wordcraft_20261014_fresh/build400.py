"""Expand the fresh cohort to 400 comparisons + 400 conversions before any vendor runs.

select : freeze an ordered, stratified candidate list (cohort 1 + seeded reserve)
stage  : copy byte-verified writable inputs into word_400/<chunk>/ folders
status : count valid fresh Word references per candidate
retry  : restage candidates whose failure was Word-session pollution, not the file
freeze : take cohort-1 survivors, then the first valid reserve rows in seeded order
         per state; write comparisons.csv / conversions.csv, oracles, ledgers.
Word itself is only ever driven through scripts/word_redline.py and scripts/word_pdf.py.
"""
from pathlib import Path
import csv,json,random,collections,shutil,sys,time,re
import fixture_reserve as f
import pymupdf
from prepare_oracles import valid
OUT=f.OUT;W=OUT/'word_400'
SEED=20261014
# Rare states take every Word-eligible distinct pair (the corpus holds 174 / 3 / 2 distinct
# with_comments_tracking / with_comments_clean / clean pairs); tracking_without_comments fills to 400.
CMP_TOTAL=400
CMP_TARGET={'with_comments_tracking':200,'with_comments_clean':5,'clean':2,'tracking_without_comments':None}
CMP_RESERVE={'tracking_without_comments':230,'with_comments_tracking':999,'with_comments_clean':999,'clean':999}
CNV_TARGET={s:100 for s in ('clean','tracking_without_comments','with_comments_clean','with_comments_tracking')}
CNV_RESERVE={s:90 for s in CNV_TARGET}
CHUNK={'compare':76,'convert':112}
# Failures that say nothing about the fixture: the Word session was polluted or never reached it.
INFRA=re.compile(r'open produced \d+ new documents|never reached|not reached|no result|timed out|AppleEvent timed out',re.I)

def cohort1_locations():
 """Cohort-1 Word references. word_compare/docx (Word's compare DOCX of the first pass) was
 removed from disk by another actor after selection; its PDFs, the only file the scorer reads,
 are intact. A cohort-1 reference whose PDF is valid but whose DOCX is gone is kept with docx=None
 and listed in oracle_provenance.json as docx_missing."""
 loc={}
 for r in f.rows(OUT/'comparisons_initial.csv'):
  for folder in (OUT/'word_corrected_retry',OUT/'word_compare'):
   if v:=valid(folder,r['id'],True):loc[r['id']]=v;break
   pdf=folder/'pdf'/(r['id']+'__vs__'+r['id']+'.pdf')
   if not (folder/'docx').exists() and pdf.exists():
    try:
     with pymupdf.open(pdf) as d:assert d.page_count>0
     loc[r['id']]=(pdf,None);break
    except Exception:pass
 return loc

def select():
 assert not (W/'candidates_compare.csv').exists(),'selection already frozen'
 W.mkdir(exist_ok=True)
 initial=f.rows(OUT/'comparisons_initial.csv');loc=cohort1_locations()
 seen={(r['base_sha256'],r['next_sha256']) for r in initial};ids={r['id'] for r in initial}
 pool=[r for r in f.comparisons() if (r['base_sha256'],r['next_sha256']) not in seen]
 pool.sort(key=lambda r:r['key']);random.Random(SEED+400).shuffle(pool)
 out=[dict(r,cohort='1',order='0',prior_location='cohort1') for r in initial if r['id'] in loc]
 taken=collections.Counter();pairs=set()
 for r in pool:
  s=r['state'];p=(r['base_sha256'],r['next_sha256'])
  if taken[s]>=CMP_RESERVE.get(s,0) or p in pairs or r['id'] in ids:continue
  assert r['id'];pairs.add(p);ids.add(r['id']);taken[s]+=1
  out.append(dict(r,cohort='2',order=str(sum(taken.values())),prior_location=''))
 f.writecsv(W/'candidates_compare.csv',out)
 conv0=f.rows(OUT/'conversions_initial.csv');seen={r['docx_sha256'] for r in conv0};stems={r['stem'] for r in conv0}
 pool=[r for r in f.conversions() if r['docx_sha256'] not in seen];pool.sort(key=lambda r:r['docx']);random.Random(SEED+401).shuffle(pool)
 cout=[dict(r,cohort='1',order='0') for r in conv0];taken=collections.Counter()
 for r in pool:
  s=r['state']
  if taken[s]>=CNV_RESERVE[s] or r['docx_sha256'] in seen or r['stem'] in stems:continue
  seen.add(r['docx_sha256']);stems.add(r['stem']);taken[s]+=1
  cout.append(dict(r,cohort='2',order=str(sum(taken.values()))))
 f.writecsv(W/'candidates_convert.csv',cout)
 meta={'seed_compare':SEED+400,'seed_convert':SEED+401,'compare_targets':CMP_TARGET,'convert_targets':CNV_TARGET,
  'compare_candidates':collections.Counter(r['state']+'|cohort'+r['cohort'] for r in out),'convert_candidates':collections.Counter(r['state']+'|cohort'+r['cohort'] for r in cout),
  'rule':'Cohort-1 rows that already have a valid fresh Word reference are kept. Reserve rows are drawn by a seeded shuffle and, per state, the first rows (in that order) with a valid fresh Word reference fill the target. Selection never reads vendor output.','selected_at':time.strftime('%Y-%m-%dT%H:%M:%S%z')}
 (W/'selection.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta,indent=1))

def chunks(rows,n):return [rows[i:i+n] for i in range(0,len(rows),n)]

def stage(prefix='',which=('compare','convert'),rows_by=None):
 made=[]
 for kind in which:
  rows=rows_by[kind] if rows_by else [r for r in f.rows(W/f'candidates_{kind}.csv') if not (kind=='compare' and r['cohort']=='1')]
  for i,part in enumerate(chunks(rows,CHUNK[kind]),1):
   folder=W/f'{prefix}{kind}_{i:02}';folder.mkdir(exist_ok=True)
   (f.stage_comparisons if kind=='compare' else f.stage_conversions)(part,folder);made.append(folder)
 return made

def results(kind):
 """ident -> (pdf,docx|None, folder) for every attempt folder, latest valid wins."""
 got={}
 for folder in sorted(W.glob(f'*{kind}_[0-9][0-9]')):
  if not (folder/'selection.csv').exists():continue
  for r in f.rows(folder/'selection.csv'):
   ident=r['id'] if kind=='compare' else r['stem']
   v=valid(folder,r.get('alias') or ident,kind=='compare')
   if v:got[ident]=(v,folder)
 return got

def alias(r):
 """Short staging name: Word for Mac rejects the long corpus stems (path length)."""
 return 'c'+r['docx_sha256'][:16]

def stage_alias(rows,folder):
 import shutil as sh
 (folder/'docx').mkdir(parents=True,exist_ok=True);out=[]
 for r in rows:
  f.restore(r['docx'].removeprefix('corpus/'));src=f.ROOT/r['docx'];dest=folder/'docx'/(alias(r)+'.docx')
  sh.copyfile(src,dest);dest.chmod(0o644);assert f.sha(dest)==r['docx_sha256'];out.append(dict(r,alias=alias(r)))
 f.writecsv(folder/'selection.csv',out);print('Staged',len(out),'alias-named conversions in',folder,flush=True)

def retry_convert_alias(round_n):
 got=results('convert');rows=[r for r in f.rows(W/'candidates_convert.csv') if r['stem'] not in got]
 made=[]
 for i,part in enumerate(chunks(rows,CHUNK['convert']),1):
  folder=W/f'aliasretry{round_n}_convert_{i:02}';folder.mkdir(exist_ok=True);stage_alias(part,folder);made.append(folder)
 return made

def driver_failures(folder):
 text=(folder/'driver.log').read_text(errors='replace') if (folder/'driver.log').exists() else ''
 fails={}
 for m in re.finditer(r'FAIL: ([^ ]+?)\.docx(?: → [^ ]+?\.docx)? (?:—|:) (.*)',text):fails[m.group(1)]=m.group(2).strip()
 return fails

def status(verbose=True):
 rep={}
 for kind in ('compare','convert'):
  cand=f.rows(W/f'candidates_{kind}.csv');got=results(kind);c=collections.Counter()
  for r in cand:
   ident=r['id'] if kind=='compare' else r['stem']
   ok=(kind=='compare' and r['cohort']=='1') or ident in got
   c[(r['state'],r['cohort'],ok)]+=1
  rep[kind]={f'{s}|cohort{co}|{"valid" if ok else "no-ref"}':n for (s,co,ok),n in sorted(c.items())}
 if verbose:print(json.dumps(rep,indent=1))
 return rep

def attempts(kind,ident):
 out=[]
 for folder in sorted(W.glob(f'*{kind}_[0-9][0-9]')):
  if not (folder/'selection.csv').exists():continue
  names={(r['id'] if kind=='compare' else r['stem']):(r.get('alias') or (r['id'] if kind=='compare' else r['stem'])) for r in f.rows(folder/'selection.csv')}
  if ident in names:
   name=names[ident];fail=driver_failures(folder).get(name)
   out.append({'folder':folder.name,'staged_as':name,'error':fail if fail is not None else ('valid' if valid(folder,name,kind=='compare') else 'no output and no FAIL line (driver did not finish)')})
 return out

def retry(round_n,kinds=('compare','convert')):
 rows_by={}
 for kind in kinds:
  got=results(kind);rows_by[kind]=[]
  for r in f.rows(W/f'candidates_{kind}.csv'):
   ident=r['id'] if kind=='compare' else r['stem']
   if (kind=='compare' and r['cohort']=='1') or ident in got:continue
   tried=attempts(kind,ident)
   last=tried[-1]['error'] if tried else 'never staged'
   if not tried or INFRA.search(last) or last.startswith('no output'):rows_by[kind].append(r)
  print(kind,'retrying',len(rows_by[kind]),'session-level failures')
 return stage(prefix=f'retry{round_n}_',which=kinds,rows_by=rows_by)

def freeze():
 assert not (OUT/'ORACLES_READY.json').exists()
 out={}
 for kind,target in (('compare',CMP_TARGET),('convert',CNV_TARGET)):
  cand=f.rows(W/f'candidates_{kind}.csv');got=results(kind);loc1=cohort1_locations() if kind=='compare' else {}
  chosen=[];locations={};taken=collections.Counter();excl=[];surplus=[]
  if kind=='compare':
   # fill-in state takes whatever the capped rare states leave of the total
   target=dict(target);fill=[s for s,v in target.items() if v is None][0]
   avail=collections.Counter(r['state'] for r in cand if (r['cohort']=='1' and r['id'] in loc1) or (r['cohort']=='2' and r['id'] in got))
   for s in target:
    if s!=fill:target[s]=min(target[s],avail[s])
   target[fill]=CMP_TOTAL-sum(v for s,v in target.items() if s!=fill)
  # cohort 1 first (its survivors are kept regardless of order), then reserve in seeded order
  for r in sorted(cand,key=lambda r:(r['cohort'],int(r['order']))):
   ident=r['id'] if kind=='compare' else r['stem'];s=r['state']
   ref=loc1.get(ident) if (kind=='compare' and r['cohort']=='1') else (got[ident][0] if ident in got else None)
   if ref is None:
    excl.append({'id':ident,'state':s,'cohort':r['cohort'],'attempts':attempts(kind,ident),'eligibility_label':'no fresh Word reference','label_scope':'Word could not compare/export it in this run; not proof of malformed OOXML','selection_uses_vendor_results':False});continue
   if taken[s]>=target[s]:surplus.append(ident);continue
   taken[s]+=1;chosen.append(dict(r,stage_cohort=r['cohort']));locations[ident]=ref
  short={s:target[s]-taken[s] for s in target if taken[s]<target[s]}
  assert not short,(kind,'short of targets',short)
  # Cohort-1 conversion failures are recorded as exclusions too (their initial row had no Word reference).
  if kind=='compare':
   for r in f.rows(OUT/'comparisons_initial.csv'):
    if r['id'] not in loc1:excl.append({'id':r['id'],'state':r['state'],'cohort':'1','attempts':[{'folder':'word_compare / word_corrected_retry','error':'see word_compare/oracle_failures_first_pass.json and word_corrected_retry/driver.log'}],'eligibility_label':'no fresh Word reference','label_scope':'Word could not compare/export it in this run; not proof of malformed OOXML','selection_uses_vendor_results':False})
  name='comparisons.csv' if kind=='compare' else 'conversions.csv'
  f.writecsv(OUT/name,chosen)
  dest=OUT/kind/'oracle';dest.mkdir(parents=True,exist_ok=True)
  if kind=='compare':(OUT/kind/'oracle_docx').mkdir(exist_ok=True)
  for ident,ref in locations.items():
   shutil.copyfile(ref[0],dest/(ident+'.pdf'))
   if kind=='compare' and ref[1]:shutil.copyfile(ref[1],OUT/kind/'oracle_docx'/(ident+'.docx'))
  key=('base_sha256','next_sha256') if kind=='compare' else ('docx_sha256',)
  assert len({tuple(r[k] for k in key) for r in chosen})==len(chosen)==sum(target.values())
  (OUT/(('comparison' if kind=='compare' else 'conversion')+'_exclusions.json')).write_text(json.dumps(excl,indent=2)+'\n')
  out[kind]={'n':len(chosen),'states':dict(taken),'by_cohort':dict(collections.Counter(r['cohort'] for r in chosen)),'excluded':len(excl),'surplus_valid_unused':len(surplus),'locations':{k:[str(p) for p in v if p] for k,v in locations.items()}}
 prov=json.loads((OUT/'sample_provenance.json').read_text())
 for kind,name in (('compare','comparisons.csv'),('convert','conversions.csv')):
  rs=f.rows(OUT/name);k='comparisons' if kind=='compare' else 'conversions'
  prov[name+'_sha256']=f.sha(OUT/name);prov.setdefault('states',{})[k]=dict(collections.Counter(r['state'] for r in rs));prov.setdefault('cells',{})[k]=dict(collections.Counter(r['state']+'|'+r['source_pool']+'|'+r['page_band'] for r in rs))
 c=f.rows(OUT/'comparisons.csv');v=f.rows(OUT/'conversions.csv')
 needed={'word/'+r[key]+'.docx' for r in c for key in ('base','next')}|{r['docx'].removeprefix('corpus/') for r in v}
 prov['manifest_hashes']={rel:f.MAN[rel] for rel in sorted(needed)};prov['input_staging_mode']='0644'
 prov['selection_policy']='400+400: cohort-1 rows with a fresh Word reference are kept; a seeded stratified reserve fills each state in shuffle order with the first rows Word could compare/export; Word-session failures (ghost documents, never reached) were retried, not excluded; no selection reads vendor output'
 prov['expansion']=json.loads((W/'selection.json').read_text());prov['frozen_at']=time.strftime('%Y-%m-%dT%H:%M:%S%z')
 (OUT/'sample_provenance.json').write_text(json.dumps(prov,indent=2)+'\n')
 refs={kind:{k:{'sha256':f.sha(OUT/kind/'oracle'/(k+'.pdf')),'fresh_source':p[0]} for k,p in out[kind]['locations'].items()} for kind in out}
 (OUT/'oracle_provenance.json').write_text(json.dumps({'fresh':True,'drivers':{d:f.sha(OUT/'drivers_ee49054d'/d) for d in ('word_pdf.py','word_redline.py')},'driver_commit':'ee49054d','driver_invocations':'word_400/driver_invocations.jsonl','input_mode':'0644','references':refs,'docx_missing':sorted(k for k,p in out['compare']['locations'].items() if len(p)<2),'docx_missing_note':'Word compare DOCX of the cohort-1 first pass (word_compare/docx) was removed from disk by another actor after selection; the Word PDFs exported in the same driver run, which are the oracles scored, are intact'},indent=2)+'\n')
 summary={k:{x:y for x,y in out[k].items() if x!='locations'} for k in out}
 (OUT/'ORACLES_READY.json').write_text(json.dumps({'comparisons':out['compare']['n'],'conversions':out['convert']['n'],'summary':summary,'final_manifest_sha256':{n:f.sha(OUT/n) for n in ('comparisons.csv','conversions.csv')},'oracle_provenance_sha256':f.sha(OUT/'oracle_provenance.json'),'frozen_at':time.strftime('%Y-%m-%dT%H:%M:%S%z')},indent=2)+'\n')
 print(json.dumps(summary,indent=1))

if __name__=='__main__':
 cmd=sys.argv[1]
 if cmd=='select':select()
 elif cmd=='stage':print('\n'.join(map(str,stage())))
 elif cmd=='status':status()
 elif cmd=='retry':print('\n'.join(map(str,retry(int(sys.argv[2]),tuple(sys.argv[3:]) or ('compare','convert')))))
 elif cmd=='retry_alias':print('\n'.join(map(str,retry_convert_alias(int(sys.argv[2])))))
 elif cmd=='freeze':freeze()
