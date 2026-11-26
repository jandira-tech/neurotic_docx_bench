#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC

# SPDX-License-Identifier: AGPL-3.0-only

"""Task loading and validation.

Tasks reference the pilot's own `fixtures/` by relative path and sha256
(copies of jubarte-redlines' test fixtures, byte-identical to the pins);
the loader refuses to run a pilot whose fixture bytes have drifted, and
only hashes them.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from harness.models import FAMILIES, Family, Task, canonical_task_sha256


class TaskError(Exception):
    """A task set that cannot be used for a pilot."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_task(path: Path, repo_root: Path) -> tuple[Task, str]:
    """Load one task JSON and verify its fixture digest.

    Returns the task and its canonical sha256.
    """

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TaskError(f"{path}: unreadable task file: {exc}") from exc
    try:
        task = Task.model_validate(raw)
    except Exception as exc:  # pydantic surfaces every field problem
        raise TaskError(f"{path}: invalid task: {exc}") from exc

    fixture = repo_root / task.source.path
    if not fixture.is_file():
        raise TaskError(f"{task.id}: fixture {task.source.path} not in repository")
    actual = sha256_file(fixture)
    if actual != task.source.sha256:
        raise TaskError(
            f"{task.id}: fixture {task.source.path} sha256 drifted: "
            f"expected {task.source.sha256}, found {actual}"
        )
    return task, canonical_task_sha256(task)


def load_tasks(tasks_dir: Path, repo_root: Path) -> dict[str, Task]:
    """Load every task in `tasks_dir`, keyed by id, and sanity-check the set."""

    files = sorted(tasks_dir.glob("*.json"))
    if not files:
        raise TaskError(f"no task files in {tasks_dir}")

    tasks: dict[str, Task] = {}
    for path in files:
        task, _ = load_task(path, repo_root)
        if task.id in tasks:
            raise TaskError(f"duplicate task id {task.id}")
        tasks[task.id] = task

    counts = {family: 0 for family in FAMILIES}
    for task in tasks.values():
        counts[task.family] += 1
        if "{binary}" not in task.prompt or "{output}" not in task.prompt:
            raise TaskError(f"{task.id}: prompt must name {{binary}} and {{output}}")
        if "JUBARTE_RESULT" not in task.prompt:
            raise TaskError(f"{task.id}: prompt must explain the JUBARTE_RESULT marker")
        if not task.rubric:
            raise TaskError(f"{task.id}: at least one rubric item is required")
        if task.genuinely_unsupported != (task.family == "unsupported"):
            raise TaskError(
                f"{task.id}: genuinely_unsupported must match the unsupported family"
            )
    expected = {
        "exact_replace": 4,
        "multi_edit": 1,
        "received_redline": 2,
        "comments": 2,
        "template_flow": 2,
        "unsupported": 1,
    }
    for family in FAMILIES:
        if counts[family] != expected[family]:
            raise TaskError(
                f"family {family} must have {expected[family]} tasks, has {counts[family]}"
            )
    return tasks


def family_of(task_id: str, tasks: dict[str, Task]) -> Family:
    return tasks[task_id].family
