#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC

# SPDX-License-Identifier: AGPL-3.0-only

"""Pydantic model round-trips and discriminator dispatch.

The harness serializes and parses every record it touches: tasks,
runs, grades. A round-trip is the cheapest way to catch a structural
mistake before it leaks into a JSONL ledger.
"""

from __future__ import annotations

import pytest

from harness.models import (
    GradeRecord,
    RubricAssessment,
    RunRecord,
    Task,
    canonical_task_sha256,
)


def test_task_discriminator_dispatches_all_check_kinds() -> None:
    payload = {
        "schema_version": 1,
        "id": "demo",
        "family": "exact_replace",
        "source": {"path": "x.docx", "sha256": "0" * 64},
        "prompt": "do {binary} {output} {author} -> JUBARTE_RESULT: success",
        "required_author": "PilotBot",
        "output_path": "out.docx",
        "tracked": True,
        "settlement": False,
        "genuinely_unsupported": False,
        "checks": [
            {"kind": "text_contains", "text": "foo"},
            {"kind": "text_contains", "text": "bar", "selector": {"contains": "foo"}},
            {"kind": "text_equals", "selector": {"contains": "foo"}, "text": "bar"},
            {"kind": "text_absent", "text": "baz"},
            {"kind": "text_absent", "text": "baz", "selector": {"contains": "foo"}},
            {"kind": "revision_count", "min": 1, "max": 2},
            {"kind": "revision_present", "text": "x", "author": "A"},
            {"kind": "comment_present", "text": "x", "author": "A", "done": True},
            {"kind": "no_artifact"},
        ],
        "rubric": [
            {"id": "r1", "description": "x"},
        ],
        "stub": {"expected_claim": "success", "steps": []},
    }
    task = Task.model_validate(payload)
    kinds = [type(c).__name__ for c in task.checks]
    assert kinds == [
        "TextContains",
        "TextContains",
        "TextEquals",
        "TextAbsent",
        "TextAbsent",
        "RevisionCount",
        "RevisionPresent",
        "CommentPresent",
        "NoArtifact",
    ]
    # The round-trip must be lossless under mode="json".
    again = Task.model_validate_json(task.model_dump_json())
    assert again.checks[2].selector.contains == "foo"


def test_task_rejects_relative_or_dotty_output_paths() -> None:
    payload = {
        "schema_version": 1,
        "id": "bad",
        "family": "exact_replace",
        "source": {"path": "x.docx", "sha256": "0" * 64},
        "prompt": "{binary} {output} {author} -> JUBARTE_RESULT",
        "required_author": "A",
        "output_path": "../escape.docx",
        "tracked": True,
        "settlement": False,
        "genuinely_unsupported": False,
        "checks": [],
        "rubric": [],
        "stub": {"expected_claim": "success", "steps": []},
    }
    with pytest.raises(Exception):
        Task.model_validate(payload)


def test_run_record_round_trips() -> None:
    record = RunRecord(
        run_id="abc",
        pilot_id="pilot",
        task_id="t1",
        task_family="exact_replace",
        task_sha256="0" * 64,
        arm="A",
        arm_binary_path="/bin/jubarte",
        arm_binary_sha256="0" * 64,
        agent_name="stub",
        agent_argv=["stub"],
        repetition=0,
        order_index=0,
        seed=42,
        started_at="2026-10-17T00:00:00Z",
        ended_at="2026-10-17T00:01:00Z",
        duration_seconds=60.0,
        timeout_seconds=120.0,
        return_code=0,
        stop_reason="exit",
        right_censored=False,
        run_dir="/tmp/run",
        prompt_path="/tmp/run/prompt.md",
        prompt_sha256="0" * 64,
        input_path="/tmp/run/input.docx",
        input_sha256="0" * 64,
        stdout_path="/tmp/run/stdout.txt",
        stderr_path="/tmp/run/stderr.txt",
        stdout_sha256="0" * 64,
        stderr_sha256="0" * 64,
        stdout_bytes=10,
        stderr_bytes=0,
        declared_output_path="/tmp/run/out.docx",
        artifact_path="/tmp/run/out.docx",
        artifact_exists=True,
        artifact_sha256="1" * 64,
        artifact_bytes=42,
        run_dir_files=["out.docx"],
        claim=None,
    )
    as_json = record.model_dump_json()
    again = RunRecord.model_validate_json(as_json)
    assert again.run_id == "abc"
    assert again.artifact_exists is True


def test_canonical_task_sha256_is_stable_and_order_independent() -> None:
    payload = {
        "schema_version": 1,
        "id": "demo",
        "family": "exact_replace",
        "source": {"path": "x.docx", "sha256": "0" * 64},
        "prompt": "do {binary} {output} {author} -> JUBARTE_RESULT",
        "required_author": "PilotBot",
        "output_path": "out.docx",
        "tracked": True,
        "settlement": False,
        "genuinely_unsupported": False,
        "checks": [{"kind": "text_contains", "text": "foo"}],
        "rubric": [{"id": "r1", "description": "x"}],
        "stub": {"expected_claim": "success", "steps": []},
    }
    task = Task.model_validate(payload)
    digest = canonical_task_sha256(task)
    again = Task.model_validate(payload)
    assert canonical_task_sha256(again) == digest


def test_grade_record_omits_unassessed_rubric() -> None:
    grade = GradeRecord(
        run_id="r",
        task_id="t",
        task_family="exact_replace",
        arm="A",
        repetition=0,
        right_censored=False,
        artifact_exists=True,
        tool_correctness=[],
        tool_correctness_overall=True,
        task_checks=[],
        task_completion_overall=True,
        rubric=[RubricAssessment(id="r1", description="x", status="unassessed")],
        claim_value="success",
        claim_expected="success",
        claim_accuracy="accurate",
        claim_detail="",
        graded_at="2026-10-17T00:00:00Z",
        grader_binary_path="/bin/j",
        grader_binary_sha256="0" * 64,
    )
    assert grade.rubric[0].status == "unassessed"
    assert grade.claim_accuracy == "accurate"
