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

    @property
    def exit_code(self) -> int:
        return 1 if self.status == "fail" else 0


def gate(scores: dict[str, float], baseline_scores: dict[str, float] | None) -> GateResult:
    """Compare a run's per-doc scores to the accepted baseline.

    No baseline (first run) → pass. Otherwise aggregate regression → fail; else per-doc
    regression (of non-100 docs) → warn; else pass.
    """
    if not baseline_scores:
        return GateResult("pass", reason="no baseline (first accepted run)")

    cur = compute_aggregate(scores)
    base = compute_aggregate(baseline_scores)

    mean_down = cur.overall_mean < base.overall_mean - _EPS
    median_down = cur.overall_median < base.overall_median - _EPS
    if mean_down or median_down:
        parts = []
        if mean_down:
            parts.append(f"mean {base.overall_mean:.2f}→{cur.overall_mean:.2f}")
        if median_down:
            parts.append(f"median {base.overall_median:.2f}→{cur.overall_median:.2f}")
        return GateResult("fail", reason="aggregate regression: " + ", ".join(parts))

    # 100 is always a pass — never flag a doc that is at 100 now.
    regressed = sorted(
        doc
        for doc, score in scores.items()
        if doc in baseline_scores
        and score < baseline_scores[doc] - _EPS
        and score < 100.0 - _EPS
    )
    if regressed:
        return GateResult(
            "warn",
            regressed_docs=regressed,
            reason=f"{len(regressed)} document(s) regressed (aggregate held)",
        )
    return GateResult("pass", reason="no regression vs baseline")
