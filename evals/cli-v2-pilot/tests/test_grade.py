#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC

# SPDX-License-Identifier: AGPL-3.0-only

"""Grade-record logic in isolation from the full pipeline.

`grade.py` reads the runs ledger, calls `jubarte read --json` /
`jubarte validate` against each artifact, and writes a single
GradeRecord per run. These tests pin the per-check semantics against
synthetic snapshots so a future change to the evaluator's
interpretation does not silently flip a passing run to a failing one.
"""

from __future__ import annotations

import pytest

from harness.models import (
    ClaimObservation,
    RunRecord,
    Task,
)
from harness.snapshot import Snapshot


def _empty_task(task_id: str = "demo") -> Task:
    return Task.model_validate(
        {
            "schema_version": 1,
            "id": task_id,
            "family": "exact_replace",
            "source": {"path": "x.docx", "sha256": "0" * 64},
            "prompt": "do {binary} {output} {author} -> JUBARTE_RESULT",
            "required_author": "PilotBot",
            "output_path": "out.docx",
            "tracked": True,
            "settlement": False,
            "genuinely_unsupported": False,
            "checks": [
                {"kind": "text_contains", "text": "alpha"},
                {
                    "kind": "text_equals",
                    "selector": {"contains": "alpha"},
                    "text": "alpha and beta",
                },
                {"kind": "text_absent", "text": "gamma"},
                {"kind": "revision_count", "min": 1, "max": 2},
                {"kind": "revision_present", "text": "alpha", "author": "PilotBot"},
                {"kind": "comment_present", "text": "hello", "author": "PilotBot"},
                {"kind": "no_artifact"},
            ],
            "rubric": [],
            "stub": {"expected_claim": "success", "steps": []},
        }
    )


def _empty_snap() -> Snapshot:
    return Snapshot(
        ok=True,
        paragraphs=[
            {"id": "p0", "text": "alpha and beta", "runs": [], "limitations": []},
            {"id": "p1", "text": "unrelated", "runs": [], "limitations": []},
        ],
        revisions=[
            {
                "id": "r1",
                "kind": "insertion",
                "author": "PilotBot",
                "text": "alpha",
                "paragraph": "p0",
            },
        ],
        comments=[
            {
                "id": 1,
                "ref": "c1",
                "author": "PilotBot",
                "text": "hello world",
                "done": False,
                "paragraph": "p0",
                "anchor_text": "alpha",
                "before": "",
                "after": "",
            },
        ],
    )


def _empty_run(
    *, artifact_exists: bool, claim_value: str | None = "success"
) -> RunRecord:
    return RunRecord(
        run_id="r",
        pilot_id="pilot",
        task_id="demo",
        task_family="exact_replace",
        task_sha256="0" * 64,
        arm="A",
        arm_binary_path="/bin/j",
        arm_binary_sha256="0" * 64,
        agent_name="stub",
        agent_argv=["stub"],
        repetition=0,
        order_index=0,
        seed=42,
        started_at="2026-10-17T00:00:00Z",
        ended_at="2026-10-17T00:00:01Z",
        duration_seconds=1.0,
        timeout_seconds=120.0,
        return_code=0,
        stop_reason="exit",
        right_censored=False,
        run_dir="/tmp/r",
        prompt_path="/tmp/r/prompt.md",
        prompt_sha256="0" * 64,
        input_path="/tmp/r/input.docx",
        input_sha256="0" * 64,
        stdout_path="/tmp/r/stdout.txt",
        stderr_path="/tmp/r/stderr.txt",
        stdout_sha256="0" * 64,
        stderr_sha256="0" * 64,
        stdout_bytes=0,
        stderr_bytes=0,
        declared_output_path="/tmp/r/out.docx",
        artifact_path="/tmp/r/out.docx",
        artifact_exists=artifact_exists,
        run_dir_files=[],
        claim=(
            ClaimObservation(raw=f"JUBARTE_RESULT: {claim_value}", value=claim_value)
            if claim_value
            else None
        ),
    )


def test_eval_task_check_handles_each_kind_unaffected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from harness.grading import eval_task_check

    task = _empty_task()
    snap = _empty_snap()
    results = []
    for check in task.checks:
        results.append(
            eval_task_check(
                check.model_dump(),
                snap,
                artifact_exists=True,
                revisions_total=1,
                comments_total=1,
            )
        )
    assert [r.status for r in results] == [
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "fail",
    ]


def test_claim_accuracy_accurate_when_marker_agrees() -> None:
    from harness.grading import claim_accuracy, eval_task_check

    task = _empty_task()
    run = _empty_run(artifact_exists=True)
    snap = _empty_snap()
    results = [
        eval_task_check(
            check.model_dump(),
            snap,
            artifact_exists=True,
            revisions_total=1,
            comments_total=1,
        )
        for check in task.checks
    ]
    assert results[-1].status == "fail"
    # Drop the no_artifact check (artifact exists), keep the rest.
    pruned = [c for c in task.checks if c.kind != "no_artifact"]
    pruned_results = [
        eval_task_check(
            check.model_dump(),
            snap,
            artifact_exists=True,
            revisions_total=1,
            comments_total=1,
        )
        for check in pruned
    ]
    claim_value, claim_expected, accuracy, detail = claim_accuracy(
        run,
        task,
        snapshot_ok=True,
        task_checks=pruned_results,
        artifact_exists=True,
    )
    assert accuracy == "accurate"


