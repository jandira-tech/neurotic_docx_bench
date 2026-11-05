"""Release-set case shards for Plan 7 (issue #131).

The ordinary case release in :mod:`neurotic_docx_bench.ledger.cases` is the
historical, store/legacy view.  A jubarte release adds two versioned shards
over the fixed evaluation sets:

* the 860 conversion rows in ``results/sets/convert_860.csv``;
* the 600 redline rows in ``results/sets/redline_600.csv``.

Each shard has the Word reference lane, the release's own jubarte lane, and
every vendor lane found by ``newest_vendor_lanes``.  A lane that did not score
a row is absent for that row -- never a zero.  The files point at the record
on Hugging Face and the shown-page asset paths are the exact keys the later
R2 upload plan must carry.

The module is imported by ``ledger.cases`` as its public ``emit_release``
entry point.  It deliberately reads only the set-scoped score artifacts and
the local run directories; it never uploads anything.
"""

from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from bench_ops.models import (
    Case,
    CaseShard,
    CasesIndex,
    MetricDiagnostics,
    ShardRef,
    engines_from_cases,
    shard_path,
    validate_bundle,
)
from neurotic_docx_bench.jubarte_release_info import (
    RUN_DIR,
    refresh_convert_lanes,
    refresh_redline_lanes,
)
from neurotic_docx_bench.ledger.scores import RESULTS_REPO_URL
from neurotic_docx_bench.pages import render as pages_render
from neurotic_docx_bench.word_outputs import find_output, read_manifest

#: The public R2 base the release's shown-page paths resolve against.
ASSETS_BASE = "https://pub-92c80eda1059428394970066c8500eda.r2.dev/"

#: The release-contract schema version.
CONTRACT_VERSION = "1"

#: The public base a case's file paths resolve against.
FILES_BASE_TEMPLATE = (
    "https://huggingface.co/datasets/arthrod/neurotic_docx_bench/resolve/{revision}/"
)

#: The fixed sets a release scores.
CONVERT_SET = Path("results/sets/convert_860.csv")
REDLINE_SET = Path("results/sets/redline_600.csv")

ReleaseKind = Literal["convert", "redline"]

_LABELS = {
    "reference": "Word",
    "docxide-pdf": "docxide-pdf",
    "apryse": "Apryse",
    "docxodus": "docxodus",
    "soffice": "LibreOffice",
    "superdoc": "SuperDoc",
}


@dataclass(frozen=True)
class ReleaseSource:
    """One lane's local PDF and the number of shown assets it contributes."""

    kind: ReleaseKind
    case: str
    lane: str
    pdf: Path | None
    pages: int


@dataclass(frozen=True)
class ReleaseBundle:
    """The release shards plus the local sources and the emission report."""

    index: CasesIndex
    shards: list[CaseShard]
    sources: tuple[ReleaseSource, ...]
    report: dict[str, object]


@dataclass(frozen=True)
class _Lane:
    """One score lane and the artifact that holds its rows."""

    kind: ReleaseKind
    key: str
    version: str
    tool: str
    work_tool: str
    upload_lane: str
    artifact: Path
    data: dict


def _files_base(value: str) -> str:
    """The public files base, from a full URL or a dataset revision."""
    text = str(value).strip()
    if not text.startswith("https://"):
        return FILES_BASE_TEMPLATE.format(revision=text)
    return text if text.endswith("/") else text + "/"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _int_or_zero(value: object) -> int:
    if not isinstance(value, (int, float, str)):
        return 0
    try:
        return max(0, int(value))
    except TypeError, ValueError, OverflowError:
        return 0


def _signed_int(value: object) -> int:
    """An integer that may be negative (the signed break drift)."""
    if not isinstance(value, (int, float, str)):
        return 0
    try:
        return int(value)
    except TypeError, ValueError, OverflowError:
        return 0


def _number(value: object) -> float | None:
    """A finite JSON number, or None when the value is absent or not numeric."""
    if value is None or not isinstance(value, (int, float, str)):
        return None
    try:
        number = float(value)
    except TypeError, ValueError, OverflowError:
        return None
    return number if math.isfinite(number) else None


def _metric(value: object) -> float | None:
    number = _number(value)
    if number is None:
        return None
    return round(number * 100.0, 1)


def _pdf_pages(path: Path | None) -> int:
    if path is None or not path.is_file():
        return 0
    try:
        return pages_render.page_count(path)
    except pages_render.RenderError:
        return 0


