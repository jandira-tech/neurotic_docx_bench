"""Scoring pipeline: match candidate redline PDFs to their Word-oracle redline PDFs,
rasterize both, and score each pair.

Matching identity (from the committed ``centralized_mapping.csv``): every base→next pair
has an oracle redline named ``<base>_<next>_redline.pdf``; a tool's candidate for the same
pair is ``<base>_<next>_<tool>_redline.pdf``. The shared key is therefore ``<base>_<next>``
— obtained by stripping the trailing ``_redline`` (oracle) or ``_<tool>_redline``
(candidate). The oracle dir ALSO contains non-redline base PDFs; those are excluded.
Collisions (two files mapping to one key) are raised, never silently last-wins.
"""

from __future__ import annotations

import shutil
import time
from collections.abc import Mapping
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import TypedDict

from skimage import color

# score.py is parity-locked (tests/test_parity.py); we import its helpers instead of
# duplicating the ink model, and never modify it.
from neurotic_docx_bench import raster
from neurotic_docx_bench.score import ScoreConfig, _ink_mask, _load_image, score_document

_REDLINE = "_redline"

# Benchmarks where a page-count mismatch is the tool's fault and must be penalized.
# The visual_* benchmarks compare renders from DIFFERENT engines, where repagination
# is endemic (90-99% of docs mismatch) — penalizing it there measures pagination
# agreement, not render quality, so their scores stay raw.
PAGEFAIR_BENCHMARKS = frozenset({"script_redlines", "accepted_changes", "roundtrip"})
SCORER_PAGEFAIR = "pagefair-v2"
SCORER_RAW = "v1"


class ScoreResult(TypedDict):
    overall_score: float
    overall_score_strict: float
    overall_score_drift: float
    page_count: int
    average_score: float
    average_score_strict: float
    average_score_drift: float
    min_score: float
    min_score_strict: float
    min_score_drift: float
    pages: list[dict[str, float | int | bool]]
    config: dict[str, float | dict[str, float]]
    page_count_oracle: int
    page_count_candidate: int
    page_count_mismatch: bool
    average_score_pagefair: float
    min_score_pagefair: float
    overall_score_pagefair: float
    raster_ns: int
    score_ns: int


def is_redline(stem: str) -> bool:
    """True for a redline filename (``…_redline``); base/source PDFs are not redlines."""
    return stem.lower().endswith(_REDLINE)


def redline_key(stem: str, tool: str | None = None) -> str:
    """Canonical ``<base>_<next>`` key for a redline filename.

    Oracle redline ``<base>_<next>_redline`` → ``<base>_<next>``.
    Tool candidate ``<base>_<next>_<tool>_redline`` (pass ``tool``) → ``<base>_<next>``.
    A non-redline stem is returned lower-cased unchanged.
    """
    s = stem.lower()
    if tool:
        suffix = f"_{tool.lower()}{_REDLINE}"
        if s.endswith(suffix):
            return s[: -len(suffix)]
    if s.endswith(_REDLINE):
        return s[: -len(_REDLINE)]
    return s


# Backwards-compatible alias for the previous public name.
def normalize_stem(stem: str) -> str:
    return redline_key(stem)


def _index_redlines(directory: Path, tool: str | None) -> dict[str, Path]:
    """Map ``<base>_<next>`` → redline PDF for every redline file in ``directory``.

    Non-redline PDFs are skipped. Two files mapping to the same key is a hard error
    (never silently drop one), so a mis-named corpus can't cause a wrong-oracle score.
    """
    index: dict[str, Path] = {}
    collisions: dict[str, list[str]] = {}
    for pdf in sorted(directory.glob("*.pdf")):
        if not is_redline(pdf.stem):
            continue
        key = redline_key(pdf.stem, tool)
        if key in index:
            collisions.setdefault(key, [index[key].name]).append(pdf.name)
        index[key] = pdf
    if collisions:
        detail = "; ".join(f"{k!r} <- {names}" for k, names in collisions.items())
        raise ValueError(f"redline key collision in {directory}: {detail}")
    return index


