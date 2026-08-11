"""Regression ratchet + census checkpoint (execution contract C1/C2, stage S0.3).

Every lift table in the three jubarte plans is **gross** arithmetic: it computes a
stage against a frozen baseline as if every other document stands still. Each
document an earlier stage knocks from 100 to 99 raises the perfect-count
requirement by one, silently, and the ≈50 cluster the next stage is sized against
has already moved. C1 gates that with four ratchets; C2 re-measures the five
figures the next stage's arithmetic depends on. Both are pure functions over
recorded scores — this module renders nothing and runs no subprocess.

**Calling convention: pass ITT scores, failures zero-filled** (``RunSnapshot.
itt_scores`` does this). A perfect document that a stage turns into a crash would
otherwise leave the score map entirely and escape R-perfect and R-tail, tripping
only R-fail — the mildest of the four. Zero-filling puts it back in the comparison
at 0.0, where it belongs.
"""

from __future__ import annotations

import json
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from pathlib import Path

# The perfect band. MUST match ``aggregate.compute_aggregate``, which is what
# writes ``exact_100`` into every bench.jsonl line: a ratchet that disagreed with
# the recorded field could pass a stage while the published perfect count falls.
PERFECT_EPS = 1e-6

CLUSTER_LO = 40.0    # the ≈50 cluster is [40,60)
CLUSTER_HI = 60.0
ABOVE_92 = 92.0      # open band: exactly 92 is not above 92
NEAR_MISS_LO = 90.0  # near-miss pool is [90,100) — i.e. ≥ 90 and not perfect
MAX_TAIL_DROP = 10.0
POOL_SHIFT_LIMIT = 0.10  # C2: a stage's sizing table is void past this
ITT_N_DOCS = 763

# Binary floating point makes 92.3 - 82.3 = 10.000000000000014. Slack so arithmetic
# noise cannot manufacture an R-tail trip; it is not a tolerance on the rule.
_FP_SLACK = 1e-9


def is_perfect(score: float) -> bool:
    return score >= 100.0 - PERFECT_EPS


# ── C1: the four ratchets ────────────────────────────────────────────────────


@dataclass(frozen=True)
class Ratchet:
    """One C1 outcome. ``offenders`` is populated whether or not the ratchet
    passed: C1's deliberate exception is priced in enumeration ("silence is not
    permitted"), and R-92/R-fail gate a COUNT, so a stage can pass while still
    owing the report a list of what it broke."""

    name: str
    passed: bool
    offenders: tuple[str, ...]
    detail: str


@dataclass(frozen=True)
class RatchetReport:
    r_perfect: Ratchet
    r_92: Ratchet
    r_fail: Ratchet
    r_tail: Ratchet
    only_in_baseline: tuple[str, ...]
    only_in_candidate: tuple[str, ...]
    n_compared: int

    @property
    def ratchets(self) -> tuple[Ratchet, ...]:
        return (self.r_perfect, self.r_92, self.r_fail, self.r_tail)

    @property
    def tripped(self) -> tuple[Ratchet, ...]:
        return tuple(r for r in self.ratchets if not r.passed)

    @property
    def corpus_stable(self) -> bool:
        return not (self.only_in_baseline or self.only_in_candidate)

    @property
    def passed(self) -> bool:
        return not self.tripped and self.corpus_stable


