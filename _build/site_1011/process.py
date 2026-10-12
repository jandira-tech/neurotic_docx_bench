"""Score and encode the 2026-10-11 site cases; everything lands under build/<prefix>/ for R2.

    uv run --with pillow python process.py d2p        # 800 corpus documents: Word, jubarte, soffice
    uv run --with pillow python process.py fixtures   # 76 docxide `cases` fixtures: Word, jubarte, soffice
    uv run --with pillow python process.py redlines   # 1000 pairs: Word compare, jubarte, docxodus

Scores: docxide-pdf page-metrics (Jaccard, SSIM, text boundary) at 150 DPI over every page,
the scorer behind every other row of the site. Shown pages: a docxide fixture shows its first 3
(its kept columns show those); every other case shows every page of Word's PDF (the images live on
R2, so no page sample is needed), the same page numbers for every engine. Images: 120 DPI (180 DPI
raster, downscaled 2/3), 16-colour lossless WebP. PDF link: the shown pages as one compressed PDF
(mutool clean -gggz): pages.pdf for the first 3, all.pdf for a whole document.
"""

from __future__ import annotations

import csv
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

H = Path(__file__).parent
BUILD = H / "build"
BENCH = Path("/Users/arthrod/temp/T/neurotic_docx_bench")
CORPUS = BENCH / "corpus/word"
RUN = BENCH / "results/site_1011"
FIXTURES = Path("/Users/arthrod/temp/T/docxide-pdf/tests/fixtures/cases")
METRICS_BIN = Path("/Users/arthrod/temp/T/docxide-pdf/tools/target/release/page-metrics")
METRICS = ["jaccard", "ssim", "text_boundary"]
JOBS = 5  # Word renders alongside


def page_count(pdf: Path) -> int:
    out = subprocess.run(["mutool", "info", str(pdf)], capture_output=True, text=True).stdout
    m = re.search(r"Pages:\s*(\d+)", out)
    return int(m.group(1)) if m else 0


def draw(pdf: Path, out: Path, dpi: int = 150, pages: str = "") -> int:
    out.mkdir(parents=True, exist_ok=True)
    cmd = ["mutool", "draw", "-q", "-F", "png", "-r", str(dpi), "-o", str(out / "page_%03d.png"), str(pdf)]
    if pages:
        cmd.append(pages)
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return len(list(out.glob("page_*.png")))


def metrics(ref: Path, pdf: Path, ref_dir: Path, dir_: Path) -> dict:
    r = subprocess.run([str(METRICS_BIN), str(ref), str(pdf), str(ref_dir), str(dir_)], capture_output=True, text=True)
    try:
        m = json.loads(r.stdout)
    except ValueError:
        return {}
    return {k: round(m[k] * 100, 1) for k in METRICS if m.get(k) is not None}




def encode(png: Path, dst: Path) -> None:
    im = Image.open(png).convert("RGB")
    im = im.resize((round(im.width * 2 / 3), round(im.height * 2 / 3)), Image.Resampling.LANCZOS)
    im = im.quantize(colors=16, method=Image.Quantize.MEDIANCUT)
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, "WEBP", lossless=True, method=4)


