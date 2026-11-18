#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC

# SPDX-License-Identifier: AGPL-3.0-only

"""The execution side of the harness: run one agent command in one directory.

The harness owns status capture, budgets, termination metadata and artifact
collection (never success inference): the agent subprocess gets a fresh
temp directory with the task inputs, its own stdout/stderr files, a wall
clock budget, and the declared output path is scanned afterwards for the
actual committed bytes.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import re
import shutil
import signal
import uuid
from datetime import datetime, timezone
from pathlib import Path

from harness.ledger import append_jsonl
from harness.models import (
    AgentConfig,
    ArmConfig,
    ClaimObservation,
    OrderEntry,
    RunConfig,
    RunRecord,
    Task,
    canonical_task_sha256,
)
from harness.tasks import sha256_file

CLAIM_RE = re.compile(r"^JUBARTE_RESULT:\s*(success|unsupported|failed)\s*$", re.M)

HARNESS_FILES = frozenset({"input.docx", "prompt.md", "stdout.txt", "stderr.txt"})


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def format_prompt(task: Task, binary: Path, run_dir: Path) -> str:
    """Bind the task prompt to this run's binary, input, output and author."""

    return task.prompt.format(
        binary=str(binary),
        input="input.docx",
        output=task.output_path,
        workdir=str(run_dir),
        author=task.required_author,
    )


def render_argv(
    template: list[str],
    *,
    binary: Path,
    input_path: Path,
    output_path: Path,
    prompt_file: Path,
    prompt: str,
    task_file: Path,
    run_dir: Path,
    author: str,
    fail_mode: str,
    agent_root: Path,
    model: str | None = None,
    provider: str | None = None,
) -> list[str]:
    values = {
        "model": model or "",
        "provider": provider or "",
        "binary": str(binary),
        "input": str(input_path),
        "output": str(output_path),
        "prompt_file": str(prompt_file),
        "prompt": prompt,
        "task_file": str(task_file),
        "run_dir": str(run_dir),
        "author": author,
        "fail_mode": fail_mode,
        "agent_root": str(agent_root),
    }
    rendered = []
    for part in template:
        try:
            rendered.append(part.format(**values))
        except KeyError as exc:
            raise ValueError(
                f"unknown placeholder {exc.args[0]!r} in agent argv: {part!r}"
            ) from exc
    return rendered


def parse_claim(stdout_text: str) -> tuple[ClaimObservation | None, str]:
    """The last JUBARTE_RESULT marker in stdout is the agent's claim."""

    texts = []
    for line in stdout_text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            texts.append(line)
            continue
        if not isinstance(event, dict):
            continue
        item = event.get("item", {})
        if isinstance(item, dict) and item.get("type") == "agent_message":
            texts.append(item.get("text", ""))
        message = event.get("message", event)
        if isinstance(message, dict) and message.get("role") == "assistant":
            content = message.get("content", [])
            if isinstance(content, str):
                texts.append(content)
            elif isinstance(content, list):
                texts.extend(
                    c.get("text", "")
                    for c in content
                    if isinstance(c, dict) and c.get("type") == "text"
                )
    matches = list(CLAIM_RE.finditer("\n".join(texts)))
    if not matches:
        return None, stdout_text
    last = matches[-1]
    # CLAIM_RE matches only the three values; pydantic checks it again.
    value = last.group(1)  # pyrefly: ignore[bad-assignment]
    return ClaimObservation(raw=last.group(0).strip(), value=value), stdout_text  # pyrefly: ignore[bad-argument-type]


def scan_artifact(declared: Path) -> tuple[bool, str | None, int | None]:
    if declared.is_file():
        return True, sha256_file(declared), declared.stat().st_size
    return False, None, None


