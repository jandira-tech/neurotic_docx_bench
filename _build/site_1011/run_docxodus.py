"""docxodus 12.6.5 over sample_redlines.csv, one process per pair (120 s cap); status.tsv records failures."""
import csv, subprocess, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
B = Path('/Users/arthrod/temp/T/neurotic_docx_bench'); R = B / 'results/site_1011/docxodus'; OUT = R / 'docx'
def staged(i):
    """The base and next Word compared, as copied for it (corpus/word's DOCX now live on the HF fixtures repo)."""
    for d in ('word_compare', 'word_compare_r'):
        a, b = B / 'results/site_1011' / d / 'A' / f'{i}.docx', B / 'results/site_1011' / d / 'B' / f'{i}.docx'
        if a.is_file() and b.is_file(): return a, b
    raise FileNotFoundError(i)
rows = list(csv.DictReader(open(Path(__file__).parent / 'sample_redlines.csv')))
def one(r):
    dst = OUT / f"{r['id']}_docxodus.docx"
    if dst.is_file(): return r['id'], 'exists', 0, ''
    t = time.time()
    try:
        a, b = staged(r['id'])
        p = subprocess.run(['node', '--import', 'tsx', 'scripts/_site1011_docxodus_one.ts', str(a), str(b), str(dst)],
                           cwd=B, capture_output=True, text=True, timeout=120)
        err = '' if p.returncode == 0 else ' '.join(l for l in (p.stderr or '').splitlines() if 'Jiterpreter' not in l)[-300:]
        code = p.returncode
    except subprocess.TimeoutExpired:
        code, err = 'timeout', ''
    if code != 0: dst.unlink(missing_ok=True)
    return r['id'], code if dst.is_file() or code != 0 else 'nodocx', time.time() - t, err
with ThreadPoolExecutor(6) as ex, open(R / 'status.tsv', 'a') as log:
    for rid, code, s, err in ex.map(one, rows):
        log.write(f'{rid}\t{code}\t{s:.1f}\t{err}\n'); log.flush()
print(sum(1 for _ in OUT.glob('*.docx')), 'docxodus redlines')
