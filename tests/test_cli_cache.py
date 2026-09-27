"""``bench run --cache/--no-cache`` and ``bench cache`` (plan item 9a)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from neurotic_docx_bench import cli
from neurotic_docx_bench import content_cache as cc


def _spy_drive(monkeypatch):
    seen: dict[str, object] = {}

    def fake(**kwargs):
        seen["active"] = cc.active()
        seen["kwargs"] = kwargs

    monkeypatch.setattr(cli, "_drive_runs", fake)
    return seen


def test_run_enables_the_cache_next_to_results_by_default(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("BENCH_NO_CACHE", raising=False)
    monkeypatch.delenv("BENCH_CACHE_DIR", raising=False)
    seen = _spy_drive(monkeypatch)
    result = CliRunner().invoke(cli.app, ["run", "--config", str(tmp_path / "bench.yaml"), "--results-dir", str(tmp_path / "results")])
    assert result.exit_code == 0, result.output
    active = seen["active"]
    assert isinstance(active, cc.ContentCache)
    assert active.root == (tmp_path / cc.DEFAULT_DIRNAME).resolve()
    # The cache is scoped to the command: nothing else in the process (or the next test)
    # inherits it.
    assert cc.active() is None


def test_run_releases_the_cache_even_when_the_drive_fails(tmp_path: Path, monkeypatch) -> None:
    def boom(**kwargs):
        raise RuntimeError("drive failed")

    monkeypatch.setattr(cli, "_drive_runs", boom)
    result = CliRunner().invoke(cli.app, ["run", "--config", str(tmp_path / "bench.yaml"), "--results-dir", str(tmp_path / "results")])
    assert result.exit_code != 0
    assert cc.active() is None


def test_run_no_cache_disables_it(tmp_path: Path, monkeypatch) -> None:
    seen = _spy_drive(monkeypatch)
    result = CliRunner().invoke(cli.app, ["run", "--config", str(tmp_path / "bench.yaml"), "--results-dir", str(tmp_path / "results"), "--no-cache"])
    assert result.exit_code == 0, result.output
    assert seen["active"] is None


def test_cache_command_reports_and_clears(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "cache"
    monkeypatch.setenv("BENCH_CACHE_DIR", str(root))
    cache = cc.ContentCache(root)
    cache.put_score("a" * 64, {"overall_score": 1.0})
    result = CliRunner().invoke(cli.app, ["cache"])
    assert result.exit_code == 0, result.output
    assert str(root) in result.output and "score: 1" in result.output
    result = CliRunner().invoke(cli.app, ["cache", "--clear"])
    assert result.exit_code == 0, result.output
    assert not root.exists()
    result = CliRunner().invoke(cli.app, ["cache"])
    assert "score: 0" in result.output


def test_cached_renderer_wraps_only_while_a_cache_is_active(tmp_path: Path) -> None:
    cache = cc.ContentCache(tmp_path / "cache")
    cc.configure(cache)
    try:
        wrapped = cli._cached_renderer(cli.PassthroughRenderer(), "passthrough")
        assert isinstance(wrapped, cc.CachedRenderer)
        assert wrapped.renderer_id == "passthrough"
        assert wrapped.cache is cache
    finally:
        cc.configure(None)
    plain = cli._cached_renderer(cli.PassthroughRenderer(), "passthrough")
    assert isinstance(plain, cli.PassthroughRenderer)


def test_execute_run_scores_through_the_active_cache() -> None:
    """Every ``score_folders_*`` call in the run path receives the active cache
    and the run's renderer id (static check of the call sites, since the run
    path itself needs a rendered corpus)."""
    import ast
    import inspect

    run_path = {"_execute_run", "_accept_compare_stage", "_roundtrip_stage"}
    tree = ast.parse(inspect.getsource(cli))
    calls = [
        node
        for fn in ast.walk(tree)
        if isinstance(fn, ast.FunctionDef) and fn.name in run_path
        for node in ast.walk(fn)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and node.func.attr.startswith("score_folders_")
    ]
    assert len(calls) == 6, len(calls)
    for call in calls:
        keywords = {kw.arg for kw in call.keywords}
        assert {"cache", "renderer_id"} <= keywords, ast.unparse(call)[:80]
