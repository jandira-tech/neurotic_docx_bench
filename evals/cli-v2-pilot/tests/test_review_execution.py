# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""Execution/provenance and report integration gates using temporary files and fakes."""

import asyncio
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_outcomes import _make_run, _task

import grade as grader
import report
import run as runner
from harness import exec as execution
from harness import grading
from harness.ledger import read_jsonl, write_json_atomic, write_jsonl_atomic
from harness.models import (
    AgentConfig,
    ArmConfig,
    FixtureRef,
    GradeRecord,
    OrderEntry,
    canonical_task_sha256,
)
from harness.snapshot import Snapshot
from harness.tasks import sha256_file

PKG = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.integration


@pytest.fixture
def cell(tmp_path, monkeypatch):
    source = tmp_path / "x.docx"
    source.write_bytes(b"input")
    task = _task().model_copy(
        update={"source": FixtureRef(path="x.docx", sha256=sha256_file(source))}
    )
    # Validate nested source after model_copy.
    task = type(task).model_validate(task.model_dump())
    monkeypatch.setattr(execution, "_fixture_path", lambda *a, **kw: source)
    arm = ArmConfig(label="A", binary="/usr/bin/true", sha256="0" * 64, role="test")
    kwargs = dict(
        task=task,
        arm=arm,
        agent=AgentConfig(name="fake", argv=["fake"]),
        repetition=0,
        order_index=0,
        seed=1,
        timeout_seconds=10,
        fail_mode="real",
        runs_root=tmp_path / "pilot",
        pilot_id="pilot",
        binary=Path("/usr/bin/true"),
        agent_root=tmp_path,
    )
    return kwargs


class Process:
    returncode = None

    def __init__(self):
        self.ready = asyncio.Event()
        self.killed = asyncio.Event()

    async def wait(self):
        self.ready.set()
        await self.killed.wait()
        return self.returncode


async def test_row02_answer_key_not_in_agent_state(cell, monkeypatch):
    observed = []

    async def spawn(*args, **kwargs):
        observed.extend(p.name for p in Path(kwargs["cwd"]).iterdir())
        raise FileNotFoundError("fake")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    await execution.run_one(**cell)
    assert "task.json" not in observed
    assert not any(
        "task.json" in value
        for value in read_jsonl(cell["runs_root"] / "runs.jsonl")[0]["agent_argv"]
    )


async def test_row16_cancellation_records_cell_and_scans_artifact(cell, monkeypatch):
    proc = Process()

    async def spawn(*args, **kwargs):
        (Path(kwargs["cwd"]) / "out.docx").write_bytes(b"committed")
        return proc

    def kill(p):
        p.returncode = -9
        p.killed.set()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(execution, "_kill_process_group", kill)
    future = asyncio.create_task(execution.run_one(**cell))
    await proc.ready.wait()
    future.cancel()
    with pytest.raises(asyncio.CancelledError):
        await future
    rows = read_jsonl(cell["runs_root"] / "runs.jsonl")
    assert len(rows) == 1, "cancelled cell must survive in the denominator"
    assert rows[0]["stop_reason"] == "cancelled" and rows[0]["right_censored"]
    assert rows[0]["artifact_sha256"] == sha256_file(Path(rows[0]["artifact_path"]))


def setup_runner(tmp_path, monkeypatch, *, failure=False):
    task = _task()
    arm = ArmConfig(label="A", binary="/usr/bin/true", sha256="0" * 64, role="test")
    monkeypatch.setattr(runner, "load_tasks", lambda *a: {task.id: task})
    monkeypatch.setattr(
        runner, "load_agent", lambda *a: AgentConfig(name="fake", argv=["fake"])
    )
    monkeypatch.setattr(
        runner, "load_arms", lambda *a: [arm, arm.model_copy(update={"label": "B"})]
    )
    calls = []

    async def fake_run(**kwargs):
        calls.append(kwargs)
        if failure:
            raise PermissionError("not executable")

    monkeypatch.setattr(runner, "run_one", fake_run)
    args = runner.parse_args(
        [
            "--agent",
            "fake.json",
            "--arm-a",
            "/usr/bin/true",
            "--arm-b",
            "/usr/bin/true",
            "--runs-root",
            str(tmp_path / "pilot"),
        ]
    )
    return args, calls


