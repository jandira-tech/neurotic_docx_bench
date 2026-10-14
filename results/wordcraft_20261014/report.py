from pathlib import Path
import csv,json,statistics,random,collections,hashlib,sys
from datetime import datetime
from zoneinfo import ZoneInfo
OUT=Path(__file__).resolve().parent
MAN={kind:list(csv.DictReader(open(OUT/name))) for kind,name in [('compare','comparisons.csv'),('convert','conversions.csv')]}

def load(kind,tool):
 folder=OUT/kind/tool;file=folder/'scores.json'
 if file.exists():return json.load(open(file))
 cp=folder/'scores.checkpoint.jsonl';rows={}
 if cp.exists():
  for line in cp.read_text().splitlines():
   if line.endswith('}'):
    v=json.loads(line);rows[v['id']]=v['result']
 failures={}
 for name in ['generate_failures.json','render_failures.json']:
  failure_file=folder/name
  if failure_file.exists():
   for failure in json.load(open(failure_file)):
    if failure['doc'] not in rows:failures[failure['doc']]=failure
 return {'tool':tool,'phase':kind,'requested':200,'scored':len(rows),'rows':rows,'failures':failures,'partial':True}

def summary(data,keys=None):
 rows=data['rows'];keys=keys or [r['id'] if data['phase']=='compare' else r['stem'] for r in MAN[data['phase']]]
 complete=[rows[k] for k in keys if k in rows];finished=not data.get('partial',False)
 denominator=len(keys) if finished else len(complete)
 def mean(field):
  values=[float(r[field]) for r in complete if r.get(field) is not None]
  return statistics.mean(values) if values else None
 xs=[rows[k]['overall_score'] if k in rows else 0 for k in keys] if finished else [r['overall_score'] for r in complete]
 pf=[rows[k]['overall_score_pagefair'] if k in rows else 0 for k in keys] if finished else [r['overall_score_pagefair'] for r in complete]
 return {'requested':len(keys),'scored':len(complete),'failed_or_pending':len(keys)-len(complete),'failed':sum(k in data.get('failures',{}) and k not in rows for k in keys),'pending':max(0,len(keys)-len(complete)-sum(k in data.get('failures',{}) and k not in rows for k in keys)) if not finished else 0,'partial':not finished,'v1_mean':statistics.mean(xs) if xs else None,'v1_median':statistics.median(xs) if xs else None,'pagefair_mean':statistics.mean(pf) if pf else None,'successful_only_mean':mean('overall_score'),'successful_only_pagefair_mean':mean('overall_score_pagefair'),'page_mismatches':sum(bool(r['page_count_mismatch']) for r in complete),'at_least_90':sum(v>=90 for v in xs),'below_50':sum(v<50 for v in xs),'ink_jaccard_mean_success':mean('ink_jaccard'),'text_boundary_mean_success':mean('text_boundary'),'max_break_drift_max':max((r.get('max_break_drift') or 0 for r in complete),default=0)}

def paired(reference,other,field,include_failures=True):
 keys=[r['id'] if reference['phase']=='compare' else r['stem'] for r in MAN[reference['phase']]]
 if not include_failures:keys=[k for k in keys if k in reference['rows'] and k in other['rows']]
 elif reference.get('partial') or other.get('partial'):keys=[k for k in keys if k in reference['rows'] and k in other['rows']]
 diff=[other['rows'].get(k,{}).get(field,0)-reference['rows'].get(k,{}).get(field,0) for k in keys]
 if not diff:return None
 rng=random.Random(20261014);boots=sorted(statistics.mean(rng.choices(diff,k=len(diff))) for _ in range(2000))
 return {'n':len(diff),'metric':field,'other_minus_wordcraft':statistics.mean(diff),'bootstrap_95_ci':[boots[50],boots[1949]],'other_wins_gt_0.5':sum(v>.5 for v in diff),'wordcraft_wins_gt_0.5':sum(v<-.5 for v in diff),'ties_within_0.5':sum(abs(v)<=.5 for v in diff)}