def match_by_stem(
    oracle_dir: Path,
    candidate_dir: Path,
    *,
    oracle_tool: str | None = None,
    candidate_tool: str | None = None,
) -> list[tuple[str, Path, Path]]:
    """Pair oracle and candidate redline PDFs by ``<base>_<next>`` key.

    ``candidate_tool`` is the tool token in the candidate filenames (e.g. ``jubarte``);
    with it, ``<base>_<next>_jubarte_redline`` pairs to oracle ``<base>_<next>_redline``.
    Returns ``[(key, oracle_pdf, candidate_pdf), ...]`` sorted by key, for keys in BOTH.
    """
    oracle = _index_redlines(oracle_dir, oracle_tool)
    candidate = _index_redlines(candidate_dir, candidate_tool)
    shared = sorted(oracle.keys() & candidate.keys())
    return [(key, oracle[key], candidate[key]) for key in shared]


def coverage(
    oracle_dir: Path,
    candidate_dir: Path,
    *,
    oracle_tool: str | None = None,
    candidate_tool: str | None = None,
) -> tuple[set[str], set[str]]:
    """(oracle-only keys, candidate-only keys) — documents present in one side but not
    the other, so a run can report what it failed to cover instead of silently dropping.
    """
    oracle = set(_index_redlines(oracle_dir, oracle_tool))
    candidate = set(_index_redlines(candidate_dir, candidate_tool))
    return oracle - candidate, candidate - oracle


def score_pdf_pair(
    oracle_pdf: Path,
    candidate_pdf: Path,
    work_dir: Path,
    *,
    dpi: int = 144,
    key: str | None = None,
) -> ScoreResult:
    """Rasterize both PDFs to PNGs under ``work_dir`` and return ``score_document``'s dict,
    augmented with page-count provenance.

    The lifted ``score_document`` scores only ``min(oracle, candidate)`` pages, so a
    page-count mismatch (a tool dropping/adding pages) would otherwise be invisible. We do
    NOT change the parity-locked score, but we record ``page_count_oracle``,
    ``page_count_candidate`` and ``page_count_mismatch`` so callers can surface/penalize it.
    """
    subdir = key or candidate_pdf.stem
    oracle_pages_dir = work_dir / subdir / "oracle"
    cand_pages_dir = work_dir / subdir / "candidate"
    # A reused work_dir must not leak stale page_*.png into the page lists — a stale
    # extra page would enter the pagefair aggregate at score 0.
    shutil.rmtree(oracle_pages_dir, ignore_errors=True)
    shutil.rmtree(cand_pages_dir, ignore_errors=True)
    t0 = time.perf_counter_ns()
    raster.rasterize_pdf(oracle_pdf, oracle_pages_dir, dpi=dpi)
    raster.rasterize_pdf(candidate_pdf, cand_pages_dir, dpi=dpi)
    t_raster = time.perf_counter_ns()
    oracle_pages = sorted(oracle_pages_dir.glob("page_*.png"))
    cand_pages = sorted(cand_pages_dir.glob("page_*.png"))
    result = score_document(oracle_pages, cand_pages)
    result["page_count_oracle"] = len(oracle_pages)  # type: ignore[assignment]
    result["page_count_candidate"] = len(cand_pages)  # type: ignore[assignment]
    result["page_count_mismatch"] = len(oracle_pages) != len(cand_pages)  # type: ignore[assignment]
    _add_pagefair(result, oracle_pages, cand_pages)
    t_score = time.perf_counter_ns()
    result["raster_ns"] = t_raster - t0  # type: ignore[assignment]
    result["score_ns"] = t_score - t_raster  # type: ignore[assignment]
    return result  # type: ignore[return-value]


def _unmatched_page_weight(png: Path) -> int:
    gray = color.rgb2gray(_load_image(png))
    ink = _ink_mask(gray, ScoreConfig().ink_min_size)
    return max(int(ink.sum()), 1)


