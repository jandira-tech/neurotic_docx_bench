"""Renew the published pages in place (2026-10-11): new cases from build/, page images on R2.

    python3 -I patch_site.py            # edits ~/temp/T/ndb-gh-pages/{index.html,redlines/index.html}

DOCX to PDF (index.html):
  * jubarte and LibreOffice leave every old case (stale); their image folders are deleted.
  * 800 new corpus documents (Word, jubarte 0.12.0, soffice 26.8.0.3) and jubarte/soffice on the 76
    local docxide `cases` fixtures are added; docxide-pdf, PyMuPDF Pro, MiniPdf, rdocx and office2pdf
    keep their published (stale) results.
Redlines (redlines/index.html):
  * jubarte (both columns) and docxodus leave the old cases; an old case left with Word only is
    dropped, the 29 with a SuperDoc column stay.
  * 1000 new pairs: Word 16.115's compare, jubarte 0.12.0 and docxodus 12.6.5, every PDF by Word.
Both: a new case shows every page of Word's PDF (`shown`, 1-based page numbers; the docxide fixtures
keep their first 3); the viewer says which pages it shows. Images of new cases load from the public R2 bucket.
"""

from __future__ import annotations

import json
import re
import shutil
import statistics
from pathlib import Path

H = Path(__file__).parent
BUILD = H / "build"
SITE = Path("/Users/arthrod/temp/T/ndb-gh-pages")
R2 = "https://pub-92c80eda1059428394970066c8500eda.r2.dev/"
STALE_D2P = ("jubarte", "libreoffice")
STALE_RED = ("jubarte-rust", "jubarte-093", "docxodus")


def split(html: str) -> tuple[str, list, str]:
    i = html.index("const DATA = ")
    j = html.index(";\n", i)
    return html[:i], json.loads(html[i + len("const DATA = "):j]), html[j:]


def once(s: str, old: str, new: str) -> str:
    if s.count(old) != 1:
        raise SystemExit(f"anchor found {s.count(old)} times: {old[:90]!r}")
    return s.replace(old, new)


def drop(c: dict, keys: tuple) -> None:
    for field in ("pages", "page_counts", "scores", "pdfs", "times", "errors"):
        for k in keys:
            (c.get(field) or {}).pop(k, None)


def remote(row: dict, rename: dict | None = None) -> dict:
    """A build/ row as a viewer case: R2 URLs, engine keys renamed."""
    rename = rename or {}
    c = {k: v for k, v in row.items() if k not in ("errors",)}
    c["pages"] = {rename.get(k, k): [R2 + p if p else None for p in v] for k, v in row["pages"].items()}
    c["pdfs"] = {rename.get(k, k): R2 + p for k, p in row.get("pdfs", {}).items()}
    for f in ("page_counts", "scores"):
        c[f] = {rename.get(k, k): v for k, v in row[f].items()}
    return c


VIEWER = [  # the page labels of a case that shows a sample of its pages
    ("$('#pageinfo').textContent = `pages 1–${state.shown} of ${maxPages}`;",
     "$('#pageinfo').textContent = `pages 1–${state.shown} of ${(c.page_counts || {}).reference ?? maxPages}`;"),
    ('`<div class="missing">no page ${p+1}</div>`', '`<div class="missing">no page ${c.shown ? c.shown[p] : p+1}</div>`'),
    ('title="the first 3 pages as a PDF"', 'title="${c.shown && c.shown.length > 3 ? \'the whole document\' : \'the first 3 pages\'} as a PDF"'),
    ("· ${n} p${n > shown ? ` (first ${shown} shown)` : ''}${sc}`;",
     "· ${n} p${c.shown ? (c.shown.length < n ? ` (${c.shown.filter((_, i) => (c.pages[key] || [])[i]).length} shown)` : '')"
     " : (n > shown ? ` (first ${shown} shown)` : '')}${sc}`;"),
]


