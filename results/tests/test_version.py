"""Bench version: stamped on every store line, major.minor joins the comparability group."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError

import pytest

from neurotic_docx_bench import version as ver


def test_bench_version_reads_installed_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ver, "_installed_version", lambda name: "0.7.0")
    assert ver.bench_version() == "0.7.0"


def test_bench_version_falls_back_when_not_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(name: str) -> str:
        raise PackageNotFoundError(name)

    monkeypatch.setattr(ver, "_installed_version", boom)
    assert ver.bench_version() == "0.0.0+unknown"


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
