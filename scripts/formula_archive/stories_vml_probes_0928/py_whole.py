# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import pathlib
p = pathlib.Path("jubarte-python/tests/test_agent_api.py"); s = p.read_text()
anchor = "def test_capabilities_manifest_reports_python_runtime() -> None:"
assert s.count(anchor) == 1
s = s.replace(anchor, '''def test_whole_replace_shows_one_deletion_then_one_insertion() -> None:
    doc = letter()
    base = EditPlan(author="Claude", date="2026-09-25T12:00:00Z").for_document(doc)
    assert base.replace(1, find="a", replacement="b").operations[0].get("whole") is None
    plan = base.replace(1, find="attorneys", replacement="outside attorneys", whole=True)
    assert plan.operations[0]["whole"] is True
    result = doc.edit(plan)
    assert result.report.ok, result.report.operations
    assert all(op.message is None for op in result.report.operations)
    assert (result.report.revisions.deleted, result.report.revisions.inserted) == (1, 1)
    assert [p.text for p in result.redline.accept().inspect().paragraphs] == [
        p.text for p in result.clean.inspect().paragraphs
    ]


''' + anchor)
p.write_text(s)