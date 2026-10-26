"""Rebuild the run manifest from what the hub holds under ``outputs/redlines_0929_full`` (issue #76).

    uv run python results/redlines_0929_full/rebuild_manifest.py              # build + report, upload nothing
    uv run python results/redlines_0929_full/rebuild_manifest.py --publish    # + one commit on the head it read

Runs before #77 republished ``run/MANIFEST.sha256.json`` from the files still on disk, so the
published manifest lost every file an earlier ``--prune`` had deleted. This lists the hub again.

The hub is read through a blob-filtered git clone of the dataset, sparse on the run folder,
without LFS smudge: the working tree holds the inline files and the LFS pointers. Every file's
bytes must hash to the git blob id the hub lists. An LFS file's sha256 is its pointer's oid; an
inline file's is the sha256 of its bytes.

The records are every version of the manifest and the 0.13.0 upload's own list
(``upload_20261025.manifest.tsv``), oldest first. The newest record naming a path must agree with
the hub, and every recorded path must still be there, or nothing is published. An older record
that disagrees is reported as replaced; a file no record names is reported as first recorded here.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from hub_upload import REPO_PREFIX, next_parent

from neurotic_docx_bench import hub

MANIFEST = f'run/{hub.MANIFEST_NAME}'
# The 0.13.0 lane was uploaded on 2026-10-25 outside hub_upload.py, with its own list.
UPLOAD_LISTS = ('upload_20261025.manifest.tsv',)
SHA256 = re.compile(r'[0-9a-f]{64}')
LFS_SPEC = b'version https://git-lfs.github.com/spec/v1\n'
URL = f'https://huggingface.co/datasets/{hub.RESULTS_REPO}'
NO_LFS = ('-c', 'filter.lfs.smudge=', '-c', 'filter.lfs.process=', '-c', 'filter.lfs.required=false')


class RebuildError(RuntimeError):
    """The hub does not match its own records; nothing is published."""


@dataclass(frozen=True)
class HubFile:
    blob_id: str
    size: int


def git(checkout: Path, *args: str) -> bytes:
    env = os.environ | {'GIT_LFS_SKIP_SMUDGE': '1'}
    return subprocess.run(['git', '-C', str(checkout), *args], check=True, capture_output=True, env=env).stdout


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def lfs_oid(data: bytes) -> str | None:
    """The sha256 an LFS pointer names, or None for an inline file."""
    if not data.startswith(LFS_SPEC):
        return None
    fields = dict(line.split(' ', 1) for line in data.decode().splitlines()[1:] if ' ' in line)
    oid = fields.get('oid', '').removeprefix('sha256:')
    if not SHA256.fullmatch(oid) or not fields.get('size', '').isdigit():
        raise RebuildError(f'unreadable LFS pointer: {data[:200]!r}')
    return oid


def hub_tree(checkout: Path, revision: str) -> dict[str, HubFile]:
    """Every blob under the run folder at ``revision``, by path relative to it."""
    prefix = REPO_PREFIX + '/'
    tree = {}
    for line in git(checkout, 'ls-tree', '-r', '-l', '-z', '--full-tree', revision, '--', prefix).split(b'\0'):
        if not line:
            continue
        meta, path = line.decode().split('\t', 1)
        _mode, kind, oid, size = meta.split()
        if kind == 'blob' and path.startswith(prefix):
            tree[path[len(prefix) :]] = HubFile(oid, int(size))
    return tree


def records(checkout: Path, revision: str) -> list[tuple[str, dict[str, str]]]:
    """Every version of the manifest and of the upload lists up to ``revision``, oldest first."""
    # A shallow clone stops before the oldest versions, which would then go unchecked.
    if git(checkout, 'rev-parse', '--is-shallow-repository').strip() != b'false':
        raise RebuildError(f'{checkout} is a shallow clone; its history hides older records')
    # Commit order, not commit time: two versions can share a second.
    rank = {c: i for i, c in enumerate(reversed(git(checkout, 'rev-list', '--topo-order', revision).split()))}
    found = []
    for order, name in enumerate((MANIFEST, *UPLOAD_LISTS)):
        path = f'{REPO_PREFIX}/{name}'
        log = git(checkout, 'log', '--full-history', '--diff-filter=AM', '--format=%H', revision, '--', path)
        for commit in log.decode().split():
            text = git(checkout, 'show', f'{commit}:{path}').decode()
            if name == MANIFEST:
                files = json.loads(text)['files']
            else:
                files = {row['key']: row['sha256'] for row in csv.DictReader(io.StringIO(text), delimiter='\t')}
            found.append((rank[commit.encode()], order, f'{commit[:9]} {name}', files))
    found.sort(key=lambda r: (r[0], r[1]))
    return [(label, files) for _, _, label, files in found]


def rebuild(
    tree: dict[str, HubFile], history: list[tuple[str, dict[str, str]]], read: Callable[[str], bytes]
) -> tuple[dict[str, str], dict]:
    """``{path: sha256}`` for every hub file but the manifest, checked against every record."""
    built = {}
    kinds = Counter()
    not_blob = []
    for path, f in sorted(tree.items()):
        if path == MANIFEST:
            continue
        data = read(path)
        if len(data) != f.size or git_blob_sha1(data) != f.blob_id:
            not_blob.append(path)
            continue
        oid = lfs_oid(data)
        built[path] = oid or hashlib.sha256(data).hexdigest()
        kinds['lfs' if oid else 'inline'] += 1
    if not_blob:
        raise RebuildError(f'{len(not_blob)} file(s) whose bytes are not the hub blob: {not_blob[:10]}')
    named: dict[str, list[tuple[str, str]]] = {}
    for label, files in history:
        for path, sha in files.items():
            named.setdefault(path, []).append((label, sha))
    gone, disagree, replaced = [], [], []
    for path, seen in sorted(named.items()):
        if path not in built:
            gone.append(path)
        elif seen[-1][1] != built[path]:
            disagree.append(f'{path} ({seen[-1][0]})')
        else:
            replaced += [(path, label) for label, sha in seen if sha != built[path]]
    if gone or disagree:
        raise RebuildError(
            f'{len(gone)} recorded path(s) gone from the hub: {gone[:10]}; '
            f'{len(disagree)} whose newest record disagrees with the hub: {disagree[:10]}; nothing published'
        )
    report = {
        'n_files': len(built),
        'lfs': kinds['lfs'],
        'inline': kinds['inline'],
        'records': [(label, len(files)) for label, files in history],
        'replaced': replaced,
        'first_recorded': sorted(p for p in built if p not in named),
    }
    return built, report


def checkout_hub(dest: Path, revision: str) -> None:
    """A blob-filtered clone of the dataset, sparse on the run folder, LFS files left as pointers."""
    if not (dest / '.git').is_dir():
        dest.parent.mkdir(parents=True, exist_ok=True)
        git(dest.parent, 'clone', '-q', '--filter=blob:none', '--no-checkout', URL, dest.name)
        git(dest, 'sparse-checkout', 'set', '--no-cone', f'{REPO_PREFIX}/')
    git(dest, 'fetch', '-q', 'origin')
    git(dest, *NO_LFS, 'checkout', '-q', '--detach', revision)


def build(checkout: Path, revision: str) -> tuple[dict[str, str], dict]:
    root = checkout / REPO_PREFIX
    return rebuild(hub_tree(checkout, revision), records(checkout, revision), lambda rel: (root / rel).read_bytes())


def publish(api, checkout: Path, revision: str, data: bytes, message: str) -> str:
    """Commit ``data`` as the run manifest on ``revision``; return the commit, read back."""
    current = api.repo_info(hub.RESULTS_REPO, repo_type=hub.REPO_TYPE).sha
    if current != revision:
        raise RebuildError(f'the hub moved to {current} since {revision} was read; nothing published')
    info = api.upload_file(
        path_or_fileobj=data,
        path_in_repo=f'{REPO_PREFIX}/{MANIFEST}',
        repo_id=hub.RESULTS_REPO,
        repo_type=hub.REPO_TYPE,
        commit_message=message,
        parent_commit=revision,
    )
    commit = next_parent(api, revision, info, message)
    if commit == revision:
        return revision
    with tempfile.TemporaryDirectory() as scratch:
        back = Path(
            api.hf_hub_download(
                hub.RESULTS_REPO,
                f'{REPO_PREFIX}/{MANIFEST}',
                repo_type=hub.REPO_TYPE,
                revision=commit,
                local_dir=scratch,
            )
        ).read_bytes()
    if back != data:
        raise RebuildError(f'the manifest read back from {commit} is not the one uploaded')
    return commit


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--checkout', type=Path, help='keep the dataset clone here (default: a temporary one)')
    ap.add_argument('--out', type=Path, help='write the manifest and report here (default: a new temporary folder)')
    ap.add_argument('--revision', help='hub commit to read (default: the head)')
    ap.add_argument('--publish', action='store_true', help='commit the manifest on that revision')
    a = ap.parse_args()
    api = hub.default_api()
    revision = a.revision or api.repo_info(hub.RESULTS_REPO, repo_type=hub.REPO_TYPE).sha
    out = a.out or Path(tempfile.mkdtemp(prefix='redlines_0929_full_manifest_'))
    out.mkdir(parents=True, exist_ok=True)
    clone = a.checkout or Path(tempfile.mkdtemp(prefix='redlines_0929_full_hub_')) / 'hub'
    try:
        checkout_hub(clone, revision)
        built, report = build(clone, revision)
    finally:
        if a.checkout is None:
            shutil.rmtree(clone.parent)
    path = hub.write_manifest(out, path=out / hub.MANIFEST_NAME, files=built)
    report |= {'revision': revision, 'manifest_sha256': hub.sha256_file(path)}
    (out / 'report.json').write_text(json.dumps(report, indent=1) + '\n')
    folders = Counter('/'.join(p.split('/')[:2]) for p in report['first_recorded'])
    print(f'{revision}: {report["n_files"]} files ({report["lfs"]} LFS, {report["inline"]} inline)', flush=True)
    for label, n in report['records']:
        print(f'  record {label}: {n} entries')
    replaced = Counter(label for _, label in report['replaced'])
    print(f'  replaced by a newer record (paths per older record): {dict(replaced)}')
    print(f'  first recorded here: {dict(folders)}')
    print(f'  wrote {path} and {out / "report.json"}')
    if a.publish:
        message = f'redlines_0929_full: {MANIFEST} rebuilt from the hub tree ({report["n_files"]} files, issue #76)'
        commit = publish(api, clone, revision, path.read_bytes(), message)
        print(f'published {commit}' if commit != revision else 'the hub already has this manifest', flush=True)


if __name__ == '__main__':
    main()
