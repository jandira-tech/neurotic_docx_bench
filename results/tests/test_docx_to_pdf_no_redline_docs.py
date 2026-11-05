"""docx_to_pdf_no_redline_docs: SHA-pinned source Word-export oracles."""

from __future__ import annotations

import json
import shutil
import stat
from pathlib import Path

import pytest

from neurotic_docx_bench import pipeline
from neurotic_docx_bench.docx_to_pdf import (
    NO_REDLINE_TRACK,
    REQUIRED_FEATURES,
    feature_coverage,
    load_fixtures,
    load_pin_rows,
    oracle_pdf_dirs,
    run_eval,
    score_folder_pair,
    verify_oracle_sha_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
LIBREOFFICE_PDF_SOURCE = REPO_ROOT / "corpus" / "libreoffice"  # every LibreOffice render the bench files
TRACK = NO_REDLINE_TRACK
KINDS = {"source", "source_randomized"}


def _corpus_present() -> bool:
    return all(f.docx.is_file() and f.oracle.is_file() for f in load_fixtures(track=TRACK))


needs_corpus = pytest.mark.skipif(
    not _corpus_present(), reason="needs corpus/ DOCX and PDF files: uv run bench fixtures download"
)


def test_pin_file_rows_are_unique_source_word_exports():
    rows = load_pin_rows(track=TRACK)
    assert len(rows) == 396
    assert len({(r.kind, r.stem) for r in rows}) == len(rows)
    assert len({r.pdf for r in rows}) == len(rows)
    assert {r.kind for r in rows} == KINDS
    for r in rows:
        assert len(r.pdf_sha256) == 64
        assert not r.pdf.startswith("libreoffice/")


@needs_corpus
def test_oracles_are_only_source_and_source_randomized_word_exports():
    fixtures = load_fixtures(track=TRACK)
    allowed = {d.resolve() for d in oracle_pdf_dirs(track=TRACK)}
    lo_root = LIBREOFFICE_PDF_SOURCE.resolve()
    for item in fixtures:
        assert item.oracle.read_bytes()[:5] == b"%PDF-"
        assert item.stem == f"{item.kind}__{item.original_stem}"
        oracle = item.oracle.resolve()
        assert oracle.parent in allowed
        assert lo_root not in oracle.parents
        head = item.oracle.read_bytes()[:65_536]
        assert b"LibreOffice" not in head, f"{item.stem} looks like a LibreOffice PDF"


@needs_corpus
def test_pinned_source_pdfs_match_their_sha256():
    verify_oracle_sha_manifest(track=TRACK)


@needs_corpus
def test_fixture_set_covers_required_document_features():
    fixtures = load_fixtures(track=TRACK)
    found = feature_coverage(fixtures)
    missing = REQUIRED_FEATURES - found
    assert not missing, f"fixture set missing features: {sorted(missing)}"


@needs_corpus
def test_identity_pdf_scores_100_via_shipped_plain_stem_path(tmp_path):
    fixtures = load_fixtures(track=TRACK)
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


@needs_corpus
def test_visibly_different_page_scores_below_100(tmp_path):
    fixtures = load_fixtures(track=TRACK)
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


@needs_corpus
def test_run_eval_itt_zero_on_convert_fail_and_does_not_abort(tmp_path):
    items = load_fixtures(track=TRACK)[:3]
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
        track=TRACK,
    )
    assert report["track"] == TRACK.name
    assert report["n"] == 3
    tool = report["tools"]["rdocx"]
    assert tool["itt_n"] == 3
    assert tool["n_scored"] == 0
    assert tool["failures"] == 3
    assert all(value == 0 for value in tool["per_doc"].values())
    saved = json.loads((tmp_path / "out.json").read_text())
    assert saved["tools"]["rdocx"]["failures"] == 3


def test_committed_no_redline_artifact_is_in_the_converter_store():
    artifact = REPO_ROOT / "results" / "docx_to_pdf_no_redline.json"
    store = REPO_ROOT / "results" / "converters.jsonl"
    if not artifact.is_file() or not store.is_file():
        pytest.skip("no_redline eval artifact or converter store not written yet")
    report = json.loads(artifact.read_text(encoding="utf-8"))
    assert report["track"] == TRACK.name
    # Written before the 2026-10-11 rename, on 398 fixtures: its stems are the pins' legacy names,
    # plus the two strict-OOXML sources dropped then because their DOCX is not in corpus/.
    legacy = {f.legacy_stem for f in load_fixtures(track=TRACK)}
    assert set(report["stems"]) - legacy == {"source__strict01_sdt_controls", "source__word_clean_strict01"}
    assert legacy <= set(report["stems"])
    lines = [
        json.loads(raw)
        for raw in store.read_text(encoding="utf-8").splitlines()
        if raw.strip()
    ]
    in_store = {ln["tool"] for ln in lines if ln.get("track") == TRACK.name}
    assert set(report["tools"]) <= in_store


def test_no_redline_report_lines_carry_the_track(tmp_path):
    from neurotic_docx_bench.ledger import converters as conv

    report = {
        "track": TRACK.name,
        "n": 396,
        "stems": ["a"],
        "tools": {
            "rdocx": {
                "n_scored": 398,
                "itt_n": 396,
                "mean": 10.0,
                "median": 9.0,
                "perfects": 0,
                "failures": 0,
            },
        },
    }
    (line,) = conv.lines_from_report(report, hardware=None, report_path="r.json")
    assert line["track"] == TRACK.name and line["itt_n"] == 396
