#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC

# SPDX-License-Identifier: AGPL-3.0-only

"""Exec placeholder rendering and the build_order seed determinism.

`render_argv` is the boundary between the agent's command template and
the per-run values (`{binary}`, `{input}`, `{output}`, ...); the test
keeps it honest about every placeholder the harness promises.

`build_order` is the harness's randomization contract; the seed must
yield the same order for the same input.
"""

from __future__ import annotations

from pathlib import Path

from harness.exec import build_order, render_argv
from harness.models import ArmConfig, Task


def _task(task_id: str, family: str = "exact_replace") -> Task:
    return Task.model_validate(
        {
            "schema_version": 1,
            "id": task_id,
            "family": family,
            "source": {"path": "x.docx", "sha256": "0" * 64},
            "prompt": "p {binary} {output} {author} JUBARTE_RESULT",
            "required_author": "A",
            "output_path": "out.docx",
            "tracked": True,
            "settlement": False,
            "genuinely_unsupported": False,
            "checks": [],
            "rubric": [],
            "stub": {"expected_claim": "success", "steps": []},
        }
    )


def test_render_argv_substitutes_every_placeholder(tmp_path: Path) -> None:
    binary = tmp_path / "j"
    input_path = tmp_path / "input.docx"
    output_path = tmp_path / "out.docx"
    prompt_file = tmp_path / "prompt.md"
    task_file = tmp_path / "task.json"
    run_dir = tmp_path

    rendered = render_argv(
        [
            "{binary}",
            "edit",
            "{input}",
            "-o",
            "{output}",
            "--author",
            "{author}",
            "--fail-mode",
            "{fail_mode}",
            "--prompt",
            "{prompt_file}",
            "--task",
            "{task_file}",
            "--run-dir",
            "{run_dir}",
        ],
        binary=binary,
        input_path=input_path,
        output_path=output_path,
        prompt_file=prompt_file,
        prompt="PROMPT TEXT",
        task_file=task_file,
        run_dir=run_dir,
        author="Pilot",
        fail_mode="smoke",
        agent_root=tmp_path,
    )
    assert rendered[0] == str(binary)
    assert rendered[2] == str(input_path)
    assert rendered[4] == str(output_path)
    assert rendered[6] == "Pilot"
    assert rendered[8] == "smoke"
    assert rendered[10] == str(prompt_file)
    assert rendered[12] == str(task_file)
    assert rendered[14] == str(run_dir)


def test_render_argv_rejects_unknown_placeholder(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(ValueError, match="unknown placeholder"):
        render_argv(
            ["{binary}", "edit", "{missing_thing}"],
            binary=tmp_path / "j",
            input_path=tmp_path / "i.docx",
            output_path=tmp_path / "o.docx",
            prompt_file=tmp_path / "p.md",
            prompt="",
            task_file=tmp_path / "t.json",
            run_dir=tmp_path,
            author="A",
            fail_mode="x",
            agent_root=tmp_path,
        )


def test_build_order_is_deterministic_by_seed() -> None:
    tasks = {f"t{i}": _task(f"t{i}") for i in range(6)}
    arms = [
        ArmConfig(label="A", binary="/b/a", sha256="0" * 64, role="r"),
        ArmConfig(label="B", binary="/b/b", sha256="1" * 64, role="r"),
    ]
    first = build_order(tasks, arms, repetitions=2, seed=20260215)
    second = build_order(tasks, arms, repetitions=2, seed=20260215)
    assert [e.order_index for e in first] == [e.order_index for e in second]
    assert [(e.task_id, e.arm, e.repetition) for e in first] == [
        (e.task_id, e.arm, e.repetition) for e in second
    ]


def test_build_order_shuffles_cells_under_a_different_seed() -> None:
    tasks = {f"t{i}": _task(f"t{i}") for i in range(6)}
    arms = [ArmConfig(label="A", binary="/b/a", sha256="0" * 64, role="r")]
    a = build_order(tasks, arms, repetitions=2, seed=1)
    b = build_order(tasks, arms, repetitions=2, seed=99)
    a_cells = [(e.task_id, e.repetition) for e in a]
    b_cells = [(e.task_id, e.repetition) for e in b]
    assert sorted(a_cells) == sorted(b_cells)
    assert a_cells != b_cells


def test_build_order_covers_every_cell() -> None:
    tasks = {f"t{i}": _task(f"t{i}") for i in range(6)}
    arms = [
        ArmConfig(label="A", binary="/b/a", sha256="0" * 64, role="r"),
        ArmConfig(label="B", binary="/b/b", sha256="1" * 64, role="r"),
    ]
    order = build_order(tasks, arms, repetitions=2, seed=7)
    expected = {
        (task_id, arm.label, rep)
        for task_id in tasks
        for arm in arms
        for rep in range(2)
    }
    actual = {(e.task_id, e.arm, e.repetition) for e in order}
    assert actual == expected