async def test_row01_existing_unmarked_directory_survives(tmp_path, monkeypatch):
    args, _ = setup_runner(tmp_path, monkeypatch)
    args.runs_root.mkdir()
    sentinel = args.runs_root / "precious"
    sentinel.write_text("keep")
    try:
        rc = await runner.main(args)
    except (ValueError, FileExistsError):
        rc = 1
    assert sentinel.is_file() and rc != 0


async def test_row01_invalid_configuration_does_not_delete_marked_root(
    tmp_path, monkeypatch
):
    args, _ = setup_runner(tmp_path, monkeypatch)
    args.replace = True
    args.runs_root.mkdir()
    (args.runs_root / ".cli-v2-pilot").write_text("cli-v2-pilot-v1\n")
    sentinel = args.runs_root / "precious"
    sentinel.write_text("keep")

    def invalid(*a):
        raise ValueError("invalid configuration")

    monkeypatch.setattr(runner, "load_agent", invalid)
    with pytest.raises(ValueError):
        await runner.main(args)
    assert sentinel.is_file()


async def test_row17_harness_failure_returns_nonzero(tmp_path, monkeypatch):
    args, _ = setup_runner(tmp_path, monkeypatch, failure=True)
    assert await runner.main(args) != 0


@pytest.mark.parametrize("repetitions", [0, -1])
def test_row17_repetitions_are_positive(repetitions):
    try:
        execution.build_order({"t": _task()}, [], repetitions, 1)
    except ValueError:
        return
    assert False, "zero or negative repetitions must be rejected"


async def test_row20_requested_root_and_actual_copied_hash(cell, monkeypatch, tmp_path):
    assert "repo_root" in inspect.signature(execution.run_one).parameters
    source = tmp_path / "other" / "x.docx"
    source.parent.mkdir()
    source.write_bytes(b"other checkout")
    cell["task"].source.sha256 = sha256_file(source)

    async def spawn(*a, **kw):
        raise FileNotFoundError("fake")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    result = await execution.run_one(**cell, repo_root=source.parent)
    assert Path(result.input_path).read_bytes() == b"other checkout"
    assert result.input_sha256 == sha256_file(Path(result.input_path))


def test_row03_bundled_agents_deliver_prompt():
    for path in (PKG / "agents").glob("*.json"):
        config = AgentConfig.model_validate_json(path.read_text())
        argv = execution.render_argv(
            config.argv,
            binary=Path("/j"),
            input_path=Path("/i"),
            output_path=Path("/o"),
            prompt_file=Path("/p"),
            prompt="TASK PROMPT",
            task_file=Path("/hidden"),
            run_dir=Path("/r"),
            author="A",
            fail_mode="real",
            agent_root=PKG,
        )
        assert "TASK PROMPT" in argv or "/p" in argv, path


def test_row04_bundled_models_are_selected_and_versions_observed():
    for path in (PKG / "agents").glob("*.json"):
        config = AgentConfig.model_validate_json(path.read_text())
        assert config.model and config.model != "unknown"
        assert "{model}" in " ".join(config.argv) or config.model in config.argv
        assert config.provider and config.provider != "unknown"
        assert getattr(config, "version_argv", None), (
            "version must be probed, not asserted unknown"
        )
    assert "sampling" in execution.make_config(
        pilot_id="p",
        seed=1,
        repetitions=1,
        timeout_seconds=1,
        fail_mode="real",
        agent=AgentConfig(name="fake", argv=["fake"]),
        arms=[],
        order=[],
    ).model_dump().get("seed_scope", "")


def grade_record(run, **updates):
    values = dict(
        run_id=run.run_id,
        task_id=run.task_id,
        task_family=run.task_family,
        arm=run.arm,
        repetition=run.repetition,
        right_censored=False,
        artifact_exists=True,
        tool_correctness=[],
        tool_correctness_overall=True,
        task_checks=[],
        task_completion_overall=True,
        rubric=[],
        claim_value="success",
        claim_expected="success",
        claim_accuracy="accurate",
        claim_detail="",
        graded_at="now",
        grader_binary_path="/usr/bin/true",
        grader_binary_sha256="0" * 64,
    )
    values.update(updates)
    return GradeRecord(**values)


