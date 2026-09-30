"""Build jubarte's DOCX->PDF engine comparison site (jubarte_site/), for GitHub Pages.

Two document sets, every DOCX->PDF engine we measure, all scored against Microsoft Word's
own PDF with docxide-pdf's page-metrics (Jaccard, SSIM, text boundary at 150 DPI):

- docxide fixtures: the 208 documents of docxide-pdf's published comparison
  (sverrejb.github.io/docxide-pdf, CI build 2026-09-15). Its engines and scores are taken
  as published; jubarte and PyMuPDF Pro were converted and scored here.
- corpus sample: a seeded random sample of neurotic-docx-bench corpus/word, stratified by
  document state and page count. Engine PDFs come from the bench runs (jubarte, docxide,
  soffice, PyMuPDF Pro); MiniPdf, rdocx and office2pdf are converted here.

Scores always cover every page of a document. Only the first 3 pages are shown, as
100 DPI 16-colour lossless WebP (150 DPI raster, downscaled), to keep the site small.
PyMuPDF Pro is unlicensed (first 3 pages only), so it is run only on documents whose
Word PDF has at most 3 pages.

    uv run --with pillow python build_site.py
"""

from __future__ import annotations

import io
import json
import os
import random
import re
import shutil
import subprocess
import tempfile
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

import add_jubarte as aj
import viewer_features

HERE = aj.HERE
OUT = HERE / "jubarte_site"
BENCH = HERE.parent / "neurotic_docx_bench"
CORPUS = BENCH / "corpus" / "word"
TOOLS_BIN = HERE / "tools" / "bin"
WORD_FONTS = aj.WORD_FONTS
SHOW_PAGES = 3
SAMPLE_N = int(os.environ.get("SAMPLE_N", "600"))
SEED = 20260928
JOBS = int(os.environ.get("JOBS", "8"))
EXTRA = ("minipdf", "rdocx", "office2pdf")  # converted here for the corpus sample
STATES = ["clean", "tracking_without_comments", "with_comments_clean", "with_comments_tracking"]
DOCXIDE_GROUPS = ["cases", "scraped", "new", "samples"]
ENGINES = [
    ["reference", "Word"],
    ["jubarte", "jubarte"],
    ["generated", "docxide-pdf"],
    ["libreoffice", "LibreOffice"],
    ["pymupdf", "PyMuPDF Pro"],
    ["minipdf", "MiniPdf (Rust)"],
    ["rdocx", "rdocx"],
    ["office2pdf", "office2pdf"],
]
VERSIONS = {
    "reference": "Microsoft Word for Mac",
    "jubarte": "0.9.3 --revisions word",
    "generated": "0.17.1",
    "libreoffice": "26.2.5.2 (docxide fixtures) / 26.8.0.3 (corpus)",
    "pymupdf": "1.28.2 unlicensed, documents up to 3 pages",
    "minipdf": "0.6.0",
    "rdocx": "0.13.1",
    "office2pdf": "0.7.0",
}


def bin_of(pages: int) -> str:
    return str(pages) if pages <= 3 else ("4-6" if pages <= 6 else "7+")


def pick_sample(rows: list[dict]) -> list[dict]:
    """Proportional stratified sample over (state, page bin), largest remainder, fixed seed."""
    strata: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        strata[(r["stem"].split("__")[0], bin_of(r["pages"]["reference"]))].append(r)
    total = len(rows)
    quota = {k: SAMPLE_N * len(v) / total for k, v in strata.items()}
    take = {k: int(q) for k, q in quota.items()}
    for k in sorted(quota, key=lambda k: quota[k] - take[k], reverse=True)[: SAMPLE_N - sum(take.values())]:
        take[k] += 1
    rng = random.Random(SEED)
    picked = []
    for k in sorted(strata):
        picked += rng.sample(sorted(strata[k], key=lambda r: r["stem"]), take[k])
    return sorted(picked, key=lambda r: r["stem"])


