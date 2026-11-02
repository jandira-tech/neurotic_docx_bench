"""scores.json: the same rows RESULTS.md renders, as JSON (#113).

RED tests. The feature under test does not exist yet:

- ``neurotic_docx_bench.ledger.scores.render_scores`` (new module),
- ``Bundle.scores_json`` (new field),
- ``render_files`` publishing ``results/scores.json`` (new entry).

Contract pinned here: ``bench report`` also writes ``results/scores.json`` built
from the SAME rows that render RESULTS.md, so the two can never disagree.
``generated`` is the date (YYYY-MM-DD) of the newest row used, never the wall
clock, so ``bench report --check`` stays stable across days.
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
from neurotic_docx_bench.ledger import rows as rws
from neurotic_docx_bench.ledger.scores import render_scores

REPO_ROOT = Path(__file__).resolve().parents[1]

REPO_URL = "https://github.com/jandira-tech/neurotic_docx_bench"
VIEWER_URL = "https://jandira-tech.github.io/neurotic_docx_bench/"

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
    assert table["title"] == (
        "docx_to_pdf: accepted and randomized redline DOCX to PDF vs Word export"
    )
    assert table["meta"] == (
        "Document set `dset1` (25 documents), renderer `oracle:microsoft_word`, "
        "scorer `v1`, bench `0.8`."
    )
    assert table["desc"] == ""
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


def test_render_scores_docxide_note_appends_text_boundary() -> None:
    row = _row(
        "jubarte",
        affiliated=True,
        benchmark="docxide_metrics",
        itt_median=70.68,
        itt_mean=66.84,
        version="jubarte 0.17.0+c607894",
        extra={"text_boundary": {"mean": 99.9, "median": 100.0}},
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
    # The docxide tables carry the text_boundary median beside the CI, exactly as
    # RESULTS.md shows it (its own column there, appended to the note here).
    assert r["note"] == "[70.20, 71.23] · text 100.00"
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
    # table order without the affiliated mark, affiliation in `ours`.
    assert obj["states"] == [
        {
            "name": "clean",
            "n": "2",
            "rows": [
                {"tool": "acme", "median": 91.0, "ours": False},
                {"tool": "bravo", "median": 81.0, "ours": True},
            ],
        },
        {
            "name": "tracking_without_comments",
            "n": "1",
            "rows": [
                {"tool": "acme", "median": 70.0, "ours": False},
                {"tool": "bravo", "median": 60.0, "ours": True},
            ],
        },
    ]
    assert set(obj["states"][0]) == {"name", "n", "rows"}
    assert set(obj["states"][0]["rows"][0]) == {"tool", "median", "ours"}


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


def test_render_scores_redlines_accept_reject_table(tmp_path: Path) -> None:
    empty_run = tmp_path / "redlines_redline_only"
    empty_run.mkdir()
    (empty_run / "scores.jsonl").write_text(
        json.dumps(_action_line("tA", "redline")) + "\n"  # not accept/reject: no table
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
    )
    obj = json.loads(text)
    assert [t["id"] for t in obj["tables"]] == ["docx_to_pdf", "redlines_accept_reject"]
    table = obj["tables"][-1]
    assert set(table) == {"id", "title", "meta", "desc", "rows"}
    assert table["title"] == "redlines accepted or rejected by Word"
    assert table["meta"] == "" and table["desc"] == ""
    # Ranked in the exact order redline_action_section renders: the accept_all
    # block then the reject_all block, each by ITT median/mean; rank is position.
    assert table["rows"] == [
        {
            "rank": "1",
            "tool": "tB",
            "pin": "tB 2.0 · accept all",
            "median": 100.0,
            "mean": 100.0,
            "docs": 400,
            "failed": 0,
            "note": "= 100: 400 · ≥ 90: 400",
            "ours": False,
        },
        {
            "rank": "2",
            "tool": "tA",
            "pin": "tA 1.2 · accept all",
            "median": 99.87,
            "mean": 90.07,
            "docs": 394,
            "failed": 6,  # pairs - scored
            "note": "= 100: 166 · ≥ 90: 299",
            "ours": False,
        },
        {
            "rank": "3",
            "tool": "tB",
            "pin": "tB 2.0 · reject all",
            "median": 99.85,
            "mean": 86.22,
            "docs": 400,
            "failed": 0,
            "note": "= 100: 186 · ≥ 90: 260",
            "ours": False,
        },
        {
            "rank": "4",
            "tool": "tA",
            "pin": "tA 1.2 · reject all",
            "median": 99.8,
            "mean": 85.38,
            "docs": 385,
            "failed": 15,
            "note": "= 100: 155 · ≥ 90: 275",
            "ours": False,
        },
    ]
    assert set(table["rows"][0]) == ROW_KEYS
    assert "≥" in text  # ensure_ascii=False keeps the note readable


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


# ---- 3. integration: the real stores of this worktree ---------------------------


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
    # The newest row in the stores (a converter line of 2026-11-01), never now().
    assert obj["generated"] == "2026-11-01"
    assert obj["repo"] == REPO_URL and obj["viewer"] == VIEWER_URL
    assert obj["provenance"] == {
        "docsets": list(bundle.provenance.docsets),
        "scorers": list(bundle.provenance.scorers),
        "renderers": list(bundle.provenance.renderers),
    }
    assert obj["headlines"] == [] and obj["home_groups"] == [] and obj["method"] == []

    sections = _sections(bundle.results_md)
    ids = [t["id"] for t in obj["tables"]]
    assert ids[-1] == "redlines_accept_reject"
    fidelity = [t for t in obj["tables"] if t["id"] != "redlines_accept_reject"]
    # The same headline tables RESULTS.md renders, in RESULTS.md order.
    assert [t["id"] for t in fidelity] == [
        g.benchmark for g in bundle.headline_groups
    ]

    expected_states: list[dict] = []
    for table in fidelity:
        lines = sections[table["title"]]
        # The group line under the section heading is the table's meta.
        first = next(ln for ln in lines if ln.startswith("Document set `"))
        assert table["meta"] == first.split(". ", 1)[0] + "."
        assert table["desc"] == ""
        header, body = _pipe_table(lines)
        assert len(body) == len(table["rows"]), table["id"]
        for row, md in zip(table["rows"], body, strict=True):
            tool = _md_tool(md["Tool"])
            note = md["95% CI"]
            if "text_boundary median" in header:
                note += f" · text {md['text_boundary median']}"
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
        # The state breakdown that follows the table, as JSON.
        if any(ln.startswith("By corpus state") for ln in lines):
            after = lines[lines.index(next(ln for ln in lines if ln.startswith("By corpus state"))) :]
            s_header, s_body = _pipe_table(after)
            for name, count in (h.rsplit(" (", 1) for h in s_header[1:]):
                n = count.rstrip(")")
                expected_states.append(
                    {
                        "name": name,
                        "n": n,
                        "rows": [
                            {
                                "tool": _md_tool(md["Tool"]),
                                "median": float(md[f"{name} ({n})"].split(" / ")[1]),
                                "ours": md["Tool"].strip().endswith("†"),
                            }
                            for md in s_body
                        ],
                    }
                )
    assert obj["states"] == expected_states

    # The accept/reject table matches its RESULTS.md section cell for cell.
    ar = obj["tables"][-1]
    header, body = _pipe_table(sections[ar["title"]])
    assert "Action" in header and "Scored" in header
    assert len(ar["rows"]) == len(body)
    for i, (row, md) in enumerate(zip(ar["rows"], body, strict=True)):
        scored, pairs = (int(x) for x in md["Scored"].split("/"))
        assert row == {
            "rank": str(i + 1),
            "tool": md["Tool"],
            "pin": f"{md['Version']} · {md['Action'].replace('_', ' ')}",
            "median": float(md["ITT Median"]),
            "mean": float(md["ITT Mean"]),
            "docs": scored,
            "failed": pairs - scored,
            "note": f"= 100: {md['= 100']} · ≥ 90: {md['>= 90']}",
            "ours": False,
        }, row["tool"]

    # And the file is published beside the stores it is built from.
    files = bd.render_files(REPO_ROOT, bundle)
    assert REPO_ROOT / "results" / "scores.json" in files
    assert files[REPO_ROOT / "results" / "scores.json"] == bundle.scores_json


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