def _add_pagefair(result: dict, oracle_pages: list[Path], cand_pages: list[Path]) -> None:
    """Fold unmatched pages (either side) into the doc aggregate at score 0.

    ``score_document`` silently truncates to ``min(oracle, candidate)`` pages, so a tool
    that drops or invents pages is invisible in ``overall_score``. The ``*_pagefair``
    fields re-derive the doc aggregate with every unmatched page contributing score 0 at
    a weight taken from its own ink (same ink model as the matched pages), using the same
    ``0.7*avg + 0.3*min`` combination as the parity-locked scorer. The min term is scaled
    by the MATCHED ink share rather than forced to 0, so a missing near-blank trailing
    page (a common pagination artifact) costs proportionally, while a missing dense page
    still collapses the score. Equal page counts reproduce the v1 values exactly.
    """
    n_matched = int(result["page_count"])
    unmatched = oracle_pages[n_matched:] + cand_pages[n_matched:]
    if not unmatched:
        avg = float(result["average_score"])
        min_pf = float(result["min_score"])
        overall = float(result["overall_score"])
    else:
        matched_w = [max(int(p["ink_area"]), 1) for p in result["pages"]]
        unmatched_w = [_unmatched_page_weight(p) for p in unmatched]
        total_w = sum(matched_w) + sum(unmatched_w)
        matched_share = sum(matched_w) / total_w
        avg = sum(p["score"] * w for p, w in zip(result["pages"], matched_w, strict=True)) / total_w
        min_pf = float(result["min_score"]) * matched_share
        overall = 0.7 * avg + 0.3 * min_pf
    result["average_score_pagefair"] = float(avg)
    result["min_score_pagefair"] = float(min_pf)
    result["overall_score_pagefair"] = float(overall)


def overall_from_result(result: Mapping[str, object]) -> float:
    """Doc-level score for ranking/gating: the pagefair value when present (new runs),
    else the raw ``overall_score`` (legacy dicts)."""
    value = result.get("overall_score_pagefair", result["overall_score"])
    return float(value)  # type: ignore[arg-type]


def raw_overall_from_result(result: Mapping[str, object]) -> float:
    """Raw ``overall_score``, ignoring pagefair — for the visual_* benchmarks, where
    cross-engine repagination makes page-count mismatch the norm, not a defect."""
    return float(result["overall_score"])  # type: ignore[arg-type]


def scorer_for_benchmark(benchmark: str) -> str:
    """Which scorer semantics a benchmark's ``scores`` dict carries — stamped into the
    JSONL line so pre/post-pagefair rows are distinguishable."""
    return SCORER_PAGEFAIR if benchmark in PAGEFAIR_BENCHMARKS else SCORER_RAW


def _score_one(args: tuple[str, Path, Path, Path, int]) -> tuple[str, ScoreResult]:
    key, oracle_pdf, cand_pdf, work_dir, dpi = args
    return key, score_pdf_pair(oracle_pdf, cand_pdf, work_dir, dpi=dpi, key=key)


def score_folders_full(
    oracle_dir: Path,
    candidate_dir: Path,
    work_dir: Path,
    *,
    dpi: int = 144,
    jobs: int = 4,
    candidate_tool: str | None = None,
) -> dict[str, ScoreResult]:
    """Score every matched pair; return ``{key: score_document_result}``.

    CPU-bound rasterize+score is fanned out with a **process** pool (PyMuPDF and the
    skimage scoring are not safe/parallel under threads); ``jobs<=1`` runs serially.
    """
    pairs = match_by_stem(oracle_dir, candidate_dir, candidate_tool=candidate_tool)
    if not pairs:
        return {}
    tasks = [(key, o, c, work_dir, dpi) for key, o, c in pairs]
    if jobs and jobs > 1 and len(tasks) > 1:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            scored = list(pool.map(_score_one, tasks))
    else:
        scored = [_score_one(t) for t in tasks]
    return dict(scored)


