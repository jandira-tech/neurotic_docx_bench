#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC

# SPDX-License-Identifier: AGPL-3.0-only

"""The grading core.

Three axes per run:

* **tool_correctness** — `jubarte read --json` and `jubarte validate`
  against the artifact, plus the no-artifact check for a refused run.
* **task_completion** — typed checks (text, revision, comment)
  against the snapshot.
* **claim_accuracy** — does the agent's printed `JUBARTE_RESULT:`
  marker agree with what the artifact and the checks actually show?

Plus the primary outcomes the design requires
(`docs/design/cli-v2/jubarte-cli-evidence-review.md` section
"Stage 3"):

* **unintended edits** — paragraphs outside the task's declared
  targets whose final text differs from the source
  (`compute_unintended_edits`).
* **preservation** — pre-existing comments and tracked revisions
  the task does not target that are no longer present in the
  artifact (`compute_preservation_defects`).
* **refusal class** — places a run in one of
  `legitimate_refusal`, `false_positive_refusal`, `nonexecution`,
  or `false_negative_acceptance` (`classify_refusal`).

The report applies a regression margin
(`margin_check`) that says pass/fail without claiming an effect
size; trials are expanded where release-relevant uncertainty
remains.

`grade.py` is a thin CLI wrapper around this module; the tests import
the functions directly so the snapshot parser and the per-check
semantics can be exercised in isolation.
"""

from __future__ import annotations

import hashlib
import subprocess
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable, Literal

from harness.models import (
    CheckResult,
    ClaimValue,
    GradeRecord,
    MarginResult,
    NamedResult,
    PreservationDefect,
    RefusalClass,
    RubricAssessment,
    RunRecord,
    Task,
    UnintendedEdit,
)
from harness.snapshot import (
    Snapshot,
    paragraph_key,
    paragraph_rows,
    read_snapshot,
    validate,
)


class _EmptySnapshot:
    paragraphs: list[dict] = []
    revisions: list[dict] = []
    comments: list[dict] = []


def empty_snapshot() -> _EmptySnapshot:
    return _EmptySnapshot()


# Cache snapshots by source bytes and reader binary identity. The pilot
# loads at most a handful of fixtures; one snapshot per path per
# process is enough.
_SOURCE_SNAPSHOT_CACHE: dict[tuple[str, str, str, str], Snapshot] = {}


def _source_snapshot(binary: Path, source_path: Path) -> Snapshot:
    key = (
        str(source_path),
        hashlib.sha256(source_path.read_bytes()).hexdigest(),
        str(binary),
        hashlib.sha256(binary.read_bytes()).hexdigest(),
    )
    if key in _SOURCE_SNAPSHOT_CACHE:
        return _SOURCE_SNAPSHOT_CACHE[key]
    snap = read_snapshot(binary, source_path)
    _SOURCE_SNAPSHOT_CACHE[key] = snap
    return snap


def reset_source_snapshot_cache() -> None:
    """Drop the source-snapshot cache (tests)."""
    _SOURCE_SNAPSHOT_CACHE.clear()


