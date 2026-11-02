"""results/release/cases: the per-case browsers' release, emitted from the stores.

What the stores hold today (survey §1.1, ``docs/plans/reviews/plan3b-survey.md``)
covers two families, and only when their asset trees sit beside them:

* ``conversion/v1/*`` — ``results/docx_to_pdf_v1_89/{full,soffice_full}.json``
  (identity, pixel scores, times, failures, version pins) plus the family's
  WebP/PDF tree under ``results/docx_to_pdf_v1_89/assets/<state>/<case>/<engine>/``
  (the ``d2p_v1/v1`` prefix on R2);
* ``redline/ar/*`` — ``results/redlines_0929_split/scores.jsonl`` (per-pair rows,
  page counts, diagnostics) plus ``versions.json`` and the
  ``results/redlines_0929_split/assets/<action>/<pair>/<engine>/`` tree
  (the ``renew1030/ar`` prefix on R2).

A family is emitted only when the stores are **complete** for it: every case needs
its reference assets and every scored lane its pages. A partial family would
shadow the published data through the merge below, so an incomplete one is left
out whole and falls back to the legacy input. Everything else — the historical
conversion cohorts, the redline corpus groups, the Wordcraft cohort — has no
canonical store: their page/PDF asset trees, shown-page vectors, per-case SSIM,
reference-app notes, display version strings and cohort ``dropped`` curation
live only in the published pages. For those, ``cases_adapter.write_legacy``
produces the ``legacy_cases`` input **once** from the published pages
(``results/legacy_cases.jsonl``, committed when under 2 MB, else
``results/release/legacy_cases.jsonl``), and :func:`emit` merges it in. The
adapter stays the documented source for those families until the stores grow
the missing records; the acceptance test in ``tests/test_ledger_cases.py``
pins that split family by family.

``bench report`` writes what this module returns under ``results/release/``:
``cases/index.json`` plus one shard per group at ``shard_path(kind, group)``,
both through ``bench_ops.models.dumps_compact``.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from bench_ops.models import (
    Case,
    CaseShard,
    CasesIndex,
    MetricDiagnostics,
    ShardRef,
    dumps_compact,
    engines_from_cases,
    shard_path,
    validate_bundle,
)
from neurotic_docx_bench.ledger.scores import RESULTS_REPO_URL

#: The public R2 base every ``~/`` asset path in the release resolves against.
ASSETS_BASE = "https://pub-92c80eda1059428394970066c8500eda.r2.dev/"

#: Contract schema version (the release tag stays in the release manifest).
CONTRACT_VERSION = "1"

#: Engine display labels, as the published pages render them. Keys missing here
#: (lanes that only ever appear as dropped/superseded pins) default to the key.
LABELS: dict[str, str] = {
    "reference": "Word",
    "jubarte": "jubarte",
    "generated": "docxide-pdf",
    "libreoffice": "LibreOffice",
    "pymupdf": "PyMuPDF Pro",
    "minipdf": "MiniPdf (Rust)",
    "rdocx": "rdocx",
    "office2pdf": "office2pdf",
    "soffice": "LibreOffice (cohort)",
    "docxodus": "docxodus",
    "superdoc": "SuperDoc",
    "wordcraft": "Wordcraft",
}

#: Labels disambiguated so they stay unique when both kinds share one index:
#: the redline ``jubarte-rust`` lane must not wear the conversion lane's label.
LABEL_OVERRIDES: dict[str, str] = {"jubarte-rust": "jubarte (rust)"}


def labels() -> dict[str, str]:
    """The full label map handed to ``engines_from_cases``."""
    return {**LABELS, **LABEL_OVERRIDES}


# ---- the two store families -------------------------------------------------------------


def _webp_pages(directory: Path) -> list[int]:
    """The page numbers of ``page_NNN.webp`` files in one engine's asset dir."""
    numbers = []
    for p in directory.glob("page_*.webp"):
        if (m := re.fullmatch(r"page_(\d{3,})\.webp", p.name)) is not None:
            numbers.append(int(m.group(1)))
    return sorted(numbers)


def _lane_assets(prefix: str, directory: Path, shown: list[int]) -> tuple[list[str | None], int]:
    """One engine's shown-page vector and whole-document page count.

    ``page_counts`` is the document's true page count when a store row carries
    it; from an asset tree alone (the v1 family) the highest shown page number
    is the closest honest value — the trees hold only the shown pages.
    """
    have = set(_webp_pages(directory))
    pages: list[str | None] = [
        f"~/{prefix}/page_{p:03d}.webp" if p in have else None for p in shown
    ]
    return pages, max(have) if have else 0


