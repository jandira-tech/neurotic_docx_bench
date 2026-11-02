"""results/scores.json: the numbers RESULTS.md renders, as JSON (#113).

``render_scores`` mirrors the ``Scores`` release contract of bench-ops
(``bench_ops.models.Scores``): the field names and types stay identical, so any
consumer can validate the output against that model unchanged.

There is one computation path. Every value comes from the helpers ``tables.py``
renders RESULTS.md with — ``_rank_cell``, ``_ci_cell``, ``fmt``, ``group_line``,
``state_data`` and the redline action rows — so scores.json and the markdown can
never disagree. Recorded, deliberate exceptions (the 2026-11-02 review):

* **Speed is not in Scores.** RESULTS.md's ``speed_redlines`` section has no
  JSON table here on purpose: speed ships as its own ``speed.json`` in a later
  plan, never inside the fidelity contract.
* **``generated`` is the date of the newest bench/converter row**, never the
  build's clock and never RESULTS.md's stamp: the file stays byte-stable across
  days, so ``bench report --check`` stays meaningful. An empty store raises
  instead of dating the file "".
* **``version`` is the bench version string as the bench writes it** (e.g.
  ``1.0.0``), not shortened to the site's ``1.0``.
* **The release-evidence sample tables come first.** ``render_scores`` also
  takes the newest release evidence's ``website_data_*.jsonl`` (the file
  ``jubarte_release_info``'s write stage files under
  ``results/release_<v>_evidence/release_info/``): its non-pending ``bench.*``
  records are the sample tables (first, in the file's order), ``headlines``,
  ``home_groups``, ``method`` and the sample ``states`` — the same values
  jubarte.pro holds, from the same file (single source, #113 / Plan 4).
* **The dagger rule.** The evidence's names carry the affiliation mark
  (``jubarte †``); the contract carries affiliation in the ``ours`` flag, never
  in a name. Sample rows and bars are copied verbatim except that a trailing
  ``†`` is stripped and ``ours`` is set — the one recorded rewrite of a
  record's value.
* **State cells carry ``table``**, the id of the table they break down, and
  ``n`` is thousands-separated (``2,480``) as the sites render it.
* ``TABLE_IDS`` pins the producer-owned table ids (benchmark ids plus the two
  redlines tables) in RESULTS.md section order, so a consumer's fixed id
  mapping can fail loudly on an unknown id. The evidence sample table ids
  (``conversion-sample``, ``redlines-sample``) are data, not schema.
"""

from __future__ import annotations

import json
import re
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from neurotic_docx_bench.ledger import policy as pol
from neurotic_docx_bench.ledger import tables as tb

if TYPE_CHECKING:
    from neurotic_docx_bench.ledger.build import Provenance

RESULTS_REPO_URL = "https://github.com/jandira-tech/neurotic_docx_bench"
VIEWER_URL = "https://jandira-tech.github.io/neurotic_docx_bench/"

# The two blocks of `results/redlines_*/scores.jsonl`, in the order their
# sections have in RESULTS.md (tables.py:redline_action_section): the redline
# action first, then accept/reject.
REDLINES_VS_WORD_ID = "redlines_vs_word"
REDLINES_VS_WORD_TITLE = "redlines vs Word's compare"
REDLINES_TABLE_ID = "redlines_accept_reject"
REDLINES_TABLE_TITLE = "redlines accepted or rejected by Word"

#: Every producer-owned table id scores.json can emit, in RESULTS.md order:
#: the fidelity benchmarks (``tables.TITLES``) then the two redlines tables.
#: The release-evidence sample tables are not producer-owned; their ids are
#: whatever the newest evidence names (``conversion-sample`` today).
TABLE_IDS: tuple[str, ...] = (*tb.TITLES, REDLINES_VS_WORD_ID, REDLINES_TABLE_ID)

# results/release_<v>_evidence/release_info/website_data_<v>_<mm-dd-yy_hh-mm>.jsonl
_EVIDENCE_NAME = re.compile(
    r"^website_data_(\d+(?:\.\d+)*)_(\d{2})-(\d{2})-(\d{2})_(\d{2})-(\d{2})\.jsonl$"
)
_SITE_KEYS = ("bench.tables", "bench.headlines", "bench.home_groups", "bench.method", "bench.states")