def score_folders(
    oracle_dir: Path,
    candidate_dir: Path,
    work_dir: Path,
    *,
    dpi: int = 144,
    jobs: int = 4,
    candidate_tool: str | None = None,
) -> dict[str, float]:
    """Score every matched pair; return ``{key: overall_score}`` (0–100)."""
    full_results = score_folders_full(
        oracle_dir,
        candidate_dir,
        work_dir,
        dpi=dpi,
        jobs=jobs,
        candidate_tool=candidate_tool,
    )
    return {k: overall_from_result(v) for k, v in full_results.items()}


def match_by_plain_stem(oracle_dir: Path, candidate_dir: Path) -> list[tuple[str, Path, Path]]:
    """Pair PDFs by filename stem with no redline-suffix logic (for roundtrip identity
    tests where both sides are plain ``<name>.pdf``).
    """
    oracle = {f.stem: f for f in sorted(oracle_dir.glob("*.pdf"))}
    candidate = {f.stem: f for f in sorted(candidate_dir.glob("*.pdf"))}
    shared = sorted(oracle.keys() & candidate.keys())
    return [(k, oracle[k], candidate[k]) for k in shared]


def score_folders_plain(
    oracle_dir: Path,
    candidate_dir: Path,
    work_dir: Path,
    *,
    dpi: int = 144,
    jobs: int = 4,
) -> dict[str, ScoreResult]:
    """Score every matched pair by plain filename stem (roundtrip identity test).

    Unlike ``score_folders_full``, this does NOT strip ``_redline`` / ``_<tool>_redline``
    suffixes — both oracle and candidate are matched by their raw stem.
    """
    pairs = match_by_plain_stem(oracle_dir, candidate_dir)
    if not pairs:
        return {}
    tasks = [(key, o, c, work_dir, dpi) for key, o, c in pairs]
    if jobs and jobs > 1 and len(tasks) > 1:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            scored = list(pool.map(_score_one, tasks))
    else:
        scored = [_score_one(t) for t in tasks]
    return dict(scored)


def _index_plain(directory: Path) -> dict[str, Path]:
    """Map lowercased stem → PDF for every PDF in ``directory`` (no redline filtering).

    Two files colliding on the case-insensitive key is a hard error, mirroring
    :func:`_index_redlines`'s collision guarantee.
    """
    index: dict[str, Path] = {}
    collisions: dict[str, list[str]] = {}
    for pdf in sorted(directory.glob("*.pdf")):
        key = pdf.stem.lower()
        if key in index:
            collisions.setdefault(key, [index[key].name]).append(pdf.name)
        index[key] = pdf
    if collisions:
        detail = "; ".join(f"{k!r} <- {names}" for k, names in collisions.items())
        raise ValueError(f"base key collision in {directory}: {detail}")
    return index


def match_base_to_candidate(oracle_dir: Path, candidate_dir: Path) -> list[tuple[str, Path, Path]]:
    """Pair oracle and candidate PDFs by plain lowercased stem, for ``visual_rendering``
    (base/source DOCX rendered through a viewer vs committed base PDFs).

    Unlike :func:`match_by_stem`, this does NOT require a ``_redline`` suffix —
    both sides are plain ``<name>.pdf``. Returns pairs for keys in BOTH dirs.
    """
    oracle = _index_plain(oracle_dir)
    candidate = _index_plain(candidate_dir)
    shared = sorted(oracle.keys() & candidate.keys())
    return [(key, oracle[key], candidate[key]) for key in shared]


def score_folders_base(
    oracle_dir: Path, candidate_dir: Path, work_dir: Path, *, dpi: int = 144, jobs: int = 4,
) -> dict[str, ScoreResult]:
    """Score every matched base pair (visual_rendering).

    See :func:`match_base_to_candidate` for the pairing rule (plain lowercased stem,
    no redline-suffix logic — unlike :func:`score_folders_full`).
    """
    pairs = match_base_to_candidate(oracle_dir, candidate_dir)
    if not pairs:
        return {}
    tasks = [(key, o, c, work_dir, dpi) for key, o, c in pairs]
    if jobs and jobs > 1 and len(tasks) > 1:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            scored = list(pool.map(_score_one, tasks))
    else:
        scored = [_score_one(t) for t in tasks]
    return dict(scored)


