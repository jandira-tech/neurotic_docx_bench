# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""Pick representative English fixtures and plan unique redline pairs for the speed bench.

Reads the ``en_pairs_500`` documents (1000 English docx with Word PDFs), confirms each is
English from its own text, measures what drives engine cost (Word page count, words,
tables, pictures, headers/footers, notes, comments, tracked changes, sections), and draws
``--count`` documents stratified by page bucket x structure, in proportion to the pool.
Then plans ``--pairs`` base->next pairs over them: every fixture is a base and a next
equally often, never against itself, no pair twice, and every pair key (the redline's
file name) is unique.

Usage:
  uv run python scripts/pick_speed_fixtures.py --out results/speed_en_500 [--count 500] [--pairs 1000] [--seed 42]

Writes, into a directory that must not exist yet:
  fixtures.csv   one row per picked document with its measures and stratum
  pairs.csv      key,base,next,category: the plan for redline_speed_bench.ts --pairs-csv
  excluded.csv   documents left out of the pool and why
  SUMMARY.md     pool vs pick distribution
"""

from __future__ import annotations

import argparse
import csv
import random
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / 'corpus' / 'word'
POOL = CORPUS / 'pools' / 'en_pairs_500_renders.csv'

# The most frequent function words of English and of the other languages the corpus
# could hold. A document is English when English words outnumber every other set: a
# fixed English share would drop terse English (tables, lists, forms).
STOPWORDS = {
    'en': frozenset("""the of and to a in is that for it as was with be by on not he this are or
        his from at which but have an they you were her she there been one all we their has
        would will if can more when no so its our who other any may shall such these than
        then them into""".split()),
    'es': frozenset("""de la que el en y los del se las por un para con una su al lo como más
        pero sus le ya o fue este ha sí porque esta son entre cuando muy sin sobre""".split()),
    'fr': frozenset("""de la le et les des en un du une est que pour dans qui par sur au pas
        plus ne ce avec il sont se ou été elle mais aux cette nous""".split()),
    'de': frozenset("""der die und in den von zu das mit sich des auf für ist im dem nicht ein
        eine als auch es an werden aus er hat dass sie nach wird bei einer um""".split()),
    'pt': frozenset("""de a o que e do da em um para é com não uma os no se na por mais as dos
        como mas foi ao ele das tem à seu sua ou ser quando muito""".split()),
    'it': frozenset("""di e il la che è per un in del non una le sono con si da al della lo
        dei come ma anche gli ha nel alla""".split()),
    'nl': frozenset("""de en van het een in is dat op te zijn met voor niet aan er die ook
        als bij door wordt worden uit maar""".split()),
}
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
TEXT = re.compile(rb'<w:t(?:\s[^>]*)?>([^<]*)</w:t>')
PAGE_BUCKETS = ((1, '1p'), (3, '2-3p'), (9, '4-9p'), (29, '10-29p'), (10**9, '30p+'))


def english_score(text: str) -> tuple[float, int, float, str, int]:
    """(English stopword share, word count, non-Latin letter share, top language, English hits)."""
    words = [w.lower() for w in WORD.findall(text)]
    letters = [c for c in text if c.isalpha()]
    non_latin = sum(1 for c in letters if ord(c) > 0x24F)
    hits = {lang: sum(1 for w in words if w in sw) for lang, sw in STOPWORDS.items()}
    top = max(hits, key=lambda lang: hits[lang])
    share = hits['en'] / len(words) if words else 0.0
    return share, len(words), (non_latin / len(letters) if letters else 0.0), top, hits['en']


def measure(docx: Path) -> dict:
    with zipfile.ZipFile(docx) as z:
        names = z.namelist()
        body = z.read('word/document.xml')
        story = body + b''.join(
            z.read(n) for n in names if re.fullmatch(r'word/(header|footer|footnotes|endnotes)\d*\.xml', n)
        )
    # Runs join inside a paragraph (a word can span runs), paragraphs with a space.
    text = ' '.join(
        ''.join(t.decode('utf-8', 'replace') for t in TEXT.findall(para)) for para in story.split(b'</w:p>')
    )
    share, words, non_latin, top, en_hits = english_score(text)
    return {
        'words': words,
        'en_share': round(share, 3),
        'non_latin': round(non_latin, 3),
        'language': top,
        'en_hits': en_hits,
        'tables': body.count(b'<w:tbl>'),
        'pictures': sum(1 for n in names if n.startswith('word/media/')),
        'headers_footers': sum(1 for n in names if re.fullmatch(r'word/(header|footer)\d*\.xml', n)),
        'notes': int(any(n in names for n in ('word/footnotes.xml', 'word/endnotes.xml'))),
        'comments': int('word/comments.xml' in names),
        'tracked': int(b'<w:ins ' in body or b'<w:del ' in body),
        'sections': body.count(b'<w:sectPr'),
        'bytes': docx.stat().st_size,
    }


def page_count(pdf: Path) -> int | None:
    import fitz  # PyMuPDF, a bench dependency

    try:
        with fitz.open(pdf) as doc:
            return doc.page_count
    except Exception:
        return None


def stratum(m: dict) -> str:
    bucket = next(label for top, label in PAGE_BUCKETS if m['pages'] <= top)
    rich = sum(
        (m['tables'] > 0, m['pictures'] > 0, m['headers_footers'] > 0, m['notes'] or m['comments'] or m['tracked'])
    )
    return f"{bucket}/{'rich' if rich >= 2 else 'plain'}"


def allocate(sizes: dict[str, int], total: int) -> dict[str, int]:
    """Largest-remainder proportional allocation; every stratum keeps at least one."""
    pool = sum(sizes.values())
    exact = {k: total * n / pool for k, n in sizes.items()}
    take = {k: max(1, int(v)) for k, v in exact.items()}
    by_rest = sorted(sizes, key=lambda k: exact[k] - int(exact[k]), reverse=True)
    i = 0
    while sum(take.values()) < total:
        k = by_rest[i % len(by_rest)]
        if take[k] < sizes[k]:
            take[k] += 1
        i += 1
    while sum(take.values()) > total:
        k = max(take, key=lambda k: take[k] - exact[k])
        take[k] -= 1
    return take


def plan_pairs(ids: list[str], count: int, rng: random.Random) -> list[tuple[str, str]]:
    """``count`` distinct (base, next) pairs, base != next, each id used equally as base and next.

    Each round pairs every id with the one a fixed shift ahead in a shuffled order. Rounds
    use distinct non-zero shifts, so no pair repeats and no id meets itself; rejection
    sampling of random derangements stalls once a few rounds are taken.
    """
    n = len(ids)
    rounds = -(-count // n)
    if rounds > n - 1:
        raise SystemExit(f'{count} pairs need {rounds} rounds; {n} fixtures allow {n - 1}')
    order = ids[:]
    rng.shuffle(order)
    shifts = rng.sample(range(1, n), rounds)
    pairs: list[tuple[str, str]] = []
    for s in shifts:
        bases = order[:]
        rng.shuffle(bases)  # interleave strata within the round
        at = {k: i for i, k in enumerate(order)}
        pairs += [(b, order[(at[b] + s) % n]) for b in bases]
    return pairs[:count]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--count', type=int, default=500)
    ap.add_argument('--pairs', type=int, default=1000)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--min-words', type=int, default=30)
    ap.add_argument('--min-en-hits', type=int, default=5)
    a = ap.parse_args()
    out = a.out if a.out.is_absolute() else ROOT / a.out
    if out.exists():
        print(f'refusing to write into existing {out}', file=sys.stderr)
        return 1

    rows = list(csv.DictReader(POOL.open()))
    pool, excluded = [], []
    for r in rows:
        docx, pdf = CORPUS / r['docx'], CORPUS / r['pdf']
        if not docx.is_file():
            excluded.append((r['key'], 'docx missing'))
            continue
        try:
            m = measure(docx)
        except (zipfile.BadZipFile, KeyError) as e:
            excluded.append((r['key'], f'unreadable: {e}'))
            continue
        pages = page_count(pdf) if pdf.is_file() else None
        if pages is None:
            excluded.append((r['key'], 'no Word PDF'))
            continue
        if m['words'] < a.min_words:
            excluded.append((r['key'], f"{m['words']} words"))
            continue
        if m['language'] != 'en' or m['en_hits'] < a.min_en_hits or m['non_latin'] > 0.2:
            excluded.append((r['key'], f"not English ({m['language']}, en share {m['en_share']}, non-Latin {m['non_latin']})"))
            continue
        m.update(key=r['key'], docx=r['docx'], pages=pages)
        m['stratum'] = stratum(m)
        pool.append(m)

    if len(pool) < a.count:
        print(f'pool has {len(pool)} English documents, fewer than --count {a.count}', file=sys.stderr)
        return 1
    rng = random.Random(a.seed)
    by = defaultdict(list)
    for m in sorted(pool, key=lambda m: m['key']):
        by[m['stratum']].append(m)
    take = allocate({k: len(v) for k, v in by.items()}, a.count)
    picked = []
    for k in sorted(by):
        picked += rng.sample(by[k], take[k])
    picked.sort(key=lambda m: m['key'])

    ids = [m['key'] for m in picked]
    docx_of = {m['key']: m['docx'] for m in picked}
    pairs = plan_pairs(ids, a.pairs, rng)

    out.mkdir(parents=True)
    cols = ['key', 'docx', 'stratum', 'pages', 'words', 'language', 'en_share', 'non_latin', 'tables', 'pictures',
            'headers_footers', 'notes', 'comments', 'tracked', 'sections', 'bytes']
    with (out / 'fixtures.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        w.writerows(picked)
    stratum_of = {m['key']: m['stratum'] for m in picked}
    with (out / 'pairs.csv').open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['key', 'base', 'next', 'category'])
        for i, (b, n) in enumerate(pairs, 1):
            # The key names the redline file: a running number keeps every name unique.
            key = f'r{i:04d}__{b.split("_")[0]}__vs__{n.split("_")[0]}'
            w.writerow([key, f'corpus/word/{docx_of[b]}', f'corpus/word/{docx_of[n]}',
                        f'{stratum_of[b]}>{stratum_of[n]}'])
    with (out / 'excluded.csv').open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['key', 'reason'])
        w.writerows(excluded)

    pool_c, pick_c = Counter(m['stratum'] for m in pool), Counter(m['stratum'] for m in picked)
    md = [
        '# Speed fixtures: representative English documents',
        '',
        f'- source: `{POOL.relative_to(ROOT)}` ({len(rows)} documents)',
        f'- English pool: {len(pool)} (excluded {len(excluded)}, see excluded.csv)',
        f'- picked: {len(picked)} (seed {a.seed}), stratified by Word page count x structure',
        f'- pairs: {len(pairs)} distinct base->next, each fixture {a.pairs // a.count}x base and {a.pairs // a.count}x next',
        '',
        '| stratum | pool | picked |',
        '| --- | ---: | ---: |',
        *[f'| {k} | {pool_c[k]} | {pick_c[k]} |' for k in sorted(pool_c)],
        '',
        '| measure | pool median | picked median |',
        '| --- | ---: | ---: |',
    ]
    for col in ('pages', 'words', 'tables', 'pictures', 'bytes'):
        med = lambda xs: sorted(xs)[len(xs) // 2]
        md.append(f'| {col} | {med([m[col] for m in pool])} | {med([m[col] for m in picked])} |')
    (out / 'SUMMARY.md').write_text('\n'.join(md) + '\n')
    print('\n'.join(md))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