def test_claim_accuracy_inaccurate_when_marker_disagrees() -> None:
    from harness.grading import claim_accuracy

    task = _empty_task()
    run = _empty_run(artifact_exists=True, claim_value="failed")
    claim_value, claim_expected, accuracy, detail = claim_accuracy(
        run,
        task,
        snapshot_ok=True,
        task_checks=[],
        artifact_exists=True,
    )
    assert accuracy == "inaccurate"


def test_claim_accuracy_missing_when_no_marker() -> None:
    from harness.grading import claim_accuracy

    task = _empty_task()
    run = _empty_run(artifact_exists=True, claim_value=None)
    _, _, accuracy, _ = claim_accuracy(
        run,
        task,
        snapshot_ok=True,
        task_checks=[],
        artifact_exists=True,
    )
    assert accuracy == "missing"


def _grade_run(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    task: Task,
    validate_result,
    validate_findings: list | None = None,
    source_file: bool = True,
    source_snapshot: Snapshot | None = None,
):
    """Grade one run with the binary swapped for stubs.

    Returns (grade, validate_calls): each call is the kwargs `grade_one`
    handed `harness.snapshot.validate`, so a test can pin whether the
    baseline-relative audit ran with the source and required author.
    """
    from harness import grading

    binary = tmp_path / "j"
    binary.write_bytes(b"fake binary")
    if source_file:
        (tmp_path / "x.docx").write_bytes(b"source")
    calls = []

    def fake_validate(binary, artifact, **kwargs):
        calls.append(kwargs)
        return validate_result, validate_findings or []

    monkeypatch.setattr(grading, "read_snapshot", lambda *a, **kw: _empty_snap())
    monkeypatch.setattr(
        grading,
        "_source_snapshot",
        lambda *a, **kw: source_snapshot or _empty_snap(),
    )
    monkeypatch.setattr(grading, "validate", fake_validate)
    run = _empty_run(artifact_exists=True)
    return grading.grade_one(run, task, binary, repo_root=tmp_path), calls


def test_tracked_task_runs_the_baseline_relative_audit(tmp_path, monkeypatch):
    # #1431 review: a tracked run could score full tool correctness with
    # the desired text written directly instead of through revisions —
    # `validate` ran without `--original`/`--author`, so the `edits`
    # rule never ran. For a tracked task the grader must run the audit
    # and fail tool correctness on its findings (UNTRACKED_EDIT,
    # FOREIGN_AUTHOR, ...).
    from types import SimpleNamespace

    grade, calls = _grade_run(
        tmp_path,
        monkeypatch,
        task=_empty_task(),
        validate_result=SimpleNamespace(return_code=2),
    )
    assert calls == [{"original": tmp_path / "x.docx", "author": "PilotBot"}]
    by_name = {r.name: r for r in grade.tool_correctness}
    assert by_name["artifact-valid"].status == "fail"
    assert not grade.tool_correctness_overall


def test_tracked_task_audit_pass_leaves_tool_correctness(tmp_path, monkeypatch):
    from types import SimpleNamespace

    grade, calls = _grade_run(
        tmp_path,
        monkeypatch,
        task=_empty_task(),
        validate_result=SimpleNamespace(return_code=0),
    )
    assert calls == [{"original": tmp_path / "x.docx", "author": "PilotBot"}]
    by_name = {r.name: r for r in grade.tool_correctness}
    assert by_name["artifact-valid"].status == "pass"


def test_untracked_task_keeps_the_default_validity_check(tmp_path, monkeypatch):
    from types import SimpleNamespace

    task = _empty_task().model_copy(update={"tracked": False})
    grade, calls = _grade_run(
        tmp_path,
        monkeypatch,
        task=task,
        validate_result=SimpleNamespace(return_code=0),
    )
    assert calls == [{"original": None, "author": None}]


def test_tracked_audit_without_a_source_is_reported_unassessed(tmp_path, monkeypatch):
    from types import SimpleNamespace

    grade, calls = _grade_run(
        tmp_path,
        monkeypatch,
        task=_empty_task(),
        validate_result=SimpleNamespace(return_code=0),
        source_file=False,
    )
    assert calls == [{"original": None, "author": None}]
    assert "tracked-edit audit" in grade.unassessed


