"""Calibration candidates: the oracle DOCX renamed as a candidate, and the base DOCX unchanged."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
import yaml

from neurotic_docx_bench import calibration as cal


def _corpus(tmp_path: Path) -> tuple[Path, Path, Path]:
    src = tmp_path / "docx_source"
    src.mkdir()
    red = tmp_path / "docx_redlines_word"
    red.mkdir()
    (src / "a.docx").write_bytes(b"A")
    (src / "b.docx").write_bytes(b"B")
    (red / "a_b_word_redline.docx").write_bytes(b"AB")
    (red / "c_d_redline.docx").write_bytes(b"CD")
    (src / "c.docx").write_bytes(b"C")
    mapping = tmp_path / "centralized_mapping.csv"
    with mapping.open("w", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=[
                "pair_stem",
                "docx_source_base",
                "redline_docx",
                "redline_docx_word",
            ],
        )
        w.writeheader()
        w.writerow(
            {
                "pair_stem": "a_b",
                "docx_source_base": "a.docx",
                "redline_docx": "",
                "redline_docx_word": "a_b_word_redline.docx",
            }
        )
        w.writerow(
            {
                "pair_stem": "c_d",
                "docx_source_base": "c.docx",
                "redline_docx": "c_d_redline.docx",
                "redline_docx_word": "",
            }
        )
    return src, red, mapping


def test_oracle_identity_candidates_are_the_oracle_docx_renamed(tmp_path: Path) -> None:
    src, red, mapping = _corpus(tmp_path)
    report = cal.build_candidates(
        "oracle-identity",
        manifest=mapping,
        source_dir=src,
        redline_dirs=[red],
        out_dir=tmp_path / "out",
    )
    assert report.written == 2
    assert sorted(p.name for p in report.out_dir.iterdir()) == [
        "a_b_oracle-identity_redline.docx",
        "c_d_oracle-identity_redline.docx",
    ]
    assert (report.out_dir / "a_b_oracle-identity_redline.docx").read_bytes() == b"AB"
    assert (report.out_dir / "c_d_oracle-identity_redline.docx").read_bytes() == b"CD"


def test_null_baseline_candidates_are_the_base_docx(tmp_path: Path) -> None:
    src, red, mapping = _corpus(tmp_path)
    report = cal.build_candidates(
        "null-baseline",
        manifest=mapping,
        source_dir=src,
        redline_dirs=[red],
        out_dir=tmp_path / "out",
    )
    assert (report.out_dir / "a_b_null-baseline_redline.docx").read_bytes() == b"A"
    assert (report.out_dir / "c_d_null-baseline_redline.docx").read_bytes() == b"C"


def test_missing_oracle_is_an_error_naming_the_pair(tmp_path: Path) -> None:
    src, red, mapping = _corpus(tmp_path)
    (red / "a_b_word_redline.docx").unlink()
    with pytest.raises(FileNotFoundError, match="a_b"):
        cal.build_candidates(
            "oracle-identity",
            manifest=mapping,
            source_dir=src,
            redline_dirs=[red],
            out_dir=tmp_path / "out",
        )


def test_missing_base_is_an_error_naming_the_pair(tmp_path: Path) -> None:
    src, red, mapping = _corpus(tmp_path)
    (src / "c.docx").unlink()
    with pytest.raises(FileNotFoundError, match="c_d"):
        cal.build_candidates(
            "null-baseline",
            manifest=mapping,
            source_dir=src,
            redline_dirs=[red],
            out_dir=tmp_path / "out",
        )


def test_calibration_config_carries_the_shared_environment_and_two_docx_runs(
    tmp_path: Path,
) -> None:
    base = {
        "source_of_truth": "corpus/word_based/pdf_redlines_word",
        "extra_oracle_dirs": ["corpus/x/pdf"],
        "holdout_list": "corpus/holdout_combined.txt",
        "scoring": {"dpi": 144},
        "corpora": [{"name": "w", "manifest": "m.csv", "source_dir": "s"}],
        "runs": [{"name": "docxodus", "render": "soffice"}],
    }
    doc = cal.calibration_config(
        base, oracle_dir=tmp_path / "o", null_dir=tmp_path / "n"
    )
    assert doc["source_of_truth"] == base["source_of_truth"]
    assert doc["extra_oracle_dirs"] == base["extra_oracle_dirs"]
    assert doc["holdout_list"] == base["holdout_list"]
    assert [
        (r["name"], r["render"], r["vendor"], r["benchmarks"], r["unversioned"])
        for r in doc["runs"]
    ] == [
        ("oracle-identity", "soffice", "oracle-identity", ["script_redlines"], True),
        ("null-baseline", "soffice", "null-baseline", ["script_redlines"], True),
    ]
    assert doc["runs"][0]["docx"] == str(tmp_path / "o")
    assert "accepted_ground_truth" not in doc
    yaml.safe_dump(doc)  # serializable


def test_calibrate_command_builds_candidates_and_drives_two_runs(
    tmp_path: Path, monkeypatch
) -> None:
    from typer.testing import CliRunner

    from neurotic_docx_bench import cli

    corpus = tmp_path / "corpus" / "word_based"
    corpus.mkdir(parents=True)
    src, red, mapping = _corpus(corpus)
    (tmp_path / "bench.yaml").write_text(
        yaml.safe_dump(
            {
                "source_of_truth": str(corpus / "pdf_redlines_word"),
                "scoring": {"dpi": 144},
                "corpora": [
                    {
                        "name": "word_based",
                        "manifest": str(mapping),
                        "source_dir": str(src),
                    },
                ],
                "runs": [],
            }
        )
    )
    captured: dict = {}

    def fake_drive(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(cli, "_drive_runs", fake_drive)
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli.app, ["calibrate", "--out", str(tmp_path / "cal")])
    assert result.exit_code == 0, result.output
    assert "oracle-identity: 2 candidate DOCX" in result.output
    assert "null-baseline: 2 candidate DOCX" in result.output
    derived = yaml.safe_load(captured["config"].read_text())
    assert [r["name"] for r in derived["runs"]] == ["oracle-identity", "null-baseline"]
    assert (
        tmp_path
        / "cal"
        / "oracle-identity"
        / "docx"
        / "a_b_oracle-identity_redline.docx"
    ).is_file()
    assert (
        captured["do_gate"] is False
        and captured["rerun"] is True
        and captured["emit"] is True
    )
