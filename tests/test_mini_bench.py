"""Spec for the mini-bench selection (``scripts/mini_bench.py``): the worst n documents of
one converter run plus n/4 spread over the rest of its distribution, reproducible by name."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "mini_bench.py"


def _load():
    spec = importlib.util.spec_from_file_location("mini_bench", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mini_bench"] = mod
    spec.loader.exec_module(mod)
    return mod


mb = _load()


def _scores(k: int) -> dict[str, float]:
    return {f"clean__d{i:04d}": float(i) for i in range(k)}


def test_worst_n_are_the_lowest_scores():
    picked = mb.select_docs(_scores(100), n=20)
    worst = [p for p in picked if p.bucket == "worst"]
    assert [p.key for p in worst] == [f"clean__d{i:04d}" for i in range(20)]
    assert [p.rank for p in worst] == list(range(1, 21))


def test_spread_is_a_quarter_of_n_over_the_rest():
    picked = mb.select_docs(_scores(100), n=20)
    spread = [p for p in picked if p.bucket == "spread"]
    assert len(spread) == 5
    # The rest is d0020..d0099 (80 docs): the midpoints of five strata of 16.
    assert [p.key for p in spread] == [f"clean__d{20 + j:04d}" for j in (8, 24, 40, 56, 72)]
    assert all(p.key not in {w.key for w in picked if w.bucket == "worst"} for p in spread)


def test_failed_documents_count_as_zero_and_ties_break_by_key():
    scores = {"clean__b": 10.0, "clean__a": 10.0, "clean__c": 50.0}
    picked = mb.select_docs(scores, n=3, failed=["clean__z"])
    assert [p.key for p in picked] == ["clean__z", "clean__a", "clean__b"]
    assert picked[0].score == 0.0


def test_small_run_takes_everything_once():
    picked = mb.select_docs(_scores(6), n=4)
    keys = [p.key for p in picked]
    assert len(keys) == len(set(keys)) == 5  # 4 worst + 1 spread of the remaining 2


def test_max_pages_drops_longer_documents_before_ranking():
    scores = {"clean__long": 1.0, "clean__short": 2.0, "clean__three": 3.0}
    pages = {"clean__long": 4, "clean__short": 1, "clean__three": 3}
    kept = mb.filter_pages(scores, pages.__getitem__, max_pages=3)
    assert kept == {"clean__short": 2.0, "clean__three": 3.0}
    assert mb.filter_pages(scores, pages.__getitem__, max_pages=None) == scores


def test_itt_reads_per_doc_and_counts_a_missing_document_as_zero():
    pixel = {"per_doc": {"clean__a": 80.0}}
    docxide = {"per_doc": {"clean__a": {"jaccard": 40.0, "text_boundary": 100.0}}}
    assert mb._itt(pixel, ["clean__a", "clean__b"], None) == [80.0, 0.0]
    assert mb._itt(docxide, ["clean__a", "clean__b"], "jaccard") == [40.0, 0.0]


def test_convert_writes_cli_pdfs_under_a_relative_out(tmp_path, monkeypatch):
    # Each CLI call runs in a scratch cwd, so a relative --out must be resolved first.
    fake = tmp_path / "fake-conv"
    fake.write_text('#!/bin/sh\nprintf "%%PDF-1.4 fake" > "$2"\n')
    fake.chmod(0o755)
    docx = tmp_path / "a.docx"
    docx.write_bytes(b"PK")
    monkeypatch.chdir(tmp_path)
    out = Path("sel")
    out.mkdir()
    (out / "selection.csv").write_text(f"bucket,rank,key,source_score,docx,pdf\nworst,1,clean__a,1.0,{docx},x.pdf\n")
    (out / "selection.json").write_text("{}")
    from neurotic_docx_bench import docx_to_pdf as d2p

    monkeypatch.setattr(d2p, "resolve_tool_binary", lambda tool, override=None: fake)
    monkeypatch.setattr(mb, "versions", lambda tools, jubarte: {t: "fake 1" for t in tools})
    args = mb.argparse.Namespace(out="sel", tools="docxide-pdf", jubarte=None, timeout=10)
    mb.cmd_convert(args)
    assert (tmp_path / "sel" / "pdf" / "docxide-pdf" / "clean__a.pdf").read_bytes().startswith(b"%PDF-")


def test_convert_with_workers_makes_every_pdf_and_one_log_row_each(tmp_path, monkeypatch):
    fake = tmp_path / "fake-conv"
    fake.write_text('#!/bin/sh\nsleep 0.2\nprintf "%%PDF-1.4 fake" > "$2"\n')
    fake.chmod(0o755)
    lines = ["bucket,rank,key,source_score,docx,pdf"]
    for i in range(8):
        (tmp_path / f"d{i}.docx").write_bytes(b"PK")
        lines.append(f"worst,{i + 1},clean__d{i},1.0,{tmp_path / f'd{i}.docx'},x.pdf")
    out = tmp_path / "sel"
    out.mkdir()
    (out / "selection.csv").write_text("\n".join(lines) + "\n")
    (out / "selection.json").write_text("{}")
    from neurotic_docx_bench import docx_to_pdf as d2p

    monkeypatch.setattr(d2p, "resolve_tool_binary", lambda tool, override=None: fake)
    monkeypatch.setattr(mb, "versions", lambda tools, jubarte: {t: "fake 1" for t in tools})
    args = mb.argparse.Namespace(out=str(out), tools="docxide-pdf", jubarte=None, timeout=10, workers=4)
    t0 = mb.time.perf_counter()
    mb.cmd_convert(args)
    assert mb.time.perf_counter() - t0 < 1.2  # 8 x 0.2 s one at a time is >= 1.6 s
    assert sorted(p.name for p in (out / "pdf" / "docxide-pdf").iterdir()) == [f"clean__d{i}.pdf" for i in range(8)]
    rows = [mb.json.loads(ln) for ln in (out / "convert.jsonl").read_text().splitlines()]
    assert sorted(r["key"] for r in rows) == [f"clean__d{i}" for i in range(8)]
    assert all(r["ok"] for r in rows)


def test_pymupdf_pro_runs_on_every_selection_and_long_documents_are_flagged():
    assert "pymupdf-pro" in mb.default_tools(None)
    assert "pymupdf-pro" in mb.default_tools(3)
    pages = {"clean__a": 2, "clean__b": 7, "clean__c": 4}
    note = mb.pymupdf_note(["clean__a", "clean__b", "clean__c"], pages.__getitem__)
    assert "2 of 3" in note and "first 3 pages" in note
    assert mb.pymupdf_note(["clean__a"], pages.__getitem__) == ""


def _prior(tool, version, per_doc, stems, *, scorer="pixel", failed=(), track="corpus/word:all"):
    data = {"tool": tool, "version": version, "per_doc": per_doc,
            "generate_failures": [{"doc": d, "stage": "generate", "error": "boom"} for d in failed]}
    rep = {"stems": list(stems), "tools": {tool: data}}
    if scorer == "pixel":
        rep["track"] = track
    else:
        rep["track"], rep["fixture_track"] = "docxide_metrics", track
    return rep


def test_prior_per_doc_takes_only_the_same_tool_version_scorer_and_corpus():
    reports = [
        ("old", _prior("soffice", "LO 1", {"clean__a": 11.0}, ["clean__a"])),
        ("other-corpus", _prior("soffice", "LO 2", {"clean__b": 12.0}, ["clean__b"], track="docx_to_pdf")),
        ("jac", _prior("soffice", "LO 2", {"clean__a": {"jaccard": 5.0, "text_boundary": 9.0}}, ["clean__a"], scorer="docxide")),
        ("good", _prior("soffice", "LO 2", {"clean__a": 80.0}, ["clean__a", "clean__c"], failed=["clean__c"])),
    ]
    got = mb.prior_per_doc(reports, "soffice", "LO 2", "pixel")
    # clean__c is covered: the prior run failed it, which is a result (0 under ITT).
    assert got == {"clean__a": ("good", 80.0, True), "clean__c": ("good", 0.0, False)}
    jac = mb.prior_per_doc(reports, "soffice", "LO 2", "docxide")
    assert jac == {"clean__a": ("jac", {"jaccard": 5.0, "text_boundary": 9.0}, True)}


def test_merge_reused_keeps_prior_values_and_fresh_scores_with_provenance():
    prior = {"clean__a": ("run-1", 80.0, True), "clean__c": ("run-1", 0.0, False)}
    fresh = {"stems": ["clean__b"], "track": "mini_bench:x", "tools": {"soffice": {
        "tool": "soffice", "version": "LO 2", "per_doc": {"clean__b": 60.0}, "generate_failures": []}}}
    rep = mb.merge_reused(fresh, prior, ["clean__a", "clean__b", "clean__c"], "soffice", "pixel")
    data = rep["tools"]["soffice"]
    assert rep["stems"] == ["clean__a", "clean__b", "clean__c"]
    assert data["per_doc"] == {"clean__a": 80.0, "clean__b": 60.0, "clean__c": 0.0}
    assert [f["doc"] for f in data["generate_failures"]] == ["clean__c"]
    assert data["itt_n"] == 3 and data["n_scored"] == 2 and data["failures"] == 1
    assert data["mean"] == 70.0 and data["median"] == 70.0
    assert data["reused_from"] == {"run-1": 2}


def test_merge_reused_with_everything_covered_needs_no_fresh_report():
    prior = {"clean__a": ("r", {"jaccard": 40.0, "text_boundary": 90.0}, True)}
    rep = mb.merge_reused(None, prior, ["clean__a"], "soffice", "docxide", version="LO 2", track="mini_bench:x")
    data = rep["tools"]["soffice"]
    assert rep["track"] == "docxide_metrics" and data["version"] == "LO 2"
    assert data["metrics"]["jaccard"]["mean"] == 40.0 and data["metrics"]["text_boundary"]["median"] == 90.0
    assert data["reused_from"] == {"r": 1}


def test_convert_skips_documents_both_scorers_already_have(tmp_path, monkeypatch):
    fake = tmp_path / "fake-conv"
    fake.write_text('#!/bin/sh\nprintf "%%PDF-1.4 fake" > "$2"\n')
    fake.chmod(0o755)
    lines = ["bucket,rank,key,source_score,docx,pdf"]
    for k in ("a", "b"):
        (tmp_path / f"{k}.docx").write_bytes(b"PK")
        lines.append(f"worst,1,clean__{k},1.0,{tmp_path / f'{k}.docx'},x.pdf")
    out = tmp_path / "sel"
    out.mkdir()
    (out / "selection.csv").write_text("\n".join(lines) + "\n")
    (out / "selection.json").write_text("{}")
    from neurotic_docx_bench import docx_to_pdf as d2p

    monkeypatch.setattr(d2p, "resolve_tool_binary", lambda tool, override=None: fake)
    monkeypatch.setattr(mb, "versions", lambda tools, jubarte: {t: "fake 1" for t in tools})
    covered = {"clean__a": ("r", 1.0, True)}
    monkeypatch.setattr(mb, "prior_covered", lambda tool, version, out_dir: covered)
    args = mb.argparse.Namespace(out=str(out), tools="docxide-pdf", jubarte=None, timeout=10, workers=1)
    mb.cmd_convert(args)
    assert sorted(p.name for p in (out / "pdf" / "docxide-pdf").iterdir()) == ["clean__b.pdf"]


def test_key_splits_into_state_and_stem():
    assert mb.split_key("with_comments_clean__abc_def") == ("with_comments_clean", "abc_def")
