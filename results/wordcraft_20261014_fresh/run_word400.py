"""Drive the repository Word CLIs over word_400 chunk folders, one at a time.

Before each chunk Word must hold zero documents for 8 consecutive seconds (a crash-
recovered or ghost document appears a few seconds after launch and poisons every
later open with "open produced 2 new documents"). The drivers run unmodified.
"""
from pathlib import Path
import subprocess,sys,time,json,hashlib,os,re
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];PY=ROOT/'.venv/bin/python'
# The committed drivers (repository HEAD ee49054d, the hashes tools.json records). The
# working-tree copies were being edited live by another session during this run.
DRIVERS=OUT/'drivers_ee49054d'

def osa(script):
 p=subprocess.run(['osascript','-e',script],capture_output=True,text=True,timeout=60);return p.returncode,p.stdout.strip(),p.stderr.strip()

def word_count():
 rc,out,err=osa('tell application "Microsoft Word" to count documents')
 return int(out) if rc==0 and out.isdigit() else None

def hard_restart():
 """Fresh Word: a crashed-and-relaunched Word (Error Reporting still up) makes every
 open after the first produce a phantom second document."""
 osa('tell application "Microsoft Word" to quit saving no');time.sleep(5)
 subprocess.run(['pkill','-x','Microsoft Word']);subprocess.run(['pkill','-f','Microsoft Error Reporting']);time.sleep(4)
 subprocess.run(['open','-g','-a','Microsoft Word']);time.sleep(15)

def settle():
 hard_restart()
 for attempt in range(6):
  stable=0
  for _ in range(30):
   n=word_count()
   if n==0:
    stable+=1
    if stable>=8:return True
   else:
    stable=0
    if n:osa('tell application "Microsoft Word" to close documents saving no')
   time.sleep(1)
  print('[settle] Word will not stay empty; quitting it (attempt',attempt+1,')',flush=True)
  osa('tell application "Microsoft Word" to quit saving no');time.sleep(8)
  subprocess.run(['pkill','-x','Microsoft Word']);time.sleep(4)
  subprocess.run(['open','-g','-a','Microsoft Word']);time.sleep(15)
 return False

def foreign_drivers():
 """Word drivers not started by this runner (another session sharing the one Word)."""
 me=str(os.getpid())
 out=subprocess.run(['ps','-axo','pid=,ppid=,command='],capture_output=True,text=True).stdout.splitlines()
 hits=[]
 for line in out:
  pid,ppid,cmd=line.strip().split(None,2)
  if ppid!=me and pid!=me and re.search(r'python[0-9.]*\s+(-[A-Za-z]\s+)*\S*word_(pdf|redline|validate)\.py',cmd) and 'pgrep' not in cmd:hits.append(line.strip()[:200])
 return hits

def wait_alone():
 waited=False
 while hits:=foreign_drivers():
  if not waited:print(time.strftime('%H:%M:%S'),'[wait] another Word driver is running; waiting:',hits,flush=True);waited=True
  time.sleep(20)
 if waited:print(time.strftime('%H:%M:%S'),'[wait] Word is free',flush=True);time.sleep(10)

def foreign_documents():
 """Open Word documents that no driver of ours staged (another agent probing Word)."""
 try:rc,out,_=osa('tell application "Microsoft Word" to get full name of every document')
 except subprocess.TimeoutExpired:return []
 if rc or not out:return []
 bad=[]
 for path in out.split(', '):
  path=path.strip()
  if ':' not in path:continue  # unsaved compare results have no path (HFS paths use ':')
  if ':tmp:wordredline.' in path or ':tmp:wordpdf.' in path:continue
  bad.append(path)
 return bad

def run_chunk(folder,cmd):
 """Run one driver; abort (and report contamination) if another Word driver appears."""
 with (folder/'driver.out').open('w') as log:
  proc=subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
  while proc.poll() is None:
   time.sleep(3)
   hits=[h for h in foreign_drivers() if not h.startswith(str(proc.pid))]
   hits=[h for h in hits if h.split()[1]!=str(proc.pid)]
   tick=getattr(run_chunk,'tick',0)+1;run_chunk.tick=tick
   if not hits and tick%5==0:hits=['document:'+d for d in foreign_documents()]
   if hits:
    print(time.strftime('%H:%M:%S'),'[contaminated] foreign Word driver appeared; aborting',folder.name,hits,flush=True)
    subprocess.run(['pkill','-TERM','-P',str(proc.pid)]);proc.terminate()
    try:proc.wait(30)
    except subprocess.TimeoutExpired:proc.kill();proc.wait()
    return None,hits
 return proc.returncode,[]

def reset(folder,why):
 n=time.strftime('%H%M%S');dest=OUT/'word_400'/'contaminated'/f'{folder.name}_{n}';dest.mkdir(parents=True,exist_ok=True)
 for name in ('driver.log','driver.out'):
  if (folder/name).exists():(folder/name).rename(dest/name)
 import shutil;shutil.rmtree(folder/'pdf',ignore_errors=True)
 if 'convert' not in folder.name:
  import shutil;shutil.rmtree(folder/'docx',ignore_errors=True)
 (dest/'why.json').write_text(json.dumps(why,indent=2)+'\n')

def main():
 receipts=OUT/'word_400'/'driver_invocations.jsonl'
 for name in sys.argv[1:]:
  folder=OUT/'word_400'/name
  if (folder/'driver.done').exists():print('skip',name,flush=True);continue
  if 'compare' in name:
   driver='word_redline.py';args=['--a',str(folder/'A'),'--b',str(folder/'B'),'--out',str(folder/'pdf'),'--docx-out',str(folder/'docx'),'--emit','both']
  else:
   driver='word_pdf.py';args=['--src',str(folder/'docx'),'--out',str(folder/'pdf')]
  cmd=[str(PY),str(DRIVERS/driver),*args,'--log',str(folder/'driver.log')]
  while True:
   wait_alone();assert settle(),'Word never settled empty'
   if foreign_drivers():continue
   print(time.strftime('%H:%M:%S'),'RUN',driver,name,flush=True);t=time.monotonic()
   rc,hits=run_chunk(folder,cmd)
   if rc is None:reset(folder,{'foreign':hits,'at':time.strftime('%Y-%m-%dT%H:%M:%S%z')});continue
   break
  n=len(list((folder/'pdf').glob('*.pdf'))) if (folder/'pdf').exists() else 0
  rec={'folder':name,'command':cmd,'returncode':rc,'driver_sha256':hashlib.sha256((DRIVERS/driver).read_bytes()).hexdigest(),'driver_commit':'ee49054d','pdfs':n,'seconds':round(time.monotonic()-t,1),'finished':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'exclusive_word':True}
  with receipts.open('a') as fh:fh.write(json.dumps(rec)+'\n')
  (folder/'driver.done').write_text(json.dumps(rec)+'\n');print(time.strftime('%H:%M:%S'),'END',name,'rc',rc,'pdfs',n,f"{rec['seconds']}s",flush=True)
if __name__=='__main__':main()
