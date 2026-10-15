from pathlib import Path
import json,csv,subprocess,time,zipfile,hashlib
from lxml import etree as E
ROOT=Path.cwd();OUT=ROOT/'results/wordcraft_20261014';destdir=OUT/'compare/docxodus-12.6.5/docx';destdir.mkdir(parents=True,exist_ok=True)
manifest={r['id']:r for r in csv.DictReader(open(OUT/'comparisons.csv'))}
reused={json.loads(line)['id'] for line in open(OUT/'operations.jsonl') if json.loads(line)['tool']=='docxodus' and json.loads(line)['reused']}
print('Regenerating',len(reused),'historical Docxodus outputs to ensure one pinned version',flush=True)
for i,ident in enumerate(sorted(reused),1):
 dest=destdir/f'{ident}.docx'
 if dest.exists():continue
 r=manifest[ident];base=ROOT/'corpus/word'/(r['base']+'.docx');nxt=ROOT/'corpus/word'/(r['next']+'.docx');cmd=['node','--import','tsx','scripts/_site1011_docxodus_one.ts',str(base),str(nxt),str(dest)]
 t=time.perf_counter_ns()
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=120);rc=p.returncode;error=(p.stderr+p.stdout)[-6000:]
 except subprocess.TimeoutExpired as ex:rc=124;error=str(ex)
 row={'id':ident,'task':'compare','tool':'docxodus-12.6.5','command':cmd,'elapsed_ms':(time.perf_counter_ns()-t)/1e6,'returncode':rc,'stderr_stdout':error,'reused':False,'output':str(dest),'ok':rc==0 and dest.exists()}
 if row['ok']:
  with zipfile.ZipFile(dest) as z:assert z.testzip() is None;E.fromstring(z.read('word/document.xml'))
  row['output_sha256']=hashlib.sha256(dest.read_bytes()).hexdigest()
 with (OUT/'operations.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
 if i%10==0 or not row['ok']:print(i,'/',len(reused),'ok' if row['ok'] else 'FAILED',flush=True)
print('historical refresh finished',flush=True)
