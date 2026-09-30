"""Score the neurotic-docx-bench corpus/word PDFs with docxide's own page-metrics.

For every corpus document, each engine's PDF (already converted by the bench runs) is
compared with Word's PDF: mutool at 150 DPI, docxide `page-metrics` (Jaccard, SSIM,
text boundary). Page images are deleted per document. PyMuPDF Pro is unlicensed and
converts only the first 3 pages, so it is scored only where Word's PDF has <= 3 pages
(the bench's below-3-pages set).

    JOBS=8 python3 score_corpus.py        # -> corpus_scores.json
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent / "neurotic_docx_bench" / "results"
METRICS_BIN = HERE / "docxide-pdf" / "tools" / "target" / "release" / "page-metrics"
WORD = BENCH / "jubarte_0.9.3_docx_to_pdf_work" / "oracle"
ENGINES = {
    "jubarte": BENCH / "jubarte_0.9.3_docx_to_pdf_work" / "jubarte" / "candidate",
    "generated": BENCH / "docxide_0.17.1_work" / "candidate",
    "libreoffice": BENCH / "soffice_26.8.0.3_work" / "candidate",
    "pymupdf": BENCH / "pymupdf-pro_1.28.2_work" / "candidate",
}
METRICS = ["jaccard", "ssim", "text_boundary"]
OUT = HERE / "corpus_scores.json"


def draw(pdf: Path, out: Path) -> int:
    out.mkdir(parents=True)
    subprocess.run(["mutool", "draw", "-q", "-F", "png", "-r", "150", "-o", str(out / "page_%03d.png"), str(pdf)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return len(list(out.glob("page_*.png")))


def score(stem: str) -> dict:
    ref = WORD / f"{stem}.pdf"
    row: dict = {"stem": stem, "scores": {}, "pages": {}}
    with tempfile.TemporaryDirectory(prefix="corpus_", dir=HERE / "work") as tmp:
        tmp = Path(tmp)
        row["pages"]["reference"] = n_ref = draw(ref, tmp / "reference")
        for key, folder in ENGINES.items():
            pdf = folder / f"{stem}.pdf"
            if not pdf.is_file():
                continue
            row["pages"][key] = draw(pdf, tmp / key)
            if key == "pymupdf" and n_ref > 3:
                continue
            r = subprocess.run([str(METRICS_BIN), str(ref), str(pdf), str(tmp / "reference"), str(tmp / key)],
                               capture_output=True, text=True)
            try:
                m = json.loads(r.stdout)
            except ValueError:
                continue
            s = {k: round(m[k] * 100, 1) for k in METRICS if m.get(k) is not None}
            if s:
                row["scores"][key] = s
            shutil.rmtree(tmp / key)
    return row


def main() -> None:
    (HERE / "work").mkdir(exist_ok=True)
    stems = sorted(p.stem for p in WORD.glob("*.pdf"))
    done = {}
    if OUT.exists():
        done = {r["stem"]: r for r in json.loads(OUT.read_text())}
    todo = [s for s in stems if s not in done]
    print(f"{len(stems)} documents, {len(todo)} to score", flush=True)
    with ThreadPoolExecutor(max_workers=int(os.environ.get("JOBS", "8"))) as pool:
        for i, row in enumerate(pool.map(score, todo), 1):
            done[row["stem"]] = row
            if i % 100 == 0 or i == len(todo):
                OUT.write_text(json.dumps([done[s] for s in stems if s in done]))
                print(f"{i}/{len(todo)}", flush=True)
    print("corpus scores written", flush=True)


if __name__ == "__main__":
    main()