def docx_of(stem: str) -> Path:
    state, name = stem.split("__", 1)
    return CORPUS / state / "docx" / f"{name}.docx"


def extra_cmd(tool: str, docx: Path, pdf: Path) -> list[str]:
    # Same invocations as docxide-pdf's engine_compare.py; Word's own font folder stands in
    # for docxide's private font pack.
    if tool == "minipdf":
        return [str(TOOLS_BIN / "minipdf"), "convert", str(docx), "-o", str(pdf), "--fonts", str(WORD_FONTS)]
    if tool == "rdocx":
        return [str(TOOLS_BIN / "rdocx"), "convert", "--to", "pdf", "--output", str(pdf), str(docx)]
    return [str(Path.home() / ".cargo" / "bin" / "office2pdf"), str(docx), "-o", str(pdf), "--font-path", str(WORD_FONTS)]


def score_extra(row: dict) -> dict:
    """Convert one corpus document with MiniPdf, rdocx and office2pdf; score each against Word."""
    stem = row["stem"]
    work = HERE / "work" / "corpus" / stem
    work.mkdir(parents=True, exist_ok=True)
    ref = aj.HERE.parent / "neurotic_docx_bench" / "results" / "jubarte_0.9.3_docx_to_pdf_work" / "oracle" / f"{stem}.pdf"
    out = {"stem": stem, "scores": {}, "pages": {}, "errors": {}}
    ref_dir = work / "reference_png"
    aj.pngs(ref, ref_dir)
    for tool in EXTRA:
        pdf = work / f"{tool}.pdf"
        if not pdf.is_file():
            ok, _, why = aj.convert(extra_cmd(tool, docx_of(stem), pdf), pdf)
            if not ok:
                pdf.unlink(missing_ok=True)
                out["errors"][tool] = why
                continue
        d = work / f"{tool}_png"
        out["pages"][tool] = len(aj.pngs(pdf, d))
        s = aj.metrics(ref, pdf, ref_dir, d)
        if s:
            out["scores"][tool] = s
        shutil.rmtree(d)
    shutil.rmtree(ref_dir)
    return out


def encode(src: Path | bytes, dst: Path) -> None:
    """150 DPI raster -> 100 DPI, 16-colour palette, lossless WebP."""
    im = Image.open(io.BytesIO(src) if isinstance(src, bytes) else src).convert("RGB")
    im = im.resize((round(im.width * 2 / 3), round(im.height * 2 / 3)), Image.Resampling.LANCZOS)
    im = im.quantize(colors=16, method=Image.Quantize.MEDIANCUT)
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, "WEBP", lossless=True, method=4)


