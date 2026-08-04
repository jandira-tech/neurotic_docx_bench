"""Change-region scoring (score_v2) and null-baseline skill score (PR3).

The parity-locked v1 metric spends most of its dynamic range on unchanged body text:
a do-nothing candidate (the base rendered unchanged) historically scored ~68 mean,
above half the leaderboard. Two parallel, informational metrics fix the range —
``score.py`` itself is never touched:

- ``null_score``: v1 ``overall_score`` of base-render vs oracle — what doing nothing
  earns for this pair. Cached in ``results/null_baseline.json`` keyed by content
  hashes, merged single-writer in the parent process (workers only compute).
- ``skill_score``: ``(overall - null) / (100 - null) * 100`` clamped to [-100, 100];
  ``None`` when the null is degenerate (base ≈ oracle). 0 = no better than nothing.
- ``score_v2``: ink-F1 with 2px tolerance computed ONLY inside the change-region mask
  (pixels where base and oracle renders differ, dilated), ink-weighted across pages.
  ``None`` when the mask is empty everywhere (no visible change — the roundtrip
  benchmark owns that case).

On this corpus most pairs chain two DIFFERENT fixture documents, so the change region
often spans most of the page and score_v2 tracks v1 closely; its value is on the
small-edit pairs (and the mutation probes) where v1's unchanged-text subsidy is
largest. Both metrics are informational: rankings stay on the ITT/pagefair scores.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy import ndimage
from skimage import color

# score.py is parity-locked; import its helpers rather than duplicating the ink model.
from neurotic_docx_bench.score import (
    ScoreConfig,
    _f1_with_tolerance,
    _ink_mask,
    _load_image,
    _resize_to_match,
)

_MASK_THRESHOLD = 0.08
_MASK_DILATE_PX = 8
_NULL_DEGENERATE_EPS = 1e-4


def skill_score(overall: float, null: float) -> float | None:
    """(overall - null) / (100 - null) * 100, clamped to [-100, 100].

    ``None`` when the null baseline is degenerate (≈100): base and oracle render
    identically, so "better than doing nothing" is undefined.
    """
    if null >= 100.0 - _NULL_DEGENERATE_EPS:
        return None
    raw = (overall - null) / (100.0 - null) * 100.0
    return float(max(-100.0, min(100.0, raw)))


def change_region_score(
    oracle_pages: list[Path],
    base_pages: list[Path],
    cand_pages: list[Path],
    config: ScoreConfig | None = None,
) -> float | None:
    """Ink-F1 (2px tolerance) restricted to where the base and oracle renders differ.

    Pages are paired by index up to the shortest list; oracle pages beyond the base
    render are treated as entirely changed (mask = full page). Returns the
    ink-weighted mean over pages with a non-empty mask, or ``None`` if every mask is
    empty.
    """
    cfg = config or ScoreConfig()
    weighted_sum = 0.0
    total_weight = 0
    n_scored = min(len(oracle_pages), len(cand_pages))
    for idx in range(n_scored):
        oracle_rgb = _load_image(oracle_pages[idx])
        cand_rgb = _resize_to_match(oracle_rgb, _load_image(cand_pages[idx]))
        oracle_gray = color.rgb2gray(oracle_rgb)
        cand_gray = color.rgb2gray(cand_rgb)

        if idx < len(base_pages):
            base_rgb = _resize_to_match(oracle_rgb, _load_image(base_pages[idx]))
            base_gray = color.rgb2gray(base_rgb)
            mask = np.abs(base_gray - oracle_gray) > _MASK_THRESHOLD
            if mask.any():
                # Iterated cross-dilation ~ diamond of radius N: same coverage intent
                # as a disk footprint at a fraction of the cost on full-page masks.
                mask = ndimage.binary_dilation(mask, iterations=_MASK_DILATE_PX)
        else:
            mask = np.ones_like(oracle_gray, dtype=bool)

        if not mask.any():
            continue
        ink_oracle = _ink_mask(oracle_gray, cfg.ink_min_size) & mask
        ink_cand = _ink_mask(cand_gray, cfg.ink_min_size) & mask
        weight = max(int(ink_oracle.sum()), 1)
        page_f1 = _f1_with_tolerance(ink_oracle, ink_cand, cfg.ink_tol_px)
        weighted_sum += page_f1 * weight
        total_weight += weight

    if total_weight == 0:
        return None
    return float(weighted_sum / total_weight * 100.0)


def resolve_base_pdfs(mapping_csvs: list[Path], base_pdf_dir: Path) -> dict[str, Path]:
    """``{pair_stem.lower(): <base_pdf_dir>/<base>.pdf}`` for every mapping row whose
    base PDF exists on disk. Keys are lowercased to match the score key space."""
    resolved: dict[str, Path] = {}
    for csv_path in mapping_csvs:
        if not csv_path.is_file():
            continue
        with csv_path.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                pair_stem = (row.get("pair_stem") or "").strip()
                base = (row.get("base") or "").strip()
                if not pair_stem or not base:
                    continue
                candidate = base_pdf_dir / f"{base}.pdf"
                if candidate.is_file():
                    resolved[pair_stem.lower()] = candidate
    return resolved


def _sha256_head(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def null_cache_key(oracle_pdf: Path, base_pdf: Path, dpi: int) -> str:
    """Content-addressed: survives renames, invalidates on oracle/base/dpi change."""
    return f"{_sha256_head(oracle_pdf)}:{_sha256_head(base_pdf)}:{dpi}"


def load_null_cache(path: Path) -> dict[str, float]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    return {str(k): float(v) for k, v in data.items()} if isinstance(data, dict) else {}


def merge_null_cache(path: Path, new_entries: dict[str, float]) -> None:
    """Single-writer merge (call from the PARENT process only — workers compute,
    the parent persists)."""
    if not new_entries:
        return
    merged = {**load_null_cache(path), **new_entries}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(merged, indent="\t", sort_keys=True) + "\n")
    tmp.replace(path)