def case(prefix: str, group: str, cid: str, ref: Path, cands: dict[str, Path], extra: dict | None = None,
         first: int = 0) -> dict:
    """Score every candidate against ref, encode the shown pages of all, write the page PDFs."""
    base = BUILD / prefix / group / cid
    row = {"group": group, "case": cid, "pages": {}, "page_counts": {}, "scores": {}, "pdfs": {}, "times": {},
           "errors": {}, **(extra or {})}
    with tempfile.TemporaryDirectory(prefix="c_", dir=BUILD) as tmp:
        tmp = Path(tmp)
        n_ref = draw(ref, tmp / "reference")
        row["page_counts"]["reference"] = n_ref
        for key, pdf in cands.items():
            if not pdf.is_file() or pdf.stat().st_size == 0:
                row["errors"][key] = "no output"
                continue
            row["page_counts"][key] = draw(pdf, tmp / key)
            s = metrics(ref, pdf, tmp / "reference", tmp / key) if row["page_counts"][key] else {}
            if s:
                row["scores"][key] = s
            shutil.rmtree(tmp / key, ignore_errors=True)
        # first=N: the columns this case keeps show its first N pages, so the new ones must too.
        show = list(range(1, (min(first, n_ref) if first else n_ref) + 1))
        row["shown"] = show
        for key, pdf in (({} if first else {"reference": ref}) | cands).items():
            n = row["page_counts"].get(key, 0)
            if not n:
                continue
            want = [p for p in show if p <= n]
            if not want:
                row["pages"][key] = []
                continue
            spec = ",".join(map(str, want))
            d = tmp / f"img_{key}"
            draw(pdf, d, 180, spec)
            pngs = sorted(d.glob("page_*.png"))  # numbered 1..len(want) in order
            paths = []
            for p, png in zip(want, pngs):
                dst = base / key / f"page_{p:03d}.webp"
                encode(png, dst)
                paths.append(dst.relative_to(BUILD).as_posix())
            # The viewer indexes pages by position; a page a short candidate lacks stays a gap.
            row["pages"][key] = [paths[want.index(p)] if p in want else None for p in show]
            sub = base / key / ("pages.pdf" if first else "all.pdf")  # a new key: R2 objects are immutable
            subprocess.run(["mutool", "clean", "-gggz", str(pdf), str(sub), spec],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            if sub.is_file():
                row["pdfs"][key] = sub.relative_to(BUILD).as_posix()
            shutil.rmtree(d, ignore_errors=True)
    return row


def d2p_jobs() -> list:
    rows = list(csv.DictReader(open(H / "sample_docx_to_pdf.csv")))
    out = []
    for r in rows:
        stem = f"{r['state']}__{r['stem']}"
        out.append(("d2p", f"corpus/{r['state']}", r["id"], CORPUS / r["pdf"],
                    {"jubarte": RUN / "jubarte-convert/pdf" / f"{stem}.pdf",
                     "libreoffice": RUN / "soffice/pdf" / f"{stem}.pdf"},
                    {"stem": stem, "lang": r["lang"], "type": r["type"]}))
    return out


def fixture_jobs() -> list:
    out = []
    for fx in sorted(FIXTURES.iterdir()):
        if (fx / "reference.pdf").is_file() and (fx / "input.docx").is_file():
            out.append(("d2p", "cases", fx.name, fx / "reference.pdf",
                        {"jubarte": RUN / "fixtures/jubarte" / f"{fx.name}.pdf",
                         "libreoffice": RUN / "fixtures/soffice" / f"{fx.name}.pdf"}, {}, 3))
    return out


def redline_jobs() -> list:
    rows = list(csv.DictReader(open(H / "sample_redlines.csv")))
    out = []
    for r in rows:
        out.append(("redlines", f"redlines/{r['state']}", r["id"], RUN / "word_compare/out" / f"{r['id']}__vs__{r['id']}.pdf",
                    {"jubarte": RUN / "word_render/jubarte" / f"{r['id']}.pdf",
                     "docxodus": RUN / "word_render/docxodus" / f"{r['id']}_docxodus.pdf"},
                    {"lang": r["lang"], "type": r["type"], "sets": r["sets"]}))
    return out


def main() -> None:
    which = sys.argv[1]
    jobs = {"d2p": d2p_jobs, "fixtures": fixture_jobs, "redlines": redline_jobs}[which]()
    BUILD.mkdir(exist_ok=True)
    jobs = [j for j in jobs if j[3].is_file()]
    with ThreadPoolExecutor(JOBS) as ex:
        rows = list(ex.map(lambda j: case(*j), jobs))
    (BUILD / f"cases_{which}.json").write_text(json.dumps(rows, indent=1))
    print(f"{which}: {len(rows)} cases -> {BUILD / f'cases_{which}.json'}")


if __name__ == "__main__":
    main()
