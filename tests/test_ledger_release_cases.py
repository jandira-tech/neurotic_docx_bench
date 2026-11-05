"""Release-set case shards and shown-page staging (plan 7, issue #131).

The fixture is wholly synthetic: two fixed-set rows, tiny PyMuPDF PDFs and
JSON score artifacts shaped like the set-scoped stores.  Nothing here reads
the corpus, the network, Word, or R2.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip(
    "bench_ops",
    reason=(
        "bench-ops is a PEP 723 dependency; run these tests with the pinned "
        "bench-ops overlay from scripts/release_views.py"
    ),
)

from neurotic_docx_bench import cli, hub_outputs
from neurotic_docx_bench.ledger import build as ledger_build
from neurotic_docx_bench.ledger import cases as cases_emit

from bench_ops.models import (
    CaseShard,
    CasesIndex,
    dumps_compact,
    shard_path,
    validate_bundle,
)

FILES_BASE = (
    "https://huggingface.co/datasets/arthrod/neurotic_docx_bench/resolve/"
    "0123456789abcdef0123456789abcdef01234567/"
)
CONVERT_A = "clean__alpha"
CONVERT_B = "clean__beta"
REDLINE_A = "alpha__vs__beta_redline_aaaaaaaa"
REDLINE_B = "alpha__vs__gamma_redline_bbbbbbbb"


def _pdf(path: Path, pages: int = 3) -> Path:
    import pymupdf

    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    for number in range(pages):
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 72), f"page {number + 1}")
    doc.save(path)
    doc.close()
    return path


def _json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _conversion_report(
    stems: list[str], scores: dict[str, float], *, per_page: dict | None = None
) -> dict:
    tool = {
        "tool": "docxodus",
        "version": "docxodus 15.0.0",
        "n_scored": len(scores),
        "per_doc": scores,
        "convert_seconds": {stem: 1.25 for stem in scores},
        "generate_failures": [],
        "failures": 0,
    }
    if per_page is not None:
        tool["per_page"] = per_page
    return {
        "generated_at": "2026-11-03T00:00:00+00:00",
        "n": len(stems),
        "oracle": "microsoft_word",
        "scorer_backend": "numpy",
        "stems": stems,
        "tools": {"docxodus": tool},
        "track": "corpus/word:list",
        "warnings": [],
    }


def _redline_scores(rows: dict[str, dict]) -> dict:
    return {
        "summary": {"scorer_backend": "numpy"},
        "missing": [],
        "fresh_missing": [],
        "rows": rows,
    }


@pytest.fixture
def release_root(tmp_path: Path) -> Path:
    """A synthetic bench root holding both fixed sets and their release lanes."""
    root = tmp_path / "repo"
    sets = root / "results" / "sets"
    sets.mkdir(parents=True)

    convert_rows = [
        {
            "state": "clean",
            "stem": CONVERT_A,
            "docx": f"corpus/word/clean/docx/{CONVERT_A}.docx",
            "word_pdf": f"corpus/word/clean/pdf/{CONVERT_A}.pdf",
            "docx_sha256": "0" * 64,
            "word_pdf_sha256": "1" * 64,
            "source": "local",
            "pages": "3",
            "jubarte_score": "80",
        },
        {
            "state": "clean",
            "stem": CONVERT_B,
            "docx": f"corpus/word/clean/docx/{CONVERT_B}.docx",
            "word_pdf": f"corpus/word/clean/pdf/{CONVERT_B}.pdf",
            "docx_sha256": "2" * 64,
            "word_pdf_sha256": "3" * 64,
            "source": "local",
            "pages": "2",
            "jubarte_score": "70",
        },
    ]
    with (sets / "convert_860.csv").open("w", newline="", encoding="utf-8") as handle:
        handle.write(
            "state,stem,docx,word_pdf,docx_sha256,word_pdf_sha256,source,pages,jubarte_score\n"
        )
        for row in convert_rows:
            handle.write(",".join(str(row[key]) for key in row) + "\n")

    redline_rows = [
        {
            "key": REDLINE_A,
            "base": "corpus/word/clean/docx/alpha.docx",
            "base_sha256": "4" * 64,
            "next": "corpus/word/clean/docx/beta.docx",
            "next_sha256": "5" * 64,
            "docx": "corpus/word/tracking_without_comments/docx/alpha__vs__beta_redline_aaaaaaaa.docx",
            "docx_sha256": "6" * 64,
            "pdf": "corpus/word/tracking_without_comments/pdf/alpha__vs__beta_redline_aaaaaaaa.pdf",
            "pdf_sha256": "7" * 64,
            "state": "tracking_without_comments",
            "id": "aaaaaaaa",
            "sets": "synthetic",
            "oracle": "corpus",
            "oracle_pdf": "corpus/word/tracking_without_comments/pdf/alpha__vs__beta_redline_aaaaaaaa.pdf",
            "oracle_pdf_sha256": "7" * 64,
        },
        {
            "key": REDLINE_B,
            "base": "corpus/word/clean/docx/alpha.docx",
            "base_sha256": "4" * 64,
            "next": "corpus/word/clean/docx/gamma.docx",
            "next_sha256": "8" * 64,
            "docx": "corpus/word/tracking_without_comments/docx/alpha__vs__gamma_redline_bbbbbbbb.docx",
            "docx_sha256": "9" * 64,
            "pdf": "corpus/word/tracking_without_comments/pdf/alpha__vs__gamma_redline_bbbbbbbb.pdf",
            "pdf_sha256": "a" * 64,
            "state": "tracking_without_comments",
            "id": "bbbbbbbb",
            "sets": "synthetic",
            "oracle": "corpus",
            "oracle_pdf": "corpus/word/tracking_without_comments/pdf/alpha__vs__gamma_redline_bbbbbbbb.pdf",
            "oracle_pdf_sha256": "a" * 64,
        },
    ]
    columns = list(redline_rows[0])
    with (sets / "redline_600.csv").open("w", newline="", encoding="utf-8") as handle:
        handle.write(",".join(columns) + "\n")
        for row in redline_rows:
            handle.write(",".join(str(row[key]) for key in columns) + "\n")

    # The release's own two lanes.
    _json(
        root / "results" / "release_1.2.3_evidence" / "docx_to_pdf_jubarte_1.2.3_sample.json",
        {
            "generated_at": "2026-11-03T00:00:00+00:00",
            "n": 2,
            "oracle": "microsoft_word",
            "scorer_backend": "numpy",
            "stems": [CONVERT_A, CONVERT_B],
            "tools": {
                "jubarte": {
                    "tool": "jubarte",
                    "version": "jubarte 1.2.3",
                    "n_scored": 2,
                    "per_doc": {CONVERT_A: 80.0, CONVERT_B: 70.0},
                    "convert_seconds": {CONVERT_A: 0.5, CONVERT_B: 0.6},
                    "generate_failures": [],
                    "failures": 0,
                }
            },
            "track": "corpus/word:list",
            "warnings": [],
        },
    )
    _json(
        root / "results" / "redlines_0929_full" / "scores_jubarte-1.2.3_sample_redline_1.2.3.json",
        _redline_scores(
            {
                REDLINE_A: {
                    "average_score": 90.0,
                    "overall_score": 90.0,
                    "ink_jaccard": 0.9,
                    "text_boundary": 0.8,
                    "ssim": 0.7,
                    "page_count": 3,
                    "page_count_oracle": 3,
                    "page_count_candidate": 3,
                    "max_break_drift": 2,
                    "pages": [
                        {"page": 1, "score": 88.0},
                        {"page": 3, "score": 91.0},
                        {"page": 4, "score": 99.0},
                    ],
                },
                REDLINE_B: {
                    "average_score": 80.0,
                    "overall_score": 80.0,
                    "ink_jaccard": 0.75,
                    "text_boundary": 1.0,
                    "page_count": 2,
                    "page_count_oracle": 2,
                    "page_count_candidate": 2,
                    "max_break_drift": 0,
                },
            }
        ),
    )

    # The newest vendor lanes.  The second fixed-set row was never run by
    # either vendor: that lane must be absent for that case, never score zero.
    _json(
        root / "results" / "docx_to_pdf_docxodus_15.0.0_set-convert_860.json",
        _conversion_report(
            [CONVERT_A, CONVERT_B],
            {CONVERT_A: 60.0},
            per_page={CONVERT_A: [55.0, None, 57.0]},
        ),
    )
    _json(
        root / "results" / "docx_to_pdf_docxide_0.18.4_set-convert_860.json",
        {
            **_conversion_report([CONVERT_A, CONVERT_B], {CONVERT_A: 65.0}),
            "tools": {
                "docxide-pdf": {
                    "tool": "docxide-pdf",
                    "version": "docxide-pdf v0.18.4",
                    "n_scored": 1,
                    "per_doc": {CONVERT_A: 65.0},
                    "per_page": {CONVERT_A: [65.0, 64.0]},
                    "convert_seconds": {CONVERT_A: 0.2},
                    "generate_failures": [],
                    "failures": 0,
                }
            },
        },
    )
    _json(
        root / "results" / "redlines_0929_full" / "scores_docxodus-15.0.0_set-redline_600.json",
        _redline_scores(
            {
                REDLINE_A: {
                    "average_score": 70.0,
                    "overall_score": 70.0,
                    "ink_jaccard": 0.7,
                    "text_boundary": 0.6,
                    "page_count": 3,
                    "page_count_oracle": 3,
                    "page_count_candidate": 3,
                    "max_break_drift": -1,
                    "per_page": [70.0, 69.0],
                }
            }
        ),
    )

    # The local PDFs the page renderer consumes.
    _pdf(root / "corpus" / "word" / "clean" / "pdf" / f"{CONVERT_A}.pdf", pages=3)
    _pdf(root / "corpus" / "word" / "clean" / "pdf" / f"{CONVERT_B}.pdf", pages=2)
    _pdf(
        root / "corpus" / "word" / "tracking_without_comments" / "pdf" / f"{REDLINE_A}.pdf",
        pages=3,
    )
    _pdf(
        root / "corpus" / "word" / "tracking_without_comments" / "pdf" / f"{REDLINE_B}.pdf",
        pages=2,
    )
    _pdf(
        root
        / "results"
        / "release_1.2.3_evidence"
        / "convert_work"
        / "jubarte"
        / "candidate"
        / f"{CONVERT_A}.pdf",
        pages=3,
    )
    _pdf(
        root
        / "results"
        / "release_1.2.3_evidence"
        / "convert_work"
        / "jubarte"
        / "candidate"
        / f"{CONVERT_B}.pdf",
        pages=2,
    )
    _pdf(
        root / "results" / "docxodus_15.0.0_work" / "docxodus" / "candidate" / f"{CONVERT_A}.pdf",
        pages=4,
    )
    _pdf(
        root / "results" / "docxide_0.18.4_work" / "docxide-pdf" / "candidate" / f"{CONVERT_A}.pdf",
        pages=3,
    )
    _pdf(
        root
        / "results"
        / "redlines_0929_full"
        / "jubarte-1.2.3"
        / "pdf_by_word"
        / f"{REDLINE_A}_jubarte-1.2.3_byword.pdf",
        pages=3,
    )
    _pdf(
        root
        / "results"
        / "redlines_0929_full"
        / "docxodus-15.0.0"
        / "pdf_by_word"
        / f"{REDLINE_A}_docxodus_byword.pdf",
        pages=3,
    )
    # the redlines themselves: the lane's docx/ folder, which the publisher stages too
    docx_dir = root / "results" / "redlines_0929_full" / "jubarte-1.2.3" / "docx"
    docx_dir.mkdir(parents=True, exist_ok=True)
    (docx_dir / f"{REDLINE_A}_jubarte-1.2.3.docx").write_bytes(b"redline")
    return root


def test_release_shards_validate_against_the_bumped_contract(release_root: Path) -> None:
    assert hasattr(cases_emit, "emit_release"), "release-set emitter is missing"
    index, shards = cases_emit.emit_release(release_root, "1.2.3", files_base=FILES_BASE)

    assert index.files_base == FILES_BASE
    assert len(shards) == 2
    assert [(shard.kind, shard.group) for shard in shards] == [
        ("conversion", "cases/release-1.2.3"),
        ("redline", "redlines/release-1.2.3"),
    ]
    assert [group.path for group in index.groups] == [
        shard_path("conversion", "cases/release-1.2.3"),
        shard_path("redline", "redlines/release-1.2.3"),
    ]
    validate_bundle(index, shards)
    for shard in shards:
        index.validate_shard(shard)
        assert dumps_compact(CaseShard.model_validate_json(dumps_compact(shard))) == dumps_compact(
            shard
        )


def test_a_lane_that_did_not_run_is_absent_not_zero(release_root: Path) -> None:
    _index, shards = cases_emit.emit_release(release_root, "1.2.3", files_base=FILES_BASE)
    by_key = {(shard.kind, case.case): case for shard in shards for case in shard.cases}

    conversion_b = by_key[("conversion", CONVERT_B)]
    assert "docxodus" not in conversion_b.scores
    assert "docxodus" not in conversion_b.pages
    assert "docxodus" not in conversion_b.versions
    assert "docxodus" not in conversion_b.files

    redline_b = by_key[("redline", REDLINE_B)]
    assert "docxodus" not in redline_b.scores
    assert "docxodus" not in redline_b.pages
    assert "docxodus" not in redline_b.versions


def test_page_scores_are_real_values_null_for_unscored_and_bounded(release_root: Path) -> None:
    _index, shards = cases_emit.emit_release(release_root, "1.2.3", files_base=FILES_BASE)
    by_key = {(shard.kind, case.case): case for shard in shards for case in shard.cases}

    conversion_a = by_key[("conversion", CONVERT_A)]
    assert conversion_a.page_scores["docxodus"] == [55.0, None, 57.0]
    assert "jubarte-1.2.3" not in conversion_a.page_scores

    redline_a = by_key[("redline", REDLINE_A)]
    assert redline_a.page_scores["jubarte-1.2.3"] == [88.0, None, 91.0]
    assert all(
        len(values) <= len(case.shown or [])
        for case in (conversion_a, redline_a)
        for values in case.page_scores.values()
    )


def test_a_per_page_list_is_sliced_to_the_shown_pages_and_null_where_absent(
    release_root: Path,
) -> None:
    """#144: the lane's per_page list becomes the case's page_scores.

    A page the lane never scored has no value: it is null in the shard, never
    a zero and never a value borrowed from another page.
    """
    _index, shards = cases_emit.emit_release(release_root, "1.2.3", files_base=FILES_BASE)
    by_key = {(shard.kind, case.case): case for shard in shards for case in shard.cases}

    conversion_a = by_key[("conversion", CONVERT_A)]
    assert conversion_a.shown == [1, 2, 3]
    # Two page scores for three shown pages: the third is null, not zero.
    assert conversion_a.page_scores["docxide-pdf"] == [65.0, 64.0, None]

    redline_a = by_key[("redline", REDLINE_A)]
    assert redline_a.shown == [1, 2, 3]
    assert redline_a.page_scores["docxodus"] == [70.0, 69.0, None]


def test_files_use_the_real_hub_layout_and_the_pinned_files_base(release_root: Path) -> None:
    index, shards = cases_emit.emit_release(release_root, "1.2.3", files_base=FILES_BASE)
    conversion = next(shard for shard in shards if shard.kind == "conversion").cases[0]

    assert conversion.files["docxodus"] == (
        f"~/outputs/convert_860/docxodus_15.0.0/pdf/{CONVERT_A}.pdf"
    )
    assert conversion.files["jubarte-1.2.3"] == (
        f"~/outputs/convert_860/jubarte_1.2.3/pdf/{CONVERT_A}.pdf"
    )
    assert conversion.files["docxide-pdf"] == (
        f"~/outputs/convert_860/docxide-pdf_0.18.4/pdf/{CONVERT_A}.pdf"
    )
    assert conversion.page_counts["docxodus"] == 4
    assert len(conversion.pages["docxodus"]) == len(conversion.shown or []) == 3
    assert index.files_base == FILES_BASE


def test_the_jubarte_lane_links_the_files_the_publisher_uploads(
    release_root: Path, tmp_path: Path
) -> None:
    """The shard's file links are the paths the publish stage uploads (#143).

    A link the publisher never uploads is a link that 404s; a file the
    publisher uploads that no case links is a file nobody can reach.
    """
    _index, shards = cases_emit.emit_release(release_root, "1.2.3", files_base=FILES_BASE)
    ev = release_root / "results" / "release_1.2.3_evidence"
    staging = tmp_path / "staging"

    convert_root = staging / "convert_860"
    hub_outputs.stage_convert_lane(
        convert_root,
        pdf_dir=ev / "convert_work" / "jubarte" / "candidate",
        report=ev / "docx_to_pdf_jubarte_1.2.3_sample.json",
    )
    redline_root = staging / "redlines"
    hub_outputs.stage_redline_lane(
        redline_root,
        lane="jubarte-1.2.3",
        lane_dir=release_root / "results" / "redlines_0929_full" / "jubarte-1.2.3",
    )

    planned_convert = {
        f"{hub_outputs.CONVERT_PREFIX}/jubarte_1.2.3/{path}"
        for path in hub_outputs.convert_case_files(convert_root)
    }
    planned_redline = {
        f"{hub_outputs.REDLINE_PREFIX}/{path}"
        for path in hub_outputs.redline_case_files(redline_root)
    }
    linked_convert = {
        case.files["jubarte-1.2.3"]
        for shard in shards
        if shard.kind == "conversion"
        for case in shard.cases
        if "jubarte-1.2.3" in case.files
    }
    linked_redline = {
        case.files["jubarte-1.2.3"]
        for shard in shards
        if shard.kind == "redline"
        for case in shard.cases
        if "jubarte-1.2.3" in case.files
    }

    assert {path.removeprefix("~/") for path in linked_convert} == planned_convert
    assert {path.removeprefix("~/") for path in linked_redline} == planned_redline
    assert planned_convert and planned_redline


def test_the_release_views_pin_the_files_base_to_the_recorded_revision(
    release_root: Path,
) -> None:
    """The links resolve against the revision the release's outputs landed on."""
    revision = "c0ffee" * 5
    hub_outputs.write_evidence(
        release_root, "1.2.3", {"revision": revision, "paths": [], "verified": True}
    )
    empty = ledger_build.Bundle(
        results_md="",
        detailed_md="",
        readme_vendor_table="",
        scores_json="",
    )
    bundle = ledger_build.add_release_views(release_root, empty, release_version="1.2.3")
    index = CasesIndex.model_validate_json(bundle.release_cases["cases/index.json"])
    assert index.files_base == (
        f"https://huggingface.co/datasets/arthrod/neurotic_docx_bench/resolve/{revision}/"
    )
    assert "/main/" not in index.files_base


