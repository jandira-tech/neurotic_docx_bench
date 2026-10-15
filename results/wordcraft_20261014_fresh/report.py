from pathlib import Path
import csv,json,statistics,random,collections,hashlib,sys
from datetime import datetime
from zoneinfo import ZoneInfo
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT))
import lanes
MAN={kind:list(csv.DictReader(open(OUT/name))) for kind,name in [('compare','comparisons.csv'),('convert','conversions.csv')]}

def failure_kinds():
 """Per comparison tool: generate failures plus the Word export failure reason from word_pdf logs."""
 import re
 out={}
 for t in lanes.COMPARE:
  folder=OUT/'compare'/t;ids={r['id'] for r in MAN['compare']}
  gen=[r for r in json.load(open(folder/'generate_failures.json')) if r['doc'] in ids] if (folder/'generate_failures.json').exists() else []
  ren={r['doc'] for r in json.load(open(folder/'render_failures.json'))} if (folder/'render_failures.json').exists() else set()
  last={}
  for name in ['word_pdf.log','word_pdf_retry.log']:
   if (folder/name).exists():
    for m in re.finditer(r'\[batch\] FAIL: (\S+)\.docx — (.*)',(folder/name).read_text()):last[m.group(1)]=m.group(2)
  c=collections.Counter()
  for g in gen:c['generation timed out' if 'timed out' in str(g.get('error','')) else 'generation failed']+=1
  for d in ren:
   e=last.get(d,'')
   c['loaded empty in Word' if 'loaded empty' in e else 'crashed Word' if 'Connection is invalid' in e else 'Word AppleEvent timeout' if 'timed out' in e else 'Word export failed without an error text']+=1
  out[t]=f"{sum(c.values())} ("+', '.join(f'{v} {k}' for k,v in c.most_common())+')' if c else '0'
 return out

def generation_reasons(minimum=20):
 """The vendors' own refusal messages behind most generation failures (top three per comparison tool)."""
 import re
 out={}
 for t in lanes.COMPARE:
  f=OUT/'compare'/t/'generate_failures.json'
  if not f.exists():continue
  ids={r['id'] for r in MAN['compare']};gen=[r for r in json.load(open(f)) if r['doc'] in ids]
  if len(gen)<minimum:continue
  c=collections.Counter()
  for g in gen:
   e=re.sub(r'/(?:var|Users|private)/\S+','<path>',str(g.get('error','')))
   hits=re.findall(r'((?:\w*Error\w*|UnsupportedEdit|ValidationFailed|InvalidDocx)[:\]]? [^\n]+)',e)
   msg='timed out' if 'timed out' in e and not hits else (hits[-1] if hits else e.strip().splitlines()[-1] if e.strip() else 'no message')
   msg=re.sub(r'\d+','N',msg.split(': ',1)[-1] if 'GenerateRedlineDocx' in msg or 'SuperDocError' in msg else msg)
   msg=re.sub(r'^.*?UnsupportedEdit: ','',msg).split(' No mutation')[0].split('. For a')[0][:150].rstrip(' .,')
   c[msg]+=1
  out[t]=(len(gen),c.most_common(3))
 return out

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
 return {'tool':tool,'phase':kind,'requested':len(lanes.keys_for(kind,tool,[r['id'] if kind=='compare' else r['stem'] for r in MAN[kind]])),'scored':len(rows),'rows':rows,'failures':failures,'partial':True}

