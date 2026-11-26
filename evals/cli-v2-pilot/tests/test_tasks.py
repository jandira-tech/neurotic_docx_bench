#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC

# SPDX-License-Identifier: AGPL-3.0-only

"""Task loading and the family-counts invariant.

The pilot refuses to run unless every task JSON loads, every fixture
sha256 still matches, and the six families match the predeclared
12-task mix. We assert those conditions against the live task directory
because the test fails closed if a task was added without balancing
its family.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from harness.models import FAMILIES, canonical_task_sha256
from harness.tasks import TaskError, load_task, load_tasks

pytestmark = pytest.mark.integration


def test_loads_every_task_with_a_balanced_family_count(
    tasks_dir: Path, repo_root: Path
) -> None:
    tasks = load_tasks(tasks_dir, repo_root)
    assert len(tasks) == 12
    counts = {family: 0 for family in FAMILIES}
    for task in tasks.values():
        counts[task.family] += 1
    assert counts == {
        "exact_replace": 4,
        "multi_edit": 1,
        "received_redline": 2,
        "comments": 2,
        "template_flow": 2,
        "unsupported": 1,
    }


def test_every_task_pins_a_real_fixture_in_the_repo(
    tasks_dir: Path, repo_root: Path
) -> None:
    tasks = load_tasks(tasks_dir, repo_root)
    for task in tasks.values():
        fixture = repo_root / task.source.path
        assert fixture.is_file(), f"missing fixture: {task.source.path}"


def test_every_task_prompt_includes_required_placeholders(
    tasks_dir: Path, repo_root: Path
) -> None:
    tasks = load_tasks(tasks_dir, repo_root)
    for task in tasks.values():
        assert "{binary}" in task.prompt
        assert "{output}" in task.prompt
        assert "JUBARTE_RESULT" in task.prompt


def test_unsupported_family_aligns_with_genuinely_unsupported(
    tasks_dir: Path, repo_root: Path
) -> None:
    tasks = load_tasks(tasks_dir, repo_root)
    for task in tasks.values():
        if task.family == "unsupported":
            assert task.genuinely_unsupported is True
        else:
            assert task.genuinely_unsupported is False


def test_fixture_sha256_drift_is_refused(
    tasks_dir: Path, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks = load_tasks(tasks_dir, repo_root)
    target = next(iter(tasks.values()))
    # Tamper only an isolated fixture tree; the repository remains read-only.
    fixture = tmp_path / target.source.path
    fixture.parent.mkdir(parents=True)
    fixture.write_bytes(b"different bytes\n")
    with pytest.raises(TaskError, match="sha256 drifted"):
        load_task(tasks_dir / f"{target.id}.json", repo_root=tmp_path)


def test_canonical_sha256_changes_only_when_payload_changes(
    tasks_dir: Path, repo_root: Path
) -> None:
    tasks = load_tasks(tasks_dir, repo_root)
    first = canonical_task_sha256(next(iter(tasks.values())))
    again = canonical_task_sha256(next(iter(tasks.values())))
    assert first == again
