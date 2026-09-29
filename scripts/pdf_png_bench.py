# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""PDF->PNG bench: LibreOffice's page PNGs of each Word PDF are the oracle; every other
rasterizer is scored against them, one document at a time.

    uv run python scripts/pdf_png_bench.py run --selection results/mini_bench/<name> [--workers 6]
    uv run python scripts/pdf_png_bench.py summary --selection results/mini_bench/<name> [...]

The documents are a mini-bench selection's Word PDFs (``selection.csv``). For each page the
oracle is ``soffice --convert-to png:draw_png_Export`` with that ``PageRange`` at the exact
pixel size PyMuPDF gives the page at ``--dpi`` (144, the bench raster DPI), so the two
lenses compare same-size pages. Candidates:

- ``pymupdf``: the library ``raster.py`` rasterizes with, in-process.
- ``pdftoppm`` (poppler) and ``mutool`` (MuPDF CLI), the other rasterizers installed here.
- ``jubarte``: it cannot read a PDF, so it converts the DOCX the Word PDF was exported
  from (``jubarte convert --png``). Its row measures jubarte's own layout plus
  rasterization, not PDF rasterization; the summary says so.

Each document is scored with the bench pixel scorer (``score.score_document``) and the
docxide ink Jaccard (``page_metrics.jaccard_from_rasters``), both unchanged; a candidate
page of another size is resized to the oracle's first (``resized`` in the row). Rasters
live in a temporary folder removed after each document. One row per document and tool
goes to ``results/pdf_png_bench/scores.jsonl`` (append-only). A document the store
already has for the same tool version, oracle version, DPI and PDF sha256 is not rerun.
``ms`` is wall time per document on a shared machine: indicative, not the speed bench.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mini_bench import _capped  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "results" / "pdf_png_bench" / "scores.jsonl"
SOT = "libreoffice"
TOOLS = ("pymupdf", "pdftoppm", "mutool", "jubarte")
SOURCE_INPUT = {SOT: "pdf", "pymupdf": "pdf", "pdftoppm": "pdf", "mutool": "pdf", "jubarte": "docx"}
JUBARTE = Path(os.environ.get("PDF_PNG_JUBARTE", Path.home() / "temp" / "T" / "speed_bins" / "jubarte-86b6b5d3"))


def page_sizes(pdf: Path, dpi: int) -> list[tuple[int, int]]:
    import pymupdf

    mat = pymupdf.Matrix(dpi / 72, dpi / 72)
    with pymupdf.open(pdf) as doc:
        return [((r := (page.rect * mat).irect).width, r.height) for page in doc]


def libreoffice_command(pdf: Path, *, page: int, size: tuple[int, int], profile: Path, outdir: Path) -> list[str]:
    spec = {"PageRange": {"type": "string", "value": str(page)},
            "PixelWidth": {"type": "long", "value": str(size[0])},
            "PixelHeight": {"type": "long", "value": str(size[1])}}
    return ["soffice", f"-env:UserInstallation=file://{profile}", "--headless",
            "--convert-to", "png:draw_png_Export:" + json.dumps(spec, separators=(",", ":")),
            "--outdir", str(outdir), str(pdf)]


def pdftoppm_command(pdf: Path, *, page: int, size: tuple[int, int], prefix: Path) -> list[str]:
    return ["pdftoppm", "-png", "-f", str(page), "-l", str(page), "-scale-to-x", str(size[0]),
            "-scale-to-y", str(size[1]), "-singlefile", str(pdf), str(prefix)]


def jubarte_command(binary: Path, docx: Path, *, dpi: int, out: Path) -> list[str]:
    return [str(binary), "convert", str(docx), "--png", "--dpi", str(dpi), "-o", str(out), "--force"]


def _run(cmd: list[str], timeout: float, cwd: Path | None = None) -> None:
    rc, text, timed_out = _capped(cmd, timeout, cwd=cwd)
    if rc != 0:
        raise RuntimeError(text.strip()[-300:] or f"exit {rc}")


def render_libreoffice(doc: dict, sizes: list[tuple[int, int]], out: Path, timeout: float) -> list[Path]:
    pdf = Path(doc["pdf"])
    profile = Path(tempfile.gettempdir()) / f"pdf-png-lo-{os.getpid()}"
    pages = []
    for i, size in enumerate(sizes, 1):
        tmp = out / f"lo{i}"
        tmp.mkdir()
        _run(libreoffice_command(pdf, page=i, size=size, profile=profile, outdir=tmp), timeout)
        made = tmp / f"{pdf.stem}.png"
        if not made.is_file():
            raise RuntimeError(f"page {i}: no PNG written")
        pages.append(made.rename(out / f"page-{i:03d}.png"))
        tmp.rmdir()
    return pages


