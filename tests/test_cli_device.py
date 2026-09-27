"""``--device``: the scorer kernel device is exported for the command's duration only
(workers inherit it) and stamped on the profile report (plan item 9c)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from typer.testing import CliRunner

from neurotic_docx_bench import cli, kernels

runner = CliRunner()


def _spy(seen: dict[str, object]):
    def fake(**kwargs):
        seen["device_env"] = os.environ.get(kernels.DEVICE_ENV)
        seen["backend"] = kernels.backend_id()
        sink = kwargs.get("timings_sink")
        if sink is not None:
            sink["t"] = {"renderer_id": "passthrough", "wall_s": 0.5, "benchmarks": {}}

    return fake


def test_run_exports_the_device_only_while_it_runs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv(kernels.DEVICE_ENV, raising=False)
    monkeypatch.delenv("BENCH_NO_CACHE", raising=False)
    kernels.reset()
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli, "_drive_runs", _spy(seen))
    result = runner.invoke(
        cli.app,
        ["run", "--config", str(tmp_path / "bench.yaml"), "--results-dir", str(tmp_path / "results"),
         "--device", "cpu", "--no-cache"],
    )
    assert result.exit_code == 0, result.output
    assert seen["device_env"] == "cpu"
    assert kernels.DEVICE_ENV not in os.environ
    assert kernels.backend_id() == "numpy"


def test_run_without_device_keeps_the_numpy_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv(kernels.DEVICE_ENV, raising=False)
    kernels.reset()
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli, "_drive_runs", _spy(seen))
    result = runner.invoke(
        cli.app, ["run", "--config", str(tmp_path / "bench.yaml"), "--results-dir", str(tmp_path / "results"), "--no-cache"],
    )
    assert result.exit_code == 0, result.output
    assert seen["device_env"] is None and seen["backend"] == "numpy"


def test_unknown_device_is_a_usage_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(cli, "_drive_runs", _spy({}))
    result = runner.invoke(cli.app, ["run", "--config", str(tmp_path / "bench.yaml"), "--device", "tpu"])
    assert result.exit_code == 2
    assert "auto, cpu, mps, cuda" in result.output


def test_profile_reports_the_backend_it_timed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv(kernels.DEVICE_ENV, raising=False)
    kernels.reset()
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli, "_drive_runs", _spy(seen))
    out = tmp_path / "profile.json"
    result = runner.invoke(
        cli.app,
        ["profile", "--config", str(tmp_path / "bench.yaml"), "--results-dir", str(tmp_path / "results"),
         "--dpi", "96", "--device", "cpu", "--json", str(out)],
    )
    assert result.exit_code == 0, result.output
    assert seen["device_env"] == "cpu"
    report = json.loads(out.read_text())
    assert report["scorer_backend"] == seen["backend"]
    assert f"backend {seen['backend']}" in result.output
    assert kernels.DEVICE_ENV not in os.environ