def pilot_config(tmp_path, *, order=None):
    arms = [
        ArmConfig(
            label=x,
            binary="/usr/bin/true",
            sha256=sha256_file(Path("/usr/bin/true")),
            role="test",
        )
        for x in ("A", "B")
    ]
    config = execution.make_config(
        pilot_id="pilot",
        seed=1,
        repetitions=1,
        timeout_seconds=10,
        fail_mode="real",
        agent=AgentConfig(name="fake", argv=["fake"]),
        arms=arms,
        order=order
        or [
            OrderEntry(order_index=i, task_id="demo", arm=x, repetition=0)
            for i, x in enumerate(("A", "B"))
        ],
    )
    write_json_atomic(tmp_path / "config.json", config.model_dump(mode="json"))
    return config


def test_row17_report_exposes_missing_scheduled_cells(tmp_path, capsys):
    pilot_config(tmp_path)
    report.main(["--runs-root", str(tmp_path)])
    text = capsys.readouterr().out
    assert "Scheduled: 2" in text and "Missing: 2" in text
    assert "demo" in text and "| A | 1 |" in text and "| B | 1 |" in text


def test_row18_missing_grades_make_margin_inconclusive(tmp_path, capsys):
    pilot_config(tmp_path)
    write_jsonl_atomic(tmp_path / "runs.jsonl", [_make_run(artifact_exists=True)])
    report.main(["--runs-root", str(tmp_path)])
    text = capsys.readouterr().out
    assert "Gate: INCONCLUSIVE" in text and "Gate: PASS" not in text


@pytest.mark.parametrize(
    "tamper",
    [
        None,
        "artifact",
        "task",
        "input",
        "grader",
        "arm",
        "prompt",
        "source",
        "stdout",
        "stderr",
    ],
)
def test_row19_grade_refuses_changed_identity(tmp_path, monkeypatch, tamper):
    config = pilot_config(tmp_path)
    task = _task()
    run = _make_run(artifact_exists=True)
    artifact, source, prompt = (
        tmp_path / x for x in ("out.docx", "input.docx", "prompt.md")
    )
    artifact.write_bytes(b"original artifact")
    source.write_bytes(b"input")
    prompt.write_text("prompt")
    (tmp_path / "x.docx").write_bytes(source.read_bytes())
    stdout, stderr = tmp_path / "stdout.txt", tmp_path / "stderr.txt"
    stdout.write_text("JUBARTE_RESULT: success\n")
    stderr.write_text("")
    task.source.sha256 = sha256_file(source)
    run = run.model_copy(
        update=dict(
            task_sha256=canonical_task_sha256(task),
            input_path=str(source),
            input_sha256=sha256_file(source),
            artifact_path=str(artifact),
            declared_output_path=str(artifact),
            artifact_sha256=sha256_file(artifact),
            arm_binary_path="/usr/bin/true",
            arm_binary_sha256=config.arms[0].sha256,
            prompt_path=str(prompt),
            prompt_sha256=sha256_file(prompt),
            stdout_path=str(stdout),
            stdout_sha256=sha256_file(stdout),
            stderr_path=str(stderr),
            stderr_sha256=sha256_file(stderr),
        )
    )
    if tamper in ("stdout", "stderr"):
        (stdout if tamper == "stdout" else stderr).write_text("tampered stream")
    if tamper == "source":
        (tmp_path / "x.docx").write_bytes(b"different source")
    if tamper == "artifact":
        artifact.write_bytes(b"replaced")
    if tamper == "task":
        task.prompt += "weakened"
    if tamper == "input":
        source.write_bytes(b"replaced")
    if tamper == "prompt":
        prompt.write_text("replaced")
    if tamper == "arm":
        run.arm_binary_sha256 = "0" * 64
    binary = "/usr/bin/false" if tamper == "grader" else "/usr/bin/true"
    write_jsonl_atomic(tmp_path / "runs.jsonl", [run])
    monkeypatch.setattr(grader, "load_tasks", lambda *a: {task.id: task})
    called = []
    monkeypatch.setattr(
        grader, "grade_one", lambda *a, **kw: called.append(1) or grade_record(run)
    )
    rc = grader.main(
        [
            "--runs-root",
            str(tmp_path),
            "--tasks-dir",
            str(tmp_path),
            "--repo-root",
            str(tmp_path),
            "--grader-binary",
            binary,
        ]
    )
    if tamper is None:
        assert rc == 0 and called == [1]
    else:
        assert rc != 0 and not called


