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
(``upload_20261025.manifest.tsv``), oldest first. Every newest record naming a path, by git ancestry,
must agree with the hub, and every recorded path must still be there, or nothing is published.
An older record that disagrees is reported as replaced; a file no record names is reported as first recorded here.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import random
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from hub_upload import REPO_PREFIX

from neurotic_docx_bench import hub

MANIFEST = f'run/{hub.MANIFEST_NAME}'
BRANCH = 'main'
# The 0.13.0 lane was uploaded on 2026-10-25 outside hub_upload.py, with its own list.
UPLOAD_LISTS = ('upload_20261025.manifest.tsv',)
# The only pointer form the run's files have (all 12,509 on 2026-10-26); anything else that
# starts like a pointer refuses rather than being hashed as inline bytes.
LFS_POINTER = re.compile(
    rb'version https://git-lfs\.github\.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize (0|[1-9][0-9]*)\n'
)
UPLOAD_LIST_HEADER = ['key', 'size', 'sha256']
URL = f'https://huggingface.co/datasets/{hub.RESULTS_REPO}'
NO_LFS = ('-c', 'filter.lfs.smudge=', '-c', 'filter.lfs.process=', '-c', 'filter.lfs.required=false')


class RebuildError(RuntimeError):
    """The hub does not match its own records; nothing is published."""


@dataclass(frozen=True)
class HubFile:
    blob_id: str
    size: int


def git_env() -> dict[str, str]:
    # Replace refs could rewrite the history the records are read from; without lazy fetching a
    # blob-filtered clone could not read an old record at all. The user's global and system
    # config (abbreviations, diff settings, filters) never shape what is read here.
    env = {k: v for k, v in os.environ.items() if k != 'GIT_NO_LAZY_FETCH'}
    return env | {
        'GIT_LFS_SKIP_SMUDGE': '1',
        'GIT_NO_REPLACE_OBJECTS': '1',
        'GIT_CONFIG_GLOBAL': os.devnull,
        'GIT_CONFIG_NOSYSTEM': '1',
    }


def git(checkout: Path, *args: str, input: bytes | None = None) -> bytes:
    try:
        run = subprocess.run(
            ['git', '-C', str(checkout), *args], check=True, capture_output=True, env=git_env(), input=input
        )
    except subprocess.CalledProcessError as exc:
        error = exc.stderr.decode(errors='replace').strip()[:500]
        raise RebuildError(f'git {" ".join(args[:3])} failed ({exc.returncode}): {error}') from exc
    return run.stdout