def render_pymupdf(doc: dict, sizes: list[tuple[int, int]], out: Path, timeout: float) -> list[Path]:
    import pymupdf

    dpi = doc["dpi"]
    pages = []
    with pymupdf.open(doc["pdf"]) as d:
        for i, page in enumerate(d, 1):
            p = out / f"page-{i:03d}.png"
            page.get_pixmap(dpi=dpi, alpha=False).save(p)
            pages.append(p)
    return pages


def render_pdftoppm(doc: dict, sizes: list[tuple[int, int]], out: Path, timeout: float) -> list[Path]:
    pages = []
    for i, size in enumerate(sizes, 1):
        prefix = out / f"page-{i:03d}"
        _run(pdftoppm_command(Path(doc["pdf"]), page=i, size=size, prefix=prefix), timeout)
        pages.append(prefix.with_suffix(".png"))
    return pages


def render_mutool(doc: dict, sizes: list[tuple[int, int]], out: Path, timeout: float) -> list[Path]:
    _run(["mutool", "draw", "-q", "-r", str(doc["dpi"]), "-o", str(out / "page-%03d.png"), doc["pdf"]], timeout)
    return sorted(out.glob("page-*.png"))


def render_jubarte(doc: dict, sizes: list[tuple[int, int]], out: Path, timeout: float) -> list[Path]:
    _run(jubarte_command(JUBARTE, Path(doc["docx"]), dpi=doc["dpi"], out=out / "j.pdf"), timeout, cwd=out)
    pages = sorted(out.glob("j-page-*.png"))
    if not pages:
        raise RuntimeError("no PNG pages written")
    return pages


RENDERERS = {SOT: render_libreoffice, "pymupdf": render_pymupdf, "pdftoppm": render_pdftoppm,
             "mutool": render_mutool, "jubarte": render_jubarte}


def _same_size(oracle: list[Path], cand: list[Path]) -> tuple[list[Path], bool]:
    """Candidate pages resized to the oracle page's size where they differ."""
    from PIL import Image

    resized = False
    fixed = []
    for i, c in enumerate(cand):
        if i < len(oracle):
            with Image.open(oracle[i]) as o, Image.open(c) as im:
                if im.size != o.size:
                    im.convert("RGB").resize(o.size, Image.LANCZOS).save(c)
                    resized = True
        fixed.append(c)
    return fixed, resized


def _timed(tool: str, doc: dict, sizes, out: Path, timeout: float) -> tuple[list[Path] | None, float, str | None]:
    t0 = time.perf_counter()
    try:
        pages = RENDERERS[tool](doc, sizes, out, timeout)
        err = None
    except Exception as exc:  # noqa: BLE001 - every failure is a row
        pages, err = None, str(exc)[:500]
    return pages, (time.perf_counter() - t0) * 1000, err


def process_doc(doc: dict, tools: list[str], *, dpi: int, timeout: float, versions: dict[str, str]) -> list[dict]:
    """Oracle then each tool on one document; rasters are gone when this returns."""
    from neurotic_docx_bench.page_metrics import jaccard_from_rasters
    from neurotic_docx_bench.score import score_document

    doc = {**doc, "dpi": dpi}
    base = {"key": doc["key"], "sha256": doc["sha256"], "dpi": dpi, "sot_version": versions[SOT]}
    rows = []
    with tempfile.TemporaryDirectory(prefix="pdf-png.") as tmp:
        sizes = page_sizes(Path(doc["pdf"]), dpi)
        sot_dir = Path(tmp) / SOT
        sot_dir.mkdir()
        oracle, ms, err = _timed(SOT, doc, sizes, sot_dir, timeout)
        rows.append({**base, "tool": SOT, "version": versions[SOT], "ok": oracle is not None, "ms": round(ms, 3),
                     "pages": len(oracle or []), **({"error": err} if err else {})})
        for tool in tools:
            row = {**base, "tool": tool, "version": versions[tool], "input": SOURCE_INPUT.get(tool, "pdf"),
                   "pixel": None, "jaccard": None}
            if oracle is None:
                rows.append({**row, "ok": False, "ms": None, "pages": 0, "error": "no oracle: LibreOffice failed"})
                continue
            out = Path(tmp) / tool
            out.mkdir()
            pages, ms, err = _timed(tool, doc, sizes, out, timeout)
            row.update(ms=round(ms, 3), pages=len(pages or []), oracle_pages=len(oracle))
            if pages:
                try:
                    pages, resized = _same_size(oracle, pages)
                    row["pixel"] = float(score_document(oracle, pages)["overall_score"])
                    jac = jaccard_from_rasters(oracle, pages)
                    row["jaccard"] = 100.0 * float(jac) if jac is not None else None  # 0-100, as the docxide reports
                    row["resized"] = resized
                except Exception as exc:  # noqa: BLE001
                    err = f"score: {exc}"[:500]
            row["ok"] = err is None and row["pixel"] is not None
            if err:
                row["error"] = err
            rows.append(row)
            shutil.rmtree(out, ignore_errors=True)
    return rows