# Suffixes used by the accepted-changes pairing (visual_accepted_changes).
# Oracle PDFs: <base>_<next>[_word]_redline_accepted.pdf
# Candidate PDFs (rendered from docx_accepted_word DOCX): <base>_<next>_redline.pdf
_ACCEPTED_SUFFIX = "_accepted"
_WORD_REDLINE = "_word_redline"
_REDLINE = "_redline"


def accepted_key(stem: str) -> str:
    """Canonical ``<base>_<next>`` key for an accepted-changes filename.

    Strips ``_accepted`` then ``_word_redline`` (oracle) or ``_redline``
    (candidate). Returns the stem lowercased with those suffixes removed.
    A stem that matches neither suffix is returned lowercased unchanged.
    """
    s = stem.lower()
    s = s.removesuffix(_ACCEPTED_SUFFIX)
    if s.endswith(_WORD_REDLINE):
        s = s[: -len(_WORD_REDLINE)]
    elif s.endswith(_REDLINE):
        s = s[: -len(_REDLINE)]
    return s


def _index_accepted(directory: Path) -> dict[str, Path]:
    """Map ``<base>_<next>`` → accepted PDF for every file in ``directory``.

    The accepted corpus can carry BOTH naming variants of the same pair
    (``<key>_redline`` and ``<key>_word_redline``). The oracle set is built
    exclusively from the ``_word_redline`` capture, so when both variants are
    present the ``_word_redline`` file is the provenance-matching one and wins
    deterministically. A collision between files of the SAME variant is still a
    hard error, mirroring :func:`_index_redlines`'s guarantee.
    """

    def rank(stem: str) -> int:
        return 1 if stem.lower().removesuffix(_ACCEPTED_SUFFIX).endswith(_WORD_REDLINE) else 0

    index: dict[str, Path] = {}
    collisions: dict[str, list[str]] = {}
    for pdf in sorted(directory.glob("*.pdf")):
        key = accepted_key(pdf.stem)
        if key in index:
            existing_rank, new_rank = rank(index[key].stem), rank(pdf.stem)
            if existing_rank == new_rank:
                collisions.setdefault(key, [index[key].name]).append(pdf.name)
            elif new_rank > existing_rank:
                index[key] = pdf
            continue
        index[key] = pdf
    if collisions:
        detail = "; ".join(f"{k!r} <- {names}" for k, names in collisions.items())
        raise ValueError(f"accepted key collision in {directory}: {detail}")
    return index


def match_accepted_to_candidate(
    oracle_dir: Path, candidate_dir: Path,
) -> list[tuple[str, Path, Path]]:
    """Pair accepted-oracle and candidate PDFs by ``<base>_<next>`` key.

    Oracle: ``<base>_<next>[_word]_redline_accepted`` (in pdf_accepted_word).
    Candidate: ``<base>_<next>_redline`` (rendered from docx_accepted_word DOCX).
    Returns pairs for keys in BOTH dirs.
    """
    oracle = _index_accepted(oracle_dir)
    candidate = _index_accepted(candidate_dir)
    shared = sorted(oracle.keys() & candidate.keys())
    return [(key, oracle[key], candidate[key]) for key in shared]


def score_folders_accepted(
    oracle_dir: Path, candidate_dir: Path, work_dir: Path, *, dpi: int = 144, jobs: int = 4,
) -> dict[str, ScoreResult]:
    """Score every matched accepted-changes pair (visual_accepted_changes).

    See :func:`match_accepted_to_candidate` for the pairing rule.
    """
    pairs = match_accepted_to_candidate(oracle_dir, candidate_dir)
    if not pairs:
        return {}
    tasks = [(key, o, c, work_dir, dpi) for key, o, c in pairs]
    if jobs and jobs > 1 and len(tasks) > 1:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            scored = list(pool.map(_score_one, tasks))
    else:
        scored = [_score_one(t) for t in tasks]
    return dict(scored)