def compute_unintended_edits(
    source_snap: Snapshot,
    artifact_snap: Snapshot,
    target_paragraph_ids: Iterable[str] | None = None,
    *,
    authorized_text: dict[str, str] | None = None,
) -> list[UnintendedEdit]:
    """Align story text sequences; authorize exact desired results only.

    Enumerated paragraph IDs cannot align additions/deletions. Repeated
    text in unequal sequences is explicitly marked for adjudication.
    A target ID alone never licenses arbitrary paragraph changes.
    """
    authorized = authorized_text or {}
    src, art = paragraph_rows(source_snap), paragraph_rows(artifact_snap)
    edits = []
    for story in sorted({p["_story"] for p in src + art}):
        before = [p for p in src if p["_story"] == story]
        after = [p for p in art if p["_story"] == story]
        a, b = (
            [p.get("text", "") or "" for p in before],
            [p.get("text", "") or "" for p in after],
        )
        ambiguous = len(a) != len(b) and any(n > 2 for n in Counter(a + b).values())
        for tag, i, j, k, stop in SequenceMatcher(
            a=a, b=b, autojunk=False
        ).get_opcodes():
            if tag == "equal":
                continue
            for offset in range(max(j - i, stop - k)):
                old = before[i + offset] if i + offset < j else None
                new = after[k + offset] if k + offset < stop else None
                old_text, new_text = (
                    (old or {}).get("text", ""),
                    (new or {}).get("text", ""),
                )
                key = paragraph_key(old) if old is not None else None
                if (
                    old is not None
                    and new is not None
                    and key is not None
                    and authorized.get(key) == new_text
                ):
                    continue
                edits.append(
                    UnintendedEdit(
                        paragraph_id=key,
                        text_before=old_text,
                        text_after=new_text,
                        adjudication_required=ambiguous,
                    )
                )
    return edits


def entity_ref(row: dict, kind: str) -> str:
    value = str(row.get("ref") or row.get("id", ""))
    prefix = "c" if kind == "comment" else "r"
    return value if value.startswith(prefix) else prefix + value


def compute_preservation_defects(
    source_snap: Snapshot,
    artifact_snap: Snapshot,
    *,
    settlement_targets: Iterable[str] | None = None,
    comment_updates: dict[str, dict] | None = None,
) -> list[PreservationDefect]:
    """Compare preserved entity content, anchoring and exposed structure.

    Missing snapshot dimensions are reported separately as not assessed;
    these defects refer only to fields actually exposed by the reader.
    """
    allowed = set(settlement_targets or ())
    defects = []

    def entities(kind: str, rows: Iterable[dict]) -> Iterable[dict]:
        """`jubarte read --json` groups a substitution as one row whose
        `members` carry the per-change ids the task files name. Compare
        member by member so settling r0 of r0+1 licenses only r0."""
        for row in rows:
            members = row.get("members") if kind == "revision" else None
            if not members:
                yield row
                continue
            for member in members:
                merged = {k: v for k, v in row.items() if k != "members"}
                merged.update(member)
                merged.pop("ref", None)
                yield merged

    for kind, src, art in (
        (
            "revision",
            entities("revision", source_snap.revisions),
            entities("revision", artifact_snap.revisions),
        ),
        ("comment", source_snap.comments, artifact_snap.comments),
    ):
        by_ref = {entity_ref(row, kind): row for row in art}
        for row in src:
            ref = entity_ref(row, kind)
            if ref in allowed:
                continue
            expected = dict(row)
            if kind == "comment":
                expected.update((comment_updates or {}).get(ref, {}))
            actual = by_ref.get(ref)
            # Context strings may change when authorized adjacent text changes.
            fields = (
                (
                    "author",
                    "text",
                    "parent",
                    "parent_id",
                    "done",
                    "paragraph",
                    "last_paragraph",
                    "anchor_text",
                )
                if kind == "comment"
                else ("kind", "author", "text", "target", "paragraph")
            )
            if actual is None or any(expected.get(f) != actual.get(f) for f in fields):
                defects.append(
                    PreservationDefect(kind=kind, id=ref, text=row.get("text", ""))
                )
    # A text diff cannot establish preservation of formatting on rewritten
    # spans. Untouched paragraph formatting and exposed paragraph properties
    # are compared, along with table geometry and control metadata.
    src, art = paragraph_rows(source_snap), paragraph_rows(artifact_snap)
    for story in sorted({p["_story"] for p in src + art}):
        before_rows = [p for p in src if p["_story"] == story]
        after_rows = [p for p in art if p["_story"] == story]
        matcher = SequenceMatcher(
            a=[p.get("text", "") for p in before_rows],
            b=[p.get("text", "") for p in after_rows],
            autojunk=False,
        )
        for _, i, j, k, stop in matcher.get_opcodes():
            for before, after in zip(before_rows[i:j], after_rows[k:stop]):
                fields = (set(before) | set(after)) - {
                    "index",
                    "id",
                    "text",
                    "limitations",
                    "_story",
                    "runs",
                }
                changed = any(before.get(f) != after.get(f) for f in fields)
                if before.get("text") == after.get("text"):
                    changed |= before.get("runs") != after.get("runs")
                if changed:
                    defects.append(
                        PreservationDefect(
                            kind="structure",
                            id=paragraph_key(before),
                            text="paragraph properties/formatting differ",
                        )
                    )

    def table_structure(table):
        return {
            **{k: v for k, v in table.items() if k not in ("index", "rows", "nested")},
            "rows": [
                [
                    {
                        k: v
                        for k, v in cell.items()
                        if k not in ("text", "paragraph_ids")
                    }
                    for cell in row
                ]
                for row in table.get("rows", [])
            ],
            "nested": [table_structure(child) for child in table.get("nested", [])],
        }

    def structure(document):
        document = document or {}
        tables = [table_structure(table) for table in document.get("tables", [])]
        summary = document.get("summary", {})
        return dict(
            tables=tables,
            controls=document.get("controls", []),
            summary={
                k: v
                for k, v in summary.items()
                if k not in ("paragraphs", "comments", "revisions", "track_changes")
            },
        )

    a, b = (
        structure(getattr(source_snap, "document", None)),
        structure(getattr(artifact_snap, "document", None)),
    )
    for key in a:
        if a[key] != b[key]:
            defects.append(
                PreservationDefect(
                    kind="structure", id=key, text=f"exposed {key} differ"
                )
            )
    return defects


