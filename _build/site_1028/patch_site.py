"""Generate reviewable copies only. Never edits the published viewers or uploads assets.

python patch_site.py [--allow-partial]
"""
from __future__ import annotations
import argparse
import copy
import json
import re
from pathlib import Path
H=Path(__file__).resolve().parent
BUILD=H/'build'
SITE=H.parents[1]
PREVIEW=H/'preview'
R2='https://pub-92c80eda1059428394970066c8500eda.r2.dev/'
SETS={'index.html':['v1','wordcraft_convert'], 'redlines/index.html':['redlines','wordcraft_compare']}
NOTE=('2026-10-28 renewal: DOCX→PDF v1 (2,925 documents); 0929 accept/reject split '
      '(400 accepted + 400 rejected pairs); Wordcraft 2026-10-14 (400 compare + 400 convert). '
      'New cases show the first 3 pages at 120 DPI, with page PDFs. Pixel is the recorded bench score '
      '(ITT failures count zero); J/SSIM/TB use upstream docxide-pdf page-metrics at 150 DPI over '
      'all pages, commit a72d91bc. Upstream can return no metric for incompatible dimensions '
      'or text layouts. Versions are specific to each case. Build and report: _build/site_1028/.')


def split(html: str) -> tuple[str,list,str]:
    i=html.index('const DATA = ')
    j=html.index(';\n',i)
    return html[:i],json.loads(html[i+13:j]),html[j:]


def once(s: str,old: str,new: str) -> str:
    if s.count(old)!=1:
        raise ValueError(f'Expected one anchor; got {s.count(old)}: {old[:100]!r}')
    return s.replace(old,new)


def remote(row: dict) -> dict:
    c=copy.deepcopy(row)
    c['pages']={k:[R2+p if p else None for p in paths] for k,paths in c['pages'].items()}
    c['pdfs']={k:R2+p for k,p in c.get('pdfs',{}).items()}
    return c


def merge_cases(old: list[dict], added: list[dict], aliases: dict[str,str]) -> list[dict]:
    new_ids={f"{c['group']}/{c['case']}" for c in added}
    if len(new_ids)!=len(added):
        raise ValueError('Duplicate new case identities')
    keep=[]
    for c in old:
        key=f"{c['group']}/{c['case']}"
        if key in new_ids or aliases.get(key) in new_ids:
            continue
        keep.append(copy.deepcopy(c))
    return keep+[remote(c) for c in added]


