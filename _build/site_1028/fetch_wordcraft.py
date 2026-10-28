"""SHA-verified R2 reads only. Download metadata first, then exactly the job PDFs.

python fetch_wordcraft.py metadata
python fetch_wordcraft.py pdfs compare|convert
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
H=Path(__file__).resolve().parent
BASE='https://pub-92c80eda1059428394970066c8500eda.r2.dev/'
MANIFEST={line.split(None,1)[1]:line.split()[0] for line in (H/'wordcraft_MANIFEST.sha256.txt').read_text().splitlines()}


def fetch(item: tuple[str,Path]) -> str:
    key, dst=item
    wanted=MANIFEST[key]
    if dst.is_file() and hashlib.sha256(dst.read_bytes()).hexdigest()==wanted:
        return key
    dst.parent.mkdir(parents=True,exist_ok=True)
    part=dst.with_suffix(dst.suffix+'.part')
    subprocess.run(['curl','-fLsS','--retry','4','--retry-delay','1',BASE+key,'-o',str(part)],check=True)
    if hashlib.sha256(part.read_bytes()).hexdigest()!=wanted:
        part.unlink()
        raise RuntimeError(f'Hash mismatch: {key}')
    part.replace(dst)
    return key


def main(argv: list[str] | None = None) -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('what',choices=['metadata','pdfs'])
    parser.add_argument('phase',nargs='?',choices=['compare','convert'])
    args=parser.parse_args(argv)
    if args.what=='metadata':
        keys=[k for k in MANIFEST if k.endswith(('scores.json','README.md','REPORT.md','REPORT.json','tools.json','comparisons.csv','conversions.csv','generate_failures.json','render_failures.json'))]
        items=[(k,H/'metadata'/k.removeprefix('wordcraft-20261014/')) for k in keys]
    else:
        jobs=json.loads((H/f'jobs_wordcraft_{args.phase}.json').read_text())
        files={j['ref'] for j in jobs}|{p for j in jobs for k,p in j['cands'].items() if k not in j['extra']['errors']}
        items=[('wordcraft-20261014/'+Path(p).relative_to(H/'inputs/wordcraft').as_posix(),Path(p)) for p in sorted(files)]
    with ThreadPoolExecutor(6) as ex:
        for i,_ in enumerate(ex.map(fetch,items),1):
            if i%100==0 or i==len(items):print(f'{args.what}: {i}/{len(items)} verified',flush=True)
if __name__=='__main__': main()
