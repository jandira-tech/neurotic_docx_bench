"""Hardware fingerprint and renderer identity: pure, cheap, always present."""

from __future__ import annotations

import json

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
    assert hardware.renderer_id(RunConfig(name="x", render="word")) == "word"


def test_renderer_id_soffice_unknown_version(monkeypatch) -> None:
    monkeypatch.setattr(hardware, "soffice_version", lambda: None)
    assert (
        hardware.renderer_id(RunConfig(name="x", render="soffice")) == "soffice-unknown"
    )
