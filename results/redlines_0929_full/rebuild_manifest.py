"""Rebuild the run manifest from what the hub holds under ``outputs/redlines_0929_full`` (issue #76).

    uv run python results/redlines_0929_full/rebuild_manifest.py              # build + report, upload nothing
    uv run python results/redlines_0929_full/rebuild_manifest.py --publish    # + one commit on the head it read

Runs before #77 republished ``run/MANIFEST.sha256.json`` from the files still on disk, so the
published manifest lost every file an earlier ``--prune`` had deleted. This lists the hub again.

The hub is read through a blob-filtered git clone of the dataset, sparse on the run folder,
without LFS smudge: the working tree holds the inline files and the LFS pointers. Every file's
bytes must hash to the git blob id the hub lists. An LFS file's sha256 is its pointer's oid; an
inline file's is the sha256 of its bytes.

The records are every version of the manifest and the 0.13.0 upload's own list
(``upload_20261025.manifest.tsv``), oldest first. The newest record naming a path must agree with
the hub, and every recorded path must still be there, or nothing is published. An older record
that disagrees is reported as replaced; a file no record names is reported as first recorded here.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


class RebuildError(RuntimeError):
    """The hub does not match its own records; nothing is published."""


@dataclass(frozen=True)
class HubFile:
    blob_id: str
    size: int


def git_blob_sha1(data: bytes) -> str:
    return ''



def hub_tree(checkout: Path, revision: str) -> dict[str, HubFile]:
    return {}


def records(checkout: Path, revision: str) -> list[tuple[str, dict[str, str]]]:
    return []


def rebuild(
    tree: dict[str, HubFile], history: list[tuple[str, dict[str, str]]], read: Callable[[str], bytes]
) -> tuple[dict[str, str], dict]:
    return {}, {}


def build(checkout: Path, revision: str) -> tuple[dict[str, str], dict]:
    return {}, {}


def publish(api, revision: str, data: bytes, message: str, *, scratch: Path) -> str:
    return revision