def summary(data,keys=None):
 rows=data['rows'];keys=lanes.keys_for(data['phase'],data['tool'],keys if keys is not None else [r['id'] if data['phase']=='compare' else r['stem'] for r in MAN[data['phase']]])
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
 keys=lanes.keys_for(reference['phase'],other['tool'],lanes.keys_for(reference['phase'],reference['tool'],keys))
 if not include_failures:keys=[k for k in keys if k in reference['rows'] and k in other['rows']]
 elif reference.get('partial') or other.get('partial'):keys=[k for k in keys if k in reference['rows'] and k in other['rows']]
 diff=[other['rows'].get(k,{}).get(field,0)-reference['rows'].get(k,{}).get(field,0) for k in keys]
 if not diff:return None
 rng=random.Random(20261014);boots=sorted(statistics.mean(rng.choices(diff,k=len(diff))) for _ in range(2000))
 return {'n':len(diff),'metric':field,'other_minus_wordcraft':statistics.mean(diff),'bootstrap_95_ci':[boots[50],boots[1949]],'other_wins_gt_0.5':sum(v>.5 for v in diff),'wordcraft_wins_gt_0.5':sum(v<-.5 for v in diff),'ties_within_0.5':sum(abs(v)<=.5 for v in diff)}

def fmt(x):return f'{x:.2f}' if x is not None else '—'

