"""CLI latency over the frozen 400+400 rows, from operations.jsonl (last attempt per document).

Prints a Markdown table (median/p90/p99/max ms, ok, failed, timeouts) for docs/SPEED.md and
REPORT.md. Latencies were observed on a shared, loaded machine; see REPORT.md."""
from pathlib import Path
import csv,json,statistics,sys
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT));import lanes
ids={'compare':{r['id'] for r in csv.DictReader(open(OUT/'comparisons.csv'))},
     'convert':{r['stem'] for r in csv.DictReader(open(OUT/'conversions.csv'))}}
last={}
for line in (OUT/'operations.jsonl').read_text().splitlines():
 op=json.loads(line)
 if op['id'] in ids[op['task']] and not op['reused']:last[(op['task'],op['tool'],op['id'])]=op

def pct(xs,p):
 xs=sorted(xs);return xs[min(len(xs)-1,max(0,round(p/100*len(xs)+.5)-1))]

def table():
 rows=['| Task | Tool | Docs run | OK | Failed | Timeouts | Median ms | p90 ms | p99 ms | Max ms |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for task in ('compare','convert'):
  for tool in sorted({t for k,t,_ in last if k==task and t in lanes.LANES[task]},key=lambda t:(t.startswith('docx') or t=='soffice',t)):
   ops=[o for (k,t,_),o in last.items() if k==task and t==tool];ok=[o['elapsed_ms'] for o in ops if o['ok']]
   timeouts=sum(o.get('returncode')==124 or 'timed out after' in (o.get('stderr_stdout') or '') for o in ops if not o['ok'])
   f=lambda v:f'{v:,.1f}'
   rows.append(f"| {task} | {tool} | {len(ops)} | {len(ok)} | {len(ops)-len(ok)} | {timeouts} | {f(statistics.median(ok)) if ok else '—'} | {f(pct(ok,90)) if ok else '—'} | {f(pct(ok,99)) if ok else '—'} | {f(max(ok)) if ok else '—'} |")
 return '\n'.join(rows)
if __name__=='__main__':print(table())
