"""results/release/speed.json: the 10,000-input speed page, emitted from the store.

This is the page's view — the per-pair raw rows of ``results/speed_10k``
aggregated — **not** the ``results/speed.jsonl`` leaderboard that RESULTS.md
renders (the two speed views stay distinct; see the survey §1.2 and
``docs/SPEED.md``). The statistics mirror ``results/speed_10k/summarize.py``,
the script that writes the page's ``SUMMARY.md``: failures are counted apart
and never mix into the success distribution, percentiles are the same
truncated-rank interpolation, and the common/category/quartile buckets are
grouped the same way. Prose (title, intro, task descriptions, notes) is plain
text; ``backtick`` spans mean inline code and the viewer escapes every string
before rendering.
"""

from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from bench_ops.models import (
    Speed,
    SpeedCoverage,
    SpeedNote,
    SpeedRow,
    SpeedTable,
    SpeedTask,
)
from neurotic_docx_bench.ledger.scores import RESULTS_REPO_URL

#: The page's title and introduction, as the speed site renders them.
TITLE = "Speed on 10,000 varied inputs"
INTRO = (
    "Every tool gets the same planned inputs, one tool at a time on one machine "
    "(Apple M4 Pro, 12 cores, 24 GB, macOS). Times are per call. Nothing produced "
    "is kept: each redline or PDF is deleted once it is timed. The raw per-call "
    "rows are in the bench repository under `results/speed_10k/`."
)

#: The per-call timeout every lane runs with (run_redline_speed.sh --timeout 120).
TIMEOUT_MS = 120_000

_CONTRACT_VERSION = "1"
_REDLINES_ID = "redlines"
_PDF_ID = "pdf"
_NOT_MEASURED = "Not measured yet."


def _pct(xs: list[float], q: float) -> float:
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def _stats(rows: list[dict]) -> dict:
    """summarize.py's ``stats``: failures counted apart, never in the distribution."""
    ok = sorted(float(r["ms"]) for r in rows if r["ok"])
    out: dict = {"n": len(rows), "ok": len(ok), "failed": len(rows) - len(ok)}
    if ok:
        out |= {
            "median": statistics.median(ok),
            "mean": statistics.fmean(ok),
            "p95": _pct(ok, 0.95),
            "p99": _pct(ok, 0.99),
            "max": ok[-1],
            "ok_total_s": sum(ok) / 1000,
        }
    return out


def _row(tool: str, bucket: str, rows: list[dict]) -> SpeedRow:
    s = _stats(rows)
    return SpeedRow(
        tool=tool,
        bucket=bucket,
        n=s["n"],
        ok=s["ok"],
        failed=s["failed"],
        median_ms=s.get("median"),
        mean_ms=s.get("mean"),
        p95_ms=s.get("p95"),
        p99_ms=s.get("p99"),
        max_ms=s.get("max"),
        ok_total_s=s.get("ok_total_s"),
    )


def _table(table_id: str, title: str, bucket_header: str, groups: dict) -> SpeedTable:
    return SpeedTable(
        id=table_id,
        title=title,
        bucket_header=bucket_header,
        rows=[
            _row(tool, bucket, rows) for (tool, bucket), rows in sorted(groups.items())
        ],
    )


