# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MAX_FILE_BYTES = 20_000_000


@dataclass(frozen=True)
class Document:
    id: str
    url: str
    path: Path | None
    sha256: str | None
    language: str | None = None
    type: str | None = None
    error: str | None = None
    review_id: str | None = None
    metadata: dict = field(default_factory=dict)
    security: dict = field(default_factory=dict)

    def public(self) -> dict[str, Any]:
        return {
            k: getattr(self, k)
            for k in ("id", "url", "sha256", "language", "type", "review_id", "metadata", "security")
        }


class ToolFailure(Exception):
    def __init__(self, message: str, *, status: str = "broken"):
        super().__init__(message[:1200])
        self.status = status


def result_id(run_id: str, sequence: int) -> str:
    return f"{run_id}-{sequence:09d}"


def batch_id(run_id: str, sequence: int, size: int) -> str:
    return f"{run_id}-batch-{(sequence - 1) // size + 1:06d}"


def queue_target(batch_size: int) -> int:
    return 2 * batch_size