@pytest.mark.parametrize("error", [False, True])
def test_row21_failed_inspection_is_not_measured_zero(tmp_path, monkeypatch, error):
    binary = Path("/usr/bin/true")
    source = tmp_path / "x.docx"
    source.write_bytes(b"input")
    run = _make_run(artifact_exists=True)

    def read(*a):
        if error:
            raise TimeoutError("reader timeout")
        return Snapshot(ok=False, error="cannot inspect")

    monkeypatch.setattr(grading, "read_snapshot", read)
    monkeypatch.setattr(
        grading, "validate", lambda *a, **kw: (SimpleNamespace(return_code=0), [])
    )
    try:
        grade = grading.grade_one(run, _task(), binary, repo_root=tmp_path)
    except TimeoutError:
        grade = None
    assert grade is not None, "a reader failure must produce a per-run error grade"
    assert (
        grade.unintended_edit_count is None and grade.preservation_defect_count is None
    )
    assert grade.model_dump().get("preservation_status") == "not_assessed"


def test_row22_margin_is_bound_before_execution_and_cannot_change(tmp_path):
    config = pilot_config(tmp_path)
    assert "margin_unintended" in config.model_dump()
    assert "margin_preservation" in config.model_dump()
    assert report.main(["--runs-root", str(tmp_path), "--margin-unintended", "2"]) != 0


async def test_row28_smoke_schedules_exactly_one_cell(tmp_path, monkeypatch):
    args, calls = setup_runner(tmp_path, monkeypatch)
    args.smoke = True
    await runner.main(args)
    assert len(calls) == 1
    config = json.loads((args.runs_root / "config.json").read_text())
    assert len(config["order"]) == 1


def observed_grade(tmp_path, monkeypatch, source, artifact, *, validation_rc=0):
    binary = tmp_path / "j"
    binary.write_bytes(b"fake binary")
    source_path = tmp_path / "x.docx"
    source_path.write_bytes(b"source")
    run = _make_run(artifact_exists=True)
    task = _task()
    data = task.model_dump()
    data["checks"] = [
        {
            "kind": "text_equals",
            "selector": {"contains": "authorized"},
            "text": "authorized result",
        }
    ]
    data["expected_paragraphs"] = {"p0": "authorized result"}
    task = type(task).model_validate(data)
    monkeypatch.setattr(grading, "read_snapshot", lambda *a: artifact)
    monkeypatch.setattr(grading, "_source_snapshot", lambda *a: source)
    monkeypatch.setattr(
        grading,
        "validate",
        lambda *a, **kw: (SimpleNamespace(return_code=validation_rc), []),
    )
    return grading.grade_one(run, task, binary, repo_root=tmp_path)


def test_row13_unchanged_copy_is_not_realized_operations(tmp_path, monkeypatch):
    from test_review import snap

    grade = observed_grade(
        tmp_path,
        monkeypatch,
        snap(["authorized original"]),
        snap(["authorized original"]),
    )
    assert not grade.tool_correctness_overall and not grade.task_completion_overall
    assert grade.claim_accuracy == "inaccurate"


@pytest.mark.parametrize("defect", ["extra_text", "invalid_package", "changed_comment"])
def test_row15_grade_propagates_known_defects_to_claim_and_refusal(
    tmp_path, monkeypatch, defect
):
    from test_review import snap

    source = snap(
        ["authorized original", "keep"],
        comments=[{"id": 4, "ref": "c4", "author": "A", "text": "old"}],
    )
    artifact = snap(
        ["authorized result", "WRONG" if defect == "extra_text" else "keep"],
        comments=[
            {
                "id": 4,
                "ref": "c4",
                "author": "A",
                "text": "changed" if defect == "changed_comment" else "old",
            }
        ],
    )
    grade = observed_grade(
        tmp_path,
        monkeypatch,
        source,
        artifact,
        validation_rc=2 if defect == "invalid_package" else 0,
    )
    assert not grade.tool_correctness_overall
    assert not grade.task_completion_overall
    assert grade.claim_accuracy == "inaccurate"
    assert grade.refusal_class == "false_negative_acceptance"