async def run_one(
    *,
    task: Task,
    arm: ArmConfig,
    agent: AgentConfig,
    repetition: int,
    order_index: int,
    seed: int,
    timeout_seconds: float,
    fail_mode: str,
    runs_root: Path,
    pilot_id: str,
    binary: Path,
    agent_root: Path,
    repo_root: Path | None = None,
) -> RunRecord:
    """Execute one (task, arm, repetition) cell and record only observations."""

    started_at = utc_now()
    monotonic_start = asyncio.get_running_loop().time()
    run_dir = (
        runs_root / "runs" / f"{order_index:03d}-{task.id}-{arm.label}-{repetition}"
    )
    run_dir.mkdir(parents=True, exist_ok=False)

    input_path = run_dir / "input.docx"
    fixture = (
        (repo_root / task.source.path) if repo_root is not None else _fixture_path(task)
    )
    shutil.copyfile(fixture, input_path)
    input_sha = sha256_file(input_path)
    if input_sha != task.source.sha256:
        raise ValueError("copied input sha256 differs from pinned task input")

    prompt = format_prompt(task, binary, run_dir)
    prompt_file = run_dir / "prompt.md"
    prompt_file.write_text(prompt, encoding="utf-8")

    # Only the deterministic stub receives the answer key. Real agents get
    # prompt.md and input.docx; no task data is materialized for them.
    task_file = runs_root / "stub-data" / f"{task.id}.json"
    if agent.stub:
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(task.model_dump_json(), encoding="utf-8")
    elif any("{task_file}" in part for part in agent.argv):
        raise ValueError("task_file is reserved for the deterministic stub")

    declared_output = run_dir / task.output_path
    stdout_path = run_dir / "stdout.txt"
    stderr_path = run_dir / "stderr.txt"

    argv = render_argv(
        agent.argv,
        binary=binary,
        input_path=input_path,
        output_path=declared_output,
        prompt_file=prompt_file,
        prompt=prompt,
        task_file=task_file,
        run_dir=run_dir,
        author=task.required_author,
        fail_mode=fail_mode,
        agent_root=agent_root,
        model=agent.model,
        provider=agent.provider,
    )

    cancelled = False
    stop_reason = "exit"
    return_code: int | None = None
    with stdout_path.open("wb") as out_handle, stderr_path.open("wb") as err_handle:
        spawn = asyncio.create_task(
            asyncio.create_subprocess_exec(
                *argv,
                cwd=str(run_dir),
                stdout=out_handle,
                stderr=err_handle,
                start_new_session=True,
            )
        )
        try:
            try:
                proc = await asyncio.shield(spawn)
            except asyncio.CancelledError:
                # Finish acquiring the process handle before killing/reaping;
                # otherwise cancellation can orphan a child during creation.
                cancelled = True
                stop_reason = "cancelled"
                proc = await spawn
        except OSError as exc:
            stderr_path.write_text(
                f"harness: agent could not start: {argv[0]}\n{exc}\n",
                encoding="utf-8",
            )
            return_code = 127
        else:
            try:
                if cancelled:
                    _kill_process_group(proc)
                    await proc.wait()
                    return_code = proc.returncode
                else:
                    return_code = await asyncio.wait_for(proc.wait(), timeout_seconds)
            except asyncio.TimeoutError:
                _kill_process_group(proc)
                await proc.wait()
                stop_reason = "timeout"
                return_code = proc.returncode
            except asyncio.CancelledError:
                _kill_process_group(proc)
                await proc.wait()
                stop_reason = "cancelled"
                return_code = proc.returncode
                cancelled = True

    stdout_bytes = stdout_path.stat().st_size
    stderr_bytes = stderr_path.stat().st_size
    claim, _ = parse_claim(stdout_path.read_text(encoding="utf-8", errors="replace"))
    artifact_exists, artifact_sha, artifact_size = scan_artifact(declared_output)
    run_dir_files = sorted(
        entry.name
        for entry in run_dir.iterdir()
        if entry.is_file() and entry.name not in HARNESS_FILES
    )

    ended_at = utc_now()
    duration = asyncio.get_running_loop().time() - monotonic_start
    record = RunRecord(
        run_id=uuid.uuid4().hex[:12],
        pilot_id=pilot_id,
        task_id=task.id,
        task_family=task.family,
        task_sha256=canonical_task_sha256(task),
        arm=arm.label,
        arm_binary_path=str(binary),
        arm_binary_sha256=arm.sha256,
        agent_name=agent.name,
        agent_model=agent.model,
        agent_provider=agent.provider,
        agent_version=agent.version,
        agent_argv=argv,
        repetition=repetition,
        order_index=order_index,
        seed=seed,
        started_at=started_at,
        ended_at=ended_at,
        duration_seconds=round(duration, 3),
        timeout_seconds=timeout_seconds,
        return_code=return_code,
        stop_reason=stop_reason,
        right_censored=stop_reason != "exit",
        run_dir=str(run_dir),
        prompt_path=str(prompt_file),
        prompt_sha256=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        input_path=str(input_path),
        input_sha256=input_sha,
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
        stdout_sha256=sha256_file(stdout_path),
        stderr_sha256=sha256_file(stderr_path),
        stdout_bytes=stdout_bytes,
        stderr_bytes=stderr_bytes,
        declared_output_path=str(declared_output),
        artifact_path=str(declared_output),
        artifact_exists=artifact_exists,
        artifact_sha256=artifact_sha,
        artifact_bytes=artifact_size,
        run_dir_files=run_dir_files,
        claim=claim,
    )
    append_jsonl(runs_root / "runs.jsonl", [record])
    if cancelled:
        raise asyncio.CancelledError
    return record


def _kill_process_group(proc: asyncio.subprocess.Process) -> None:
    if proc.returncode is not None:
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        try:
            proc.kill()
        except ProcessLookupError:
            pass


_FIXTURE_CACHE: dict[tuple[str, str], Path] = {}


def _fixture_path(task: Task) -> Path:
    """Locate the task fixture relative to this repository's root."""

    here = Path(__file__).resolve()
    for ancestor in here.parents:
        candidate = ancestor / task.source.path
        if candidate.is_file():
            key = (task.source.path, task.source.sha256)
            _FIXTURE_CACHE[key] = candidate
            return candidate
    raise FileNotFoundError(
        f"{task.id}: fixture {task.source.path} not found above {here}"
    )


def build_order(
    tasks: dict[str, Task],
    arms: list[ArmConfig],
    repetitions: int,
    seed: int,
) -> list[OrderEntry]:
    """Every (task, arm, repetition) cell, shuffled by the recorded seed."""

    if repetitions < 1:
        raise ValueError("repetitions must be at least 1")
    cells = [
        (task_id, arm.label, rep)
        for task_id in sorted(tasks)
        for arm in arms
        for rep in range(repetitions)
    ]
    rng = random.Random(seed)
    rng.shuffle(cells)
    return [
        OrderEntry(order_index=index, task_id=task_id, arm=arm, repetition=rep)
        for index, (task_id, arm, rep) in enumerate(cells)
    ]


def make_config(
    *,
    pilot_id: str,
    seed: int,
    repetitions: int,
    timeout_seconds: float,
    fail_mode: str,
    agent: AgentConfig,
    arms: list[ArmConfig],
    order: list[OrderEntry],
    margin_unintended: int = 0,
    margin_preservation: int = 0,
) -> RunConfig:
    return RunConfig(
        pilot_id=pilot_id,
        seed=seed,
        repetitions=repetitions,
        timeout_seconds=timeout_seconds,
        fail_mode=fail_mode,
        agent=agent,
        arms=arms,
        order=order,
        created_at=utc_now(),
        margin_unintended=margin_unintended,
        margin_preservation=margin_preservation,
    )
