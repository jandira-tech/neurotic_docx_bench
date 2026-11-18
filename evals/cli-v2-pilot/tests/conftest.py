#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC

# SPDX-License-Identifier: AGPL-3.0-only

"""Shared pytest fixtures for the held-out pilot's harness tests."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PKG_ROOT = HERE.parent
# Task paths resolve from the package itself: its fixtures/ holds every source.
REPO_ROOT = PKG_ROOT


def _resolve_binary() -> Path | None:
    """`JUBARTE_CLI`, else `jubarte` on PATH. Build it from a jubarte-redlines
    checkout (`cargo build --bin jubarte`) and point `JUBARTE_CLI` at it."""
    candidate = os.environ.get("JUBARTE_CLI")
    if candidate:
        p = Path(candidate).resolve()
        return p if p.is_file() else None
    found = shutil.which("jubarte")
    return Path(found) if found else None


JUBARTE_CLI = _resolve_binary()


def _ensure_binary() -> Path:
    if JUBARTE_CLI is None:
        pytest.skip("no jubarte binary: set JUBARTE_CLI or put jubarte on PATH")
    return JUBARTE_CLI


@pytest.fixture(scope="session")
def jubarte_binary() -> Path:
    return _ensure_binary()


@pytest.fixture()
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture()
def tasks_dir() -> Path:
    return PKG_ROOT / "tasks"


@pytest.fixture()
def harness_pkg() -> Path:
    return PKG_ROOT / "harness"


@pytest.hookimpl(trylast=True)
def pytest_terminal_summary(terminalreporter):
    """Emit the required independent line and branch percentages."""
    import io
    import json
    from contextlib import redirect_stdout

    plugin = terminalreporter.config.pluginmanager.getplugin("_cov")
    if plugin and plugin.cov_controller and plugin.cov_controller.cov:
        buf = io.StringIO()
        with redirect_stdout(buf):
            plugin.cov_controller.cov.json_report(outfile="-")
        totals = json.loads(buf.getvalue())["totals"]
        lines = 100 * totals["covered_lines"] / max(totals["num_statements"], 1)
        branches = (
            100
            * totals.get("covered_branches", 0)
            / max(totals.get("num_branches", 0), 1)
        )
        terminalreporter.write_line(
            f"Coverage: {lines:.2f}% lines, {branches:.2f}% branches"
        )
