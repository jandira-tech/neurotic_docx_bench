# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""Regression gates from the V2-15 adversarial review (stable row numbers)."""

import json
import tomllib
from pathlib import Path

import pytest
from test_outcomes import _make_run, _task

from harness import grading
from harness.exec import parse_claim
from harness.models import Task
from harness.snapshot import Snapshot
from harness.tasks import load_task

PKG = Path(__file__).resolve().parents[1]


@pytest.mark.integration
def test_row29_default_pytest_reports_line_and_branch_coverage():
    config = tomllib.loads((PKG / "pyproject.toml").read_text())
    assert any("pytest-cov" in dep for dep in config["dependency-groups"]["dev"])
    options = config["tool"]["pytest"]["ini_options"]["addopts"]
    assert "--cov=harness" in options and "--cov-branch" in options


def snap(texts=(), **kw):
    return Snapshot(
        ok=True,
        paragraphs=[{"id": f"p{i}", "text": t} for i, t in enumerate(texts)],
        **kw,
    )


def test_row05_nonbody_stories_are_compared():
    a, b = snap(), snap()
    a.document = {
        "stories": [{"id": "header1", "paragraphs": [{"id": "p0", "text": "secret"}]}]
    }
    b.document = {
        "stories": [{"id": "header1", "paragraphs": [{"id": "p0", "text": "tampered"}]}]
    }
    assert len(grading.compute_unintended_edits(a, b)) == 1


@pytest.mark.parametrize(
    "kind,field,value",
    [
        ("comment", "text", "corrupted"),
        ("comment", "author", "impostor"),
        ("comment", "parent", 9),
        ("comment", "done", True),
        ("comment", "paragraph", "p9"),
        ("comment", "anchor_text", "elsewhere"),
        ("revision", "kind", "deletion"),
        ("revision", "author", "impostor"),
        ("revision", "text", "corrupted"),
    ],
)
def test_row06_preserved_entities_compare_material_fields(kind, field, value):
    a, b = snap(), snap()
    row = (
        {
            "id": 4,
            "ref": "c4",
            "text": "old",
            "author": "A",
            "parent": None,
            "done": False,
            "paragraph": "p0",
            "anchor_text": "x",
        }
        if kind == "comment"
        else {"id": "r2", "kind": "insertion", "author": "A", "text": "old"}
    )
    setattr(a, "comments" if kind == "comment" else "revisions", [row])
    setattr(
        b,
        "comments" if kind == "comment" else "revisions",
        [dict(row, **{field: value})],
    )
    assert len(grading.compute_preservation_defects(a, b)) == 1


def test_row06_structure_exposed_by_snapshot_is_compared():
    a, b = snap(["same"]), snap(["same"])
    a.paragraphs[0]["style"] = "Heading1"
    b.paragraphs[0]["style"] = "Normal"
    assert len(grading.compute_preservation_defects(a, b)) == 1


def test_row07_targeted_paragraph_is_not_blanket_exempt():
    assert (
        len(
            grading.compute_unintended_edits(
                snap(["authorized original"]), snap(["unauthorized clause"]), {"p0"}
            )
        )
        == 1
    )


def test_row08_added_paragraph_is_counted():
    assert (
        len(
            grading.compute_unintended_edits(
                snap(["original"]), snap(["original", "unauthorized clause"])
            )
        )
        == 1
    )


def test_row09_deleting_first_paragraph_counts_once():
    edits = grading.compute_unintended_edits(snap(["a", "b", "c"]), snap(["b", "c"]))
    assert len(edits) == 1 and edits[0].text_before == "a" and edits[0].text_after == ""


def test_row09_ambiguous_alignment_requires_adjudication():
    edits = grading.compute_unintended_edits(snap(["same", "same"]), snap(["same"]))
    assert edits and getattr(edits[0], "adjudication_required", False)


@pytest.mark.integration
def test_row10_task_model_preserves_selector_and_rejects_unknown_fields(
    tasks_dir, repo_root
):
    task, _ = load_task(tasks_dir / "02-exact-replace-multibody.json", repo_root)
    check = task.checks[0].model_dump(exclude_none=True)
    result = grading.eval_task_check(
        check, snap(["START BODY 1 blue fox", "red fox elsewhere"]), True, 0, 0
    )
    assert result.status != "pass"
    raw = task.model_dump()
    raw["checks"][0]["typo_selector"] = {"contains": "x"}
    with pytest.raises(ValueError):
        Task.model_validate(raw)


@pytest.mark.integration
def test_row11_selected_revision_must_be_absent(tasks_dir, repo_root):
    task, _ = load_task(tasks_dir / "05-received-redline-with-edit.json", repo_root)
    checks = [
        c.model_dump(exclude_none=True)
        for c in task.checks
        if c.kind == "revision_absent"
    ]
    assert checks, "a final-view text absence does not prove revision settlement"
    for check in checks:
        assert (
            grading.eval_task_check(
                check,
                snap(revisions=[{"id": "r0", "text": "zero backend required"}]),
                True,
                1,
                0,
            ).status
            == "fail"
        )


