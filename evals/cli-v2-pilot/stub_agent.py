#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC

# SPDX-License-Identifier: AGPL-3.0-only

"""A model-free stub agent for the held-out pilot.

The stub reproduces the task's expected behavior using the current jubarte
CLI, so the full pipeline (run -> grade -> report) can be exercised
end to end without any model. It reads a private stub task record, walks the `stub.steps` block, renders the same placeholders
the agent receives (`{binary}`, `{input}`, `{output}`, `{author}`), and
prints the task's `expected_claim` as a `JUBARTE_RESULT:` line at the
end. It only handles the stub's small vocabulary of placeholder writers
(`stub-edit-generated`, `stub-copy-input`);
any other argv is passed to the binary verbatim.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def _render_argv(
    argv: list[str], *, binary: str, input_path: Path, output_path: Path, author: str
) -> list[str]:
    values = {
        "binary": binary,
        "input": str(input_path),
        "output": str(output_path),
        "run_dir": str(output_path.parent),
        "author": author,
    }
    rendered: list[str] = []
    for part in argv:
        rendered.append(part.format(**values))
    return rendered


def _run_subprocess(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True)


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("usage: stub_agent.py <task.json> <binary> <run_dir>", file=sys.stderr)
        return 2
    task_path = Path(argv[1]).resolve()
    binary = argv[2]
    run_dir = Path(argv[3]).resolve()

    task = json.loads(task_path.read_text(encoding="utf-8"))
    expected_claim = task["stub"]["expected_claim"]
    steps = task["stub"]["steps"]
    author = task["required_author"]
    input_path = run_dir / "input.docx"
    output_path = run_dir / task["output_path"]

    for step in steps:
        rendered = _render_argv(
            step["argv"],
            binary=binary,
            input_path=input_path,
            output_path=output_path,
            author=author,
        )
        if rendered[0] == "stub-edit-generated":
            plan_path = Path(rendered[1])
            plan = json.loads(plan_path.read_text())
            if plan["schema_version"] != 2 or not plan.get("source", {}).get("sha256"):
                raise ValueError(
                    "template generator did not produce a source-bound PlanV2"
                )
            changed = set()
            for row in plan["operations"]:
                pid = row["target"]["short_id"]
                if pid in task["expected_paragraphs"]:
                    row["text"] = task["expected_paragraphs"][pid]
                    changed.add(pid)
            if changed != set(task["expected_paragraphs"]):
                raise ValueError("generated rows do not cover the requested edits")
            plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
            continue
        if rendered[0] == "stub-copy-input":
            shutil.copyfile(rendered[1], rendered[2])
            continue
        result = _run_subprocess(rendered, cwd=run_dir)
        # If the plan step names an output, that step's outcome matters.
        expected_rc = step.get("expect_rc", 0)
        if result.returncode != expected_rc:
            print(
                f"stub step failed (expected rc={expected_rc}, got {result.returncode}): "
                f"{rendered}\nstdout: {result.stdout}\nstderr: {result.stderr}",
                file=sys.stderr,
            )
            return 1

    print(f"JUBARTE_RESULT: {expected_claim}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