def load_store(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()] if path.is_file() else []


def _store_key(r: dict) -> tuple:
    return (r["tool"], r["version"], r["sot_version"], r["dpi"], r["sha256"])


def todo(docs: list[dict], tools: list[str], versions: dict[str, str], dpi: int, store: list[dict]) -> list[tuple[str, list[str]]]:
    have = {_store_key(r) for r in store if r["tool"] != SOT}
    out = []
    for d in docs:
        need = [t for t in tools if (t, versions[t], versions[SOT], dpi, d["sha256"]) not in have]
        if need:
            out.append((d["key"], need))
    return out


def tool_versions(tools: list[str]) -> dict[str, str]:
    import pymupdf

    def first(cmd: list[str]) -> str:
        p = subprocess.run(cmd, capture_output=True, text=True)
        return ((p.stdout or "") + (p.stderr or "")).strip().splitlines()[0]

    v = {SOT: first(["soffice", "--version"]),
         "pymupdf": f"pymupdf {pymupdf.VersionBind} (MuPDF {pymupdf.VersionFitz})",
         "pdftoppm": first(["pdftoppm", "-v"]),
         "mutool": first(["mutool", "-v"]),
         "jubarte": f"{first([str(JUBARTE), '--version'])}@{JUBARTE.name.rsplit('-', 1)[-1]} (from the DOCX)"}
    return {k: v[k] for k in (SOT, *tools)}


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def selection_docs(selection: Path) -> list[dict]:
    rows = list(csv.DictReader(open(selection / "selection.csv")))
    return [{"key": r["key"], "pdf": str(ROOT / r["pdf"]), "docx": str(ROOT / r["docx"]),
             "sha256": _sha256(ROOT / r["pdf"]), "bucket": r["bucket"]} for r in rows]


def cmd_run(args: argparse.Namespace) -> None:
    tools = args.tools.split(",") if args.tools else list(TOOLS)
    vers = tool_versions(tools)
    docs = {d["key"]: d for s in args.selection for d in selection_docs(Path(s))}
    work = todo(list(docs.values()), tools, vers, args.dpi, load_store(STORE))
    print(f"{len(docs)} documents, {len(work)} need a run ({sum(len(t) for _, t in work)} tool rows); versions {vers}", flush=True)
    STORE.parent.mkdir(parents=True, exist_ok=True)
    done = 0
    with ProcessPoolExecutor(max_workers=args.workers) as pool, open(STORE, "a") as fh:
        futs = [pool.submit(process_doc, {k: docs[key][k] for k in ("key", "pdf", "docx", "sha256")}, need,
                            dpi=args.dpi, timeout=args.timeout, versions=vers) for key, need in work]
        for fut in as_completed(futs):
            for row in fut.result():
                fh.write(json.dumps(row) + "\n")
            fh.flush()
            done += 1
            if done % 25 == 0 or done == len(futs):
                print(f"{done}/{len(futs)} documents", flush=True)
    for s in args.selection:
        write_summary(Path(s), tools, vers, args.dpi)


def summarize(rows: list[dict], keys: list[str]) -> dict:
    """ITT over ``keys``: a failed or missing document counts 0."""
    by_key = {r["key"]: r for r in rows}
    pix = [float(by_key[k]["pixel"]) if k in by_key and by_key[k].get("ok") else 0.0 for k in keys]
    jac = [float(by_key[k]["jaccard"]) if k in by_key and by_key[k].get("ok") and by_key[k].get("jaccard") is not None
           else 0.0 for k in keys]
    per_page = [r["ms"] / r["pages"] for r in rows if r.get("ms") is not None and r.get("pages")]
    per_page += [r["ms"] for r in rows if r.get("ms") is not None and not r.get("pages")]
    return {"n": len(keys), "ok": sum(1 for k in keys if by_key.get(k, {}).get("ok")),
            "pixel_mean": statistics.fmean(pix) if pix else 0.0, "pixel_median": statistics.median(pix) if pix else 0.0,
            "jaccard_mean": statistics.fmean(jac) if jac else 0.0,
            "ms_per_page_median": statistics.median(per_page) if per_page else None,
            "resized": sum(1 for r in rows if r.get("resized"))}


