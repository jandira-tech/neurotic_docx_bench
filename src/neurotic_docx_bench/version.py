"""Bench version: stamped on every store line; the major.minor series joins the
comparability group so rows produced by different bench generations never rank
against each other.

Rows written before the stamp existed were all produced by the code released as
0.6.0, so an absent ``bench_version`` reads as the ``0.6`` series.
"""

from __future__ import annotations

import re
import tomllib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _metadata_version
from pathlib import Path

PACKAGE = "neurotic-docx-bench"
UNKNOWN = "0.0.0+unknown"
PRE_STAMP_SERIES = "0.6"
_SERIES = re.compile(r"^(\d+)\.(\d+)")


def _installed_version(name: str) -> str:
    return _metadata_version(name)


def _pyproject_path() -> Path:
    """The pyproject.toml of the checkout this module lives in (src layout).
    In an installation (site-packages) the path points at nothing useful and
    the read is simply refused."""
    return Path(__file__).resolve().parents[2] / "pyproject.toml"


def _checkout_version() -> str | None:
    """The checkout's own ``project.version``, for contexts that run ndb from
    ``src/`` without installing it (scripts/release_views.py's PEP 723
    environment, #134); None when this is not a checkout or it states no
    version."""
    try:
        with _pyproject_path().open("rb") as fh:
            found = tomllib.load(fh)["project"]["version"]
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError):
        return None
    return str(found) or None


def bench_version() -> str:
    """The installed package version; outside an installation, the checkout's
    pyproject.toml; ``0.0.0+unknown`` when neither exists."""
    try:
        return _installed_version(PACKAGE)
    except PackageNotFoundError:
        return _checkout_version() or UNKNOWN


def series(full: str | None) -> str:
    """``major.minor`` of a version string; unstamped rows belong to ``0.6``."""
    if not full:
        return PRE_STAMP_SERIES
    m = _SERIES.match(full)
    return f"{m.group(1)}.{m.group(2)}" if m else PRE_STAMP_SERIES
