"""Run one tool over the 2026-10-11 samples; outputs and a status TSV under results/site_1011/<lane>.

    python3 -I run_tools.py jubarte-convert | soffice | jubarte-compare | docxodus
"""
import csv, os, shutil, subprocess, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
H = Path(__file__).parent
B = Path('/Users/arthrod/temp/T/neurotic_docx_bench')
C = B / 'corpus/word'
R = B / 'results/site_1011'
J = Path('/Users/arthrod/temp/T/jubarte-v0.12.0/target/release/jubarte')  # v0.12.0 tag, its own worktree
SOFFICE = '/Applications/LibreOffice.app/Contents/MacOS/soffice'
TIMEOUT = 300
def run(cmd, **kw):
    t = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, **kw)
        return p.returncode, (p.stderr or p.stdout).strip().replace('\n', ' ')[:300], time.time() - t
    except subprocess.TimeoutExpired:
        return 'timeout', '', time.time() - t
def jubarte_convert(r, out):
    dst = out / f"{r['state']}__{r['stem']}.pdf"
    if dst.is_file(): return r['id'], 'exists', '', 0
    code, err, s = run([str(J), 'convert', str(C / r['docx']), '--revisions', 'word', '--compress', '-o', str(dst), '--force'])
    return r['id'], code if dst.is_file() or code else 'nopdf', err, s
def soffice(r, out):
    dst = out / f"{r['state']}__{r['stem']}.pdf"
    if dst.is_file(): return r['id'], 'exists', '', 0
    with tempfile.TemporaryDirectory(prefix='so_') as tmp:
        src = Path(tmp) / f"{r['state']}__{r['stem']}.docx"; shutil.copy(C / r['docx'], src)
        code, err, s = run([SOFFICE, f'-env:UserInstallation=file://{tmp}/profile', '--headless', '--convert-to', 'pdf',
                            '--outdir', str(out), str(src)])
    return r['id'], code if dst.is_file() or code else 'nopdf', err, s
def staged(i):
    """The base and next Word compared, as copied for it (corpus/word's DOCX now live on the HF fixtures repo)."""
    for d in ('word_compare', 'word_compare_r'):
        a, b = R / d / 'A' / f'{i}.docx', R / d / 'B' / f'{i}.docx'
        if a.is_file() and b.is_file(): return a, b
    raise FileNotFoundError(i)
def jubarte_compare(r, out):
    dst = out / f"{r['id']}.docx"
    if dst.is_file(): return r['id'], 'exists', '', 0
    a, b = staged(r['id'])
    code, err, s = run([str(J), 'compare', '-b', str(a), '-m', str(b),
                        '-o', str(dst), '--force', '--quiet'])
    return r['id'], code if dst.is_file() or code else 'nodocx', err, s
LANES = {'jubarte-convert': ('sample_docx_to_pdf.csv', jubarte_convert, 8),
         'soffice': ('sample_docx_to_pdf.csv', soffice, 6),
         'jubarte-compare': ('sample_redlines.csv', jubarte_compare, 8)}
def main():
    lane = sys.argv[1]
    sample, fn, jobs = LANES[lane]
    rows = list(csv.DictReader(open(H / sample)))
    out = R / lane / ('docx' if lane.endswith('compare') else 'pdf'); out.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(jobs) as ex, open(R / lane / 'status.tsv', 'a') as log:
        for i, (rid, code, err, s) in enumerate(ex.map(lambda r: fn(r, out), rows), 1):
            log.write(f'{rid}\t{code}\t{s:.2f}\t{err}\n'); log.flush()
    n = sum(1 for _ in out.iterdir()); print(f'{lane}: {n}/{len(rows)} outputs in {out}')
if __name__ == '__main__':
    main()
