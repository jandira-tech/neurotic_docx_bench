"""Gate epsilon from the measured render noise floor (PR6).

Empirical finding (recorded, not assumed): double-rendering the same DOCX with the
same LibreOffice build produces BYTE-IDENTICAL rasters — the render noise floor on
this pipeline is exactly 0, and the historical fixed epsilon (1e-4) is already
correct. This module still earns its keep two ways:

- ``bench noise-floor`` re-measures and RECORDS the floor per environment
  (``results/noise_floor.json``). A nonzero sigma is itself an environment alarm —
  it means rendering stopped being deterministic here — complementing the canary,
  which only catches drift *between* environments.
- The gate epsilon becomes explicit and data-driven: ``eps = max(1e-4, 3*sigma)``
  from the recorded file, instead of a buried constant.
"""

from __future__ import annotations

import json
import math
import statistics
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_EPS = 1e-4


def stats_from_deltas(deltas: list[float]) -> dict[str, float | int]:
    if not deltas:
        return {"n": 0, "sigma": 0.0, "max_delta": 0.0}
    return {
        "n": len(deltas),
        "sigma": float(statistics.pstdev(deltas)),
        "max_delta": float(max(deltas)),
    }


def eps_from_file(path: Path) -> float:
    """``max(DEFAULT_EPS, 3*sigma)`` from a recorded noise-floor file; the default
    when the file is absent, unreadable, or carries a non-finite sigma."""
    if not path.is_file():
        return DEFAULT_EPS
    try:
        data = json.loads(path.read_text())
        sigma = float(data.get("sigma", 0.0))
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return DEFAULT_EPS
    if not math.isfinite(sigma) or sigma < 0:
        # Non-finite / negative would disable the gate or invert it — refuse them.
        return DEFAULT_EPS
    return max(DEFAULT_EPS, 3.0 * sigma)


def write_noise_floor(
    path: Path,
    deltas: list[float],
    *,
    lo_version: str | None,
    dpi: int,
) -> dict:
    record = {
        **stats_from_deltas(deltas),
        "deltas": [round(d, 6) for d in deltas],
        "lo_version": lo_version,
        "dpi": dpi,
        "measured_at": datetime.now(UTC).isoformat(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent="\t", sort_keys=True) + "\n")
    return record