def test_row21_unexposed_dimensions_stay_not_assessed_on_clean_grade(
    tmp_path, monkeypatch
):
    from test_review import snap

    grade = observed_grade(
        tmp_path,
        monkeypatch,
        snap(["authorized original"]),
        snap(["authorized result"]),
    )
    assert grade.tool_correctness_overall and grade.preservation_defect_count == 0
    assert (
        "section properties" in grade.unassessed and "relationships" in grade.unassessed
    )


def test_row04_version_probe_and_recorded_model_drive_rendered_argv(
    tmp_path, monkeypatch
):
    config = json.loads((PKG / "agents/codex-exec.json").read_text())
    path = tmp_path / "agent.json"
    path.write_text(json.dumps(config))
    seen = []

    def version(argv, **kw):
        seen.append(argv)
        return SimpleNamespace(stdout="codex 1.2.3", stderr="")

    monkeypatch.setattr(runner.subprocess, "run", version)
    agent = runner.load_agent(path)
    assert agent.version == "codex 1.2.3" and seen == [config["version_argv"]]
    argv = execution.render_argv(
        agent.argv,
        binary=Path("/j"),
        input_path=Path("/i"),
        output_path=Path("/o"),
        prompt_file=Path("/p"),
        prompt="PROMPT",
        task_file=Path("/private"),
        run_dir=tmp_path,
        author="A",
        fail_mode="real",
        agent_root=tmp_path,
        model=agent.model,
        provider=agent.provider,
    )
    assert argv[argv.index("--model") + 1] == agent.model
    assert 'model_provider="openai"' in argv and argv[-1] == "PROMPT"


async def test_row01_marked_explicit_replacement_archives_evidence(
    tmp_path, monkeypatch
):
    args, _ = setup_runner(tmp_path, monkeypatch)
    args.runs_root.mkdir()
    (args.runs_root / ".cli-v2-pilot").write_text("cli-v2-pilot-v1\n")
    (args.runs_root / "precious").write_text("old evidence")
    args.replace = True
    assert await runner.main(args) == 0
    archives = list(tmp_path.glob("pilot.previous-*"))
    assert (
        len(archives) == 1 and (archives[0] / "precious").read_text() == "old evidence"
    )
    assert (args.runs_root / "config.json").is_file()


async def test_row01_symlink_root_is_refused(tmp_path, monkeypatch):
    args, _ = setup_runner(tmp_path, monkeypatch)
    target = tmp_path / "target"
    target.mkdir()
    (target / "precious").write_text("keep")
    args.runs_root.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        await runner.main(args)
    assert (target / "precious").read_text() == "keep"


async def test_row16_timeout_records_censored_cell(cell, monkeypatch):
    proc = Process()

    async def spawn(*a, **kw):
        return proc

    async def timeout(awaitable, seconds):
        awaitable.close()
        raise TimeoutError

    def kill(p):
        p.returncode = -9
        p.killed.set()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(asyncio, "wait_for", timeout)
    monkeypatch.setattr(execution, "_kill_process_group", kill)
    result = await execution.run_one(**cell)
    assert result.right_censored and result.stop_reason == "timeout"


@pytest.mark.parametrize("mode", ["pass", "fail", "missing_b"])
def test_row18_margin_needs_assessed_paired_grades(tmp_path, capsys, mode):
    pilot_config(tmp_path)
    a = _make_run(artifact_exists=True)
    b = a.model_copy(update={"run_id": "b", "arm": "B", "order_index": 1})
    write_jsonl_atomic(tmp_path / "runs.jsonl", [a, b])
    gs = [
        grade_record(
            a,
            preservation_status="assessed",
            unintended_edit_count=0,
            preservation_defect_count=0,
        )
    ]
    if mode != "missing_b":
        gs.append(
            grade_record(
                b,
                preservation_status="assessed",
                unintended_edit_count=int(mode == "fail"),
                preservation_defect_count=0,
            )
        )
    write_jsonl_atomic(tmp_path / "grades.jsonl", gs)
    report.main(["--runs-root", str(tmp_path)])
    text = capsys.readouterr().out
    expected = {"pass": "PASS", "fail": "FAIL", "missing_b": "INCONCLUSIVE"}[mode]
    assert f"Gate: {expected}" in text


