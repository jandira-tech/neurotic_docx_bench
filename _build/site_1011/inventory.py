"""Inventory of corpus/word for the 2026-10-11 site sample: language, type, topic, pages."""
import csv, json, re, subprocess, sys, zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
C = Path('/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word')
OUT = Path(__file__).parent
meta = {}
for f in ('manifest.jsonl', '500_en_sources.jsonl'):
    for line in open(C / 'notices' / f):
        r = json.loads(line); meta.setdefault(r['id'], r)
docs = list(csv.DictReader(open(C / 'documents.csv')))
cmps = list(csv.DictReader(open(C / 'comparisons.csv')))
def pages(rel):
    if not rel or not (C / rel).is_file(): return 0
    out = subprocess.run(['mutool', 'info', str(C / rel)], capture_output=True, text=True).stdout
    m = re.search(r'Pages:\s*(\d+)', out); return int(m.group(1)) if m else 0
def text(rel, n=4000):
    try:
        x = zipfile.ZipFile(C / rel).read('word/document.xml').decode('utf8', 'replace')
        return ' '.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', x))[:n]
    except Exception: return ''
from langdetect import detect, DetectorFactory
DetectorFactory.seed = 0
def lang_of(d):
    for n in re.split(r'[;|]', d['names']):
        for k in (n.strip()[:64],):
            if k in meta: return meta[k].get('language') or '?', meta[k].get('type') or '?', meta[k].get('topic') or '?', 'meta'
    t = text(d['docx'])
    try: return (detect(t) if len(t) > 40 else '?'), 'synthetic', '?', 'detect'
    except Exception: return '?', 'synthetic', '?', 'detect'
def doc_row(d):
    l, ty, to, src = lang_of(d)
    return {'id': d['id'], 'stem': d['stem'], 'state': d['state'], 'docx': d['docx'], 'pdf': d['pdf'],
            'sets': d['sets'], 'lang': l, 'type': ty, 'topic': to, 'lang_src': src, 'pages': pages(d['pdf'])}
with ThreadPoolExecutor(12) as ex:
    drows = list(ex.map(doc_row, docs))
by = {r['id']: r for r in drows}
def cmp_row(c):
    b, n = by.get(c['base_id']), by.get(c['next_id'])
    return {'id': c['id'], 'key': c['key'], 'state': c['state'], 'docx': c['docx'], 'pdf': c['pdf'], 'sets': c['sets'],
            'base': b['docx'][:-5] if b else '', 'next': n['docx'][:-5] if n else '',
            'lang': b['lang'] if b else '?', 'type': b['type'] if b else '?', 'pages': pages(c['pdf'])}
with ThreadPoolExecutor(12) as ex:
    crows = list(ex.map(cmp_row, cmps))
for name, rows in (('documents', drows), ('comparisons', crows)):
    with open(OUT / f'inv_{name}.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(drows), len(crows))