@contextmanager
def blob_reader(checkout: Path):
    """``read(oid)``: a blob's bytes as git stores them, before any checkout filter or eol conversion."""
    with tempfile.TemporaryFile() as errors:
        proc = subprocess.Popen(
            ['git', '-C', str(checkout), 'cat-file', '--batch'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=errors,
            env=git_env(),
        )

        def read(oid: str) -> bytes:
            proc.stdin.write(oid.encode() + b'\n')
            proc.stdin.flush()
            header = proc.stdout.readline().split()
            if len(header) != 3 or header[0] != oid.encode() or header[1] != b'blob':
                errors.seek(0)
                said = errors.read().decode(errors='replace').strip()[:500]
                raise RebuildError(f'git cat-file {oid}: {b" ".join(header).decode(errors="replace")} {said}'.strip())
            size = int(header[2])
            data = proc.stdout.read(size)
            if len(data) != size or proc.stdout.read(1) != b'\n':
                raise RebuildError(f'git cat-file {oid}: short read ({len(data)} of {size} bytes)')
            return data

        try:
            yield read
        finally:
            proc.stdin.close()
            proc.stdout.close()
            proc.wait()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def lfs_oid(data: bytes) -> str | None:
    """The sha256 an LFS pointer names, or None for an inline file."""
    if not data.startswith(b'version https://git-lfs'):
        return None
    pointer = LFS_POINTER.fullmatch(data)
    if pointer is None or int(pointer[2]) >= 2**63:
        raise RebuildError(f'not a canonical LFS pointer: {data[:200]!r}')
    return pointer[1].decode()


def hub_tree(checkout: Path, revision: str) -> dict[str, HubFile]:
    """Every blob under the run folder at ``revision``, by path relative to it."""
    prefix = REPO_PREFIX + '/'
    tree = {}
    for line in git(checkout, 'ls-tree', '-r', '-l', '-z', '--full-tree', revision, '--', prefix).split(b'\0'):
        if not line:
            continue
        meta, path = line.decode().split('\t', 1)
        mode, kind, oid, size = meta.split()
        if path.startswith(prefix):
            if kind != 'blob' or mode not in ('100644', '100755'):
                raise RebuildError(f'{path} is not a regular blob (mode {mode}, type {kind})')
            tree[path[len(prefix) :]] = HubFile(oid, int(size))
    return tree


def lfs_pointer(data: bytes) -> bytes:
    """The canonical LFS pointer of ``data``."""
    return f'version https://git-lfs.github.com/spec/v1\noid sha256:{hashlib.sha256(data).hexdigest()}\nsize {len(data)}\n'.encode()


def unique(pairs, where: str) -> dict:
    """``dict(pairs)``, refusing a key that appears twice (json and csv keep the last silently)."""
    twice = sorted(k for k, n in Counter(k for k, _ in pairs).items() if n > 1)
    if twice:
        raise RebuildError(f'{where} has duplicate key(s) {twice[:10]}')
    return dict(pairs)


def parse_record(name: str, raw: bytes, label: str, fetch_lfs=None) -> dict[str, str]:
    """A record's ``{path: sha256}``; one stored in LFS is fetched and must match its pointer."""
    try:
        oid = lfs_oid(raw)
    except RebuildError as exc:
        raise RebuildError(f'{label}: {exc}') from exc
    if oid is not None:
        if fetch_lfs is None:
            raise RebuildError(f'{label} is stored in LFS and no LFS fetcher was given')
        content = fetch_lfs()
        if lfs_pointer(content) != raw:
            raise RebuildError(f'{label} is stored in LFS and the fetched bytes do not match its pointer')
        raw = content
    try:
        text = raw.decode()
    except UnicodeError as exc:
        raise RebuildError(f'{label} is not UTF-8: {exc}') from exc
    if name == MANIFEST:

        def reject_constant(value):
            raise ValueError(f'non-JSON constant {value}')

        try:
            document = json.loads(
                text, object_pairs_hook=lambda pairs: unique(pairs, label), parse_constant=reject_constant
            )
        except ValueError as exc:
            raise RebuildError(f'{label} is not valid JSON: {exc}') from exc
        if not isinstance(document, dict) or not isinstance(document.get('files'), dict):
            raise RebuildError(f'{label} must be an object with a files object')
        files = document['files']
        if any(
            not isinstance(k, str) or not isinstance(v, str) or re.fullmatch(r'[0-9a-f]{64}', v) is None
            for k, v in files.items()
        ):
            raise RebuildError(f'{label} must map string paths to lowercase sha256 digests')
        return files
    try:
        # Quotes are literal characters: csv's quoting would accept an unterminated quote silently.
        rows = list(csv.reader(io.StringIO(text), delimiter='\t', quoting=csv.QUOTE_NONE, strict=True))
    except csv.Error as exc:
        raise RebuildError(f'{label} is not a tab-separated list: {exc}') from exc
    if not rows or rows[0] != UPLOAD_LIST_HEADER or any(len(row) != len(UPLOAD_LIST_HEADER) for row in rows):
        raise RebuildError(f'{label} is not a {"/".join(UPLOAD_LIST_HEADER)} list (header {rows[:1]})')
    if any(
        re.fullmatch(r'[0-9]+', size) is None or re.fullmatch(r'[0-9a-f]{64}', digest) is None
        for _, size, digest in rows[1:]
    ):
        raise RebuildError(f'{label} has an invalid size or lowercase sha256 digest')
    return unique([(key, digest) for key, _size, digest in rows[1:]], label)


def records(checkout: Path, revision: str, fetch_lfs=None, commits_by_label=None) -> list[tuple[str, dict[str, str]]]:
    """Every version of the manifest and of the upload lists up to ``revision``, oldest first.

    A record is a version whose blob differs from at least one parent's, merges included, or a
    file present at a root commit. Ancestry determines which records are newest for each path. Paths
    are read from each commit's tree, so a blob not fetched yet is never taken for an absent file.
    ``fetch_lfs(commit, path)`` returns the bytes of a record stored in LFS.
    """
    # A shallow clone or a grafts file stops the history before the oldest versions.
    if git(checkout, 'rev-parse', '--is-shallow-repository').strip() != b'false':
        raise RebuildError(f'{checkout} is a shallow clone; its history hides older records')
    grafts = checkout / git(checkout, 'rev-parse', '--git-path', 'info/grafts').decode().strip()
    if grafts.exists():
        raise RebuildError(f'{grafts} rewrites the history the records are read from')
    lines = [
        line.split() for line in git(checkout, 'rev-list', '--topo-order', '--parents', revision).decode().splitlines()
    ]
    commits = [line[0] for line in reversed(lines)]
    parents = {line[0]: line[1:] for line in lines}
    names = {f'{REPO_PREFIX}/{name}': name for name in (MANIFEST, *UPLOAD_LISTS)}
    blobs: dict[str, dict[str, str]] = {commit: {} for commit in commits}
    for commit in commits:
        for entry in git(checkout, 'ls-tree', '-z', '--full-tree', commit, '--', *names).split(b'\0'):
            if entry:
                meta, path = entry.decode().split('\t', 1)
                _mode, kind, oid = meta.split()
                if kind == 'blob' and path in names:
                    blobs[commit][path] = oid
    found = []
    for rank, commit in enumerate(commits):
        for order, path in enumerate(names):
            blob = blobs[commit].get(path)
            if blob is not None and (not parents[commit] or any(blobs[p].get(path) != blob for p in parents[commit])):
                found.append((rank, order, commit, path, blob))
    found.sort(key=lambda r: (r[0], r[1]))
    parsed = {}
    history = []
    for _, _, commit, path, blob in found:
        label = f'{commit[:9]} {names[path]}'
        if commits_by_label is not None and commits_by_label.setdefault(label, commit) != commit:
            raise RebuildError(f'two commits share the label {label}; nothing published')
        key = (names[path], blob)
        if key not in parsed:
            fetch = None if fetch_lfs is None else (lambda c=commit, p=path: fetch_lfs(c, p))
            parsed[key] = parse_record(names[path], git(checkout, 'cat-file', 'blob', blob), label, fetch)
        history.append((label, parsed[key]))
    return history


def rebuild(
    tree: dict[str, HubFile], history: list[tuple[str, dict[str, str]]], read: Callable[[str], bytes], newest=None
) -> tuple[dict[str, str], dict]:
    """``{path: sha256}`` for every hub file but the manifest, checked against every record.

    ``newest(labels)`` picks, among the records naming one path, those that must agree with the hub
    (``build`` passes git ancestry). Without it every record must agree.
    """
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
            if path != MANIFEST:
                named.setdefault(path, []).append((label, sha))
    gone, disagree, replaced = [], [], []
    for path, seen in sorted(named.items()):
        if path not in built:
            gone.append(path)
        else:
            labels = [label for label, _ in seen]
            latest = set(labels) if newest is None else newest(labels)
            disagree += [f'{path} ({label})' for label, sha in seen if label in latest and sha != built[path]]
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
    """A blob-filtered clone of the dataset, sparse on the run folder, LFS files left as pointers.

    The checkout is what fetches the run folder's blobs in one batch; the bytes are read from the
    objects (``blob_reader``), never from the working-tree files a filter or eol rule may convert.
    """
    if not (dest / '.git').is_dir():
        dest.parent.mkdir(parents=True, exist_ok=True)
        git(dest.parent, 'clone', '-q', '--filter=blob:none', '--no-checkout', URL, dest.name)
        git(dest, 'sparse-checkout', 'set', '--no-cone', f'{REPO_PREFIX}/')
    git(dest, 'fetch', '-q', 'origin')
    git(dest, *NO_LFS, '-c', 'core.autocrlf=false', '-c', 'core.eol=lf', 'checkout', '-q', '--detach', revision)


def build(checkout: Path, revision: str, fetch_lfs=None) -> tuple[dict[str, str], dict]:
    commits = {}
    history = records(checkout, revision, fetch_lfs, commits)
    independent_by_commits = {}

    def newest(labels):
        distinct = tuple(sorted({commits[label] for label in labels}))
        if distinct not in independent_by_commits:
            independent_by_commits[distinct] = set(
                git(checkout, 'merge-base', '--independent', *distinct).decode().split()
            )
        independent = independent_by_commits[distinct]
        return {label for label in labels if commits[label] in independent}

    tree = hub_tree(checkout, revision)
    with blob_reader(checkout) as read:
        return rebuild(tree, history, lambda rel: read(tree[rel].blob_id), newest)


def hub_fetcher(api, repo_id: str, revision: str):
    """Pinned downloads, removed as soon as the caller finishes reading each file."""

    @contextmanager
    def fetch(path: str):
        with tempfile.TemporaryDirectory() as scratch:
            try:
                got = api.hf_hub_download(repo_id, path, repo_type=hub.REPO_TYPE, revision=revision, local_dir=scratch)
            except Exception as exc:
                raise RebuildError(f'LFS download {path} at {revision} failed: {exc}') from exc
            yield Path(got)

    return fetch


def check_lfs(checkout: Path, revision: str, fetch, count: int | str, seed: int) -> int:
    entries = {}
    with blob_reader(checkout) as read:
        for path, entry in sorted(hub_tree(checkout, revision).items()):
            # Canonical pointers fit in 256 bytes; inline payloads can be much larger.
            if entry.size <= 256:
                oid = lfs_oid(read(entry.blob_id))
                if oid is not None:
                    entries[path] = oid
    paths = sorted(entries)
    chosen = paths if count == 'all' else random.Random(seed).sample(paths, min(count, len(paths)))
    for path in chosen:
        try:
            with fetch(f'{REPO_PREFIX}/{path}') as got:
                if hub.sha256_file(got) != entries[path]:
                    raise RebuildError(f'LFS {path} fetched bytes do not match the pointer oid')
        except OSError as exc:
            raise RebuildError(f'LFS {path} could not be checked: {exc}') from exc
    return len(chosen)


def lfs_limit(value: str) -> int | str:
    if value == 'all':
        return value
    if re.fullmatch(r'[0-9]+', value):
        return int(value)
    raise argparse.ArgumentTypeError('expected a non-negative integer or all')


def leaves(checkout: Path, commit: str) -> dict[str, tuple[str, ...]]:
    """Every blob and gitlink in ``commit``: ``{path: (mode, type, oid)}``, no diff config applied."""
    entries = {}
    for line in git(checkout, 'ls-tree', '-r', '-z', '--full-tree', commit).split(b'\0'):
        if line:
            meta, path = line.decode().split('\t', 1)
            entries[path] = tuple(meta.split())
    return entries


def publish(api, checkout: Path, revision: str, data: bytes, message: str) -> str:
    """Commit ``data`` as the run manifest on ``revision``; return the commit, checked through git.

    A no-op upload skips the ``parent_commit`` check and returns whatever the branch head is, so
    the commit is fetched and must have ``revision`` as its one parent and change nothing else.
    """
    path = f'{REPO_PREFIX}/{MANIFEST}'
    current = api.repo_info(hub.RESULTS_REPO, repo_type=hub.REPO_TYPE, revision=BRANCH).sha
    if current != revision:
        raise RebuildError(f'the hub moved to {current} since {revision} was read; nothing published')
    # The hub may store the manifest inline or, if its preupload says so, as an LFS pointer.
    accepted = (data, lfs_pointer(data))
    present = git(checkout, 'ls-tree', '-z', revision, '--', path)
    if present and git(checkout, 'cat-file', 'blob', f'{revision}:{path}') in accepted:
        return revision
    info = api.upload_file(
        path_or_fileobj=data,
        path_in_repo=path,
        repo_id=hub.RESULTS_REPO,
        repo_type=hub.REPO_TYPE,
        commit_message=message,
        parent_commit=revision,
        revision=BRANCH,
    )
    commit = info.oid
    git(checkout, 'fetch', '-q', 'origin')
    parents = git(checkout, 'rev-list', '--parents', '-n', '1', commit).decode().split()
    if parents != [commit, revision]:
        raise RebuildError(f'{commit} is not a commit on {revision} (parents {parents[1:]})')
    before, after = leaves(checkout, revision), leaves(checkout, commit)
    changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
    if changed != [path]:
        raise RebuildError(f'{commit} changes {changed[:10]}, not only {path}; it is not this upload')
    if git(checkout, 'cat-file', 'blob', f'{commit}:{path}') not in accepted:
        raise RebuildError(f'the manifest at {commit} is not the one uploaded')
    return commit


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--checkout', type=Path, help='keep the dataset clone here (default: a temporary one)')
    ap.add_argument('--out', type=Path, help='write the manifest and report here (default: a new temporary folder)')
    ap.add_argument('--revision', help='hub commit to read (default: the head)')
    ap.add_argument('--publish', action='store_true', help='commit the manifest on that revision')
    ap.add_argument('--lfs-check', type=lfs_limit, default=25, help='LFS downloads to hash (N or all; default: 25)')
    ap.add_argument('--seed', type=int, default=0, help='LFS sampling seed (default: 0)')
    a = ap.parse_args()
    api = hub.default_api()
    revision = a.revision or api.repo_info(hub.RESULTS_REPO, repo_type=hub.REPO_TYPE, revision=BRANCH).sha
    out = a.out or Path(tempfile.mkdtemp(prefix='redlines_0929_full_manifest_'))
    out.mkdir(parents=True, exist_ok=True)
    clone = a.checkout or Path(tempfile.mkdtemp(prefix='redlines_0929_full_hub_')) / 'hub'
    try:
        checkout_hub(clone, revision)

        def fetch_lfs(commit: str, path: str) -> bytes:
            with hub_fetcher(api, hub.RESULTS_REPO, commit)(path) as got:
                return got.read_bytes()

        built, report = build(clone, revision, fetch_lfs)
        checked = check_lfs(clone, revision, hub_fetcher(api, hub.RESULTS_REPO, revision), a.lfs_check, a.seed)
        report |= {'lfs_checked': checked, 'seed': a.seed}
        # hub.write_manifest's bytes, kept in memory: what is published is what was built, whatever
        # the out folder holds (a symlink there would otherwise redirect the write or the read).
        data = (json.dumps(hub.manifest_document(built), indent=2, sort_keys=True) + '\n').encode()
        path = out / hub.MANIFEST_NAME
        path.unlink(missing_ok=True)
        path.write_bytes(data)
        report |= {'revision': revision, 'manifest_sha256': hashlib.sha256(data).hexdigest()}
        (out / 'report.json').write_text(json.dumps(report, indent=1) + '\n')
        folders = Counter('/'.join(p.split('/')[:2]) for p in report['first_recorded'])
        print(f'{revision}: {report["n_files"]} files ({report["lfs"]} LFS, {report["inline"]} inline)', flush=True)
        for label, n in report['records']:
            print(f'  record {label}: {n} entries')
        replaced = Counter(label for _, label in report['replaced'])
        print(f'  replaced by a newer record (paths per older record): {dict(replaced)}')
        print(f'  first recorded here: {dict(folders)}')
        print(f'  wrote {path} and {out / "report.json"}', flush=True)
        if a.publish:
            message = (
                f'redlines_0929_full: {MANIFEST} rebuilt from the hub tree ({report["n_files"]} files, issue #76)'
            )
            commit = publish(api, clone, revision, data, message)
            print(f'published {commit}' if commit != revision else 'the hub already has this manifest', flush=True)
    finally:
        if a.checkout is None:
            shutil.rmtree(clone.parent)


if __name__ == '__main__':
    main()
