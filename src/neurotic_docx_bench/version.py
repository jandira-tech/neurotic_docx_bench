"""Bench version: stamped on every store line; the major.minor series joins the
comparability group so rows produced by different bench generations never rank
against each other.

Rows written before the stamp existed were all produced by the code released as
0.6.0, so an absent ``bench_version`` reads as the ``0.6`` series.
"""

from __future__ import annotations

import re
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _metadata_version

PACKAGE = "neurotic-docx-bench"
UNKNOWN = "0.0.0+unknown"
PRE_STAMP_SERIES = "0.6"
_SERIES = re.compile(r"^(\d+)\.(\d+)")


def _installed_version(name: str) -> str:
    return _metadata_version(name)


def bench_version() -> str:
    """The installed package version, or ``0.0.0+unknown`` outside an installation."""
    try:
        return _installed_version(PACKAGE)
    except PackageNotFoundError:
        return UNKNOWN


def series(full: str | None) -> str:
    """``major.minor`` of a version string; unstamped rows belong to ``0.6``."""
    if not full:
        return PRE_STAMP_SERIES
    m = _SERIES.match(full)
    return f"{m.group(1)}.{m.group(2)}" if m else PRE_STAMP_SERIES