def pdf_pages(pdf: Path, dest: Path) -> list[str]:
    """First SHOW_PAGES pages of a PDF, rastered at 150 DPI, encoded into dest/page_NNN.webp."""
    with tempfile.TemporaryDirectory(prefix="pg_", dir=HERE / "work") as tmp:
        subprocess.run(["mutool", "draw", "-q", "-F", "png", "-r", "150", "-o", f"{tmp}/page_%03d.png",
                        str(pdf), f"1-{SHOW_PAGES}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        out = []
        for p in sorted(Path(tmp).glob("page_*.png")):
            encode(p, dest / f"{p.stem}.webp")
            out.append((dest / f"{p.stem}.webp").relative_to(OUT).as_posix())
    return out


def docxide_case(case: dict, local: dict, pym: dict) -> dict:
    g, c = case["group"], case["case"]
    base = OUT / "docxide" / g / c
    pages, counts = {}, {}
    for key, files in case["pages"].items():  # published engines, 150 DPI lossless WebP
        counts[key] = len(files)
        pages[key] = []
        for rel in files[:SHOW_PAGES]:
            dst = base / key / Path(rel).name
            encode(aj.SITE / rel, dst)
            pages[key].append(dst.relative_to(OUT).as_posix())
    scores = dict(case["scores"])
    for key, pdf, sc in (("jubarte", aj.WORK / g / c / "jubarte.pdf", local.get("jubarte_scores")),
                         ("pymupdf", aj.WORK / g / c / "pymupdf.pdf", pym.get("scores"))):
        if sc and pdf.is_file():
            pages[key] = pdf_pages(pdf, base / key)
            counts[key] = int(subprocess.run(["mutool", "info", str(pdf)], capture_output=True, text=True)
                              .stdout.split("Pages:")[1].split()[0])
            scores[key] = sc
    return {"group": g, "case": c, "pages": pages, "page_counts": counts, "scores": scores,
            "times": case.get("times", {}), "reference_app": case.get("reference_app", "")}


def corpus_case(row: dict, extra: dict) -> dict:
    stem = row["stem"]
    state, name = stem.split("__", 1)
    doc_id = name.split("_")[0]
    base = OUT / "corpus" / state / doc_id
    res = BENCH / "results"
    pdfs = {
        "reference": res / "jubarte_0.9.3_docx_to_pdf_work" / "oracle" / f"{stem}.pdf",
        "jubarte": res / "jubarte_0.9.3_docx_to_pdf_work" / "jubarte" / "candidate" / f"{stem}.pdf",
        "generated": res / "docxide_0.17.1_work" / "candidate" / f"{stem}.pdf",
        "libreoffice": res / "soffice_26.8.0.3_work" / "candidate" / f"{stem}.pdf",
        "pymupdf": res / "pymupdf-pro_1.28.2_work" / "candidate" / f"{stem}.pdf",
        **{t: HERE / "work" / "corpus" / stem / f"{t}.pdf" for t in EXTRA},
    }
    scores = {**row["scores"], **extra["scores"]}
    counts = {**row["pages"], **extra["pages"]}
    pages = {}
    for key, pdf in pdfs.items():
        if key == "pymupdf" and row["pages"]["reference"] > 3:
            continue
        if pdf.is_file():
            pages[key] = pdf_pages(pdf, base / key)
    return {"group": f"corpus/{state}", "case": doc_id, "stem": stem, "pages": pages, "page_counts": counts,
            "scores": scores, "times": {}, "reference_app": pdf_creator(pdfs["reference"])}


def pdf_creator(pdf: Path) -> str:
    """engine_compare.pdf_creator, but a Quartz Producer holds escaped parens it would cut at."""
    info = subprocess.run(["mutool", "info", str(pdf)], capture_output=True, text=True).stdout
    for tag in ("Creator", "Producer"):
        m = re.search(r"/" + tag + r"\(((?:\\.|[^\\)])*)\)", info)
        if m:
            return re.sub(r"\\(.)", r"\1", m.group(1))
    return ""


def patched_template(note: str, mode: str = "convert") -> str:
    t = aj.ec.HTML_TEMPLATE
    swaps = [
        ("<title>Engine comparison</title>", "<title>jubarte DOCX to PDF vs Microsoft Word: engine comparison</title>"),
        ("{ get: r => (r.c.pages.reference || []).length, show: r => (r.c.pages.reference || []).length, num: true },",
         "{ get: r => (r.c.page_counts || {}).reference ?? (r.c.pages.reference || []).length, "
         "show: r => (r.c.page_counts || {}).reference ?? (r.c.pages.reference || []).length, num: true },"),
        ("const s = c.scores[key] || {}; const n = (c.pages[key]||[]).length;",
         "const s = c.scores[key] || {}; const shown = (c.pages[key]||[]).length; "
         "const n = (c.page_counts || {})[key] ?? shown;"),
        ("${ver ? ` <span class=\"ver\">${ver}</span>` : ''} · ${n} p${sc}`;",
         "${ver ? ` <span class=\"ver\">${ver}</span>` : ''} · ${n} p${n > shown ? ` (first ${shown} shown)` : ''}${sc}`;"),
        ("<kbd>1</kbd>-<kbd>6</kbd> engines", "<kbd>1</kbd>-<kbd>8</kbd> engines"),
        ("extra pages are ignored.</span>' +", "extra pages are ignored.</span>" + note + "' +"),
    ]
    for old, new in swaps:
        if t.count(old) != 1:
            raise SystemExit(f"template anchor not found once: {old[:70]}")
        t = t.replace(old, new)
    return viewer_features.patch(t, mode)  # mode drop-down, case filters, random first case


def main() -> None:
    t0 = time.time()
    rows = json.loads((HERE / "corpus_scores.json").read_text())
    if len(rows) != 3554:
        raise SystemExit(f"corpus_scores.json has {len(rows)} rows; wait for score_corpus.py")
    sample = pick_sample(rows)
    (HERE / "sample.json").write_text(json.dumps([r["stem"] for r in sample], indent=1))
    print(f"sample {len(sample)} of {len(rows)} (seed {SEED})", flush=True)

    extra_path = HERE / "corpus_extra_scores.json"
    extra = {r["stem"]: r for r in json.loads(extra_path.read_text())} if extra_path.exists() else {}
    todo = [r for r in sample if r["stem"] not in extra]
    with ThreadPoolExecutor(max_workers=JOBS) as pool:
        for r in pool.map(score_extra, todo):
            extra[r["stem"]] = r
    extra_path.write_text(json.dumps(list(extra.values()), indent=1))
    print(f"extra engines scored ({time.time() - t0:.0f} s)", flush=True)

    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir()
    published = subprocess.run(["git", "-C", str(aj.SITE), "show", "HEAD:index.html"],
                               capture_output=True, text=True, check=True).stdout
    data = json.loads(re.search(r"const DATA = (.*?);\n", published).group(1))
    local = {(r["group"], r["case"]): r for r in json.loads((HERE / "local_scores.json").read_text())["cases"]}
    pym = {(r["group"], r["case"]): r for r in json.loads((HERE / "local_pymupdf.json").read_text())["cases"]}
    with ThreadPoolExecutor(max_workers=JOBS) as pool:
        cases = list(pool.map(lambda c: docxide_case(c, local[(c["group"], c["case"])], pym[(c["group"], c["case"])]), data))
        cases += list(pool.map(lambda r: corpus_case(r, extra[r["stem"]]), sample))
    print(f"images encoded ({time.time() - t0:.0f} s)", flush=True)

    note = ("<span><b>What this is</b>: every DOCX to PDF engine we measure, scored against Microsoft Word&#8217;s own PDF "
            "with docxide-pdf&#8217;s page-metrics at 150 DPI over every page. Two document sets: the 208 "
            "<b>docxide fixtures</b> of docxide-pdf&#8217;s published comparison (its engines and scores as published "
            "on 2026-09-15; jubarte and PyMuPDF Pro added here) and a " + str(len(sample)) + "-document random "
            "<b>corpus sample</b> of neurotic-docx-bench corpus/word, stratified by state and page count. Only the "
            "first 3 pages are shown, at 100 DPI. PyMuPDF Pro runs unlicensed (first 3 pages only), so it is "
            "measured only on documents of at most 3 pages. Viewer, scorer and docxide fixtures: "
            "<a href=\"https://github.com/sverrejb/docxide-pdf\" style=\"color:var(--accent)\">sverrejb/docxide-pdf</a> "
            "(Apache-2.0, see NOTICE.md).</span>")
    assert "'" not in note
    aj.ec.HTML_TEMPLATE = patched_template(note)
    aj.ec.ENGINES = ENGINES
    aj.ec.GROUPS = DOCXIDE_GROUPS + [f"corpus/{s}" for s in STATES]
    aj.ec.write_html(cases, VERSIONS, OUT / "index.html")
    (OUT / ".nojekyll").touch()
    shutil.copy(HERE / "NOTICE.md", OUT / "NOTICE.md")
    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    n_img = sum(1 for _ in OUT.rglob("*.webp"))
    print(f"site {OUT}: {len(cases)} cases, {n_img} images, {size / 2**20:.0f} MiB ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