def classify_refusal(
    run: RunRecord,
    task: Task,
    *,
    task_checks_pass: bool,
    preservation_defects: list[PreservationDefect],
    checks_expect_no_artifact: bool | None = None,
    unintended_edits: list | None = None,
    validation_ok: bool = True,
) -> RefusalClass | None:
    """Place a run in one of `legitimate_refusal`,
    `false_positive_refusal`, `nonexecution`, or
    `false_negative_acceptance`.

    `checks_expect_no_artifact` defaults to "the task is in the
    unsupported family or any typed check is `no_artifact`"; callers
    that already know the answer (e.g., a stub that computed it) may
    pass it explicitly.
    """

    if checks_expect_no_artifact is None:
        checks_expect_no_artifact = task.genuinely_unsupported or any(
            getattr(c, "kind", None) == "no_artifact" for c in task.checks
        )

    no_artifact = not run.artifact_exists
    claim = run.claim.value if run.claim is not None else None  # type: ignore[assignment]

    if run.right_censored:
        return "nonexecution"

    if no_artifact:
        if claim is None:
            return "nonexecution"
        if claim in ("failed", "unsupported"):
            if checks_expect_no_artifact:
                return "legitimate_refusal"
            return "false_positive_refusal"
        return "nonexecution"

    has_defect = (
        bool(preservation_defects)
        or not task_checks_pass
        or bool(unintended_edits)
        or not validation_ok
    )
    if claim == "success" and has_defect:
        return "false_negative_acceptance"

    return None


