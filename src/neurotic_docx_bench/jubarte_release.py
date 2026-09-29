"""Find a jubarte binary of an exact version: locally first, else the GitHub release
asset (checked against the release's ``SHA256SUMS.txt``), else ``cargo install`` of the
crates.io crate, else :class:`JubarteNotFound`.

No version (or ``latest``) means the latest GitHub release, with crates.io's newest stable
version when GitHub cannot be reached. Downloads and cargo installs land under the cache
(``BENCH_JUBARTE_CACHE``, default ``~/.cache/neurotic-docx-bench/jubarte``) and are found
there by the next resolve without the network.

The network goes through the injected ``fetch(url) -> bytes`` (raising :class:`NotFound`
for a 404) so the tests never touch it.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import re
import shutil
import subprocess
import tarfile
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

REPO = 'jandira-tech/jubarte-redlines'
CRATE = 'jubarte-redlines'
BIN = 'jubarte'
USER_AGENT = 'neurotic-docx-bench'
_SEMVER = re.compile(r'(\d+\.\d+\.\d+)')
_OS = {'darwin': 'macos', 'linux': 'linux', 'windows': 'windows'}
_ARCH = {'arm64': 'aarch64', 'aarch64': 'aarch64', 'x86_64': 'x86_64', 'amd64': 'x86_64'}

Fetch = Callable[[str], bytes]
Run = Callable[..., subprocess.CompletedProcess]


class NotFound(Exception):
    """``fetch`` got a 404."""


class JubarteNotFound(Exception):
    """No jubarte of the asked version could be found or installed; the message says why."""


@dataclass(frozen=True)
class Resolved:
    path: Path
    version: str
    source: str  # local | github | crates


def http_get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise NotFound(url) from exc
        raise


def default_cache() -> Path:
    return Path(os.environ.get('BENCH_JUBARTE_CACHE', Path.home() / '.cache' / 'neurotic-docx-bench' / 'jubarte'))


def parse_version(text: str) -> str | None:
    match = _SEMVER.search(text)
    return match.group(1) if match else None


def normalize(version: str) -> str:
    return version.strip().removeprefix('v')


def binary_version(path: Path, run: Run = subprocess.run) -> str | None:
    """The semver ``path --version`` prints, None when it does not run."""
    try:
        proc = run([str(path), '--version'], capture_output=True, text=True, timeout=30, check=False)
    except OSError, subprocess.TimeoutExpired:
        return None
    return parse_version(proc.stdout or '') if proc.returncode == 0 else None


def asset_name(version: str, *, system: str | None = None, machine: str | None = None) -> str:
    system = (system or platform.system()).lower()
    machine = (machine or platform.machine()).lower()
    os_name, arch = _OS.get(system, system), _ARCH.get(machine, machine)
    ext = 'zip' if os_name == 'windows' else 'tar.gz'
    return f'jubarte-{version}-{os_name}-{arch}.{ext}'


def cached_binaries(cache: Path) -> list[Path]:
    """Binaries earlier resolves left in the cache: release folders and cargo roots."""
    exe = BIN + ('.exe' if platform.system() == 'Windows' else '')
    return sorted([*cache.glob(f'*/jubarte-*/{exe}'), *cache.glob(f'*-cargo/bin/{exe}')])


def local_candidates(root: Path | None = None, cache: Path | None = None) -> list[Path]:
    """Where a jubarte may already sit on this machine, most explicit first:
    ``BENCH_JUBARTE``, ``PATH``, ``~/.cargo/bin``, the cache, the bench's vendored copy,
    and the speed-lane builds next to the repository (``../speed_bins/jubarte-*``).
    A development build under a ``target/`` folder is never a candidate: its
    ``--version`` names a release its code may no longer be."""
    out: list[Path] = []
    if env := os.environ.get('BENCH_JUBARTE'):
        out.append(Path(env))
    if on_path := shutil.which(BIN):
        out.append(Path(on_path))
    out.append(Path.home() / '.cargo' / 'bin' / BIN)
    out.extend(cached_binaries(cache or default_cache()))
    if root is not None:
        root = root.resolve()  # a relative root's parent would be "." and miss ../speed_bins
        out.append(root / 'src' / 'neurotic_docx_bench' / 'utils' / 'jubarte' / 'jubarte-rust' / BIN)
        out.extend(sorted((root.parent / 'speed_bins').glob('jubarte-*')))
    seen: set[Path] = set()
    unique = []
    for p in out:
        if p.is_file() and p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def find_local(version: str, candidates: Sequence[Path], run: Run = subprocess.run) -> Path | None:
    for path in candidates:
        if binary_version(path, run) == version:
            return path
    return None


def latest_version(fetch: Fetch) -> str:
    """The latest GitHub release tag; crates.io's newest stable version when GitHub fails."""
    try:
        tag = json.loads(fetch(f'https://api.github.com/repos/{REPO}/releases/latest'))['tag_name']
        return normalize(tag)
    except NotFound, OSError, KeyError, ValueError:
        pass
    try:
        return normalize(json.loads(fetch(f'https://crates.io/api/v1/crates/{CRATE}'))['crate']['max_stable_version'])
    except (NotFound, OSError, KeyError, ValueError) as exc:
        raise JubarteNotFound(f'cannot tell the latest jubarte: neither GitHub {REPO} nor crates.io answered') from exc


