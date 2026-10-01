"""Progress reporting and deterministic results for serial and pooled scoring."""

from __future__ import annotations

from concurrent.futures import Future
from unittest.mock import Mock

import pytest

from neurotic_docx_bench import kernels, pipeline


@pytest.mark.parametrize(
    ("done", "total", "score", "now", "expected"),
    [
        (1, 4, 87.125, 110.0, "[1/4]  25.0%  87.12  résumé.docx  (elapsed 10s, eta 30s)"),
        (2, 3, 0.0, 110.0, "[2/3]  66.7%   0.00  résumé.docx  (elapsed 10s, eta 5s)"),
        (3, 3, 100.0, 112.0, "[3/3] 100.0% 100.00  résumé.docx  (elapsed 12s, eta 0s)"),
        (1, 1, 100.0, 100.0, "[1/1] 100.0% 100.00  résumé.docx  (elapsed 0s, eta 0s)"),
    ],
)
def test_progress_reports_score_percent_elapsed_and_eta(monkeypatch, capsys, done, total, score, now, expected):
    monkeypatch.setattr(pipeline.time, "monotonic", lambda: now)
    pipeline._progress(done, total, "résumé.docx", {"overall_score": score}, 100.0)
    captured = capsys.readouterr()
    assert captured.out == expected + "\n"
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


@pytest.fixture
def controlled_pool(monkeypatch):
    """Real Futures with a controlled completion order; no child processes."""
    pool = Mock()
    executor = Mock()
    executor.return_value.__enter__ = Mock(return_value=pool)
    executor.return_value.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(pipeline, "ProcessPoolExecutor", executor)
    return executor, pool


def test_parallel_progress_follows_completion_but_results_keep_task_order(monkeypatch, controlled_pool):
    executor, pool = controlled_pool
    tasks = [("slow",), ("fast",), ("middle",)]
    results = [(task[0], {"overall_score": score}) for task, score in zip(tasks, [10.0, 90.0, 50.0])]
    futures = [Future() for _ in tasks]
    pool.submit.side_effect = futures

    def complete(submitted):
        assert list(submitted) == futures
        assert pool.submit.call_count == len(tasks)
        for index in [1, 2, 0]:
            futures[index].set_result(results[index])
            yield futures[index]

    monkeypatch.setattr(pipeline, "as_completed", complete)
    monkeypatch.setattr(pipeline.time, "monotonic", lambda: 100.0)
    progress = Mock()
    monkeypatch.setattr(pipeline, "_progress", progress)
    result = pipeline._run_tasks(tasks, 3)
    executor.assert_called_once_with(max_workers=3, initializer=kernels.worker_init, initargs=(3,))
    assert [call.args for call in pool.submit.call_args_list] == [(pipeline._score_one, task) for task in tasks]
    assert [call.args for call in progress.call_args_list] == [
        (done, 3, *results[index], 100.0) for done, index in enumerate([1, 2, 0], 1)
    ]
    assert list(result.items()) == results
    executor.return_value.__exit__.assert_called_once_with(None, None, None)


@pytest.mark.parametrize("jobs", [1, 2])
def test_scoring_failure_propagates_without_reporting_failed_task(monkeypatch, controlled_pool, jobs):
    executor, pool = controlled_pool
    error = ValueError("cannot score broken PDF")
    success = ("good", {"overall_score": 100.0})
    tasks = [("good",), ("broken",)]
    if jobs == 1:
        monkeypatch.setattr(pipeline, "_score_one", Mock(side_effect=[success, error]))
    else:
        good, broken = Future(), Future()
        good.set_result(success)
        broken.set_exception(error)
        pool.submit.side_effect = [good, broken]
        monkeypatch.setattr(pipeline, "as_completed", lambda futures: iter(futures))
    progress = Mock()
    monkeypatch.setattr(pipeline, "_progress", progress)
    monkeypatch.setattr(pipeline.time, "monotonic", lambda: 100.0)
    with pytest.raises(ValueError, match="cannot score broken PDF") as raised:
        pipeline._run_tasks(tasks, jobs)
    assert raised.value is error
    progress.assert_called_once_with(1, 2, *success, 100.0)
    if jobs == 2:
        assert executor.return_value.__exit__.call_args.args[:2] == (ValueError, error)
