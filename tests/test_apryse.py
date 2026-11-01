"""Apryse (apryse-sdk) as a DOCX→PDF converter and a DOCX redline generator (#100)."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from neurotic_docx_bench import apryse_gen, docx_to_pdf

ROOT = Path(__file__).resolve().parents[1]
WORD = ROOT / "corpus" / "word"
# A small Word compare pair from the v1 redline set (0000ae5089) and one convert input.
BASE = "clean/docx/572990f05c_right_alignment_demo_id_paraid_overflow"
NEXT = "tracking_without_comments/docx/4b97a33168_risk_assessment_product_launch_suggesting_insert"
CONVERT_SRC = WORD / "tracking_without_comments/docx/003c8c6d7d_4433455597_rejected_tracking.docx"

needs_key = pytest.mark.skipif(
    not apryse_gen.api_key(), reason="APRYSE_API_KEY not set (env or .env)",
)
needs_corpus = pytest.mark.skipif(
    not (WORD / f"{BASE}.docx").is_file() or not CONVERT_SRC.is_file(),
    reason="corpus docx not downloaded (bench fixtures download)",
)


def test_apryse_is_a_word_pdf_tool() -> None:
    assert "apryse" in docx_to_pdf.WORD_PDF_TOOLS


def test_convert_command_is_src_dest(tmp_path: Path) -> None:
    binary = tmp_path / "apryse-convert"
    cmd = docx_to_pdf.convert_command("apryse", Path("a.docx"), Path("a.pdf"), binary=binary)
    assert cmd == [str(binary), "a.docx", "a.pdf"]


def test_resolve_binary_is_the_bundled_shim() -> None:
    path = docx_to_pdf.resolve_tool_binary("apryse")
    assert path == docx_to_pdf.APRYSE_CONVERTER
    assert path.is_file() and os.access(path, os.X_OK)


def test_version_names_the_sdk_and_demo_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APRYSE_API_KEY", "demo:someone@example.com:0123")
    v = apryse_gen.version()
    assert v.startswith("apryse-sdk ")
    assert "PDFNet " in v
    assert "demo key" in v


def test_version_without_demo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APRYSE_API_KEY", "Acme Corp:OEM:licensed:0123")
    assert "demo" not in apryse_gen.version()


def test_tool_version_reads_the_shim() -> None:
    v = docx_to_pdf.tool_version(docx_to_pdf.APRYSE_CONVERTER)
    assert v is not None and v.startswith("apryse-sdk ")


def test_api_key_falls_back_to_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APRYSE_API_KEY", raising=False)
    env = tmp_path / ".env"
    env.write_text("OTHER=1\nAPRYSE_API_KEY='demo:x:y'\n")
    assert apryse_gen.api_key(env) == "demo:x:y"


def test_batch_names_failures_and_does_not_abort(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing source is a missing_source failure; a compare error is a generate failure;
    the batch still writes the redlines that worked and exits 0."""
    src = tmp_path / "src"
    src.mkdir()
    for name in ("good_a", "good_b", "bad_a", "bad_b"):
        (src / f"{name}.docx").write_bytes(b"x")
    manifest = tmp_path / "pairs.csv"
    with manifest.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["key", "base", "next"])
        w.writeheader()
        w.writerow({"key": "k1", "base": "good_a", "next": "good_b"})
        w.writerow({"key": "k2", "base": "bad_a", "next": "bad_b"})
        w.writerow({"key": "k3", "base": "gone_a", "next": "gone_b"})

    def fake_run(base: Path, nxt: Path, out: Path, timeout_s: float) -> float:
        if base.stem == "bad_a":
            raise RuntimeError("compare refused")
        out.write_bytes(b"PK")
        return 0.01

    monkeypatch.setattr(apryse_gen, "_compare_in_child", fake_run)
    out = tmp_path / "run" / "docx"
    rc = apryse_gen.main(
        ["batch", "--manifest", str(manifest), "--source-dir", str(src), "--out", str(out), "--jobs", "2"],
    )
    assert rc == 0
    assert sorted(p.name for p in out.iterdir()) == ["k1_apryse.docx"]
    failures = json.loads((out.parent / "generate_failures.json").read_text())
    assert {(f["doc"], f["stage"]) for f in failures} == {("k2", "generate"), ("k3", "missing_source")}
    assert "compare refused" in next(f["error"] for f in failures if f["doc"] == "k2")
    timings = json.loads((out.parent / "generate_timings.json").read_text())
    assert set(timings) == {"k1_apryse"}


def test_batch_total_wipeout_exits_nonzero(tmp_path: Path) -> None:
    manifest = tmp_path / "pairs.csv"
    manifest.write_text("key,base,next\nk1,nope_a,nope_b\n")
    out = tmp_path / "run" / "docx"
    rc = apryse_gen.main(
        ["batch", "--manifest", str(manifest), "--source-dir", str(tmp_path), "--out", str(out)],
    )
    assert rc == 1


def test_child_timeout_is_a_failure(tmp_path: Path) -> None:
    with pytest.raises(TimeoutError):
        apryse_gen._run_child([sys.executable, "-c", "import time; time.sleep(30)"], timeout_s=0.5)


@needs_key
@needs_corpus
def test_compare_emits_tracked_changes(tmp_path: Path) -> None:
    out = tmp_path / "r.docx"
    seconds = apryse_gen._compare_in_child(
        WORD / f"{BASE}.docx", WORD / f"{NEXT}.docx", out, timeout_s=120,
    )
    assert seconds >= 0
    xml = zipfile.ZipFile(out).read("word/document.xml").decode()
    assert "<w:ins " in xml and "<w:del " in xml


@needs_key
@needs_corpus
def test_convert_shim_writes_a_pdf(tmp_path: Path) -> None:
    dest = tmp_path / "c.pdf"
    proc = subprocess.run(
        [str(docx_to_pdf.APRYSE_CONVERTER), str(CONVERT_SRC), str(dest)],
        capture_output=True, text=True, timeout=180, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert dest.read_bytes()[:5] == b"%PDF-"


@needs_key
def test_convert_shim_fails_loudly_on_garbage(tmp_path: Path) -> None:
    src = tmp_path / "junk.docx"
    src.write_bytes(b"not a docx")
    proc = subprocess.run(
        [str(docx_to_pdf.APRYSE_CONVERTER), str(src), str(tmp_path / "j.pdf")],
        capture_output=True, text=True, timeout=180, check=False,
    )
    assert proc.returncode != 0
    assert not (tmp_path / "j.pdf").exists()