def write_summary(selection: Path, tools: list[str], vers: dict[str, str], dpi: int) -> None:
    docs = selection_docs(selection)
    shas = {d["sha256"]: d["key"] for d in docs}
    store = [r for r in load_store(STORE) if r["sha256"] in shas and r["dpi"] == dpi and r["sot_version"] == vers[SOT]]
    for r in store:
        r["key"] = shas[r["sha256"]]
    sot = {r["key"]: r for r in store if r["tool"] == SOT and r["version"] == vers[SOT]}
    keys = [d["key"] for d in docs if sot.get(d["key"], {}).get("ok")]
    no_oracle = [d["key"] for d in docs if d["key"] not in keys]
    lines = [
        f"# PDF->PNG bench: {selection.name}",
        "",
        f"Oracle: {vers[SOT]} page PNGs of each Word PDF ({dpi} DPI, PyMuPDF's pixel size per page). "
        f"{len(keys)} of {len(docs)} documents have an oracle; the rest are listed below and not scored. "
        "Every column is intent-to-treat over those documents: a failed document counts 0. Pixel is the "
        "bench scorer, Jaccard the docxide-pdf ink Jaccard on the same rasters. ms per page is the median "
        "wall time on a shared machine (indicative only).",
        "",
        "| Tool | Version | Input | OK | Pixel mean | Pixel median | Jaccard mean | ms per page | Pages resized |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    table = []
    for tool in tools:
        rows = [r for r in store if r["tool"] == tool and r["version"] == vers[tool]]
        latest = {}
        for r in rows:
            latest[r["key"]] = r
        s = summarize([latest[k] for k in keys if k in latest], keys)
        table.append((tool, s))
    for tool, s in sorted(table, key=lambda t: -t[1]["pixel_mean"]):
        ms = f"{s['ms_per_page_median']:.1f}" if s["ms_per_page_median"] is not None else "n/a"
        lines.append(f"| {tool} | {vers[tool]} | {SOURCE_INPUT[tool]} | {s['ok']}/{s['n']} | {s['pixel_mean']:.2f} | "
                     f"{s['pixel_median']:.2f} | {s['jaccard_mean']:.2f} | {ms} | {s['resized']} |")
    sot_ms = [r["ms"] / r["pages"] for r in sot.values() if r.get("ok") and r.get("pages")]
    lines += ["", f"The oracle itself: {statistics.median(sot_ms):.1f} ms per page (median; one soffice call per page)."
              if sot_ms else "", ""]
    if "jubarte" in tools:
        lines += ["jubarte cannot read a PDF: it converts the DOCX each Word PDF was exported from. Its row measures "
                  "its own layout plus rasterization against LibreOffice's raster of Word's layout, not PDF "
                  "rasterization, so it is not comparable with the other rows.", ""]
    if no_oracle:
        lines += [f"No oracle ({len(no_oracle)}): " + ", ".join(f"`{k}`" for k in no_oracle), ""]
    out = ROOT / "results" / "pdf_png_bench" / f"SUMMARY_{selection.name}.md"
    out.write_text("\n".join(lines).rstrip() + "\n")
    print("\n".join(lines))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--selection", action="append", required=True, help="a mini-bench selection dir (repeatable)")
    r.add_argument("--tools", help=f"default: {','.join(TOOLS)}")
    r.add_argument("--dpi", type=int, default=144)
    r.add_argument("--timeout", type=float, default=120)
    r.add_argument("--workers", type=int, default=6)
    s = sub.add_parser("summary")
    s.add_argument("--selection", action="append", required=True)
    s.add_argument("--tools")
    s.add_argument("--dpi", type=int, default=144)
    args = ap.parse_args()
    if args.cmd == "run":
        cmd_run(args)
    else:
        tools = args.tools.split(",") if args.tools else list(TOOLS)
        vers = tool_versions(tools)
        for sel in args.selection:
            write_summary(Path(sel), tools, vers, args.dpi)


if __name__ == "__main__":
    main()
