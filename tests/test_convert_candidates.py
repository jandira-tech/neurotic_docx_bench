"""#89: LibreOffice candidates are held to the converter rules docxodus and jubarte meet.

Same per-document timeout, a PDF that does not open is a failure (never scored),
and every document's conversion seconds are recorded.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

import pymupdf

from neurotic_docx_bench import docx_to_pdf as d2p
from neurotic_docx_bench.render.soffice import RenderResult

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "convert_candidates.py"


def _load():
    spec = importlib.util.spec_from_file_location("convert_candidates", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fixture(tmp_path: Path, name: str) -> d2p.Fixture:
    docx = tmp_path / "corpus" / "clean" / "docx" / f"{name}.docx"
    docx.parent.mkdir(parents=True, exist_ok=True)
    docx.write_bytes(b"PK")
    return d2p.Fixture(stem=f"clean__{name}", kind="clean", original_stem=name, docx=docx, oracle=docx)


def test_soffice_candidates_share_the_timeout_the_pdf_check_and_record_seconds(tmp_path, monkeypatch) -> None:
    mod = _load()
    good, broken = _fixture(tmp_path, "good"), _fixture(tmp_path, "broken")
    timeouts = []

    def convert_one(soffice, docx, out_dir, *, force=False, timeout=1200.0, retries=1):
        time.sleep(0.2)
        timeouts.append(timeout)
        pdf = Path(out_dir) / f"{docx.stem}.pdf"
        if docx.stem == "good":
            doc = pymupdf.open()
            doc.new_page()
            pdf.write_bytes(doc.tobytes())
        else:
            pdf.write_bytes(b"%PDF-1.7 not really")
        return RenderResult(source=docx, pdf=pdf, ok=True)

    monkeypatch.setattr(mod.so, "convert_one", convert_one)
    monkeypatch.setattr(mod.so, "find_soffice", lambda: Path("/opt/soffice"))
    monkeypatch.setattr(mod.cli, "_corpus_word_selection",
                        lambda **k: type("S", (), {"fixtures": [good, broken]})())
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["convert_candidates.py", "--engine", "soffice", "--out", str(out), "--jobs", "2"])
    mod.main()
    assert timeouts == [d2p.CONVERT_TIMEOUT_S] * 2
    assert (out / "candidate" / "clean__good.pdf").is_file()
    assert not (out / "candidate" / "clean__broken.pdf").exists()
    record = json.loads((out / "convert_seconds.json").read_text())
    assert set(record["seconds"]) == {"clean__good", "clean__broken"}
    assert all(s >= 0.2 for s in record["seconds"].values())
    assert "unreadable PDF" in record["failures"]["clean__broken"]


def test_resume_reconverts_a_leftover_pdf_that_does_not_open(tmp_path, monkeypatch) -> None:
    """A ``%PDF-`` header is not enough to skip a document on rerun; it must open in MuPDF (#90)."""
    mod = _load()
    item = _fixture(tmp_path, "leftover")
    out = tmp_path / "out"
    (out / "candidate").mkdir(parents=True)
    (out / "candidate" / f"{item.stem}.pdf").write_bytes(b"%PDF-1.7 truncated garbage")
    called = []

    def convert_one(soffice, docx, out_dir, *, force=False, timeout=1200.0, retries=1):
        called.append(docx.stem)
        doc = pymupdf.open()
        doc.new_page()
        pdf = Path(out_dir) / f"{docx.stem}.pdf"
        pdf.write_bytes(doc.tobytes())
        return RenderResult(source=docx, pdf=pdf, ok=True)

    monkeypatch.setattr(mod.so, "convert_one", convert_one)
    monkeypatch.setattr(mod.so, "find_soffice", lambda: Path("/opt/soffice"))
    monkeypatch.setattr(mod.cli, "_corpus_word_selection", lambda **k: type("S", (), {"fixtures": [item]})())
    monkeypatch.setattr(sys, "argv", ["convert_candidates.py", "--engine", "soffice", "--out", str(out)])
    mod.main()
    assert called == ["leftover"]
    assert d2p._unreadable_pdf(out / "candidate" / f"{item.stem}.pdf") is None


def test_a_failed_reconversion_removes_the_unreadable_leftover(tmp_path, monkeypatch) -> None:
    """#90: when the retry of an unreadable kept PDF fails, the broken file must not stay to be scored."""
    mod = _load()
    item = _fixture(tmp_path, "leftover")
    out = tmp_path / "out"
    (out / "candidate").mkdir(parents=True)
    (out / "candidate" / f"{item.stem}.pdf").write_bytes(b"%PDF-1.7 truncated garbage")
    monkeypatch.setattr(mod.so, "convert_one", lambda soffice, docx, out_dir, **k: RenderResult(
        source=docx, pdf=None, ok=False, error="soffice timed out"))
    monkeypatch.setattr(mod.so, "find_soffice", lambda: Path("/opt/soffice"))
    monkeypatch.setattr(mod.cli, "_corpus_word_selection", lambda **k: type("S", (), {"fixtures": [item]})())
    monkeypatch.setattr(sys, "argv", ["convert_candidates.py", "--engine", "soffice", "--out", str(out)])
    mod.main()
    assert not (out / "candidate" / f"{item.stem}.pdf").exists()
    assert json.loads((out / "convert_seconds.json").read_text())["failures"] == {item.stem: "soffice timed out"}
