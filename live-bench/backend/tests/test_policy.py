# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
from pathlib import Path

import pytest

from livebench.benchmark import Benchmark
from livebench.models import Document, ToolFailure, batch_id, queue_target
from livebench.service import health_status


class FakeTools:
    def __init__(self, failures=None, score_failure=False):
        self.failures = failures or {}
        self.score_failure = score_failure
        self.calls = []

    def perform(self, tool, operation, inputs, output):
        self.calls.append((tool, operation, inputs, output))
        failure = self.failures.get((tool, operation, output.name), self.failures.get((tool, operation)))
        if failure:
            raise ToolFailure("document rejected", status=failure)
        return output

    def score(self, oracle, candidate, work):
        if self.score_failure:
            raise ToolFailure("scorer unavailable", status="error")
        return {
            "overall": 72.5,
            "page_count_mismatch": True,
            "page_count_oracle": 2,
            "page_count_candidate": 3,
        }

    def functional(self, candidate, previous, current, work):
        return {"accept_ok": True, "reject_ok": False, "blind": False}

    def artifacts(self, work, prefix):
        return []


def run(failures=None, previous=None, current=None, score_failure=False):
    tools = FakeTools(failures, score_failure)
    counter = iter(range(1000))
    phases = []
    result = Benchmark(tools, lambda: next(counter), lambda: "2026-10-08T12:00:00Z").run(
        "run",
        100,
        100,
        previous or Document("before", "https://example.com/a.docx", Path("a.docx"), "a" * 64),
        current
        or Document("after", "https://example.com/b.docx", Path("b.docx"), "b" * 64, review_id="review"),
        Path("work"),
        phases.append,
    )
    return result, tools, phases


def score(result, tool, task):
    return next(row for row in result["scores"] if row["tool"] == tool and row["benchmark"] == task)


def test_all_six_measurements_share_word_references_and_keep_functional_metrics():
    result, tools, phases = run()
    assert result["id"] == "review"
    assert len(result["scores"]) == 6
    assert {r["tool"] for r in result["scores"] if r["benchmark"] == "redline"} == {
        "jubarte",
        "docxodus",
        "superdoc-redlines",
    }
    assert all(r["reference_tool"] == "word" for r in result["scores"])
    assert all(r["overall"] == 72.5 for r in result["scores"])
    assert score(result, "jubarte", "redline")["functional"]["reject_ok"] is False
    assert "jubarte:native_redline_render" in phases
    assert all(call[2][0] == Path("b.docx") for call in tools.calls if call[1] == "convert")


@pytest.mark.parametrize("failure", ["broken", "error"])
def test_conversion_failure_only_changes_conversion_reference(failure):
    result, _, _ = run({("word", "convert"): failure})
    assert score(result, "jubarte", "convert")["reference_tool"] == "soffice"
    assert score(result, "soffice", "convert")["status"] == "reference"
    assert score(result, "jubarte", "redline")["reference_tool"] == "word"
    assert any(
        s["tool"] == "word" and s["operation"] == "convert" and s["status"] == failure
        for s in result["stages"]
    )


@pytest.mark.parametrize("operation", ["compare", "redline_render"])
def test_redline_failure_only_changes_redline_reference_and_common_renderer(operation):
    failure = (
        ("word", operation, "word-redline.pdf") if operation == "redline_render" else ("word", operation)
    )
    result, tools, _ = run({failure: "broken"})
    assert score(result, "jubarte", "convert")["reference_tool"] == "word"
    assert score(result, "jubarte", "redline")["reference_tool"] == "docxodus"
    assert score(result, "docxodus", "redline")["status"] == "reference"
    assert all(
        row["reference_renderer"] == "soffice" for row in result["scores"] if row["benchmark"] == "redline"
    )
    assert any(c[0] == "soffice" and c[1] == "redline_render" for c in tools.calls)