def _extract(blob: bytes, name: str, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    if name.endswith('.zip'):
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            zf.extractall(dest)
        return
    with tarfile.open(fileobj=io.BytesIO(blob), mode='r:gz') as tar:
        tar.extractall(dest, filter='data')


def github_download(version: str, cache: Path, fetch: Fetch) -> Path | None:
    """The release binary for this platform under ``cache/<version>/``; None when the
    release or this platform's asset does not exist. A sha256 mismatch is an error."""
    base = f'https://github.com/{REPO}/releases/download/v{version}'
    name = asset_name(version)
    try:
        sums = fetch(f'{base}/SHA256SUMS.txt').decode()
    except NotFound, OSError:
        return None
    expected = {parts[1].lstrip('*'): parts[0] for line in sums.splitlines() if len(parts := line.split()) == 2}
    if name not in expected:
        return None
    blob = fetch(f'{base}/{name}')
    got = hashlib.sha256(blob).hexdigest()
    if got != expected[name]:
        raise JubarteNotFound(f'{name}: sha256 {got} does not match SHA256SUMS.txt ({expected[name]})')
    dest = cache / version
    _extract(blob, name, dest)
    folder = name.removesuffix('.tar.gz').removesuffix('.zip')
    exe = dest / folder / (BIN + ('.exe' if name.endswith('.zip') else ''))
    if not exe.is_file():
        raise JubarteNotFound(f'{name} has no {folder}/{exe.name}')
    exe.chmod(exe.stat().st_mode | 0o111)
    return exe


def crates_has(version: str, fetch: Fetch) -> bool:
    try:
        versions = json.loads(fetch(f'https://crates.io/api/v1/crates/{CRATE}/versions'))['versions']
    except NotFound, OSError, KeyError, ValueError:
        return False
    return any(v.get('num') == version and not v.get('yanked') for v in versions)


def cargo_install(
    version: str, cache: Path, fetch: Fetch, run: Run, which: Callable[[str], str | None]
) -> Path | None:
    """``cargo install`` the crate version into ``cache/<version>-cargo``; None when
    crates.io does not have that version."""
    if not crates_has(version, fetch):
        return None
    if which('cargo') is None:
        raise JubarteNotFound(f'crates.io has {CRATE} {version} but cargo is not installed')
    root = cache / f'{version}-cargo'
    cmd = ['cargo', 'install', CRATE, '--version', version, '--root', str(root), '--bin', BIN, '--locked']
    proc = run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        tail = ' '.join((proc.stderr or '').split())[-400:]
        raise JubarteNotFound(f'cargo install {CRATE} {version} failed: {tail}')
    exe = root / 'bin' / BIN
    return exe if exe.is_file() else None


def resolve(
    version: str | None,
    *,
    root: Path | None = None,
    cache: Path | None = None,
    candidates: Sequence[Path] | None = None,
    fetch: Fetch = http_get,
    run: Run = subprocess.run,
    which: Callable[[str], str | None] = shutil.which,
) -> Resolved:
    """A jubarte binary whose ``--version`` is ``version`` (the latest release when None
    or ``latest``): local, else GitHub release, else crates.io; else JubarteNotFound."""
    cache = cache or default_cache()
    wanted = latest_version(fetch) if version in (None, '', 'latest') else normalize(version)
    pool = [*(candidates if candidates is not None else local_candidates(root, cache)), *cached_binaries(cache)]
    if (path := find_local(wanted, pool, run)) is not None:
        return Resolved(path=path, version=wanted, source='local')
    for source, get in (
        ('github', lambda: github_download(wanted, cache, fetch)),
        ('crates', lambda: cargo_install(wanted, cache, fetch, run, which)),
    ):
        path = get()
        if path is None:
            continue
        got = binary_version(path, run)
        if got != wanted:
            raise JubarteNotFound(f'{source} gave {path} reporting {got!r}, not {wanted}')
        return Resolved(path=path, version=wanted, source=source)
    raise JubarteNotFound(
        f'jubarte {wanted}: not on this machine, no GitHub release v{wanted} of {REPO} for '
        f'{asset_name(wanted)}, and not on crates.io as {CRATE}'
    )
