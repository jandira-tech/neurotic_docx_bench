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

``--oracles`` (default ``libreoffice,pymupdf,jubarte``) makes each of them an oracle in
turn: every tool is rendered once per document and scored against every oracle but
itself, one summary table per oracle. ``sanity`` renders 10 pages twice with each oracle
and scores the second render against the first (100 expected).

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


def _score_row(base: dict, tool: str, oracle: str, versions: dict[str, str], rendered: dict) -> dict:
    from neurotic_docx_bench.page_metrics import jaccard_from_rasters
    from neurotic_docx_bench.score import score_document

    row = {**base, "tool": tool, "version": versions[tool], "input": SOURCE_INPUT.get(tool, "pdf"),
           "sot": oracle, "sot_version": versions[oracle], "pixel": None, "jaccard": None}
    ref, ref_ms, _ = rendered[oracle]
    if ref is None:
        return {**row, "ok": False, "ms": None, "pages": 0, "error": f"no oracle: {oracle} failed"}
    pages, ms, err = rendered[tool]
    row.update(ms=round(ms, 3), pages=len(pages or []), oracle_pages=len(ref))
    if pages:
        try:
            # Copies, so resizing to this oracle's size leaves the tool's own pages intact.
            work = Path(tempfile.mkdtemp(dir=pages[0].parent.parent, prefix=f"{tool}-vs-{oracle}."))
            cand = [Path(shutil.copy(pg, work / pg.name)) for pg in pages]
            cand, resized = _same_size(ref, cand)
            row["pixel"] = float(score_document(ref, cand)["overall_score"])
            jac = jaccard_from_rasters(ref, cand)
            row["jaccard"] = 100.0 * float(jac) if jac is not None else None  # 0-100, as the docxide reports
            row["resized"] = resized
            shutil.rmtree(work, ignore_errors=True)
        except Exception as exc:  # noqa: BLE001
            err = f"score: {exc}"[:500]
    row["ok"] = err is None and row["pixel"] is not None
    if err:
        row["error"] = err
    return row


def process_doc(doc: dict, tools: list[str], *, dpi: int, timeout: float, versions: dict[str, str],
                oracles: tuple[str, ...] = (SOT,)) -> list[dict]:
    """Render the document once with every oracle and tool, then score each tool against each
    oracle that is not itself. Rasters are gone when this returns."""
    doc = {**doc, "dpi": dpi}
    base = {"key": doc["key"], "sha256": doc["sha256"], "dpi": dpi}
    rows = []
    with tempfile.TemporaryDirectory(prefix="pdf-png.") as tmp:
        sizes = page_sizes(Path(doc["pdf"]), dpi)
        rendered = {}
        for tool in dict.fromkeys((*oracles, *tools)):
            out = Path(tmp) / tool
            out.mkdir()
            rendered[tool] = _timed(tool, doc, sizes, out, timeout)
        for o in oracles:
            pages, ms, err = rendered[o]
            rows.append({**base, "tool": o, "version": versions[o], "sot": o, "sot_version": versions[o],
                         "ok": pages is not None, "ms": round(ms, 3), "pages": len(pages or []),
                         **({"error": err} if err else {})})
        for o in oracles:
            for tool in dict.fromkeys((*oracles, *tools)):
                if tool != o:
                    rows.append(_score_row(base, tool, o, versions, rendered))
    return rows


def sanity(docs: list[dict], oracle: str, *, pages: int = 10, dpi: int = 144, timeout: float = 120) -> list[dict]:
    """Render documents twice with ``oracle``, independently, and score the second render
    against the first page by page until ``pages`` pages: 100 on both lenses means the
    oracle is deterministic and the scoring path is sound."""
    from neurotic_docx_bench.page_metrics import jaccard_from_rasters
    from neurotic_docx_bench.score import score_document

    rows: list[dict] = []
    for d in docs:
        if len(rows) >= pages:
            break
        doc = {**d, "dpi": dpi}
        with tempfile.TemporaryDirectory(prefix="pdf-png-sanity.") as tmp:
            sizes = page_sizes(Path(doc["pdf"]), dpi)
            runs = []
            for i in (1, 2):
                out = Path(tmp) / f"run{i}"
                out.mkdir()
                runs.append(_timed(oracle, doc, sizes, out, timeout)[0])
            if not runs[0] or not runs[1]:
                rows.append({"oracle": oracle, "key": d["key"], "page": None, "ok": False, "pixel": None,
                             "jaccard": None, "error": "render failed"})
                continue
            for n, (a, b) in enumerate(zip(runs[0], runs[1]), 1):
                if len(rows) >= pages:
                    break
                jac = jaccard_from_rasters([a], [b])
                rows.append({"oracle": oracle, "key": d["key"], "page": n, "ok": True,
                             "pixel": float(score_document([a], [b])["overall_score"]),
                             "jaccard": 100.0 * float(jac) if jac is not None else None,
                             "identical_bytes": a.read_bytes() == b.read_bytes()})
    return rows


