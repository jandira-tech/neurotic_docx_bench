"""The published wheel: version 0.7.0, no vendored competitor tools, competitors optional."""

from __future__ import annotations

import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text())


def test_version_is_0_8_0() -> None:
    assert _pyproject()["project"]["version"] == "0.8.0"


def test_competitor_sdks_are_an_extra_not_core_dependencies() -> None:
    proj = _pyproject()["project"]
    core = " ".join(proj["dependencies"])
    for name in ("superdoc-sdk", "playwright", "redlines", "nupunkt"):
        assert name not in core, name
    extra = " ".join(proj["optional-dependencies"]["competitors"])
    for name in ("superdoc-sdk", "playwright", "redlines", "nupunkt"):
        assert name in extra, name
    assert "docx-revisions" in core


def test_wheel_config_excludes_the_vendored_tools() -> None:
    wheel = _pyproject()["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert any("utils/" in e for e in wheel["exclude"])


@pytest.mark.slow
def test_built_wheel_has_no_vendored_tools_and_is_small(tmp_path: Path) -> None:
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path), str(ROOT)],
        check=True,
        capture_output=True,
        text=True,
    )
    version = _pyproject()["project"]["version"]
    wheels = list(tmp_path.glob(f"neurotic_docx_bench-{version}-*.whl"))
    assert len(wheels) == 1, list(tmp_path.iterdir())
    with zipfile.ZipFile(wheels[0]) as zf:
        names = zf.namelist()
    assert not any(n.startswith("neurotic_docx_bench/utils/") for n in names)
    assert "neurotic_docx_bench/utils.py" in names
    assert "neurotic_docx_bench/cli.py" in names
    assert wheels[0].stat().st_size < 20 * 2**20
    assert sys.version_info >= (3, 14)
