"""Competitor pins agree across the full and smoke configs, the manifests and the lockfiles.

tests/test_superdoc_pins.py holds bench.yaml's superdoc pins to the installed packages.
This file covers what it does not: docxodus everywhere, bench.smoke1.yaml, and the
lockfiles that ``bun install --frozen-lockfile`` / ``uv sync`` install from. Versions are
read from package.json and pyproject.toml, never hardcoded, so a bump only has to be
consistent to pass.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pytest
import yaml
from helpers import REPO_ROOT

CONFIGS = ['bench.yaml', 'bench.smoke1.yaml']
DOCXODUS_VENDOR = REPO_ROOT / 'src/neurotic_docx_bench/utils/docxodus'


def _runs(config_name: str) -> dict[str, dict]:
    config = yaml.safe_load((REPO_ROOT / config_name).read_text())
    return {run['name']: run for run in config['runs']}


def _declared(package_dir: Path, package: str) -> str:
    return json.loads((package_dir / 'package.json').read_text())['dependencies'][package]


def _bun_locked(package_dir: Path, package: str) -> str | None:
    """The version bun.lock resolves ``package`` to (its ``"<pkg>": ["<pkg>@<ver>", ...]`` entry)."""
    text = (package_dir / 'bun.lock').read_text()
    m = re.search(rf'^\s*"{re.escape(package)}": \["{re.escape(package)}@([^"]+)"', text, re.MULTILINE)
    return m.group(1) if m else None


@pytest.mark.parametrize('package_dir', [REPO_ROOT, DOCXODUS_VENDOR], ids=['root', 'utils-docxodus'])
def test_docxodus_declaration_matches_its_bun_lock(package_dir):
    assert _bun_locked(package_dir, 'docxodus') == _declared(package_dir, 'docxodus')


def test_docxodus_vendor_package_declares_the_root_version():
    assert _declared(DOCXODUS_VENDOR, 'docxodus') == _declared(REPO_ROOT, 'docxodus')


@pytest.mark.parametrize('config_name', CONFIGS)
def test_docxodus_runs_pin_the_declared_version(config_name):
    version = _declared(REPO_ROOT, 'docxodus')
    runs = _runs(config_name)
    names = ['docxodus', *(n for n in runs if n.startswith('docxodus-playwright-'))]
    assert len(names) > 1, 'no docxodus-playwright-* runs'
    for name in names:
        assert runs[name]['package'] == f'docxodus@{version}', name


def test_superdoc_editor_declaration_matches_bun_lock():
    assert _bun_locked(REPO_ROOT, 'superdoc') == _declared(REPO_ROOT, 'superdoc')


def test_smoke_superdoc_playwright_runs_pin_the_declared_editor():
    version = _declared(REPO_ROOT, 'superdoc')
    runs = {n: r for n, r in _runs('bench.smoke1.yaml').items() if n.startswith('superdoc-playwright-')}
    assert runs, 'no superdoc-playwright-* runs in bench.smoke1.yaml'
    for name, run in runs.items():
        assert run['package'] == f'superdoc@{version}', name


def test_superdoc_sdk_pin_matches_uv_lock_and_the_smoke_config():
    project = tomllib.loads((REPO_ROOT / 'pyproject.toml').read_text())['project']
    deps = [*project['dependencies'], *project['optional-dependencies']['competitors']]
    spec = next(d for d in deps if re.match(r'^superdoc-sdk\b', d)).replace(' ', '')
    lock = tomllib.loads((REPO_ROOT / 'uv.lock').read_text())
    locked = next(p for p in lock['package'] if p['name'] == 'superdoc-sdk')
    assert spec == f'superdoc-sdk=={locked["version"]}'
    assert _runs('bench.smoke1.yaml')['superdoc']['python_package'].replace(' ', '') == spec