def load_store(path: Path) -> list[dict]:
    rows = [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()] if path.is_file() else []
    for r in rows:
        r.setdefault("sot", SOT)  # rows before the second oracle were all against LibreOffice
    return rows


def _store_key(r: dict) -> tuple:
    return (r["tool"], r["version"], r["sot"], r["sot_version"], r["dpi"], r["sha256"])


def todo(docs: list[dict], tools: list[str], versions: dict[str, str], dpi: int, store: list[dict],
         oracles: tuple[str, ...] = (SOT,)) -> list[tuple[str, list[str]]]:
    """Per document, the tools with a (tool, oracle) score the store does not have yet."""
    have = {_store_key(r) for r in store if r["tool"] != r["sot"]}
    out = []
    for d in docs:
        need = [t for t in dict.fromkeys((*oracles, *tools))
                if any(o != t and (t, versions[t], o, versions[o], dpi, d["sha256"]) not in have for o in oracles)]
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
    return {k: v[k] for k in dict.fromkeys((SOT, *tools))}


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def selection_docs(selection: Path) -> list[dict]:
    rows = list(csv.DictReader(open(selection / "selection.csv")))
    return [{"key": r["key"], "pdf": str(ROOT / r["pdf"]), "docx": str(ROOT / r["docx"]),
             "sha256": _sha256(ROOT / r["pdf"]), "bucket": r["bucket"]} for r in rows]


def cmd_run(args: argparse.Namespace) -> None:
    tools = args.tools.split(",") if args.tools else list(TOOLS)
    oracles = tuple(args.oracles.split(","))
    vers = tool_versions([*tools, *oracles])
    docs = {d["key"]: d for s in args.selection for d in selection_docs(Path(s))}
    work = todo(list(docs.values()), tools, vers, args.dpi, load_store(STORE), oracles=oracles)
    print(f"{len(docs)} documents, {len(work)} need a run ({sum(len(t) for _, t in work)} tool rows); versions {vers}", flush=True)
    STORE.parent.mkdir(parents=True, exist_ok=True)
    done = 0
    with ProcessPoolExecutor(max_workers=args.workers) as pool, open(STORE, "a") as fh:
        futs = [pool.submit(process_doc, {k: docs[key][k] for k in ("key", "pdf", "docx", "sha256")}, need,
                            dpi=args.dpi, timeout=args.timeout, versions=vers, oracles=oracles)
                for key, need in work]
        for fut in as_completed(futs):
            for row in fut.result():
                fh.write(json.dumps(row) + "\n")
            fh.flush()
            done += 1
            if done % 25 == 0 or done == len(futs):
                print(f"{done}/{len(futs)} documents", flush=True)
    for s in args.selection:
        write_summary(Path(s), tools, vers, args.dpi, oracles)


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