def _quartile_cuts(sizes: list[int]) -> list[int]:
    s = sorted(sizes)
    return [s[len(s) * q // 4] for q in (1, 2, 3)]


def _paragraphs(lines: list[str]) -> list[str]:
    """Consecutive non-blank, non-special lines joined into paragraphs."""
    out: list[str] = []
    current: list[str] = []
    for line in lines:
        if line.strip() and not line.startswith(("#", "-", "|")):
            current.append(line.strip())
        elif current:
            out.append(" ".join(current))
            current = []
    if current:
        out.append(" ".join(current))
    return out


def _section_body(lines: list[str]) -> tuple[list[str], list[str]]:
    """A note section's lines as (paragraphs, bullets), rendered like the page:
    consecutive text lines join into one paragraph, ``- `` starts a bullet,
    indented lines continue the last bullet."""
    paragraphs: list[str] = []
    bullets: list[str] = []
    para: list[str] = []
    for line in lines:
        if line.startswith("- "):
            if para:
                paragraphs.append(" ".join(para))
                para = []
            bullets.append(line[2:].strip())
        elif line.startswith("  ") and bullets:
            bullets[-1] += " " + line.strip()
        elif line.strip():
            para.append(line.strip())
        elif para:
            paragraphs.append(" ".join(para))
            para = []
    if para:
        paragraphs.append(" ".join(para))
    return paragraphs, bullets


def _notes(md: str) -> list[SpeedNote]:
    """NOTES.md as plain-text sections: ``##`` headings, paragraphs and bullets."""
    sections: list[SpeedNote] = []
    heading: str | None = None
    body: list[str] = []
    for line in md.splitlines():
        if line.startswith("## "):
            if heading is not None:
                paragraphs, bullets = _section_body(body)
                sections.append(SpeedNote(heading=heading, paragraphs=paragraphs, bullets=bullets))
            heading, body = line[3:].strip(), []
        elif line.startswith("# "):
            continue  # the notes document's own title
        else:
            body.append(line)
    if heading is not None:
        paragraphs, bullets = _section_body(body)
        sections.append(SpeedNote(heading=heading, paragraphs=paragraphs, bullets=bullets))
    return sections


def _redlines_task(base: Path) -> SpeedTask:
    out = base / _REDLINES_ID
    plan = {
        str(r["key"]): r
        for r in csv.DictReader((base / "pairs_10k.csv").open(encoding="utf-8"))
    }
    cuts = _quartile_cuts([int(r["base_bytes"]) for r in plan.values()])
    per_tool: dict[str, dict[str, dict]] = {}
    for path in sorted((out / "per_pair").glob("*.jsonl")):
        rows: dict[str, dict] = {}
        for ln in path.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                row = json.loads(ln)
                rows[str(row["key"])] = row
        per_tool[path.stem] = rows
    # Only a lane that covered the whole plan belongs in the comparison tables: a
    # partial rerun lane still in progress would shrink the common bucket for
    # every other tool (its own progress shows in coverage instead).
    compared = {tool for tool, rows in per_tool.items() if len(rows) == len(plan)}
    by_cat: dict[tuple[str, str], list[dict]] = defaultdict(list)
    by_q: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for tool, rows in per_tool.items():
        if tool not in compared:
            continue
        for key, row in rows.items():
            if key not in plan:
                raise ValueError(f"{out / 'per_pair'}: pair {key!r} is not in pairs_10k.csv")
            quartile = sum(int(plan[key]["base_bytes"]) >= cut for cut in cuts)
            by_cat[(tool, "all")].append(row)
            by_cat[(tool, str(row["category"]))].append(row)
            by_q[(tool, f"Q{quartile + 1}")].append(row)
    common = (
        set.intersection(*(set(per_tool[tool]) for tool in sorted(compared)))
        if compared
        else set()
    )
    by_common = {
        (tool, f"{len(common)} common"): [per_tool[tool][k] for k in sorted(common)]
        for tool in sorted(compared)
    }
    summary = out / "SUMMARY.md"
    description = ""
    if summary.is_file():  # the page's intro prose; the numbers stay derived from the rows
        intro = summary.read_text(encoding="utf-8").split("\n## ", 1)[0]
        description = "\n\n".join(_paragraphs(intro.splitlines()[1:]))
    notes_path = out / "NOTES.md"
    return SpeedTask(
        id=_REDLINES_ID,
        title="Redline generation",
        description=description,
        available=True,
        planned=len(plan),
        timeout_ms=TIMEOUT_MS,
        quartile_cuts_bytes=cuts,
        coverage=[
            SpeedCoverage(tool=tool, completed=len(rows), planned=len(plan))
            for tool, rows in sorted(per_tool.items())
        ],
        tables=[
            _table("category", "By pair category", "category", by_cat),
            _table("common", "Same pairs for every tool", "pairs", by_common),
            _table("quartile", "By base size quartile", "quartile", by_q),
        ],
        notes=_notes(notes_path.read_text(encoding="utf-8")) if notes_path.is_file() else [],
    )


def _pdf_task(base: Path) -> SpeedTask:
    root = base / _PDF_ID
    summary = root / "SUMMARY.md"
    if not summary.is_file():
        return SpeedTask(
            id=_PDF_ID, title="DOCX to PDF", description=_NOT_MEASURED, available=False
        )
    docs = {
        str(r["path"]): r
        for r in csv.DictReader((base / "pdf_docs_10k.csv").open(encoding="utf-8"))
    }
    runs = sorted(p for p in root.iterdir() if p.is_dir() and (p / "files.jsonl").is_file())
    by_fam: dict[tuple[str, str], list[dict]] = defaultdict(list)
    by_q: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for ln in (runs[-1] / "files.jsonl").read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        row = json.loads(ln)
        doc = docs.get(str(row.get("path", "")), {})
        family = str(doc.get("family", "?")).split("/")[0].split(":")[0]
        by_fam[(str(row["tool"]), "all")].append(row)
        by_fam[(str(row["tool"]), family)].append(row)
        by_q[(str(row["tool"]), f"Q{int(doc.get('quartile', -1)) + 1}")].append(row)
    description = "\n\n".join(_paragraphs(summary.read_text(encoding="utf-8").splitlines()[1:]))
    counted: dict[str, int] = {}
    for (tool, _), rows in by_fam.items():
        counted[tool] = counted.get(tool, 0) + len(rows)
    return SpeedTask(
        id=_PDF_ID,
        title="DOCX to PDF",
        description=description,
        available=True,
        planned=len(docs),
        coverage=[
            SpeedCoverage(tool=tool, completed=counted[tool], planned=len(docs))
            for tool in sorted(counted)
        ],
        tables=[
            _table("family", "By source family", "family", by_fam),
            _table("quartile", "By document size quartile", "quartile", by_q),
        ],
    )


def emit(root: Path, *, now: datetime | None = None) -> Speed | None:
    """The speed release from ``results/speed_10k``; None when the store is absent.

    Tasks are sorted by id, as the contract orders every list: ``pdf`` before
    ``redlines``. ``generated`` is the emission clock, timezone-aware.
    """
    base = Path(root) / "results" / "speed_10k"
    if not base.is_dir():
        return None
    has_redlines = (base / _REDLINES_ID / "per_pair").is_dir() and (base / "pairs_10k.csv").is_file()
    tasks: list[SpeedTask] = []
    if has_redlines:
        tasks.append(_redlines_task(base))
        tasks.append(_pdf_task(base))
    elif (base / _PDF_ID / "SUMMARY.md").is_file():
        tasks.append(_pdf_task(base))
    if not tasks:
        raise ValueError(
            f"{base}: a speed_10k store with neither a redlines/per_pair lane set nor a pdf summary"
        )
    return Speed(
        version=_CONTRACT_VERSION,
        generated=now or datetime.now(UTC),
        repo=RESULTS_REPO_URL,
        title=TITLE,
        intro=INTRO,
        tasks=sorted(tasks, key=lambda t: t.id),
    )