def _first_existing(candidates: list[Path]) -> Path | None:
    return next((path for path in candidates if path.is_file()), None)


def _conversion_candidate(root: Path, vendor_root: Path, lane: _Lane, stem: str) -> Path | None:
    """The lane's local candidate PDF for one conversion fixture."""
    if lane.key.startswith("jubarte-"):
        preferred = (
            root
            / "results"
            / f"release_{lane.upload_lane.removeprefix('jubarte_')}_evidence"
            / "convert_work"
            / "jubarte"
            / "candidate"
            / f"{stem}.pdf"
        )
        return _first_existing([preferred]) or preferred

    work = vendor_root / "results" / f"{lane.work_tool}_{lane.version}_work"
    candidates = [
        work / "candidate" / f"{stem}.pdf",
        work / lane.tool / "candidate" / f"{stem}.pdf",
        work / "docxide-pdf" / "candidate" / f"{stem}.pdf",
        work / "docxodus" / "candidate" / f"{stem}.pdf",
        work / "apryse" / "candidate" / f"{stem}.pdf",
    ]
    return _first_existing(candidates) or candidates[0]


def _word_pdf(folder: Path, key: str, *tools: str) -> Path | None:
    """The PDF Word exported for one redline, following the driver's manifest.

    ``tools`` are the names the lane's redlines may carry, most specific first
    (a refresh lane's ``<tool>-<version>``, then ``<tool>``; #177). Long names
    are trimmed before Word sees them; the manifest's ``renamed`` lines lead to
    the trimmed name. A prefix of the key is never trusted: pairs that share a
    base document share it, and a wrong pair's redline is worse than none (#177)."""
    if not folder.is_dir():
        return None
    originals = [f"{key}_{tool}.docx" for tool in tools] + [f"{key}.docx"]
    for original in originals:
        found = find_output(folder, original, kind="pdf", ext=".pdf")
        if found is not None:
            return found
    return _sibling_word_pdf(folder, key, tools)


#: Word's fresh compares: local folder and its results-dataset path (hub.FRESH_COMPARES).
COMPARE_REGEN_OUT = Path("results/compare_regen/out")
FRESH_COMPARES = "outputs/redlines_0929_full/fresh_compares"

#: word_pdf.py's trim_name: a long stem keeps 8 hex of sha1(original) before the suffix.
_TRIMMED_EXPORT = re.compile(r"_[0-9a-f]{8}_byword\.pdf$")

_REDLINE_ID = re.compile(r"^(?P<pair>.+)_redline_[0-9a-f]+$")


def _sibling_word_pdf(folder: Path, key: str, tools: tuple[str, ...]) -> Path | None:
    """The lane's redline of the same base/next pair under another Word comparison id.

    Word compared some pairs twice, so one pair has two redline ids; a lane
    generates the pair once, under one of them, while the set may key the case by
    the other. The ids in ``<base>__vs__<next>`` are content hashes, so a name
    that carries the whole pair is a redline of the same two documents. Only a
    single such sibling is linked; two are ambiguous and give nothing."""
    match = _REDLINE_ID.match(key)
    if match is None:
        return None
    pair = re.escape(match["pair"])
    names = {str(line.get("original_filename") or "") for line in read_manifest(folder)}
    names |= {
        path.name.removesuffix(".pdf").removesuffix("_byword") + ".docx"
        for path in folder.glob("*.pdf")
    }
    for tool in tools:
        pattern = re.compile(rf"^{pair}_redline_[0-9a-f]+_{re.escape(tool)}\.docx$")
        siblings = sorted(
            name for name in names if pattern.match(name) and name != f"{key}_{tool}.docx"
        )
        if len(siblings) > 1:
            return None
        if siblings:
            found = find_output(folder, siblings[0], kind="pdf", ext=".pdf")
            if found is not None:
                return found
    return None


def _redline_lane_dir(lane: _Lane) -> str:
    """The lane's folder under the run directory — the folder the uploader published.

    The release's own lane is ``jubarte-<v>``; a vendor refresh lane is
    ``<tool>-<version>``. The hub copy lives under the same name.
    """
    return lane.key if lane.key.startswith("jubarte-") else f"{lane.tool}-{lane.version}"


