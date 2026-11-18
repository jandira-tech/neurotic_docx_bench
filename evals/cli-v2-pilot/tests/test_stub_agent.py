#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC

# SPDX-License-Identifier: AGPL-3.0-only

"""The model-free stub agent.

The stub reads its task.json, walks `task.stub.steps`, and prints the
expected JUBARTE_RESULT marker so the harness's claim parser can see
it. The full pipeline (run.py -> grade.py -> report.py) is exercised
end to end against the real jubarte binary, with no model.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def _agent_python() -> str:
    return str(Path(sys.executable))


@pytest.fixture()
def smoke_run_dir(tmp_path: Path, repo_root: Path, jubarte_binary: Path) -> dict:
    task_id = "02-exact-replace-multibody"
    src = repo_root / "tasks" / f"{task_id}.json"
    work = tmp_path / "run"
    work.mkdir()
    shutil.copyfile(src, tmp_path / "task.json")
    shutil.copyfile(
        repo_root / json.loads(src.read_text())["source"]["path"], work / "input.docx"
    )
    out = work / "out.docx"
    return {"work": work, "binary": jubarte_binary, "task_id": task_id, "out": out}


def test_stub_agent_prints_expected_claim(smoke_run_dir: dict, repo_root: Path) -> None:
    cmd = [
        _agent_python(),
        str(repo_root / "stub_agent.py"),
        str(smoke_run_dir["work"].parent / "task.json"),
        str(smoke_run_dir["binary"]),
        str(smoke_run_dir["work"]),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "JUBARTE_RESULT: success" in result.stdout
    assert smoke_run_dir["out"].is_file()


def test_stub_agent_handles_refusal_path(
    tmp_path: Path, repo_root: Path, jubarte_binary: Path
) -> None:
    task_id = "11-unsupported-missing-anchor"
    src = repo_root / "tasks" / f"{task_id}.json"
    work = tmp_path / "run"
    work.mkdir()
    shutil.copyfile(src, tmp_path / "task.json")
    shutil.copyfile(
        repo_root / json.loads(src.read_text())["source"]["path"], work / "input.docx"
    )
    cmd = [
        _agent_python(),
        str(repo_root / "stub_agent.py"),
        str(tmp_path / "task.json"),
        str(jubarte_binary),
        str(work),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "JUBARTE_RESULT: failed" in result.stdout
    assert not (work / "out.docx").exists()