def margin_check(
    *,
    arm_a: dict[str, int],
    arm_b: dict[str, int],
    margin_unintended: int = 0,
    margin_preservation: int = 0,
) -> MarginResult:
    """Apply the regression margin: arm B may exceed arm A by up to
    `margin_unintended` unintended edits and up to
    `margin_preservation` preservation defects without failing.

    The result is a pass/fail statement, never an effect-size claim.
    Trials are expanded where release-relevant uncertainty remains;
    see the report's expansion note.
    """

    a_un = int(arm_a.get("unintended_edits", 0))
    a_pr = int(arm_a.get("preservation_defects", 0))
    b_un = int(arm_b.get("unintended_edits", 0))
    b_pr = int(arm_b.get("preservation_defects", 0))
    un_delta = b_un - a_un
    pr_delta = b_pr - a_pr
    over_un = un_delta > margin_unintended
    over_pr = pr_delta > margin_preservation
    passed = not (over_un or over_pr)
    if passed:
        reason = (
            f"arm B - arm A: unintended_edits {un_delta:+d} (margin "
            f"{margin_unintended}), preservation_defects {pr_delta:+d} "
            f"(margin {margin_preservation}); within margin"
        )
    else:
        reasons = []
        if over_un:
            reasons.append(
                f"unintended_edits {un_delta:+d} exceeds margin {margin_unintended}"
            )
        if over_pr:
            reasons.append(
                f"preservation_defects {pr_delta:+d} exceeds margin "
                f"{margin_preservation}"
            )
        reason = "arm B exceeds arm A: " + "; ".join(reasons)
    return MarginResult(
        passed=passed,
        margin_unintended=margin_unintended,
        margin_preservation=margin_preservation,
        unintended_delta=un_delta,
        preservation_delta=pr_delta,
        reason=reason,
    )


def _revisions_with_text(snapshot, text: str, author: str | None) -> int:
    matches = 0
    for row in snapshot.revisions:
        if author is not None and row.get("author") != author:
            continue
        if text in (row.get("text") or ""):
            matches += 1
    return matches


def tool_correctness(
    run: RunRecord,
    task: Task,
    snapshot_ok: bool,
    validate_rc: int,
    validate_findings: list[dict],
) -> list[NamedResult]:
    """Realization-level checks: did the artifact open and stay valid?

    These run even when the task is `unsupported`: refusal is itself a
    correct outcome and the artifact must not exist.
    """

    if not run.artifact_exists:
        results: list[NamedResult] = []
        if task.genuinely_unsupported:
            claim_agrees = run.claim is not None and run.claim.value in (
                "failed",
                "unsupported",
            )
            results.append(
                NamedResult(
                    name="refused",
                    status="pass" if claim_agrees else "fail",
                    detail=(
                        f"agent claim="
                        f"{run.claim.value if run.claim else 'none'!r}; "
                        "artifact present? False"
                    ),
                )
            )
        results.append(
            NamedResult(
                name="no_artifact",
                status="pass" if task.genuinely_unsupported else "fail",
                detail="the artifact path was not created",
            )
        )
        return results

    return [
        NamedResult(
            name="artifact-readable",
            status="pass" if snapshot_ok else "fail",
            detail="jubarte read --json parsed the artifact"
            if snapshot_ok
            else "jubarte read --json could not parse the artifact",
        ),
        NamedResult(
            name="artifact-valid",
            status="pass" if validate_rc == 0 else "fail",
            detail=(
                f"validate returned {validate_rc} with "
                f"{len(validate_findings)} findings"
            ),
        ),
    ]


