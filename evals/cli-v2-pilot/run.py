#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC

# SPDX-License-Identifier: AGPL-3.0-only

"""The held-out pilot runner.

`run.py` drives the harness's execution core: every (task, arm,
repetition) cell is run in a fresh directory, in a randomized order
seeded for reproducibility. Subprocess return code, separate stdout and
stderr, start and end timestamps, stop reason, the scanned artifact path
and digest, and the model/version strings are written to one JSONL
record per run, appended atomically.

The runner takes the binary path for each interface arm and the
`--repetitions` count from the command line; the agent command template
comes from the agent config in the harness (see
`harness/agents/<name>.json`). The harness never infers success from a
log tail or a shell status: each run's only delivery facts are the
artifact path, its sha256 and its size, captured by `exec.run_one`.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from harness.exec import build_order, format_prompt, make_config, render_argv, run_one
from harness.ledger import write_json_atomic
from harness.models import AgentConfig, ArmConfig
from harness.tasks import load_tasks

HERE = Path(__file__).resolve().parent
# The pilot's fixtures live beside it (moved from jubarte-redlines'
# eval/cli-v2-pilot, whose root held them); task paths resolve from here.
DEFAULT_REPO_ROOT = HERE


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_agent(agent_path: Path) -> AgentConfig:
    agent = AgentConfig.model_validate_json(agent_path.read_text(encoding="utf-8"))
    if not agent.stub:
        if not agent.model or not agent.provider or not agent.version_argv:
            raise ValueError(
                "model, provider and version_argv are required for a real agent"
            )
        if "{model}" not in " ".join(agent.argv) or "{provider}" not in " ".join(
            agent.argv
        ):
            raise ValueError("argv must select the recorded model and provider")
        if not any("{prompt}" in p or "{prompt_file}" in p for p in agent.argv):
            raise ValueError("argv must deliver the prompt")
        if any("{task_file}" in p for p in agent.argv):
            raise ValueError("task_file is reserved for the stub")
        result = subprocess.run(
            agent.version_argv, capture_output=True, text=True, timeout=10, check=True
        )
        agent.version = result.stdout.strip() or result.stderr.strip()
        if not agent.version:
            raise ValueError("agent version probe returned no version")
    return agent


def load_arms(arms: list[tuple[str, Path]]) -> list[ArmConfig]:
    out: list[ArmConfig] = []
    for label, path in arms:
        out.append(
            ArmConfig(
                label=label,  # type: ignore[arg-type]
                binary=str(path),
                sha256=sha256_file(path),
                role=f"jubarte CLI binary {label}",
            )
        )
    return out


async def main(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    tasks_dir = args.tasks_dir.resolve()
    agent_path = args.agent.resolve()
    runs_root = args.runs_root.resolve()

    if args.smoke:
        # Smoke: a single task, one repetition, one arm — for the --smoke
        # pipeline test that uses the stub agent.
        args.repetitions = 1

    tasks = load_tasks(tasks_dir, repo_root)
    agent = load_agent(agent_path)
    arms = load_arms([("A", args.arm_a.resolve()), ("B", args.arm_b.resolve())])
    if args.smoke:
        tasks = {min(tasks): tasks[min(tasks)]}
        arms = arms[:1]
    order = build_order(tasks, arms, args.repetitions, args.seed)
    config = make_config(
        pilot_id=f"pilot-{uuid.uuid4().hex[:8]}",
        seed=args.seed,
        repetitions=args.repetitions,
        timeout_seconds=args.timeout_seconds,
        fail_mode=args.fail_mode,
        agent=agent,
        arms=arms,
        order=order,
        margin_unintended=args.margin_unintended,
        margin_preservation=args.margin_preservation,
    )
    # Preflight pure formatting as part of configuration validation: a bad
    # placeholder must not move even an explicitly replaceable old root.
    for task in tasks.values():
        for arm in arms:
            work = runs_root / "preflight"
            try:
                prompt = format_prompt(task, Path(arm.binary), work)
                render_argv(
                    agent.argv,
                    binary=Path(arm.binary),
                    input_path=work / "input.docx",
                    output_path=work / task.output_path,
                    prompt_file=work / "prompt.md",
                    prompt=prompt,
                    task_file=runs_root / "stub-data" / f"{task.id}.json",
                    run_dir=work,
                    author=task.required_author,
                    fail_mode=args.fail_mode,
                    agent_root=agent_path.parent,
                    model=agent.model,
                    provider=agent.provider,
                )
            except (ValueError, KeyError) as exc:
                raise ValueError(f"invalid prompt/agent configuration: {exc}") from exc
            if not agent.stub and any("{task_file}" in part for part in agent.argv):
                raise ValueError("task_file is reserved for the deterministic stub")
    config.task_families = {task.id: task.family for task in tasks.values()}
    marker = runs_root / ".cli-v2-pilot"
    if args.runs_root.is_symlink():
        raise ValueError("runs-root must not be a symlink")
    if runs_root.exists():
        if (
            not args.replace
            or not marker.is_file()
            or marker.read_text() != "cli-v2-pilot-v1\n"
        ):
            raise FileExistsError(
                "existing runs-root needs a pilot marker and --replace"
            )
        # Preserve previous evidence. Replacement archives it next to the root.
        archived = runs_root.with_name(
            runs_root.name + ".previous-" + uuid.uuid4().hex[:8]
        )
        runs_root.rename(archived)
    runs_root.mkdir(parents=True)
    marker.write_text("cli-v2-pilot-v1\n")
    write_json_atomic(runs_root / "config.json", config.model_dump(mode="json"))

    binary_by_label = {arm.label: Path(arm.binary) for arm in arms}
    agent_root = agent_path.resolve().parent
    failures = 0
    for entry in order:
        task = tasks[entry.task_id]
        arm_cfg = next(a for a in arms if a.label == entry.arm)
        binary = binary_by_label[entry.arm]
        try:
            await run_one(
                task=task,
                arm=arm_cfg,
                agent=agent,
                repetition=entry.repetition,
                order_index=entry.order_index,
                seed=args.seed,
                timeout_seconds=args.timeout_seconds,
                fail_mode=args.fail_mode,
                runs_root=runs_root,
                pilot_id=config.pilot_id,
                binary=binary,
                agent_root=agent_root,
                repo_root=repo_root,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            failures += 1
            print(
                f"harness: run {entry.order_index} ({entry.task_id} arm={entry.arm}) "
                f"failed unexpectedly: {exc}",
                file=sys.stderr,
            )
    return 1 if failures else 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="Run the held-out paired workflow pilot.",
    )
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    parser.add_argument("--tasks-dir", type=Path, default=HERE / "tasks")
    parser.add_argument(
        "--agent", type=Path, required=True, help="Path to the agent config JSON."
    )
    parser.add_argument(
        "--arm-a",
        type=Path,
        required=True,
        help="Path to the current jubarte CLI binary (arm A).",
    )
    parser.add_argument(
        "--arm-b",
        type=Path,
        required=True,
        help="Path to the v2 jubarte CLI binary (arm B).",
    )
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=Path(tempfile.gettempdir()) / "pilot-runs",
        help="Directory the pilot writes its ledger into.",
    )
    parser.add_argument("--seed", type=int, default=20260215)
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument(
        "--fail-mode",
        default="real",
        help="Mode tag passed through to the agent command template.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Archive and replace a marked pilot root after validating inputs.",
    )
    parser.add_argument("--margin-unintended", type=int, default=0)
    parser.add_argument("--margin-preservation", type=int, default=0)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run a single repetition with one task for smoke tests.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(parse_args(sys.argv[1:]))))