def write_summary(selection: Path, tools: list[str], vers: dict[str, str], dpi: int,
                  oracles: tuple[str, ...] = (SOT,)) -> None:
    docs = selection_docs(selection)
    shas = {d["sha256"]: d["key"] for d in docs}
    store = [r for r in load_store(STORE) if r["sha256"] in shas and r["dpi"] == dpi]
    for r in store:
        r["key"] = shas[r["sha256"]]
    lines = [
        f"# PDF->PNG bench: {selection.name}",
        "",
        f"{len(docs)} Word PDFs of the mini-bench selection `{selection.name}`, rasterized at {dpi} DPI (PyMuPDF's "
        "pixel size per page). One table per oracle. Every column is intent-to-treat over the documents that "
        "oracle rendered: a failed document counts 0. Pixel is the bench scorer, Jaccard the docxide-pdf ink "
        "Jaccard (0 to 100) on the same rasters. ms per page is the median wall time on a shared machine "
        "(indicative only).",
        "",
        "LibreOffice does not rasterize a PDF: it imports it as editable text boxes and lays the text out "
        "again with its own font metrics (justified lines get other word spacing). Against LibreOffice, a "
        "tool scores its closeness to that re-layout; the PyMuPDF table scores closeness to the PDF as "
        "MuPDF draws it, with LibreOffice as one of the candidates.",
        "",
    ]
    for oracle in oracles:
        mine = [r for r in store if r["sot"] == oracle and r["sot_version"] == vers[oracle]]
        ref = {r["key"]: r for r in mine if r["tool"] == oracle}
        keys = [d["key"] for d in docs if ref.get(d["key"], {}).get("ok")]
        missing = [d["key"] for d in docs if d["key"] not in keys]
        lines += [f"## Oracle: {oracle} ({vers[oracle]})", "",
                  f"{len(keys)} of {len(docs)} documents have this oracle.", "",
                  "| Tool | Version | Input | OK | Pixel mean | Pixel median | Jaccard mean | ms per page | Pages resized |",
                  "|---|---|---|---|---|---|---|---|---|"]
        table = []
        for tool in dict.fromkeys((*oracles, *tools)):
            if tool == oracle:
                continue
            latest = {r["key"]: r for r in mine if r["tool"] == tool and r["version"] == vers[tool]}
            table.append((tool, summarize([latest[k] for k in keys if k in latest], keys)))
        for tool, st in sorted(table, key=lambda t: -t[1]["pixel_mean"]):
            ms = f"{st['ms_per_page_median']:.1f}" if st["ms_per_page_median"] is not None else "n/a"
            lines.append(f"| {tool} | {vers[tool]} | {SOURCE_INPUT.get(tool, 'pdf')} | {st['ok']}/{st['n']} | "
                         f"{st['pixel_mean']:.2f} | {st['pixel_median']:.2f} | {st['jaccard_mean']:.2f} | {ms} | "
                         f"{st['resized']} |")
        own = [r["ms"] / r["pages"] for r in ref.values() if r.get("ok") and r.get("pages")]
        if own:
            lines += ["", f"{oracle} itself: {statistics.median(own):.1f} ms per page (median)."]
        if missing:
            lines += ["", f"No {oracle} oracle ({len(missing)}): " + ", ".join(f"`{k}`" for k in missing)]
        lines.append("")
    if "jubarte" in tools:
        lines += ["jubarte cannot read a PDF: it converts the DOCX each Word PDF was exported from. Its rows "
                  "measure its own layout plus rasterization, not PDF rasterization, so they are not comparable "
                  "with the other rows.", ""]
    out = ROOT / "results" / "pdf_png_bench" / f"SUMMARY_{selection.name}.md"
    out.write_text("\n".join(lines).rstrip() + "\n")
    print("\n".join(lines))


def cmd_sanity(args: argparse.Namespace) -> None:
    docs = [d for sel in args.selection for d in selection_docs(Path(sel))]
    out = ROOT / "results" / "pdf_png_bench" / "sanity.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    vers = tool_versions(list(args.oracles.split(",")))
    lines = ["| Oracle | Version | Pages | Pixel min | Pixel mean | Jaccard min | Byte-identical |", "|---|---|---|---|---|---|---|"]
    with open(out, "a") as fh:
        for oracle in args.oracles.split(","):
            rows = sanity(docs, oracle, pages=args.pages, dpi=args.dpi)
            for r in rows:
                fh.write(json.dumps({**r, "version": vers[oracle], "dpi": args.dpi}) + "\n")
            ok = [r for r in rows if r["ok"]]
            px = [r["pixel"] for r in ok]
            jc = [r["jaccard"] for r in ok if r["jaccard"] is not None]
            lines.append(f"| {oracle} | {vers[oracle]} | {len(ok)}/{len(rows)} | {min(px):.2f} | {statistics.fmean(px):.2f} | "
                         f"{min(jc):.2f} | {sum(r['identical_bytes'] for r in ok)}/{len(ok)} |" if ok else
                         f"| {oracle} | {vers[oracle]} | 0/{len(rows)} | n/a | n/a | n/a | n/a |")
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
    r.add_argument("--oracles", default=f"{SOT},pymupdf,jubarte", help="comma list; each scores every other tool")
    sn = sub.add_parser("sanity")
    sn.add_argument("--selection", action="append", required=True)
    sn.add_argument("--oracles", default=f"{SOT},pymupdf,jubarte")
    sn.add_argument("--pages", type=int, default=10)
    sn.add_argument("--dpi", type=int, default=144)
    s = sub.add_parser("summary")
    s.add_argument("--selection", action="append", required=True)
    s.add_argument("--tools")
    s.add_argument("--dpi", type=int, default=144)
    s.add_argument("--oracles", default=f"{SOT},pymupdf,jubarte")
    args = ap.parse_args()
    if args.cmd == "run":
        cmd_run(args)
    elif args.cmd == "sanity":
        cmd_sanity(args)
    else:
        tools = args.tools.split(",") if args.tools else list(TOOLS)
        oracles = tuple(args.oracles.split(","))
        vers = tool_versions([*tools, *oracles])
        for sel in args.selection:
            write_summary(Path(sel), tools, vers, args.dpi, oracles)


if __name__ == "__main__":
    main()