def test_settlement_task_tolerates_only_the_licensed_gone_revision(
    tmp_path, monkeypatch
):
    # The edits audit has no licence for a settlement task's declared
    # removals: `jubarte validate --original --author` reports a settled
    # foreign revision as FOREIGN_AUTHOR "gone". The grader tolerates
    # exactly the `settled_revisions` entries and still fails on
    # anything else.
    from types import SimpleNamespace

    task = _empty_task().model_copy(
        update={"settlement": True, "settled_revisions": ["r0"]}
    )
    gone = {
        "code": "FOREIGN_AUTHOR",
        "set": "edits",
        "severity": "error",
        "part": "word/document.xml",
        "location": "",
        "ref": "",
        "message": "sara.k's r0 in the original is gone",
    }
    grade, _ = _grade_run(
        tmp_path,
        monkeypatch,
        task=task,
        validate_result=SimpleNamespace(return_code=2),
        validate_findings=[gone],
    )
    by_name = {r.name: r for r in grade.tool_correctness}
    assert by_name["artifact-valid"].status == "pass"

    grade, _ = _grade_run(
        tmp_path,
        monkeypatch,
        task=task,
        validate_result=SimpleNamespace(return_code=2),
        validate_findings=[{**gone, "message": "sara.k's r7 in the original is gone"}],
    )
    by_name = {r.name: r for r in grade.tool_correctness}
    assert by_name["artifact-valid"].status == "fail"

    grade, _ = _grade_run(
        tmp_path,
        monkeypatch,
        task=task,
        validate_result=SimpleNamespace(return_code=2),
        validate_findings=[
            {
                "code": "UNTRACKED_EDIT",
                "set": "edits",
                "severity": "error",
                "part": "word/document.xml",
                "location": "p6",
                "ref": "p6",
                "message": "p6 differs after rejecting PilotBot's changes",
            }
        ],
    )
    by_name = {r.name: r for r in grade.tool_correctness}
    assert by_name["artifact-valid"].status == "fail"


def test_settlement_task_licenses_untracked_edit_at_a_settled_paragraph(
    tmp_path, monkeypatch
):
    # Settling a revision leaves residue the same audit also reports as
    # UNTRACKED_EDIT at the revision's paragraph: rejecting a foreign
    # insertion removes its text with no tracked mark of ours. The
    # licence reaches that paragraph through the source snapshot; an
    # untracked edit anywhere else still fails.
    from types import SimpleNamespace

    source = Snapshot(
        ok=True,
        paragraphs=[
            {"id": "p0", "text": "alpha and beta", "runs": [], "limitations": []},
            {"id": "p1", "text": "unrelated", "runs": [], "limitations": []},
        ],
        revisions=[
            {
                "id": "r0+1",
                "ref": "r0+1",
                "kind": "replacement",
                "author": "sara.k",
                "text": "beta → alpha",
                "paragraph": "p0",
                "members": [
                    {"id": "r0", "kind": "deletion", "text": "beta"},
                    {"id": "r1", "kind": "insertion", "text": "alpha"},
                ],
            },
        ],
        comments=[],
    )
    task = _empty_task().model_copy(
        update={"settlement": True, "settled_revisions": ["r0"]}
    )
    findings = [
        {
            "code": "FOREIGN_AUTHOR",
            "set": "edits",
            "severity": "error",
            "part": "word/document.xml",
            "location": "",
            "ref": "",
            "message": "sara.k's r0 in the original is gone",
        },
        {
            "code": "UNTRACKED_EDIT",
            "set": "edits",
            "severity": "error",
            "part": "word/document.xml",
            "location": "p0",
            "ref": "p0",
            "message": "p0 differs after rejecting PilotBot's changes",
        },
    ]
    grade, _ = _grade_run(
        tmp_path,
        monkeypatch,
        task=task,
        validate_result=SimpleNamespace(return_code=2),
        validate_findings=findings,
        source_snapshot=source,
    )
    by_name = {r.name: r for r in grade.tool_correctness}
    assert by_name["artifact-valid"].status == "pass"

    grade, _ = _grade_run(
        tmp_path,
        monkeypatch,
        task=task,
        validate_result=SimpleNamespace(return_code=2),
        validate_findings=[
            *findings,
            {
                "code": "UNTRACKED_EDIT",
                "set": "edits",
                "severity": "error",
                "part": "word/document.xml",
                "location": "p9",
                "ref": "p9",
                "message": "p9 differs after rejecting PilotBot's changes",
            },
        ],
        source_snapshot=source,
    )
    by_name = {r.name: r for r in grade.tool_correctness}
    assert by_name["artifact-valid"].status == "fail"


def test_tool_correctness_for_a_refused_run() -> None:
    from harness.grading import tool_correctness

    task = Task.model_validate(
        {
            "schema_version": 1,
            "id": "refuse",
            "family": "unsupported",
            "source": {"path": "x.docx", "sha256": "0" * 64},
            "prompt": "p {binary} {output} {author} JUBARTE_RESULT",
            "required_author": "A",
            "output_path": "out.docx",
            "tracked": True,
            "settlement": False,
            "genuinely_unsupported": True,
            "checks": [],
            "rubric": [],
            "stub": {"expected_claim": "failed", "steps": []},
        }
    )
    run = _empty_run(artifact_exists=False, claim_value="failed")
    results = tool_correctness(
        run, task, snapshot_ok=False, validate_rc=2, validate_findings=[]
    )
    by_name = {r.name: r for r in results}
    assert by_name["refused"].status == "pass"
    assert by_name["no_artifact"].status == "pass"
