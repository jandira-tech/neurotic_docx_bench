#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC

# SPDX-License-Identifier: AGPL-3.0-only

"""Shared pydantic records for the held-out paired workflow pilot.

Every structure that reaches a JSONL ledger or a task file is a pydantic
model here: tasks and their typed checks, the run configuration, the
one-row-per-run execution record, and the three-axis grade. `docs/design/
cli-v2/jubarte-edit-implementation-plan.md` section 6 fixes what the harness
owns (status capture, budgets, termination metadata, artifact collection);
these models are that boundary made concrete.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCHEMA_VERSION = 1

Family = Literal[
    "exact_replace",
    "multi_edit",
    "received_redline",
    "comments",
    "template_flow",
    "unsupported",
]

FAMILIES: tuple[Family, ...] = (
    "exact_replace",
    "multi_edit",
    "received_redline",
    "comments",
    "template_flow",
    "unsupported",
)

ClaimValue = Literal["success", "unsupported", "failed"]
StopReason = Literal["exit", "timeout", "cancelled"]

# Primary outcomes beyond the three-axis grade
# (docs/design/cli-v2/jubarte-cli-evidence-review.md section "Stage 3").
RefusalClass = Literal[
    "legitimate_refusal",
    "false_positive_refusal",
    "nonexecution",
    "false_negative_acceptance",
]
REFUSAL_CLASSES: tuple[RefusalClass, ...] = (
    "legitimate_refusal",
    "false_positive_refusal",
    "nonexecution",
    "false_negative_acceptance",
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FixtureRef(StrictModel):
    """A docx already in this repository, pinned by relative path and sha256."""

    path: str
    sha256: str


class Selector(StrictModel):
    """Locates one paragraph in the artifact snapshot by a unique substring.

    The selector is matched against the paragraph's final logical text
    (insertions applied, deletions removed) and must match exactly one
    paragraph, so checks stay meaningful after tracked edits renumber ids.
    """

    contains: str


class TextEquals(StrictModel):
    kind: Literal["text_equals"] = "text_equals"
    selector: Selector
    text: str


class TextContains(StrictModel):
    kind: Literal["text_contains"] = "text_contains"
    text: str
    selector: Selector | None = None


class TextAbsent(StrictModel):
    kind: Literal["text_absent"] = "text_absent"
    text: str
    selector: Selector | None = None


class RevisionCount(StrictModel):
    kind: Literal["revision_count"] = "revision_count"
    min: int = 0
    max: int


class RevisionAbsent(StrictModel):
    kind: Literal["revision_absent"] = "revision_absent"
    ref: str


class RevisionPresent(StrictModel):
    """Some revision carries text containing `text`, optionally by `author`."""

    kind: Literal["revision_present"] = "revision_present"
    text: str
    author: str | None = None


class CommentPresent(StrictModel):
    """A comment whose text contains `text`, optionally by `author` and done."""

    kind: Literal["comment_present"] = "comment_present"
    text: str
    author: str | None = None
    done: bool | None = None
    ref: str | None = None
    parent_ref: str | None = None
    paragraph: str | None = None
    anchor_text: str | None = None


class NoArtifact(StrictModel):
    """The declared output must not exist (unsupported-report tasks)."""

    kind: Literal["no_artifact"] = "no_artifact"


Check = Annotated[
    TextEquals
    | TextContains
    | TextAbsent
    | RevisionCount
    | RevisionPresent
    | RevisionAbsent
    | CommentPresent
    | NoArtifact,
    Field(discriminator="kind"),
]


class RubricItem(StrictModel):
    """A quality judgment only an external grader can make.

    The harness never fills these in; an external adjudication step must do so.
    """

    id: str
    description: str
    status: Literal["unassessed", "pass", "fail"] = "unassessed"
    note: str | None = None


class StubStep(StrictModel):
    """One jubarte CLI invocation the deterministic stub agent replays.

    `argv` may reference `{binary}`, `{input}`, `{output}`, `{author}` and
    relative filenames inside the run directory; `out` names the file this
    step writes (`{output}` or an intermediate such as `tmp1.docx`) so the
    stub can reroute it under the no-artifact fail mode. `expect_rc` is the
    return code the stub treats as the expected outcome (3 for refusals).
    """

    argv: list[str]
    out: str | None = None
    expect_rc: int = 0


class StubSpec(StrictModel):
    """How the model-free stub agent performs this task, for tests/smoke."""

    expected_claim: ClaimValue
    steps: list[StubStep] = Field(default_factory=list)


class Task(StrictModel):
    """One held-out pilot task."""

    schema_version: int = SCHEMA_VERSION
    id: str
    family: Family
    source: FixtureRef
    prompt: str
    required_author: str
    output_path: str
    tracked: bool = True
    settlement: bool = False
    genuinely_unsupported: bool = False
    checks: list[Check] = Field(default_factory=list)
    rubric: list[RubricItem] = Field(default_factory=list)
    stub: StubSpec
    expected_paragraphs: dict[str, str] = Field(default_factory=dict)
    comment_updates: dict[str, dict[str, Any]] = Field(default_factory=dict)
    settled_revisions: list[str] = Field(default_factory=list)
    coverage_tags: list[str] = Field(default_factory=list)
    unchanged: bool = False

    @field_validator("output_path")
    @classmethod
    def _plain_name(cls, value: str) -> str:
        if Path(value).name != value or value in (".", ".."):
            raise ValueError(f"output_path must be a bare file name: {value!r}")
        return value


class AgentConfig(StrictModel):
    """A command template for one agent CLI, with provenance strings.

    `argv` entries may contain the placeholders `{binary}` (the arm's
    jubarte binary), `{input}`, `{output}`, `{prompt_file}`, `{prompt}`,
    `{task_file}`, `{run_dir}`, `{author}` and `{fail_mode}`.
    """

    name: str
    argv: list[str]
    model: str | None = None
    provider: str | None = None
    version: str | None = None
    version_argv: list[str] = Field(default_factory=list)
    stub: bool = False


class ArmConfig(StrictModel):
    """One interface arm: a jubarte binary pinned by path and sha256."""

    label: Literal["A", "B"]
    binary: str
    sha256: str
    role: str


class OrderEntry(StrictModel):
    """One cell of the randomized execution order."""

    order_index: int
    task_id: str
    arm: Literal["A", "B"]
    repetition: int


class RunConfig(StrictModel):
    """Everything a pilot run was bound to, written beside the ledger."""

    schema_version: int = SCHEMA_VERSION
    pilot_id: str
    seed: int
    repetitions: int = Field(ge=1)
    margin_unintended: int = Field(ge=0)
    margin_preservation: int = Field(ge=0)
    seed_scope: str = "cell ordering only; not a model sampling seed"
    timeout_seconds: float = Field(gt=0)
    fail_mode: str
    agent: AgentConfig
    arms: list[ArmConfig]
    order: list[OrderEntry]
    created_at: str
    task_families: dict[str, Family] = Field(default_factory=dict)


class ClaimObservation(StrictModel):
    """The result marker the task prompt asks the agent to print last."""

    raw: str
    value: ClaimValue


class RunRecord(StrictModel):
    """One executed run: the harness's own observations only.

    Success is never inferred from a log tail or a shell status: the only
    delivery facts here are the scanned artifact path, its sha256 and its
    size. Right-censored runs (timeout, cancelled) stay in the ledger and
    therefore in every denominator.
    """

    schema_version: int = SCHEMA_VERSION
    run_id: str
    pilot_id: str
    task_id: str
    task_family: Family
    task_sha256: str
    arm: Literal["A", "B"]
    arm_binary_path: str
    arm_binary_sha256: str
    agent_name: str
    agent_model: str | None = None
    agent_provider: str | None = None
    agent_version: str | None = None
    agent_argv: list[str]
    repetition: int
    order_index: int
    seed: int
    seed_scope: str = "cell ordering only; not a model sampling seed"
    started_at: str
    ended_at: str | None = None
    duration_seconds: float | None = None
    timeout_seconds: float
    return_code: int | None = None
    stop_reason: StopReason
    right_censored: bool
    run_dir: str
    prompt_path: str
    prompt_sha256: str
    input_path: str
    input_sha256: str
    stdout_path: str
    stderr_path: str
    stdout_sha256: str | None = None
    stderr_sha256: str | None = None
    stdout_bytes: int = 0
    stderr_bytes: int = 0
    declared_output_path: str
    artifact_path: str
    artifact_exists: bool
    artifact_sha256: str | None = None
    artifact_bytes: int | None = None
    run_dir_files: list[str] = Field(default_factory=list)
    claim: ClaimObservation | None = None


class CheckResult(StrictModel):
    """The outcome of one typed check against the artifact snapshot."""

    check: dict[str, Any]
    status: Literal["pass", "fail", "error"]
    detail: str


class UnintendedEdit(StrictModel):
    """One artifact paragraph outside the task's declared targets whose
    final text differs from the source.

    `paragraph_id` is the source-side paragraph id when present; the
    sequence text alignment method is documented in
    `grading.compute_unintended_edits`.
    """

    paragraph_id: str | None
    text_before: str
    text_after: str
    adjudication_required: bool = False


class PreservationDefect(StrictModel):
    """A pre-existing comment or tracked revision the task did not
    target that is absent or materially altered in the artifact, or an
    exposed structural property that changed. Unexposed dimensions are
    listed separately as not assessed."""

    kind: Literal["comment", "revision", "structure"]
    id: str
    text: str


class NamedResult(StrictModel):
    name: str
    status: Literal["pass", "fail", "error", "not_run"]
    detail: str = ""


class RubricAssessment(StrictModel):
    id: str
    description: str
    status: Literal["unassessed", "pass", "fail"]
    note: str | None = None


class GradeRecord(StrictModel):
    """The three-axis grade for one run, plus the primary outcomes the
    design requires.

    tool_correctness asks whether declared operations were realized or
    correctly refused (artifact-level CLI checks); task_completion asks
    whether the typed user requirements hold (rubric items stay unassessed
    unless an external grader supplies them); claim_accuracy asks whether
    the final response's success/failure/unsupported claim matches the
    artifact and the checks.

    `unintended_edits`, `preservation_defects`, and `refusal_class` add
    the primary outcomes (unintended edits, preservation, refusal
    classification) the design requires alongside the three axes.
    """

    schema_version: int = SCHEMA_VERSION
    run_id: str
    task_id: str
    task_family: Family
    arm: Literal["A", "B"]
    repetition: int
    right_censored: bool
    artifact_exists: bool
    tool_correctness: list[NamedResult]
    tool_correctness_overall: bool
    task_checks: list[CheckResult]
    task_completion_overall: bool
    rubric: list[RubricAssessment]
    claim_value: ClaimValue | None = None
    claim_expected: ClaimValue
    claim_accuracy: Literal["accurate", "inaccurate", "missing"]
    claim_detail: str
    unintended_edits: list[UnintendedEdit] = Field(default_factory=list)
    unintended_edit_count: int | None = None
    preservation_defects: list[PreservationDefect] = Field(default_factory=list)
    preservation_defect_count: int | None = None
    preservation_status: Literal["assessed", "not_assessed"] = "not_assessed"
    unassessed: list[str] = Field(default_factory=list)
    inspection_errors: list[str] = Field(default_factory=list)
    refusal_class: RefusalClass | None = None
    graded_at: str
    grader_binary_path: str
    grader_binary_sha256: str


class MarginResult(StrictModel):
    """The pass/fail result of the regression-margin gate.

    The margin is a configured allowance (default 0 in both axes):
    arm B may exceed arm A by up to `margin_unintended` unintended
    edits and up to `margin_preservation` preservation defects
    without failing the gate. A positive `passed=False` is not an
    effect-size claim; it says only that the configured margin was
    exceeded.
    """

    passed: bool
    margin_unintended: int
    margin_preservation: int
    unintended_delta: int
    preservation_delta: int
    reason: str


def canonical_task_sha256(task: Task) -> str:
    """A stable digest of the task record (sorted keys, no whitespace)."""
    import hashlib
    import json

    payload = json.dumps(
        task.model_dump(mode="json", exclude_none=True),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
