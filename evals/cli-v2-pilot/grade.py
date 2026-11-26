#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC

# SPDX-License-Identifier: AGPL-3.0-only

"""Three-axis grading for the held-out pilot.

For every run, this script writes one `GradeRecord` to the ledger:

* **tool_correctness** asks whether the artifact's tracked edits and
  comments realize the operations the agent claimed, or were correctly
  refused when refusal was the right answer. We grade this by running
  arm A's `jubarte read --json` and `jubarte validate` against the
  artifact and checking what actually happened in the docx package.
* **task_completion** asks whether the artifact satisfies the typed
  user requirements (text equality / containment / absence, revision
  and comment counts, expected-no-artifact). Rubric items stay
  `unassessed` unless an external grader fills them.
* **claim_accuracy** asks whether the agent's printed
  `JUBARTE_RESULT:` line matched the artifact and the checks.

Missing artifacts and right-censored runs stay in the denominator. The
artifact (when present) is always graded with arm A's binary, even if
arm B produced it; the grader does not depend on which arm ran.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from harness.grading import grade_one
from harness.ledger import read_jsonl, write_jsonl_atomic
from harness.models import GradeRecord, RunConfig, RunRecord, canonical_task_sha256
from harness.tasks import load_tasks, sha256_file


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="grade.py")
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--tasks-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument(
        "--grader-binary",
        type=Path,
        required=True,
        help="Path to arm A's jubarte binary (used for grading).",
    )
    args = parser.parse_args(argv)

    runs_root = args.runs_root.resolve()
    repo_root = args.repo_root.resolve()
    tasks = load_tasks(args.tasks_dir.resolve(), repo_root)
    grader_binary = args.grader_binary.resolve()

    config_path = runs_root / "config.json"
    if not config_path.is_file():
        print(f"missing {config_path}", file=sys.stderr)
        return 1
    config = RunConfig.model_validate_json(config_path.read_text(encoding="utf-8"))

    runs = [
        RunRecord.model_validate(row) for row in read_jsonl(runs_root / "runs.jsonl")
    ]
    # Verify the complete join before inspecting or publishing any grade.
    try:
        reference = next(a for a in config.arms if a.label == "A")
        if (
            grader_binary != Path(reference.binary).resolve()
            or sha256_file(grader_binary) != reference.sha256
        ):
            raise ValueError("grader differs from recorded reference arm A")
        for run in runs:
            task = tasks.get(run.task_id)
            if task is None or canonical_task_sha256(task) != run.task_sha256:
                raise ValueError(f"{run.run_id}: task hash differs")
            arm = next(a for a in config.arms if a.label == run.arm)
            if (
                run.pilot_id != config.pilot_id
                or run.arm_binary_path != arm.binary
                or run.arm_binary_sha256 != arm.sha256
                or sha256_file(Path(arm.binary)) != arm.sha256
            ):
                raise ValueError(f"{run.run_id}: arm identity differs")
            if not any(
                e.task_id == run.task_id
                and e.arm == run.arm
                and e.repetition == run.repetition
                and e.order_index == run.order_index
                for e in config.order
            ):
                raise ValueError(f"{run.run_id}: unscheduled cell")
            for path, digest in (
                (Path(run.input_path), run.input_sha256),
                (Path(run.prompt_path), run.prompt_sha256),
                (repo_root / task.source.path, task.source.sha256),
                (Path(run.stdout_path), run.stdout_sha256),
                (Path(run.stderr_path), run.stderr_sha256),
            ):
                if sha256_file(path) != digest:
                    raise ValueError(
                        f"{run.run_id}: recorded input/prompt/source/stream hash differs"
                    )
            if run.input_sha256 != task.source.sha256:
                raise ValueError(f"{run.run_id}: input differs from task")
            artifact = Path(run.artifact_path)
            if (
                artifact.resolve() != Path(run.declared_output_path).resolve()
                or artifact.is_file() != run.artifact_exists
                or (
                    run.artifact_exists and sha256_file(artifact) != run.artifact_sha256
                )
            ):
                raise ValueError(f"{run.run_id}: artifact identity differs")
    except (OSError, ValueError, StopIteration) as exc:
        print(f"refusing grade: {exc}", file=sys.stderr)
        return 1
    grades: list[GradeRecord] = []
    for run in runs:
        grades.append(
            grade_one(run, tasks[run.task_id], grader_binary, repo_root=repo_root)
        )

    write_jsonl_atomic(runs_root / "grades.jsonl", grades)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
