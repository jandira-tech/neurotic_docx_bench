"""Validate a completed set, then delete its downloaded inputs and leftover rasters."""
import argparse
import json
import shutil
from pathlib import Path
import report
from process import H,BUILD,METRICS


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('which',choices=list(report.EXPECTED))
    args=parser.parse_args(argv)
    name=args.which
    file=BUILD/f'cases_{name}.json'
    rows=json.loads(file.read_text())
    # Early v1 checkpoints used site_1011's omission of null metrics. Make nulls explicit.
    for r in rows:
        for key in r['pages']:
            if key=='reference':continue
            for m in METRICS:r['scores'][key].setdefault(m,None)
    file.write_text(json.dumps(rows,indent=1,ensure_ascii=False))
    report.validate_set(name,rows)
    paths={'v1':[H/'inputs/v1'], 'redlines':[H/'inputs/v1_ar',H/'inputs/redlines_split'],
           'wordcraft_compare':[H/'inputs/wordcraft/compare'],
           'wordcraft_convert':[H/'inputs/wordcraft/convert']}[name]
    for p in paths:
        if p.exists():shutil.rmtree(p)
    # Call only after this set's process has exited; no other set runs concurrently.
    for p in BUILD.glob('c_*'):
        if p.is_dir():shutil.rmtree(p)
    for p in BUILD.rglob('*.png'):
        raise RuntimeError(f'Unexpected leftover PNG: {p}')
    print(f'{name}: {len(rows)} cases validated; downloaded inputs and all rasters removed',flush=True)
if __name__=='__main__':main()
