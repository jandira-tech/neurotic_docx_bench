"""The updated competitor pins must agree across smoke/full runs and dependency files."""
from __future__ import annotations

import json
import tomllib

import pytest
import yaml
from helpers import REPO_ROOT


@pytest.mark.parametrize('config_name', ['bench.yaml', 'bench.smoke1.yaml'])
@pytest.mark.parametrize(
    ('package', 'run_names'),
    [
        ('docxodus', ['docxodus', 'docxodus-playwright-rendering',
                      'docxodus-playwright-redlines', 'docxodus-playwright-accepted']),
        ('superdoc', ['superdoc-playwright-rendering',
                      'superdoc-playwright-redlines', 'superdoc-playwright-accepted']),
    ],
)
def test_updated_npm_pins_agree_with_declared_and_locked_versions(config_name, package, run_names):
    package_json = json.loads((REPO_ROOT / 'package.json').read_text())
    version = package_json['dependencies'][package]
    lock = json.loads((REPO_ROOT / 'package-lock.json').read_text())
    assert lock['packages'][f'node_modules/{package}']['version'] == version
    config = yaml.safe_load((REPO_ROOT / config_name).read_text())
    runs = {run['name']: run for run in config['runs']}
    for name in run_names:
        assert runs[name]['package'] == f'{package}@{version}', name
    if package == 'docxodus':
        vendor = json.loads((REPO_ROOT / 'src/neurotic_docx_bench/utils/docxodus/package.json').read_text())
        assert vendor['dependencies'][package] == version


@pytest.mark.parametrize('config_name', ['bench.yaml', 'bench.smoke1.yaml'])
def test_updated_python_sdk_pin_agrees_with_declared_and_locked_version(config_name):
    project = tomllib.loads((REPO_ROOT / 'pyproject.toml').read_text())
    spec = next(dep for dep in project['project']['dependencies'] if dep.startswith('superdoc-sdk=='))
    lock = tomllib.loads((REPO_ROOT / 'uv.lock').read_text())
    locked = next(package for package in lock['package'] if package['name'] == 'superdoc-sdk')
    assert spec == f'superdoc-sdk=={locked["version"]}'
    config = yaml.safe_load((REPO_ROOT / config_name).read_text())
    run = next(run for run in config['runs'] if run['name'] == 'superdoc')
    assert run['python_package'] == spec
