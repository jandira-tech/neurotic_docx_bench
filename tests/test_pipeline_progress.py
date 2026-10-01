"""Progress reporting, deterministic results and the resume checkpoint for scoring."""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from neurotic_docx_bench import pipeline

STAMP = "2026-10-01T02:03:04Z"


class _FixedClock:
    """Stands in for ``pipeline.datetime`` so the UTC stamp is deterministic."""

    @staticmethod
    def now(tz=None):
        return datetime(2026, 10, 1, 2, 3, 4, tzinfo=tz or UTC)


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(pipeline, "datetime", _FixedClock)


@pytest.fixture
def thread_pool(monkeypatch):
    """The process pool replaced by threads: no child processes, same futures."""
    made: list[dict] = []

    def factory(max_workers, initializer=None, initargs=()):
        made.append({"max_workers": max_workers, "initargs": initargs})
        return ThreadPoolExecutor(max_workers=max_workers)

    monkeypatch.setattr(pipeline, "ProcessPoolExecutor", factory)
    return made


@pytest.mark.parametrize(
    ("done", "total", "score", "now", "expected"),
    [
        (1, 4, 87.125, 110.0, "[1/4]  25.0%  87.12  résumé.docx  (elapsed 10s, eta 30s)"),
        (2, 3, 0.0, 110.0, "[2/3]  66.7%   0.00  résumé.docx  (elapsed 10s, eta 5s)"),
        (3, 3, 100.0, 112.0, "[3/3] 100.0% 100.00  résumé.docx  (elapsed 12s, eta 0s)"),
        (1, 1, 100.0, 100.0, "[1/1] 100.0% 100.00  résumé.docx  (elapsed 0s, eta 0s)"),
    ],
)
def test_progress_reports_stamp_score_percent_elapsed_and_eta(monkeypatch, capsys, done, total, score, now, expected):
    monkeypatch.setattr(pipeline.time, "monotonic", lambda: now)
    pipeline._progress(done, total, "résumé.docx", {"overall_score": score}, 100.0)
    captured = capsys.readouterr()
    assert captured.out == f"{STAMP} {expected}\n"
    assert captured.err == ""


def test_progress_flushes_each_line(monkeypatch):
    printer = Mock()
    monkeypatch.setattr(pipeline, "print", printer, raising=False)
    monkeypatch.setattr(pipeline.time, "monotonic", lambda: 0.0)
    pipeline._progress(1, 1, "doc", {"overall_score": 50.0}, 0.0)
    assert printer.call_count == 1
    assert printer.call_args.kwargs == {"flush": True}


@pytest.mark.parametrize(("jobs", "count"), [(0, 2), (1, 2), (8, 1), (1, 0), (8, 0)])
def test_serial_and_empty_runs_report_only_completed_tasks(monkeypatch, jobs, count):
    tasks = [(f"doc-{i}", {"overall_score": float(i)}) for i in range(count)]
    scorer = Mock(side_effect=lambda task: task)
    pool = Mock(side_effect=AssertionError("no process pool needed"))
    progress = Mock()
    monkeypatch.setattr(pipeline, "_score_one", scorer)
    monkeypatch.setattr(pipeline, "ProcessPoolExecutor", pool)
    monkeypatch.setattr(pipeline, "_progress", progress)
    monkeypatch.setattr(pipeline.time, "monotonic", lambda: 100.0)
    result = pipeline._run_tasks(tasks, jobs)
    assert list(result.items()) == tasks
    assert [call.args for call in scorer.call_args_list] == [(task,) for task in tasks]
    assert [call.args for call in progress.call_args_list] == [
        (i, count, key, value, 100.0) for i, (key, value) in enumerate(tasks, 1)
    ]
    pool.assert_not_called()


def test_parallel_progress_counts_completions_and_results_keep_task_order(monkeypatch, thread_pool):
    tasks = [("slow",), ("fast",), ("middle",)]
    gates = {name: threading.Event() for name, in tasks}
    scores = {"slow": 10.0, "fast": 90.0, "middle": 50.0}

    def scorer(task):
        gates[task[0]].wait(timeout=5)
        return task[0], {"overall_score": scores[task[0]]}

    reported: list[tuple] = []

    def progress(done, total, key, result, started):
        reported.append((done, total, key))
        # release the next task only once this one is reported: completion order is fast, middle, slow
        nxt = {"fast": "middle", "middle": "slow"}.get(key)
        if nxt:
            gates[nxt].set()

    monkeypatch.setattr(pipeline, "_score_one", scorer)
    monkeypatch.setattr(pipeline, "_progress", progress)
    gates["fast"].set()
    result = pipeline._run_tasks(tasks, 3)
    assert thread_pool == [{"max_workers": 3, "initargs": (3,)}]
    assert reported == [(1, 3, "fast"), (2, 3, "middle"), (3, 3, "slow")]
    assert list(result) == ["slow", "fast", "middle"]  # task order, whatever finished first
    assert result["fast"]["overall_score"] == 90.0


