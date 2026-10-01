"""CPU-derived scoring defaults and explicit worker overrides at the CLI boundary."""

from __future__ import annotations

import importlib.util
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from neurotic_docx_bench import cli, docx_to_pdf, docxide_metrics


@pytest.fixture(params=[None, 1, 24], ids=["unknown-cpus", "one-cpu", "many-cpus"])
def isolated_cli(request, monkeypatch):
    # Typer defaults are evaluated at import time. Load a separate module so other
    # tests retain their original app and registered callbacks.
    monkeypatch.setattr(cli.os, "cpu_count", lambda: request.param)
    spec = importlib.util.spec_from_file_location("_cli_worker_defaults", cli.__file__)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, request.param


@pytest.mark.parametrize(
    ("command", "backend", "option", "keyword", "fallback"),
    [
        ("docx-to-pdf", docx_to_pdf, "--jobs", "jobs", 8),
        ("docxide-metrics", docxide_metrics, "--score-workers", "score_workers", 4),
    ],
)
@pytest.mark.parametrize("override", [None, 3], ids=["default", "explicit"])
def test_scoring_worker_count_reaches_evaluator(
    isolated_cli, monkeypatch, tmp_path, command, backend, option, keyword, fallback, override,
):
    module, cpu_count = isolated_cli
    selection = SimpleNamespace(fixtures=[object()], candidates={}, warnings=[])
    monkeypatch.setattr(module, "_corpus_word_selection", lambda **kwargs: selection)
    evaluator = Mock(return_value={"n": 1, "tools": {}})
    monkeypatch.setattr(backend, "run_eval", evaluator)
    monkeypatch.setattr(module, "_append_converter_lines", Mock())
    args = [command, "--tool", "jubarte", "--json", str(tmp_path / "report.json")]
    if override is not None:
        args += [option, str(override)]
    result = CliRunner().invoke(module.app, args)
    assert result.exit_code == 0, result.output
    evaluator.assert_called_once()
    assert evaluator.call_args.kwargs[keyword] == (override if override is not None else cpu_count or fallback)