@pytest.mark.integration
def test_legacy_multibody_normalization_is_detected(
    tmp_path, repo_root, jubarte_binary
):
    """Retain the real engine defect discovered by the stronger grader.
    The legacy multi-body repair probe is not the clean-edit task fixture."""
    import subprocess

    from harness.tasks import load_task

    source = repo_root / "fixtures/multibody.docx"
    out = tmp_path / "out.docx"
    result = subprocess.run(
        [
            str(jubarte_binary),
            "edit",
            str(source),
            "-p",
            "p0",
            "--anchor",
            "brown",
            "--content",
            "red",
            "--author",
            "PilotBot",
            "-o",
            str(out),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    task, _ = load_task(PKG / "tasks/02-exact-replace-multibody.json", repo_root)
    task.source.path = "fixtures/multibody.docx"
    task.source.sha256 = sha256_file(source)
    run = _make_run(artifact_exists=True).model_copy(update={"artifact_path": str(out)})
    grade = grading.grade_one(run, task, jubarte_binary, repo_root=repo_root)
    assert grade.unintended_edit_count > 0 and grade.preservation_defect_count > 0
    assert not grade.tool_correctness_overall and grade.claim_accuracy == "inaccurate"


async def test_row16_cancellation_during_spawn_is_recorded(cell, monkeypatch):
    proc = Process()
    spawning, release = asyncio.Event(), asyncio.Event()

    async def spawn(*a, **kw):
        spawning.set()
        await release.wait()
        return proc

    def kill(p):
        p.returncode = -9
        p.killed.set()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(execution, "_kill_process_group", kill)
    future = asyncio.create_task(execution.run_one(**cell))
    await spawning.wait()
    future.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await future
    rows = read_jsonl(cell["runs_root"] / "runs.jsonl")
    assert len(rows) == 1 and rows[0]["stop_reason"] == "cancelled"


async def test_row01_invalid_prompt_or_argv_is_validated_before_replacement(
    tmp_path, monkeypatch
):
    args, _ = setup_runner(tmp_path, monkeypatch)
    args.runs_root.mkdir()
    (args.runs_root / ".cli-v2-pilot").write_text("cli-v2-pilot-v1\n")
    sentinel = args.runs_root / "precious"
    sentinel.write_text("keep")
    args.replace = True
    monkeypatch.setattr(
        runner,
        "load_agent",
        lambda *a: AgentConfig(name="fake", argv=["fake", "{unknown}"]),
    )
    try:
        await runner.main(args)
    except ValueError:
        pass
    assert sentinel.is_file(), "invalid argv must not even archive the old root"


def test_row22_report_requires_explicit_predeclared_margins(tmp_path):
    pilot_config(tmp_path)
    path = tmp_path / "config.json"
    raw = json.loads(path.read_text())
    del raw["margin_unintended"]
    del raw["margin_preservation"]
    path.write_text(json.dumps(raw))
    try:
        rc = report.main(["--runs-root", str(tmp_path)])
    except ValueError:
        rc = 1
    assert rc != 0, "a legacy unbound margin cannot be called predeclared"


def test_report_retains_primary_outcome_counts_per_family(tmp_path, capsys):
    config = pilot_config(tmp_path)
    config.task_families = {"demo": "exact_replace"}
    write_json_atomic(tmp_path / "config.json", config.model_dump(mode="json"))
    a = _make_run(artifact_exists=True)
    b = a.model_copy(update={"run_id": "b", "arm": "B", "order_index": 1})
    write_jsonl_atomic(tmp_path / "runs.jsonl", [a, b])
    write_jsonl_atomic(
        tmp_path / "grades.jsonl",
        [
            grade_record(
                a,
                preservation_status="assessed",
                unintended_edit_count=0,
                preservation_defect_count=0,
            ),
            grade_record(
                b,
                preservation_status="assessed",
                unintended_edit_count=2,
                preservation_defect_count=1,
            ),
        ],
    )
    report.main(["--runs-root", str(tmp_path)])
    text = capsys.readouterr().out
    assert "## Unintended edits and preservation defects per family and arm" in text
    section = text.split(
        "## Unintended edits and preservation defects per family and arm"
    )[1]
    assert "| exact_replace | B | 1 | 0 | 2 | 1 |" in section