def patch_html(html: str,added: list[dict],aliases: dict[str,str] | None = None) -> str:
    head,old,tail=split(html)
    old_engines=json.loads(re.search(r'const ENGINES = (.*?);\n',tail).group(1))
    old_versions=json.loads(re.search(r'const VERSIONS = (.*?);\n',tail).group(1))
    # Freeze historical versions before introducing newer versions or separately keyed lanes.
    for c in old:
        c['versions']={**old_versions,**c.get('versions',{})}
    data=merge_cases(old,added,aliases or {})
    engines=old_engines[:]
    known={k for k,_ in engines}
    labels={'docxodus':'docxodus','wordcraft':'Wordcraft','soffice':'LibreOffice (cohort)'}
    for key in sorted({k for c in added for f in ('scores','errors','pages') for k in c.get(f,{})}-known):
        engines.append([key,labels.get(key,key)])
    keys={k for k,_ in engines}
    # Hide lanes not measured for this case, while keeping genuine failures visible.
    for c in data:
        present={k for f in ('scores','errors','pages','page_counts') for k in c.get(f,{})}
        c['dropped']=sorted(set(c.get('dropped',[])) | (keys-present))
    tail=once(tail,'const ENGINES = '+json.dumps(old_engines)+';', 'const ENGINES = '+json.dumps(engines)+';')
    tail=once(tail,'const METRICS = ["jaccard", "ssim", "text_boundary"];',
              'const METRICS = ["pixel", "jaccard", "ssim", "text_boundary"];')
    tail=once(tail,"const METRIC_LABEL = { jaccard:","const METRIC_LABEL = { pixel: 'Pixel', jaccard:")
    tail=once(tail,'const METRIC_INFO = {',
              "const METRIC_INFO = {\n  pixel: 'Recorded bench pixel score (0–100), not recomputed here. ITT failures count zero. J/SSIM/TB are separate upstream page-metrics. Missing means no published measurement.',")
    helper='''function versionLabel(key, rows = DATA) {
  const versions = [...new Set(rows.filter(c => !(c.dropped || []).includes(key))
    .map(c => c.versions?.[key] ?? VERSIONS[key] ?? '').filter(Boolean))];
  return versions.length > 1 ? 'varies by case' : (versions[0] || '');
}
const ENGINE_COLORS = Object.fromEntries(ENGINES.map(([key], i) => [key,
  ['#1e5580', '#3d7eae', '#1c5f46', '#8a3b2e', '#67c6ee', '#123b5c', '#8fa6b6', '#061c30', '#a35f16', '#7d4085', '#367966'][i % 11]]));
'''
    tail=once(tail,'const PAGE_STEP = 10;',helper+'const PAGE_STEP = 10;')
    tail=tail.replace("const ver = (VERSIONS[key] || '') + odd;", "const ver = ((c.versions || {})[key] ?? VERSIONS[key] ?? '') + odd;")
    tail=once(tail,'${VERSIONS[key] ? ` <small class="ver">${VERSIONS[key]}</small>` : \'\'}',
              '${versionLabel(key) ? ` <small class="ver">${versionLabel(key)}</small>` : \'\'}')
    tail=once(tail,'data-e="${key}"> ${label}',
              'data-e="${key}"> <span style="color:${ENGINE_COLORS[key]}">●</span> ${label}')
    tail=once(tail,"const h = document.createElement('h3'); h.className = 'colhead';",
              "const h = document.createElement('h3'); h.className = 'colhead'; h.style.borderTop = `2px solid ${ENGINE_COLORS[key]}`;")
    # Redline viewer did not expose its existing pdfs map. Match the conversion viewer.
    red_header='<b>${label}</b>${ver ? ` <span class="ver">${ver}</span>` : \'\'}'
    if red_header in tail:
        tail=once(tail,red_header,'<b>${label}</b>${c.pdfs?.[key] ? ` <a href="${c.pdfs[key]}" target="_blank" rel="noopener" title="Shown pages as a PDF">PDF</a>` : \'\'}${ver ? ` <span class="ver">${ver}</span>` : \'\'}')
    # Empty Pixel cells on old-only selections need no column; new selections sort like J/SSIM/TB.
    tail=once(tail,"  const engines = ENGINES.filter(([k]) => k !== 'reference');", """  const rows = visibleCases().map(([c, i]) => ({ c, i }));
  const engines = ENGINES.filter(([k]) => k !== 'reference' && rows.some(r => !(r.c.dropped || []).includes(k)));
  const tableCols = TABLE_COLS.filter(m => m !== 'pixel' || rows.some(r => Object.values(r.c.scores).some(s => s.pixel != null)));""")
    tail=once(tail,'  const rows = visibleCases().map(([c, i]) => ({ c, i }));\n  const { col: sc, dir }', '  const { col: sc, dir }')
    # Only the score-table body uses TABLE_COLS except the legend, which must retain the Pixel definition.
    start=tail.index('function renderScores()')
    end=tail.index('\nfunction render()',start)
    table=tail[start:end].replace('TABLE_COLS.length','tableCols.length').replace('of TABLE_COLS','of tableCols').replace('cl.m === METRICS[0]','cl.m === tableCols[0]')
    old_header='''engines.map(([, label]) => `<th class="eng" colspan="${tableCols.length}">${label}${VERSIONS[engines.find(e => e[1] === label)[0]] ? ` <span class="ver">${VERSIONS[engines.find(e => e[1] === label)[0]]}</span>` : ''}</th>`)'''
    new_header='''engines.map(([key, label]) => `<th class="eng" colspan="${tableCols.length}" style="border-top:2px solid ${ENGINE_COLORS[key]}">${label}${versionLabel(key, rows.map(r => r.c)) ? ` <span class="ver">${versionLabel(key, rows.map(r => r.c))}</span>` : ''}</th>`)'''
    table=once(table,old_header,new_header)
    tail=tail[:start]+table+tail[end:]
    tail=once(tail,"$('#legend').innerHTML = '","$('#legend').innerHTML = '<span><b>2026-10-28</b>: "+NOTE+"</span>")
    tail=tail.replace('All scores are against the Word reference, averaged over the pages both PDFs have; extra pages are ignored.', 'J/SSIM/TB compare against Word over compatible pages both PDFs have; extra pages are ignored. Pixel is the separately recorded bench score.')
    # Report a recorded failure rather than implying an absent page is a conversion success.
    tail=once(tail,"const ver = ((c.versions || {})[key] ?? VERSIONS[key] ?? '') + odd;",
              "const ver = ((c.versions || {})[key] ?? VERSIONS[key] ?? '') + odd + (c.errors?.[key] ? ' · no scored PDF' : '');")
    return head+'const DATA = '+json.dumps(data,ensure_ascii=False)+tail


def main(argv: list[str] | None = None) -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-partial',action='store_true',help='Preview completed sets while another input set is unresolved; label explicitly')
    args=parser.parse_args(argv)
    aliases=json.loads((H/'redline_replacements.json').read_text()) if (H/'redline_replacements.json').exists() else {}
    for rel,sets in SETS.items():
        missing=[s for s in sets if not (BUILD/f'cases_{s}.json').is_file()]
        if missing and not args.allow_partial:
            raise SystemExit(f'Missing sets: {missing}; finish build before creating final previews')
        added=[r for s in sets if (BUILD/f'cases_{s}.json').is_file() for r in json.loads((BUILD/f'cases_{s}.json').read_text())]
        html=patch_html((SITE/rel).read_text(),added,aliases if rel.startswith('redlines/') else {})
        if missing:
            html=html.replace('<b>2026-10-28</b>:', '<b>PARTIAL PREVIEW — missing '+', '.join(missing)+'</b>:')
        dest=PREVIEW/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(html)
        print(f'{dest.relative_to(H)}: {len(split(html)[1])} cases, {len(added)} from completed sets; missing={missing}')

if __name__=='__main__':main()
