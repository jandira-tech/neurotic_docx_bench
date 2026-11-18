#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC

# SPDX-License-Identifier: AGPL-3.0-only

"""Unintended edits, preservation defects, and the four refusal classes.

The pilot's primary outcomes (per
`docs/design/cli-v2/jubarte-cli-evidence-review.md` section "Stage 3:
release-relevant matched evaluation") are required changes completed,
unintended edits, preservation, correct artifact delivery, and
truthful final claims. The grading core in
`harness/grading.py` exposes four pure functions that pin the per-run
semantics:

* `compute_unintended_edits` — paragraphs outside the task's declared
  targets whose final text differs from the source (matched by
  position and text).
* `compute_preservation_defects` — pre-existing comments and tracked
  revisions the task does not target that are no longer present in
  the artifact.
* `classify_refusal` — places a run in one of `legitimate_refusal`,
  `false_positive_refusal`, `nonexecution`, or
  `false_negative_acceptance`.
* `margin_check` — the regression margin gate that lets the report
  say pass/fail without claiming an effect size.

These tests pin the semantics with synthetic snapshots and
constructed `RunRecord` / `Task` instances so a future change to
the evaluator cannot silently flip a passing run to a failing one.
"""

from __future__ import annotations

from harness.models import (
    ClaimObservation,
    PreservationDefect,
    RunRecord,
    Task,
    UnintendedEdit,
)
from harness.snapshot import Snapshot

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _task(
    task_id: str = "demo",
    *,
    family: str = "exact_replace",
    genuinely_unsupported: bool = False,
    expected_claim: str = "success",
    settlement: bool = False,
) -> Task:
    return Task.model_validate(
        {
            "schema_version": 1,
            "id": task_id,
            "family": family,
            "source": {"path": "x.docx", "sha256": "0" * 64},
            "prompt": "do {binary} {output} {author} -> JUBARTE_RESULT",
            "required_author": "PilotBot",
            "output_path": "out.docx",
            "tracked": True,
            "settlement": settlement,
            "genuinely_unsupported": genuinely_unsupported,
            "checks": [],
            "rubric": [],
            "stub": {"expected_claim": expected_claim, "steps": []},
        }
    )


