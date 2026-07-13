"""emit.gallery — per-run side-by-side visual report (candidate vs Word oracle).

Renders one self-contained HTML page from the rasters the scoring pipeline
already persists under ``<run_dir>/score/<key>/{candidate,oracle}/page_NNNN.png``.
Documents are ordered worst-first (ascending score) so the page reads as a
triage list; a score index at the top anchors into each document's section.

The page references the PNGs by relative path, so it must live in ``run_dir``
(next to ``score/``) — :func:`write_gallery` handles that.
"""

from __future__ import annotations

import html
import statistics
from pathlib import Path

_STYLE = (
    "body{font-family:system-ui,sans-serif;margin:20px;background:#1b1b1f;color:#ddd}"
    "h2{position:sticky;top:0;background:#1b1b1f;padding:8px 0;"
    "border-bottom:2px solid #e66;font-size:15px;margin:24px 0 4px}"
    ".pair{display:flex;gap:8px;margin:10px 0}.pair>div{flex:1;min-width:0}"
    "img{width:100%;border:1px solid #444;background:#fff}"
    "h4{margin:4px 0;font-weight:500;color:#9ac}"
    "table{border-collapse:collapse;margin:.5rem 0}td,th{border:1px solid #444;"
    "padding:.2rem .6rem;text-align:left}th{background:#26262b}"
    "a{color:#9ac}p.missing{color:#e66}"
)


def _pages(dir_: Path) -> list[str]:
    if not dir_.is_dir():
        return []
    return sorted(p.name for p in dir_.glob("page_*.png"))


def _fmt(score: float | None) -> str:
    return "n/a" if score is None else f"{score:.2f}"


def render_gallery(
    scores: dict[str, float | None],
    score_dir: Path,
    *,
    title: str,
    rel_prefix: str = "score",
    limit: int | None = None,
) -> str:
    """Render the worst-first candidate-vs-oracle gallery as one HTML page.

    ``scores`` maps document key → overall score (``None`` sorts first, as a
    failure to score is the worst outcome). ``score_dir`` is the pipeline's
    raster tree; ``rel_prefix`` is how the page reaches it relative to where
    the HTML file will live. ``limit`` caps the number of documents (worst
    first); the score index always lists every document.
    """
    ordered = sorted(scores.items(), key=lambda kv: (kv[1] is not None, kv[1]))
    vals = [v for v in scores.values() if v is not None]
    summary = (
        f"n {len(scores)} · mean {statistics.mean(vals):.2f} · "
        f"median {statistics.median(vals):.2f} · min {min(vals):.2f} · max {max(vals):.2f}"
        if vals
        else f"n {len(scores)} · no scored documents"
    )
    index_rows = "".join(
        f'<tr><td><a href="#{html.escape(k)}">{html.escape(k)}</a></td>'
        f"<td>{_fmt(v)}</td></tr>"
        for k, v in ordered
    )
    shown = ordered if limit is None else ordered[:limit]
    sections = []
    for key, score in shown:
        cand = _pages(score_dir / key / "candidate")
        orac = _pages(score_dir / key / "oracle")
        cells = []
        for page in sorted(set(cand) | set(orac)):
            n = int(page[5:9]) if page[5:9].isdigit() else 0
            c_img = (
                f'<img loading="lazy" src="{rel_prefix}/{html.escape(key)}/candidate/{page}">'
                if page in cand
                else '<p class="missing">missing page</p>'
            )
            o_img = (
                f'<img loading="lazy" src="{rel_prefix}/{html.escape(key)}/oracle/{page}">'
                if page in orac
                else '<p class="missing">missing page</p>'
            )
            cells.append(
                f'<div class="pair"><div><h4>candidate p{n}</h4>{c_img}</div>'
                f'<div><h4>Word oracle p{n}</h4>{o_img}</div></div>',
            )
        if not cells:
            cells.append('<p class="missing">no rasters persisted for this document</p>')
        sections.append(
            f'<section id="{html.escape(key)}">'
            f"<h2>{html.escape(key)} — {_fmt(score)}</h2>{''.join(cells)}</section>",
        )
    return (
        f"<!doctype html><meta charset=utf-8><title>{html.escape(title)}</title>"
        f"<style>{_STYLE}</style><h1>{html.escape(title)}</h1><p>{summary}</p>"
        f"<details open><summary>score index (worst first)</summary>"
        f"<table><thead><tr><th>document</th><th>score</th></tr></thead>"
        f"<tbody>{index_rows}</tbody></table></details>"
        f"{''.join(sections)}"
    )


def write_gallery(
    run_dir: Path,
    scores: dict[str, float | None],
    *,
    title: str,
    limit: int | None = None,
) -> Path:
    """Write the gallery next to the run's ``score/`` tree and return its path."""
    out = run_dir / "report.html"
    out.write_text(
        render_gallery(scores, run_dir / "score", title=title, limit=limit),
        encoding="utf-8",
    )
    return out
