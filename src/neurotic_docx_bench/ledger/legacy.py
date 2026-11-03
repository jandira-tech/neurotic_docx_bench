"""Where the adapter-produced ``legacy_cases`` input may live.

This module deliberately has no third-party imports: both the release-views
flow (which has bench-ops) and ``bench cases snapshot-upload`` (which does not)
need the same two lookup locations.
"""

from __future__ import annotations

from pathlib import Path

LEGACY_NAME = "legacy_cases.jsonl"


def legacy_candidates(root: Path) -> list[Path]:
    """The legacy input's locations, in lookup order."""
    return [
        Path(root) / "results" / LEGACY_NAME,
        Path(root) / "results" / "release" / LEGACY_NAME,
    ]


def legacy_path(root: Path) -> Path:
    """The legacy input that exists, else the canonical (committed) location."""
    for candidate in legacy_candidates(root):
        if candidate.is_file():
            return candidate
    return legacy_candidates(root)[0]
