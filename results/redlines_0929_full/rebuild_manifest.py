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
import sys
import tempfile
from collections import Counter
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from huggingface_hub import CommitOperationAdd
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
# The caller's GIT_ variables that git_env() passes on: tracing, and how the dataset is fetched over
# HTTPS (a proxy's CA bundle, the slow-transfer timeout). Any other can point git at another
# repository, work tree, index, object or reference store, template, namespace or config, or change
# what a pathspec or a ref means; `git rev-parse --local-env-vars` lists only some of those
# (GIT_REFERENCE_BACKEND and GIT_TEMPLATE_DIR are not among them on git 2.56.0).
PASSED_GIT_ENV = re.compile(r'GIT_(TRACE\w*|CURL_VERBOSE|SSL_CAINFO|SSL_CAPATH|HTTP_LOW_SPEED_(LIMIT|TIME))')


class RebuildError(RuntimeError):
    """The run stopped having published nothing: the hub does not match its own records, or the clone cannot be
    used or read; the --revision given with --publish is not the head's commit id; the hub moved since it was
    read; the manifest's path is one a commit cannot put it at (a folder, or an LFS pointer to its content that is
    not canonical) or that the hub ignores, or already holds the manifest's content id (both from its answer to
    the preupload); the upload failed before its commit request was sent; or that request made no commit. The
    claim is this run's; a commit another run sent may land at any time."""


class UnverifiedPublish(RebuildError):
    """The commit request may have made its commit: it failed once it may have been sent, or it returned a commit
    that could not be checked. The hub may hold the manifest; a rerun recognises one already there."""


@dataclass(frozen=True)
class HubFile:
    blob_id: str
    size: int