def main():
 required=lanes.LANES
 data={kind:{tool:load(kind,tool) for tool in tools} for kind,tools in required.items()};full=all(not v.get('partial') for group in data.values() for v in group.values())
 if '--final' in sys.argv:assert full,'Do not publish an incomplete report as final'
 overview={'complete':full,'sample_provenance':json.load(open(OUT/'sample_provenance.json')),'tools':json.load(open(OUT/'tools.json')),'summary':{},'paired':{},'strata':{}}
 lines=['# Wordcraft CLI benchmark — '+('complete' if full else 'partial'),'', 'Updated: '+datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %H:%M:%S %Z')+'.', '', 'Seed 20261014. '+str(len(MAN['compare']))+' unique base→next comparisons and '+str(len(MAN['convert']))+' distinct conversion DOCX, in two cohorts: the original 200+200 sample and a seeded, stratified expansion drawn before any vendor ran. Word eligibility is established first: a fixture for which Word could not produce a fresh oracle in this run is excluded and logged (`comparison_exclusions.json`, `conversion_exclusions.json`); Word-session failures were retried, not excluded. Inputs are frozen before vendor generation; vendor failures are never replaced and count as zero.','','Comparison redlines are rendered by Word 16.115. All tools in each task use identical per-fixture Word PDF oracles, 144 DPI and the unchanged scorer. Its two kernels (mean CIEDE2000 and SSIM) ran on NumPy for the rows scored early and on the torch port over Apple MPS for the rest (`BENCH_DEVICE=mps`); `tests/test_kernels.py` holds the torch port within 1e-3 of NumPy per document (15 passed on this machine), and every scored row records its `scorer_backend` (counts below). Full-cohort means include tool failures as zero. Partial means include only completed scores and can be biased toward faster documents.','']
 lines.extend(['Lanes. The original run: Wordcraft CLI 0.6.1, jubarte 0.11.0 and 0.12.0, and docxodus 12.6.5 (comparisons) or LibreOffice 26.8.1.1 (conversions). Added the same day, on the same frozen fixtures, oracles, renderer and scorer, at their newest releases: the top three non-jubarte tools of every past results table in RESULTS.md (comparisons: docxodus, stemma, folio, superdoc; conversions: office2pdf, pdfitdown, rdocx, libreoffice_convert_rust, docxide-pdf, PyMuPDF Pro, with LibreOffice already present), plus Wordcraft CLI 0.7.0 and docxodus 13.0.0, released while this run was in progress. Each tool runs through the bench\'s own adapter for it, one document per process; exact versions and hashes are in `tools.json`. libreoffice_convert_rust drives the installed /Applications/LibreOffice.app, the same LibreOffice build as the soffice lane, so the two score alike. jubarte is author-affiliated.',''])
 rowscsv=[]
 latest_ops={}
 for line in (OUT/'operations.jsonl').read_text().splitlines() if (OUT/'operations.jsonl').exists() else []:
  op=json.loads(line);latest_ops[(op['task'],op['tool'],op['id'])]=op
 ids_of={kind:{r['id'] if kind=='compare' else r['stem'] for r in MAN[kind]} for kind in MAN}
 def latency(kind,tool):
  aliases=['docxodus','docxodus-12.6.5'] if tool=='docxodus-12.6.5' else [tool]
  measured={}
  for (task,lane,key),op in latest_ops.items():
   if task==kind and lane in aliases and key in ids_of[kind] and op['ok'] and not op['reused']:measured[key]=op['elapsed_ms']
  return statistics.median(measured.values()) if measured else None
 for kind,group in data.items():
  overview['summary'][kind]={tool:summary(v) for tool,v in group.items()};overview['paired'][kind]={};overview['strata'][kind]={}
  lines.extend(['## '+('Comparisons' if kind=='compare' else 'Conversions'),'','| Tool | Scored / '+str(len(MAN[kind]))+' | Failed | Pending | Mean v1 | Mean pagefair | Median v1 | Median CLI latency (ms) | Page mismatches |','|---|---:|---:|---:|---:|---:|---:|---:|---:|'])
  for tool,v in group.items():
   s=overview['summary'][kind][tool]
   label=tool+(' (partial)' if s['partial'] else '')+(f" (≤3-page subset, n={s['requested']})" if tool in lanes.LE3_ONLY else '')
   lines.append(f"| {label} | {s['scored']} | {s['failed']} | {s['pending']} | {fmt(s['v1_mean'])} | {fmt(s['pagefair_mean'])} | {fmt(s['v1_median'])} | {fmt(latency(kind,tool))} | {s['page_mismatches']} |")
  lines.append('')
  lines.append('CLI latency includes startup, file loading and saving; Word export is excluded from comparison latency. Docxodus includes WASM initialization. Each tool lane ran serially, one document at a time, but on a shared machine: Word batches, scoring and other sessions were running (load average 35–77 on 12 cores), and the lanes added later ran concurrently with each other and with cargo builds of the Rust converters, so latencies are observations, not a throughput ranking.'+('' if full else ' A blank median means it has not yet been measured for this build and cohort.'))
  backends={tool:collections.Counter(r.get('scorer_backend','numpy') for k,r in group[tool]['rows'].items() if k in ids_of[kind]) for tool in group}
  lines.extend(['','Scorer backend per tool (scored rows): '+'; '.join(f"{t}: "+', '.join(f'{b} {n}' for b,n in sorted(c.items())) for t,c in backends.items())+'.'])
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
  if 'cohort' in MAN[kind][0]:
   buckets=collections.defaultdict(list)
   for r in MAN[kind]:buckets['cohort '+r['cohort']].append(r['id'] if kind=='compare' else r['stem'])
   overview['strata'][kind]['cohort']={label:{tool:summary(v,keys) for tool,v in group.items()} for label,keys in sorted(buckets.items())}
   lines.extend(['### By cohort (pagefair mean, failures as zero)','','| Cohort | N | '+' | '.join(group)+' |','|---|---:|'+'|'.join('---:' for _ in group)+'|'])
   for label,by in overview['strata'][kind]['cohort'].items():
    lines.append('| '+label+' | '+str(next(iter(by.values()))['requested'])+' | '+' | '.join(fmt(s['pagefair_mean']) for s in by.values())+' |')
   lines.append('')
  for old_tool,new_tool in lanes.TRANSITIONS:
   a,b=group.get(old_tool),group.get(new_tool)
   if not(a and b and not a.get('partial') and not b.get('partial')):continue
   keys=[r['id'] if kind=='compare' else r['stem'] for r in MAN[kind]];t=collections.Counter((k in a['rows'],k in b['rows']) for k in keys)
   d=[b['rows'][k]['overall_score_pagefair']-a['rows'][k]['overall_score_pagefair'] for k in keys if k in a['rows'] and k in b['rows']]
   j={'both_ok':t[(True,True)],'fixed':t[(False,True)],'broken':t[(True,False)],'both_failed':t[(False,False)],'common_success_pagefair_delta_mean':statistics.mean(d) if d else None,'improved_gt_0.5':sum(x>.5 for x in d),'regressed_gt_0.5':sum(x<-.5 for x in d)}
   overview.setdefault('transitions',{}).setdefault(kind,{})[f'{old_tool}->{new_tool}']=j
   lines.extend([f'### {old_tool} → {new_tool}','',f"Failure transitions: {j['both_ok']} scored by both, {j['fixed']} failed in the old version and scored in the new, {j['broken']} scored in the old and failed in the new, {j['both_failed']} failed in both. On the documents both scored, new minus old pagefair averages {fmt(j['common_success_pagefair_delta_mean'])} points ({j['improved_gt_0.5']} improved, {j['regressed_gt_0.5']} regressed by more than 0.5).",''])
  if kind=='convert':
   sub=lanes.le3_ids();overview['le3_subset']={tool:summary(v,sub) for tool,v in group.items()}
   lines.extend([f'### Conversions whose Word PDF has at most 3 pages (n={len(sub)})','','Every conversion tool on the same subset, so PyMuPDF Pro (unlicensed: it converts only the first 3 pages) is compared like for like. Pagefair mean, failures as zero.','','| Tool | Scored / '+str(len(sub))+' | Mean pagefair | Median v1 |','|---|---:|---:|---:|'])
   for tool,s2 in sorted(overview['le3_subset'].items(),key=lambda kv:-(kv[1]['pagefair_mean'] or 0)):lines.append(f"| {tool} | {s2['scored']} | {fmt(s2['pagefair_mean'])} | {fmt(s2['v1_median'])} |")
   lines.append('')
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
 for line in (OUT/'operations.jsonl').read_text().splitlines() if (OUT/'operations.jsonl').exists() else []:
  r=json.loads(line);ops[(r['task'],r['tool'],r['id'])]=r
 overview['timing']={}
 keys={'compare':{r['id'] for r in MAN['compare']},'convert':{r['stem'] for r in MAN['convert']}}
 for task,tool in [(k,t) for k,ts in lanes.LANES.items() for t in ts]:
  xs=sorted(r['elapsed_ms'] for r in ops.values() if r['task']==task and r['tool']==tool and r['id'] in keys[task] and r['ok'] and not r['reused']);
  if not xs:continue
  overview['timing'][task+'|'+tool]={'n':len(xs),'unit':'ms_per_cli_invocation','mean':statistics.mean(xs),'median':statistics.median(xs),'p95':xs[max(0,int(.95*len(xs))-1)],'min':min(xs),'max':max(xs),'startup_open_save_included':True,'warmups_excluded':3}
 lines.extend(['## Timing and limits','', 'Observed Wordcraft CLI medians: comparison '+f"{overview['timing'].get('compare|wordcraft',{}).get('median',float('nan')):.2f} ms"+', conversion '+f"{overview['timing'].get('convert|wordcraft',{}).get('median',float('nan')):.2f} ms"+'. Each invocation includes process startup, file loading and saving. Three warmups per lane were excluded. Timing is a single-pass observation; other work was active on the machine, and the Docxodus wrapper includes WASM initialization. Do not treat these numbers as a rigorous throughput ranking.','', *(['Per-lane CLI latency over the frozen rows (last attempt per document; a timeout is the 120 s per-call limit):','',__import__('speed_table').table(),''] if full else []), *(['Why vendor redlines failed (counted as zero): '+'; '.join(f"{t}: {n}" for t,n in failure_kinds().items())+'. "Loaded empty" means Word refused the vendor DOCX in both fresh sessions with "Word experienced an error trying to open the file" (for some docxodus files after an "unreadable content" repair prompt, answered No); the alert text is in compare/<tool>/word_pdf*.log. "Crashed Word" means Word quit on it in both sessions.',''] if full else []), *(['Most generation failures are the vendor refusing the pair, in its own words (top three messages, digits as N): '+'; '.join(f"{t} ({n}): "+', '.join(f'{k!r} ×{v}' for k,v in top) for t,(n,top) in generation_reasons().items())+'. stemma 0.6.0 fails more pairs than 0.5.0 did on the same 400 (292 against 104), and its failures are explicit refusals (`UnsupportedEdit`), where the 0.5.0 failures were validation and invalid-package errors; 0.5.0 is not a lane here because 0.6.0 is the newest release; folio-cli 0.5.1 `compare -o` calls the same folio-core `generateRedlineDocx` and produced part-for-part identical output on three probe pairs (`folio_cli_probe/`).',''] if full else []), 'The primary conversion command uses `--markup`, matching Word oracle PDFs that display comments and tracked changes. Wordcraft comparison uses word granularity with formatting/case/whitespace differences enabled. Unsupported Wordcraft compare options are documented in its own CLI command catalog.','', 'All reported vendor outputs, Word references and scores are freshly generated in this run. Official jubarte 0.11.0 and 0.12.0 release archives are verified against their SHA256SUMS. No historical scores or candidate/reference PDFs are reused.','', 'Word redlines and all Word oracle PDF exports are made by invoking the repository scripts/word_redline.py and scripts/word_pdf.py directly (hashes in `oracle_provenance.json` and `word_400/driver_invocations.jsonl`); every vendor redline Word could not export gets one retry in a fresh Word session, the same rule for every tool. Word-oracle exclusions and their replacements are recorded before vendor generation; no fixture is substituted after a vendor failure.','', 'Both raw v1 and pagefair are reported. The raw scorer compares shared pages; pagefair additionally accounts for extra or missing pages. Failure-aware means and common-success paired comparisons distinguish tool failure from fidelity among readable outputs.','', 'This is a balanced stress sample, not a frequency-weighted estimate of the full corpus. All '+str(len(MAN['compare']))+' comparison input pairs and all '+str(len(MAN['convert']))+' conversion content hashes are distinct. The corpus holds only 174 distinct with_comments_tracking, 3 with_comments_clean and 2 clean comparison pairs, so comparisons take every Word-eligible pair of those states and tracking_without_comments fills the rest.','', 'Rasters are discarded after each scored document. DOCX, PDF, manifests, logs and score checkpoints are retained.','', '## Evidence','', '- `comparisons.csv`, `conversions.csv`, `sample_provenance.json`: frozen selection, seed, hub revision and hashes.','- `tools.json`, `oracle_provenance.json`, `ORACLES_READY.json`: exact binaries, Word version, the committed driver hashes (`drivers_ee49054d/`) and the source of every oracle.','- `comparison_exclusions.json`, `conversion_exclusions.json`, `word_400/selection.json`, `word_400/candidates_*.csv`: Word-ineligible fixtures with every attempt, and the seeded reserve order.','- `word_400/driver_invocations.jsonl` and `word_400/*/driver.log`: every Word batch (command, driver hash, exclusive-Word flag, PDFs produced) and its alerts; `word_400/contaminated/`: batches aborted because another session touched Word, rerun from scratch.','- `operations.jsonl`: invocation, timing, exit status, revision XML and output hashes.','- `compare/<tool>/word_pdf.log`, `render_retry.json`, `render_failures.json`, `generate_failures.json`: vendor redline export by Word and every failure.','- Per-tool `scores.json` and `scores.checkpoint.jsonl`: full metrics (with `scorer_backend`) and resumable progress.',''])
 eligibility=OUT/'oracle_eligibility_progress.json'
 if eligibility.exists() and not full:  # a pre-expansion snapshot; the final report points to ORACLES_READY.json
  overview['oracle_eligibility']=json.load(open(eligibility));lines.extend(['## Fresh Word oracle preparation','',*['- '+k+': '+str(v) for k,v in overview['oracle_eligibility'].items()],''])
 name='REPORT' if full else 'PARTIALS';(OUT/(name+'.md')).write_text('\n'.join(lines));(OUT/(name+'.json')).write_text(json.dumps(overview,indent=2,default=str)+'\n')
 with (OUT/'per_document.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rowscsv[0]));w.writeheader();w.writerows(rowscsv)
 print('Wrote',name,'complete=',full,flush=True)
if __name__=='__main__':main()
