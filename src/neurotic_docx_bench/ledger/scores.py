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
* **Every table carries a human title and description (#133).** Producer-owned
  titles and descriptions live in ``TABLE_TITLES`` / ``TABLE_DESCS`` — neutral,
  factual wording (what is measured, against which oracle, on which documents,
  which scorer) because jubarte.pro and benchmarks.law render the same text;
  a title never starts with (or leaks) the machine id, and the md keeps its own
  section headings. A producer-owned id missing from either mapping fails the
  report by name; the sample tables bring their own title and description.
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
REDLINES_TABLE_ID = "redlines_accept_reject"

#: Every producer-owned table id scores.json can emit, in RESULTS.md order:
#: the fidelity benchmarks (``tables.TITLES``) then the two redlines tables.
#: The release-evidence sample tables are not producer-owned; their ids are
#: whatever the newest evidence names (``conversion-sample`` today).
TABLE_IDS: tuple[str, ...] = (*tb.TITLES, REDLINES_VS_WORD_ID, REDLINES_TABLE_ID)

#: The human title of every producer-owned table (#133): plain words for what
#: the table shows — never the machine id, which rides in ``id`` and stays out
#: of the title. Neutral and factual on purpose: jubarte.pro and benchmarks.law
#: render the same text, so no product claims and no "ours". The wording
#: adapts jubarte.pro's hand-written headings.
TABLE_TITLES: dict[str, str] = {
    "script_redlines": "Redline markup vs Word's compare",
    "accepted_changes": "Accepted changes match the final document",
    "roundtrip": "Roundtrip: a document diffed against itself",
    "visual_rendering": "Editor rendering of the plain DOCX",
    "visual_redlines": "Editor rendering of the redline DOCX",
    "visual_accepted_changes": "Editor rendering of the accepted DOCX",
    "docx_to_pdf": "Accepted and randomized redline DOCX to PDF vs Word export",
    "docx_to_pdf_no_redline_docs": "Source DOCX → PDF, no redlines",
    "corpus/word:all": "Every corpus/word DOCX → PDF vs Word's own PDF",
    "docxide_metrics": "The same documents under docxide-pdf's own metrics",
    "corpus/word:le3pages": "Below 3 pages: every converter on the same short documents",
    "docxide_metrics:le3pages": "Below 3 pages: docxide-pdf's metrics on the same short documents",
    REDLINES_VS_WORD_ID: "Redlines vs Word's compare",
    REDLINES_TABLE_ID: "Redlines accepted or rejected by Word",
}

#: One paragraph per producer-owned table (#133): what is measured, against
#: which oracle, on which documents, and with which scorer — the same neutral
#: contract as the titles. Failed documents always score 0 (intent-to-treat);
#: the wording mirrors the oracle notes and section intros RESULTS.md already
#: carries, so the two publications tell the same story.
TABLE_DESCS: dict[str, str] = {
    "script_redlines": (
        "Each tool redlines every base-to-next document pair; its redline DOCX is rendered "
        "by the same Word build that renders the oracle and scored pixel-wise against "
        "Word's own tracked-change redline for the pair, so 100 means pixel-identical to "
        "Word's redline as Word draws it. A failed document scores 0 (intent-to-treat)."
    ),
    "accepted_changes": (
        "The candidate is each tool's own redline with every change accepted; the oracle is "
        "Word's render of Word's accepted document for the same pair, and the two are "
        "compared pixel-wise. A failed accept or render scores 0 (intent-to-treat)."
    ),
    "roundtrip": (
        "Each tool redlines a document against itself; its roundtrip output is scored "
        "pixel-wise against Word's render of the unchanged source, so any change the tool "
        "marks is invented noise. A failed document scores 0 (intent-to-treat)."
    ),
    "visual_rendering": (
        "Each dependency editor loads the plain source DOCX and is captured to PDF by "
        "Playwright; the capture is scored pixel-wise against Word's own PDF export of the "
        "same document. A document the editor fails to load or render scores 0 "
        "(intent-to-treat)."
    ),
    "visual_redlines": (
        "Each dependency editor loads Word's tracked-change DOCX for the pair and is "
        "captured to PDF by Playwright; the capture is scored pixel-wise against Word's own "
        "PDF export of that redline. A failed load or render scores 0 (intent-to-treat)."
    ),
    "visual_accepted_changes": (
        "Each dependency editor loads Word's accepted DOCX for the pair and is captured to "
        "PDF by Playwright; the capture is scored pixel-wise against Word's own PDF export "
        "of the accepted document. A failed load or render scores 0 (intent-to-treat)."
    ),
    "docx_to_pdf": (
        "Each converter turns accepted and randomized-redline DOCX documents into PDF; its "
        "PDF is scored pixel-wise against the SHA-pinned PDF Word itself exported from the "
        "same file. A failed conversion scores 0 for that document (intent-to-treat)."
    ),
    "docx_to_pdf_no_redline_docs": (
        "Each converter turns the clean source DOCX documents, with no tracked changes in "
        "them, into PDF; its PDF is scored pixel-wise against the SHA-pinned PDF Word itself "
        "exported from the same source. A failed conversion scores 0 (intent-to-treat)."
    ),
    "corpus/word:all": (
        "Word's PDF export of each DOCX in all four corpus/word states (clean; tracking "
        "without comments; comments with tracking; comments clean) is the oracle; the "
        "candidate is each converter's PDF of the same file, scored pixel-wise. A failed "
        "conversion scores 0 (intent-to-treat)."
    ),
    "docxide_metrics": (
        "The same documents as the corpus-wide table, scored instead with docxide-pdf's own "
        "ink Jaccard (the ranked number) and text-boundary metrics at 150 DPI against the "
        "same Word PDF exports, so no converter is measured only by this bench's pixel "
        "scorer."
    ),
    "corpus/word:le3pages": (
        "The corpus-wide conversion benchmark restricted to the documents Word lays out in "
        "1 to 3 pages, so a converter that renders only the first 3 pages (unlicensed "
        "PyMuPDF Pro) is compared with every other converter on the same documents. The "
        "oracle stays Word's own PDF export of each document, scored pixel-wise; a failed "
        "conversion scores 0 (intent-to-treat)."
    ),
    "docxide_metrics:le3pages": (
        "The docxide-pdf metrics on the same 1-to-3-page documents: each converter's PDF "
        "scored with ink Jaccard (the ranked number) and text-boundary metrics at 150 DPI "
        "against Word's own PDF exports of the same files."
    ),
    REDLINES_VS_WORD_ID: (
        "Each tool redlines a document pair; Word opens that redline and exports it to PDF, "
        "and the PDF is scored with the pixel scorer against Word's own compare of the same "
        "pair. A pair with no scored PDF — no redline, or one Word could not open — counts "
        "0 in the ITT columns; the = 100, ≥ 90 and < 50 counts and the docxide-pdf Ink "
        "Jaccard and Text boundary means are over the scored PDFs only."
    ),
    REDLINES_TABLE_ID: (
        "Each tool redlines a pair; Word accepts — or rejects — every change in that "
        "redline and exports the result to PDF, scored with the pixel scorer against "
        "Word's own compare of the pair resolved the same way. A pair with no scored PDF "
        "counts 0 (intent-to-treat); the calibration row is Word's own compare against "
        "itself."
    ),
}

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


def _producer_text(mapping: Mapping[str, str], table_id: str, field: str) -> str:
    """A producer-owned table's title or description (#133). A table id
    without one is a bug in this ledger, so it fails the report by name —
    never an empty string the sites would render."""
    try:
        return mapping[table_id]
    except KeyError:
        raise ValueError(
            f"scores.json table {table_id!r} has no human {field} "
            f"(ledger/scores.py TABLE_{field.upper()}S, #133)"
        ) from None


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
                "title": _producer_text(TABLE_TITLES, t.benchmark, "title"),
                "meta": tb.group_line(t),
                "desc": _producer_text(TABLE_DESCS, t.benchmark, "description"),
                "rows": _fidelity_rows(t, row_ci),
            }
            for t in fidelity
        ),
    ]
    for table_id, rows in (
        (REDLINES_VS_WORD_ID, vs_word),
        (REDLINES_TABLE_ID, accept_reject),
    ):
        if rows:
            out_tables.append(
                {
                    "id": table_id,
                    "title": _producer_text(TABLE_TITLES, table_id, "title"),
                    "meta": "",
                    "desc": _producer_text(TABLE_DESCS, table_id, "description"),
                    "rows": rows,
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
        "states": [*sample.get("states", []), *_states(fidelity)],
        "headlines": sample.get("headlines", []),
        "home_groups": sample.get("home_groups", []),
        "method": sample.get("method", []),
    }
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
