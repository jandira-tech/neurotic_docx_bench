"""The denominator of every benchmark is the oracle document set, not oracle ∩ candidate."""

from __future__ import annotations

import json
from pathlib import Path

from neurotic_docx_bench.ledger import docset as ds


def _touch(d: Path, *names: str) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    for n in names:
        (d / n).write_bytes(b"")
    return d


def test_redline_keys_normalize_word_variant_and_skip_non_redlines(
    tmp_path: Path,
) -> None:
    d = _touch(
        tmp_path / "o",
        "a_b_redline.pdf",
        "c_d_word_redline.pdf",
        "c_d_redline.pdf",
        "a.pdf",
    )
    assert ds.keys_in_dir(d, "redline") == {"a_b", "c_d"}


def test_accepted_keys_from_docx_and_pdf(tmp_path: Path) -> None:
    d = _touch(
        tmp_path / "o",
        "a_b_redline_accepted.docx",
        "a_b_word_redline_accepted.pdf",
        "c_d_redline_accepted.docx",
    )
    assert ds.keys_in_dir(d, "accepted") == {"a_b", "c_d"}


def test_plain_keys_lowercase_stems(tmp_path: Path) -> None:
    d = _touch(tmp_path / "o", "Alpha.docx", "beta.pdf", "notes.txt")
    assert ds.keys_in_dir(d, "plain") == {"alpha", "beta"}


def test_docset_id_is_order_independent_and_12_hex() -> None:
    a = ds.docset_id({"x", "y"})
    b = ds.docset_id(["y", "x"])
    assert a == b and len(a) == 12 and int(a, 16) >= 0


def test_benchmark_docset_applies_holdout(tmp_path: Path) -> None:
    d = _touch(tmp_path / "o", "a_b_redline.pdf", "c_d_redline.pdf", "e_f_redline.pdf")
    full = ds.benchmark_docset(
        "script_redlines", [d], holdout={"c_d"}, holdout_mode=None
    )
    excl = ds.benchmark_docset(
        "script_redlines", [d], holdout={"c_d"}, holdout_mode="excluded"
    )
    only = ds.benchmark_docset(
        "script_redlines", [d], holdout={"c_d"}, holdout_mode="only"
    )
    assert set(full.keys) == {"a_b", "c_d", "e_f"}
    assert set(excl.keys) == {"a_b", "e_f"}
    assert set(only.keys) == {"c_d"}
    assert full.id != excl.id != only.id
    assert full.n == 3


def test_missing_output_failures_name_docs_with_no_score_and_no_failure() -> None:
    keys = {"a", "b", "c", "d"}
    scores = {"a": 1.0}
    failures = [{"doc": "b", "stage": "generate", "error": "x"}]
    added = ds.missing_output_failures(keys, scores, failures)
    assert added == [
        {
            "doc": "c",
            "stage": "missing_output",
            "error": "no candidate output for this document",
        },
        {
            "doc": "d",
            "stage": "missing_output",
            "error": "no candidate output for this document",
        },
    ]


def test_missing_output_ignores_docs_outside_the_set() -> None:
    assert ds.missing_output_failures({"a"}, {"zzz": 1.0}, []) == [
        {
            "doc": "a",
            "stage": "missing_output",
            "error": "no candidate output for this document",
        },
    ]


def test_restrict_to_docset_drops_outsiders_and_fills_missing() -> None:
    r = ds.restrict_to_docset(
        {"a", "b", "c"},
        {"a": 90.0, "zzz": 1.0},
        {"a": {"score": 90.0}, "zzz": {"score": 1.0}},
        [
            {"doc": "b", "stage": "generate", "error": "x"},
            {"doc": "yyy", "stage": "generate", "error": "x"},
        ],
    )
    assert r.scores == {"a": 90.0}
    assert r.per_doc == {"a": {"score": 90.0}}
    assert [f["doc"] for f in r.failures] == ["b", "c"]
    assert r.failures[1]["stage"] == "missing_output"
    assert r.dropped_scores == ("zzz",) and r.dropped_failures == ("yyy",)
    assert len(r.scores) + len({f["doc"] for f in r.failures}) == 3


def test_restrict_to_docset_keeps_per_doc_none() -> None:
    r = ds.restrict_to_docset({"a"}, {"a": 1.0}, None, [])
    assert r.per_doc is None and r.failures == []


def test_write_and_load_docsets(tmp_path: Path) -> None:
    d = _touch(tmp_path / "o", "a_b_redline.pdf")
    one = ds.benchmark_docset(
        "script_redlines", [d], holdout=set(), holdout_mode="excluded"
    )
    p = tmp_path / "docsets.json"
    ds.write_docsets(p, [one], source_dirs={one.id: [str(d)]})
    loaded = ds.load_docsets(p)
    assert loaded[one.id]["benchmark"] == "script_redlines"
    assert loaded[one.id]["n"] == 1
    assert json.loads(p.read_text())[one.id]["holdout_mode"] == "excluded"


def test_docset_command_lists_benchmarks(tmp_path: Path, monkeypatch) -> None:
    from typer.testing import CliRunner

    from neurotic_docx_bench.cli import app

    oracle = _touch(
        tmp_path / "pdf_redlines_word", "a_b_redline.pdf", "c_d_redline.pdf"
    )
    (tmp_path / "bench.yaml").write_text(
        f"source_of_truth: {oracle}\nscoring: {{dpi: 144}}\nruns: []\n"
    )
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["docset", "--config", "bench.yaml", "--write"])
    assert result.exit_code == 0, result.output
    assert "script_redlines: 2 documents" in result.output
    assert (tmp_path / "results" / "docsets.json").is_file()