def _redline_tools(lane: _Lane) -> tuple[str, ...]:
    """The names the lane's redlines may carry (``<key>_<name>.docx``), most specific
    first: the release's own lane is ``jubarte-<v>``; a refresh lane's Word manifest
    names ``<tool>-<version>``, older lanes ``<tool>`` (#177)."""
    if lane.key.startswith("jubarte-"):
        return (lane.key,)
    return (f"{lane.tool}-{lane.version}", lane.tool)


def _redline_candidate(root: Path, vendor_root: Path, lane: _Lane, key: str) -> Path | None:
    folder = vendor_root / RUN_DIR / _redline_lane_dir(lane) / "pdf_by_word"
    return _word_pdf(folder, key, *_redline_tools(lane))


def _redline_file(lane: _Lane, pdf: Path) -> str:
    """The record path of a redline lane's Word PDF, in the #140 HF layout."""
    return f"~/outputs/redlines_0929_full/{_redline_lane_dir(lane)}/pdf_by_word/{pdf.name}"


def _asset_path(version: str, kind: ReleaseKind, case: str, lane: str, page: int) -> str:
    """The R2-relative path of one shown page."""
    safe_case = case.replace("/", "__")
    safe_lane = lane.replace("/", "__")
    return f"~/release/{version}/{kind}/{safe_case}/{safe_lane}/page_{page:03d}.webp"


def _conversion_file(lane: _Lane, stem: str) -> str:
    """The record path of a conversion candidate, in the #140 HF layout."""
    return f"~/outputs/convert_860/{lane.upload_lane}/pdf/{stem}.pdf"


def _normalise_page_scores(raw: object) -> dict[int, float | None] | None:
    """A raw per-page score payload as ``{page number: score or None}``."""
    if raw is None:
        return None
    values: dict[int, float | None] = {}
    if isinstance(raw, list):
        for index, item in enumerate(raw, start=1):
            if isinstance(item, dict):
                page = _int_or_zero(item.get("page")) or index
                score = item.get("score")
                if score is None:
                    score = item.get("pixel")
            else:
                page = index
                score = item
            values[page] = _number(score)
        return values
    if isinstance(raw, dict):
        scores = raw.get("scores")
        if isinstance(scores, list):
            return _normalise_page_scores(scores)
        for key, item in raw.items():
            if not isinstance(key, (int, str)):
                continue
            try:
                page = int(key)
            except TypeError, ValueError:
                continue
            if isinstance(item, dict):
                item = item.get("score")
            values[page] = _number(item)
        return values
    return None


def _page_scores_for(lane: _Lane, case: str, shown: list[int]) -> list[float | None] | None:
    """The lane's real per-page scores for one case, or None when absent."""
    raw: object = None
    if lane.kind == "convert":
        for name in ("per_page", "page_scores", "pages"):
            value = lane.data.get(name)
            if isinstance(value, dict) and case in value:
                raw = value[case]
                break
            if isinstance(value, list):
                raw = value
                break
        if raw is None:
            per_doc = lane.data.get("per_doc")
            if isinstance(per_doc, dict) and isinstance(per_doc.get(case), dict):
                raw = per_doc[case].get("pages")
    else:
        row = lane.data.get(case)
        if isinstance(row, dict):
            for name in ("pages", "page_scores", "per_page"):
                if name in row:
                    raw = row[name]
                    break
    values = _normalise_page_scores(raw)
    if values is None:
        return None
    return [values.get(page) for page in shown]


def _conversion_score(lane: _Lane, stem: str) -> tuple[float | None, dict[str, float | None]]:
    per_doc = lane.data.get("per_doc") or {}
    matches = {str(key).lower(): value for key, value in per_doc.items()}
    pixel = matches.get(stem.lower())
    metrics: dict[str, float | None] = {}
    page_metrics = lane.data.get("page_metrics") or {}
    if isinstance(page_metrics, dict):
        values = page_metrics.get(stem)
        if isinstance(values, dict):
            for name in ("jaccard", "ssim", "text_boundary"):
                if values.get(name) is not None:
                    metrics[name] = _metric(values[name])
    return (None if pixel is None else float(pixel)), metrics


def _redline_score(lane: _Lane, key: str) -> tuple[float | None, dict[str, float | None]]:
    row = lane.data.get(key)
    if not isinstance(row, dict):
        return None, {}
    pixel = row.get("overall_score_pagefair")
    if pixel is None:
        pixel = row.get("overall_score")
    if pixel is None:
        pixel = row.get("average_score")
    metrics: dict[str, float | None] = {}
    for name, target in (
        ("ink_jaccard", "jaccard"),
        ("ssim", "ssim"),
        ("text_boundary", "text_boundary"),
    ):
        if row.get(name) is not None:
            metrics[target] = _metric(row[name])
    return (None if pixel is None else float(pixel)), metrics


