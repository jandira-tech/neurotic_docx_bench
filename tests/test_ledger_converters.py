"""Converter reports become store lines; the table is built from the store, never from the last run."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from neurotic_docx_bench.ledger import converters as cv
from neurotic_docx_bench.ledger import rows as rws
from neurotic_docx_bench.ledger.registry import load_registry


def _report(track: str = "docx_to_pdf") -> dict:
    return {
        "generated_at": "2026-08-16T19:50:57+00:00",
        "n": 3,
        "oracle": "microsoft_word",
        "track": track,
        "stems": ["s1", "s2", "s3"],
        "tools": {
            "jubarte": {
                "version": "jubarte 0.7.0",
                "itt_n": 3,
                "n_scored": 3,
                "failures": 0,
                "generate_failures": [],
                "mean": 60.0,
                "median": 62.0,
                "perfects": 0,
                "per_doc": {"s1": 60.0, "s2": 62.0, "s3": 58.0},
            },
            "doxx": {
                "version": "doxx 0.1.4",
                "itt_n": 3,
                "n_scored": 0,
                "failures": 3,
                "generate_failures": [{"doc": "s1"}, {"doc": "s2"}, {"doc": "s3"}],
                "mean": 0.0,
                "median": 0.0,
                "perfects": 0,
                "per_doc": {"s1": 0.0, "s2": 0.0, "s3": 0.0},
            },
        },
    }


def _docxide_report() -> dict:
    return {
        "generated_at": "2026-09-05T07:30:17+00:00",
        "n": 2,
        "oracle": "microsoft_word",
        "track": "docxide_metrics",
        "dpi": 150,
        "stems": ["s1", "s2"],
        "tools": {
            "jubarte": {
                "version": "jubarte 0.8.0",
                "itt_n": 2,
                "n_scored": 2,
                "failures": 0,
                "generate_failures": [],
                "metrics": {
                    "jaccard": {"mean": 53.1, "median": 43.5},
                    "ssim": {"mean": 72.8, "median": 89.0},
                    "text_boundary": {"mean": 87.6, "median": 100.0},
                },
                "per_doc": {
                    "s1": {"jaccard": 40.0, "ssim": 80.0, "text_boundary": 100.0},
                    "s2": {"jaccard": 47.0, "ssim": 98.0, "text_boundary": 100.0},
                },
            }
        },
    }


def test_lines_from_docx_to_pdf_report() -> None:
    lines = cv.lines_from_report(
        _report(), hardware={"cpu": "x"}, report_path="results/r.json"
    )
    assert [
        (ln["tool"], ln["lens"], ln["itt_n"], ln["n_scored"], ln["failures"])
        for ln in lines
    ] == [
        ("jubarte", "pixel", 3, 3, 0),
        ("doxx", "pixel", 3, 0, 3),
    ]
    j = lines[0]
    assert j["scores"] == {"s1": 60.0, "s2": 62.0, "s3": 58.0}
    assert j["failed_docs"] == []
    assert j["docset_id"] == cv.stems_docset_id(["s3", "s1", "s2"])
    assert j["timestamp"] == "2026-08-16T19:50:57+00:00" and j["hardware"] == {
        "cpu": "x"
    }
    assert j["id_run"] and j["report_path"] == "results/r.json"
    assert lines[1]["scores"] == {} and lines[1]["failed_docs"] == ["s1", "s2", "s3"]


def test_lines_from_docxide_report_rank_on_jaccard_and_carry_extras() -> None:
    (line,) = cv.lines_from_report(_docxide_report(), hardware=None, report_path="")
    assert line["lens"] == "jaccard" and line["scorer"] == "docxide-150dpi"
    assert line["scores"] == {"s1": 40.0, "s2": 47.0}
    assert line["extra"] == {
        "ssim": {"mean": 72.8, "median": 89.0},
        "text_boundary": {"mean": 87.6, "median": 100.0},
    }
    assert line["mean"] == 53.1 and line["median"] == 43.5


def test_append_report_writes_jsonl(tmp_path: Path) -> None:
    p = tmp_path / "converters.jsonl"
    assert cv.append_report(p, _report(), hardware=None, report_path="r.json") == 2
    assert (
        cv.append_report(p, _docxide_report(), hardware=None, report_path="d.json") == 1
    )
    assert len(p.read_text().splitlines()) == 3


@pytest.fixture
def registry(tmp_path: Path):
    doc = {
        "schema_version": 1,
        "tools": [
            {
                "id": "jubarte-pdf",
                "vendor": "jubarte",
                "display": "jubarte",
                "role": "converter",
                "engine": "jubarte-redlines",
                "affiliated": True,
                "converter_tools": ["jubarte"],
            },
            {
                "id": "doxx",
                "vendor": "doxx",
                "display": "doxx",
                "role": "converter",
                "engine": "doxx",
                "converter_tools": ["doxx"],
                "not_applicable": ["docx_to_pdf"],
            },
        ],
    }
    p = tmp_path / "reg.yaml"
    p.write_text(yaml.safe_dump(doc))
    return load_registry(p)


def test_converter_rows_load_with_tool_ids(tmp_path: Path, registry) -> None:
    p = tmp_path / "converters.jsonl"
    cv.append_report(p, _report(), hardware=None, report_path="r.json")
    cv.append_report(p, _docxide_report(), hardware=None, report_path="d.json")
    with p.open("a") as fh:
        fh.write(
            '{"source": "converter", "track": "docx_to_pdf", "tool": "ghost", "itt_n": 1}\n'
        )
    rows, unmapped = rws.load_converter_rows(p, registry)
    assert [u["tool"] for u in unmapped] == ["ghost"]
    assert [
        (r.tool_id, r.benchmark, r.itt_n, r.n_failed_docs, r.provenance) for r in rows
    ] == [
        ("jubarte-pdf", "docx_to_pdf", 3, 0, "stamped"),
        ("doxx", "docx_to_pdf", 3, 3, "stamped"),
        ("jubarte-pdf", "docxide_metrics", 2, 0, "stamped"),
    ]
    assert rows[0].renderer_id == "oracle:microsoft_word" and rows[0].docset_id
    assert rows[1].itt_scores() == {"s1": 0.0, "s2": 0.0, "s3": 0.0}
    assert rows[2].lens == "jaccard" and rows[2].extra["ssim"]["median"] == 89.0
    assert rws.load_converter_rows(tmp_path / "missing.jsonl", registry) == ([], [])