# -- conversion/v1: results/docx_to_pdf_v1_89 + its asset tree

_V1_R2_PREFIX = "d2p_v1/v1"
_V1_LANE_OF_TOOL = {"soffice": "libreoffice"}  # the published lane name
_V1_REFERENCE_VERSION = "Word"
_V1_SET = "v1"
_ORACLE_APPS = {"microsoft_word": "Microsoft Word"}


def _v1_shards(root: Path) -> list[CaseShard] | None:
    """The ``v1/<state>`` shards, or None when the stores are incomplete for them."""
    run = root / "results" / "docx_to_pdf_v1_89"
    full_path = run / "full.json"
    if not full_path.is_file():
        return None
    full = json.loads(full_path.read_text(encoding="utf-8"))
    lo_path = run / "soffice_full.json"
    lo = json.loads(lo_path.read_text(encoding="utf-8")) if lo_path.is_file() else {"tools": {}}
    tools: dict[str, dict] = dict(full.get("tools") or {})
    if lo.get("tools", {}).get("soffice") is not None:
        tools["soffice"] = lo["tools"]["soffice"]
    assets = run / "assets"
    failures = {
        tool: {f["doc"]: f["error"] for f in row.get("generate_failures") or []}
        for tool, row in tools.items()
    }
    versions = {"reference": _V1_REFERENCE_VERSION}
    for tool, row in tools.items():
        versions[_V1_LANE_OF_TOOL.get(tool, tool)] = str(row.get("version", tool))
    reference_app = _ORACLE_APPS.get(str(full.get("oracle", "")), str(full.get("oracle", "")))
    by_group: dict[str, list[Case]] = {}
    for stem in full.get("stems") or []:
        state, name = str(stem).split("__", 1)
        case_id = name.split("_")[0]
        prefix = f"{_V1_R2_PREFIX}/{state}/{case_id}"
        base = assets / state / case_id
        shown = _webp_pages(base / "reference")
        if not shown:
            return None  # the reference assets are the family's spine: incomplete -> legacy
        pages: dict[str, list[str | None]] = {
            "reference": [f"~/{prefix}/reference/page_{p:03d}.webp" for p in shown]
        }
        page_counts: dict[str, int] = {"reference": shown[-1]}
        pdfs: dict[str, str] = {}
        if (base / "reference" / "pages.pdf").is_file():
            pdfs["reference"] = f"~/{prefix}/reference/pages.pdf"
        scores: dict[str, dict[str, float | None]] = {}
        times: dict[str, float] = {}
        errors: dict[str, str] = {}
        for tool, row in tools.items():
            lane = _V1_LANE_OF_TOOL.get(tool, tool)
            per_doc = row.get("per_doc") or {}
            failed = stem in failures.get(tool, {})
            lane_pages, lane_count = _lane_assets(f"{prefix}/{lane}", base / lane, shown)
            if failed or not lane_pages or all(p is None for p in lane_pages):
                if not failed and not lane_pages:
                    return None  # a scored lane without assets: incomplete -> legacy
                scores[lane] = {"pixel": float(per_doc.get(stem, 0.0))}
                if failed:
                    errors[lane] = failures[tool][stem]
                continue  # a failed lane carries no pages, counts or PDF
            pages[lane] = lane_pages
            page_counts[lane] = lane_count
            if (base / lane / "pages.pdf").is_file():
                pdfs[lane] = f"~/{prefix}/{lane}/pages.pdf"
            if stem in per_doc:
                scores[lane] = {"pixel": float(per_doc[stem])}
            seconds = (row.get("convert_seconds") or {}).get(stem)
            if seconds is not None:
                times[lane] = float(seconds)
        by_group.setdefault(f"v1/{state}", []).append(
            Case(
                kind="conversion",
                group=f"v1/{state}",
                case=case_id,
                pages=pages,
                page_counts=page_counts,
                scores=scores,
                times=times,
                versions=dict(versions),
                dropped=[],
                reference_app=reference_app,
                pdfs=pdfs,
                errors=errors,
                shown=list(shown),
                stem=str(stem),
                set=_V1_SET,
            )
        )
    if not by_group:
        return None
    return [
        CaseShard(kind="conversion", group=group, cases=cases)
        for group, cases in by_group.items()
    ]


