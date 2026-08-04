"""Pass/fail gating (PLAN §8).

- **100 is always a pass.** A doc (or whole tool) at 100 is never flagged.
- **Per-document decrease** vs the accepted baseline → **WARNING** (names the docs; does
  not fail the build).
- **Aggregate decrease** (overall_mean or overall_median down vs baseline) → **FAIL**
  (non-zero exit).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from neurotic_docx_bench.aggregate import compute_aggregate

_EPS = 1e-4

Status = Literal["pass", "warn", "fail"]


@dataclass(frozen=True)
class GateResult:
    status: Status
    regressed_docs: list[str] = field(default_factory=list)
    reason: str = ""
    # Doc keys present on only one side of the comparison (corpus-regime drift:
    # e.g. a 403-doc snapshot vs a 383-doc post-holdout run). The aggregates are
    # compared over the intersection only; these counts make the drift visible.
    n_only_baseline: int = 0
    n_only_current: int = 0

    @property
    def exit_code(self) -> int:
        return 1 if self.status == "fail" else 0


def gate(
    scores: dict[str, float],
    baseline_scores: dict[str, float] | None,
    *,
    eps: float | None = None,
) -> GateResult:
    """Compare a run's per-doc scores to the accepted baseline.

    No baseline (first run) → pass. Otherwise aggregate regression → fail; else per-doc
    regression (of non-100 docs) → warn; else pass. ``eps`` is the regression
    threshold — callers derive it from the recorded render noise floor
    (``noise_floor.eps_from_file``); default is the historical 1e-4.

    Both the aggregate and per-doc comparisons run over the INTERSECTION of doc
    keys: a snapshot accepted under a different corpus regime (403-doc
    pre-holdout vs 383-doc post-holdout) must not manufacture a regression out
    of the key-set change itself. Keys present on only one side are counted and
    reported in the reason; disjoint key sets are a warn (nothing comparable),
    never a silent pass or a spurious fail.
    """
    if not baseline_scores:
        return GateResult("pass", reason="no baseline (first accepted run)")
    threshold = _EPS if eps is None else eps

    shared = scores.keys() & baseline_scores.keys()
    n_only_baseline = len(baseline_scores.keys() - shared)
    n_only_current = len(scores.keys() - shared)
    key_note = (
        f" [{len(shared)} shared doc(s); {n_only_baseline} baseline-only, "
        f"{n_only_current} current-only]"
        if (n_only_baseline or n_only_current)
        else ""
    )
    if not shared:
        if not scores:
            # A total wipeout (every doc failed to score) is a regression, not
            # corpus drift — the disjoint-warn below is for key-set changes,
            # and must not let a crash-on-everything release through at exit 0.
            return GateResult(
                "fail",
                reason="current run scored no docs (wipeout) vs a non-empty baseline"
                + key_note,
                n_only_baseline=n_only_baseline,
                n_only_current=n_only_current,
            )
        return GateResult(
            "warn",
            reason="no shared docs with baseline — aggregate not comparable" + key_note,
            n_only_baseline=n_only_baseline,
            n_only_current=n_only_current,
        )

    cur = compute_aggregate({k: scores[k] for k in shared})
    base = compute_aggregate({k: baseline_scores[k] for k in shared})

    mean_down = cur.overall_mean < base.overall_mean - threshold
    median_down = cur.overall_median < base.overall_median - threshold
    if mean_down or median_down:
        parts = []
        if mean_down:
            parts.append(f"mean {base.overall_mean:.2f}→{cur.overall_mean:.2f}")
        if median_down:
            parts.append(f"median {base.overall_median:.2f}→{cur.overall_median:.2f}")
        return GateResult(
            "fail",
            reason="aggregate regression: " + ", ".join(parts) + key_note,
            n_only_baseline=n_only_baseline,
            n_only_current=n_only_current,
        )

    # 100 is always a pass — never flag a doc that is at 100 now.
    regressed = sorted(
        doc
        for doc in shared
        if scores[doc] < baseline_scores[doc] - threshold
        and scores[doc] < 100.0 - _EPS
    )
    if regressed:
        return GateResult(
            "warn",
            regressed_docs=regressed,
            reason=f"{len(regressed)} document(s) regressed (aggregate held)" + key_note,
            n_only_baseline=n_only_baseline,
            n_only_current=n_only_current,
        )
    return GateResult(
        "pass",
        reason="no regression vs baseline" + key_note,
        n_only_baseline=n_only_baseline,
        n_only_current=n_only_current,
    )
