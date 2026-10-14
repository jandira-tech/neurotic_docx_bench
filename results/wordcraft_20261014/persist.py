from pathlib import Path
import csv,json,uuid,hashlib,statistics,math
from datetime import datetime,UTC
from neurotic_docx_bench.emit.jsonl import build_results_line,append_line
from neurotic_docx_bench.config import BenchConfig,ScoringConfig,RunConfig,CorpusEntry
from neurotic_docx_bench.hardware import hardware_info
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
receipt=OUT/'emission_receipts.json';done=json.load(open(receipt)) if receipt.exists() else {}
meta=json.load(open(OUT/'sample_provenance.json'));tools=json.load(open(OUT/'tools.json'))
ops={}
for line in open(OUT/'operations.jsonl'):
 r=json.loads(line);ops[(r['task'],r['tool'],r['id'])]=r

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def version(tool):
 if tool=='wordcraft':return '0.6.1;sha256:'+tools['wordcraft-cli']['sha256']
 if tool=='jubarte-0.11.0':return '0.11.0;sha256:'+tools['jubarte']['sha256']
 if tool=='docxodus-12.6.5':return 'docxodus@12.6.5'
 return tools.get('soffice',{}).get('version',tool) if tool=='soffice' else tool

def stat(xs):
 xs=sorted(xs)
 def p(q):return xs[max(0,math.ceil(q*len(xs))-1)]
 return {'n':len(xs),'mean':statistics.mean(xs),'median':statistics.median(xs),'p90':p(.9),'p95':p(.95),'p99':p(.99),'min':min(xs),'max':max(xs),'std':statistics.pstdev(xs),'total':sum(xs),'throughput_per_s':1000*len(xs)/sum(xs)}

def main():
 for kind,lane in [('convert','wordcraft'),('convert','soffice'),('compare','wordcraft'),('compare','jubarte-0.11.0'),('compare','docxodus-12.6.5')]:
  file=OUT/kind/lane/'scores.json';key=kind+'|'+lane
  if not file.exists() or key in done:continue
  data=json.load(open(file));assert data['requested']==200;rows=data['rows'];manifest=OUT/('comparisons.csv' if kind=='compare' else 'conversions.csv');docset=digest(manifest);runid=uuid.uuid7();stamp=datetime.now(UTC)
  common={'run_directory':str(OUT),'scorer_fingerprint':data['scorer_fingerprint'],'hub_revision':meta['revision'],'frozen_manifest_sha256':docset}
  if kind=='compare':
   byid={r['id']:r['key'] for r in csv.DictReader(open(manifest))};per={byid[k]:v for k,v in rows.items()};scores={k:v['overall_score_pagefair'] for k,v in per.items()};failures=[{'doc':byid[k],'stage':'render' if v['stage']=='tool_output' else 'generate','error':v['error']} for k,v in data['failures'].items()]
   cfg=BenchConfig(source_of_truth=OUT/'compare/oracle',scoring=ScoringConfig(144),runs=[RunConfig(name=lane,render='word',docx=OUT/'compare'/lane/'docx',vendor=lane,benchmarks=['script_redlines'])],renderer='word',corpora=(CorpusEntry('wordcraft-balanced-200',str(manifest),str(ROOT/'corpus/word')),),config_dir=ROOT)
   timings={byid[k]:{'generate_s':r['elapsed_ms']/1000} for (task,tool,k),r in ops.items() if task=='compare' and tool==lane and k in byid and not r['reused']}
   line=build_results_line(id_run=runid,vendor='wordcraft-cli' if lane=='wordcraft' else lane,benchmark='script_redlines',scores=scores,per_doc=per,speed_samples_ms=[],environment_config=cfg,timestamp=stamp,tool_version=version(lane),config_hash=docset,failures=failures,timings=timings,scorer='pagefair-v2',corpus_revision=meta['revision'],tool_id=lane,configuration=json.dumps(common,sort_keys=True),docset_id=docset[:16],renderer_id='word-16.115',hardware=hardware_info())
   assert line['itt_n_docs']==200,(key,line['itt_n_docs']);append_line(ROOT/'results/bench.jsonl',line);append_line(OUT/'bench.jsonl',line)
  else:
   scores={k:v['overall_score'] for k,v in rows.items()};allkeys=[r['stem'] for r in csv.DictReader(open(manifest))];xs=[scores.get(k,0.0) for k in allkeys]
   line={'source':'converter','id_run':str(runid),'track':'docx_to_pdf','tool':'wordcraft-cli' if lane=='wordcraft' else 'soffice','version':version(lane),'timestamp':stamp.isoformat(),'oracle':'microsoft_word','dpi':144,'docset_id':docset[:16],'lens':'pixel','scorer':'v1','itt_n':200,'n_scored':len(rows),'failures':len(data['failures']),'failed_docs':list(data['failures']),'mean':statistics.mean(xs),'median':statistics.median(xs),'per_doc':scores,'pagefair_mean':statistics.mean(rows.get(k,{}).get('overall_score_pagefair',0) for k in allkeys),'renderer_id':'wordcraft-0.6.1' if lane=='wordcraft' else tools.get('soffice',{}).get('version','soffice'),'hardware':hardware_info(),'configuration':'--markup' if lane=='wordcraft' else 'soffice --headless PDF export',**common}
   append_line(ROOT/'results/converters.jsonl',line);append_line(OUT/'converters.jsonl',line)
  done[key]={'id_run':str(runid),'score_file_sha256':digest(file),'timestamp':stamp.isoformat()};receipt.write_text(json.dumps(done,indent=2)+'\n');print('Appended',key,'run',runid,flush=True)
 for kind,lane,unit in [('compare','wordcraft','ms_per_redline'),('convert','wordcraft','ms_per_render'),('compare','jubarte-0.11.0','ms_per_redline')]:
  key='speed|'+kind+'|'+lane
  if key in done:continue
  selected=[r for (task,tool,_),r in ops.items() if task==kind and tool==lane and r['ok'] and not r['reused']]
  assert len(selected)==200
  line={'schema':1,'kind':'speed','tool':'wordcraft-cli' if lane=='wordcraft' else lane,'tool_version':version(lane),'runtime':'native-cli','run_ts':datetime.now(UTC).isoformat(),'init_ms':None,'failures':0,'unit':unit,'task':kind,'warmup':3,'reps':1,'methodology':'cli_end_to_end_single_pass','includes':'process startup + file open + operation + save','fairness_caveat':'other work active on host; observational latency, not controlled throughput ranking','docset_id':digest(OUT/('comparisons.csv' if kind=='compare' else 'conversions.csv'))[:16],'hardware':hardware_info(),**stat([r['elapsed_ms'] for r in selected])}
  append_line(ROOT/'results/speed.jsonl',line);append_line(OUT/'speed.jsonl',line);done[key]={'timestamp':line['run_ts']};receipt.write_text(json.dumps(done,indent=2)+'\n');print('Appended',key,flush=True)
if __name__=='__main__':main()