# -- redline/ar: results/redlines_0929_split + its asset tree

_AR_R2_PREFIX = "renew1030/ar"
_AR_REFERENCE_VERSION = "Microsoft Word for Mac accept/reject"
_AR_REFERENCE_APP = "Microsoft Word for Mac"
_AR_MISSING_ERROR = "Recorded split-run failure: no scored Word PDF"
_WORD_IDENTITY_TOOL = "word-identity"  # the calibration lane; its rows are the reference


def _scaled(value: object) -> float | None:
    """A 0–1 store metric as the 0–100 case value, 1 decimal (published rounding)."""
    return None if value is None else round(float(value) * 100, 1)


def _ar_shards(root: Path) -> list[CaseShard] | None:
    """The ``ar/<action>`` shards, or None when the stores are incomplete for them."""
    store = root / "results" / "redlines_0929_split"
    scores_path = store / "scores.jsonl"
    if not scores_path.is_file():
        return None
    lines = [
        json.loads(ln)
        for ln in scores_path.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    by_tool_action = {
        (str(line["tool"]), str(line["action"])): line
        for line in lines
        if str(line.get("tool")) != _WORD_IDENTITY_TOOL
    }
    versions_path = store / "versions.json"
    pins = json.loads(versions_path.read_text(encoding="utf-8")) if versions_path.is_file() else {}
    missing_pins = sorted({tool for tool, _ in by_tool_action} - set(pins))
    if missing_pins:
        raise ValueError(f"{versions_path}: no version pin for {missing_pins}")
    assets = store / "assets"
    shards: list[CaseShard] = []
    for action in sorted({a for _, a in by_tool_action}):
        tools = sorted(tool for tool, a in by_tool_action if a == action)
        action_lines = {tool: by_tool_action[(tool, action)] for tool in tools}
        oracle_pages: dict[str, int] = {}
        pairs: set[str] = set()
        for line in action_lines.values():
            for key, row in (line.get("rows") or {}).items():
                oracle_pages[key] = int(row.get("page_count_oracle", 0))
            pairs |= set(line.get("rows") or {})
            pairs |= {str(k) for k in line.get("missing") or []}
        cases: list[Case] = []
        for pair in sorted(pairs):
            prefix = f"{_AR_R2_PREFIX}/{action}/{pair}"
            base = assets / action / pair
            shown = _webp_pages(base / "reference")
            if not shown:
                return None  # the reference assets are the family's spine
            pages: dict[str, list[str | None]] = {
                "reference": [f"~/{prefix}/reference/page_{p:03d}.webp" for p in shown]
            }
            page_counts: dict[str, int] = {
                "reference": oracle_pages.get(pair) or shown[-1]
            }
            pdfs: dict[str, str] = {}
            if (base / "reference" / "pages.pdf").is_file():
                pdfs["reference"] = f"~/{prefix}/reference/pages.pdf"
            scores: dict[str, dict[str, float | None]] = {}
            errors: dict[str, str] = {}
            diagnostics: dict[str, MetricDiagnostics] = {}
            for tool in tools:
                row = (action_lines[tool].get("rows") or {}).get(pair)
                if row is None:
                    scores[tool] = {"pixel": 0.0}
                    errors[tool] = _AR_MISSING_ERROR
                    page_counts[tool] = 0
                    pages[tool] = [None] * len(shown)
                    continue
                lane_pages, _lane_count = _lane_assets(
                    f"{prefix}/{tool}", base / tool, shown
                )
                if all(p is None for p in lane_pages):
                    return None  # a scored lane without assets: incomplete -> legacy
                pages[tool] = lane_pages
                page_counts[tool] = int(row.get("page_count_candidate") or 0) or max(
                    (shown[i] for i, v in enumerate(lane_pages) if v is not None), default=0
                )
                if (base / tool / "pages.pdf").is_file():
                    pdfs[tool] = f"~/{prefix}/{tool}/pages.pdf"
                pixel = row.get(
                    "overall_score_pagefair", row.get("overall_score", row.get("average_score"))
                )
                if pixel is None:
                    return None  # a scored row without a score: incomplete -> legacy
                scores[tool] = {"pixel": float(pixel)}
                if (j := _scaled(row.get("ink_jaccard"))) is not None:
                    scores[tool]["jaccard"] = j
                if (t := _scaled(row.get("text_boundary"))) is not None:
                    scores[tool]["text_boundary"] = t
                diagnostics[tool] = MetricDiagnostics(
                    ref_pages=int(row.get("page_count_oracle", 0)),
                    pages=int(row.get("page_count_candidate", 0)),
                    scored_pages=int(row.get("page_count", 0)),
                    max_break_drift=int(row.get("max_break_drift", 0)),
                )
            cases.append(
                Case(
                    kind="redline",
                    group=f"ar/{action}",
                    case=pair,
                    pages=pages,
                    page_counts=page_counts,
                    scores=scores,
                    times={},
                    versions={"reference": _AR_REFERENCE_VERSION}
                    | {tool: str(pins[tool]) for tool in tools},
                    dropped=[],
                    reference_app=_AR_REFERENCE_APP,
                    pdfs=pdfs,
                    errors=errors,
                    metric_diagnostics=diagnostics,
                    shown=list(shown),
                )
            )
        shards.append(CaseShard(kind="redline", group=f"ar/{action}", cases=cases))
    return shards or None


# ---- the release -------------------------------------------------------------------------


def _bundle(
    shards: list[CaseShard], *, now: datetime | None
) -> tuple[CasesIndex, list[CaseShard]]:
    shards = sorted(shards, key=lambda s: (s.kind, s.group))
    cases = [case for shard in shards for case in shard.cases]
    index = CasesIndex(
        version=CONTRACT_VERSION,
        generated=now or datetime.now(UTC),
        repo=RESULTS_REPO_URL,
        assets_base=ASSETS_BASE,
        engines=engines_from_cases(cases, labels()),
        groups=[
            ShardRef(
                kind=shard.kind,
                group=shard.group,
                count=len(shard.cases),
                path=shard_path(shard.kind, shard.group),
            )
            for shard in shards
        ],
    )
    validate_bundle(index, shards)
    return index, shards


def from_stores(root: Path, *, now: datetime | None = None) -> tuple[CasesIndex, list[CaseShard]]:
    """The families the stores emit on their own: complete ``v1`` and ``ar`` shards.

    A family whose stores are incomplete (no asset tree, a scored lane without
    pages) is left out whole — it reaches the release through the legacy input
    until the stores grow the missing records.
    """
    shards: list[CaseShard] = []
    for families in (_v1_shards(root), _ar_shards(root)):
        if families:
            shards.extend(families)
    return _bundle(shards, now=now)


def legacy_candidates(root: Path) -> list[Path]:
    """Where the adapter-produced legacy input may sit, in lookup order."""
    return [
        Path(root) / "results" / "legacy_cases.jsonl",
        Path(root) / "results" / "release" / "legacy_cases.jsonl",
    ]


def legacy_path(root: Path) -> Path:
    """The legacy input that exists, else the canonical (committed) location."""
    for candidate in legacy_candidates(root):
        if candidate.is_file():
            return candidate
    return legacy_candidates(root)[0]


def read_legacy(root: Path) -> list[CaseShard]:
    """The legacy input's shards: the published families the stores cannot derive."""
    path = legacy_path(root)
    if not path.is_file():
        return []
    return [
        CaseShard.model_validate_json(ln)
        for ln in path.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]


def emit(root: Path, *, now: datetime | None = None) -> tuple[CasesIndex, list[CaseShard]]:
    """The cases release: store families first, legacy families for the rest.

    The stores win per family: a legacy shard for a family the stores now cover
    is dropped, so a store regression can never hide behind the published copy.
    """
    _, store_shards = from_stores(root, now=now)
    covered = {(shard.kind, shard.group) for shard in store_shards}
    legacy = [
        shard for shard in read_legacy(root) if (shard.kind, shard.group) not in covered
    ]
    return _bundle(store_shards + legacy, now=now)


def release_texts(index: CasesIndex, shards: list[CaseShard]) -> dict[str, str]:
    """The release files' texts: the index plus one shard per group, compact."""
    by_ref = {(shard.kind, shard.group): shard for shard in shards}
    texts = {
        ref.path: dumps_compact(by_ref[ref.kind, ref.group]) for ref in index.groups
    }
    if texts:
        texts["cases/index.json"] = dumps_compact(index)
    return texts