@pytest.mark.parametrize("jobs", [1, 2])
def test_scoring_failure_propagates(monkeypatch, thread_pool, jobs):
    error = ValueError("cannot score broken PDF")

    def scorer(task):
        if task[0] == "broken":
            raise error
        return task[0], {"overall_score": 100.0}

    monkeypatch.setattr(pipeline, "_score_one", scorer)
    monkeypatch.setattr(pipeline, "_progress", Mock())
    with pytest.raises(ValueError, match="cannot score broken PDF") as raised:
        pipeline._run_tasks([("good",), ("broken",)], jobs)
    assert raised.value is error


def _pair(tmp_path: Path, name: str) -> tuple:
    oracle, cand = tmp_path / f"{name}.o.pdf", tmp_path / f"{name}.c.pdf"
    oracle.write_bytes(b"%PDF-oracle-" + name.encode())
    cand.write_bytes(b"%PDF-cand-" + name.encode())
    return (name, oracle, cand, tmp_path / "work", 144)


def test_checkpoint_records_each_document_and_a_rerun_scores_only_the_rest(monkeypatch, tmp_path, capsys):
    checkpoint = tmp_path / "scores.checkpoint.jsonl"
    first = [_pair(tmp_path, "a"), _pair(tmp_path, "b")]
    scored: list[str] = []

    def scorer(task):
        scored.append(task[0])
        return task[0], {"overall_score": 70.0, "page_count": 1}

    monkeypatch.setattr(pipeline, "_score_one", scorer)
    pipeline._run_tasks(first, 1, checkpoint)
    lines = [json.loads(line) for line in checkpoint.read_text().splitlines()]
    assert [row["key"] for row in lines] == ["a", "b"]
    assert all(row["scored_at"] == STAMP and row["result"]["overall_score"] == 70.0 for row in lines)

    scored.clear()
    capsys.readouterr()
    result = pipeline._run_tasks([*first, _pair(tmp_path, "c")], 1, checkpoint)
    assert scored == ["c"]  # a and b came from the checkpoint
    assert list(result) == ["a", "b", "c"]
    assert f"{STAMP} scoring started, 3 documents (2 from checkpoint, 1 to score)" in capsys.readouterr().out
    assert [json.loads(line)["key"] for line in checkpoint.read_text().splitlines()] == ["a", "b", "c"]


def test_checkpoint_row_is_stale_when_the_pdf_changes(monkeypatch, tmp_path):
    checkpoint = tmp_path / "scores.checkpoint.jsonl"
    task = _pair(tmp_path, "a")
    monkeypatch.setattr(pipeline, "_score_one", lambda t: (t[0], {"overall_score": 1.0}))
    pipeline._run_tasks([task], 1, checkpoint)
    task[2].write_bytes(b"%PDF-cand-a-but-longer-now")  # different size, different signature
    rescored: list[str] = []
    monkeypatch.setattr(pipeline, "_score_one", lambda t: (rescored.append(t[0]), (t[0], {"overall_score": 2.0}))[1])
    result = pipeline._run_tasks([task], 1, checkpoint)
    assert rescored == ["a"] and result["a"]["overall_score"] == 2.0


def test_checkpoint_ignores_a_line_cut_short_by_a_kill(monkeypatch, tmp_path):
    checkpoint = tmp_path / "scores.checkpoint.jsonl"
    task = _pair(tmp_path, "a")
    monkeypatch.setattr(pipeline, "_score_one", lambda t: (t[0], {"overall_score": 5.0}))
    pipeline._run_tasks([task], 1, checkpoint)
    checkpoint.write_text(checkpoint.read_text() + '{"key": "b", "sig": "x", "res')
    result = pipeline._run_tasks([task], 1, checkpoint)
    assert list(result) == ["a"]