def d2p() -> None:
    path = SITE / "index.html"
    head, data, tail = split(path.read_text())
    for c in data:
        drop(c, STALE_D2P)
    fixtures = {r["case"]: r for r in json.loads((BUILD / "cases_fixtures.json").read_text())}
    for c in data:  # jubarte 0.12.0 and soffice 26.8.0.3 on the local docxide `cases` fixtures
        r = fixtures.get(c["case"]) if c["group"] == "cases" else None
        if r:
            new = remote(r)
            for f in ("pages", "page_counts", "scores", "pdfs"):
                c.setdefault(f, {}).update({k: v for k, v in new[f].items() if k != "reference"})
    added = [remote(r) for r in json.loads((BUILD / "cases_d2p.json").read_text())]
    for c in added:
        c["reference_app"] = "Microsoft Word"
    data += added
    for k in STALE_D2P:
        for d in list((SITE / "corpus").glob(f"*/*/{k}")) + list((SITE / "docxide").glob(f"*/*/*/{k}")) + list((SITE / "docxide").glob(f"*/*/{k}")):
            shutil.rmtree(d)
    tail = once(tail, '"jubarte": "0.10.1 --revisions word --compress"', '"jubarte": "0.12.0 --revisions word --compress"')
    tail = once(tail, '"libreoffice": "26.2.5.2 (docxide fixtures) / 26.8.0.3 (corpus)"', '"libreoffice": "26.8.0.3"')
    for old, new in VIEWER:
        tail = once(tail, old, new)
    tail = once(tail,
        "and a varied 860-document <b>corpus sample</b> of neurotic-docx-bench corpus/word, stratified by state, page count and "
        "jubarte score band. Only the first 3 pages are shown, at 100 DPI.",
        "and two samples of neurotic-docx-bench corpus/word. The <b>October 2026 sample</b>: 800 documents not shown before "
        "(half English, every Portuguese document, the rest across 30 languages; every state; one page to 300+), "
        "Word&#8217;s PDF against jubarte 0.12.0 and LibreOffice 26.8.0.3, showing every page "
        "at 120 DPI (images on R2). The earlier 860-document sample keeps the engines not rerun "
        "(docxide-pdf, MiniPdf, rdocx, office2pdf, PyMuPDF Pro) with their first 3 pages at 100 DPI; its jubarte and LibreOffice "
        "columns were stale and are gone. On the docxide fixtures, jubarte 0.12.0 and LibreOffice 26.8.0.3 were rerun on the 76 "
        "<i>cases</i> whose Word PDF we have.")
    tail = tail.replace("jubarte and PyMuPDF Pro added here", "PyMuPDF Pro added here")
    path.write_text(head + "const DATA = " + json.dumps(data, ensure_ascii=False) + tail)
    print(f"index.html: {len(data)} cases ({len(added)} new)")


def stats(rows: list, key: str) -> str:
    vals = [statistics.mean(s.values()) for r in rows if (s := r["scores"].get(key))]
    if not vals:
        return f"0/{len(rows)}"
    return (f"{len(vals)}/{len(rows)}, mean {statistics.mean(vals):.1f}, median {statistics.median(vals):.1f}, "
            f"{sum(v >= 90 for v in vals)} at 90+")


def redlines() -> None:
    path = SITE / "redlines" / "index.html"
    head, data, tail = split(path.read_text())
    keep, gone = [], []
    for c in data:
        drop(c, STALE_RED)
        (keep if "superdoc" in c["pages"] else gone).append(c)
    for c in gone:
        shutil.rmtree(SITE / "redlines" / c["group"] / c["case"], ignore_errors=True)
    for k in STALE_RED:
        for d in (SITE / "redlines").glob(f"*/*/*/{k}"):
            shutil.rmtree(d)
    rows = json.loads((BUILD / "cases_redlines.json").read_text())
    added = [remote(r, {"jubarte": "jubarte-rust"}) for r in rows]
    for c in added:
        c["reference_app"] = "Microsoft Word"
    for c in keep:  # compared by an earlier Word than the new pairs
        c["versions"] = {"reference": "Word 16.114 compare"}
    data = keep + added
    tail = once(tail, '["jubarte-093", "jubarte 0.9.3"], ', "")
    tail = once(tail, "const ver = (VERSIONS[key] || '') + odd;", "const ver = ((c.versions || {})[key] ?? VERSIONS[key] ?? '') + odd;")
    tail = once(tail, '"reference": "Word 16.114 compare", "jubarte-rust": "0.11.2 (release)", "jubarte-093": "0.9.3 (release)", "docxodus": "12.6.5"',
                '"reference": "Word 16.115 compare", "jubarte-rust": "0.12.0 (release)", "docxodus": "12.6.5"')
    for old, new in VIEWER:
        if "as a PDF" not in old:  # the redline viewer has no PDF links
            tail = once(tail, old, new)
    i = tail.index("<span><b>What this is</b>")
    j = tail.index("' +\n  TABLE_COLS.map", i)
    note = (
        "<span><b>What this is</b>: redlines by jubarte 0.12.0 and docxodus 12.6.5 against Microsoft Word&#8217;s own compare, "
        "every PDF rendered by Word for Mac 16.115, scored with docxide-pdf&#8217;s page-metrics at 150 DPI over every page. "
        f"<b>October 2026</b>: {len(rows)} corpus pairs not shown before (half English, every Portuguese pair, the rest across "
        "many languages; with and without comments; one page to 400+), each compared again by Word 16.115 on 2026-10-11. "
        "Shown: every page of each redline at 120 DPI (images on R2). "
        f"Scores over the {len(rows)} pairs (per pair, the mean of J, SSIM and TB): jubarte 0.12.0 {stats(rows, 'jubarte')}; docxodus 12.6.5 {stats(rows, 'docxodus')} "
        "(a failure or timeout leaves the column empty; docxodus ran last, one process per pair, 120 s each). "
        f"The {len(keep)} earlier cases that have a SuperDoc column keep it (SuperDoc was not rerun; Word 16.114&#8217;s compare); "
        "their jubarte and docxodus columns were stale and are gone. Scores and scripts: _build/site_1011/.</span>")
    tail = tail[:i] + note + tail[j:]
    path.write_text(head + "const DATA = " + json.dumps(data, ensure_ascii=False) + tail)
    print(f"redlines/index.html: {len(data)} cases ({len(added)} new, {len(keep)} kept, {len(gone)} dropped)")


if __name__ == "__main__":
    import sys
    for part in sys.argv[1:] or ["d2p", "redlines"]:
        {"d2p": d2p, "redlines": redlines}[part]()
