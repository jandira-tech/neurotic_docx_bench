"""Spec for ``jubarte_release``: find a jubarte binary of an exact version locally, else
download the GitHub release asset, else ``cargo install`` it from crates.io, else fail."""

from __future__ import annotations

import hashlib
import io
import json
import stat
import subprocess
import tarfile
from pathlib import Path

import pytest

from neurotic_docx_bench import jubarte_release as jr


def _script(path: Path, version: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\necho 'jubarte {version}'\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _tarball(version: str, folder: str) -> bytes:
    body = f"#!/bin/sh\necho 'jubarte {version}'\n".encode()
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tar:
        info = tarfile.TarInfo(f'{folder}/jubarte')
        info.size, info.mode = len(body), 0o755
        tar.addfile(info, io.BytesIO(body))
        font = tarfile.TarInfo(f'{folder}/fonts/NOTICE.txt')
        font.size = 2
        tar.addfile(font, io.BytesIO(b'ok'))
    return buf.getvalue()


class FakeWeb:
    """``fetch(url) -> bytes``; unknown URLs are 404s."""

    def __init__(self, pages: dict[str, bytes]) -> None:
        self.pages = pages
        self.seen: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.seen.append(url)
        if url not in self.pages:
            raise jr.NotFound(url)
        return self.pages[url]


def test_parse_version_takes_the_first_semver():
    assert jr.parse_version('jubarte 0.10.0') == '0.10.0'
    assert jr.parse_version('jubarte 0.9.3 (673aff74)') == '0.9.3'
    assert jr.parse_version('no version here') is None
    assert jr.normalize('v0.10.0') == '0.10.0'


@pytest.mark.parametrize(
    ('system', 'machine', 'name'),
    [
        ('Darwin', 'arm64', 'jubarte-0.10.0-macos-aarch64.tar.gz'),
        ('Darwin', 'x86_64', 'jubarte-0.10.0-macos-x86_64.tar.gz'),
        ('Linux', 'x86_64', 'jubarte-0.10.0-linux-x86_64.tar.gz'),
        ('Linux', 'aarch64', 'jubarte-0.10.0-linux-aarch64.tar.gz'),
        ('Windows', 'AMD64', 'jubarte-0.10.0-windows-x86_64.zip'),
    ],
)
def test_asset_name_matches_the_release_naming(system, machine, name):
    assert jr.asset_name('0.10.0', system=system, machine=machine) == name


def test_a_local_binary_of_that_version_wins_and_nothing_is_fetched(tmp_path):
    old = _script(tmp_path / 'a' / 'jubarte', '0.9.3')
    new = _script(tmp_path / 'b' / 'jubarte', '0.10.0')
    web = FakeWeb({})
    got = jr.resolve('0.10.0', cache=tmp_path / 'cache', candidates=[old, new], fetch=web)
    assert got == jr.Resolved(path=new, version='0.10.0', source='local')
    assert web.seen == []


def test_a_missing_local_version_downloads_the_github_release_and_checks_its_sha(tmp_path):
    asset = jr.asset_name('0.10.0')
    blob = _tarball('0.10.0', asset.removesuffix('.tar.gz'))
    base = f'https://github.com/{jr.REPO}/releases/download/v0.10.0'
    sums = f'{hashlib.sha256(blob).hexdigest()}  {asset}\n{"0" * 64}  other.tar.gz\n'.encode()
    web = FakeWeb({f'{base}/SHA256SUMS.txt': sums, f'{base}/{asset}': blob})
    got = jr.resolve('0.10.0', cache=tmp_path / 'cache', candidates=[], fetch=web)
    assert got.source == 'github' and got.version == '0.10.0'
    assert got.path.is_file() and got.path.is_relative_to(tmp_path / 'cache')
    assert (got.path.parent / 'fonts' / 'NOTICE.txt').is_file()  # the fonts travel with the binary
    # A second resolve finds the download in the cache without the network.
    web2 = FakeWeb({})
    again = jr.resolve('0.10.0', cache=tmp_path / 'cache', candidates=[], fetch=web2)
    assert again.path == got.path and again.source == 'local' and web2.seen == []


def test_a_release_asset_with_the_wrong_sha_is_refused(tmp_path):
    asset = jr.asset_name('0.10.0')
    base = f'https://github.com/{jr.REPO}/releases/download/v0.10.0'
    web = FakeWeb({
        f'{base}/SHA256SUMS.txt': f'{"0" * 64}  {asset}\n'.encode(),
        f'{base}/{asset}': _tarball('0.10.0', 'x'),
    })
    with pytest.raises(jr.JubarteNotFound, match='sha256'):
        jr.resolve('0.10.0', cache=tmp_path / 'cache', candidates=[], fetch=web)


def test_without_a_release_it_cargo_installs_the_crate_version(tmp_path):
    crate = json.dumps({'versions': [{'num': '0.8.0', 'yanked': False}]}).encode()
    web = FakeWeb({f'https://crates.io/api/v1/crates/{jr.CRATE}/versions': crate})
    calls: list[list[str]] = []

    def run(cmd, **kw):
        calls.append(cmd)
        if cmd[0] == 'cargo':
            root = Path(cmd[cmd.index('--root') + 1])
            _script(root / 'bin' / 'jubarte', '0.8.0')
            return subprocess.CompletedProcess(cmd, 0, '', '')
        return subprocess.run(cmd, **kw)

    got = jr.resolve(
        '0.8.0', cache=tmp_path / 'cache', candidates=[], fetch=web, run=run, which=lambda name: '/usr/bin/cargo'
    )
    assert got.source == 'crates' and got.version == '0.8.0'
    cargo = next(c for c in calls if c[0] == 'cargo')
    assert cargo[:5] == ['cargo', 'install', jr.CRATE, '--version', '0.8.0']
    assert '--locked' in cargo and cargo[cargo.index('--bin') + 1] == 'jubarte'


def test_a_version_that_exists_nowhere_fails(tmp_path):
    crate = json.dumps({'versions': [{'num': '0.10.0', 'yanked': False}]}).encode()
    web = FakeWeb({f'https://crates.io/api/v1/crates/{jr.CRATE}/versions': crate})
    with pytest.raises(jr.JubarteNotFound, match=r'9\.9\.9'):
        jr.resolve('9.9.9', cache=tmp_path / 'cache', candidates=[], fetch=web, which=lambda name: None)


def test_crates_has_it_but_no_cargo_is_a_clear_failure(tmp_path):
    crate = json.dumps({'versions': [{'num': '0.8.0', 'yanked': False}]}).encode()
    web = FakeWeb({f'https://crates.io/api/v1/crates/{jr.CRATE}/versions': crate})
    with pytest.raises(jr.JubarteNotFound, match='cargo'):
        jr.resolve('0.8.0', cache=tmp_path / 'cache', candidates=[], fetch=web, which=lambda name: None)


def test_no_version_means_the_latest_github_release(tmp_path):
    local = _script(tmp_path / 'a' / 'jubarte', '0.10.0')
    web = FakeWeb({
        f'https://api.github.com/repos/{jr.REPO}/releases/latest': json.dumps({'tag_name': 'v0.10.0'}).encode()
    })
    got = jr.resolve(None, cache=tmp_path / 'cache', candidates=[local], fetch=web)
    assert got == jr.Resolved(path=local, version='0.10.0', source='local')
    assert jr.resolve('latest', cache=tmp_path / 'cache', candidates=[local], fetch=web).version == '0.10.0'


def test_latest_falls_back_to_crates_when_github_is_unreachable(tmp_path):
    crate = json.dumps({'crate': {'max_stable_version': '0.10.0'}}).encode()
    web = FakeWeb({f'https://crates.io/api/v1/crates/{jr.CRATE}': crate})
    assert jr.latest_version(web) == '0.10.0'


def test_local_candidates_resolve_a_relative_root(tmp_path, monkeypatch):
    repo = tmp_path / 'repo'
    repo.mkdir()
    lane = _script(tmp_path / 'speed_bins' / 'jubarte-abc', '0.10.0')
    monkeypatch.chdir(repo)
    assert lane in jr.local_candidates(Path('.'), tmp_path / 'cache')