def main():
 required={'compare':['wordcraft','jubarte-0.11.0','docxodus-12.6.5'],'convert':['wordcraft','jubarte-0.12.0-c551','soffice']}
 data={kind:{tool:load(kind,tool) for tool in tools} for kind,tools in required.items()};full=all(not v.get('partial') for group in data.values() for v in group.values())
 if '--final' in sys.argv:assert full,'Do not publish an incomplete report as final'
 overview={'complete':full,'sample_provenance':json.load(open(OUT/'sample_provenance.json')),'tools':json.load(open(OUT/'tools.json')),'summary':{},'paired':{},'strata':{}}
 lines=['# Wordcraft CLI benchmark — '+('complete' if full else 'partial'),'', 'Updated: '+datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %H:%M:%S %Z')+'.', '', 'Fixed seed 20261014. 200 unique base→next comparisons from 11 pools; 200 distinct conversion DOCX, 50 per document state. The sample was frozen before running Wordcraft.','', 'Comparison redlines are rendered by Word 16.115. All tools in each task use identical per-fixture Word PDF oracles, 144 DPI and the unchanged NumPy scorer. Full-cohort means include tool failures as zero. Partial means include only completed scores and can be biased toward faster documents.','']
 rowscsv=[]
 latest_ops={}
 for line in open(OUT/'operations.jsonl'):
  op=json.loads(line);latest_ops[(op['task'],op['tool'],op['id'])]=op
 def latency(kind,tool):
  aliases=['docxodus','docxodus-12.6.5'] if tool=='docxodus-12.6.5' else [tool]
  measured={}
  for (task,lane,key),op in latest_ops.items():
   if task==kind and lane in aliases and op['ok'] and not op['reused']:measured[key]=op['elapsed_ms']
  return statistics.median(measured.values()) if measured else None
 for kind,group in data.items():
  overview['summary'][kind]={tool:summary(v) for tool,v in group.items()};overview['paired'][kind]={};overview['strata'][kind]={}
  lines.extend(['## '+('Comparisons' if kind=='compare' else 'Conversions'),'','| Tool | Scored / 200 | Failed | Pending | Mean v1 | Mean pagefair | Median v1 | Median CLI latency (ms) | Page mismatches |','|---|---:|---:|---:|---:|---:|---:|---:|---:|'])
  for tool,v in group.items():
   s=overview['summary'][kind][tool]
   def fmt(x):return f'{x:.2f}' if x is not None else '—'
   label=tool+(' (partial)' if s['partial'] else '')
   lines.append(f"| {label} | {s['scored']} | {s['failed']} | {s['pending']} | {fmt(s['v1_mean'])} | {fmt(s['pagefair_mean'])} | {fmt(s['v1_median'])} | {fmt(latency(kind,tool))} | {s['page_mismatches']} |")
  lines.append('')
  lines.append('CLI latency includes startup, file loading and saving; Word export is excluded from comparison latency. Docxodus includes WASM initialization and was measured amid concurrent scoring, so its latency is observational. A blank median means it was not measured for that exact build and cohort.')
  lines.append('')
  ref=group['wordcraft']
  for tool,v in group.items():
   if tool=='wordcraft':continue
   entry={mode:paired(ref,v,field,itt) for mode,field,itt in [('itt_v1','overall_score',True),('itt_pagefair','overall_score_pagefair',True),('common_success_v1','overall_score',False),('common_success_pagefair','overall_score_pagefair',False)]};overview['paired'][kind][tool]=entry
   pf=entry['itt_pagefair']
   if pf:lines.append(f"{tool} minus Wordcraft, pagefair: **{pf['other_minus_wordcraft']:+.2f} points**, paired bootstrap 95% interval [{pf['bootstrap_95_ci'][0]:+.2f}, {pf['bootstrap_95_ci'][1]:+.2f}], n={pf['n']}. This interval describes the selected benchmark cohort, not a population-wide guarantee.")
  lines.append('')
  for field in ['state','source_pool','page_band']:
   buckets=collections.defaultdict(list)
   for r in MAN[kind]:buckets[r[field]].append(r['id'] if kind=='compare' else r['stem'])
   overview['strata'][kind][field]={label:{tool:summary(v,keys) for tool,v in group.items()} for label,keys in buckets.items()}
  lines.extend(['### By state','','| State | N | '+ ' | '.join(group)+' |','|---|---:|'+ '|'.join('---:' for _ in group)+'|'])
  for state,by in overview['strata'][kind]['state'].items():
   n=next(iter(by.values()))['requested'];lines.append('| '+state+' | '+str(n)+' | '+' | '.join(fmt(s['pagefair_mean']) for s in by.values())+' |')
  lines.append('')
  for r in MAN[kind]:
   key=r['id'] if kind=='compare' else r['stem']
   for tool,v in group.items():
    score=v['rows'].get(key,{})
    rowscsv.append({'task':kind,'tool':tool,'key':key,'state':r['state'],'source_pool':r['source_pool'],'page_band':r['page_band'],'scored':key in v['rows'],**{k:score.get(k) for k in ['overall_score','overall_score_pagefair','page_count_oracle','page_count_candidate','page_count_mismatch','ink_jaccard','text_boundary','max_break_drift']}})
 ops={}
 for line in open(OUT/'operations.jsonl'):
  r=json.loads(line);ops[(r['task'],r['tool'],r['id'])]=r
 overview['timing']={}
 for task,tool in [('compare','wordcraft'),('convert','wordcraft'),('compare','jubarte-0.11.0')]:
  xs=sorted(r['elapsed_ms'] for r in ops.values() if r['task']==task and r['tool']==tool and r['ok'] and not r['reused']);overview['timing'][task+'|'+tool]={'n':len(xs),'unit':'ms_per_cli_invocation','mean':statistics.mean(xs),'median':statistics.median(xs),'p95':xs[max(0,int(.95*len(xs))-1)],'min':min(xs),'max':max(xs),'startup_open_save_included':True,'warmups_excluded':3}
 lines.extend(['## Timing and limits','', 'Observed Wordcraft CLI medians: comparison '+f"{overview['timing']['compare|wordcraft']['median']:.2f} ms"+', conversion '+f"{overview['timing']['convert|wordcraft']['median']:.2f} ms"+'. Each invocation includes process startup, file loading and saving. Three warmups per lane were excluded. Timing is a single-pass observation; other work was active on the machine, and the Docxodus wrapper includes WASM initialization. Do not treat these numbers as a rigorous throughput ranking.','', 'The primary conversion command uses `--markup`, matching Word oracle PDFs that display comments and tracked changes. Wordcraft comparison uses word granularity with formatting/case/whitespace differences enabled. Unsupported Wordcraft compare options are documented in its own CLI command catalog.','', 'Jubarte 0.12.0 c551 conversion fidelity reuses historical rows only after verifying fixture and oracle SHA256 and the same scorer fingerprint. No fresh speed measurement is claimed for that build. LibreOffice conversions and jubarte 0.11.0/Docxodus 12.6.5 comparison baselines are freshly generated for this sample.','', 'Wordcraft redline export: 190 readable, 10 rejected as unreadable after two Word attempts. Existing Word oracles were reused; scripts/word_redline.py refreshed 4 of 8 audited comparisons, while 4 produced Word scripting errors and retained their verified saved oracle. No fixture was substituted after a failure.','', 'Both raw v1 and pagefair are reported. The raw scorer compares shared pages; pagefair additionally accounts for extra or missing pages. Failure-aware means and common-success paired comparisons distinguish tool failure from fidelity among readable outputs.','', 'This is a balanced stress sample, not a frequency-weighted estimate of the full corpus. All 200 comparison input pairs and all 200 conversion content hashes are distinct.','', 'Rasters are discarded after each scored document. DOCX, PDF, manifests, logs and score checkpoints are retained. Scorer parity validation: 5 passed; focused coverage 58.6% lines and 71.2% branches.','', '## Evidence','', '- `comparisons.csv`, `conversions.csv`, `sample_provenance.json`: frozen selection, seed, hub revision and hashes.','- `tools.json`, `oracle_provenance.json`, `pdf_preset.txt`: exact binaries, Word version and oracle sources.','- `operations.jsonl`: invocation, timing, exit status, revision XML and output hashes.','- Per-tool `scores.json` and `scores.checkpoint.jsonl`: full metrics and resumable progress.','- `wordcraft_word_pdf.out`, `jubarte_word_pdf.out`, `word_audit/word_redline.out`, `word_screen.log`: Word outputs and exact alerts.','- `feature_distribution.json`, `actual_page_distribution.json`: corpus complexity and reference page counts.',''])
 name='REPORT' if full else 'PARTIALS';(OUT/(name+'.md')).write_text('\n'.join(lines));(OUT/(name+'.json')).write_text(json.dumps(overview,indent=2,default=str)+'\n')
 with (OUT/'per_document.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rowscsv[0]));w.writeheader();w.writerows(rowscsv)
 print('Wrote',name,'complete=',full,flush=True)
if __name__=='__main__':main()
