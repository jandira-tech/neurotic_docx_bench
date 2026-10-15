"""Select and restore hash-verified reserve inputs; never drives Word or vendors."""
from pathlib import Path
import csv,json,random,hashlib,shutil,collections
from concurrent.futures import ThreadPoolExecutor
from huggingface_hub import hf_hub_download
ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
PROV=json.loads((OUT/'sample_provenance.json').read_text()); MAN=json.loads((ROOT/'corpus/MANIFEST.sha256.json').read_text())['files']
def rows(path):return list(csv.DictReader(path.open()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def band(n):
 n=int(n or 0);return '1' if n==1 else '2-4' if 1<n<=4 else '5-10' if 4<n<=10 else '11+' if n>10 else 'unknown'
def writecsv(path,rs):
 fields=list(dict.fromkeys(k for r in rs for k in r))
 with path.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rs)
def restore(rel):
 target=ROOT/'corpus'/rel;expected=MAN[rel]
 if not target.exists() or sha(target)!=expected:
  source=Path(hf_hub_download(PROV['repo'],rel,repo_type='dataset',revision=PROV['revision']))
  assert sha(source)==expected,(rel,'download hash mismatch')
  target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
 if target.suffix=='.docx':target.chmod(0o644)
 assert sha(target)==expected
 return target

def comparisons():
 old=rows(ROOT/'results/release_0.12.0_evidence_c551/sample_redline_0.12.0.csv')
 pages=json.loads((ROOT/'results/redlines_0929_full/scores_jubarte-0.12.0_sample_redline_0.12.0.json').read_text())['rows']
 metadata={r['key']:r for r in rows(ROOT/'corpus/word/comparisons.csv')}
 pool={r['key']:r for f in sorted((ROOT/'corpus/word/pools').glob('*_pairs.csv')) for r in rows(f)}
 allrows={r['key']:dict(r) for r in old}
 for key,m in metadata.items():
  if key in allrows or key not in pool or not m['docx'] or not m['pdf']:continue
  r=pool[key];base=r['base'];nxt=r['next']
  allrows[key]={'key':key,'base':base,'next':nxt,'docx':m['docx'],'pdf':m['pdf'],'state':m['state'],'id':m['id'],'sets':m['sets'],'base_sha256':MAN['word/'+base+'.docx'],'next_sha256':MAN['word/'+nxt+'.docx'],'docx_sha256':MAN['word/'+m['docx']],'pdf_sha256':MAN['word/'+m['pdf']]}
 for key,r in allrows.items():
  r['pages']=pages.get(key,{}).get('page_count_oracle',0);r['page_band']=band(r['pages']);r['source_pool']=r['sets'].split(';')[0] or 'unknown';r['reserve_source']='previously_benchmarked_release_0.12.0' if key in {v['key'] for v in old} else 'full_word_corpus'
 return list(allrows.values())

def select_replacements(failed,used,round_number):
 candidates=comparisons();rng=random.Random(20261014+round_number);rng.shuffle(candidates)
 seen={(r['base_sha256'],r['next_sha256']) for r in used};chosen=[];ledger=[]
 for original in failed:
  available=[r for r in candidates if (r['base_sha256'],r['next_sha256']) not in seen]
  def rank(r):
   state=r['state']==original['state'];pool=r['source_pool']==original['source_pool'];page=r['page_band']==original['page_band']
   return (state,pool and page,page,pool,r['reserve_source']=='previously_benchmarked_release_0.12.0')
  same_state=[r for r in available if r['state']==original['state']]
  # Rare comparison states can exhaust the entire corpus after Word exclusions.
  if not same_state:
   preferred='with_comments_tracking' if original['state']=='with_comments_clean' else 'tracking_without_comments'
   available=[r for r in available if r['state']==preferred]
  best=max(same_state or available,key=rank)
  chosen.append(best);seen.add((best['base_sha256'],best['next_sha256']))
  ledger.append({'excluded_id':original['id'],'replacement_id':best['id'],'excluded_state':original['state'],'replacement_state':best['state'],'source_pool_preserved':best['source_pool']==original['source_pool'],'page_band_preserved':best['page_band']==original['page_band'],'selection_uses_vendor_results':False,'state_change_reason':None if best['state']==original['state'] else 'No unused same-state comparison in full Word corpus; nearest markup state used','round':round_number})
 return chosen,ledger

def stage_comparisons(rs,folder):
 paths=sorted({'word/'+r[k]+'.docx' for r in rs for k in ('base','next')})
 with ThreadPoolExecutor(8) as pool:list(pool.map(restore,paths))
 for group,key,hashkey in [('A','base','base_sha256'),('B','next','next_sha256')]:
  (folder/group).mkdir(parents=True,exist_ok=True)
  for r in rs:
   source=ROOT/'corpus/word'/(r[key]+'.docx');assert sha(source)==r[hashkey]
   dest=folder/group/(r['id']+'.docx')
   if not dest.exists():shutil.copyfile(source,dest)
   dest.chmod(0o644)
   assert sha(dest)==r[hashkey]
 writecsv(folder/'selection.csv',rs)
 print('Staged',len(rs),'reserve pairs in',folder,flush=True)

def conversions():
 old=rows(ROOT/'results/release_0.12.0_evidence_c551/sample_conversion_0.12.0.csv')
 metadata={r['docx']:r for f in ('documents.csv','comparisons.csv') for r in rows(ROOT/'corpus/word'/f)}
 allrows={r['docx']:dict(r) for r in old}
 pages={json.loads(line)['key']:json.loads(line)['result'].get('page_count_oracle',0) for line in (ROOT/'results/release_0.12.0_evidence_c551/convert_work/jubarte/scores.checkpoint.jsonl').read_text().splitlines() if line.endswith('}')}
 for rel,m in metadata.items():
  if not rel or not m['pdf'] or m['state'] not in ('clean','tracking_without_comments','with_comments_clean','with_comments_tracking'):continue
  path='corpus/word/'+rel
  if path not in allrows:allrows[path]={'state':m['state'],'stem':m['state']+'__'+Path(rel).stem,'docx':path,'word_pdf':'corpus/word/'+m['pdf'],'docx_sha256':MAN['word/'+rel],'word_pdf_sha256':MAN['word/'+m['pdf']]}
 for r in allrows.values():
  r['sets']=metadata[r['docx'].removeprefix('corpus/word/')]['sets'];r['source_pool']=r['sets'].split(';')[0] or 'unknown';r['pages']=pages.get(r['stem'],0);r['page_band']=band(r['pages'])
 return list(allrows.values())

def select_conversion_replacements(failed,used,round_number):
 candidates=conversions();random.Random(20261014+100+round_number).shuffle(candidates);seen={r['docx_sha256'] for r in used};chosen=[];ledger=[]
 for original in failed:
  available=[r for r in candidates if r['docx_sha256'] not in seen and r['state']==original['state']]
  assert available,('No same-state conversion reserve',original['state'])
  def rank(r):
   pool=r['source_pool']==original['source_pool'];page=r['page_band']==original['page_band'];return (pool and page,page,pool)
  best=max(available,key=rank);chosen.append(best);seen.add(best['docx_sha256'])
  ledger.append({'excluded_stem':original['stem'],'replacement_stem':best['stem'],'state':original['state'],'excluded_sha256':original['docx_sha256'],'replacement_sha256':best['docx_sha256'],'source_pool_preserved':best['source_pool']==original['source_pool'],'page_band_preserved':best['page_band']==original['page_band'],'selection_uses_vendor_results':False,'round':round_number,'eligibility_label':'corrupt / rejected by Word','label_scope':'Word oracle eligibility; not proof of malformed OOXML'})
 return chosen,ledger

def stage_conversions(rs,folder):
 with ThreadPoolExecutor(8) as pool:list(pool.map(restore,sorted({r['docx'].removeprefix('corpus/') for r in rs})))
 (folder/'docx').mkdir(parents=True,exist_ok=True)
 for r in rs:
  source=ROOT/r['docx'];assert sha(source)==r['docx_sha256'];dest=folder/'docx'/(r['stem']+'.docx')
  if not dest.exists():shutil.copyfile(source,dest)
  dest.chmod(0o644);assert sha(dest)==r['docx_sha256']
 writecsv(folder/'selection.csv',rs)
 print('Staged',len(rs),'reserve conversions in',folder,flush=True)