@pytest.mark.integration
@pytest.mark.parametrize(
    "task_id,text",
    [
        ("05-received-redline-with-edit", "Looks good."),
        ("07-comments-edit-and-reply", "Acknowledged, will revise."),
        ("08-comments-add-multiple", "first new note"),
    ],
)
def test_row12_comment_checks_require_parent_and_anchor(
    tasks_dir, repo_root, task_id, text
):
    task, _ = load_task(tasks_dir / f"{task_id}.json", repo_root)
    check = next(
        c.model_dump(exclude_none=True)
        for c in task.checks
        if getattr(c, "text", None) == text
    )
    wrong = snap(
        comments=[
            {
                "id": 99,
                "ref": "c99",
                "author": "PilotBot",
                "text": text,
                "paragraph": "p0",
                "anchor_text": "wrong",
                "parent": None,
            }
        ]
    )
    assert grading.eval_task_check(check, wrong, True, 0, 1).status == "fail"


def test_row13_supported_refusal_is_not_tool_correct():
    results = grading.tool_correctness(
        _make_run(artifact_exists=False, claim_value="failed"), _task(), False, 2, []
    )
    assert any(r.status != "pass" for r in results)


@pytest.mark.parametrize(
    "unsupported,claim", [(False, "failed"), (True, "unsupported"), (True, "failed")]
)
def test_row14_claim_accuracy_uses_observed_failure(unsupported, claim):
    task = _task(
        genuinely_unsupported=unsupported,
        family="unsupported" if unsupported else "exact_replace",
    )
    result = grading.claim_accuracy(
        _make_run(artifact_exists=False, claim_value=claim), task, False, [], False
    )
    assert result[2] == "accurate"


def test_row15_acceptance_includes_unintended_edits_and_validation():
    # Public classifier must receive the two observations, rather than silently losing them.
    import inspect

    params = inspect.signature(grading.classify_refusal).parameters
    assert "unintended_edits" in params and "validation_ok" in params
    run = _make_run(artifact_exists=True)
    assert (
        grading.classify_refusal(
            run,
            _task(),
            task_checks_pass=True,
            preservation_defects=[],
            unintended_edits=[object()],
            validation_ok=True,
        )
        == "false_negative_acceptance"
    )
    assert (
        grading.classify_refusal(
            run,
            _task(),
            task_checks_pass=True,
            preservation_defects=[],
            unintended_edits=[],
            validation_ok=False,
        )
        == "false_negative_acceptance"
    )


@pytest.mark.integration
def test_row23_tasks_use_generated_template_then_apply(tasks_dir, repo_root):
    for name in ("09-template-flow-rewrite", "10-template-flow-multi-rewrite"):
        task, _ = load_task(tasks_dir / f"{name}.json", repo_root)
        commands = [step.argv for step in task.stub.steps]
        assert any(cmd[1:3] == ["edit", "template"] for cmd in commands)
        assert any(cmd[1:3] == ["edit", "apply"] for cmd in commands)
        assert "edit template" in task.prompt and "edit apply" in task.prompt


@pytest.mark.integration
def test_row24_twelve_tasks_include_unchanged_ambiguity_and_cell(tasks_dir, repo_root):
    from harness.tasks import load_tasks

    tasks = load_tasks(tasks_dir, repo_root)
    assert len(tasks) == 12
    tags = {
        tag for task in tasks.values() for tag in getattr(task, "coverage_tags", [])
    }
    assert {"meaningful_unchanged", "repeated_anchor", "table_cell"} <= tags


@pytest.mark.integration
def test_row25_drift_test_never_writes_tracked_fixture(
    tasks_dir, repo_root, tmp_path, monkeypatch
):
    from test_tasks import test_fixture_sha256_drift_is_refused

    original = Path.write_bytes

    def guarded(path, data):
        assert path.is_relative_to(tmp_path), (
            f"attempt to overwrite tracked fixture: {path}"
        )
        return original(path, data)

    monkeypatch.setattr(Path, "write_bytes", guarded)
    test_fixture_sha256_drift_is_refused(tasks_dir, repo_root, tmp_path, monkeypatch)


@pytest.mark.parametrize(
    "event",
    [
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": "JUBARTE_RESULT: success"},
        },
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "JUBARTE_RESULT: failed"}],
        },
    ],
)
def test_row26_json_agent_claims(event):
    claim, _ = parse_claim(json.dumps(event))
    assert claim is not None
    assert claim.value in ("success", "failed")


def test_row27_numeric_comment_ids_use_refs():
    assert (
        grading.compute_preservation_defects(
            snap(comments=[{"id": 4, "ref": "c4", "text": "old"}]),
            snap(),
            settlement_targets={"c4"},
        )
        == []
    )


