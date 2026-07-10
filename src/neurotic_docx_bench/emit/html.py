"""Minimal self-contained HTML report for JSONL lines (per-tool aggregate + per-doc scores)."""

from __future__ import annotations

import html
import json


def render_html(lines: list[dict]) -> str:
    """Render one or more tool-run lines as a single self-contained HTML page."""
    sections = []
    for ln in lines:
        agg = ln.get("aggregate", {})
        agg_rows = "".join(
            f"<tr><td>{html.escape(k)}</td><td>{html.escape(str(v))}</td></tr>"
            for k, v in agg.items()
        )
        scores = ln.get("scores", {})
        score_rows = "".join(
            f"<tr><td>{html.escape(k)}</td><td>{v:.2f}</td></tr>"
            for k, v in sorted(scores.items())
        )
        sections.append(
            f"<section><h2>{html.escape(str(ln.get('tool')))} "
            f"({html.escape(str(ln.get('render')))})</h2>"
            f"<p>version {html.escape(str(ln.get('tool_version') or 'n/a'))} · "
            f"{ln.get('n_docs')} docs · baseline "
            f"<code>{html.escape(str(ln.get('baseline_ref')))}</code></p>"
            f"<table class=agg><thead><tr><th>metric</th><th>value</th></tr></thead>"
            f"<tbody>{agg_rows}</tbody></table>"
            f"<details><summary>per-document scores</summary>"
            f"<table><thead><tr><th>document</th><th>score</th></tr></thead>"
            f"<tbody>{score_rows}</tbody></table></details></section>",
        )
    body = "\n".join(sections)
    return (
        "<!doctype html><meta charset=utf-8><title>neurotic-docx-bench</title>"
        "<style>body{font-family:system-ui,sans-serif;margin:2rem;max-width:60rem}"
        "table{border-collapse:collapse;margin:.5rem 0}td,th{border:1px solid #ccc;"
        "padding:.2rem .5rem;text-align:left}th{background:#f4f4f4}"
        "td+td,th+th{text-align:right}</style>"
        "<h1>neurotic-docx-bench</h1>" + body
    )


def dumps_lines(lines: list[dict]) -> str:
    """JSON payload (used by richer viewers / debugging)."""
    return json.dumps(lines, indent=2, sort_keys=True)
