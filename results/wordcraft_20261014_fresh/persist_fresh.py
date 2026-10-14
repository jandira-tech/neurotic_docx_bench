"""Emit the completed fresh cohort through canonical append-only result schemas."""
from pathlib import Path
import csv,json,uuid,hashlib,statistics,math
from datetime import datetime,UTC
from neurotic_docx_bench.emit.jsonl import build_results_line,append_line
from neurotic_docx_bench.config import BenchConfig,ScoringConfig,RunConfig,CorpusEntry
from neurotic_docx_bench.hardware import hardware_info
from neurotic_docx_bench import version as bench_version
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def stat(xs):
 xs=sorted(xs)
 def percentile(q):return xs[max(0,math.ceil(q*len(xs))-1)]
 return {'n':len(xs),'mean':statistics.mean(xs),'median':statistics.median(xs),'p90':percentile(.9),'p95':percentile(.95),'p99':percentile(.99),'min':min(xs),'max':max(xs),'std':statistics.pstdev(xs),'total':sum(xs),'throughput_per_s':1000*len(xs)/sum(xs)}
def main():
 ready=json.loads((OUT/'ORACLES_READY.json').read_text());meta=json.loads((OUT/'sample_provenance.json').read_text());tools=json.loads((OUT/'tools.json').read_text())
 receipts=OUT/'emission_receipts.json';done=json.loads(receipts.read_text()) if receipts.exists() else {};ops={}
 for line in (OUT/'operations.jsonl').read_text().splitlines():
  r=json.loads(line);ops[(r['task'],r['tool'],r['id'])]=r
 def version(tool):
  if tool=='wordcraft':return '0.6.1@'+tools['wordcraft-cli']['sha256']
  if tool.startswith('jubarte-'):return tool.removeprefix('jubarte-')+'@'+tools[tool]['sha256']
  if tool.startswith('docxodus-'):return '12.6.5'
  return tools['soffice']['version']
 required={'compare':['wordcraft','jubarte-0.11.0','jubarte-0.12.0','docxodus-12.6.5'],'convert':['wordcraft','jubarte-0.11.0','jubarte-0.12.0','soffice']}
 for phase,lanes in required.items():
  manifest=OUT/('comparisons.csv' if phase=='compare' else 'conversions.csv');assert digest(manifest)==ready['final_manifest_sha256'][manifest.name]
  manifest_rows=list(csv.DictReader(manifest.open()));n=len(manifest_rows);ids=[r['id'] if phase=='compare' else r['stem'] for r in manifest_rows];docset=digest(manifest)[:16]
  for lane in lanes:
   key=phase+'|'+lane;file=OUT/phase/lane/'scores.json';data=json.loads(file.read_text());assert data['requested']==n
   rows=data['rows'];fail=data['failures'];assert set(rows).isdisjoint(fail) and set(rows)|set(fail)==set(ids),(lane,'Incomplete cohort')
   if key in done:assert done[key]['score_file_sha256']==digest(file);continue
   selected=[r for (task,tool,ident),r in ops.items() if task==phase and tool==lane and ident in ids and r['ok'] and not r['reused']];samples=[r['elapsed_ms'] for r in selected]
   stamp=datetime.now(UTC);runid=uuid.uuid7();common={'run_directory':str(OUT),'scorer_fingerprint':data['scorer_fingerprint'],'hub_revision':meta['revision'],'frozen_manifest_sha256':digest(manifest),'fresh_word_oracle_provenance_sha256':digest(OUT/'oracle_provenance.json'),'fresh':True,'fixture_selection':'Word eligibility established before vendor generation; vendor failures retained','candidate_options':'Wordcraft --markup; jubarte --revisions word' if phase=='convert' else 'Wordcraft level=word formatting/case/whitespace=true; native compares for other tools'}
   config_hash=hashlib.sha256(json.dumps(common,sort_keys=True).encode()).hexdigest();name='wordcraft-cli' if lane=='wordcraft' else lane
   if phase=='compare':
    byid={r['id']:r['key'] for r in manifest_rows};per={byid[k]:v for k,v in rows.items()};scores={k:v['overall_score_pagefair'] for k,v in per.items()};failures=[{'doc':byid[k],'stage':'render' if v['stage'] in ('tool_output','score') else 'generate','error':v['error']} for k,v in fail.items()]
    cfg=BenchConfig(source_of_truth=OUT/'compare/oracle',scoring=ScoringConfig(144),runs=[RunConfig(name=lane,render='word',docx=OUT/'compare'/lane/'docx',vendor=name,benchmarks=['script_redlines'])],renderer='word',corpora=(CorpusEntry('wordcraft-balanced-'+str(n),str(manifest),str(ROOT/'corpus/word')),),config_dir=ROOT)
    timings={byid[k]:{'generate_s':r['elapsed_ms']/1000} for (task,tool,k),r in ops.items() if task==phase and tool==lane and k in byid and not r['reused']}
    line=build_results_line(id_run=runid,vendor=name,benchmark='script_redlines',scores=scores,per_doc=per,speed_samples_ms=samples,environment_config=cfg,timestamp=stamp,tool_version=version(lane),config_hash=config_hash,failures=failures,timings=timings,scorer='pagefair-v2',corpus_revision=meta['revision'],tool_id=name,configuration=json.dumps(common,sort_keys=True),docset_id=docset,renderer_id='word-16.115',hardware=hardware_info())
    assert line['itt_n_docs']==n;append_line(OUT/'bench.jsonl',line)
   else:
    scores={k:v['overall_score'] for k,v in rows.items()};xs=[scores.get(k,0.0) for k in ids]
    line={'source':'converter','id_run':str(runid),'track':'docx_to_pdf','tool':name,'version':version(lane),'timestamp':stamp.isoformat(),'oracle':'microsoft_word','dpi':144,'docset_id':docset,'lens':'pixel','scorer':'v1','itt_n':n,'n_scored':len(rows),'failures':len(fail),'failed_docs':list(fail),'mean':statistics.mean(xs),'median':statistics.median(xs),'scores':scores,'perfects':sum(x==100 for x in xs),'pagefair_mean':statistics.mean(rows.get(k,{}).get('overall_score_pagefair',0) for k in ids),'renderer_id':'oracle:microsoft_word-16.115','hardware':hardware_info(),'bench_version':bench_version.bench_version(),'configuration':common['candidate_options'],**common}
    append_line(OUT/'converters.jsonl',line)
   done[key]={'id_run':str(runid),'score_file_sha256':digest(file),'timestamp':stamp.isoformat()};receipts.write_text(json.dumps(done,indent=2)+'\n')
   speed_key='speed|'+key
   if samples and speed_key not in done:
    speed={'schema':1,'kind':'speed','tool':name,'tool_version':version(lane),'runtime':'native-cli','run_ts':stamp.isoformat(),'init_ms':None,'failures':sum(not r['ok'] for (task,tool,_),r in ops.items() if task==phase and tool==lane),'unit':'ms_per_redline' if phase=='compare' else 'ms_per_render','task':phase,'warmup':3,'reps':1,'methodology':'cli_end_to_end_single_pass','includes':'process startup + file open + operation + save','fairness_caveat':'Timed lanes serial with no own scoring or Word batch active; unrelated host activity uncontrolled; single pass','docset_id':docset,'hardware':hardware_info(),**stat(samples)}
    append_line(OUT/'speed.jsonl',speed);done[speed_key]={'timestamp':stamp.isoformat()};receipts.write_text(json.dumps(done,indent=2)+'\n')
   print('Emitted',key,'scored',len(rows),'failed',len(fail),'median CLI ms',statistics.median(samples) if samples else None,flush=True)
 print('Completed cohort result stores emitted; publication appends these fresh lines only',flush=True)
if __name__=='__main__':main()
