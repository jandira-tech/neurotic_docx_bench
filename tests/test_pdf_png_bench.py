"""Spec for the PDF->PNG bench (``scripts/pdf_png_bench.py``): LibreOffice's page PNGs are
the oracle, every other rasterizer is scored against them per document."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pymupdf
import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "pdf_png_bench.py"


def _load():
    sys.path.insert(0, str(_SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("pdf_png_bench", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pdf_png_bench"] = mod
    spec.loader.exec_module(mod)
    return mod


pb = _load()


def _pdf(path: Path, pages: int = 2) -> Path:
    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 100), f"Page {i + 1} of a small test document", fontsize=14)
        page.draw_rect(pymupdf.Rect(72, 200, 300, 260), color=(1, 0, 0), fill=(0, 0, 1))
    doc.save(path)
    return path


def test_page_sizes_are_pymupdf_pixel_sizes_at_the_dpi(tmp_path):
    sizes = pb.page_sizes(_pdf(tmp_path / "a.pdf"), dpi=144)
    assert sizes == [(1190, 1684), (1190, 1684)]


def test_libreoffice_command_exports_one_page_at_an_exact_size():
    cmd = pb.libreoffice_command(Path("/x/a.pdf"), page=3, size=(1190, 1684), profile=Path("/p"), outdir=Path("/o"))
    spec = json.loads(cmd[cmd.index("--convert-to") + 1].split(":", 2)[2])
    assert spec == {"PageRange": {"type": "string", "value": "3"},
                    "PixelWidth": {"type": "long", "value": "1190"},
                    "PixelHeight": {"type": "long", "value": "1684"}}
    assert cmd[0] == "soffice" and "--headless" in cmd and cmd[-1] == "/x/a.pdf"


def test_pdftoppm_command_renders_one_page_at_an_exact_size():
    cmd = pb.pdftoppm_command(Path("/x/a.pdf"), page=2, size=(1190, 1684), prefix=Path("/o/p"))
    assert cmd == ["pdftoppm", "-png", "-f", "2", "-l", "2", "-scale-to-x", "1190", "-scale-to-y", "1684",
                   "-singlefile", "/x/a.pdf", "/o/p"]


def test_jubarte_command_converts_the_docx_source_to_png_pages():
    cmd = pb.jubarte_command(Path("/bin/jubarte"), Path("/x/a.docx"), dpi=144, out=Path("/o/a.pdf"))
    assert cmd == ["/bin/jubarte", "convert", "/x/a.docx", "--png", "--dpi", "144", "-o", "/o/a.pdf", "--force"]
    assert pb.SOURCE_INPUT["jubarte"] == "docx" and pb.SOURCE_INPUT["pymupdf"] == "pdf"


def test_identical_rasterizer_scores_100_on_both_lenses(tmp_path, monkeypatch):
    pdf = _pdf(tmp_path / "a.pdf")
    # pymupdf standing in for the oracle: identical pages must score 100 on both lenses.
    monkeypatch.setitem(pb.RENDERERS, pb.SOT, pb.RENDERERS["pymupdf"])
    rows = pb.process_doc({"key": "clean__a", "pdf": str(pdf), "sha256": "s"}, ["pymupdf"], dpi=144,
                          timeout=60, versions={pb.SOT: "sot 1", "pymupdf": "mu 1"})
    by_tool = {r["tool"]: r for r in rows}
    assert by_tool[pb.SOT]["ok"] and by_tool[pb.SOT]["pages"] == 2
    cand = by_tool["pymupdf"]
    assert cand["ok"] and cand["pixel"] == pytest.approx(100.0) and cand["jaccard"] == pytest.approx(100.0)
    assert cand["sot_version"] == "sot 1" and cand["dpi"] == 144
    assert not list(tmp_path.glob("**/*.png"))  # rasters never outlive the document


def test_a_failed_rasterizer_is_a_row_with_the_error(tmp_path, monkeypatch):
    pdf = _pdf(tmp_path / "a.pdf", pages=1)
    monkeypatch.setitem(pb.RENDERERS, pb.SOT, pb.RENDERERS["pymupdf"])

    def broken(doc, sizes, out, timeout):
        raise RuntimeError("no pages")

    monkeypatch.setitem(pb.RENDERERS, "broken", broken)
    rows = pb.process_doc({"key": "clean__a", "pdf": str(pdf), "sha256": "s"}, ["broken"], dpi=144,
                          timeout=60, versions={pb.SOT: "sot 1", "broken": "b 1"})
    bad = next(r for r in rows if r["tool"] == "broken")
    assert not bad["ok"] and "no pages" in bad["error"] and bad["pixel"] is None


def test_todo_skips_documents_the_store_already_has(tmp_path):
    store = tmp_path / "scores.jsonl"
    store.write_text(json.dumps({"tool": "pymupdf", "version": "mu 1", "sot_version": "sot 1", "dpi": 144,
                                 "sha256": "s1", "key": "clean__a", "ok": True}) + "\n")
    docs = [{"key": "clean__a", "sha256": "s1"}, {"key": "clean__b", "sha256": "s2"}]
    vers = {pb.SOT: "sot 1", "pymupdf": "mu 1", "pdftoppm": "p 1"}
    todo = pb.todo(docs, ["pymupdf", "pdftoppm"], vers, 144, pb.load_store(store))
    assert todo == [("clean__a", ["pdftoppm"]), ("clean__b", ["pymupdf", "pdftoppm"])]
    # A new oracle version invalidates every earlier score.
    vers2 = {**vers, pb.SOT: "sot 2"}
    assert pb.todo(docs, ["pymupdf"], vers2, 144, pb.load_store(store))[0] == ("clean__a", ["pymupdf"])


def test_summary_counts_a_failed_or_missing_document_as_zero():
    rows = [
        {"tool": "pymupdf", "key": "clean__a", "ok": True, "pixel": 90.0, "jaccard": 80.0, "ms": 10.0, "pages": 2},
        {"tool": "pymupdf", "key": "clean__b", "ok": False, "pixel": None, "jaccard": None, "ms": 5.0, "pages": 0},
    ]
    s = pb.summarize(rows, ["clean__a", "clean__b", "clean__c"])
    assert s["n"] == 3 and s["ok"] == 1
    assert s["pixel_mean"] == 30.0 and s["jaccard_mean"] == 80.0 / 3
    assert s["ms_per_page_median"] == 5.0
