"""Bench version: stamped on every store line, major.minor joins the comparability group.

Outside an installation, ``scripts/release_views.py`` runs ndb from ``src/`` in
a PEP 723 environment that deliberately does not install the package, so
``importlib.metadata`` knows nothing of it. The version that stamps page
provenance, freezes ``RESULTS_v<old>.md`` and dates ``results/scores.json``
must still be the real one: the checkout's ``pyproject.toml`` is the fallback,
and only when there is no checkout either does it stay ``0.0.0+unknown``.
"""

from __future__ import annotations

import tomllib
from importlib.metadata import PackageNotFoundError
from pathlib import Path

import pytest

from neurotic_docx_bench import version as ver

REPO = Path(__file__).resolve().parents[1]


def _not_installed(name: str) -> str:
    raise PackageNotFoundError(name)


def test_bench_version_reads_installed_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ver, "_installed_version", lambda name: "0.7.0")
    assert ver.bench_version() == "0.7.0"


def test_outside_an_installation_the_checkout_pyproject_answers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ver, "_installed_version", _not_installed)
    with (REPO / "pyproject.toml").open("rb") as fh:
        stamped = tomllib.load(fh)["project"]["version"]
    assert ver.bench_version() == stamped
    assert ver.bench_version() != ver.UNKNOWN


def test_without_a_checkout_the_version_stays_unknown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(ver, "_installed_version", _not_installed)
    monkeypatch.setattr(ver, "_pyproject_path", lambda: tmp_path / "nowhere.toml")
    assert ver.bench_version() == ver.UNKNOWN


def test_a_pyproject_without_a_project_version_stays_unknown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.other]\nkey = 1\n", encoding="utf-8")
    monkeypatch.setattr(ver, "_installed_version", _not_installed)
    monkeypatch.setattr(ver, "_pyproject_path", lambda: pyproject)
    assert ver.bench_version() == ver.UNKNOWN


@pytest.mark.parametrize(
    ("full", "series"),
    [
        ("0.7.0", "0.7"),
        ("0.7.3rc1", "0.7"),
        ("1.2.0", "1.2"),
        ("0.0.0+unknown", "0.0"),
        (None, ver.PRE_STAMP_SERIES),
        ("", ver.PRE_STAMP_SERIES),
    ],
)
def test_comparability_series_is_major_minor(full: str | None, series: str) -> None:
    assert ver.series(full) == series


def test_installed_version_reads_real_metadata() -> None:
    assert ver._installed_version("neurotic-docx-bench").count(".") >= 2