def test_without_a_pinned_revision_the_release_views_refuse(release_root: Path) -> None:
    empty = ledger_build.Bundle(
        results_md="",
        detailed_md="",
        readme_vendor_table="",
        scores_json="",
    )
    with pytest.raises(hub_outputs.PinnedRevisionMissing):
        ledger_build.add_release_views(release_root, empty, release_version="1.2.3")


def test_the_release_views_say_which_revision_is_missing(
    release_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    said: list[str] = []
    assert (
        ledger_build.run_release_views(release_root, release_version="1.2.3", echo=said.append) == 1
    )
    assert any("pinned" in line for line in said), said
    assert not any("main" in line for line in said), said


def test_release_texts_leave_empty_plan7_fields_out(
    release_root: Path,
) -> None:
    index, shards = cases_emit.emit_release(release_root, "1.2.3", files_base=FILES_BASE)
    generic = index.model_copy(update={"files_base": None})
    texts = cases_emit.release_texts(generic, shards)
    assert '"files_base"' not in texts["cases/index.json"]
    for text in texts.values():
        assert '"page_scores":{}' not in text
        assert '"files":{}' not in text
        assert '"pdfs":{}' not in text  # #149: no pages.pdf links are emitted


def test_release_views_can_emit_and_validate_the_versioned_shards(
    release_root: Path,
) -> None:
    empty = ledger_build.Bundle(
        results_md="",
        detailed_md="",
        readme_vendor_table="",
        scores_json="",
    )
    bundle = ledger_build.add_release_views(
        release_root,
        empty,
        release_version="1.2.3",
        files_base=FILES_BASE,
    )
    assert "cases/index.json" in bundle.release_cases
    index = CasesIndex.model_validate_json(bundle.release_cases["cases/index.json"])
    assert index.files_base == FILES_BASE
    for group in index.groups:
        shard = CaseShard.model_validate_json(bundle.release_cases[group.path])
        index.validate_shard(shard)


def test_release_pages_stages_every_lane_and_plans_exactly_the_shard_assets(
    release_root: Path, tmp_path: Path
) -> None:
    spec = importlib.util.find_spec("neurotic_docx_bench.release_pages")
    assert spec is not None, "release page staging module is missing"
    release_pages = importlib.import_module("neurotic_docx_bench.release_pages")

    out = tmp_path / "out" / "release-pages" / "1.2.3"
    report = release_pages.stage_release_pages(
        release_root,
        "1.2.3",
        out=out,
        kinds=("convert",),
        limit=2,
        jobs=1,
    )

    index, shards = cases_emit.emit_release(
        release_root, "1.2.3", files_base=FILES_BASE, kinds=("convert",), limit=2
    )
    expected = {
        path
        for shard in shards
        for case in shard.cases
        for pages in case.pages.values()
        for path in pages
        if path is not None
    }
    assert set(report.plan) == expected
    assert expected
    for entry in report.plan.values():
        local = Path(entry["path"])
        assert local.is_file()
        assert local.name.startswith("page_") and local.name.endswith(".webp")
        assert entry["bytes"] == local.stat().st_size
        assert entry["sha256"] == hashlib.sha256(local.read_bytes()).hexdigest()
        assert local.is_relative_to(out)
        assert local.parent.name in {
            "docxodus",
            "docxide-pdf",
            "jubarte-1.2.3",
            "reference",
        }
    assert (out / "r2-plan.json").is_file()
    assert json.loads((out / "r2-plan.json").read_text()) == report.plan
    assert not list(out.rglob("pages.pdf")), "#149: staging writes no pages.pdf"
    assert index.groups  # the emitter and the renderer use the same release shape


def test_plain_cli_launches_the_reviewed_contract_overlay(
    release_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    from typer.testing import CliRunner

    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0)

    monkeypatch.setitem(sys.modules, "bench_ops", None)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    result = CliRunner().invoke(
        cli.app,
        [
            "release-pages",
            "1.2.3",
            "--root",
            str(release_root),
            "--out",
            str(tmp_path / "plain-cli"),
            "--kind",
            "convert",
        ],
    )
    assert result.exit_code == 0, result.output
    command = captured["command"]
    assert isinstance(command, list)
    assert "6478817465f67726c1450dbeaf090a9fa7ca44b2" in " ".join(command)
    assert "neurotic_docx_bench.release_pages_cli" in command


def test_release_pages_cli_stages_the_same_assets(release_root: Path, tmp_path: Path) -> None:
    from typer.testing import CliRunner

    out = tmp_path / "cli-pages"
    result = CliRunner().invoke(
        cli.app,
        [
            "release-pages",
            "1.2.3",
            "--root",
            str(release_root),
            "--out",
            str(out),
            "--kind",
            "convert",
            "--limit",
            "2",
            "--jobs",
            "1",
        ],
    )
    assert result.exit_code == 0, result.output
    assert (out / "r2-plan.json").is_file()
    assert "per-page scores" in result.output


#: The case fields the viewer never reads; the release text drops them (#162).
UNREAD_CASE_FIELDS = ("metric_diagnostics", "stem", "lang", "type", "set", "sets", "state", "pair")


def test_release_texts_drop_the_case_fields_the_viewer_never_reads(
    release_root: Path,
) -> None:
    index, shards = cases_emit.emit_release(release_root, "1.2.3", files_base=FILES_BASE)
    filled = [
        shard.model_copy(
            update={
                "cases": [
                    case.model_copy(
                        update={
                            "metric_diagnostics": {"jubarte": {"ink_jaccard": 0.5}},
                            "stem": "s",
                            "lang": "en",
                            "type": "t",
                            "set": "v1",
                            "sets": ["v1"],
                            "state": "clean",
                            "pair": "a__b",
                        }
                    )
                    for case in shard.cases
                ]
            }
        )
        for shard in shards
    ]
    texts = cases_emit.release_texts(index, filled)
    plain = cases_emit.release_texts(index, shards)
    assert texts.keys() == plain.keys()
    for ref in index.groups:
        data = json.loads(texts[ref.path])
        for case in data["cases"]:
            assert not set(UNREAD_CASE_FIELDS) & case.keys(), case.keys()
        # Everything else is what the unfilled shard wrote, minus the same fields.
        expected = json.loads(plain[ref.path])
        for case in expected["cases"]:
            for field in UNREAD_CASE_FIELDS:
                case.pop(field, None)
        assert data == expected
        index.validate_shard(CaseShard.model_validate_json(texts[ref.path]))
    # The source models keep their fields.
    assert filled[0].cases[0].stem == "s"


def _no_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    """The release fixture has no stores; these tests are about the case bundle."""
    empty = ledger_build.Bundle(results_md="", detailed_md="", readme_vendor_table="", scores_json="")
    monkeypatch.setattr(ledger_build, "build", lambda root, now=None: empty)


def test_check_without_a_version_reads_the_release_on_disk(
    release_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#175: `bench publish`'s before-check runs `release_views.py --check` with no
    version. After a versioned release is written, that check must check the same
    release (the version its index names), not rebuild the legacy bundle and call
    every shard stale."""
    _no_pages(monkeypatch)
    (release_root / "README.md").write_text(
        f"{ledger_build.VENDORS_START}\n{ledger_build.VENDORS_END}\n", encoding="utf-8"
    )
    hub_outputs.write_evidence(
        release_root, "1.2.3", {"revision": "c0ffee" * 5, "paths": [], "verified": True}
    )
    said: list[str] = []
    assert ledger_build.run_release_views(release_root, release_version="1.2.3", echo=said.append) == 0, said
    checked: list[str] = []
    assert ledger_build.run_release_views(release_root, check=True, echo=checked.append) == 0, checked
    assert "published views are current" in checked
    assert any("release 1.2.3" in line and "index.json" in line for line in checked), checked


def test_an_index_naming_two_release_versions_is_refused(
    release_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The version is inferred only when every release group names one version."""
    _no_pages(monkeypatch)
    index = release_root / "results/release/cases/index.json"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(json.dumps({"groups": [
        {"group": "cases/release-1.2.3", "kind": "conversion", "path": "a.json", "count": 1},
        {"group": "redlines/release-1.2.4", "kind": "redline", "path": "b.json", "count": 1},
    ]}))
    said: list[str] = []
    assert ledger_build.run_release_views(release_root, check=True, echo=said.append) == 1
    assert any("1.2.3" in line and "1.2.4" in line for line in said), said


def test_a_write_without_a_version_keeps_the_legacy_flow(
    release_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Codex on #176: only the check infers the release on disk; a write without
    --release-version is the legacy emitter, as the CLI documents, so a versioned
    bundle can still be replaced by the historical one."""
    _no_pages(monkeypatch)
    index = release_root / "results/release/cases/index.json"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(json.dumps({"groups": [
        {"group": "cases/release-1.2.3", "kind": "conversion", "path": "a.json", "count": 1},
    ]}))
    said: list[str] = []
    ledger_build.run_release_views(release_root, echo=said.append)
    assert not any(line.startswith("release 1.2.3") for line in said), said


def test_a_vendor_lane_links_its_own_trimmed_word_pdf_not_a_prefix_neighbour(
    release_root: Path,
) -> None:
    """#177: the refresh lanes' Word manifests name `<key>_<tool>-<version>.docx`,
    trimmed on disk; a lookup of `<key>_<tool>.docx` missed and a 35-character
    prefix glob took another pair's PDF sorted first. The lane must link its own."""
    folder = release_root / "results" / "redlines_0929_full" / "docxodus-15.0.0" / "pdf_by_word"
    (folder / f"{REDLINE_A}_docxodus_byword.pdf").unlink()
    trimmed = f"{REDLINE_A[:20]}_a1b2c3d4"
    _pdf(folder / f"{trimmed}_byword.pdf", pages=3)
    _pdf(folder / f"{REDLINE_A[:35]}0_decoy_byword.pdf", pages=1)  # another pair, sorted first
    (folder / "manifest.jsonl").write_text(
        json.dumps(
            {
                "original_filename": f"{REDLINE_A}_docxodus-15.0.0.docx",
                "converted_filename": f"{trimmed}.docx",
                "status": "renamed",
                "kind": "rename",
            }
        )
        + "\n"
        + json.dumps(
            {
                "original_filename": f"{trimmed}.docx",
                "converted_filename": f"{trimmed}_byword.pdf",
                "path_out": f"results/redlines_0929_full/docxodus-15.0.0/pdf_by_word/{trimmed}_byword.pdf",
                "status": "ok",
                "kind": "pdf",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _, shards = cases_emit.emit_release(release_root, "1.2.3", files_base=FILES_BASE)
    redline = next(shard for shard in shards if shard.kind == "redline").cases[0]
    assert redline.files["docxodus"].endswith(f"/{trimmed}_byword.pdf"), redline.files


def test_an_ambiguous_prefix_never_picks_a_pdf(release_root: Path) -> None:
    """#177: with no manifest entry and two PDFs sharing the key's prefix, no file is
    linked — a wrong pair's redline is worse than none."""
    folder = release_root / "results" / "redlines_0929_full" / "docxodus-15.0.0" / "pdf_by_word"
    (folder / f"{REDLINE_A}_docxodus_byword.pdf").unlink()
    _pdf(folder / f"{REDLINE_A[:35]}0_one_byword.pdf", pages=3)
    _pdf(folder / f"{REDLINE_A[:35]}1_two_byword.pdf", pages=3)
    _, shards = cases_emit.emit_release(release_root, "1.2.3", files_base=FILES_BASE)
    redline = next(shard for shard in shards if shard.kind == "redline").cases[0]
    assert "docxodus" not in redline.files, redline.files


def test_a_lone_prefix_neighbour_is_never_linked(release_root: Path) -> None:
    """Adversarial review of #178: one PDF sharing the key's first 35 characters
    may still be another pair's; with no manifest entry and no exact name, nothing
    is linked."""
    folder = release_root / "results" / "redlines_0929_full" / "docxodus-15.0.0" / "pdf_by_word"
    (folder / f"{REDLINE_A}_docxodus_byword.pdf").unlink()
    _pdf(folder / f"{REDLINE_A[:35]}_other_pair_byword.pdf", pages=3)
    _, shards = cases_emit.emit_release(release_root, "1.2.3", files_base=FILES_BASE)
    redline = next(shard for shard in shards if shard.kind == "redline").cases[0]
    assert "docxodus" not in redline.files, redline.files


def test_a_sibling_comparison_of_the_same_pair_is_linked(release_root: Path) -> None:
    """Real 0.17.0 data: Word compared one base/next pair twice (two redline ids).
    The set keys the case by one id; the vendor lane generated the pair once, under
    the other. Same base and next bytes (the ids are content hashes), so that
    redline is this case's, found through the full pair, never a prefix."""
    folder = release_root / "results" / "redlines_0929_full" / "docxodus-15.0.0" / "pdf_by_word"
    (folder / f"{REDLINE_A}_docxodus_byword.pdf").unlink()
    sibling = REDLINE_A.replace("aaaaaaaa", "bbbbbbbb")
    trimmed = f"{sibling[:20]}_c0ffee00"
    _pdf(folder / f"{trimmed}_byword.pdf", pages=3)
    (folder / "manifest.jsonl").write_text(
        json.dumps(
            {
                "original_filename": f"{sibling}_docxodus-15.0.0.docx",
                "converted_filename": f"{trimmed}.docx",
                "status": "renamed",
                "kind": "rename",
            }
        )
        + "\n"
        + json.dumps(
            {
                "original_filename": f"{trimmed}.docx",
                "converted_filename": f"{trimmed}_byword.pdf",
                "path_out": "nowhere",
                "status": "ok",
                "kind": "pdf",
            }
        )
        + "\n"
    )
    _, shards = cases_emit.emit_release(release_root, "1.2.3", files_base=FILES_BASE)
    redline = next(shard for shard in shards if shard.kind == "redline").cases[0]
    assert redline.files["docxodus"].endswith(f"/{trimmed}_byword.pdf"), redline.files


def test_two_sibling_comparisons_with_redlines_are_ambiguous(release_root: Path) -> None:
    """When the lane holds redlines under two other ids of the pair, neither is chosen."""
    folder = release_root / "results" / "redlines_0929_full" / "docxodus-15.0.0" / "pdf_by_word"
    (folder / f"{REDLINE_A}_docxodus_byword.pdf").unlink()
    for other in ("bbbbbbbb", "cccccccc"):
        _pdf(folder / f"{REDLINE_A.replace('aaaaaaaa', other)}_docxodus-15.0.0_byword.pdf", pages=3)
    _, shards = cases_emit.emit_release(release_root, "1.2.3", files_base=FILES_BASE)
    redline = next(shard for shard in shards if shard.kind == "redline").cases[0]
    assert "docxodus" not in redline.files, redline.files