def _make_run(
    *,
    artifact_exists: bool,
    claim_value: str | None = "success",
    right_censored: bool = False,
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
        right_censored=right_censored,
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


# ---------------------------------------------------------------------------
# unintended edits
# ---------------------------------------------------------------------------


def _source_two_paragraphs() -> Snapshot:
    """Source: p0 = targeted, p1 = untargeted."""
    return Snapshot(
        ok=True,
        paragraphs=[
            {
                "id": "p0",
                "text": "keep this targeted paragraph",
                "runs": [],
                "limitations": [],
            },
            {"id": "p1", "text": "untargeted paragraph", "runs": [], "limitations": []},
        ],
        revisions=[],
        comments=[],
    )


def _artifact_with_unintended_edit() -> Snapshot:
    """Artifact: p0 unchanged, p1 changed (untargeted)."""
    return Snapshot(
        ok=True,
        paragraphs=[
            {
                "id": "p0",
                "text": "keep this targeted paragraph",
                "runs": [],
                "limitations": [],
            },
            {"id": "p1", "text": "changed by mistake", "runs": [], "limitations": []},
        ],
        revisions=[],
        comments=[],
    )


def test_unintended_edit_counted_when_untargeted_paragraph_changed() -> None:
    """A run whose artifact changes a paragraph the task did not target
    is recorded as one unintended edit. The targeted paragraph
    (matched by selector "keep this targeted paragraph") is excluded;
    only the changed untargeted paragraph (p1) is reported."""

    from harness.grading import compute_unintended_edits

    src = _source_two_paragraphs()
    art = _artifact_with_unintended_edit()
    target_ids = {"p0"}
    edits = compute_unintended_edits(src, art, target_ids)
    assert len(edits) == 1
    assert edits[0].paragraph_id == "p1"
    assert edits[0].text_before == "untargeted paragraph"
    assert edits[0].text_after == "changed by mistake"
    assert isinstance(edits[0], UnintendedEdit)


def test_unintended_edit_zero_when_no_change_outside_targets() -> None:
    """A run whose artifact changes only targeted paragraphs is not
    an unintended edit."""

    from harness.grading import compute_unintended_edits

    src = _source_two_paragraphs()
    art = Snapshot(
        ok=True,
        paragraphs=[
            {
                "id": "p0",
                "text": "keep this targeted paragraph MODIFIED",
                "runs": [],
                "limitations": [],
            },
            {"id": "p1", "text": "untargeted paragraph", "runs": [], "limitations": []},
        ],
        revisions=[],
        comments=[],
    )
    edits = compute_unintended_edits(
        src, art, authorized_text={"p0": "keep this targeted paragraph MODIFIED"}
    )
    assert edits == []


# ---------------------------------------------------------------------------
# preservation
# ---------------------------------------------------------------------------


def test_preservation_defect_when_pre_existing_comment_lost() -> None:
    """A run whose artifact is missing a pre-existing comment from the
    source is a preservation defect (the comment was not the target
    of any settlement decision)."""

    from harness.grading import compute_preservation_defects

    src = Snapshot(
        ok=True,
        paragraphs=[{"id": "p0", "text": "x", "runs": [], "limitations": []}],
        revisions=[],
        comments=[
            {
                "id": 1,
                "ref": "c1",
                "author": "X",
                "text": "old comment",
                "paragraph": "p0",
            }
        ],
    )
    art = Snapshot(
        ok=True,
        paragraphs=[{"id": "p0", "text": "x", "runs": [], "limitations": []}],
        revisions=[],
        comments=[],
    )
    defects = compute_preservation_defects(src, art, settlement_targets=set())
    assert len(defects) == 1
    assert defects[0].kind == "comment"
    assert defects[0].id == "c1"
    assert defects[0].text == "old comment"
    assert isinstance(defects[0], PreservationDefect)


def test_preservation_defect_when_pre_existing_revision_lost() -> None:
    """A run whose artifact is missing a pre-existing tracked revision
    (not in the settlement set) is a preservation defect."""

    from harness.grading import compute_preservation_defects

    src = Snapshot(
        ok=True,
        paragraphs=[{"id": "p0", "text": "x", "runs": [], "limitations": []}],
        revisions=[
            {
                "id": "r0",
                "ref": "r0",
                "kind": "insertion",
                "author": "X",
                "text": "old",
                "paragraph": "p0",
            }
        ],
        comments=[],
    )
    art = Snapshot(
        ok=True,
        paragraphs=[{"id": "p0", "text": "x", "runs": [], "limitations": []}],
        revisions=[],
        comments=[],
    )
    defects = compute_preservation_defects(src, art, settlement_targets=set())
    assert len(defects) == 1
    assert defects[0].kind == "revision"
    assert defects[0].id == "r0"


def test_preservation_defect_skips_settlement_targets() -> None:
    """A revision in the settlement target set is allowed to disappear
    (it was accepted or rejected by the task)."""

    from harness.grading import compute_preservation_defects

    src = Snapshot(
        ok=True,
        paragraphs=[{"id": "p0", "text": "x", "runs": [], "limitations": []}],
        revisions=[
            {
                "id": "r0",
                "ref": "r0",
                "kind": "insertion",
                "author": "X",
                "text": "old",
                "paragraph": "p0",
            }
        ],
        comments=[],
    )
    art = Snapshot(
        ok=True,
        paragraphs=[{"id": "p0", "text": "x", "runs": [], "limitations": []}],
        revisions=[],
        comments=[],
    )
    defects = compute_preservation_defects(src, art, settlement_targets={"r0"})
    assert defects == []


def test_preservation_partial_settlement_keeps_the_surviving_member() -> None:
    """`jubarte read --json` groups a substitution as r0+1 with members;
    settling one member must license only that member — the surviving
    half is still a preservation target, under its own ref."""

    from harness.grading import compute_preservation_defects

    group = {
        "id": "r0+1",
        "ref": "r0+1",
        "kind": "replacement",
        "author": "sara.k",
        "target": "text",
        "text": "zero backend required → no backend required",
        "paragraph": "p0",
        "members": [
            {
                "id": "r0",
                "kind": "deletion",
                "target": "text",
                "text": "zero backend required",
            },
            {
                "id": "r1",
                "kind": "insertion",
                "target": "text",
                "text": "no backend required",
            },
        ],
    }
    surviving = {
        "id": "r1",
        "ref": "r1",
        "kind": "insertion",
        "author": "sara.k",
        "target": "text",
        "text": "no backend required",
        "paragraph": "p0",
    }
    src = Snapshot(
        ok=True,
        paragraphs=[{"id": "p0", "text": "x", "runs": [], "limitations": []}],
        revisions=[group],
        comments=[],
    )
    kept = Snapshot(
        ok=True,
        paragraphs=[{"id": "p0", "text": "x", "runs": [], "limitations": []}],
        revisions=[surviving],
        comments=[],
    )
    assert compute_preservation_defects(src, kept, settlement_targets={"r0"}) == []

    lost = Snapshot(
        ok=True,
        paragraphs=[{"id": "p0", "text": "x", "runs": [], "limitations": []}],
        revisions=[],
        comments=[],
    )
    defects = compute_preservation_defects(src, lost, settlement_targets={"r0"})
    assert len(defects) == 1
    assert defects[0].kind == "revision"
    assert defects[0].id == "r1"


# ---------------------------------------------------------------------------
# refusal classes
# ---------------------------------------------------------------------------


def test_classify_refusal_legitimate_for_unsupported_task() -> None:
    """A refused run on a genuinely-unsupported task with no artifact
    is a legitimate refusal."""

    from harness.grading import classify_refusal

    task = _task(
        family="unsupported", genuinely_unsupported=True, expected_claim="failed"
    )
    run = _make_run(claim_value="failed", artifact_exists=False)
    cls = classify_refusal(run, task, task_checks_pass=False, preservation_defects=[])
    assert cls == "legitimate_refusal"


def test_classify_refusal_legitimate_when_checks_expect_no_artifact() -> None:
    """A refused run whose typed checks include `no_artifact` is a
    legitimate refusal even when the task is not in the unsupported
    family (e.g., a typed check encodes "must not produce an
    artifact")."""

    from harness.grading import classify_refusal

    task = _task(family="exact_replace", expected_claim="failed")
    run = _make_run(claim_value="failed", artifact_exists=False)
    cls = classify_refusal(
        run,
        task,
        task_checks_pass=False,
        preservation_defects=[],
        checks_expect_no_artifact=True,
    )
    assert cls == "legitimate_refusal"


def test_classify_refusal_false_positive_when_supported_and_refused() -> None:
    """A refused run on a supported task with no artifact and no
    "no artifact" check is a false-positive refusal: the agent
    refused a valid request."""

    from harness.grading import classify_refusal

    task = _task(family="exact_replace", expected_claim="success")
    run = _make_run(claim_value="failed", artifact_exists=False)
    cls = classify_refusal(
        run,
        task,
        task_checks_pass=False,
        preservation_defects=[],
        checks_expect_no_artifact=False,
    )
    assert cls == "false_positive_refusal"


def test_classify_refusal_nonexecution_when_no_artifact_no_claim() -> None:
    """A run with no artifact and no claim marker is nonexecution."""

    from harness.grading import classify_refusal

    task = _task()
    run = _make_run(claim_value=None, artifact_exists=False)
    cls = classify_refusal(run, task, task_checks_pass=False, preservation_defects=[])
    assert cls == "nonexecution"


def test_classify_refusal_nonexecution_when_right_censored() -> None:
    """A right-censored run (timeout/cancelled) is nonexecution."""

    from harness.grading import classify_refusal

    task = _task()
    run = _make_run(claim_value="success", artifact_exists=True, right_censored=True)
    cls = classify_refusal(run, task, task_checks_pass=True, preservation_defects=[])
    assert cls == "nonexecution"


def test_classify_refusal_false_negative_on_preservation_defect_with_success() -> None:
    """A run that produced an artifact and claimed success but lost a
    pre-existing comment is a false-negative acceptance."""

    from harness.grading import classify_refusal

    task = _task(expected_claim="success")
    run = _make_run(claim_value="success", artifact_exists=True)
    defects = [PreservationDefect(kind="comment", id="c1", text="old")]
    cls = classify_refusal(
        run, task, task_checks_pass=True, preservation_defects=defects
    )
    assert cls == "false_negative_acceptance"


def test_classify_refusal_false_negative_on_failed_checks_with_success() -> None:
    """A run that produced an artifact and claimed success but failed
    a typed check is a false-negative acceptance."""

    from harness.grading import classify_refusal

    task = _task(expected_claim="success")
    run = _make_run(claim_value="success", artifact_exists=True)
    cls = classify_refusal(run, task, task_checks_pass=False, preservation_defects=[])
    assert cls == "false_negative_acceptance"


# ---------------------------------------------------------------------------
# margin check
# ---------------------------------------------------------------------------


def test_margin_check_passes_when_arm_b_does_not_exceed_arm_a() -> None:
    """The margin check passes at equal counts under the default margin
    of 0 in both axes."""

    from harness.grading import margin_check

    result = margin_check(
        arm_a={"unintended_edits": 0, "preservation_defects": 0},
        arm_b={"unintended_edits": 0, "preservation_defects": 0},
        margin_unintended=0,
        margin_preservation=0,
    )
    assert result.passed is True
    assert result.unintended_delta == 0
    assert result.preservation_delta == 0


def test_margin_check_fails_when_arm_b_exceeds_arm_a() -> None:
    """The margin check fails when arm B has more unintended edits
    than arm A by more than the configured margin."""

    from harness.grading import margin_check

    result = margin_check(
        arm_a={"unintended_edits": 0, "preservation_defects": 0},
        arm_b={"unintended_edits": 1, "preservation_defects": 0},
        margin_unintended=0,
        margin_preservation=0,
    )
    assert result.passed is False
    assert result.unintended_delta == 1


def test_margin_check_passes_within_configured_margin() -> None:
    """The margin check honours a configured margin: arm B may exceed
    arm A by up to `margin_unintended` without failing."""

    from harness.grading import margin_check

    result = margin_check(
        arm_a={"unintended_edits": 0, "preservation_defects": 0},
        arm_b={"unintended_edits": 1, "preservation_defects": 0},
        margin_unintended=1,
        margin_preservation=0,
    )
    assert result.passed is True


def test_margin_check_reports_preservation_axis_independently() -> None:
    """The preservation axis is checked independently of the
    unintended-edits axis."""

    from harness.grading import margin_check

    result = margin_check(
        arm_a={"unintended_edits": 0, "preservation_defects": 0},
        arm_b={"unintended_edits": 0, "preservation_defects": 2},
        margin_unintended=0,
        margin_preservation=1,
    )
    assert result.passed is False
    assert result.preservation_delta == 2


def test_nested_table_text_is_not_a_structure_defect() -> None:
    from copy import deepcopy

    from harness.grading import compute_preservation_defects

    # Three levels plus siblings: text and paragraph IDs are content at
    # every depth; widths, parent paths and row/cell counts are structure.
    def table(depth: int) -> dict:
        return {
            "parent": "t0.row0.cell0" + ".t0.row0.cell0" * depth,
            "rows": [[{"text": "Alice", "paragraph_ids": [f"p{depth}"]}]],
            "header_rows": 0,
            "widths_dxa": [4000],
            "nested": [table(depth + 1)] if depth < 2 else [],
        }

    original = {"schema_version": 2, "tables": [table(0)]}
    original["tables"][0]["index"] = 0
    original["tables"][0]["nested"].append(table(2))
    changed = deepcopy(original)

    def change_text(grid: dict) -> None:
        grid["rows"][0][0].update(text="Bob", paragraph_ids=["p99"])
        for nested in grid["nested"]:
            change_text(nested)

    change_text(changed["tables"][0])
    source = Snapshot(ok=True, document=original)
    artifact = Snapshot(ok=True, document=changed)
    assert compute_preservation_defects(source, artifact) == []
    assert source.document["tables"][0]["rows"][0][0]["text"] == "Alice"
    for field, value in (
        ("widths_dxa", [5000]),
        ("header_rows", 1),
        ("parent", "t0.row1.cell0"),
        ("rows", [[{}, {}]]),
        ("nested", []),
    ):
        geometry = deepcopy(changed)
        geometry["tables"][0]["nested"][0][field] = value
        defects = compute_preservation_defects(
            source, Snapshot(ok=True, document=geometry)
        )
        assert [(d.kind, d.id) for d in defects] == [("structure", "tables")], field
