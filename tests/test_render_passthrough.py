"""passthrough renderer — the source is already PDFs."""

from __future__ import annotations

import shutil

import pytest

from neurotic_docx_bench.render.passthrough import PassthroughRenderer


def test_passthrough_lists_existing_pdfs(tmp_path, sample_oracle_pdfs):
    src = tmp_path / "pdfs"
    src.mkdir()
    for p in sample_oracle_pdfs:
        shutil.copy(p, src / p.name)

    report = PassthroughRenderer().to_pdfs(src, tmp_path / "work")
    assert report.pdf_dir == src, "passthrough points at the source, does not copy"
    assert report.ok_count == len(sample_oracle_pdfs)
    assert all(r.skipped for r in report.results)
    assert len(report.pdfs) == len(sample_oracle_pdfs)


def test_passthrough_missing_dir_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        PassthroughRenderer().to_pdfs(tmp_path / "nope", tmp_path / "work")


def test_passthrough_empty_dir_ok(tmp_path):
    src = tmp_path / "empty"
    src.mkdir()
    report = PassthroughRenderer().to_pdfs(src, tmp_path / "work")
    assert report.ok_count == 0 and report.pdfs == []