def evaluate_ratchets(
    baseline_scores: Mapping[str, float],
    candidate_scores: Mapping[str, float],
    *,
    baseline_failures: Collection[str],
    candidate_failures: Collection[str],
) -> RatchetReport:
    """The four C1 ratchets between a stage's entry baseline and its exit run.

    - **R-perfect** — no document at 100 in the baseline may score < 100 (offenders:
      every fallen perfect).
    - **R-92** — ``count(score > 92)`` may not decrease (offenders: every document
      that left the band, enumerated even when risers offset the count).
    - **R-fail** — the failure count may not increase (offenders: newly failing
      documents; a one-for-one swap passes the count and is still enumerated).
    - **R-tail** — no document may drop more than 10 points.

    **Documents present on one side only** are excluded from all four comparisons
    and enumerated in ``only_in_baseline`` / ``only_in_candidate``. Two reasons to
    exclude rather than impute: imputing 0 would manufacture ratchet trips out of a
    corpus-regime change (the 403-doc pre-holdout vs 383-doc post-holdout drift that
    ``gate.gate`` already handles this way), and imputing the baseline score would
    hide a document that vanished. Excluding is not the same as forgiving, so
    ``RatchetReport.passed`` is False whenever either list is non-empty: C1 states
    its guarantees over the stage's entry corpus, and a changed corpus voids the
    comparison exactly as C2 voids a stale sizing table. Per-ratchet outcomes stay
    readable on the intersection so a reviewer can tell corpus drift from a real
    regression. A document that regressed *into a failure* is not corpus drift and
    must not land here — zero-fill it (see the module docstring).
    """
    common = sorted(set(baseline_scores) & set(candidate_scores))
    only_baseline = tuple(sorted(set(baseline_scores) - set(candidate_scores)))
    only_candidate = tuple(sorted(set(candidate_scores) - set(baseline_scores)))

    fallen_perfect = tuple(
        doc for doc in common
        if is_perfect(baseline_scores[doc]) and not is_perfect(candidate_scores[doc])
    )
    base_above = sum(1 for doc in common if baseline_scores[doc] > ABOVE_92)
    cand_above = sum(1 for doc in common if candidate_scores[doc] > ABOVE_92)
    left_92 = tuple(
        doc for doc in common
        if baseline_scores[doc] > ABOVE_92 >= candidate_scores[doc]
    )
    new_failures = tuple(sorted(set(candidate_failures) - set(baseline_failures)))
    big_drops = tuple(
        doc for doc in common
        if baseline_scores[doc] - candidate_scores[doc] > MAX_TAIL_DROP + _FP_SLACK
    )

    return RatchetReport(
        r_perfect=Ratchet(
            "R-perfect",
            not fallen_perfect,
            fallen_perfect,
            f"{len(fallen_perfect)} of {sum(1 for d in common if is_perfect(baseline_scores[d]))} "
            f"perfect documents fell",
        ),
        r_92=Ratchet(
            "R-92",
            cand_above >= base_above,
            left_92,
            f"above 92: {base_above} → {cand_above} ({cand_above - base_above:+d})",
        ),
        r_fail=Ratchet(
            "R-fail",
            len(set(candidate_failures)) <= len(set(baseline_failures)),
            new_failures,
            f"failures: {len(set(baseline_failures))} → {len(set(candidate_failures))}",
        ),
        r_tail=Ratchet(
            "R-tail",
            not big_drops,
            big_drops,
            f"{len(big_drops)} documents dropped more than {MAX_TAIL_DROP:g} points",
        ),
        only_in_baseline=only_baseline,
        only_in_candidate=only_candidate,
        n_compared=len(common),
    )


# ── C2: the census checkpoint ────────────────────────────────────────────────


@dataclass(frozen=True)
class Census:
    """The five C2 figures for one run. ``n_itt`` is the ITT denominator, not the
    number of scored documents — the median position is a property of the corpus."""

    n_scored: int
    n_itt: int
    cluster: tuple[str, ...]        # [40,60) membership, C2's "≈50 cluster"
    above_92: int
    near_miss: tuple[str, ...]      # [90,100) membership
    near_miss_at_or_below_92: int
    perfect: int

    @property
    def n_cluster(self) -> int:
        return len(self.cluster)

    @property
    def n_near_miss(self) -> int:
        return len(self.near_miss)

    @property
    def majority_position(self) -> int:
        """The rank that moves the median: a strict majority of the ITT corpus,
        ``n // 2 + 1`` — 382 of 763. Derived, so a corpus resize cannot leave a
        stale 382 behind in a stage table."""
        return self.n_itt // 2 + 1

    @property
    def shortfall_to_majority(self) -> int:
        """Documents still needed above 92 to carry the median there; 0 once met."""
        return max(0, self.majority_position - self.above_92)


def census(scores: Mapping[str, float], *, n_itt: int = ITT_N_DOCS) -> Census:
    """C2's post-stage re-measurement of a run's score distribution.

    Pass ITT scores (failures zero-filled): a failure is a document below every
    band, not a document outside the corpus. The bands are half-open and pinned to
    the recorded aggregates — ``perfect`` reproduces ``exact_100`` and
    ``perfect + n_near_miss`` reproduces ``at_least_90`` for the same run.
    """
    cluster = tuple(sorted(d for d, s in scores.items() if CLUSTER_LO <= s < CLUSTER_HI))
    near_miss = tuple(
        sorted(d for d, s in scores.items() if s >= NEAR_MISS_LO and not is_perfect(s))
    )
    return Census(
        n_scored=len(scores),
        n_itt=n_itt,
        cluster=cluster,
        above_92=sum(1 for s in scores.values() if s > ABOVE_92),
        near_miss=near_miss,
        near_miss_at_or_below_92=sum(1 for d in near_miss if scores[d] <= ABOVE_92),
        perfect=sum(1 for s in scores.values() if is_perfect(s)),
    )