def eval_task_check(
    check: dict[str, Any],
    snapshot,
    artifact_exists: bool,
    revisions_total: int,
    comments_total: int,
) -> CheckResult:
    kind = check.get("kind")
    try:
        if kind == "text_contains":
            text = check["text"]
            selector = check.get("selector")
            paragraphs = paragraph_rows(snapshot)
            if selector is not None:
                needle = selector["contains"]
                matches = [p for p in paragraphs if needle in p.get("text", "")]
                if len(matches) != 1:
                    return CheckResult(
                        check=check,
                        status="error",
                        detail=f"selector matched {len(matches)} paragraphs",
                    )
                paragraphs = matches
            present = any(text in p.get("text", "") for p in paragraphs)
            return CheckResult(
                check=check,
                status="pass" if present else "fail",
                detail=f"{'found' if present else 'missing'} substring {text!r}",
            )
        if kind == "text_equals":
            target = check["text"]
            needle = check["selector"]["contains"]
            paragraphs = paragraph_rows(snapshot)
            matches = [p for p in paragraphs if needle in p.get("text", "")]
            if len(matches) != 1:
                return CheckResult(
                    check=check,
                    status="error",
                    detail=f"selector matched {len(matches)} paragraphs",
                )
            actual = matches[0].get("text", "")
            return CheckResult(
                check=check,
                status="pass" if actual == target else "fail",
                detail=f"got {actual!r}; expected {target!r}",
            )
        if kind == "text_absent":
            text = check["text"]
            selector = check.get("selector")
            paragraphs = paragraph_rows(snapshot)
            if selector is not None:
                needle = selector["contains"]
                matches = [p for p in paragraphs if needle in p.get("text", "")]
                if len(matches) != 1:
                    return CheckResult(
                        check=check,
                        status="error",
                        detail=f"selector matched {len(matches)} paragraphs",
                    )
                paragraphs = matches
            present = any(text in p.get("text", "") for p in paragraphs)
            return CheckResult(
                check=check,
                status="pass" if not present else "fail",
                detail=f"{'present' if present else 'absent'}: {text!r}",
            )
        if kind == "revision_absent":
            absent = not any(
                entity_ref(row, "revision") == check["ref"]
                for row in snapshot.revisions
            )
            return CheckResult(
                check=check,
                status="pass" if absent else "fail",
                detail=f"selected revision {check['ref']} {'settled' if absent else 'still pending'}",
            )
        if kind == "revision_count":
            lo = int(check.get("min", 0))
            hi = int(check.get("max", 10**9))
            ok = lo <= revisions_total <= hi
            return CheckResult(
                check=check,
                status="pass" if ok else "fail",
                detail=f"revision count {revisions_total} not in [{lo},{hi}]",
            )
        if kind == "revision_present":
            text = check["text"]
            author = check.get("author")
            count = _revisions_with_text(snapshot, text=text, author=author)
            return CheckResult(
                check=check,
                status="pass" if count > 0 else "fail",
                detail=f"{count} matching revisions (author={author!r}, text={text!r})",
            )
        if kind == "comment_present":
            text = check["text"]
            author = check.get("author")
            done = check.get("done")
            matches = []
            for row in snapshot.comments:
                if text not in (row.get("text") or "") or (
                    author is not None and row.get("author") != author
                ):
                    continue
                if done is not None and bool(row.get("done")) != done:
                    continue
                if (
                    check.get("ref") is not None
                    and entity_ref(row, "comment") != check["ref"]
                ):
                    continue
                if check.get("parent_ref") is not None:
                    parent = row.get("parent")
                    if (
                        parent is None
                        or entity_ref({"id": parent}, "comment") != check["parent_ref"]
                    ):
                        continue
                if any(
                    check.get(key) is not None and row.get(key) != check[key]
                    for key in ("paragraph", "anchor_text")
                ):
                    continue
                matches.append(row)
            count = len(matches)
            return CheckResult(
                check=check,
                status="pass" if count > 0 else "fail",
                detail=f"{count} matching comments (author={author!r})",
            )
        if kind == "no_artifact":
            return CheckResult(
                check=check,
                status="pass" if not artifact_exists else "fail",
                detail="artifact present" if artifact_exists else "no artifact",
            )
        return CheckResult(
            check=check, status="error", detail=f"unknown check kind: {kind}"
        )
    except Exception as exc:  # defensive: every check yields a structured result
        return CheckResult(
            check=check, status="error", detail=f"{type(exc).__name__}: {exc}"
        )