def _md_float(value: object, *, tool: str, table: str, stat: str) -> float:
    """The value exactly as its markdown cell renders it: ``fmt`` text parsed back.

    A value the markdown would print ``n/a`` (nothing was measured) is never
    written as a number — 0.0 is a real score, a failed document — so the row
    is refused, naming the tool and the table."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(
            f"scores.json table {table!r}: row {tool!r} has no {stat} value "
            "(its RESULTS.md cell reads n/a); refusing to fabricate 0.0"
        )
    return float(tb.fmt(float(value)))


def _metric_label(metric: str) -> str:
    """How a metric is spelled inside a note: ``text_boundary`` → ``text``."""
    return metric.split("_")[0]


def _fidelity_rows(
    table: pol.HeadlineTable, row_ci: Mapping[str, tuple[float, float] | None]
) -> list[dict]:
    """One JSON row per ranked row: the Rank/Tool/Pin/Docs/Failed/ITT/CI cells of
    RESULTS.md as values, the affiliated ``†`` as the ``ours`` flag, and every
    extra-metric column the markdown renders folded into the note."""
    extras = tb._extra_metrics([r.row for r in table.rows])
    out: list[dict] = []
    for r in table.rows:
        note = tb._ci_cell(row_ci.get(r.row.key))
        for m in extras:
            v = r.row.extra.get(m, {}).get("median")
            note += f" · {_metric_label(m)} {tb.fmt(v) if v is not None else 'n/a'}"
        out.append(
            {
                "rank": tb._rank_cell(r),
                "tool": r.row.display,
                "pin": r.row.pin.display,
                "median": _md_float(
                    r.row.itt_median, tool=r.row.display, table=table.benchmark, stat="median"
                ),
                "mean": _md_float(
                    r.row.itt_mean, tool=r.row.display, table=table.benchmark, stat="mean"
                ),
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
    invented for a measurement that was not made. Every cell names the table it
    breaks down in ``table``."""
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
                    "n": f"{counts[name]:,}",
                    "table": table.benchmark,
                    "rows": [
                        {
                            "tool": row.display,
                            "median": _md_float(
                                cell[1], tool=row.display, table=table.benchmark, stat="median"
                            ),
                            "ours": row.affiliated,
                        }
                        for row, cells in rows
                        if (cell := cells[i]) is not None
                    ],
                }
            )
    return out


def _action_note(line: dict) -> str:
    """Every count/metric column the md's action tables show for the row, folded
    into one note (``_action_cells`` order); ``n/a`` where the md prints it."""
    ov = line.get("overall") or {}

    def cell(block: object, key: str) -> str:
        return tb._fmt_or_na((block or {}).get(key))  # type: ignore[union-attr]

    return (
        f"= 100: {ov.get('exact_100', 0)} · ≥ 90: {ov.get('at_least_90', 0)}"
        f" · < 50: {ov.get('below_50', 0)}"
        f" · ink {cell(line.get('ink_jaccard'), 'mean')}"
        f" · text {cell(line.get('text_boundary'), 'mean')}"
    )


def _action_rows(
    redline_runs: Sequence[Path],
    action: str,
    *,
    table_id: str,
    affiliated_tools: Collection[str],
    pin_action: bool,
) -> list[dict]:
    """One action's rows over every run directory, in the order
    ``ranked_actions`` ranks them (ITT median, then mean — the order the
    markdown shows). The rank is the position within the (run, action) block:
    the markdown ranks each block on its own and has no rank column to copy,
    so no cross-block rank is invented. ``ours`` comes from the registry's
    affiliated tool ids; a name that is not a registry id (the calibration
    identity, a versioned lane) is not ours."""
    rows: list[dict] = []
    for run_dir in redline_runs:
        latest, versions = tb.action_lines(run_dir)
        for i, (tool, line) in enumerate(tb.ranked_actions(latest, action)):
            version = versions.get(tool, "unknown")
            scored = int(line.get("scored", 0) or 0)
            pairs = int(line.get("pairs", 0) or 0)
            rows.append(
                {
                    "rank": str(i + 1),
                    "tool": tool,
                    "pin": f"{version} · {action.replace('_', ' ')}" if pin_action else version,
                    "median": _md_float(
                        line.get("itt_median"), tool=tool, table=table_id, stat="median"
                    ),
                    "mean": _md_float(
                        line.get("itt_mean"), tool=tool, table=table_id, stat="mean"
                    ),
                    "docs": scored,
                    "failed": pairs - scored,
                    "note": _action_note(line),
                    "ours": tool in affiliated_tools,
                }
            )
    return rows


# ------------------------------------------------------------------ the site facts


def _undagger(row: dict, *, name_key: str) -> dict:
    """The dagger rule for one evidence row or bar: a trailing ``†`` moves from
    the name into the ``ours`` flag, which every row then carries explicitly."""
    out = dict(row)
    name = out.get(name_key)
    if isinstance(name, str) and name.endswith(tb.AFFILIATED_MARK):
        out[name_key] = name[: -len(tb.AFFILIATED_MARK)].rstrip()
        out["ours"] = True
    out["ours"] = bool(out.get("ours"))
    return out


@dataclass(frozen=True)
class SiteFacts:
    """The newest release evidence's non-pending ``bench.*`` records — the sample
    tables, headlines, home groups, method and the sample states — as
    ``render_scores`` publishes them (dagger rule applied). The site copy the
    ledger does not compute itself; ndb and jubarte.pro read the same file."""

    tables: tuple[dict, ...]
    headlines: tuple[dict, ...]
    home_groups: tuple[dict, ...]
    method: tuple[dict, ...]
    states: tuple[dict, ...]


