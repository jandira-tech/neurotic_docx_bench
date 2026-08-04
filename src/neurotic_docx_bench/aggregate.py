"""Aggregate a tool run's per-document scores into the distribution stats used in the
JSONL line (PLAN §7) and by the gate.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Aggregate:
    n_docs: int
    overall_mean: float
    overall_median: float
    exact_100: int
    at_least_90: int
    below_50: int
    min: float
    max: float
    std: float
    q1: float
    q3: float
    page_mean: float | None = None
    page_median: float | None = None

    def to_dict(self) -> dict[str, float | int | None]:
        return {k: v for k, v in asdict(self).items() if v is not None}


def _round(x: float, nd: int = 4) -> float:
    return round(float(x), nd)


def compute_aggregate(
    scores: dict[str, float],
    per_doc: Mapping[str, Mapping[str, object]] | None = None,
) -> Aggregate:
    """Compute distribution stats from a ``{doc: overall_score}`` map.

    If ``per_doc`` (``{doc: score_document_result}``) is supplied, also compute
    ``page_mean``/``page_median`` across every page of every document. ``exact_100``
    counts docs at 100 (within 1e-6); ``at_least_90`` counts ``>= 90``; ``below_50``
    counts ``< 50``. Empty input yields an all-zero aggregate.
    """
    values = list(scores.values())
    n = len(values)
    if n == 0:
        return Aggregate(0, 0.0, 0.0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0)

    quartiles = (
        statistics.quantiles(values, n=4, method="inclusive")
        if n >= 2
        else [values[0], values[0], values[0]]
    )

    page_mean = page_median = None
    if per_doc:
        page_scores = [
            float(page["score"])
            for result in per_doc.values()
            for page in result.get("pages", [])  # type: ignore[arg-type]
        ]
        if page_scores:
            page_mean = _round(statistics.mean(page_scores))
            page_median = _round(statistics.median(page_scores))

    return Aggregate(
        n_docs=n,
        overall_mean=_round(statistics.mean(values)),
        overall_median=_round(statistics.median(values)),
        exact_100=sum(1 for v in values if v >= 100.0 - 1e-6),
        at_least_90=sum(1 for v in values if v >= 90.0),
        below_50=sum(1 for v in values if v < 50.0),
        min=_round(min(values)),
        max=_round(max(values)),
        std=_round(statistics.pstdev(values)),
        q1=_round(quartiles[0]),
        q3=_round(quartiles[2]),
        page_mean=page_mean,
        page_median=page_median,
    )


def compute_aggregate_itt(
    scores: dict[str, float],
    failure_docs: Iterable[str],
    per_doc: Mapping[str, Mapping[str, object]] | None = None,
) -> Aggregate:
    """Intent-to-treat aggregate: every explicitly-failed doc scores 0.

    The completed-only aggregate silently rewards a tool for crashing on hard documents
    (the doc leaves the denominator). Here each unique failed doc that did not also
    produce a score enters at 0.0; a doc that scored keeps its score even if a failure
    record exists for it (non-fatal stage error). Failure docs are deduped.
    """
    zeroed = {doc: 0.0 for doc in set(failure_docs) if doc not in scores}
    return compute_aggregate({**scores, **zeroed}, per_doc=per_doc)