def claim_accuracy(
    run: RunRecord,
    task: Task,
    snapshot_ok: bool,
    task_checks: list[CheckResult],
    artifact_exists: bool,
) -> tuple[
    ClaimValue | None, ClaimValue, Literal["accurate", "inaccurate", "missing"], str
]:
    """Compare the agent's printed JUBARTE_RESULT against the artifact."""

    completion_pass = all(c.status == "pass" for c in task_checks)
    successful = artifact_exists and snapshot_ok and completion_pass
    expected: ClaimValue = (
        "success"
        if successful
        else (
            "unsupported"
            if task.genuinely_unsupported and not artifact_exists
            else "failed"
        )
    )
    if run.claim is None:
        return None, expected, "missing", "no JUBARTE_RESULT marker in stdout"
    observed = run.claim.value
    accurate = observed == expected or (
        expected == "unsupported" and observed == "failed"
    )
    return (
        observed,
        expected,
        "accurate" if accurate else "inaccurate",
        "claim compared with observed artifact and checks",
    )


def grade_one(
    run: RunRecord, task: Task, grader_binary: Path, *, repo_root: Path | None = None
) -> GradeRecord:
    errors = []
    snap = empty_snapshot()
    snapshot_ok, validate_rc, validate_findings = False, 2, []
    tracked_audit = False
    if run.artifact_exists:
        try:
            snap = read_snapshot(grader_binary, Path(run.artifact_path))
            snapshot_ok = snap.ok
            if not snap.ok:
                errors.append(snap.error or "artifact snapshot failed")
            # A tracked task is audited against its source under the
            # required author (`jubarte validate --original --author`,
            # the `edits` rule): a desired text written directly, or a
            # change under another author, is a finding, not a passing
            # validity check.
            audit_source = None
            if task.tracked and repo_root is not None:
                candidate = repo_root / task.source.path
                if candidate.is_file():
                    audit_source = candidate
                    tracked_audit = True
            result, validate_findings = validate(
                grader_binary,
                Path(run.artifact_path),
                original=audit_source,
                author=task.required_author if audit_source is not None else None,
            )
            validate_rc = result.return_code
            if validate_rc != 0 and audit_source is not None and task.settlement:
                # The edits audit cannot mark what a settlement task
                # licenses: removing a `settled_revisions` entry reports
                # FOREIGN_AUTHOR "gone", and rejecting a foreign
                # insertion leaves no tracked mark, so the same removal
                # also shows as UNTRACKED_EDIT at the revision's
                # paragraph. Both are the declared effect, not foreign
                # damage. Anything else still fails.
                settled_locations: set[str] = set()
                try:
                    src_snap = _source_snapshot(grader_binary, audit_source)
                    if src_snap.ok:
                        settled_locations = {
                            str(row.get("paragraph") or rev.get("paragraph"))
                            for rev in src_snap.revisions
                            for row in (rev, *rev.get("members", []))
                            if entity_ref(row, "revision") in task.settled_revisions
                            and (row.get("paragraph") or rev.get("paragraph"))
                        }
                except (
                    OSError,
                    TimeoutError,
                    subprocess.TimeoutExpired,
                    ValueError,
                ) as exc:
                    errors.append(f"settlement licence inspection: {exc}")
                failing = [
                    f
                    for f in validate_findings
                    if f.get("set") in ("word", "edits") or f.get("severity") == "error"
                ]
                licensed = (
                    (
                        f.get("code") == "FOREIGN_AUTHOR"
                        and any(
                            f"{ref} in the original is gone" in (f.get("message") or "")
                            for ref in task.settled_revisions
                        )
                    )
                    or (
                        f.get("code") == "UNTRACKED_EDIT"
                        and bool(f.get("location"))
                        and f.get("location") in settled_locations
                    )
                    for f in failing
                )
                if failing and all(licensed):
                    validate_rc = 0
        except (
            OSError,
            TimeoutError,
            subprocess.TimeoutExpired,
            ValueError,
        ) as exc:
            errors.append(f"artifact inspection: {exc}")
    task_checks = [
        eval_task_check(
            check.model_dump(exclude_none=True),
            snap,
            run.artifact_exists,
            len(snap.revisions),
            len(snap.comments),
        )
        for check in task.checks
    ]
    unintended_edits, preservation_defects = [], []
    assessed = False
    if run.artifact_exists and repo_root is not None:
        try:
            source_path = repo_root / task.source.path
            if source_path.is_file():
                src = _source_snapshot(grader_binary, source_path)
                if src.ok and snapshot_ok and isinstance(snap, Snapshot):
                    assessed = True
                    unintended_edits = compute_unintended_edits(
                        src, snap, authorized_text=task.expected_paragraphs
                    )
                    preservation_defects = compute_preservation_defects(
                        src,
                        snap,
                        settlement_targets=task.settled_revisions,
                        comment_updates=task.comment_updates,
                    )
                else:
                    errors.append("source/artifact preservation inspection failed")
            else:
                errors.append("source fixture unavailable")
        except (
            OSError,
            TimeoutError,
            subprocess.TimeoutExpired,
            ValueError,
        ) as exc:
            errors.append(f"source inspection: {exc}")
    tool_results = tool_correctness(
        run, task, snapshot_ok, validate_rc, validate_findings
    )
    checks_pass = all(c.status == "pass" for c in task_checks)
    # Required effects and preservation are independent of package validity.
    if run.artifact_exists:
        realized = (
            checks_pass
            and assessed
            and not unintended_edits
            and not preservation_defects
        )
        if task.unchanged:
            realized &= run.artifact_sha256 == run.input_sha256
        tool_results.append(
            NamedResult(
                name="declared-effects-and-preservation",
                status="pass" if realized else "fail",
                detail="exact task effects, exposed preservation and unchanged byte identity",
            )
        )
    tool_ok = all(r.status == "pass" for r in tool_results) and not run.right_censored
    completion = checks_pass and (
        tool_ok if run.artifact_exists else task.genuinely_unsupported
    )
    claim_value, claim_expected, accuracy, claim_detail = claim_accuracy(
        run, task, snapshot_ok and tool_ok, task_checks, run.artifact_exists
    )
    refusal_class = classify_refusal(
        run,
        task,
        task_checks_pass=checks_pass,
        preservation_defects=preservation_defects,
        unintended_edits=unintended_edits,
        validation_ok=tool_ok,
    )
    unassessed = [
        "section properties",
        "bookmarks",
        "media bytes",
        "relationships",
        "numbering definitions",
        "formatting on rewritten spans",
    ]
    if not assessed:
        unassessed += ["unintended edits", "exposed structure/comments/revisions"]
    if task.tracked and run.artifact_exists and not tracked_audit:
        unassessed.append("tracked-edit audit")
    if any(e.adjudication_required for e in unintended_edits):
        unassessed.append("ambiguous paragraph alignment requires adjudication")
    return GradeRecord(
        run_id=run.run_id,
        task_id=run.task_id,
        task_family=run.task_family,
        arm=run.arm,
        repetition=run.repetition,
        right_censored=run.right_censored,
        artifact_exists=run.artifact_exists,
        tool_correctness=tool_results,
        tool_correctness_overall=tool_ok,
        task_checks=task_checks,
        task_completion_overall=completion,
        rubric=[
            RubricAssessment(
                id=item.id, description=item.description, status="unassessed"
            )
            for item in task.rubric
        ],
        claim_value=claim_value,
        claim_expected=claim_expected,
        claim_accuracy=accuracy,
        claim_detail=claim_detail,
        unintended_edits=unintended_edits,
        unintended_edit_count=len(unintended_edits) if assessed else None,
        preservation_defects=preservation_defects,
        preservation_defect_count=len(preservation_defects) if assessed else None,
        preservation_status="assessed" if assessed else "not_assessed",
        unassessed=unassessed,
        inspection_errors=errors,
        refusal_class=refusal_class,
        graded_at=run.ended_at or run.started_at,
        grader_binary_path=str(grader_binary),
        grader_binary_sha256=hashlib.sha256(grader_binary.read_bytes()).hexdigest(),
    )
