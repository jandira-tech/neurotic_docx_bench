from pathlib import Path
import csv,json,random,hashlib,collections,shutil
from concurrent.futures import ThreadPoolExecutor
from huggingface_hub import HfApi,hf_hub_download
ROOT=Path.cwd(); OUT=ROOT/'results/wordcraft_20261014'; OLD=ROOT/'results/release_0.12.0_evidence_c551'
SEED=20261014
manifest=json.load(open(ROOT/'corpus/MANIFEST.sha256.json'))['files']
repo='arthrod/neurotic_docx_bench-fixtures'; revision=HfApi().dataset_info(repo).sha

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def download(rel):
 dest=ROOT/'corpus'/rel; expected=manifest[rel]
 if not dest.exists() or sha(dest)!=expected:
  src=Path(hf_hub_download(repo,rel,repo_type='dataset',revision=revision)); assert sha(src)==expected,(rel,'hub hash mismatch')
  dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
 assert sha(dest)==expected
 return str(dest)

def sample(rows,quotas):
 rng=random.Random(SEED);chosen=[]
 for state,quota in sorted(quotas.items()):
  cells=collections.defaultdict(list)
  for r in rows:
   if r['state']!=state:continue
   pages=int(r.get('pages',0)); band='1' if pages==1 else '2-4' if 1<pages<=4 else '5-10' if 4<pages<=10 else '11+' if pages>10 else 'unknown'
   r['page_band']=band; r['source_pool']=r.get('sets','').split(';')[0] or 'unknown'
   cells[(r['source_pool'],band)].append(r)
  for items in cells.values():rng.shuffle(items)
  keys=sorted(cells);rng.shuffle(keys);part=[]
  while len(part)<quota:
   before=len(part)
   for key in keys:
    if cells[key] and len(part)<quota:part.append(cells[key].pop())
   assert len(part)>before,('not enough',state,quota)
  chosen.extend(part)
 rng.shuffle(chosen);assert len(chosen)==sum(quotas.values());return chosen

def writecsv(name,rows):
 fields=list(dict.fromkeys(k for r in rows for k in r))
 with (OUT/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
red=list(csv.DictReader(open(OLD/'sample_redline_0.12.0.csv')))
oldred=json.load(open(ROOT/'results/redlines_0929_full/scores_jubarte-0.12.0_sample_redline_0.12.0.json'))['rows']
for r in red:r['pages']=oldred.get(r['key'],{}).get('page_count_oracle',0)
reds=sample(red,{'tracking_without_comments':98,'with_comments_tracking':97,'clean':2,'with_comments_clean':3})
conv=list(csv.DictReader(open(OLD/'sample_conversion_0.12.0.csv')))
docs={r['docx']:r for table in ['documents.csv','comparisons.csv'] for r in csv.DictReader(open(ROOT/'corpus/word'/table))}
oldconv={json.loads(line)['key']:json.loads(line)['result'] for line in open(OLD/'convert_work/jubarte/scores.checkpoint.jsonl') if line.strip()}
for r in conv:
 r['sets']=docs[r['docx'].removeprefix('corpus/word/')]['sets'];r['pages']=oldconv.get(r['stem'],{}).get('page_count_oracle',oldconv.get(r['stem'],{}).get('page_count',0))
convs=sample(conv,{s:50 for s in ['clean','tracking_without_comments','with_comments_clean','with_comments_tracking']})
assert len({r['docx_sha256'] for r in convs})==200
writecsv('comparisons.csv',reds);writecsv('conversions.csv',convs)
needed=set()
for r in reds:
 for field in ['base','next']:needed.add('word/'+r[field]+'.docx')
 for field in ['docx','pdf']:needed.add('word/'+r[field])
for r in convs:
 for field in ['docx','word_pdf']:needed.add(r[field].removeprefix('corpus/'))
print('Restoring',len(needed),'verified files at',revision,flush=True)
with ThreadPoolExecutor(8) as pool:
 for i,_ in enumerate(pool.map(download,sorted(needed)),1):
  if i%50==0:print('downloaded',i,'/',len(needed),flush=True)
provenance={'seed':SEED,'repo':repo,'revision':revision,'n_comparisons':200,'n_conversions':200,'restored_files':len(needed),'states':{label:dict(collections.Counter(r['state'] for r in rows)) for label,rows in [('comparisons',reds),('conversions',convs)]},'cells':{label:dict(collections.Counter(r['state']+'|'+r['source_pool']+'|'+r['page_band'] for r in rows)) for label,rows in [('comparisons',reds),('conversions',convs)]},'manifest_hashes':{rel:manifest[rel] for rel in sorted(needed)}}
for name in ['comparisons.csv','conversions.csv']:provenance[name+'_sha256']=sha(OUT/name)
(OUT/'sample_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
print('Sample frozen and all selected fixture hashes verified',flush=True)
