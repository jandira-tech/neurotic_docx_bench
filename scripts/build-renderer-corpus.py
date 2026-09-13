#!/usr/bin/env python3
"""Build the three-way DOCX-to-PDF renderer corpus.

This is adapted from docxide-pdf's Apache-2.0 ``tools/engine_compare.py`` on
its ``add-jubarte-redlines`` branch.  The upstream comparison tool's useful
invariant is retained here: every engine is keyed by the same source DOCX
stem and the Word PDF is the reference, not a generated approximation.

The Word PDFs already committed under ``pdf_source`` and
``pdf_source_randomized`` are copied into the corpus; Word is not invoked by
this script.  Jubarte and docxide-pdf are rendered from the same 398 source
DOCX files.

Usage:
    python3 scripts/build-renderer-corpus.py
    python3 scripts/build-renderer-corpus.py --force

The output is intentionally a separate corpus from the benchmark work trees:
``corpus/no_comments_pdf_was_generated_by_word/renderer_corpus``.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORD_ROOT = ROOT / "corpus" / "no_comments_pdf_was_generated_by_word"
OUT = WORD_ROOT / "renderer_corpus"
DOCXIDE_WORK = ROOT / "results" / "docx_to_pdf_work" / "docxide-pdf" / "candidate"

POOLS = (
    ("source", WORD_ROOT / "docx_source", WORD_ROOT / "pdf_source"),
    ("source_randomized", WORD_ROOT / "docx_source_randomized", WORD_ROOT / "pdf_source_randomized"),
)


def _tool(env_name: str, defaults: tuple[Path, ...]) -> Path:
    value = os.environ.get(env_name)
    if value:
        return Path(value).expanduser().resolve()
    for candidate in defaults:
        if candidate.is_file():
            return candidate.resolve()
    raise SystemExit(f"{env_name} not found; set {env_name} to the pinned executable")


def _copy_word_and_docxide(force: bool) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for pool, docx_dir, word_dir in POOLS:
        for docx in sorted(docx_dir.glob("*.docx")):
            stem = docx.stem
            word = word_dir / f"{stem}.pdf"
            if not word.is_file():
                raise SystemExit(f"missing committed Word PDF for {docx}")
            source = docx
            word_out = OUT / "word" / f"{pool}__{stem}.pdf"
            docxide_out = OUT / "docxide-pdf" / f"{pool}__{stem}.pdf"
            word_out.parent.mkdir(parents=True, exist_ok=True)
            docxide_out.parent.mkdir(parents=True, exist_ok=True)
            if force or not word_out.exists():
                shutil.copy2(word, word_out)
            cached = DOCXIDE_WORK / f"{pool}__{stem}.pdf"
            if not cached.is_file():
                # The evaluator prefixes the pool name in its candidate tree.
                # Keep this explicit rather than falling back to a same-stem glob;
                # source and source_randomized intentionally share many stems.
                raise SystemExit(
                    f"missing docxide-pdf output {cached}; run the no-redline evaluation first"
                )
            if force or not docxide_out.exists():
                shutil.copy2(cached, docxide_out)
            rows.append({
                "pool": pool,
                "stem": stem,
                "source": str(source.relative_to(ROOT)),
                "word": str(word_out.relative_to(ROOT)),
                "docxide-pdf": str(docxide_out.relative_to(ROOT)),
            })
    return rows


def _git_revision(path: Path) -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _render_one(jubarte: Path, source: Path, out: Path, force: bool) -> tuple[Path, str | None]:
    if out.exists() and not force:
        return out, None
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [str(jubarte), "convert", str(source), "-o", str(out), "--force"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode or not out.is_file():
        detail = (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()
        return out, detail
    return out, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="regenerate/copy every corpus artifact")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    jubarte = _tool(
        "JUBARTE_BIN",
        (
            ROOT.parent / "jubarte-redlines" / "target" / "release" / "jubarte",
            Path.home() / ".cargo" / "bin" / "jubarte",
        ),
    )
    rows = _copy_word_and_docxide(args.force)
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = []
        for row in rows:
            out = OUT / "jubarte" / f"{row['pool']}__{row['stem']}.pdf"
            row["jubarte"] = str(out.relative_to(ROOT))
            futures.append(pool.submit(_render_one, jubarte, ROOT / row["source"], out, args.force))
        for future in as_completed(futures):
            out, error = future.result()
            if error:
                failures.append(f"{out}: {error}")
    if failures:
        raise SystemExit("Jubarte render failures:\n" + "\n".join(sorted(failures)))

    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": 1,
        "comparison_tool_source": {
            "repository": "https://github.com/sverrejb/docxide-pdf",
            "branch": "add-jubarte-redlines-engine",
            "commit": "1c83074a2f35a8a0a8bdd40642247b0e0c9abf08",
            "license": "Apache-2.0",
        },
        "source": "corpus/no_comments_pdf_was_generated_by_word/docx_source + docx_source_randomized",
        "reference": "Microsoft Word PDFs already committed in pdf_source + pdf_source_randomized",
        "engines": {
            "word": "Microsoft Word reference PDFs",
            "jubarte": {
                "binary": "../jubarte-redlines/target/release/jubarte",
                "repository_revision": _git_revision(ROOT.parent / "jubarte-redlines"),
            },
            "docxide-pdf": {
                "binary": "~/.cargo/bin/docxide-pdf",
                "repository_revision": _git_revision(ROOT.parent / "docxide-pdf"),
            },
        },
        "documents": rows,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    cases = [
        {
            "pool": row["pool"],
            "stem": row["stem"],
            "files": {
                "word": Path(row["word"]).name,
                "jubarte": Path(row["jubarte"]).name,
                "docxide-pdf": Path(row["docxide-pdf"]).name,
            },
        }
        for row in rows
    ]
    (OUT / "index.html").write_text(_comparison_html(cases), encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Renderer corpus\n\n"
        "Open [`index.html`](index.html) to compare every case side by side in a browser.\n\n"
        "Each source DOCX has three same-stem PDFs: `word/` (the committed Word reference), "
        "`jubarte/`, and `docxide-pdf/`. The source DOCX files remain in the canonical "
        "`docx_source/` and `docx_source_randomized/` directories.\n\n"
        "The comparison layout is adapted from `sverrejb/docxide-pdf`'s Apache-2.0 "
        "`tools/engine_compare.py` on the `add-jubarte-redlines` branch; see "
        "`licenses/docxide-pdf-Apache-2.0.txt`.\n",
        encoding="utf-8",
    )
    print(f"built {len(rows)} three-way renderer cases in {OUT}")
    return 0


def _comparison_html(cases: list[dict[str, object]]) -> str:
    """A dependency-free local viewer: three same-case PDF panes side by side."""
    import html
    import json

    payload = json.dumps(cases, separators=(",", ":"))
    options = "".join(
        f'<option value="{i}">{html.escape(str(c["pool"]))} / '
        f'{html.escape(str(c["stem"]))}</option>'
        for i, c in enumerate(cases)
    )
    return f'''<!doctype html>
<meta charset="utf-8">
<title>DOCX renderer comparison</title>
<style>
body {{ margin:0; font:14px system-ui,sans-serif; color:#222; }}
header {{ position:sticky; top:0; z-index:2; padding:10px; background:#222; color:#fff; }}
select {{ max-width:70vw; padding:5px; }}
.grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; padding:8px; align-items:start; }}
.column {{ min-width:0; }}
h2 {{ position:sticky; top:52px; z-index:1; margin:0 0 6px; padding:6px 0; font-size:16px; background:#fff; }}
.page {{ margin:0 0 12px; border:1px solid #bbb; background:#eee; }}
canvas {{ width:100%; height:auto; display:block; background:#fff; }}
small {{ color:#bbb; margin-left:12px; }}
.status {{ color:#666; padding:8px; }}
</style>
<header><button id="previous" type="button">Previous</button> <button id="next" type="button">Next</button> <label>Case <select id="case">{options}</select></label><small>Word · docxide-pdf · Jubarte · use ←/→ or J/K to change cases</small></header>
<main id="grid" class="grid"><div class="status">Select a case.</div></main>
<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
<script>
const cases={payload}; const sel=document.querySelector('#case');
const previous=document.querySelector('#previous'), next=document.querySelector('#next');
const engines=[['word','Microsoft Word'],['docxide-pdf','docxide-pdf'],['jubarte','Jubarte']];
function move(delta) {{ sel.selectedIndex=(Number(sel.value)+delta+cases.length)%cases.length; show(); }}
previous.addEventListener('click',()=>move(-1)); next.addEventListener('click',()=>move(1));
document.addEventListener('keydown',event=>{{ if (event.target===sel) return; if (event.key==='ArrowLeft'||event.key.toLowerCase()==='k') move(-1); if (event.key==='ArrowRight'||event.key.toLowerCase()==='j') move(1); }});
pdfjsLib.GlobalWorkerOptions.workerSrc='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
async function loadPdf(url) {{ return pdfjsLib.getDocument(url).promise; }}
async function show() {{
  const c=cases[Number(sel.value)], grid=document.querySelector('#grid'); grid.replaceChildren();
  const columns=engines.map(([key,label]) => {{ const col=document.createElement('section'); col.className='column'; col.innerHTML='<h2>'+label+'</h2>'; grid.append(col); return col; }});
  try {{
    const pdfs=await Promise.all(engines.map(([key]) => loadPdf(key+'/'+c.files[key])));
    const pageCount=Math.max(...pdfs.map(pdf => pdf.numPages));
    for (let pageNo=1; pageNo<=pageCount; pageNo++) {{
      await Promise.all(pdfs.map(async (pdf, i) => {{
        const page=columns[i].appendChild(document.createElement('div')); page.className='page';
        if (pageNo>pdf.numPages) {{ page.textContent='No page '+pageNo; return; }}
        const p=await pdf.getPage(pageNo), viewport=p.getViewport({{scale:1.35}}), canvas=document.createElement('canvas');
        canvas.width=viewport.width; canvas.height=viewport.height; page.append(canvas);
        await p.render({{canvasContext:canvas.getContext('2d'),viewport}}).promise;
      }}));
    }}
  }} catch (e) {{ grid.innerHTML='<div class="status">Could not load PDFs: '+e+'</div>'; }}
}}
sel.addEventListener('change',show); show();
</script>'''


if __name__ == "__main__":
    raise SystemExit(main())