@pytest.mark.parametrize(
    "tool,operation,task",
    [
        ("jubarte", "compare", "redline"),
        ("docxodus", "compare", "redline"),
        ("superdoc-redlines", "compare", "redline"),
        ("jubarte", "convert", "convert"),
        ("docxide", "convert", "convert"),
        ("soffice", "convert", "convert"),
    ],
)
def test_broken_candidate_counts_as_zero_with_usable_reference(tool, operation, task):
    result, _, _ = run({(tool, operation): "broken"})
    assert score(result, tool, task)["status"] == "broken"
    assert score(result, tool, task)["overall"] == 0


def test_candidate_word_render_failure_does_not_reward_word_invalid_output():
    result, _, _ = run({("word", "redline_render", "jubarte-redline-word.pdf"): "broken"})
    assert score(result, "jubarte", "redline")["overall"] == 0
    assert score(result, "jubarte", "redline")["reference_tool"] == "word"
    assert score(result, "docxodus", "redline")["overall"] == 72.5


def test_candidate_word_render_infrastructure_failure_is_not_a_zero():
    result, _, _ = run({("word", "redline_render", "jubarte-redline-word.pdf"): "error"})
    row = score(result, "jubarte", "redline")
    assert row["status"] == "error" and row["overall"] is None
    failure = next(s for s in result["stages"] if s.get("target_tool") == "jubarte")
    assert failure["tool"] == "word" and failure["status"] == "error"


def test_no_usable_reference_is_unavailable():
    result, _, _ = run(
        {
            ("word", "convert"): "broken",
            ("soffice", "convert"): "broken",
            ("word", "compare"): "broken",
            ("docxodus", "compare"): "broken",
        }
    )
    assert all(row["overall"] is None and row["status"] == "unavailable" for row in result["scores"])


def test_scoring_infrastructure_errors_are_not_fabricated_zero_scores():
    result, _, _ = run(score_failure=True)
    assert all(row["overall"] is None and row["status"] == "error" for row in result["scores"])
    assert any(stage["tool"] == "scorer" for stage in result["stages"])


def test_tool_unavailable_is_distinct_from_broken_fixture():
    result, _, _ = run({("docxide", "convert"): "error"})
    assert score(result, "docxide", "convert")["status"] == "error"
    assert score(result, "docxide", "convert")["overall"] is None


def test_failed_download_stays_in_chain_without_executing_tools():
    doc = Document("after", "https://example.com/x", None, None, error="404", review_id="review")
    result, tools, _ = run(current=doc)
    assert not tools.calls
    assert result["source"]["id"] == "after"
    assert all(row["status"] == "unavailable" for row in result["scores"])
    assert result["stages"][0]["tool"] == "download"


def test_unsafe_package_is_recorded_before_any_vendor_sees_it():
    doc = Document(
        "after",
        "https://example.com/x",
        Path("x.docx"),
        "b" * 64,
        error="DTD forbidden",
        security={"status": "rejected"},
    )
    result, tools, _ = run(current=doc)
    assert not tools.calls
    assert result["stages"][0]["operation"] == "security_preflight"


@pytest.mark.parametrize("path,security", [(None, {}), (Path("bomb.docx"), {"status": "rejected"})])
def test_broken_predecessor_does_not_change_chain_or_block_current_conversion(path, security):
    doc = Document("before", "https://example.com/x", path, None, security=security)
    result, tools, _ = run(previous=doc)
    assert result["previous"]["id"] == "before"
    assert not any(c[1] == "compare" for c in tools.calls)
    assert score(result, "jubarte", "convert")["status"] == "ok"
    assert score(result, "jubarte", "redline")["status"] == "unavailable"


def test_internal_group_boundary_and_health_freshness():
    assert batch_id("run", 100, 100) != batch_id("run", 101, 100)
    assert queue_target(100) == 200
    assert health_status({"healthy": True, "timestamp": 100}, 150)
    assert not health_status({"healthy": True, "timestamp": 100}, 161)
    assert not health_status({"healthy": False, "timestamp": 100}, 100)
    assert not health_status({"healthy": True, "timestamp": 120}, 100)
