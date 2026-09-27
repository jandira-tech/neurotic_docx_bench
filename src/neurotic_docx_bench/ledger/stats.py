"""Uncertainty for ranked tables.

Every vendor scores the same documents, so comparisons are paired: the statistic is
the median of per-document deltas on the shared document set, with a percentile
bootstrap interval (B resamples of the delta vector with replacement, fixed seed).
Two adjacent rows tie when that interval includes 0. Per-row intervals are the
percentile bootstrap of the row's own median. Deterministic by construction.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
from pydantic import BaseModel, ConfigDict

DEFAULT_REPS = 2000
DEFAULT_SEED = 42
MIN_PAIRED_DOCS = 20


class PairedDiff(BaseModel):
    model_config = ConfigDict(frozen=True)

    n: int
    median_delta: float
    ci_low: float
    ci_high: float
    wins: int
    losses: int
    ties: int


def bootstrap_median_ci(
    values: Sequence[float],
    *,
    reps: int = DEFAULT_REPS,
    seed: int = DEFAULT_SEED,
    alpha: float = 0.05,
) -> tuple[float, float] | None:
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return None
    if arr.size < 3:
        return (float(arr.min()), float(arr.max()))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, arr.size, size=(reps, arr.size))
    medians = np.median(arr[idx], axis=1)
    lo, hi = np.quantile(medians, [alpha / 2, 1 - alpha / 2])
    return (round(float(lo), 2), round(float(hi), 2))


def paired_median_diff(
    a: Mapping[str, float],
    b: Mapping[str, float],
    *,
    reps: int = DEFAULT_REPS,
    seed: int = DEFAULT_SEED,
    alpha: float = 0.05,
) -> PairedDiff | None:
    shared = sorted(set(a) & set(b))
    if len(shared) < MIN_PAIRED_DOCS:
        return None
    deltas = np.asarray([float(a[k]) - float(b[k]) for k in shared], dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, deltas.size, size=(reps, deltas.size))
    medians = np.median(deltas[idx], axis=1)
    lo, hi = np.quantile(medians, [alpha / 2, 1 - alpha / 2])
    eps = 1e-9
    return PairedDiff(
        n=int(deltas.size),
        median_delta=round(float(np.median(deltas)), 4),
        ci_low=round(float(lo), 4),
        ci_high=round(float(hi), 4),
        wins=int((deltas > eps).sum()),
        losses=int((deltas < -eps).sum()),
        ties=int((np.abs(deltas) <= eps).sum()),
    )


def tie_by_paired_bootstrap(
    a: Mapping[str, float],
    b: Mapping[str, float],
    *,
    reps: int = DEFAULT_REPS,
    seed: int = DEFAULT_SEED,
) -> bool:
    d = paired_median_diff(a, b, reps=reps, seed=seed)
    if d is None:
        return False
    return d.ci_low <= 0.0 <= d.ci_high
