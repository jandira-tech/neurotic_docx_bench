"""Build the /speed/ page of jandira-tech/neurotic_docx_bench from the bench's speed_10k results.

Reads results/speed_10k/{redlines,pdf}/SUMMARY.md and NOTES.md (whichever exist) and writes
speed_site/index.html. Only headings, paragraphs, bullet lists and pipe tables are used in
those files, so this renders exactly that subset of Markdown.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

BENCH = Path.home() / 'temp/T/neurotic_docx_bench/results/speed_10k'
OUT = Path(__file__).parent / 'speed_site'

CSS = """
:root { --bg:#1e1e1e; --panel:#252526; --fg:#ddd; --muted:#888; --accent:#4ea1ff; --border:#3a3a3a; }
body { margin:0 auto; max-width:1200px; padding:16px 24px 48px; font:14px/1.5 -apple-system, Helvetica, Arial, sans-serif; background:var(--bg); color:var(--fg); }
a { color:var(--accent); }
h1 { font-size:22px; } h2 { font-size:17px; margin-top:28px; border-bottom:1px solid var(--border); padding-bottom:4px; }
h3 { font-size:15px; }
table { border-collapse:collapse; margin:8px 0 16px; font-variant-numeric:tabular-nums; }
th, td { border:1px solid var(--border); padding:3px 8px; }
th { background:var(--panel); } td.n { text-align:right; }
code { background:#333; padding:0 4px; border-radius:3px; }
section { margin-bottom:40px; }
nav { color:var(--muted); font-size:13px; }
"""


def inline(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    return re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', s)


def render(md: str, shift: int = 0) -> str:
    out: list[str] = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith('#'):
            level = len(ln) - len(ln.lstrip('#'))
            out.append(f'<h{level + shift}>{inline(ln[level:].strip())}</h{level + shift}>')
        elif ln.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                rows.append([c.strip() for c in lines[i].strip('|').split('|')])
                i += 1
            head, body = rows[0], [r for r in rows[1:] if not set(''.join(r)) <= set('-:')]
            out.append('<table><tr>' + ''.join(f'<th>{inline(c)}</th>' for c in head) + '</tr>')
            for r in body:
                cells = ''.join(
                    f'<td class="n">{inline(c)}</td>' if re.fullmatch(r'[-\d.,]+', c) else f'<td>{inline(c)}</td>'
                    for c in r
                )
                out.append(f'<tr>{cells}</tr>')
            out.append('</table>')
            continue
        elif ln.startswith('- '):
            items = []
            while i < len(lines) and (lines[i].startswith('- ') or lines[i].startswith('  ')):
                if lines[i].startswith('- '):
                    items.append(lines[i][2:])
                else:
                    items[-1] += ' ' + lines[i].strip()
                i += 1
            out.append('<ul>' + ''.join(f'<li>{inline(t)}</li>' for t in items) + '</ul>')
            continue
        elif ln.strip():
            para = [ln]
            while i + 1 < len(lines) and lines[i + 1].strip() and lines[i + 1][0] not in '#|-':
                i += 1
                para.append(lines[i])
            out.append(f'<p>{inline(" ".join(para))}</p>')
        i += 1
    return '\n'.join(out)


def main() -> None:
    parts = []
    for name, title in (('redlines', 'Redline generation'), ('pdf', 'DOCX to PDF')):
        d = BENCH / name
        if not (d / 'SUMMARY.md').exists():
            parts.append(f'<section id="{name}"><h2>{title}</h2><p>Not measured yet.</p></section>')
            continue
        body = render((d / 'SUMMARY.md').read_text(), shift=1)
        if (d / 'NOTES.md').exists():
            body += render((d / 'NOTES.md').read_text(), shift=2)
        parts.append(f'<section id="{name}">{body}</section>')
    page = f"""<!doctype html>
<meta charset="utf-8">
<title>Speed: jubarte, docxodus, SuperDoc, docxide, LibreOffice</title>
<style>{CSS}</style>
<nav><a href="../">DOCX to PDF engines</a> &middot; <a href="../redlines/">Redlines vs Microsoft Word</a> &middot; Speed</nav>
<h1>Speed on 10,000 varied inputs</h1>
<p>Every tool gets the same planned inputs, one tool at a time on one machine (Apple M4 Pro, 12 cores, 24 GB, macOS).
Times are per call. Nothing produced is kept: each redline or PDF is deleted once it is timed.
The raw per-call rows are in the bench repository under <code>results/speed_10k/</code>.</p>
{''.join(parts)}
"""
    OUT.mkdir(exist_ok=True)
    (OUT / 'index.html').write_text(page)
    print(f'wrote {OUT / "index.html"}')


if __name__ == '__main__':
    main()
