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
    WORD_CORPUS,
    feature_coverage,
    load_fixtures,
    oracle_pdf_dirs,
    render_docx_to_pdf_table,
    run_eval,
    score_folder_pair,
    select_word_oracle_fixtures,
    update_readme_docx_to_pdf,
    verify_oracle_sha_manifest,
    write_oracle_sha_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
LIBREOFFICE_PDF_SOURCE = REPO_ROOT / "corpus" / "word_based" / "pdf_source"
TRACK = NO_REDLINE_TRACK
KINDS = {"source", "source_randomized"}


def test_oracles_are_only_source_and_source_randomized_word_exports():
    fixtures = load_fixtures(track=TRACK)
    assert fixtures
    stems = [item.stem for item in fixtures]
    assert len(set(stems)) == len(fixtures)
    allowed = {d.resolve() for d in oracle_pdf_dirs(track=TRACK)}
    assert {d.name for d in allowed} == set(TRACK.oracle_pdf_dir_names)
    lo_root = LIBREOFFICE_PDF_SOURCE.resolve()
    kinds: set[str] = set()
    for item in fixtures:
        kinds.add(item.kind)
        assert item.docx.is_file(), f"missing DOCX {item.docx}"
        assert item.oracle.is_file(), f"missing Word oracle {item.oracle}"
        assert item.oracle.read_bytes()[:5] == b"%PDF-"
        assert item.kind in KINDS
        assert item.stem == f"{item.kind}__{item.original_stem}"
        oracle = item.oracle.resolve()
        assert oracle.parent in allowed
        assert lo_root not in oracle.parents
        assert oracle.parent.name in TRACK.oracle_pdf_dir_names
        head = item.oracle.read_bytes()[:65_536]
        assert b"LibreOffice" not in head, f"{item.stem} looks like a LibreOffice PDF"
    assert kinds == KINDS


def test_pin_list_matches_deterministic_no_redline_selection():
    pinned = [(item.kind, item.original_stem) for item in load_fixtures(track=TRACK)]
    expected = [(item.kind, item.original_stem) for item in select_word_oracle_fixtures(track=TRACK)]
    assert pinned == expected
    assert {kind for kind, _ in pinned} == KINDS


def test_oracle_sha256_manifest_covers_every_source_pdf_and_detects_tamper(tmp_path):
    verify_oracle_sha_manifest(track=TRACK)
    fixtures = load_fixtures(track=TRACK)
    from neurotic_docx_bench.oracle_manifest import _sha256, load_manifest

    manifest = load_manifest(TRACK.sha_manifest)
    assert manifest
    for item in fixtures:
        rel = item.oracle.resolve().relative_to(WORD_CORPUS.resolve()).as_posix()
        assert manifest[rel] == _sha256(item.oracle)
    fake_root = tmp_path / "corpus"
    for name in TRACK.oracle_pdf_dir_names:
        (fake_root / name).mkdir(parents=True)
        src = next(p for p in fixtures if p.oracle.parent.name == name).oracle
        dest = fake_root / name / src.name
        dest.write_bytes(src.read_bytes())
    write_oracle_sha_manifest(tmp_path / "sha.json", fake_root, track=TRACK)
    victim = next((fake_root / TRACK.oracle_pdf_dir_names[0]).glob("*.pdf"))
    victim.write_bytes(b"%PDF-TAMPER")
    with pytest.raises(RuntimeError, match="oracle PDF drift"):
        verify_oracle_sha_manifest(tmp_path / "sha.json", fake_root, track=TRACK)


def test_fixture_set_covers_required_document_features():
    fixtures = load_fixtures(track=TRACK)
    found = feature_coverage(fixtures)
    missing = REQUIRED_FEATURES - found
    assert not missing, f"fixture set missing features: {sorted(missing)}"


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


def test_readme_no_redline_table_matches_committed_artifact():
    artifact = REPO_ROOT / "results" / "docx_to_pdf_no_redline.json"
    if not artifact.is_file():
        pytest.skip("no_redline eval artifact not written yet")
    report = json.loads(artifact.read_text(encoding="utf-8"))
    assert report["track"] == TRACK.name
    assert report["n"] == len(load_fixtures(track=TRACK))
    expected = render_docx_to_pdf_table(report, track=TRACK).strip()
    assert expected in (REPO_ROOT / "README.md").read_text(encoding="utf-8")


def test_update_readme_replaces_no_redline_marked_block(tmp_path):
    report = {
        "track": TRACK.name,
        "n": 398,
        "tools": {
            "rdocx": {
                "n_scored": 398,
                "itt_n": 398,
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
        f"{TRACK.readme_start}\nold table\n{TRACK.readme_end}\ntail\n",
    )
    update_readme_docx_to_pdf(readme, report, track=TRACK)
    text = readme.read_text()
    assert "head" in text
    assert "tail" in text
    assert "old table" not in text
    assert render_docx_to_pdf_table(report, track=TRACK).strip() in text
