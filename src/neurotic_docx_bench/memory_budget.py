"""Peak-memory budget per corpus size class + explicit wasm32-viability (TODO §1/§3).

The wasm32 lane has a hard **4 GiB** linear-memory ceiling. A real run-fragmented
diff (the 276k-run dissertation, ~9.8 MiB inputs) peaks ~11.6 GiB native, ~2.9x over
the ceiling — so wasm32 aborts on it. This module classifies a document by input size
into a size class, attaches a peak-memory budget per class, and emits an explicit
boolean ``wasm32_viable`` verdict (predicted/measured peak < 4 GiB).

Deliberately a *pure classifier plus an advisory gate*: it is NOT wired into the live
``gate`` path (a memory over-budget must not fail a real bench run). It reports the way
speed regressions surface — as a diff — reusing :class:`~neurotic_docx_bench.gate.GateResult`.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from neurotic_docx_bench.gate import GateResult

# The wasm32 linear-memory ceiling: 32-bit pointers cap the heap at 4 GiB.
WASM32_CEILING_BYTES = 4 * 1024**3

_MiB = 1024**2
_GiB = 1024**3


@dataclass(frozen=True)
class SizeClass:
    """One input-size bucket with its peak-memory budget and wasm32 verdict."""

    name: str
    max_input_bytes: int      # upper bound (exclusive) of this class's input size
    peak_budget_bytes: int    # acceptable peak-footprint envelope for docs in this class
    wasm32_viable: bool       # whether this class's budget fits under the 4 GiB ceiling


# Default size-class table, ordered by ascending input-size threshold. Budgets are
# rough peak-footprint envelopes anchored to the 2026-07-17 dissertation measurement
# (TODO §3): a ~9.8 MiB / 276k-run diff peaks ~11.6 GiB native — so the large/xlarge
# classes are wasm32-infeasible and their budgets sit above the 4 GiB ceiling.
DEFAULT_SIZE_CLASSES: tuple[SizeClass, ...] = (
    SizeClass("small", 1 * _MiB, 2 * _GiB, True),      # < 1 MiB   → ≤ 2 GiB, wasm32-ok
    SizeClass("medium", 5 * _MiB, 3 * _GiB, True),     # < 5 MiB   → ≤ 3 GiB, wasm32-ok
    SizeClass("large", 12 * _MiB, 6 * _GiB, False),    # < 12 MiB  → ≤ 6 GiB, wasm32-infeasible
    SizeClass("xlarge", sys.maxsize, 24 * _GiB, False),  # ≥ 12 MiB → ≤ 24 GiB, wasm32-infeasible
)


def classify(
    input_bytes: int, classes: tuple[SizeClass, ...] = DEFAULT_SIZE_CLASSES,
) -> SizeClass:
    """The first size class whose ``max_input_bytes`` bound ``input_bytes`` falls under.

    Falls back to the last (largest) class when nothing matches, so an unbounded
    top class need not carry a literal infinity.
    """
    for size_class in classes:
        if input_bytes < size_class.max_input_bytes:
            return size_class
    return classes[-1]


def wasm32_viable(predicted_peak_bytes: int) -> bool:
    """True iff a predicted/measured peak fits under the 4 GiB wasm32 ceiling."""
    return predicted_peak_bytes < WASM32_CEILING_BYTES


def _gib(n: int) -> str:
    return f"{n / _GiB:.2f} GiB"


def budget_gate(
    input_bytes: int,
    measured_peak_bytes: int,
    classes: tuple[SizeClass, ...] = DEFAULT_SIZE_CLASSES,
) -> GateResult:
    """Advisory peak-memory gate for one document's ``(input_bytes, measured_peak_bytes)``.

    - ``fail`` when the measured peak exceeds the size class's ``peak_budget_bytes``;
    - ``warn`` when it is within budget but still over the 4 GiB wasm32 ceiling;
    - ``pass`` otherwise.

    The ``wasm32_viable`` verdict for the measured peak is always reported in ``reason``.
    """
    size_class = classify(input_bytes, classes)
    verdict = f"wasm32_viable={wasm32_viable(measured_peak_bytes)}"
    peak = _gib(measured_peak_bytes)
    budget = _gib(size_class.peak_budget_bytes)
    if measured_peak_bytes > size_class.peak_budget_bytes:
        return GateResult(
            "fail",
            reason=f"peak {peak} exceeds {size_class.name} budget {budget} ({verdict})",
        )
    if not wasm32_viable(measured_peak_bytes):
        return GateResult(
            "warn",
            reason=(
                f"peak {peak} within {size_class.name} budget {budget} but over the "
                f"4 GiB wasm32 ceiling ({verdict})"
            ),
        )
    return GateResult(
        "pass",
        reason=f"peak {peak} within {size_class.name} budget {budget} ({verdict})",
    )


def size_classes_from_config(raw: list[dict[str, object]]) -> tuple[SizeClass, ...]:
    """Build a size-class table from a bench.yaml ``memory_budgets:`` list.

    Each entry is ``{name, max_input_bytes, peak_budget_bytes, wasm32_viable}``.
    An empty/absent list yields ``()`` — consumers fall back to ``DEFAULT_SIZE_CLASSES``.
    """
    classes: list[SizeClass] = []
    for entry in raw:
        classes.append(
            SizeClass(
                name=str(entry["name"]),
                max_input_bytes=int(entry["max_input_bytes"]),  # type: ignore[arg-type]
                peak_budget_bytes=int(entry["peak_budget_bytes"]),  # type: ignore[arg-type]
                wasm32_viable=bool(entry.get("wasm32_viable", False)),
            ),
        )
    return tuple(classes)