@dataclass(frozen=True)
class CensusDelta:
    """Change in each C2 figure, plus the two readings of "the input pool changed"."""

    d_cluster: int
    d_above_92: int
    d_shortfall: int
    d_near_miss: int
    d_near_miss_at_or_below_92: int
    d_perfect: int
    entered_cluster: tuple[str, ...]
    left_cluster: tuple[str, ...]
    pool_shift_fraction: float
    pool_churn_fraction: float

    @property
    def sizing_void(self) -> bool:
        """C2: past a 10% change in the stage's input pool, its sizing table is void
        and must be recomputed before work starts."""
        return (
            abs(self.pool_shift_fraction) > POOL_SHIFT_LIMIT
            or self.pool_churn_fraction > POOL_SHIFT_LIMIT
        )


def census_delta(before: Census, after: Census) -> CensusDelta:
    """What one stage did to the census, and whether the next stage's table survives.

    Two fractions, because "the input pool changed by more than 10%" has two
    readings and only the pair is honest. ``pool_shift_fraction`` is the signed size
    change (the literal reading); ``pool_churn_fraction`` is the symmetric
    difference over the entry size, which catches a cluster that kept its size while
    swapping its members — the sizing table was built on the documents, not on the
    count. Either breaching 10% voids the table. With an empty entry cluster the
    shift is 0.0 if it stayed empty and infinite if it grew, since no proportional
    change from nothing is meaningful.
    """
    entered = tuple(d for d in after.cluster if d not in set(before.cluster))
    left = tuple(d for d in before.cluster if d not in set(after.cluster))

    if before.n_cluster:
        shift = (after.n_cluster - before.n_cluster) / before.n_cluster
        churn = len(entered + left) / before.n_cluster
    else:
        shift = churn = 0.0 if not after.n_cluster else float("inf")

    return CensusDelta(
        d_cluster=after.n_cluster - before.n_cluster,
        d_above_92=after.above_92 - before.above_92,
        d_shortfall=after.shortfall_to_majority - before.shortfall_to_majority,
        d_near_miss=after.n_near_miss - before.n_near_miss,
        d_near_miss_at_or_below_92=(
            after.near_miss_at_or_below_92 - before.near_miss_at_or_below_92
        ),
        d_perfect=after.perfect - before.perfect,
        entered_cluster=entered,
        left_cluster=left,
        pool_shift_fraction=shift,
        pool_churn_fraction=churn,
    )


# ── reading a recorded run ───────────────────────────────────────────────────


@dataclass(frozen=True)
class RunSnapshot:
    """One recorded ``results/bench.jsonl`` line, reduced to what C1/C2 need."""

    id_run: str
    vendor: str
    tool_version: str | None
    scores: dict[str, float]
    failure_docs: tuple[str, ...]
    itt_n_docs: int

    @property
    def itt_scores(self) -> dict[str, float]:
        """Scores with every failed document entered at 0.0 — the same intent-to-treat
        convention as ``aggregate.compute_aggregate_itt``: a document that scored keeps
        its score even if a failure record exists for it (non-fatal stage error)."""
        return {**{doc: 0.0 for doc in self.failure_docs if doc not in self.scores}, **self.scores}


def load_run(jsonl_path: Path, id_run: str) -> RunSnapshot | None:
    """The recorded run with this ``id_run``, or None when absent.

    Streams and pre-filters on the substring rather than going through
    ``emit.jsonl.read_lines``: the log is tens of MB of embedded per-doc detail and
    the ratchet only ever wants two lines out of it.
    """
    if not jsonl_path.is_file():
        return None
    with jsonl_path.open() as fh:
        for raw in fh:
            if id_run not in raw:
                continue
            line = json.loads(raw)
            if line.get("id_run") != id_run:
                continue
            scores = {str(k): float(v) for k, v in (line.get("scores") or {}).items()}
            return RunSnapshot(
                id_run=id_run,
                vendor=str(line.get("vendor", "")),
                tool_version=line.get("tool_version"),
                scores=scores,
                failure_docs=_failure_docs(line.get("failures")),
                itt_n_docs=int(line.get("itt_n_docs") or len(scores)),
            )
    return None


def _failure_docs(failures: object) -> tuple[str, ...]:
    """Deduped, sorted doc names from a line's ``failures`` list of
    ``{doc, stage, error}`` records; several stages can fail the same document."""
    if not isinstance(failures, list):
        return ()
    docs: set[str] = set()
    for record in failures:
        doc = record.get("doc") if isinstance(record, dict) else None
        if isinstance(doc, str):
            docs.add(doc)
    return tuple(sorted(docs))