@pytest.mark.integration
def test_row30_task03_has_exact_consistent_authorized_result(tasks_dir, repo_root):
    task, _ = load_task(tasks_dir / "03-multi-edit-one-paragraph.json", repo_root)
    exact = [c for c in task.checks if c.kind == "text_equals"]
    assert exact, "the exact authorized paragraph must be checked"
    assert "an energetic dog" in exact[0].text
    assert "lazy" not in task.stub.steps[0].argv or "a lazy" in task.stub.steps[0].argv


@pytest.mark.integration
def test_edit_tasks_use_single_body_fixture(tasks_dir, repo_root):
    """The two paragraph tasks require a valid single-body source, not a
    legacy multi-body repair probe whose normalization changes other stories."""
    from xml.etree import ElementTree as ET
    from zipfile import ZipFile

    for prefix in ("02", "03"):
        task, _ = load_task(next(tasks_dir.glob(prefix + "-*.json")), repo_root)
        with ZipFile(repo_root / task.source.path) as package:
            document = ET.fromstring(package.read("word/document.xml"))
        bodies = document.findall(
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}body"
        )
        assert len(bodies) == 1, (
            "normal edit task must not require implicit multi-body repair"
        )


def test_row06_structure_alignment_survives_paragraph_deletion():
    source, artifact = snap(["a", "b", "c"]), snap(["b", "c"])
    source.paragraphs[2]["style"] = "Heading1"
    artifact.paragraphs[1]["style"] = "Normal"
    defects = grading.compute_preservation_defects(source, artifact)
    assert any(d.kind == "structure" for d in defects)


@pytest.mark.parametrize("story", ["header1", "footer1", "footnotes", "endnotes"])
def test_row05_nonbody_text_requirements_and_damage_are_visible(story):
    source, artifact = snap(), snap()
    source.document = {
        "stories": [
            {"id": story, "paragraphs": [{"id": "p0", "text": "required text"}]}
        ]
    }
    artifact.document = {
        "stories": [{"id": story, "paragraphs": [{"id": "p0", "text": "wrong text"}]}]
    }
    check = {"kind": "text_contains", "text": "required text"}
    assert grading.eval_task_check(check, source, True, 0, 0).status == "pass"
    assert grading.eval_task_check(check, artifact, True, 0, 0).status == "fail"
    assert grading.compute_unintended_edits(source, artifact)[
        0
    ].paragraph_id.startswith(story + ":")


@pytest.mark.parametrize(
    "check,expected",
    [
        (
            {"kind": "text_contains", "text": "x", "selector": {"contains": "missing"}},
            "error",
        ),
        (
            {"kind": "text_absent", "text": "x", "selector": {"contains": "missing"}},
            "error",
        ),
        (
            {"kind": "text_absent", "text": "alpha", "selector": {"contains": "alpha"}},
            "fail",
        ),
        (
            {"kind": "text_equals", "text": "x", "selector": {"contains": "missing"}},
            "error",
        ),
        ({"kind": "revision_count", "min": 1, "max": 2}, "fail"),
        ({"kind": "revision_present", "text": "change", "author": "wrong"}, "fail"),
        ({"kind": "comment_present", "text": "hello", "author": "wrong"}, "fail"),
        ({"kind": "comment_present", "text": "hello", "done": True}, "fail"),
        ({"kind": "comment_present", "text": "hello", "ref": "c99"}, "fail"),
        ({"kind": "comment_present", "text": "hello", "parent_ref": "c99"}, "fail"),
        (
            {
                "kind": "comment_present",
                "text": "hello",
                "paragraph": "p0",
                "anchor_text": "alpha",
                "parent_ref": "c4",
            },
            "pass",
        ),
        ({"kind": "unknown"}, "error"),
        ({"kind": "text_contains"}, "error"),
    ],
)
def test_independent_check_failures_are_structured(check, expected):
    snapshot = snap(
        ["alpha"],
        revisions=[{"id": "r0", "text": "change", "author": "A"}],
        comments=[
            {
                "id": 5,
                "ref": "c5",
                "text": "hello",
                "author": "A",
                "done": False,
                "paragraph": "p0",
                "anchor_text": "alpha",
                "parent": 4,
            }
        ],
    )
    assert grading.eval_task_check(check, snapshot, True, 0, 1).status == expected


def test_row07_exact_authorization_rejects_extra_content_in_same_paragraph():
    source = snap(["original clause"])
    authorized = {"p0": "authorized clause"}
    assert (
        grading.compute_unintended_edits(
            source, snap(["authorized clause"]), authorized_text=authorized
        )
        == []
    )
    edits = grading.compute_unintended_edits(
        source,
        snap(["authorized clause; unauthorized waiver"]),
        authorized_text=authorized,
    )
    assert len(edits) == 1 and "waiver" in edits[0].text_after


@pytest.mark.parametrize(
    "text",
    [
        "ordinary output",
        '{"type":"tool_result","text":"JUBARTE_RESULT: success"}',
        "[]",
        '{"type":"message","role":"user","content":"JUBARTE_RESULT: success"}',
    ],
)
def test_row26_tool_or_user_events_are_not_final_claims(text):
    assert parse_claim(text)[0] is None