def git_env() -> dict[str, str]:
    # Replace refs could rewrite the history the records are read from; without lazy fetching a
    # blob-filtered clone could not read an old record at all. The user's global and system
    # config (abbreviations, diff settings, filters) never shape what is read here, nor does any
    # GIT_ variable of the caller's but PASSED_GIT_ENV (a git hook exports GIT_DIR and GIT_WORK_TREE
    # for its own repository, and ``-C`` does not override them).
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_') or PASSED_GIT_ENV.fullmatch(k)}
    return env | {
        'GIT_LFS_SKIP_SMUDGE': '1',
        'GIT_NO_REPLACE_OBJECTS': '1',
        'GIT_CONFIG_GLOBAL': os.devnull,
        'GIT_CONFIG_NOSYSTEM': '1',
        'GIT_TERMINAL_PROMPT': '0',  # the dataset is public; an auth failure fails instead of prompting
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
            # int() would take a sign or underscores; the size git prints is ASCII digits
            if len(header) != 3 or header[0] != oid.encode() or header[1] != b'blob' or not header[2].isdigit():
                errors.seek(0)
                said = errors.read().decode(errors='replace').strip()[:500]
                raise RebuildError(f'git cat-file {oid}: {b" ".join(header).decode(errors="replace")} {said}'.strip())
            size = int(header[2])
            try:
                data = proc.stdout.read(size)
            except (MemoryError, OverflowError) as exc:  # the read makes its size-byte buffer first
                raise RebuildError(f'git cat-file {oid}: a size of {size} bytes, too large to read') from exc
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
        meta, raw = line.split(b'\t', 1)
        try:
            path = raw.decode()
        except UnicodeError as exc:
            raise RebuildError(f'{raw!r} is not UTF-8; a JSON manifest cannot name it') from exc
        mode, kind, oid, size = meta.decode().split()
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
        # --template=: nothing copied from a template folder (hooks, or an objects symlink into another store)
        git(dest.parent, 'clone', '-q', '--template=', '--filter=blob:none', '--no-checkout', URL, dest.name)
        git(dest, 'sparse-checkout', 'set', '--no-cone', f'{REPO_PREFIX}/')
    else:  # a reused clone must already be sparse on the run folder; making it so would empty its worktree
        try:
            patterns = git(dest, 'sparse-checkout', 'list').decode().split()
        except RebuildError:
            patterns = []
        if patterns != [f'{REPO_PREFIX}/']:
            raise RebuildError(
                f'{dest} is not a clone sparse on {REPO_PREFIX}/ (patterns {patterns}); checking it out would '
                'materialise the whole dataset. Point --checkout at a new folder'
            )
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


def leaves(checkout: Path, commit: str) -> dict[bytes, tuple[bytes, ...]]:
    """Every blob and gitlink in ``commit``: ``{path: (mode, type, oid)}`` as git's bytes, no diff config applied.

    Paths stay bytes: git allows names that are not UTF-8 anywhere in the repository.
    """
    entries = {}
    for line in git(checkout, 'ls-tree', '-r', '-z', '--full-tree', commit).split(b'\0'):
        if line:
            meta, path = line.split(b'\t', 1)
            entries[path] = tuple(meta.split())
    return entries


def folders(checkout: Path, commit: str) -> set[bytes]:
    """Every tree in ``commit``, an empty one included: ``leaves`` lists none, as ``ls-tree -r`` lists no tree.
    ``-d`` lists gitlinks too (``leaves`` has them), so only the entries of type tree are kept."""
    listing = git(checkout, 'ls-tree', '-r', '-d', '-z', '--full-tree', commit)
    entries = (line.split(b'\t', 1) for line in listing.split(b'\0') if line)
    return {path for meta, path in entries if meta.split()[1] == b'tree'}


def spelled(path: bytes) -> str:
    """A repo path as text, one spelling per byte string: backslashes doubled, then each byte that is not UTF-8 as
    ``\\xNN`` (backslashreplace alone spells the byte 0xff and a backslash followed by ``xff`` the same)."""
    return path.replace(b'\\', b'\\\\').decode(errors='backslashreplace')


def regular_blob(entry: tuple[bytes, ...] | None) -> bool:
    return entry is not None and entry[:2] in ((b'100644', b'blob'), (b'100755', b'blob'))


def publish(api, checkout: Path, revision: str, data: bytes, message: str) -> str:
    """Commit ``data`` as the run manifest on ``revision``; return the commit, checked through git.

    The upload is two calls, so that what a failure says of the hub rests on which call failed, never on
    the error's shape: ``preupload`` sends everything before the commit request, ``commit_manifest`` the
    commit request. The preupload's answer can stop the run between the two, read in the SDK's order: a path
    that already holds this content id, for which ``create_commit`` would send no commit (the SDK's own test,
    ``hf_api.py`` 5143), read the head and return it without the ``parent_commit`` check; then a path the hub
    ignores. So it is never called for a no-op, and every failure from it on may follow a commit (``UnverifiedPublish``); before it,
    nothing this run sent can make one (``RebuildError``). The commit it returns is fetched and must have
    ``revision`` as its one parent and change nothing else; the head itself means no commit was made. A
    Ctrl-C stops the run with a note saying the same.
    """
    path = f'{REPO_PREFIX}/{MANIFEST}'
    note = 'stopped before the commit request: nothing published by this run'
    try:
        current = api.repo_info(hub.RESULTS_REPO, repo_type=hub.REPO_TYPE, revision=BRANCH).sha
        if current != revision:
            raise RebuildError(
                f'the hub moved to {current} since {revision} was read; nothing published by this run. The new head '
                'may hold another commit of this manifest: rerun on it to check'
            )
        # The hub may store the manifest inline or, if its preupload says so, as an LFS pointer.
        accepted = (data, lfs_pointer(data))
        unread = 'Nothing published by this run: no commit request was sent; rerun once git can read the clone'
        # Read before the upload, so a tree this cannot read stops the run before anything is committed.
        try:
            before = leaves(checkout, revision)
            trees = folders(checkout, revision)
        except RebuildError as exc:
            raise RebuildError(f'{exc}. {unread}') from exc
        key = path.encode()
        under = sorted(leaf for leaf in before if leaf.startswith(key + b'/'))  # ls-tree -r lists a folder's leaves
        if under:
            named = ', '.join(spelled(leaf) for leaf in under[:5])  # a name that is not UTF-8 reads as its bytes
            more = f' and {len(under) - 5} more' if len(under) > 5 else ''
            kinds = Counter(before[leaf][1] for leaf in under)  # a blob, or a gitlink (b'commit')
            held = ' and '.join(
                f'{n} {what}' for n, what in ((kinds[b'blob'], 'file(s)'), (kinds[b'commit'], 'submodule(s)')) if n
            )
            raise RebuildError(
                f'{path} at {revision} is a folder holding {held} ({named}{more}); a commit putting the manifest '
                'there would drop them, so this run makes none. Nothing published by this run; move or remove that '
                'folder on the hub, then rerun'
            )
        if key in trees:  # a folder with no file in it, which leaves() does not list
            inside = any(t.startswith(key + b'/') for t in trees)
            what = 'a folder holding only empty folders' if inside else 'an empty folder'
            raise RebuildError(
                f'{path} at {revision} is {what}; a commit putting the manifest there would replace it, so this run '
                'makes none. Nothing published by this run; remove that folder on the hub, then rerun'
            )
        entry = before.get(key)
        # A blob's bytes in any mode, read with the tree, before anything is sent (a symlink's are its target).
        try:
            there = git(checkout, 'cat-file', 'blob', f'{revision}:{path}') if entry and entry[1] == b'blob' else None
        except RebuildError as exc:
            raise RebuildError(f'{exc}. {unread}') from exc
        # A symlink (mode 120000) stores its target as blob bytes; the same bytes there are not the manifest.
        if regular_blob(entry):
            if there in accepted:
                return revision
            pointer = LFS_POINTER.fullmatch(there)
            if pointer and pointer.group(1).decode() == hashlib.sha256(data).hexdigest():
                # create_commit compares content ids (an LFS pointer's oid), so it would return the head unchanged
                raise RebuildError(
                    f'{path} at {revision} is an LFS pointer to this manifest\'s content that is not its canonical '
                    f'pointer (size {pointer.group(2).decode()} for {len(data)} bytes); create_commit would not replace '
                    'it, since it compares content ids. Nothing published by this run; fix the pointer on the hub'
                )
        operation = CommitOperationAdd(path_in_repo=path, path_or_fileobj=data)
        preupload(api, operation)
        # The preupload's answer (_commit_api.py 777-779), read in the SDK's order: a no-op is dropped before the
        # payload builder looks at shouldIgnore (hf_api.py 5143, _commit_api.py 939).
        remote = getattr(operation, '_remote_oid', None)
        if remote is not None and remote == operation._local_oid:
            # Whether the tree this run read holds this content id at the path itself, in whatever git mode (a
            # symlink whose target bytes are the manifest): only then is the answer about the commit this run read.
            # A regular blob that does was settled above, and main()'s build() refuses a symlink there, so this is
            # true only for a tree build() did not check; publish() stays right on its own.
            explained = there is not None and holds(there, data, operation._upload_mode)
            raise RebuildError(no_op(api, revision, path, entry, remote, explained))
        # create_commit would leave an ignored file out of the commit it still sends (_commit_api.py 939).
        if getattr(operation, '_should_ignore', None):
            raise RebuildError(
                f'the hub ignores {path} (the answer to the preupload, from the repo\'s .gitignore), so a commit would '
                'leave it out. Nothing published by this run; fix the .gitignore on the hub'
            )
        note = (
            'stopped calling create_commit, which sends the commit request: the hub may hold the manifest now; rerun '
            'to check it'
        )
        commit = commit_manifest(api, operation, message, revision)
        note = (
            f'stopped while checking {commit}, which create_commit returned: the hub holds {commit}, which may be '
            'this manifest\'s commit; rerun to check it'
        )
        if commit == revision:  # the branch head did not move: create_commit sent no commit request
            held = f'a mode {entry[0].decode()} entry' if entry else 'no file'
            raise RebuildError(
                f'create_commit made no commit: {BRANCH} is still at {revision}, where {path} holds {held}. The hub '
                'compares content ids, not modes, so an entry with this manifest\'s content counts as the manifest '
                'already there. Nothing published by this run; fix the path on the hub'
            )
        try:
            return verify_upload(checkout, revision, commit, before, data)
        except Exception as exc:
            raise UnverifiedPublish(
                f'create_commit returned {commit}, but checking it failed: {exc}; the hub holds {commit}, so it may '
                'hold the manifest now; rerun to check it (a manifest already there is recognised)'
            ) from exc
    except BaseException as exc:
        if not isinstance(exc, Exception):  # Ctrl-C: stop, but say what may have happened
            exc.add_note(note)
        raise


def holds(blob: bytes, data: bytes, mode: str) -> bool:
    """Whether ``blob`` holds ``data``'s content id in the preupload's upload ``mode`` (``_commit_api.py`` 297).

    A regular file's id is the git blob sha1 of its bytes, so ``blob`` must be them; an LFS file's is the sha256 a
    pointer names, so ``blob`` must be a pointer to theirs.
    """
    if mode == 'lfs':
        pointer = LFS_POINTER.fullmatch(blob)
        return pointer is not None and pointer.group(1).decode() == hashlib.sha256(data).hexdigest()
    return blob == data


def no_op(api, revision: str, path: str, entry: tuple[bytes, ...] | None, remote: str, explained: bool) -> str:
    """Why a no-op the preupload's answer shows stops the run. ``create_commit`` was not called, so nothing was
    published by this run; the rest says whether a rerun or a fix on the hub comes next.

    A fix only when the tree at ``revision`` holds this content id at the path, in the preupload's upload mode
    (``explained``), and the head is still ``revision`` when read again: two equal readings alone do not show the
    branch stayed put, since it may have moved and come back, and the answer may describe the commit it passed
    through.
    """
    said = (
        f'the hub answered the preupload that {path} on {BRANCH} already holds this manifest\'s content id ({remote}), '
        'so create_commit would make no commit; create_commit was not called. Nothing published by this run'
    )
    held = f'a mode {entry[0].decode()} entry' if entry else 'no file'
    if not explained:
        return (
            f'{said}; at {revision}, the commit this run read, {path} holds {held} without this content, so the answer '
            f'describes another commit of {BRANCH} (it moved, or moved and came back): rerun to check it'
        )
    try:
        now = api.repo_info(hub.RESULTS_REPO, repo_type=hub.REPO_TYPE, revision=BRANCH).sha
    except Exception as exc:
        return f'{said}; reading the head of {BRANCH} again failed ({type(exc).__name__}: {exc}): rerun to check it'
    if now != revision:
        return f'{said}; {BRANCH} moved to {now} since {revision} was read and may hold this manifest: rerun on it to check it'
    return (
        f'{said}; {BRANCH} is still at {revision}, where {path} holds {held}. The hub compares content ids, not '
        'modes, so an entry with this content counts as the manifest already there: fix the path on the hub'
    )


def preupload(api, operation: CommitOperationAdd) -> None:
    """Everything the upload sends before its commit request: the preupload, and the storage upload it asks for.

    ``preupload_lfs_files`` sends the preupload request (``huggingface_hub/_commit_api.py`` 764) and, for a
    file the hub keeps in LFS, the storage upload (through the Xet client, or the LFS batch request at
    ``lfs.py`` 185 and the uploads it names). It sends no commit, so whatever fails here, a redirect or a
    response hook included, this run has sent no commit request. ``free_memory=False`` keeps the operation as
    built; the SDK would free only an LFS file's bytes, after their upload (``hf_api.py`` 5385), and the commit
    carries an LFS file's id and size, an inline file's bytes (``_commit_api.py`` 945-964).
    """
    try:
        api.preupload_lfs_files(
            repo_id=hub.RESULTS_REPO,
            additions=[operation],
            repo_type=hub.REPO_TYPE,
            revision=BRANCH,
            free_memory=False,
        )
    except Exception as exc:
        raise RebuildError(
            f'the upload failed before its commit request ({type(exc).__name__}: {exc}); this run sent no commit '
            'request: nothing published by this run'
        ) from exc


def commit_manifest(api, operation: CommitOperationAdd, message: str, revision: str) -> str:
    """The commit request for the preuploaded ``operation``, on ``revision``; the commit it returns.

    ``create_commit`` finds the preupload done (``hf_api.py`` 5329: no preupload request for an operation
    whose upload mode is known, none for an LFS file already uploaded), so the one request it sends is the
    commit (``publish`` never calls it for a no-op, which would read the head instead). Any failure here may
    follow a commit (an answer lost on its way back, a proxy that forwarded the request and answered with an
    error or a redirect, a transport that retried it) and raises ``UnverifiedPublish``.
    """
    try:
        return api.create_commit(
            repo_id=hub.RESULTS_REPO,
            operations=[operation],
            commit_message=message,
            repo_type=hub.REPO_TYPE,
            revision=BRANCH,
            parent_commit=revision,
        ).oid
    except Exception as exc:
        raise UnverifiedPublish(
            f'create_commit failed ({type(exc).__name__}: {exc}); its commit request may have been sent, so the hub '
            'may hold the manifest now; rerun to check it (a manifest already there is recognised)'
        ) from exc


def verify_upload(checkout: Path, revision: str, commit: str, before: dict, data: bytes) -> str:
    """``commit`` must sit on ``revision`` and change only the manifest, to ``data`` as a regular file.

    Folders count as changes too, an empty one included (``leaves`` lists no tree), except the manifest's own
    parents, which a commit writing it makes or keeps.
    """
    path = f'{REPO_PREFIX}/{MANIFEST}'
    key = path.encode()
    accepted = (data, lfs_pointer(data))
    git(checkout, 'fetch', '-q', 'origin')
    parents = git(checkout, 'rev-list', '--parents', '-n', '1', commit).decode().split()
    if parents != [commit, revision]:
        raise RebuildError(f'{commit} is not a commit on {revision} (parents {parents[1:]})')
    after = leaves(checkout, commit)
    after_trees = folders(checkout, commit)
    moved = {t for t in folders(checkout, revision) ^ after_trees if not key.startswith(t + b'/')}
    changed = sorted({p for p in before.keys() | after.keys() if before.get(p) != after.get(p)} | moved)
    if changed != [key]:
        shown = [spelled(p) for p in changed[:10]]
        raise RebuildError(f'{commit} changes {shown}, not only {path}; it is not this upload')
    entry = after.get(key)
    if entry is None:
        if key in after_trees:
            raise RebuildError(f'the manifest at {commit} is a folder, not a regular file; it is not this upload')
        raise RebuildError(f'{commit} removes {path}; it is not this upload')  # in the tree before, then
    if not regular_blob(entry):
        mode = entry[0].decode()
        raise RebuildError(f'the manifest at {commit} is not a regular file (mode {mode}); it is not this upload')
    if git(checkout, 'cat-file', 'blob', f'{commit}:{path}') not in accepted:
        raise RebuildError(f'the manifest at {commit} is not the one uploaded')
    return commit


def main() -> None:
    """Build the manifest and, with ``--publish``, publish it. A Ctrl-C anywhere, the removal of the temporary
    clone included, says what the hub holds; an error that press interrupts is named in its notes."""
    publishing = False
    published = None
    temporary = None  # the folder of a temporary clone, removed at the end
    failure = None

    def outcome() -> str:  # what the hub holds (the module's holds compares a blob with the built bytes)
        if published is not None:
            return f'the hub holds this manifest at {published}'
        if publishing:  # as publish() was called or returned: the two instants look the same here
            return 'the hub may hold the manifest now; rerun to check it'
        return 'nothing published by this run'

    try:
        ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
        ap.add_argument('--checkout', type=Path, help='keep the dataset clone here (default: a temporary one)')
        ap.add_argument('--out', type=Path, help='write the manifest and report here (default: a new temporary folder)')
        ap.add_argument('--revision', help='hub commit to read (default, or main: the head)')
        ap.add_argument('--publish', action='store_true', help='commit the manifest on that revision, which must be the head (its full commit id, or main)')
        ap.add_argument('--lfs-check', type=lfs_limit, default=25, help='LFS downloads to hash (N or all; default: 25)')
        ap.add_argument('--seed', type=int, default=0, help='LFS sampling seed (default: 0)')
        a = ap.parse_args()
        # `--revision "$REV"` with REV unset, say; no git argument can carry a NUL
        if a.revision is not None and (not a.revision.strip() or '\0' in a.revision):
            ap.error(f'--revision {a.revision!r} names no commit: leave it out to read the head of {BRANCH}')
        api = hub.default_api()
        if a.checkout is None:
            temporary = Path(tempfile.mkdtemp(prefix='redlines_0929_full_hub_'))
        clone = a.checkout or temporary / 'hub'
        given = None if a.revision in (None, BRANCH) else a.revision  # the branch's name is its head, read from the hub
        if given is not None and re.fullmatch(r'[0-9a-fA-F]{40}', given):
            given = given.lower()  # a full commit id, in any case, as git takes it
        revision = given or api.repo_info(hub.RESULTS_REPO, repo_type=hub.REPO_TYPE, revision=BRANCH).sha
        if a.publish and given is not None:  # publish() commits only on the head: say so before the build
            head = api.repo_info(hub.RESULTS_REPO, repo_type=hub.REPO_TYPE, revision=BRANCH).sha
            if head != given:  # ids as given: a tag or a short id may name the head, and is still not its id
                raise RebuildError(
                    f'--publish commits only on the head of {BRANCH}, given by no --revision, by --revision {BRANCH} '
                    f'or by its full commit id ({head}); --revision {a.revision!r} is not that id, so nothing '
                    'published by this run: rerun without --revision'
                )
        out = a.out or Path(tempfile.mkdtemp(prefix='redlines_0929_full_manifest_'))
        out.mkdir(parents=True, exist_ok=True)
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
        first_in = Counter('/'.join(p.split('/')[:2]) for p in report['first_recorded'])
        print(f'{revision}: {report["n_files"]} files ({report["lfs"]} LFS, {report["inline"]} inline)', flush=True)
        for label, n in report['records']:
            print(f'  record {label}: {n} entries')
        replaced = Counter(label for _, label in report['replaced'])
        print(f'  replaced by a newer record (paths per older record): {dict(replaced)}')
        print(f'  first recorded here: {dict(first_in)}')
        print(f'  wrote {path} and {out / "report.json"}', flush=True)
        if a.publish:
            message = (
                f'redlines_0929_full: {MANIFEST} rebuilt from the hub tree ({report["n_files"]} files, issue #76)'
            )
            publishing = True  # inside publish() its own notes say what a Ctrl-C left
            commit = published = publish(api, clone, revision, data, message)
            # A foreign commit that made the same change is indistinguishable from this upload: say what is known.
            where = f'{commit}, a commit on {revision} that changes only it' if commit != revision else revision
            print(f'the hub holds this manifest at {where}', flush=True)
    except BaseException as exc:
        failure = exc
        if isinstance(exc, KeyboardInterrupt) and not getattr(exc, '__notes__', None):
            if published is not None:
                exc.add_note(f'stopped after publishing: {outcome()}')
            elif publishing:
                exc.add_note(f'stopped as the upload began or ended: {outcome()}')
            else:
                exc.add_note(f'stopped before the upload: {outcome()}')
        raise
    finally:
        if temporary is not None:
            try:
                try:
                    shutil.rmtree(temporary)
                except OSError as exc:  # a warning: the run's own outcome stands
                    print(f'could not remove the temporary clone {temporary}: {exc}', file=sys.stderr, flush=True)
            except KeyboardInterrupt as stop:  # it takes the place of what was on its way out: name both
                stop.add_note(
                    f'stopped while removing the temporary clone {temporary}, which may be left behind: {outcome()}'
                )
                if failure is not None:
                    said = [f'{type(failure).__name__}: {failure}' if str(failure) else type(failure).__name__]
                    stop.add_note(f'before that the run stopped on {"; ".join(said + getattr(failure, "__notes__", []))}')
                raise


if __name__ == '__main__':
    main()
