"""results/scores.json: the numbers RESULTS.md renders, as JSON (#113).

``render_scores`` mirrors the ``Scores`` release contract of bench-ops
(``bench_ops.models.Scores``): the field names and types stay identical, so any
consumer can validate the output against that model unchanged. ``headlines``,
``home_groups`` and ``method`` are site copy the ledger does not own; they stay
empty here and are filled by the sites' own facts.

There is one computation path. Every value comes from the helpers ``tables.py``
renders RESULTS.md with — ``_rank_cell``, ``_ci_cell``, ``fmt``, ``group_line``,
``state_data`` and the redline action rows — so scores.json and the markdown can
never disagree. ``generated`` is the date of the newest bench/converter row,
never the wall clock, which keeps the file byte-stable across days and
``bench report --check`` meaningful.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from neurotic_docx_bench.ledger import policy as pol
from neurotic_docx_bench.ledger import tables as tb

if TYPE_CHECKING:
    from neurotic_docx_bench.ledger.build import Provenance

RESULTS_REPO_URL = "https://github.com/jandira-tech/neurotic_docx_bench"
VIEWER_URL = "https://jandira-tech.github.io/neurotic_docx_bench/"

# The accept/reject block of ``results/redlines_*/scores.jsonl``: one table after
# the fidelity tables, in the position its section has in RESULTS.md.
REDLINES_TABLE_ID = "redlines_accept_reject"
REDLINES_TABLE_TITLE = "redlines accepted or rejected by Word"


def _md_float(value: object) -> float:
    """The value exactly as its markdown cell renders it: ``fmt`` text parsed back."""
    if not isinstance(value, int | float) or isinstance(value, bool):
        return 0.0  # the cell would read "n/a"; the model's number is required
    return float(tb.fmt(float(value)))


def _fidelity_rows(
    table: pol.HeadlineTable, row_ci: Mapping[str, tuple[float, float] | None]
) -> list[dict]:
    """One JSON row per ranked row: the Rank/Tool/Pin/Docs/Failed/ITT/CI cells of
    RESULTS.md as values, the affiliated ``†`` as the ``ours`` flag."""
    extras = tb._extra_metrics([r.row for r in table.rows])
    show_text = "text_boundary" in extras
    out: list[dict] = []
    for r in table.rows:
        note = tb._ci_cell(row_ci.get(r.row.key))
        if show_text:
            v = r.row.extra.get("text_boundary", {}).get("median")
            note += f" · text {tb.fmt(v) if v is not None else 'n/a'}"
        out.append(
            {
                "rank": tb._rank_cell(r),
                "tool": r.row.display,
                "pin": r.row.pin.display,
                "median": _md_float(r.row.itt_median),
                "mean": _md_float(r.row.itt_mean),
                "docs": r.row.n_scored,
                "failed": r.row.n_failed_docs,
                "note": note,
                "ours": r.row.affiliated,
            }
        )
    return out


def _states(tables: Sequence[pol.HeadlineTable]) -> list[dict]:
    """The state breakdown of every table that has one, in RESULTS.md table order
    then ``CORPUS_STATES`` order, tools in table order. A tool that scored no
    document of a state (``n/a`` in the markdown) is skipped: no number is
    invented for a measurement that was not made."""
    out: list[dict] = []
    for table in tables:
        data = tb.state_data(table)
        if data is None:
            continue
        names, counts, rows = data
        for i, name in enumerate(names):
            out.append(
                {
                    "name": name,
                    "n": str(counts[name]),
                    "rows": [
                        {
                            "tool": row.display,
                            "median": _md_float(cell[1]),
                            "ours": row.affiliated,
                        }
                        for row, cells in rows
                        if (cell := cells[i]) is not None
                    ],
                }
            )
    return out


def _accept_reject_rows(redline_runs: Sequence[Path]) -> list[dict]:
    """The accept/reject block, in the exact order ``redline_action_section``
    renders it: the accept_all rows then the reject_all rows, each ranked by ITT
    median then mean, latest line per (tool, action); rank is the position."""
    rows: list[dict] = []
    for run_dir in redline_runs:
        latest, versions = tb.action_lines(run_dir)
        for action in ("accept_all", "reject_all"):
            for tool, line in tb.ranked_actions(latest, action):
                ov = line.get("overall") or {}
                scored = int(line.get("scored", 0) or 0)
                pairs = int(line.get("pairs", 0) or 0)
                rows.append(
                    {
                        "rank": "",  # the position, filled in below
                        "tool": tool,
                        "pin": f"{versions.get(tool, 'unknown')} · {action.replace('_', ' ')}",
                        "median": _md_float(line.get("itt_median")),
                        "mean": _md_float(line.get("itt_mean")),
                        "docs": scored,
                        "failed": pairs - scored,
                        "note": f"= 100: {ov.get('exact_100', 0)} · ≥ 90: {ov.get('at_least_90', 0)}",
                        "ours": False,  # scores.jsonl carries no affiliation
                    }
                )
    for i, row in enumerate(rows):
        row["rank"] = str(i + 1)
    return rows


def render_scores(
    tables: Mapping[str, pol.HeadlineTable],
    *,
    row_ci: Mapping[str, tuple[float, float] | None],
    redline_runs: Sequence[Path],
    provenance: Provenance,
    generated: str,
    bench_version: str,
) -> str:
    """The Scores JSON text for ``results/scores.json``: the same headline tables
    RESULTS.md renders, in the same order, with the same cells. A benchmark with
    no eligible rows renders nothing in compact RESULTS.md and is absent here
    too. Canonical JSON: sorted keys, 2-space indent, unescaped non-ASCII, one
    trailing newline — deterministic for the same stores."""
    fidelity = [
        tables[b]
        for b in tb.TITLES
        if b in tables and tables[b].group is not None and tables[b].rows
    ]
    out_tables: list[dict] = [
        {
            "id": t.benchmark,
            "title": tb.TITLES.get(t.benchmark, t.benchmark),
            "meta": tb.group_line(t),
            "desc": "",
            "rows": _fidelity_rows(t, row_ci),
        }
        for t in fidelity
    ]
    accept_reject = _accept_reject_rows(redline_runs)
    if accept_reject:
        out_tables.append(
            {
                "id": REDLINES_TABLE_ID,
                "title": REDLINES_TABLE_TITLE,
                "meta": "",
                "desc": "",
                "rows": accept_reject,
            }
        )
    obj = {
        "version": bench_version,
        "generated": generated,
        "repo": RESULTS_REPO_URL,
        "viewer": VIEWER_URL,
        "provenance": {
            "docsets": list(provenance.docsets),
            "scorers": list(provenance.scorers),
            "renderers": list(provenance.renderers),
        },
        "tables": out_tables,
        "states": _states(fidelity),
        "headlines": [],
        "home_groups": [],
        "method": [],
    }
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