def _redline_reference_pages(lanes: list[_Lane], key: str, pdf: Path | None) -> int:
    for lane in lanes:
        row = lane.data.get(key)
        if isinstance(row, dict) and row.get("page_count_oracle") is not None:
            return _int_or_zero(row.get("page_count_oracle"))
    return _pdf_pages(pdf)


def _current_conversion_artifact(root: Path, version: str) -> Path:
    candidates = [
        root
        / "results"
        / f"release_{version}_evidence"
        / f"docx_to_pdf_jubarte_{version}_sample.json",
        root / "results" / f"docx_to_pdf_jubarte_{version}.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError(f"no jubarte {version} conversion score artifact: expected {candidates[0]}")


def _current_redline_artifact(root: Path, version: str) -> Path:
    candidates = [
        root / RUN_DIR / f"scores_jubarte-{version}_sample_redline_{version}.json",
        root / RUN_DIR / f"scores_jubarte-{version}_set-redline_600.json",
        root / RUN_DIR / f"scores_jubarte-rust_sample_redline_{version}.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError(f"no jubarte {version} redline score artifact: expected {candidates[0]}")


def _conversion_lanes(root: Path, version: str, set_name: str) -> list[_Lane]:
    current_path = _current_conversion_artifact(root, version)
    current = _read_json(current_path)
    tool = current.get("tools", {}).get("jubarte")
    if tool is None and current.get("tools"):
        tool = next(iter(current["tools"].values()))
    if tool is None:
        raise RuntimeError(f"{current_path}: no tool scores")
    lanes = [
        _Lane(
            kind="convert",
            key=f"jubarte-{version}",
            version=version,
            tool="jubarte",
            work_tool="jubarte",
            upload_lane=f"jubarte_{version}",
            artifact=current_path,
            data=tool,
        )
    ]
    for tool_name, (lane_version, path) in sorted(refresh_convert_lanes(root, set_name).items()):
        report = _read_json(path)
        tools = report.get("tools") or {}
        tool_data = tools.get(tool_name)
        inner_tool = tool_name
        if tool_data is None and len(tools) == 1:
            # The refresh filename says ``docxide`` while the report and the
            # uploaded lane say ``docxide-pdf``.  The report's own tool key is
            # the published identity; the work directory keeps the filename's
            # spelling.
            inner_tool, tool_data = next(iter(tools.items()))
        if tool_data is None:
            continue
        lanes.append(
            _Lane(
                kind="convert",
                key=inner_tool,
                version=lane_version,
                tool=inner_tool,
                work_tool=tool_name,
                upload_lane=f"{inner_tool}_{lane_version}",
                artifact=path,
                data=tool_data,
            )
        )
    return lanes


def _redline_lanes(root: Path, version: str, set_name: str) -> list[_Lane]:
    current_path = _current_redline_artifact(root, version)
    current = _read_json(current_path)
    lanes = [
        _Lane(
            kind="redline",
            key=f"jubarte-{version}",
            version=version,
            tool="jubarte",
            work_tool="jubarte",
            upload_lane=f"jubarte_{version}",
            artifact=current_path,
            data=current.get("rows") or {},
        )
    ]
    for tool_name, (lane_version, path) in sorted(refresh_redline_lanes(root, set_name).items()):
        score = _read_json(path)
        lanes.append(
            _Lane(
                kind="redline",
                key=tool_name,
                version=lane_version,
                tool=tool_name,
                work_tool=tool_name,
                upload_lane=f"{tool_name}_{lane_version}",
                artifact=path,
                data=score.get("rows") or {},
            )
        )
    return lanes


def _conversion_cases(
    root: Path,
    vendor_root: Path,
    version: str,
    rows: list[dict[str, str]],
    lanes: list[_Lane],
    limit: int | None,
) -> tuple[list[Case], list[ReleaseSource], int]:
    cases: list[Case] = []
    sources: list[ReleaseSource] = []
    page_score_entries = 0
    selected = rows if limit is None else rows[:limit]
    for row in sorted(selected, key=lambda item: item["stem"]):
        stem = row["stem"]
        reference_pdf = root / row["word_pdf"]
        if not reference_pdf.is_file():
            # A vendor refresh work directory keeps Word's oracle beside its
            # candidate renders; use it read-only when the corpus is absent.
            for lane in lanes:
                work = vendor_root / "results" / f"{lane.work_tool}_{lane.version}_work" / "oracle"
                candidate = work / f"{stem}.pdf"
                if candidate.is_file():
                    reference_pdf = candidate
                    break
        reference_count = _int_or_zero(row.get("pages")) or _pdf_pages(reference_pdf)
        if reference_count < 1:
            raise RuntimeError(f"{stem}: no Word reference PDF or page count")
        shown = list(range(1, min(12, reference_count) + 1))

        pages: dict[str, list[str | None]] = {
            "reference": [
                _asset_path(version, "convert", stem, "reference", page) for page in shown
            ]
        }
        page_counts: dict[str, int] = {"reference": reference_count}
        scores: dict[str, dict[str, float | None]] = {}
        times: dict[str, float] = {}
        versions: dict[str, str] = {"reference": "Microsoft Word"}
        files: dict[str, str] = {}
        errors: dict[str, str] = {}
        page_scores: dict[str, list[float | None]] = {}

        for lane in lanes:
            failures = {
                str(item.get("doc")): str(item.get("error") or "conversion failed")
                for item in (lane.data.get("generate_failures") or [])
            }
            pixel, metrics = _conversion_score(lane, stem)
            if pixel is None:
                # The lane never ran this row: absent, never zero.
                continue
            candidate = _conversion_candidate(root, vendor_root, lane, stem)
            candidate_count = _int_or_zero(lane.data.get("page_count_candidate")) or _pdf_pages(
                candidate
            )
            if not candidate_count and stem not in failures:
                # #180: never a scored case with no pages and no file, silently
                raise RuntimeError(
                    f"{stem}: lane {lane.key} is scored but its candidate PDF is missing "
                    f"({candidate}) and its row records no page count; {_inputs_hint(version)}"
                )
            lane_pages = [
                _asset_path(version, "convert", stem, lane.key, page)
                if page <= candidate_count
                else None
                for page in shown
            ]
            pages[lane.key] = lane_pages
            page_counts[lane.key] = candidate_count
            scores[lane.key] = {"pixel": pixel} | metrics
            versions[lane.key] = (
                f"jubarte {version}"
                if lane.key.startswith("jubarte-")
                else str(lane.data.get("version") or f"{lane.tool} {lane.version}")
            )
            seconds = (lane.data.get("convert_seconds") or {}).get(stem)
            if seconds is not None:
                times[lane.key] = float(seconds)
            if stem in failures:
                errors[lane.key] = failures[stem]
            if candidate_count:
                files[lane.key] = _conversion_file(lane, stem)
            raw_page_scores = _page_scores_for(lane, stem, shown)
            if raw_page_scores is not None:
                page_scores[lane.key] = raw_page_scores
                page_score_entries += 1
            sources.append(
                ReleaseSource(
                    kind="convert",
                    case=stem,
                    lane=lane.key,
                    pdf=candidate if candidate is not None and candidate.is_file() else None,
                    pages=min(candidate_count, len(shown)),
                )
            )

        sources.append(
            ReleaseSource(
                kind="convert",
                case=stem,
                lane="reference",
                pdf=reference_pdf if reference_pdf.is_file() else None,
                pages=len(shown),
            )
        )
        cases.append(
            Case(
                kind="conversion",
                group=f"cases/release-{version}",
                case=stem,
                pages=pages,
                page_counts=page_counts,
                scores=scores,
                times=times,
                versions=versions,
                dropped=[],
                reference_app="Microsoft Word",
                files=files,
                errors=errors,
                page_scores=page_scores,
                shown=shown,
                stem=stem,
                state=row.get("state") or None,
                set="convert_860",
            )
        )
    return cases, sources, page_score_entries


def _redline_cases(
    root: Path,
    vendor_root: Path,
    version: str,
    rows: list[dict[str, str]],
    lanes: list[_Lane],
    limit: int | None,
) -> tuple[list[Case], list[ReleaseSource], int]:
    cases: list[Case] = []
    sources: list[ReleaseSource] = []
    page_score_entries = 0
    selected = rows if limit is None else rows[:limit]
    for lane in lanes:
        folder = vendor_root / RUN_DIR / _redline_lane_dir(lane) / "pdf_by_word"
        if lane.data and not any(folder.glob("*.pdf")):
            # #180: without the lane's PDFs every link of the lane vanishes, silently
            raise RuntimeError(
                f"lane {lane.key} is scored but {folder} holds no PDF; {_inputs_hint(version)}"
            )
        trimmed = any(_TRIMMED_EXPORT.search(p.name) for p in folder.glob("*.pdf"))
        if lane.data and trimmed and not (folder / "manifest.jsonl").is_file():
            # #180: a trimmed export name resolves to its key only through the manifest;
            # without it the lane's links vanished silently (592 of 600 in a clean tree)
            raise RuntimeError(
                f"lane {lane.key}: {folder} holds trimmed export names but no manifest.jsonl "
                f"to resolve them; {_inputs_hint(version)}"
            )
    for row in sorted(selected, key=lambda item: item["key"]):
        key = row["key"]
        reference_pdf = _redline_reference(root, row)
        if not reference_pdf.is_file():
            for lane in lanes:
                folder = vendor_root / RUN_DIR / _redline_lane_dir(lane) / "pdf_by_word"
                candidate = _word_pdf(folder, key, *_redline_tools(lane))
                if candidate is not None:
                    reference_pdf = candidate
                    break
        reference_count = _redline_reference_pages(lanes, key, reference_pdf)
        if reference_count < 1:
            raise RuntimeError(f"{key}: no Word reference PDF or page count; {_inputs_hint(version)}")
        shown = list(range(1, min(12, reference_count) + 1))

        pages: dict[str, list[str | None]] = {
            "reference": [_asset_path(version, "redline", key, "reference", page) for page in shown]
        }
        page_counts: dict[str, int] = {"reference": reference_count}
        scores: dict[str, dict[str, float | None]] = {}
        versions: dict[str, str] = {"reference": "Microsoft Word"}
        diagnostics: dict[str, MetricDiagnostics] = {}
        page_scores: dict[str, list[float | None]] = {}
        files: dict[str, str] = {}

        for lane in lanes:
            pixel, metrics = _redline_score(lane, key)
            if pixel is None:
                continue
            candidate = _redline_candidate(root, vendor_root, lane, key)
            row_data = lane.data.get(key) or {}
            candidate_count = _int_or_zero(row_data.get("page_count_candidate")) or _pdf_pages(
                candidate
            )
            if not candidate_count:
                raise RuntimeError(
                    f"{key}: lane {lane.key} is scored but has no page count and no PDF "
                    f"({candidate}); {_inputs_hint(version)}"
                )
            pages[lane.key] = [
                _asset_path(version, "redline", key, lane.key, page)
                if page <= candidate_count
                else None
                for page in shown
            ]
            page_counts[lane.key] = candidate_count
            scores[lane.key] = {"pixel": pixel} | metrics
            versions[lane.key] = (
                f"jubarte {version}"
                if lane.key.startswith("jubarte-")
                else f"{lane.tool} {lane.version}"
            )
            diagnostics[lane.key] = MetricDiagnostics(
                ref_pages=_int_or_zero(row_data.get("page_count_oracle")),
                pages=candidate_count,
                scored_pages=_int_or_zero(row_data.get("page_count")) or candidate_count,
                max_break_drift=_signed_int(row_data.get("max_break_drift")),
            )
            raw_page_scores = _page_scores_for(lane, key, shown)
            if raw_page_scores is not None:
                page_scores[lane.key] = raw_page_scores
                page_score_entries += 1
            if candidate is not None and candidate.is_file():
                # the lane's Word export of the redline, on the hub (#143)
                files[lane.key] = _redline_file(lane, candidate)
            sources.append(
                ReleaseSource(
                    kind="redline",
                    case=key,
                    lane=lane.key,
                    pdf=candidate if candidate is not None and candidate.is_file() else None,
                    pages=min(candidate_count, len(shown)),
                )
            )

        sources.append(
            ReleaseSource(
                kind="redline",
                case=key,
                lane="reference",
                pdf=reference_pdf if reference_pdf.is_file() else None,
                pages=len(shown),
            )
        )
        cases.append(
            Case(
                kind="redline",
                group=f"redlines/release-{version}",
                case=key,
                pages=pages,
                page_counts=page_counts,
                scores=scores,
                times={},
                versions=versions,
                dropped=[],
                reference_app="Microsoft Word",
                metric_diagnostics=diagnostics,
                page_scores=page_scores,
                files=files,
                shown=shown,
                state=row.get("state") or None,
                set="redline_600",
                pair=key,
            )
        )
    return cases, sources, page_score_entries


def _index(
    version: str,
    files_base: str,
    shards: list[CaseShard],
    *,
    now: datetime | None,
) -> CasesIndex:
    cases = [case for shard in shards for case in shard.cases]
    labels = dict(_LABELS)
    labels[f"jubarte-{version}"] = f"jubarte {version}"
    index = CasesIndex(
        version=CONTRACT_VERSION,
        generated=now or datetime.now(UTC),
        repo=RESULTS_REPO_URL,
        assets_base=ASSETS_BASE,
        engines=engines_from_cases(cases, labels),
        groups=[
            ShardRef(
                kind=shard.kind,
                group=shard.group,
                count=len(shard.cases),
                path=shard_path(shard.kind, shard.group),
            )
            for shard in shards
        ],
        files_base=files_base,
    )
    validate_bundle(index, shards)
    return index


def _inputs_hint(version: str) -> str:
    return (
        f"fetch the release's inputs from the hub first: "
        f"uv run scripts/release_inputs.py --release-version {version}"
    )


@dataclass(frozen=True)
class ReleaseInput:
    """One folder the release build reads, and the results-hub folder it comes from (#180)."""

    hub_path: str
    local: Path
    repo: str = "results"  # "results" (pinned by the release evidence) or "fixtures" (set v1)
    files: tuple[str, ...] = ()  # names inside hub_path; empty = every PDF of the folder


def _redline_reference(root: Path, row: dict[str, str]) -> Path:
    """Word's compare for a redline row: ``oracle_pdf``, or the corpus ``pdf`` when the set
    records the same bytes for both (#180: the oracle_pdf/ folder is a local copy of
    corpus PDFs, never published under that name)."""
    oracle = root / (row.get("oracle_pdf") or row.get("pdf") or "")
    if oracle.is_file() or not row.get("pdf"):
        return oracle
    same = row.get("oracle_pdf_sha256") and row.get("oracle_pdf_sha256") == row.get("pdf_sha256")
    return root / row["pdf"] if same else oracle


def release_inputs(
    root: Path,
    version: str,
    *,
    convert_csv: Path | None = None,
    redline_csv: Path | None = None,
    vendor_root: Path | None = None,
) -> list[ReleaseInput]:
    """Every local folder of PDFs the versioned build reads, with its hub folder (#180).

    The PDFs are not tracked: the conversion candidates and the redline lanes' Word
    exports live on the results dataset (``outputs/``), pinned by the release evidence.
    ``scripts/release_inputs.py`` downloads exactly these, so a clean checkout builds the
    same release as the machine that ran the bench.
    """
    root = Path(root).resolve()
    vendor_root = Path(vendor_root or root).resolve()
    convert_csv = Path(convert_csv or CONVERT_SET)
    redline_csv = Path(redline_csv or REDLINE_SET)
    out: list[ReleaseInput] = []
    for lane in _conversion_lanes(root, version, convert_csv.stem):
        if lane.key.startswith("jubarte-"):
            local = root / "results" / f"release_{version}_evidence" / "convert_work" / "jubarte"
        else:
            local = vendor_root / "results" / f"{lane.work_tool}_{lane.version}_work"
        out.append(ReleaseInput(f"outputs/convert_860/{lane.upload_lane}/pdf", local / "candidate"))
    # Word's own compare PDFs, the redline references: Word's fresh compares on the
    # results dataset, or corpus PDFs on the fixtures dataset (what _redline_reference reads)
    redline_rows = _read_csv(redline_csv if redline_csv.is_absolute() else root / redline_csv)
    wanted: dict[tuple[str, str, Path], set[str]] = {}
    for row in redline_rows:
        oracle = Path(row.get("oracle_pdf") or "")
        same = row.get("oracle_pdf_sha256") and row.get("oracle_pdf_sha256") == row.get("pdf_sha256")
        if oracle.is_relative_to(COMPARE_REGEN_OUT):
            where = ("results", FRESH_COMPARES, root / COMPARE_REGEN_OUT)
            wanted.setdefault(where, set()).add(oracle.name)
        elif row.get("pdf") and (same or not row.get("oracle_pdf")):
            corpus = Path(row["pdf"])  # corpus/word/<state>/pdf/<name>
            if corpus.is_relative_to("corpus"):
                folder = corpus.parent.relative_to("corpus").as_posix()
                where = ("fixtures", folder, root / corpus.parent)
                wanted.setdefault(where, set()).add(corpus.name)
    for (repo, hub_path, local), names in sorted(wanted.items(), key=lambda kv: kv[0][1]):
        out.append(ReleaseInput(hub_path, local, repo=repo, files=tuple(sorted(names))))
    for lane in _redline_lanes(root, version, redline_csv.stem):
        lane_dir = _redline_lane_dir(lane)
        out.append(
            ReleaseInput(
                f"outputs/redlines_0929_full/{lane_dir}/pdf_by_word",
                vendor_root / RUN_DIR / lane_dir / "pdf_by_word",
            )
        )
    return out


def build_release(
    root: Path,
    version: str,
    *,
    files_base: str,
    now: datetime | None = None,
    convert_csv: Path | None = None,
    redline_csv: Path | None = None,
    vendor_root: Path | None = None,
    kinds: tuple[ReleaseKind, ...] = ("convert", "redline"),
    limit: int | None = None,
) -> ReleaseBundle:
    """Build the versioned release shards and their local source map."""
    root = Path(root).resolve()
    vendor_root = Path(vendor_root or root).resolve()
    convert_csv = Path(convert_csv or CONVERT_SET)
    redline_csv = Path(redline_csv or REDLINE_SET)
    if not convert_csv.is_absolute():
        convert_csv = root / convert_csv
    if not redline_csv.is_absolute():
        redline_csv = root / redline_csv
    unknown = sorted(set(kinds) - {"convert", "redline"})
    if unknown:
        raise ValueError(f"unknown release case kind(s): {unknown}")

    shards: list[CaseShard] = []
    sources: list[ReleaseSource] = []
    used_lanes: list[_Lane] = []
    page_score_entries = 0
    if "convert" in kinds:
        if not convert_csv.is_file():
            raise RuntimeError(f"the fixed conversion set is missing: {convert_csv}")
        lanes = _conversion_lanes(root, version, convert_csv.stem)
        used_lanes.extend(lanes)
        cases, case_sources, entries = _conversion_cases(
            root, vendor_root, version, _read_csv(convert_csv), lanes, limit
        )
        page_score_entries += entries
        sources.extend(case_sources)
        shards.append(CaseShard(kind="conversion", group=f"cases/release-{version}", cases=cases))
    if "redline" in kinds:
        if not redline_csv.is_file():
            raise RuntimeError(f"the fixed redline set is missing: {redline_csv}")
        lanes = _redline_lanes(root, version, redline_csv.stem)
        used_lanes.extend(lanes)
        cases, case_sources, entries = _redline_cases(
            root, vendor_root, version, _read_csv(redline_csv), lanes, limit
        )
        page_score_entries += entries
        sources.extend(case_sources)
        shards.append(CaseShard(kind="redline", group=f"redlines/release-{version}", cases=cases))

    shards.sort(key=lambda shard: (shard.kind, shard.group))
    index = _index(version, _files_base(files_base), shards, now=now)
    if page_score_entries:
        page_score_message = (
            f"{page_score_entries} case/lane pair(s) carry per-page scores; "
            "the other lanes leave page_scores empty"
        )
    else:
        page_score_message = (
            "the set-scoped score files carry no per-page scores; "
            "page_scores is left empty (no values are invented)"
        )
    report: dict[str, object] = {
        "page_scores": {
            "available": bool(page_score_entries),
            "entries": page_score_entries,
            "message": page_score_message,
        },
        "lanes": {
            kind: sorted({lane.key for lane in used_lanes if lane.kind == kind}) for kind in kinds
        },
    }
    return ReleaseBundle(index=index, shards=shards, sources=tuple(sources), report=report)


def emit_release(
    root: Path,
    version: str,
    *,
    files_base: str,
    now: datetime | None = None,
    convert_csv: Path | None = None,
    redline_csv: Path | None = None,
    vendor_root: Path | None = None,
    kinds: tuple[ReleaseKind, ...] = ("convert", "redline"),
    limit: int | None = None,
) -> tuple[CasesIndex, list[CaseShard]]:
    """Emit the release-set shards and their cases index.

    ``files_base`` is the public Hugging Face ``resolve/<revision>/`` base the
    case's ``files`` paths resolve against.
    """
    bundle = build_release(
        root,
        version,
        files_base=files_base,
        now=now,
        convert_csv=convert_csv,
        redline_csv=redline_csv,
        vendor_root=vendor_root,
        kinds=kinds,
        limit=limit,
    )
    return bundle.index, bundle.shards
