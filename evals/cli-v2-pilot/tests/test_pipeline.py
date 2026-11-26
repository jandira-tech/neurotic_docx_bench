#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC

# SPDX-License-Identifier: AGPL-3.0-only

"""End-to-end pipeline: run.py -> grade.py -> report.py.

The harness's contract is "the same model, the same harness, two
arms; missing artifacts stay in the denominator." The integration
test exercises the contract end to end against the stub agent and the
real jubarte binary, with one repetition. Two arms, twelve tasks,
one repetition each = 24 runs.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture()
def smoke_pilot(tmp_path: Path, repo_root: Path, jubarte_binary: Path) -> dict:
    return {"root": repo_root, "runs": tmp_path / "pilot", "bin": jubarte_binary}


def _python() -> str:
    return sys.executable


def _run(cmd: list[str], cwd: Path) -> None:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    assert result.returncode == 0, (
        f"command failed: {cmd}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_full_pipeline_runs_24_runs_and_grades_each(smoke_pilot: dict) -> None:
    root = smoke_pilot["root"]
    pkg = root
    runs_root = smoke_pilot["runs"]

    # The pilot's run.py is invoked with the same binary for both arms;
    # the v2 arm is a future input.
    _run(
        [
            _python(),
            str(pkg / "run.py"),
            "--arm-a",
            str(smoke_pilot["bin"]),
            "--arm-b",
            str(smoke_pilot["bin"]),
            "--agent",
            str(pkg / "stub-agent.json"),
            "--runs-root",
            str(runs_root),
            "--repetitions",
            "1",
            "--seed",
            "20260215",
        ],
        cwd=pkg,
    )

    assert (runs_root / "config.json").is_file()
    runs_path = runs_root / "runs.jsonl"
    runs_records = [
        json.loads(line) for line in runs_path.read_text().splitlines() if line.strip()
    ]
    assert len(runs_records) == 24

    # Every run must have a captured claim (the stub prints one) and
    # either an artifact path or a clean refusal record.
    for record in runs_records:
        assert record["claim"] is not None, record

    _run(
        [
            _python(),
            str(pkg / "grade.py"),
            "--runs-root",
            str(runs_root),
            "--tasks-dir",
            str(pkg / "tasks"),
            "--repo-root",
            str(root),
            "--grader-binary",
            str(smoke_pilot["bin"]),
        ],
        cwd=pkg,
    )
    grades = [
        json.loads(line)
        for line in (runs_root / "grades.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert len(grades) == 24

    # Stub produces a faithful reproduction of every task: tool, task,
    # and claim axes all accurate on every supported run.
    for grade in grades:
        assert grade["tool_correctness_overall"] is True, grade
        assert grade["task_completion_overall"] is True, grade
        assert grade["claim_accuracy"] == "accurate", grade

    # And the report writes without crashing.
    _run(
        [_python(), str(pkg / "report.py"), "--runs-root", str(runs_root)],
        cwd=pkg,
    )


def test_run_with_two_repetitions_yields_48_runs(smoke_pilot: dict) -> None:
    root = smoke_pilot["root"]
    pkg = root
    runs_root = smoke_pilot["runs"]
    _run(
        [
            _python(),
            str(pkg / "run.py"),
            "--arm-a",
            str(smoke_pilot["bin"]),
            "--arm-b",
            str(smoke_pilot["bin"]),
            "--agent",
            str(pkg / "stub-agent.json"),
            "--runs-root",
            str(runs_root),
            "--repetitions",
            "2",
            "--seed",
            "20260215",
        ],
        cwd=pkg,
    )
    n = sum(
        1
        for line in (runs_root / "runs.jsonl").read_text().splitlines()
        if line.strip()
    )
    assert n == 48


def test_report_emits_a_markdown_summary(smoke_pilot: dict) -> None:
    root = smoke_pilot["root"]
    pkg = root
    runs_root = smoke_pilot["runs"]
    _run(
        [
            _python(),
            str(pkg / "run.py"),
            "--arm-a",
            str(smoke_pilot["bin"]),
            "--arm-b",
            str(smoke_pilot["bin"]),
            "--agent",
            str(pkg / "stub-agent.json"),
            "--runs-root",
            str(runs_root),
            "--repetitions",
            "1",
            "--seed",
            "1",
        ],
        cwd=pkg,
    )
    _run(
        [
            _python(),
            str(pkg / "grade.py"),
            "--runs-root",
            str(runs_root),
            "--tasks-dir",
            str(pkg / "tasks"),
            "--repo-root",
            str(root),
            "--grader-binary",
            str(smoke_pilot["bin"]),
        ],
        cwd=pkg,
    )
    out = runs_root / "report.md"
    _run(
        [
            _python(),
            str(pkg / "report.py"),
            "--runs-root",
            str(runs_root),
            "--output",
            str(out),
        ],
        cwd=pkg,
    )
    text = out.read_text(encoding="utf-8")
    assert "# Held-out pilot report" in text
    assert "Tool correctness, task completion, and claim accuracy" in text
    assert "unsupported" in text
    assert "right-censored" in text.lower()