def newest_evidence(results_dir: Path) -> Path | None:
    """The newest ``results/release_*_evidence/release_info/website_data_*.jsonl``
    (newest by version, then by stamp), or None when no release filed its copy."""
    best: tuple[tuple, Path] | None = None
    for path in sorted(Path(results_dir).glob("release_*_evidence/release_info/website_data_*.jsonl")):
        m = _EVIDENCE_NAME.match(path.name)
        if m is None:
            continue
        version = tuple(int(x) for x in m.group(1).split("."))
        mm, dd, yy, hh, mi = (int(m.group(i)) for i in range(2, 7))
        key = (version, (2000 + yy, mm, dd, hh, mi))
        if best is None or key > best[0]:
            best = (key, path)
    return best[1] if best is not None else None


def read_site_facts(path: Path) -> SiteFacts:
    """A ``website_data_*.jsonl`` as :class:`SiteFacts`: the latest non-pending
    record per ``bench.*`` key, the dagger rule applied to the tables' rows, the
    bars' names and the states' rows (affiliation moves into ``ours``); every
    other value verbatim. A record the file does not hold is an error, named."""
    latest: dict[str, dict] = {}
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("pending"):
            continue
        key = str(record.get("key", ""))
        if key in _SITE_KEYS:
            latest[key] = record["value"]
    missing = [k for k in _SITE_KEYS if k not in latest]
    if missing:
        raise ValueError(f"{path}: the release evidence has no {', '.join(missing)} record(s)")
    return SiteFacts(
        tables=tuple(
            t | {"rows": [_undagger(r, name_key="tool") for r in t["rows"]]}
            for t in latest["bench.tables"]
        ),
        headlines=tuple(latest["bench.headlines"]),
        home_groups=tuple(
            g | {"rows": [_undagger(b, name_key="name") for b in g["rows"]]}
            for g in latest["bench.home_groups"]
        ),
        method=tuple(latest["bench.method"]),
        states=tuple(
            c | {"rows": [_undagger(r, name_key="tool") for r in c["rows"]]}
            for c in latest["bench.states"]
        ),
    )


def _site(site: SiteFacts) -> dict:
    """The evidence's records as the Scores fields: the sample tables first, the
    sample states carrying the conversion sample table's id (the tables' first
    entry — the states are that table's breakdown), copy verbatim otherwise."""
    conversion = site.tables[0]["id"] if site.tables else ""
    return {
        "tables": [dict(t) for t in site.tables],
        "states": [dict(c, table=conversion) for c in site.states],
        "headlines": [dict(h) for h in site.headlines],
        "home_groups": [dict(g) for g in site.home_groups],
        "method": [dict(m) for m in site.method],
    }


def render_scores(
    tables: Mapping[str, pol.HeadlineTable],
    *,
    row_ci: Mapping[str, tuple[float, float] | None],
    redline_runs: Sequence[Path],
    provenance: Provenance,
    generated: str,
    bench_version: str,
    site: SiteFacts | None = None,
    affiliated_tools: Collection[str] = frozenset(),
) -> str:
    """The Scores JSON text for ``results/scores.json``: the same headline tables
    RESULTS.md renders, in the same order, with the same cells — the
    release-evidence sample tables first, then the fidelity tables, then the two
    redlines tables in their RESULTS.md section order. A benchmark with no
    eligible rows renders nothing in compact RESULTS.md and is absent here
    too. Canonical JSON: sorted keys, 2-space indent, unescaped non-ASCII, one
    trailing newline — deterministic for the same stores."""
    if not generated:
        raise ValueError(
            "scores.json needs the date of the newest row: results/bench.jsonl and "
            "results/converters.jsonl hold no rows"
        )
    fidelity = [
        tables[b]
        for b in tb.TITLES
        if b in tables and tables[b].group is not None and tables[b].rows
    ]
    sample = _site(site) if site is not None else {}
    vs_word = _action_rows(
        redline_runs,
        "redline",
        table_id=REDLINES_VS_WORD_ID,
        affiliated_tools=affiliated_tools,
        pin_action=False,
    )
    accept_reject = _action_rows(
        redline_runs,
        "accept_all",
        table_id=REDLINES_TABLE_ID,
        affiliated_tools=affiliated_tools,
        pin_action=True,
    ) + _action_rows(
        redline_runs,
        "reject_all",
        table_id=REDLINES_TABLE_ID,
        affiliated_tools=affiliated_tools,
        pin_action=True,
    )
    out_tables: list[dict] = [
        *sample.get("tables", []),
        *(
            {
                "id": t.benchmark,
                "title": tb.TITLES.get(t.benchmark, t.benchmark),
                "meta": tb.group_line(t),
                "desc": "",
                "rows": _fidelity_rows(t, row_ci),
            }
            for t in fidelity
        ),
    ]
    for table_id, title, rows in (
        (REDLINES_VS_WORD_ID, REDLINES_VS_WORD_TITLE, vs_word),
        (REDLINES_TABLE_ID, REDLINES_TABLE_TITLE, accept_reject),
    ):
        if rows:
            out_tables.append({"id": table_id, "title": title, "meta": "", "desc": "", "rows": rows})
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
        "states": [*sample.get("states", []), *_states(fidelity)],
        "headlines": sample.get("headlines", []),
        "home_groups": sample.get("home_groups", []),
        "method": sample.get("method", []),
    }
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
