"""Ready-made downloads of what the bench keeps on the Hugging Face hub (issue #79)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from neurotic_docx_bench import hub

ARCHIVE_REPO = "arthrod/neurotic_docx_bench-git-archive"


class GetError(Exception):
    """A download was refused; nothing was moved into the destination."""


@dataclass(frozen=True)
class Preset:
    name: str
    repo_id: str
    path: str
    dest: Path
    about: str
    exclude: tuple[str, ...] = ()


PRESETS: dict[str, Preset] = {}


@dataclass(frozen=True)
class RemoteFile:
    rel: str
    repo_path: str
    size: int
    sha256: str | None
    blob_id: str | None


@dataclass(frozen=True)
class GetReport:
    repo_id: str
    revision: str
    dest: Path
    n_files: int
    n_bytes: int
    to_download: int
    downloaded: int
    skipped: int
    replaced: int
    kept_local: tuple[str, ...]
    dry_run: bool


def free_bytes(path: Path) -> int:
    raise NotImplementedError


def staging_dir(dest: Path, revision: str) -> Path:
    raise NotImplementedError


def remote_files(api: Any, repo_id: str, revision: str, path: str) -> list[RemoteFile]:
    raise NotImplementedError


def get(
    preset: Preset,
    *,
    api: hub.HubApi,
    revision: str | None = None,
    dest: Path | None = None,
    include: Sequence[str] = (),
    on_conflict: str = "refuse",
    dry_run: bool = False,
    workers: int = 8,
) -> GetReport:
    raise NotImplementedError
