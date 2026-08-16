"""DOCX→PDF track: fixture pin, shipped visual scoring, plain-stem pairing."""

from __future__ import annotations

import shutil

import pytest

from neurotic_docx_bench import pipeline
from neurotic_docx_bench.docx_to_pdf import (
    REQUIRED_FEATURES,
    feature_coverage,
    load_fixtures,
    score_folder_pair,
)
from helpers import CORPUS


PDF_SOURCE = CORPUS / "pdf_source"


def test_fixture_set_is_100_distinct_docx_with_soffice_oracles():
    fixtures = load_fixtures()
    assert len(fixtures) == 100
    stems = [item.stem for item in fixtures]
    assert len(set(stems)) == 100
    for item in fixtures:
        assert item.docx.is_file(), f"missing DOCX {item.docx}"
        assert item.docx.suffix == ".docx"
        assert item.oracle.is_file(), f"missing soffice oracle {item.oracle}"
        assert item.oracle.suffix == ".pdf"
        assert item.docx.stem == item.stem
        assert item.oracle.stem == item.stem
        assert item.oracle.read_bytes()[:5] == b"%PDF-"


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
