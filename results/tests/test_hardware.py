"""Hardware fingerprint and renderer identity: pure, cheap, always present."""

from __future__ import annotations

import json
import platform
import subprocess

from neurotic_docx_bench import hardware
from neurotic_docx_bench.config import RunConfig


def test_hardware_info_has_the_fields_the_tables_print() -> None:
    info = hardware.hardware_info()
    assert set(info) >= {
        "system",
        "release",
        "machine",
        "cpu",
        "cores",
        "ram_gb",
        "python",
    }
    assert isinstance(info["cores"], int) and info["cores"] >= 1
    assert isinstance(info["ram_gb"], float) and info["ram_gb"] > 0
    assert info["cpu"]  # never empty: falls back to platform.machine()


def test_hardware_info_is_json_serializable() -> None:
    json.dumps(hardware.hardware_info())


def test_renderer_id_for_each_render_backend(monkeypatch) -> None:
    monkeypatch.setattr(hardware, "soffice_version", lambda: "26.2.4.2")
    assert (
        hardware.renderer_id(RunConfig(name="x", render="soffice"))
        == "soffice-26.2.4.2"
    )
    assert (
        hardware.renderer_id(
            RunConfig(name="x", render="playwright", package="superdoc@2.18.0")
        )
        == "playwright:superdoc@2.18.0"
    )
    assert (
        hardware.renderer_id(RunConfig(name="x", render="passthrough")) == "passthrough"
    )
    monkeypatch.setattr(hardware, "word_version", lambda: "16.101.1")
    assert hardware.renderer_id(RunConfig(name="x", render="word")) == "word-16.101.1"
    monkeypatch.setattr(hardware, "word_version", lambda: None)
    assert hardware.renderer_id(RunConfig(name="x", render="word")) == "word-unknown"


def test_word_version_comes_from_osascript() -> None:
    from subprocess import CompletedProcess

    from neurotic_docx_bench.render import word

    calls: list[list[str]] = []

    def run(argv, **_):
        calls.append(list(argv))
        return CompletedProcess(argv, 0, stdout="16.101.1\n", stderr="")

    assert word.word_version(run) == "16.101.1"
    assert calls == [list(word.WORD_VERSION_ARGV)]
    assert (
        word.word_version(lambda argv, **_: CompletedProcess(argv, 1, "", "no word"))
        is None
    )
    assert (
        word.word_version(lambda argv, **_: CompletedProcess(argv, 0, "\n", "")) is None
    )


def test_word_version_is_none_without_osascript(monkeypatch) -> None:
    from neurotic_docx_bench.render import word

    monkeypatch.setattr(
        word, "WORD_VERSION_ARGV", ("definitely-not-osascript", "-e", "x")
    )
    assert word.word_version() is None


def test_renderer_id_soffice_unknown_version(monkeypatch) -> None:
    monkeypatch.setattr(hardware, "soffice_version", lambda: None)
    assert (
        hardware.renderer_id(RunConfig(name="x", render="soffice")) == "soffice-unknown"
    )


def test_cpu_brand_darwin_reads_sysctl(tmp_path) -> None:
    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=[], returncode=0, stdout="Apple M3 Max\n"
        )

    assert hardware._cpu_brand(system="Darwin", run=fake_run) == "Apple M3 Max"


def test_cpu_brand_darwin_falls_back_when_sysctl_fails() -> None:
    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=[], returncode=1, stdout="")

    brand = hardware._cpu_brand(system="Darwin", run=fake_run)
    assert brand == (platform.processor() or platform.machine())


def test_cpu_brand_darwin_swallows_subprocess_errors() -> None:
    def fake_run(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="sysctl", timeout=5)

    brand = hardware._cpu_brand(system="Darwin", run=fake_run)
    assert brand == (platform.processor() or platform.machine())


def test_cpu_brand_linux_parses_model_name(tmp_path) -> None:
    cpuinfo = tmp_path / "cpuinfo"
    cpuinfo.write_text(
        "processor\t: 0\nvendor_id\t: GenuineIntel\nmodel name\t: Intel(R) Xeon(R) W-3345\n",
        encoding="utf-8",
    )
    assert (
        hardware._cpu_brand(system="Linux", cpuinfo=str(cpuinfo))
        == "Intel(R) Xeon(R) W-3345"
    )


def test_cpu_brand_linux_without_model_name_falls_back(tmp_path) -> None:
    cpuinfo = tmp_path / "cpuinfo"
    cpuinfo.write_text("processor\t: 0\nBogoMIPS\t: 48.00\n", encoding="utf-8")
    brand = hardware._cpu_brand(system="Linux", cpuinfo=str(cpuinfo))
    assert brand == (platform.processor() or platform.machine())


def test_cpu_brand_linux_missing_cpuinfo_falls_back(tmp_path) -> None:
    brand = hardware._cpu_brand(system="Linux", cpuinfo=str(tmp_path / "absent"))
    assert brand == (platform.processor() or platform.machine())


def test_soffice_version_none_when_canary_cannot_run(monkeypatch) -> None:
    from neurotic_docx_bench import canary

    def boom() -> str:
        raise RuntimeError("soffice not installed")

    monkeypatch.setattr(canary, "current_soffice_version", boom)
    assert hardware.soffice_version() is None


def test_soffice_version_passes_the_canary_value_through(monkeypatch) -> None:
    from neurotic_docx_bench import canary

    monkeypatch.setattr(canary, "current_soffice_version", lambda: "26.2.4.2")
    assert hardware.soffice_version() == "26.2.4.2"


def test_ram_gb_zero_when_sysconf_is_unavailable(monkeypatch) -> None:
    def no_sysconf(_name: str) -> int:
        raise ValueError("unknown configuration name")

    monkeypatch.setattr(hardware.os, "sysconf", no_sysconf)
    assert hardware._ram_gb() == 0.0


def test_cpu_brand_other_systems_use_the_platform_fallback() -> None:
    brand = hardware._cpu_brand(system="Windows")
    assert brand == (platform.processor() or platform.machine())
