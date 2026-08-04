"""The three superdoc packages must be benchmarked at the version bench.yaml claims.

"superdoc" is THREE distinct packages, and the bench pins each one separately:

===========================  ===========================  =============================
bench.yaml run               package                      pin key
===========================  ===========================  =============================
``superdoc``                 PyPI ``superdoc-sdk``        ``python_package:``
``superdoc-ts``              npm ``@superdoc-dev/sdk``    ``package:``
``superdoc-playwright-*``    npm ``superdoc`` (editor)    ``package:``
===========================  ===========================  =============================

``tool_updater.resolve_tool_version`` records ``tool_version`` from what is INSTALLED
(``importlib.metadata`` / ``node_modules/<pkg>/package.json``), never from the bench.yaml
pin. So a pin that disagrees with the environment does not fail loudly — it silently
publishes results labelled with one version that were produced by another. These tests
turn that drift into a red test.

They compare the pin against the *installed* copy, never against npm/PyPI "latest": a new
upstream release must not spontaneously break the suite. Bumping a version means bumping
the pin AND installing it (``bun install`` / ``uv sync``) in the same commit.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pytest
import yaml
from helpers import REPO_ROOT

from neurotic_docx_bench import tool_updater

BENCH_YAML = REPO_ROOT / "bench.yaml"
PYPROJECT = REPO_ROOT / "pyproject.toml"
NODE_MODULES = REPO_ROOT / "node_modules"


def _runs() -> dict[str, dict]:
    doc = yaml.safe_load(BENCH_YAML.read_text())
    return {r["name"]: r for r in doc.get("runs", [])}


def _pinned_version(spec: str) -> str:
    """``@superdoc-dev/sdk@1.21.3`` → ``1.21.3``; ``superdoc-sdk==2.0.0`` → ``2.0.0``."""
    if "==" in spec:
        return spec.split("==", 1)[1].strip()
    name = tool_updater._package_name(spec)
    return spec[len(name) + 1 :].strip()


def _installed_npm(package: str) -> str | None:
    pkg_json = NODE_MODULES / package / "package.json"
    if not pkg_json.is_file():
        return None
    return json.loads(pkg_json.read_text()).get("version")


requires_node_modules = pytest.mark.skipif(
    not NODE_MODULES.is_dir(), reason="node_modules absent (run `bun install`)",
)


def test_superdoc_python_pin_matches_installed_sdk():
    """``superdoc`` run: bench.yaml ``python_package`` == the installed superdoc-sdk."""
    spec = _runs()["superdoc"]["python_package"]
    assert tool_updater._python_package_name(spec) == "superdoc-sdk"
    installed = tool_updater.installed_python_version(spec)
    assert installed is not None, "superdoc-sdk not installed — run `uv sync`"
    assert installed == _pinned_version(spec), (
        f"bench.yaml pins superdoc-sdk=={_pinned_version(spec)} but {installed} is "
        f"installed; the JSONL would record tool_version={installed}. Run `uv sync`."
    )


def test_superdoc_python_pin_matches_pyproject_dependency():
    """The bench.yaml pin and the pyproject dependency must name the same version.

    ``uv sync`` installs what pyproject says; bench.yaml only *labels* the run. If they
    disagree, the pin is decorative.
    """
    spec = _runs()["superdoc"]["python_package"]
    deps = tomllib.loads(PYPROJECT.read_text())["project"]["dependencies"]
    pyproject_pin = next(d for d in deps if re.match(r"^superdoc-sdk\b", d))
    assert pyproject_pin.replace(" ", "") == spec.replace(" ", "")


@requires_node_modules
def test_superdoc_ts_pin_matches_installed_npm_sdk():
    """``superdoc-ts`` run: bench.yaml ``package`` == the installed @superdoc-dev/sdk."""
    spec = _runs()["superdoc-ts"]["package"]
    assert tool_updater._package_name(spec) == "@superdoc-dev/sdk"
    installed = _installed_npm("@superdoc-dev/sdk")
    assert installed is not None, "@superdoc-dev/sdk not installed — run `bun install`"
    assert installed == _pinned_version(spec)


def test_superdoc_ts_pin_matches_the_utils_subpackage_declaration():
    """utils/superdoc/package.json declares the same SDK version as bench.yaml.

    A second declaration of the same dependency is a second thing that can go stale, and
    this one did: it still said 1.19.2 after the adapter moved to the root install.
    """
    spec = _runs()["superdoc-ts"]["package"]
    sub = json.loads(
        (
            REPO_ROOT / "src/neurotic_docx_bench/utils/superdoc/package.json"
        ).read_text(),
    )
    assert sub["dependencies"]["@superdoc-dev/sdk"] == _pinned_version(spec)


@requires_node_modules
def test_superdoc_playwright_pins_match_installed_editor():
    """Every ``superdoc-playwright-*`` run pins the npm *editor* at the installed version.

    A different package from the SDK — the visual_* lanes render through it, so a stale
    pin here mislabels the renderer, not the redline generator.
    """
    installed = _installed_npm("superdoc")
    assert installed is not None, "superdoc (editor) not installed — run `bun install`"
    playwright_runs = {
        name: r for name, r in _runs().items() if name.startswith("superdoc-playwright-")
    }
    assert playwright_runs, "no superdoc-playwright-* runs in bench.yaml"
    for name, run in playwright_runs.items():
        spec = run["package"]
        assert tool_updater._package_name(spec) == "superdoc", name
        assert _pinned_version(spec) == installed, name


def test_pin_documentation_comment_matches_the_actual_pins():
    """The header comment block names all three pins; it must not go stale either.

    It is the only place a reader sees the three packages side by side, and it drifted
    once already (it still claimed 1.19.2 / 1.44.1 after the runs moved on).
    """
    text = BENCH_YAML.read_text()
    header = text.split("runs:", 1)[0]
    runs = _runs()
    for spec in (
        runs["superdoc"]["python_package"],
        runs["superdoc-ts"]["package"],
        runs["superdoc-playwright-rendering"]["package"],
    ):
        version = _pinned_version(spec)
        assert version in header, (
            f"bench.yaml header comment does not mention {spec!r} "
            f"(version {version}); update the pin-documentation block."
        )
