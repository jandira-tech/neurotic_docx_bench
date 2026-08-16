"""DOCX→PDF track: SHA-pinned Word-export oracles, shipped adapters, ITT failures."""

from __future__ import annotations

import json
import shutil
import stat
from pathlib import Path

import pytest

from neurotic_docx_bench import pipeline
from neurotic_docx_bench.docx_to_pdf import (
    ORACLE_PDF_DIRS,
    ORACLE_SHA_MANIFEST,
    REQUIRED_FEATURES,
    WORD_CORPUS,
    WORD_PDF_TOOLS,
    convert_command,
    feature_coverage,
    load_fixtures,
    oracle_pdf_dirs,
    render_docx_to_pdf_table,
    run_eval,
    score_folder_pair,
    select_word_oracle_fixtures,
    try_convert_fixture,
    update_readme_docx_to_pdf,
    verify_oracle_sha_manifest,
    write_oracle_sha_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
LIBREOFFICE_PDF_SOURCE = REPO_ROOT / "corpus" / "word_based" / "pdf_source"


def test_oracles_are_only_the_two_pinned_word_export_folders():
    fixtures = load_fixtures()
    assert fixtures
    stems = [item.stem for item in fixtures]
    assert len(set(stems)) == len(fixtures)
    allowed = {d.resolve() for d in oracle_pdf_dirs()}
    assert {d.name for d in allowed} == set(ORACLE_PDF_DIRS)
    lo_root = LIBREOFFICE_PDF_SOURCE.resolve()
    kinds: set[str] = set()
    for item in fixtures:
        kinds.add(item.kind)
        assert item.docx.is_file(), f"missing DOCX {item.docx}"
        assert item.oracle.is_file(), f"missing Word oracle {item.oracle}"
        assert item.oracle.read_bytes()[:5] == b"%PDF-"
        assert item.kind in {"accepted", "redline_randomized"}
        assert item.stem == f"{item.kind}__{item.original_stem}"
        oracle = item.oracle.resolve()
        assert oracle.parent in allowed
        assert lo_root not in oracle.parents
        assert oracle.parent.name in ORACLE_PDF_DIRS
        head = item.oracle.read_bytes()[:65_536]
        assert b"LibreOffice" not in head, f"{item.stem} looks like a LibreOffice PDF"
    assert kinds == {"accepted", "redline_randomized"}


def test_pin_list_matches_deterministic_word_pool_selection():
    pinned = [(item.kind, item.original_stem) for item in load_fixtures()]
    expected = [(item.kind, item.original_stem) for item in select_word_oracle_fixtures()]
    assert pinned == expected
    assert {kind for kind, _ in pinned} == {"accepted", "redline_randomized"}


def test_oracle_sha256_manifest_covers_every_pinned_pdf_and_detects_tamper(tmp_path):
    verify_oracle_sha_manifest()
    fixtures = load_fixtures()
    from neurotic_docx_bench.oracle_manifest import load_manifest, _sha256

    manifest = load_manifest(ORACLE_SHA_MANIFEST)
    assert manifest
    for item in fixtures:
        rel = item.oracle.resolve().relative_to(WORD_CORPUS.resolve()).as_posix()
        assert manifest[rel] == _sha256(item.oracle)
    # Tamper detection uses a copy. The committed oracle PDFs are not written.
    fake_root = tmp_path / "corpus"
    for name in ORACLE_PDF_DIRS:
        (fake_root / name).mkdir(parents=True)
        src = next(p for p in fixtures if p.oracle.parent.name == name).oracle
        dest = fake_root / name / src.name
        dest.write_bytes(src.read_bytes())
    write_oracle_sha_manifest(tmp_path / "sha.json", fake_root)
    victim = next((fake_root / ORACLE_PDF_DIRS[0]).glob("*.pdf"))
    victim.write_bytes(b"%PDF-TAMPER")
    with pytest.raises(RuntimeError, match="oracle PDF drift"):
        verify_oracle_sha_manifest(tmp_path / "sha.json", fake_root)


def test_fixture_set_covers_required_document_features():
    fixtures = load_fixtures()
    found = feature_coverage(fixtures)
    missing = REQUIRED_FEATURES - found
    assert not missing, f"fixture set missing features: {sorted(missing)}"


def test_identity_pdf_scores_100_via_shipped_plain_stem_path(tmp_path):
    fixtures = load_fixtures()
    stem = fixtures[0].stem
    oracle = fixtures[0].oracle
    odir = tmp_path / "oracle"
    cdir = tmp_path / "cand"
    odir.mkdir()
    cdir.mkdir()
    shutil.copy(oracle, odir / f"{stem}.pdf")
    shutil.copy(oracle, cdir / f"{stem}.pdf")
    full = score_folder_pair(odir, cdir, tmp_path / "work", jobs=1)
    assert list(full) == [stem]
    score = pipeline.overall_from_result(full[stem])
    assert score == pytest.approx(100.0, abs=1e-6)


def test_visibly_different_page_scores_below_100(tmp_path):
    fixtures = load_fixtures()
    left, right = fixtures[0].oracle, fixtures[1].oracle
    assert left.read_bytes() != right.read_bytes()
    odir = tmp_path / "oracle"
    cdir = tmp_path / "cand"
    odir.mkdir()
    cdir.mkdir()
    shutil.copy(left, odir / "doc.pdf")
    shutil.copy(right, cdir / "doc.pdf")
    full = score_folder_pair(odir, cdir, tmp_path / "work", jobs=1)
    score = pipeline.overall_from_result(full["doc"])
    assert score < 100.0


def test_pairing_is_by_plain_stem_not_redline_key(tmp_path):
    oracle = tmp_path / "oracle"
    cand = tmp_path / "cand"
    oracle.mkdir()
    cand.mkdir()
    (oracle / "alpha.pdf").write_bytes(b"%PDF-1.4\n")
    (oracle / "pair_redline.pdf").write_bytes(b"%PDF-1.4\n")
    (cand / "alpha.pdf").write_bytes(b"%PDF-1.4\n")
    (cand / "pair.pdf").write_bytes(b"%PDF-1.4\n")  # must not match pair_redline
    (cand / "pair_redline.pdf").write_bytes(b"%PDF-1.4\n")
    pairs = pipeline.match_by_plain_stem(oracle, cand)
    keys = [key for key, _, _ in pairs]
    assert keys == ["alpha", "pair_redline"]
    redline_pairs = pipeline.match_by_stem(oracle, cand)
    assert [key for key, _, _ in redline_pairs] == ["pair"]


def test_convert_command_rdocx_uses_native_to_pdf():
    cmd = convert_command("rdocx", Path("in.docx"), Path("out.pdf"), binary=Path("/opt/rdocx"))
    assert cmd == ["/opt/rdocx", "convert", "in.docx", "--to", "pdf", "-o", "out.pdf"]


def test_convert_command_office2pdf_uses_native_cli():
    cmd = convert_command(
        "office2pdf", Path("in.docx"), Path("out.pdf"), binary=Path("/opt/office2pdf"),
    )
    assert cmd == ["/opt/office2pdf", "in.docx", "-o", "out.pdf"]


def test_convert_command_pdfitdown_uses_native_cli():
    cmd = convert_command(
        "pdfitdown", Path("in.docx"), Path("out.pdf"), binary=Path("/opt/pdfitdown"),
    )
    assert cmd == ["/opt/pdfitdown", "-i", "in.docx", "-o", "out.pdf"]


def test_convert_command_doxx_is_native_not_markdown_pipeline():
    cmd = convert_command("doxx", Path("in.docx"), Path("out.pdf"), binary=Path("/opt/doxx"))
    joined = " ".join(cmd).lower()
    assert cmd[0] == "/opt/doxx"
    assert "in.docx" in cmd
    assert "pandoc" not in joined
    assert "markdown" not in joined
    assert "soffice" not in joined


def test_convert_command_jubarte_uses_native_convert():
    cmd = convert_command(
        "jubarte", Path("in.docx"), Path("out.pdf"), binary=Path("/opt/jubarte"),
    )
    assert cmd == ["/opt/jubarte", "convert", "in.docx", "-o", "out.pdf", "--force"]
    assert "soffice" not in " ".join(cmd).lower()


def test_known_tools_are_the_four_named_converters():
    assert WORD_PDF_TOOLS == ("rdocx", "office2pdf", "pdfitdown", "doxx")


def test_try_convert_records_crash_as_generate_failure(tmp_path):
    fixture = load_fixtures()[0]
    dest = tmp_path / f"{fixture.stem}.pdf"
    script = tmp_path / "boom"
    script.write_text("#!/bin/sh\necho nope >&2\nexit 7\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    fail = try_convert_fixture("rdocx", script, fixture, dest)
    assert fail is not None
    assert fail["doc"] == fixture.stem
    assert fail["stage"] == "generate"
    assert fail["error"]
    assert fail["cmd"][0] == str(script)
    assert not dest.is_file() or dest.read_bytes()[:5] != b"%PDF-"


def test_try_convert_rejects_non_pdf_output(tmp_path):
    fixture = load_fixtures()[0]
    dest = tmp_path / f"{fixture.stem}.pdf"
    script = tmp_path / "notpdf"
    script.write_text("#!/bin/sh\nwhile [ $# -gt 0 ]; do\n  if [ \"$1\" = \"-o\" ]; then printf 'not-a-pdf' > \"$2\"; fi\n  shift\ndone\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    fail = try_convert_fixture("rdocx", script, fixture, dest)
    assert fail is not None
    assert fail["stage"] == "generate"
    assert "PDF" in fail["error"] or "pdf" in fail["error"].lower()


def test_run_eval_itt_zero_on_convert_fail_and_does_not_abort(tmp_path):
    items = load_fixtures()[:3]
    script = tmp_path / "fail_all"
    script.write_text("#!/bin/sh\nexit 1\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    report = run_eval(
        json_out=tmp_path / "out.json",
        work_dir=tmp_path / "work",
        tools=["rdocx"],
        converter=script,
        fixtures=items,
        jobs=1,
    )
    assert report["n"] == 3
    tool = report["tools"]["rdocx"]
    assert tool["itt_n"] == 3
    assert tool["n_scored"] == 0
    assert tool["failures"] == 3
    assert tool["mean"] == 0
    assert tool["median"] == 0
    assert tool["perfects"] == 0
    assert len(tool["generate_failures"]) == 3
    assert set(tool["per_doc"]) == {item.stem for item in items}
    assert all(value == 0 for value in tool["per_doc"].values())
    saved = json.loads((tmp_path / "out.json").read_text())
    assert saved["tools"]["rdocx"]["failures"] == 3


def test_render_table_uses_report_itt_fields_not_invented_means():
    report = {
        "n": 500,
        "tools": {
            "rdocx": {
                "n_scored": 499,
                "itt_n": 500,
                "mean": 12.3456,
                "median": 11.0,
                "perfects": 2,
                "failures": 1,
            },
            "doxx": {
                "n_scored": 0,
                "itt_n": 500,
                "mean": 0.0,
                "median": 0.0,
                "perfects": 0,
                "failures": 500,
            },
        },
    }
    table = render_docx_to_pdf_table(report)
    assert "| rdocx |" in table
    assert "| doxx |" in table
    assert "499" in table
    assert "500" in table
    assert "12.35" in table or "12.3456" in table
    data_rows = [line for line in table.splitlines() if line.startswith("|") and "Tool" not in line and "---" not in line]
    assert any("| rdocx |" in line for line in data_rows)
    assert any("| doxx |" in line for line in data_rows)
    assert not any("| office2pdf |" in line for line in data_rows)


def test_readme_docx_to_pdf_table_matches_committed_artifact():
    artifact = REPO_ROOT / "results" / "docx_to_pdf_500.json"
    readme = REPO_ROOT / "README.md"
    report = json.loads(artifact.read_text(encoding="utf-8"))
    assert report["n"] == len(load_fixtures())
    for name, tool in report["tools"].items():
        assert tool["itt_n"] == report["n"], name
        assert len(tool["per_doc"]) == report["n"], name
    expected = render_docx_to_pdf_table(report).strip()
    assert expected in readme.read_text(encoding="utf-8")


def test_update_readme_replaces_marked_docx_to_pdf_block(tmp_path):
    report = {
        "n": 500,
        "tools": {
            "rdocx": {
                "n_scored": 500,
                "itt_n": 500,
                "mean": 10.0,
                "median": 9.0,
                "perfects": 0,
                "failures": 0,
            },
        },
    }
    readme = tmp_path / "README.md"
    readme.write_text(
        "head\n<!-- RANKING-END -->\n"
        "<!-- DOCX-TO-PDF-START -->\nold table\n<!-- DOCX-TO-PDF-END -->\ntail\n",
    )
    update_readme_docx_to_pdf(readme, report)
    text = readme.read_text()
    assert "head" in text
    assert "tail" in text
    assert "old table" not in text
    assert render_docx_to_pdf_table(report).strip() in text
