"""scores.json: the same rows RESULTS.md renders, as JSON (#113).

Contract pinned here: ``bench report`` also writes ``results/scores.json`` built
from the SAME rows that render RESULTS.md, so the two can never disagree.
``generated`` is the date (YYYY-MM-DD) of the newest row used, never the wall
clock, so ``bench report --check`` stays stable across days.

Also pinned here (the 2026-11-02 adversarial review):

- every ``###`` section of RESULTS.md that has a score pipe table has a JSON
  table (the speed section is the documented exception),
- ``scores.TABLE_IDS`` (the producer-owned ids, in RESULTS.md order),
- the release-evidence sample tables come first and equal jubarte-app's own
  ``bench.*`` facts (single source: the engine's release_info, filed by ndb).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml
import pytest

from neurotic_docx_bench.ledger import build as bd
from neurotic_docx_bench.ledger import pins as tp
from neurotic_docx_bench.ledger import policy as pol
from neurotic_docx_bench.ledger import registry as reg
from neurotic_docx_bench.ledger import rows as rws
from neurotic_docx_bench.ledger import scores as sc
from neurotic_docx_bench.ledger import tables as tb
from neurotic_docx_bench.ledger.scores import render_scores

REPO_ROOT = Path(__file__).resolve().parents[1]

REPO_URL = "https://github.com/jandira-tech/neurotic_docx_bench"
VIEWER_URL = "https://jandira-tech.github.io/neurotic_docx_bench/"
# jubarte-app's live facts: the sample tables/headlines/home_groups/method in
# scores.json must equal the bench.* values the site holds (single source).
JUBARTE_APP_FACTS = Path(
    "/Users/arthrod/temp/T/1_jubarte-redlines/jubarte-app/data/facts.jsonl"
)

TOP_KEYS = {
    "version",
    "generated",
    "repo",
    "viewer",
    "provenance",
    "tables",
    "states",
    "headlines",
    "home_groups",
    "method",
}
ROW_KEYS = {"rank", "tool", "pin", "median", "mean", "docs", "failed", "note", "ours"}


# ---- synthetic rows, built the way the ledger models them ----------------------


def _row(
    display: str,
    *,
    tool_id: str | None = None,
    affiliated: bool = False,
    benchmark: str = "docx_to_pdf",
    docset: str = "dset1",
    itt_median: float = 80.0,
    itt_mean: float | None = None,
    scores: dict[str, float] | None = None,
    failed_docs: tuple[str, ...] = (),
    ts: str = "2026-09-02T00:00:00+00:00",
    version: str = "1.0",
    extra: dict[str, dict[str, float]] | None = None,
) -> rws.ResultRow:
    pool = scores if scores is not None else {f"doc{i}": itt_median for i in range(3)}
    return rws.ResultRow(
        source="converter",
        id_run=f"run-{display}",
        tool_id=tool_id or display.lower(),
        display=display,
        affiliated=affiliated,
        benchmark=benchmark,
        lens="pixel",
        pin=tp.ToolPin.parse(version),
        timestamp=datetime.fromisoformat(ts),
        docset_id=docset,
        corpus_revision=docset,
        renderer_id="oracle:microsoft_word",
        bench_version="0.8.0",
        scorer="v1",
        n_scored=len(pool),
        n_failed_docs=len(failed_docs),
        n_failure_events=len(failed_docs),
        itt_n=len(pool) + len(failed_docs),
        itt_mean=itt_mean if itt_mean is not None else itt_median,
        itt_median=itt_median,
        mean=itt_median,
        median=itt_median,
        exact_100=0,
        scores=pool,
        failed_docs=failed_docs,
        extra=extra or {},
    )


def _group(
    benchmark: str = "docx_to_pdf", docset: str = "dset1"
) -> pol.GroupKey:
    return pol.GroupKey(
        benchmark=benchmark,
        lens="pixel",
        docset=docset,
        renderer="oracle:microsoft_word",
        scorer="v1",
        bench="0.8",
    )


def _table(
    benchmark: str, group: pol.GroupKey | None, ranked: list[pol.RankedRow], *, n: int
) -> pol.HeadlineTable:
    return pol.HeadlineTable(
        benchmark=benchmark,
        group=group,
        expected_n=n,
        rows=ranked,
        calibration=[],
        excluded=[],
        not_applicable=[],
        history_groups=[],
    )


def _provenance() -> bd.Provenance:
    return bd.Provenance(
        bench_version="0.8.0",
        docsets=("dset1",),
        scorers=("v1",),
        renderers=("oracle:microsoft_word",),
    )


def _canonical(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


# ---- 1. shape, rows, tie rank, affiliation, determinism ------------------------


def test_render_scores_shape_rows_and_tie_rank() -> None:
    acme = _row("acme", itt_median=82.45, itt_mean=79.93, version="0.12.0@3c81203f1f66")
    bravo = _row(
        "bravo",
        affiliated=True,
        itt_median=79.75,
        itt_mean=76.24,
        version="jubarte 0.11.0",
        failed_docs=("doc9",),
        ts="2026-09-01T00:00:00+00:00",
    )
    tables = {
        # An empty table (no eligible rows) renders nothing in RESULTS.md compact
        # mode, so it must not appear in scores.json either.
        "script_redlines": _table("script_redlines", None, [], n=25),
        "docx_to_pdf": _table(
            "docx_to_pdf",
            _group(),
            [
                pol.RankedRow(row=acme, rank=1),
                pol.RankedRow(row=bravo, rank=2, tied_with_previous=True),
            ],
            n=25,
        ),
    }
    row_ci = {
        acme.key: (81.13, 83.23),
        bravo.key: (77.54, 81.89),
    }
    text = render_scores(
        tables,
        row_ci=row_ci,
        redline_runs=[],
        provenance=_provenance(),
        generated="2026-09-02",
        bench_version="0.8.0",
    )
    obj = json.loads(text)
    assert set(obj) == TOP_KEYS
    assert obj["version"] == "0.8.0"
    assert obj["generated"] == "2026-09-02"
    assert obj["repo"] == REPO_URL
    assert obj["viewer"] == VIEWER_URL
    assert obj["provenance"] == {
        "docsets": ["dset1"],
        "scorers": ["v1"],
        "renderers": ["oracle:microsoft_word"],
    }
    assert set(obj["provenance"]) == {"docsets", "scorers", "renderers"}
    assert obj["states"] == []
    assert obj["headlines"] == []
    assert obj["home_groups"] == []
    assert obj["method"] == []

    # One table: the empty benchmark is skipped, the rest in RESULTS.md order.
    assert [t["id"] for t in obj["tables"]] == ["docx_to_pdf"]
    table = obj["tables"][0]
    assert set(table) == {"id", "title", "meta", "desc", "rows"}
    assert table["title"] == sc.TABLE_TITLES["docx_to_pdf"] == (
        "Accepted and randomized redline DOCX to PDF vs Word export"
    )
    assert table["meta"] == (
        "Document set `dset1` (25 documents), renderer `oracle:microsoft_word`, "
        "scorer `v1`, bench `0.8`."
    )
    assert table["desc"] == sc.TABLE_DESCS["docx_to_pdf"]
    assert table["rows"] == [
        {
            "rank": "1",
            "tool": "acme",
            "pin": "0.12.0@3c81203f1f66",
            "median": 82.45,
            "mean": 79.93,
            "docs": 3,
            "failed": 0,
            "note": "[81.13, 83.23]",
            "ours": False,
        },
        {
            "rank": "2=",  # the tie rank renders exactly like the Rank cell
            "tool": "bravo",  # display WITHOUT the affiliated mark
            "pin": "jubarte 0.11.0",
            "median": 79.75,
            "mean": 76.24,
            "docs": 3,
            "failed": 1,
            "note": "[77.54, 81.89]",
            "ours": True,  # affiliation lives in the flag, never in the name
        },
    ]
    row = table["rows"][0]
    assert set(row) == ROW_KEYS
    assert isinstance(row["rank"], str)
    assert isinstance(row["tool"], str)
    assert isinstance(row["pin"], str)
    assert isinstance(row["median"], float) and not isinstance(row["median"], bool)
    assert isinstance(row["mean"], float) and not isinstance(row["mean"], bool)
    assert isinstance(row["docs"], int) and not isinstance(row["docs"], bool)
    assert isinstance(row["failed"], int) and not isinstance(row["failed"], bool)
    assert isinstance(row["note"], str)
    assert isinstance(row["ours"], bool)
    assert "†" not in table["rows"][1]["tool"]

    # Canonical JSON: sorted keys, 2-space indent, unescaped non-ASCII, one newline.
    assert text.endswith("\n") and not text.endswith("\n\n")
    assert text == _canonical(obj)
    # Deterministic: the same inputs render the same text.
    assert (
        render_scores(
            tables,
            row_ci=row_ci,
            redline_runs=[],
            provenance=_provenance(),
            generated="2026-09-02",
            bench_version="0.8.0",
        )
        == text
    )


def test_render_scores_docxide_note_carries_every_extra_metric() -> None:
    row = _row(
        "jubarte",
        affiliated=True,
        benchmark="docxide_metrics",
        itt_median=70.68,
        itt_mean=66.84,
        version="jubarte 0.17.0+c607894",
        extra={
            "text_boundary": {"mean": 99.9, "median": 100.0},
            "ssim": {"mean": 61.4, "median": 61.5},
        },
    )
    tables = {
        "docxide_metrics": _table(
            "docxide_metrics",
            _group("docxide_metrics"),
            [pol.RankedRow(row=row, rank=1)],
            n=6427,
        )
    }
    text = render_scores(
        tables,
        row_ci={row.key: (70.20, 71.23)},
        redline_runs=[],
        provenance=_provenance(),
        generated="2026-11-01",
        bench_version="1.0.0",
    )
    obj = json.loads(text)
    (r,) = obj["tables"][0]["rows"]
    # Every extra-metric column RESULTS.md renders is folded into the note,
    # in the md's column order, spelled as the md spells the value.
    assert r["note"] == "[70.20, 71.23] · text 100.00 · ssim 61.50"
    assert r["median"] == 70.68
    assert r["mean"] == 66.84


def test_render_scores_states_from_corpus_keyed_pools() -> None:
    acme = _row(
        "acme",
        scores={
            "clean__d1": 90.0,
            "clean__d2": 92.0,
            "tracking_without_comments__d3": 70.0,
        },
        itt_median=90.0,
    )
    bravo = _row(
        "bravo",
        affiliated=True,
        scores={
            "clean__d1": 80.0,
            "clean__d2": 82.0,
            "tracking_without_comments__d3": 60.0,
        },
        itt_median=81.0,
    )
    tables = {
        "corpus/word:all": _table(
            "corpus/word:all",
            _group("corpus/word:all"),
            [pol.RankedRow(row=acme, rank=1), pol.RankedRow(row=bravo, rank=2)],
            n=3,
        )
    }
    obj = json.loads(
        render_scores(
            tables,
            row_ci={acme.key: (89.0, 91.0), bravo.key: (80.0, 82.0)},
            redline_runs=[],
            provenance=_provenance(),
            generated="2026-09-02",
            bench_version="0.8.0",
        )
    )
    # Per-state medians in the state_breakdown order, counts as strings, tools in
    # table order without the affiliated mark, affiliation in `ours`, and the
    # `table` the cell breaks down (the Table id) on every cell.
    assert obj["states"] == [
        {
            "name": "clean",
            "n": "2",
            "table": "corpus/word:all",
            "rows": [
                {"tool": "acme", "median": 91.0, "ours": False},
                {"tool": "bravo", "median": 81.0, "ours": True},
            ],
        },
        {
            "name": "tracking_without_comments",
            "n": "1",
            "table": "corpus/word:all",
            "rows": [
                {"tool": "acme", "median": 70.0, "ours": False},
                {"tool": "bravo", "median": 60.0, "ours": True},
            ],
        },
    ]
    assert set(obj["states"][0]) == {"name", "n", "rows", "table"}
    assert set(obj["states"][0]["rows"][0]) == {"tool", "median", "ours"}


def test_state_n_uses_a_thousands_separator() -> None:
    # The site's fact renders n as `(${s.n})` with a separator; the md header
    # shows the bare count. The contract takes the site's spelling.
    scores = {**{f"clean__d{i}": 90.0 for i in range(2480)}, "tracking_without_comments__d0": 91.0}
    row = _row("acme", scores=scores, itt_median=90.0)
    tables = {
        "corpus/word:all": _table(
            "corpus/word:all",
            _group("corpus/word:all"),
            [pol.RankedRow(row=row, rank=1)],
            n=len(scores),
        )
    }
    obj = json.loads(
        render_scores(
            tables,
            row_ci={row.key: (89.0, 91.0)},
            redline_runs=[],
            provenance=_provenance(),
            generated="2026-09-02",
            bench_version="0.8.0",
        )
    )
    assert [c["n"] for c in obj["states"]] == ["2,480", "1"]


# ---- redlines accept/reject table ----------------------------------------------

_ACCEPT_REJECT_LINE_KEYS = ("tool", "action", "pairs", "scored", "itt_mean", "itt_median")


def _action_line(tool: str, action: str, **kw: object) -> dict:
    line: dict = {
        "tool": tool,
        "action": action,
        "pairs": 400,
        "scored": 394,
        "itt_mean": 90.07,
        "itt_median": 99.87,
        "overall": {"exact_100": 166, "at_least_90": 299, "below_50": 16},
        "timestamp": "2026-09-29T00:00:00+00:00",
    }
    line.update(kw)
    return line


def test_render_scores_redlines_vs_word_table(tmp_path: Path) -> None:
    # The full-corpus redline table RESULTS.md renders as its own section:
    # "redlines vs Word's compare" (C1: it used to be dropped silently).
    run = tmp_path / "redlines_full"
    run.mkdir()
    (run / "scores.jsonl").write_text(
        json.dumps(
            _action_line(
                "jubarte-0.17.0",
                "redline",
                scored=3454,
                pairs=3502,
                itt_mean=84.68,
                itt_median=84.56,
                overall={"exact_100": 244, "at_least_90": 902, "below_50": 1355},
                ink_jaccard={"mean": 0.67},
                text_boundary={"mean": 0.77},
            )
        )
        + "\n"
        + json.dumps(
            _action_line("docxodus", "redline", scored=2612, pairs=3502,
                         itt_mean=81.75, itt_median=62.87)
        )
        + "\n"
    )
    (run / "versions.json").write_text(
        json.dumps({"jubarte-0.17.0": "jubarte 0.17.0", "docxodus": "Docxodus 12.6.5 (C#)"})
    )
    row = _row("acme", benchmark="docx_to_pdf")
    tables = {
        "docx_to_pdf": _table(
            "docx_to_pdf", _group(), [pol.RankedRow(row=row, rank=1)], n=25
        )
    }
    obj = json.loads(
        render_scores(
            tables,
            row_ci={row.key: (79.0, 81.0)},
            redline_runs=[run],
            provenance=_provenance(),
            generated="2026-09-29",
            bench_version="0.8.0",
        )
    )
    assert [t["id"] for t in obj["tables"]] == ["docx_to_pdf", "redlines_vs_word"]
    table = obj["tables"][-1]
    assert set(table) == {"id", "title", "meta", "desc", "rows"}
    assert table["title"] == "Redlines vs Word's compare"
    assert table["meta"] == "" and table["desc"] == sc.TABLE_DESCS["redlines_vs_word"]
    # Rows in the order redline_action_section ranks them (ITT median, then
    # mean), one rank per block; the pin is the run's version (no action suffix:
    # the md's redline table has no Action column); `ours` from the registry.
    assert table["rows"] == [
        {
            "rank": "1",
            "tool": "jubarte-0.17.0",
            "pin": "jubarte 0.17.0",
            "median": 84.56,
            "mean": 84.68,
            "docs": 3454,
            "failed": 48,
            "note": "= 100: 244 · ≥ 90: 902 · < 50: 1355 · ink 0.67 · text 0.77",
            "ours": False,  # a versioned lane is not a registry id
        },
        {
            "rank": "2",
            "tool": "docxodus",
            "pin": "Docxodus 12.6.5 (C#)",
            "median": 62.87,
            "mean": 81.75,
            "docs": 2612,
            "failed": 890,
            "note": "= 100: 166 · ≥ 90: 299 · < 50: 16 · ink n/a · text n/a",
            "ours": False,
        },
    ]


def test_render_scores_redlines_accept_reject_table(tmp_path: Path) -> None:
    empty_run = tmp_path / "redlines_redline_only"
    empty_run.mkdir()
    (empty_run / "scores.jsonl").write_text(
        json.dumps(_action_line("tA", "redline")) + "\n"  # its own table, tested above
    )
    run = tmp_path / "redlines_split"
    run.mkdir()
    (run / "scores.jsonl").write_text(
        # an older (tA, accept_all) line is superseded by the later one
        json.dumps(_action_line("tA", "accept_all", itt_median=1.0, itt_mean=1.0))
        + "\n"
        + json.dumps(
            _action_line(
                "tA",
                "accept_all",
                scored=394,
                itt_mean=90.07,
                itt_median=99.87,
                overall={"exact_100": 166, "at_least_90": 299, "below_50": 16},
            )
        )
        + "\n"
        + json.dumps(
            _action_line(
                "tB",
                "accept_all",
                scored=400,
                itt_mean=100.0,
                itt_median=100.0,
                overall={"exact_100": 400, "at_least_90": 400, "below_50": 0},
                ink_jaccard={"mean": 0.99},
                text_boundary={"mean": 0.98},
            )
        )
        + "\n"
        + json.dumps(
            _action_line(
                "tA",
                "reject_all",
                scored=385,
                itt_mean=85.38,
                itt_median=99.80,
                overall={"exact_100": 155, "at_least_90": 275, "below_50": 26},
            )
        )
        + "\n"
        + json.dumps(
            _action_line(
                "tB",
                "reject_all",
                scored=400,
                itt_mean=86.22,
                itt_median=99.85,
                overall={"exact_100": 186, "at_least_90": 260, "below_50": 35},
            )
        )
        + "\n"
    )
    (run / "versions.json").write_text(
        json.dumps({"tA": "tA 1.2", "tB": "tB 2.0"})
    )

    row = _row("acme", benchmark="docx_to_pdf")
    tables = {
        "docx_to_pdf": _table(
            "docx_to_pdf", _group(), [pol.RankedRow(row=row, rank=1)], n=25
        )
    }
    text = render_scores(
        tables,
        row_ci={row.key: (79.0, 81.0)},
        redline_runs=[empty_run, run],
        provenance=_provenance(),
        generated="2026-09-29",
        bench_version="0.8.0",
        affiliated_tools={"tB"},  # the registry's affiliated tool ids
    )
    obj = json.loads(text)
    assert [t["id"] for t in obj["tables"]] == [
        "docx_to_pdf",
        "redlines_vs_word",
        "redlines_accept_reject",
    ]
    table = obj["tables"][-1]
    assert set(table) == {"id", "title", "meta", "desc", "rows"}
    assert table["title"] == "Redlines accepted or rejected by Word"
    assert table["meta"] == "" and table["desc"] == sc.TABLE_DESCS["redlines_accept_reject"]
    # Ranked in the exact order redline_action_section renders: the accept_all
    # block then the reject_all block, each by ITT median/mean; the rank is the
    # position WITHIN its action block (the md ranks each block on its own and
    # has no rank column of its own). `ours` comes from the registry.
    assert table["rows"] == [
        {
            "rank": "1",
            "tool": "tB",
            "pin": "tB 2.0 · accept all",
            "median": 100.0,
            "mean": 100.0,
            "docs": 400,
            "failed": 0,
            "note": "= 100: 400 · ≥ 90: 400 · < 50: 0 · ink 0.99 · text 0.98",
            "ours": True,
        },
        {
            "rank": "2",
            "tool": "tA",
            "pin": "tA 1.2 · accept all",
            "median": 99.87,
            "mean": 90.07,
            "docs": 394,
            "failed": 6,  # pairs - scored
            "note": "= 100: 166 · ≥ 90: 299 · < 50: 16 · ink n/a · text n/a",
            "ours": False,
        },
        {
            "rank": "1",  # the reject_all block ranks from 1 again
            "tool": "tB",
            "pin": "tB 2.0 · reject all",
            "median": 99.85,
            "mean": 86.22,
            "docs": 400,
            "failed": 0,
            "note": "= 100: 186 · ≥ 90: 260 · < 50: 35 · ink n/a · text n/a",
            "ours": True,
        },
        {
            "rank": "2",
            "tool": "tA",
            "pin": "tA 1.2 · reject all",
            "median": 99.8,
            "mean": 85.38,
            "docs": 385,
            "failed": 15,
            "note": "= 100: 155 · ≥ 90: 275 · < 50: 26 · ink n/a · text n/a",
            "ours": False,
        },
    ]
    assert set(table["rows"][0]) == ROW_KEYS
    assert "≥" in text  # ensure_ascii=False keeps the note readable


def test_an_unmeasured_itt_stat_is_refused_not_zero(tmp_path: Path) -> None:
    # A redline line without an ITT stat renders "n/a" in the md; 0.0 is a real
    # score (a failed document), so writing 0.0 for an unmeasured stat would be a
    # fabricated number (M2). Both action tables refuse it, naming tool and table.
    for action, table_id in (("accept_all", "redlines_accept_reject"),
                             ("redline", "redlines_vs_word")):
        run = tmp_path / f"redlines_{action}"
        run.mkdir()
        (run / "scores.jsonl").write_text(
            json.dumps(_action_line("ghost", action, itt_median=None)) + "\n"
        )
        row = _row("acme", benchmark="docx_to_pdf")
        tables = {
            "docx_to_pdf": _table(
                "docx_to_pdf", _group(), [pol.RankedRow(row=row, rank=1)], n=25
            )
        }
        with pytest.raises(ValueError, match=rf"{table_id}.*ghost"):
            render_scores(
                tables,
                row_ci={row.key: (79.0, 81.0)},
                redline_runs=[run],
                provenance=_provenance(),
                generated="2026-09-29",
                bench_version="0.8.0",
            )


# ---- 2. `generated` is deterministic from the stores ---------------------------


def _line(
    vendor: str,
    median: float,
    ts: str,
    *,
    n: int = 25,
    version: str = "1.0",
    benchmark: str = "script_redlines",
    docset: str = "dset1",
) -> dict:
    scores = {f"doc{i}": median for i in range(n)}
    return {
        "id_run": f"run-{vendor}-{ts}",
        "vendor": vendor,
        "benchmark": benchmark,
        "n_docs": n,
        "overall_mean": median,
        "overall_median": median,
        "exact_100": 0,
        "scores": scores,
        "failures": [],
        "n_failures": 0,
        "itt_n_docs": n,
        "itt_mean": median,
        "itt_median": median,
        "tool_version": version,
        "timestamp": ts,
        "corpus_revision": "rev1",
        "scorer": "pagefair-v2",
        "holdout_mode": "excluded",
        "docset_id": docset,
        "renderer_id": "word-16.101.1",
        "environment_config": {"runs": [{"name": vendor, "render": "word"}]},
    }


def _gate_lines(*vendors: str) -> str:
    ts = "2026-08-31T00:00:00+00:00"
    lines = [
        _line(v, 90.0, ts, n=2, docset="gset1") for v in vendors
    ]
    lines.append(_line("null-baseline", 10.0, ts, n=2, docset="gset1"))
    return "".join(json.dumps(x) + "\n" for x in lines)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "results").mkdir()
    (tmp_path / "bench.registry.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "tools": [
                    {
                        "id": "a",
                        "vendor": "a",
                        "display": "acme",
                        "role": "generator",
                        "engine": "a",
                        "run_names": ["a"],
                        "bench_vendors": ["a"],
                        "speed_tools": ["a"],
                        "url": "https://example.com/a",
                    },
                    {
                        "id": "b",
                        "vendor": "b",
                        "display": "bravo",
                        "role": "generator",
                        "engine": "b",
                        "run_names": ["b"],
                        "bench_vendors": ["b"],
                        "affiliated": True,
                    },
                    {
                        "id": "null-baseline",
                        "vendor": "bench",
                        "display": "null baseline",
                        "role": "calibration",
                        "engine": "pipeline",
                        "run_names": ["null-baseline"],
                        "bench_vendors": ["null-baseline"],
                    },
                ],
            }
        )
    )
    (tmp_path / "results" / "bench.jsonl").write_text(
        json.dumps(_line("a", 80.0, "2026-09-01T00:00:00+00:00"))
        + "\n"
        + json.dumps(_line("b", 90.0, "2026-09-02T00:00:00+00:00"))
        + "\n"
        + _gate_lines("a", "b")
    )
    (tmp_path / "results" / "docsets.json").write_text(
        json.dumps(
            {
                "dset1": {"benchmark": "script_redlines", "n": 25},
                "gset1": {"benchmark": "script_redlines", "n": 2, "gate_of": "dset1"},
            }
        )
    )
    (tmp_path / "README.md").write_text(
        "# repo\n\nintro\n\n<!-- VENDORS-START -->\nold\n<!-- VENDORS-END -->\n\ntail\n"
    )
    return tmp_path


def test_generated_is_the_newest_rows_date_not_the_clock(repo: Path) -> None:
    far = datetime(2030, 1, 1, tzinfo=UTC)
    bundle = bd.build(repo, now=far)
    obj = json.loads(bundle.scores_json)
    assert obj["tables"], "the fixture must rank at least one table"
    # The newest row used is bravo's 2026-09-02 line, not the far wall clock.
    assert obj["generated"] == "2026-09-02"
    again = bd.build(repo, now=datetime(2026, 9, 27, tzinfo=UTC))
    assert again.scores_json == bundle.scores_json
    assert json.loads(again.scores_json)["generated"] == "2026-09-02"


def test_an_empty_store_is_refused_not_an_empty_generated(repo: Path) -> None:
    # m4: `generated` would be the empty string and the consumer would print
    # `bench · generated ` — an empty store refuses the build instead.
    (repo / "results" / "bench.jsonl").write_text("")
    with pytest.raises(ValueError, match="no rows"):
        bd.build(repo)


# ---- 2b. the release-evidence sample facts (single source) ----------------------


def test_table_ids_are_pinned() -> None:
    # M5: the consumer maps ndb table ids with a fixed table (an unknown id
    # fails there), so the producer pins the id set it can emit. The
    # release-evidence sample tables are evidence data, not producer ids.
    assert sc.TABLE_IDS == (
        "script_redlines",
        "accepted_changes",
        "roundtrip",
        "visual_rendering",
        "visual_redlines",
        "visual_accepted_changes",
        "docx_to_pdf",
        "docx_to_pdf_no_redline_docs",
        "corpus/word:all",
        "docxide_metrics",
        "corpus/word:le3pages",
        "docxide_metrics:le3pages",
        "redlines_vs_word",
        "redlines_accept_reject",
    )
    # every producer id is a benchmark id or one of the two redlines tables
    assert set(sc.TABLE_IDS) - set(tb.TITLES) == {
        "redlines_vs_word",
        "redlines_accept_reject",
    }


def _site_jsonl(path: Path) -> None:
    records = [
        {"id": "1", "ts": "2026-11-01T06:06:38.798Z", "key": "engine.version", "value": "0.17.0"},
        {"id": "2", "ts": "2026-11-01T06:06:38.798Z", "key": "bench.version",
         "value": "<the bench results version>", "pending": True},
        {"id": "3", "ts": "2026-11-01T06:06:38.798Z", "key": "bench.tables", "value": [
            {"id": "conversion-sample", "title": "DOCX → PDF vs Word's own PDF — 600-document sample",
             "meta": "600 docs · scorer torch-mps · 2026-11-01", "desc": "d",
             "rows": [
                 {"rank": "1", "tool": "jubarte †", "pin": "jubarte 0.17.0", "median": 81.0931,
                  "mean": 79.2446, "docs": 600, "failed": 0, "note": "[80.42, 81.7]", "ours": True},
                 {"rank": "2", "tool": "soffice", "pin": "LibreOffice 26.8.0.3", "median": 47.8822,
                  "mean": 54.6071, "docs": 600, "failed": 2, "note": "[47.53, 48.47]"},
             ]},
            {"id": "redlines-sample", "title": "Redlines vs Word's compare — 600-pair sample",
             "meta": "m", "desc": "d",
             "rows": [
                 {"rank": "1=", "tool": "jubarte-0.17.0 †", "pin": "jubarte 0.17.0", "median": 83.7553,
                  "mean": 74.3589, "docs": 600, "failed": 7,
                  "note": "= 100: 47 · ≥ 90: 109", "ours": True},
             ]},
        ]},
        {"id": "4", "ts": "2026-11-01T06:06:38.798Z", "key": "bench.headlines", "value": [
            {"label": "DOCX → PDF · median, 600-doc sample", "value": "81.09",
             "vs": "LibreOffice 26.8.0.3 47.88", "sub": "s"},
        ]},
        {"id": "5", "ts": "2026-11-01T06:06:38.798Z", "key": "bench.home_groups", "value": [
            {"title": "DOCX → PDF vs Word's own export", "meta": "m",
             "rows": [{"name": "jubarte 0.17.0 †", "v": 81.0931, "ours": True},
                      {"name": "LibreOffice 26.8.0.3", "v": 47.8822}],
             "note": None},
        ]},
        {"id": "6", "ts": "2026-11-01T06:06:38.798Z", "key": "bench.method", "value": [
            {"t": "Oracle: real Word", "d": "Every reference PDF is exported by Microsoft Word."},
        ]},
        {"id": "7", "ts": "2026-11-01T06:06:38.798Z", "key": "bench.states", "value": [
            {"name": "clean", "n": "150", "rows": [
                {"tool": "jubarte †", "median": 90.7695, "ours": True},
                {"tool": "soffice", "median": 68.8332},
            ]},
        ]},
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))


def test_read_site_facts_strips_the_dagger_and_sets_ours(tmp_path: Path) -> None:
    path = tmp_path / "website_data_0.17.0_11-01-26_01-06.jsonl"
    _site_jsonl(path)
    facts = sc.read_site_facts(path)
    # The dagger rule: jubarte's facts carry the affiliation mark in the name;
    # the contract carries it in `ours`. Every name loses the mark, every row
    # gets an explicit `ours`. Everything else is the record's value verbatim.
    conv, red = facts.tables
    assert conv["rows"][0]["tool"] == "jubarte" and conv["rows"][0]["ours"] is True
    assert conv["rows"][1] == {"rank": "2", "tool": "soffice", "pin": "LibreOffice 26.8.0.3",
                               "median": 47.8822, "mean": 54.6071, "docs": 600, "failed": 2,
                               "note": "[47.53, 48.47]", "ours": False}
    assert red["rows"][0]["tool"] == "jubarte-0.17.0"
    assert facts.states[0]["rows"][0]["tool"] == "jubarte"
    assert facts.states[0]["rows"][1]["ours"] is False
    assert facts.home_groups[0]["rows"][0]["name"] == "jubarte 0.17.0"
    assert facts.home_groups[0]["rows"][1]["ours"] is False
    assert facts.headlines and facts.method  # carried verbatim (no ours flag to move)
    assert "†" not in json.dumps(
        [facts.tables, facts.states, facts.home_groups], ensure_ascii=False
    )


def test_site_facts_refuse_a_file_without_the_bench_records(tmp_path: Path) -> None:
    path = tmp_path / "website_data_0.1.0_01-01-26_00-00.jsonl"
    path.write_text(json.dumps({"id": "1", "ts": "t", "key": "engine.version", "value": "0.1.0"}) + "\n")
    with pytest.raises(ValueError, match="bench.tables"):
        sc.read_site_facts(path)


def test_newest_evidence_is_newest_by_version_then_stamp(tmp_path: Path) -> None:
    def put(version: str, stamp: str) -> None:
        d = tmp_path / "results" / f"release_{version}_evidence" / "release_info"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"website_data_{version}_{stamp}.jsonl").write_text("")

    put("0.9.0", "12-31-26_23-59")
    put("0.16.0", "12-01-26_00-00")
    put("0.17.0", "11-01-26_01-05")
    put("0.17.0", "11-01-26_01-06")
    empty = tmp_path / "results" / "release_0.18.0_evidence" / "release_info"
    empty.mkdir(parents=True)
    found = sc.newest_evidence(tmp_path / "results")
    assert found is not None and found.name == "website_data_0.17.0_11-01-26_01-06.jsonl"
    (found).unlink()
    found = sc.newest_evidence(tmp_path / "results")
    assert found is not None and found.name == "website_data_0.17.0_11-01-26_01-05.jsonl"
    assert sc.newest_evidence(tmp_path / "nowhere") is None


def test_render_scores_carries_the_site_facts_first(tmp_path: Path) -> None:
    path = tmp_path / "website_data_0.17.0_11-01-26_01-06.jsonl"
    _site_jsonl(path)
    site = sc.read_site_facts(path)
    row = _row("acme", benchmark="docx_to_pdf")
    tables = {
        "docx_to_pdf": _table(
            "docx_to_pdf", _group(), [pol.RankedRow(row=row, rank=1)], n=25
        )
    }
    obj = json.loads(
        render_scores(
            tables,
            row_ci={row.key: (79.0, 81.0)},
            redline_runs=[],
            provenance=_provenance(),
            generated="2026-11-01",
            bench_version="1.0.0",
            site=site,
        )
    )
    # The sample tables come FIRST, in the file's order, values verbatim; then
    # the full-corpus tables, as now.
    assert [t["id"] for t in obj["tables"]] == [
        "conversion-sample",
        "redlines-sample",
        "docx_to_pdf",
    ]
    assert obj["tables"][0]["rows"][0] == site.tables[0]["rows"][0]
    assert obj["tables"][1]["title"] == "Redlines vs Word's compare — 600-pair sample"
    # headlines/home_groups/method are the file's records verbatim.
    assert obj["headlines"] == list(site.headlines)
    assert obj["home_groups"] == list(site.home_groups)
    assert obj["method"] == list(site.method)
    # The sample states lead, carrying the conversion sample table's id.
    assert obj["states"][0] == {
        "name": "clean",
        "n": "150",
        "table": "conversion-sample",
        "rows": site.states[0]["rows"],
    }
    # The full-corpus states follow, as before, with their own table id.
    corpus = _row(
        "acme",
        benchmark="corpus/word:all",
        scores={"clean__d1": 90.0},
        itt_median=90.0,
    )
    tables = {
        "corpus/word:all": _table(
            "corpus/word:all",
            _group("corpus/word:all"),
            [pol.RankedRow(row=corpus, rank=1)],
            n=1,
        )
    }
    obj = json.loads(
        render_scores(
            tables,
            row_ci={corpus.key: (89.0, 91.0)},
            redline_runs=[],
            provenance=_provenance(),
            generated="2026-11-01",
            bench_version="1.0.0",
            site=site,
        )
    )
    assert [c["table"] for c in obj["states"]] == ["conversion-sample", "corpus/word:all"]


# ---- 3. integration: the real stores of this worktree ---------------------------


# The md section heading each producer-owned table renders under (#133 kept
# them: scores.json titles are the human ones, the md keeps its own spelling).
MD_SECTION: dict[str, str] = {
    **tb.TITLES,
    sc.REDLINES_VS_WORD_ID: "redlines vs Word's compare",
    sc.REDLINES_TABLE_ID: "redlines accepted or rejected by Word",
}


def _sections(md: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    current: str | None = None
    for line in md.splitlines():
        if line.startswith("### "):
            current = line[4:].strip()
            out.setdefault(current, [])
        elif current is not None:
            out[current].append(line)
    return out


def _pipe_table(lines: list[str]) -> tuple[list[str], list[dict[str, str]]]:
    """The first pipe table in ``lines``: header and body rows keyed by column."""
    block: list[str] = []
    for ln in lines:
        if ln.startswith("|"):
            block.append(ln)
        elif block:
            break  # the table ended; a later one (the state breakdown) is separate
    assert block, "expected a pipe table"
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in block]
    header = cells[0]
    assert all(set(c) <= {"-", ":", " "} for c in cells[1]), "separator row"
    return header, [dict(zip(header, r, strict=True)) for r in cells[2:]]


def _md_tool(cell: str) -> str:
    cell = cell.strip()
    return cell[:-1].strip() if cell.endswith("†") else cell


def test_scores_json_matches_results_md_on_the_real_store() -> None:
    bundle = bd.build(REPO_ROOT)
    obj = json.loads(bundle.scores_json)
    assert set(obj) == TOP_KEYS
    assert obj["version"] == bundle.provenance.bench_version
    # The newest row in the stores (a converter line of 2026-11-03, the
    # convert_860 lane), never now().
    assert obj["generated"] == "2026-11-03"
    assert obj["repo"] == REPO_URL and obj["viewer"] == VIEWER_URL
    assert obj["provenance"] == {
        "docsets": list(bundle.provenance.docsets),
        "scorers": list(bundle.provenance.scorers),
        "renderers": list(bundle.provenance.renderers),
    }

    sections = _sections(bundle.results_md)
    ids = [t["id"] for t in obj["tables"]]
    # The release-evidence sample tables lead (the 0.17.0 release_info this
    # repo files under results/release_0.17.0_evidence/), then the fidelity
    # tables, then the two redlines tables in RESULTS.md section order.
    assert ids[:2] == ["conversion-sample", "redlines-sample"]
    assert ids[-2:] == ["redlines_vs_word", "redlines_accept_reject"]
    fidelity = [t for t in obj["tables"] if t["id"] in tb.TITLES]
    # The same headline tables RESULTS.md renders, in RESULTS.md order.
    assert [t["id"] for t in fidelity] == [
        g.benchmark for g in bundle.headline_groups
    ]
    # Every producer-owned id is pinned and in TABLE_IDS order.
    order = {tid: i for i, tid in enumerate(sc.TABLE_IDS)}
    producer_ids = [t["id"] for t in obj["tables"] if t["id"] in order]
    assert producer_ids == sorted(producer_ids, key=lambda x: order[x])

    expected_states: list[dict] = []
    for table in fidelity:
        lines = sections[MD_SECTION[table["id"]]]
        # The group line under the section heading is the table's meta.
        first = next(ln for ln in lines if ln.startswith("Document set `"))
        assert table["meta"] == first.split(". ", 1)[0] + "."
        assert table["desc"] == sc.TABLE_DESCS[table["id"]]
        header, body = _pipe_table(lines)
        assert len(body) == len(table["rows"]), table["id"]
        # every extra-metric column of the md is folded into the note
        extras = header[header.index("Perfect (100)") + 1 :]
        for row, md in zip(table["rows"], body, strict=True):
            tool = _md_tool(md["Tool"])
            note = md["95% CI"]
            for m in extras:
                note += f" · {m.split('_')[0]} {md[m]}"
            assert row == {
                "rank": md["Rank"],
                "tool": tool,
                "pin": md["Pin"],
                "median": float(md["ITT Median"]),
                "mean": float(md["ITT Mean"]),
                "docs": int(md["Docs"]),
                "failed": int(md["Failed"]),
                "note": note,
                "ours": md["Tool"].strip().endswith("†"),
            }, (table["id"], row["tool"])
        # The state breakdown that follows the table, as JSON: every cell
        # carries the table it breaks down and a thousands-separated n.
        if any(ln.startswith("By corpus state") for ln in lines):
            after = lines[lines.index(next(ln for ln in lines if ln.startswith("By corpus state"))) :]
            s_header, s_body = _pipe_table(after)
            for name, count in (h.rsplit(" (", 1) for h in s_header[1:]):
                n = f"{int(count.rstrip(')')):,}"
                expected_states.append(
                    {
                        "name": name,
                        "n": n,
                        "table": table["id"],
                        "rows": [
                            {
                                "tool": _md_tool(md["Tool"]),
                                "median": float(md[f"{name} ({count.rstrip(')')})"].split(" / ")[1]),
                                "ours": md["Tool"].strip().endswith("†"),
                            }
                            for md in s_body
                        ],
                    }
                )
    # The sample states lead (their equality with the site's facts is proven
    # below); the full-corpus states match their RESULTS.md breakdowns.
    site_cells = next(
        int(i) for i, c in enumerate(obj["states"]) if c.get("table") in tb.TITLES
    )
    assert obj["states"][site_cells:] == expected_states
    assert all(c["table"] == "conversion-sample" for c in obj["states"][:site_cells])

    # The accept/reject table matches its RESULTS.md section cell for cell:
    # the rank restarts in each action block (the md has no rank column), and
    # the note carries every count/metric column the md shows.
    registry = reg.load_registry(REPO_ROOT / reg.DEFAULT_REGISTRY_PATH)
    affiliated = {t.id for t in registry.tools if t.affiliated}
    ar = next(t for t in obj["tables"] if t["id"] == "redlines_accept_reject")
    header, body = _pipe_table(sections[MD_SECTION[ar["id"]]])
    assert "Action" in header and "Scored" in header
    assert len(ar["rows"]) == len(body)
    block_rank: dict[str, int] = {}
    for row, md in zip(ar["rows"], body, strict=True):
        scored, pairs = (int(x) for x in md["Scored"].split("/"))
        block_rank[md["Action"]] = block_rank.get(md["Action"], 0) + 1
        assert row == {
            "rank": str(block_rank[md["Action"]]),
            "tool": md["Tool"],
            "pin": f"{md['Version']} · {md['Action'].replace('_', ' ')}",
            "median": float(md["ITT Median"]),
            "mean": float(md["ITT Mean"]),
            "docs": scored,
            "failed": pairs - scored,
            "note": (
                f"= 100: {md['= 100']} · ≥ 90: {md['>= 90']} · < 50: {md['< 50']}"
                f" · ink {md['Ink Jaccard mean']} · text {md['Text boundary mean']}"
            ),
            "ours": md["Tool"] in affiliated,
        }, row["tool"]

    # The redlines_vs_word table matches its section the same way: rank
    # within the block, pin the version, ours from the registry. A line that
    # carries `subset` shows the same statistic in parentheses in the md; the
    # JSON carries the main value.
    def _main(cell: str) -> str:
        return cell.split(" (")[0]

    vs = next(t for t in obj["tables"] if t["id"] == "redlines_vs_word")
    header, body = _pipe_table(sections[MD_SECTION[vs["id"]]])
    assert "Action" not in header and "Version" in header
    assert len(vs["rows"]) == len(body)
    for i, (row, md) in enumerate(zip(vs["rows"], body, strict=True)):
        scored, pairs = (int(x) for x in _main(md["Scored"]).split("/"))
        assert row == {
            "rank": str(i + 1),
            "tool": md["Tool"],
            "pin": md["Version"],
            "median": float(_main(md["ITT Median"])),
            "mean": float(_main(md["ITT Mean"])),
            "docs": scored,
            "failed": pairs - scored,
            "note": (
                f"= 100: {_main(md['= 100'])} · ≥ 90: {_main(md['>= 90'])} · < 50: {_main(md['< 50'])}"
                f" · ink {_main(md['Ink Jaccard mean'])} · text {_main(md['Text boundary mean'])}"
            ),
            "ours": md["Tool"] in affiliated,
        }, row["tool"]

    # And the file is published beside the stores it is built from.
    files = bd.render_files(REPO_ROOT, bundle)
    assert REPO_ROOT / "results" / "scores.json" in files
    assert files[REPO_ROOT / "results" / "scores.json"] == bundle.scores_json


def test_every_results_md_section_with_a_score_table_has_a_json_table() -> None:
    # M5/C1: a section the markdown renders with a pipe table cannot be
    # silently dropped from the JSON. The speed section is the one documented
    # exception (speed ships as its own speed.json in a later plan, not in
    # Scores), so the test also asserts the exception is the speed section.
    # The md keeps its own section headings; scores.json titles are the human
    # ones (#133), so the match runs over table ids, not titles.
    bundle = bd.build(REPO_ROOT)
    obj = json.loads(bundle.scores_json)
    md_to_id = {heading: bid for bid, heading in MD_SECTION.items()}
    ids = {t["id"] for t in obj["tables"]}
    with_table = {
        title
        for title, lines in _sections(bundle.results_md).items()
        if any(ln.startswith("|") for ln in lines)
    }
    speed = {t for t in with_table if t.startswith("speed_")}
    assert speed, "the store's speed section must exist for the exclusion to mean anything"
    assert {md_to_id[s] for s in with_table - speed} <= ids


# ---- 3b. every table carries a human title and description (#133) ---------------


def test_producer_titles_and_descs_cover_every_table_id() -> None:
    # #133: every producer-owned table id has a human title and a one-paragraph
    # description, so a new benchmark id cannot ship untitled: the mapping is
    # keyed on TABLE_IDS and render_scores refuses a table without an entry.
    assert set(sc.TABLE_TITLES) == set(sc.TABLE_IDS)
    assert set(sc.TABLE_DESCS) == set(sc.TABLE_IDS)
    for tid, title in sc.TABLE_TITLES.items():
        assert title.strip(), tid
        assert not title.startswith(tid), f"{tid}: title starts with its own id"
        for machine_id in sc.TABLE_IDS:
            if "_" in machine_id:
                assert machine_id not in title, f"{tid}: title contains {machine_id!r}"
    for tid, desc in sc.TABLE_DESCS.items():
        assert desc.strip(), f"{tid}: empty desc"
        assert "\n" not in desc, f"{tid}: desc must be one paragraph"


def test_scores_json_tables_carry_human_titles_and_descriptions() -> None:
    # #133 on the real store: no table ships an empty desc, no title is the
    # machine id with a colon after it, and the four tables the issue names
    # carry exactly the agreed titles (jubarte.pro's wording, neutralised —
    # benchmarks.law shows the same text).
    obj = json.loads(bd.build(REPO_ROOT).scores_json)
    assert obj["tables"]
    for table in obj["tables"]:
        tid = table["id"]
        assert table["title"].strip(), f"{tid}: empty title"
        assert table["desc"].strip(), f"{tid}: empty desc"
        assert "\n" not in table["desc"], tid
        assert not table["title"].startswith(tid), f"{tid}: title starts with its own id"
        for machine_id in sc.TABLE_IDS:
            if "_" in machine_id:
                assert machine_id not in table["title"], (
                    f"{tid}: title contains {machine_id!r}"
                )
    by_id = {t["id"]: t for t in obj["tables"]}
    assert by_id["docx_to_pdf_no_redline_docs"]["title"] == "Source DOCX → PDF, no redlines"
    assert by_id["docxide_metrics"]["title"] == (
        "The same documents under docxide-pdf's own metrics"
    )
    assert by_id["corpus/word:le3pages"]["title"] == (
        "Below 3 pages: every converter on the same short documents"
    )
    assert by_id["redlines_accept_reject"]["title"] == "Redlines accepted or rejected by Word"


def _undagger(value: dict) -> dict:
    """The site's spelling → the contract's: affiliation in `ours`, never in the name."""
    out = dict(value)
    if isinstance(out.get("name"), str) and out["name"].endswith("†"):
        out["name"] = out["name"][: -len("†")].rstrip()
        out["ours"] = True
    if isinstance(out.get("tool"), str) and out["tool"].endswith("†"):
        out["tool"] = out["tool"][: -len("†")].rstrip()
        out["ours"] = True
    out.setdefault("ours", False)
    return out


def test_real_store_sample_facts_equal_jubarte_app_s_facts() -> None:
    # B4, the single-source proof: the sample tables/headlines/home_groups/
    # method scores.json carries are the bench.* values jubarte.pro holds —
    # the same release_info file, read by both sides.
    if not JUBARTE_APP_FACTS.is_file():
        pytest.skip(f"no jubarte-app checkout at {JUBARTE_APP_FACTS}")
    facts: dict[str, object] = {}
    for line in JUBARTE_APP_FACTS.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("key") in (
            "bench.tables",
            "bench.headlines",
            "bench.home_groups",
            "bench.method",
            "bench.states",
        ):
            facts[record["key"]] = record["value"]
    obj = json.loads(bd.build(REPO_ROOT).scores_json)
    theirs_tables = facts["bench.tables"]
    assert [t["id"] for t in theirs_tables[:2]] == ["conversion-sample", "redlines-sample"]
    for mine, theirs in zip(obj["tables"][:2], theirs_tables[:2], strict=True):
        assert mine == theirs | {
            "rows": [_undagger(r) for r in theirs["rows"]]
        }, mine["id"]
    assert obj["headlines"] == facts["bench.headlines"]
    assert obj["home_groups"] == [
        g | {"rows": [_undagger(b) for b in g["rows"]]} for g in facts["bench.home_groups"]
    ]
    assert obj["method"] == facts["bench.method"]
    sample_states = [
        {k: v for k, v in c.items() if k != "table"} for c in obj["states"][:4]
    ]
    assert sample_states == [
        c | {"rows": [_undagger(r) for r in c["rows"]]} for c in facts["bench.states"]
    ]


# ---- 4. render_files / changed_files publish and check it -----------------------


def test_scores_json_is_written_and_checked(repo: Path) -> None:
    now = datetime(2026, 9, 27, tzinfo=UTC)
    bundle = bd.build(repo, now=now)
    written = bd.write(repo, bundle)
    path = repo / "results" / "scores.json"
    assert path.is_file()
    assert path in written
    assert path.read_text(encoding="utf-8") == bundle.scores_json

    # Stable across days: only the RESULTS.md stamp moves, and that is ignored.
    assert (
        bd.changed_files(repo, bd.build(repo, now=now + timedelta(days=3))) == []
    )
    # Drift in the published file is reported like any other page.
    path.write_text('{\n  "drift": true\n}\n', encoding="utf-8")
    assert path in bd.changed_files(repo, bd.build(repo, now=now))
