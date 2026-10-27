"""Rebuild the redlines_0929_full run manifest from the hub's own git tree (issue #76)."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import httpx2
import pytest
from huggingface_hub.errors import HfHubHTTPError

from neurotic_docx_bench import hub

PREFIX = 'outputs/redlines_0929_full'
MANIFEST = f'run/{hub.MANIFEST_NAME}'
HEAD = 'a' * 40


@pytest.fixture
def rebuild(monkeypatch):
    monkeypatch.syspath_prepend('results/redlines_0929_full')
    spec = importlib.util.spec_from_file_location('rebuild_manifest', 'results/redlines_0929_full/rebuild_manifest.py')
    module = importlib.util.module_from_spec(spec)
    # dataclasses look their module up in sys.modules
    monkeypatch.setitem(sys.modules, 'rebuild_manifest', module)
    spec.loader.exec_module(module)
    return module


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pointer(data: bytes) -> bytes:
    return f'version https://git-lfs.github.com/spec/v1\noid sha256:{sha(data)}\nsize {len(data)}\n'.encode()


def manifest(files: dict[str, str]) -> bytes:
    return (json.dumps(hub.manifest_document(files), indent=2, sort_keys=True) + '\n').encode()


def tree_of(rebuild, files: dict[str, bytes]):
    return {p: rebuild.HubFile(rebuild.git_blob_sha1(b), len(b)) for p, b in files.items()}


def git(cwd: Path, *args: str, env: dict | None = None) -> str:
    run = subprocess.run(
        ['git', *args], cwd=cwd, check=True, capture_output=True, text=True, env={**os.environ, **(env or {})}
    )
    return run.stdout.strip()


def test_git_blob_sha1_is_the_id_git_gives(rebuild, tmp_path):
    data = b'inline docx bytes\x00\xff'
    (tmp_path / 'f').write_bytes(data)
    assert rebuild.git_blob_sha1(data) == git(tmp_path, 'hash-object', 'f')


def test_every_hub_file_gets_the_hub_hash_and_the_manifest_is_left_out(rebuild):
    files = {'a/x.docx': b'inline', 'b/y.pdf': pointer(b'large pdf'), MANIFEST: manifest({})}
    history = [('m1', {'a/x.docx': sha(b'inline'), 'b/y.pdf': sha(b'large pdf')})]
    built, report = rebuild.rebuild(tree_of(rebuild, files), history, files.__getitem__)
    assert built == {'a/x.docx': sha(b'inline'), 'b/y.pdf': sha(b'large pdf')}
    assert report['lfs'] == 1 and report['inline'] == 1
    assert report['replaced'] == [] and report['first_recorded'] == []


def test_the_newest_record_disagreeing_with_the_hub_refuses(rebuild):
    files = {'a/x.docx': b'inline'}
    history = [('m1', {'a/x.docx': sha(b'inline')}), ('m2', {'a/x.docx': sha(b'other')})]
    with pytest.raises(rebuild.RebuildError, match=re.escape('a/x.docx')):
        rebuild.rebuild(tree_of(rebuild, files), history, files.__getitem__)


def test_an_older_record_a_newer_one_replaced_is_reported(rebuild):
    files = {'a/x.docx': pointer(b'regenerated')}
    history = [('m1', {'a/x.docx': sha(b'first')}), ('m2', {'a/x.docx': sha(b'regenerated')})]
    built, report = rebuild.rebuild(tree_of(rebuild, files), history, files.__getitem__, newest=lambda labels: {'m2'})
    assert built == {'a/x.docx': sha(b'regenerated')}
    assert report['replaced'] == [('a/x.docx', 'm1')]


def test_a_recorded_path_gone_from_the_hub_refuses(rebuild):
    files = {'a/x.docx': b'inline'}
    history = [('m1', {'a/x.docx': sha(b'inline'), 'a/gone.docx': sha(b'gone')})]
    with pytest.raises(rebuild.RebuildError, match=re.escape('a/gone.docx')):
        rebuild.rebuild(tree_of(rebuild, files), history, files.__getitem__)


def test_a_file_no_record_names_is_first_recorded_here(rebuild):
    files = {'a/x.docx': b'inline', 'new/z.docx': b'never listed'}
    history = [('m1', {'a/x.docx': sha(b'inline')})]
    built, report = rebuild.rebuild(tree_of(rebuild, files), history, files.__getitem__)
    assert built['new/z.docx'] == sha(b'never listed')
    assert report['first_recorded'] == ['new/z.docx']


@pytest.mark.parametrize('bad', [b'tampered', pointer(b'other large pdf')])
def test_bytes_that_are_not_the_hub_blob_refuse(rebuild, bad):
    tree = tree_of(rebuild, {'a/x.docx': b'inline'})
    with pytest.raises(rebuild.RebuildError, match=re.escape('a/x.docx')):
        rebuild.rebuild(tree, [], {'a/x.docx': bad}.__getitem__)


def test_an_lfs_pointer_whose_oid_is_not_a_sha256_refuses(rebuild):
    bad = b'version https://git-lfs.github.com/spec/v1\noid sha256:not-a-digest\nsize 9\n'
    with pytest.raises(rebuild.RebuildError, match='LFS pointer'):
        rebuild.rebuild(tree_of(rebuild, {'b/y.pdf': bad}), [], {'b/y.pdf': bad}.__getitem__)


@pytest.mark.parametrize(
    'bad',
    [
        b'version https://git-lfs.github.com/spec/v1\noid ' + b'a' * 64 + b'\nsize 9\n',
        b'version https://git-lfs.github.com/spec/v1\noid sha256:'
        + b'a' * 64
        + b'\noid sha256:'
        + b'b' * 64
        + b'\nsize 9\n',
        b'version https://git-lfs.github.com/spec/v1\noid sha256:' + b'a' * 64 + b'\nsize 9\nsomething else',
        b'version https://git-lfs.github.com/spec/v1\r\noid sha256:' + b'a' * 64 + b'\r\nsize 9\r\n',
        b'version https://git-lfs.github.com/spec/v1\noid sha256:' + b'a' * 64 + b'\nsize 01\n',
        b'version https://git-lfs.github.com/spec/v1\noid sha256:' + b'a' * 64 + b'\nsize 9223372036854775808\n',
    ],
    ids=['no-sha256-prefix', 'two-oids', 'trailing-text', 'crlf', 'size-leading-zero', 'size-overflow'],
)
def test_a_pointer_that_is_not_canonical_refuses(rebuild, bad):
    with pytest.raises(rebuild.RebuildError, match='LFS pointer'):
        rebuild.rebuild(tree_of(rebuild, {'b/y.pdf': bad}), [], {'b/y.pdf': bad}.__getitem__)


@pytest.fixture
def checkout(tmp_path):
    """A dataset with two manifest versions and the 0.13.0 upload list, one commit each day."""
    repo = tmp_path / 'hub'
    repo.mkdir()
    git(repo, 'init', '-q', '-b', 'main')
    git(repo, 'config', 'user.email', 't@example.com')
    git(repo, 'config', 'user.name', 't')

    def commit(files: dict[str, bytes], day: int) -> str:
        for rel, data in files.items():
            path = repo / PREFIX / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        (repo / 'other').mkdir(exist_ok=True)
        (repo / 'other' / f'outside{day}.txt').write_text('not the run')
        git(repo, 'add', '-A')
        stamp = f'2026-09-{day:02d}T12:00:00+00:00'
        git(repo, 'commit', '-q', '-m', f'day {day}', env={'GIT_AUTHOR_DATE': stamp, 'GIT_COMMITTER_DATE': stamp})
        return git(repo, 'rev-parse', 'HEAD')

    first = commit({'a/x.docx': b'inline', MANIFEST: manifest({'a/x.docx': sha(b'before regeneration')})}, 1)
    tsv = f'key\tsize\tsha256\nc/z.docx\t3\t{sha(b"zzz")}\n'.encode()
    second = commit(
        {
            'b/y.pdf': pointer(b'large pdf'),
            'c/z.docx': b'zzz',
            'd/new.docx': b'new',
            'upload_20261025.manifest.tsv': tsv,
            MANIFEST: manifest({'a/x.docx': sha(b'inline'), 'b/y.pdf': sha(b'large pdf')}),
        },
        2,
    )
    return SimpleNamespace(repo=repo, first=first, second=second, tsv=tsv)


def test_the_tree_is_the_run_folder_with_git_blob_ids(rebuild, checkout):
    tree = rebuild.hub_tree(checkout.repo, checkout.second)
    assert sorted(tree) == ['a/x.docx', 'b/y.pdf', 'c/z.docx', 'd/new.docx', MANIFEST, 'upload_20261025.manifest.tsv']
    blob = git(checkout.repo, 'rev-parse', f'{checkout.second}:{PREFIX}/c/z.docx')
    assert tree['c/z.docx'] == rebuild.HubFile(blob, 3)


def test_the_records_are_every_manifest_version_and_the_upload_list_oldest_first(rebuild, checkout):
    history = rebuild.records(checkout.repo, checkout.second)
    assert [files for _, files in history] == [
        {'a/x.docx': sha(b'before regeneration')},
        {'a/x.docx': sha(b'inline'), 'b/y.pdf': sha(b'large pdf')},
        {'c/z.docx': sha(b'zzz')},
    ]
    assert history[0][0].startswith(checkout.first[:9]) and history[1][0].startswith(checkout.second[:9])


def test_build_reads_the_checkout(rebuild, checkout):
    built, report = rebuild.build(checkout.repo, checkout.second)
    assert built == {
        'a/x.docx': sha(b'inline'),
        'b/y.pdf': sha(b'large pdf'),
        'c/z.docx': sha(b'zzz'),
        'd/new.docx': sha(b'new'),
        'upload_20261025.manifest.tsv': sha(checkout.tsv),
    }
    assert [p for p, _ in report['replaced']] == ['a/x.docx']
    assert report['first_recorded'] == ['d/new.docx', 'upload_20261025.manifest.tsv']


class GitHub:
    """The hub's commit API over a real git repository standing in for the dataset.

    ``preuploads`` lists the paths preuploaded; ``uploads`` the commit requests, so an empty one means no
    commit request was sent; ``commit_calls`` every ``create_commit`` call, a no-op's included. Like the SDK,
    the preupload's answer sets each operation's upload mode and the content id at its path, and
    ``create_commit`` decides a no-op from those (``hf_api.py`` 5143), not from the head it then finds: a
    foreign commit that should make a no-op lands in ``before_preupload``, one in ``before_upload`` meets the
    parent check.
    """

    def __init__(self, origin: Path, before_upload=None, lfs: bool = False, before_preupload=None):
        self.origin = origin
        self.before_upload = before_upload
        self.before_preupload = before_preupload
        self.lfs = lfs  # the hub's preupload picked LFS storage for the upload
        self.preuploads: list[str] = []
        self.uploads: list[dict] = []
        self.commit_calls: list[str] = []
        self.info_revisions = []
        self.lfs_contents = {}

    def head(self) -> str:
        return git(self.origin, 'rev-parse', 'HEAD')

    def commit(self, files: dict[str, bytes], message: str) -> None:
        for rel, data in files.items():
            path = self.origin / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        git(self.origin, 'add', '--', *files)  # like the hub's commit API, only the paths given
        git(self.origin, 'commit', '-q', '-m', message)

    def repo_info(self, repo_id, *, repo_type, revision=None):
        assert revision == 'main'
        self.info_revisions.append(revision)
        return SimpleNamespace(sha=self.head())

    def preupload_lfs_files(self, *, repo_id, additions, repo_type, revision=None, free_memory=True):
        assert revision == 'main' and not free_memory  # as publish() passes it
        if self.before_preupload:
            self.before_preupload(self)
        for operation in additions:
            # The answer (_commit_api.py 777-779). The hub compares content ids only: an LFS pointer's oid, not its
            # text; not modes.
            operation._upload_mode = 'lfs' if self.lfs else 'regular'
            operation._should_ignore = False
            data = operation.path_or_fileobj
            current = subprocess.run(['git', 'cat-file', 'blob', f'HEAD:{operation.path_in_repo}'], cwd=self.origin, capture_output=True)
            remote = re.fullmatch(rb'version https://git-lfs\.github\.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize \d+\n', current.stdout)
            same = (remote.group(1).decode() == sha(data)) if self.lfs and remote else current.stdout == (pointer(data) if self.lfs else data)
            if current.returncode != 0:
                operation._remote_oid = None
            else:
                operation._remote_oid = operation._local_oid if same else '0' * 40
            self.preuploads.append(operation.path_in_repo)

    def create_commit(self, *, repo_id, operations, commit_message, repo_type, revision=None, parent_commit=None):
        assert revision == 'main'
        self.commit_calls.append(parent_commit)
        (operation,) = operations
        path_in_repo, path_or_fileobj = operation.path_in_repo, operation.path_or_fileobj
        assert path_in_repo in self.preuploads  # preuploaded first, as publish() does
        if self.before_upload:
            self.before_upload(self)
        stored = pointer(path_or_fileobj) if self.lfs else path_or_fileobj
        if self.lfs:
            self.lfs_contents[sha(path_or_fileobj)] = path_or_fileobj
        if operation._remote_oid is not None and operation._remote_oid == operation._local_oid:
            # the SDK's no-op: the head, read now, without a commit request or a parent check (hf_api.py 5167)
            return SimpleNamespace(oid=self.head())
        self.uploads.append({  # the commit request, which a no-op never sends (hf_api.py 5167)
            'path_in_repo': path_in_repo,
            'parent_commit': parent_commit,
            'commit_message': commit_message,
            'revision': revision,
        })
        if parent_commit is not None and parent_commit != self.head():
            request = httpx2.Request('POST', f'https://huggingface.co/api/datasets/{repo_id}/commit/{revision}')
            raise HfHubHTTPError('412 parent moved', response=httpx2.Response(412, request=request))
        self.commit({path_in_repo: stored}, commit_message)
        return SimpleNamespace(oid=self.head())

    def hf_hub_download(self, repo_id, filename, *, repo_type, revision=None, local_dir=None):
        out = Path(local_dir) / filename
        out.parent.mkdir(parents=True, exist_ok=True)
        data = subprocess.run(
            ['git', 'show', f'{revision}:{filename}'], cwd=self.origin, check=True, capture_output=True
        ).stdout
        if data.startswith(b'version https://git-lfs'):
            oid = data.splitlines()[1].removeprefix(b'oid sha256:').decode()
            data = self.lfs_contents[oid]
        out.write_bytes(data)
        return str(out)


@pytest.fixture
def hub_pair(tmp_path):
    """A repository standing in for the dataset, and a clone of it."""
    origin = tmp_path / 'origin'
    origin.mkdir()
    git(origin, 'init', '-q', '-b', 'main')
    git(origin, 'config', 'user.email', 't@example.com')
    git(origin, 'config', 'user.name', 't')
    api = GitHub(origin)
    api.commit({f'{PREFIX}/{MANIFEST}': manifest({})}, 'before')
    clone = tmp_path / 'clone'
    git(tmp_path, 'clone', '-q', f'file://{origin}', str(clone))
    return SimpleNamespace(api=api, clone=clone, head=api.head())


def test_publish_commits_on_the_head_it_read_and_checks_it_through_git(rebuild, hub_pair):
    data = manifest({'a/x.docx': sha(b'inline')})
    commit = rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, data, 'rebuild')
    assert commit == hub_pair.api.head() != hub_pair.head
    assert hub_pair.api.uploads == [
        {'path_in_repo': f'{PREFIX}/{MANIFEST}', 'parent_commit': hub_pair.head, 'commit_message': 'rebuild', 'revision': 'main'}
    ]
    assert git(hub_pair.clone, 'show', f'{commit}:{PREFIX}/{MANIFEST}') + '\n' == data.decode()


def test_publish_refuses_when_the_hub_moved_since_it_was_read(rebuild, hub_pair):
    hub_pair.api.commit({f'{PREFIX}/run/RUN.md': b'someone else'}, 'foreign')
    with pytest.raises(rebuild.RebuildError, match='moved'):
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, manifest({'a': sha(b'a')}), 'rebuild')
    assert hub_pair.api.uploads == []


def test_publish_with_nothing_to_change_uploads_nothing(rebuild, hub_pair):
    assert rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, manifest({}), 'rebuild') == hub_pair.head
    assert hub_pair.api.uploads == []


def test_publish_refuses_someone_elses_commit_that_create_commit_returns(rebuild, hub_pair):
    """create_commit returns the head it finds on its no-op path (hf_api.py 5175); here another writer committed the
    same manifest plus a file first. The commit returned is checked, not trusted."""
    data = manifest({'a/x.docx': sha(b'inline')})

    def returns_theirs(**kw):
        hub_pair.api.commit({f'{PREFIX}/{MANIFEST}': data, f'{PREFIX}/new/unlisted.docx': b'not in the manifest'}, 'rebuild')
        return SimpleNamespace(oid=hub_pair.api.head())

    hub_pair.api.create_commit = returns_theirs
    with pytest.raises(rebuild.RebuildError, match=re.escape('unlisted.docx')):
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, data, 'rebuild')


def test_versions_committed_in_the_same_second_keep_their_commit_order(rebuild, tmp_path):
    """The newer of two same-second versions disagrees with the hub: that must refuse."""
    repo = tmp_path / 'same'
    repo.mkdir()
    git(repo, 'init', '-q', '-b', 'main')
    git(repo, 'config', 'user.email', 't@example.com')
    git(repo, 'config', 'user.name', 't')
    stamp = {'GIT_AUTHOR_DATE': '2026-09-01T12:00:00+00:00', 'GIT_COMMITTER_DATE': '2026-09-01T12:00:00+00:00'}
    for files in ({'a/x.docx': sha(b'inline')}, {'a/x.docx': sha(b'what the newer run claimed')}):
        path = repo / PREFIX / 'a' / 'x.docx'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'inline')
        (repo / PREFIX / MANIFEST).parent.mkdir(parents=True, exist_ok=True)
        (repo / PREFIX / MANIFEST).write_bytes(manifest(files))
        git(repo, 'add', '-A')
        git(repo, 'commit', '-q', '-m', 'same second', env=stamp)
    history = rebuild.records(repo, 'HEAD')
    assert [files for _, files in history][-1] == {'a/x.docx': sha(b'what the newer run claimed')}
    with pytest.raises(rebuild.RebuildError, match=re.escape('a/x.docx')):
        rebuild.build(repo, 'HEAD')


def test_a_shallow_clone_hides_old_records_and_refuses(rebuild, checkout, tmp_path):
    shallow = tmp_path / 'shallow'
    git(tmp_path, 'clone', '-q', '--depth', '1', f'file://{checkout.repo}', str(shallow))
    with pytest.raises(rebuild.RebuildError, match='shallow'):
        rebuild.records(shallow, 'HEAD')


def test_a_manifest_version_made_in_a_merge_is_a_record(rebuild, checkout):
    repo = checkout.repo
    git(repo, 'checkout', '-q', '-b', 'side', checkout.first)
    (repo / 'other' / 'side.txt').write_text('side')
    git(repo, 'add', '-A')
    git(repo, 'commit', '-q', '-m', 'side')
    git(repo, 'checkout', '-q', 'main')
    git(repo, 'merge', '-q', '--no-ff', '--no-commit', 'side')
    current = json.loads((repo / PREFIX / MANIFEST).read_text())['files']
    (repo / PREFIX / MANIFEST).write_bytes(manifest(current | {'a/gone.docx': sha(b'gone')}))
    git(repo, 'add', '-A')
    git(repo, 'commit', '-q', '-m', 'merge')
    with pytest.raises(rebuild.RebuildError, match=re.escape('a/gone.docx')):
        rebuild.build(repo, 'HEAD')


def test_replace_refs_do_not_hide_old_records(rebuild, checkout):
    git(checkout.repo, 'replace', '--graft', checkout.second)
    assert len(rebuild.records(checkout.repo, checkout.second)) == 3


def test_a_grafts_file_refuses(rebuild, checkout):
    grafts = checkout.repo / '.git' / 'info' / 'grafts'
    grafts.parent.mkdir(parents=True, exist_ok=True)
    grafts.write_text(checkout.second + '\n')
    with pytest.raises(rebuild.RebuildError, match='grafts'):
        rebuild.records(checkout.repo, checkout.second)


def repo_with(tmp_path: Path, *commits: dict[str, bytes]) -> tuple[Path, list[str]]:
    """A dataset repository with one commit per mapping of run-folder paths to bytes."""
    repo = tmp_path / 'repo'
    repo.mkdir()
    git(repo, 'init', '-q', '-b', 'main')
    git(repo, 'config', 'user.email', 't@example.com')
    git(repo, 'config', 'user.name', 't')
    shas = []
    for i, files in enumerate(commits):
        for rel, data in files.items():
            path = repo / PREFIX / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        git(repo, 'add', '-A')
        git(repo, 'commit', '-q', '--allow-empty', '-m', f'commit {i}')
        shas.append(git(repo, 'rev-parse', 'HEAD'))
    return repo, shas


def tsv(rows: dict[str, bytes]) -> bytes:
    return ('key\tsize\tsha256\n' + ''.join(f'{k}\t{len(v)}\t{sha(v)}\n' for k, v in rows.items())).encode()


def test_a_newer_manifest_outranks_an_upload_list_written_before_it(rebuild, tmp_path):
    """Both name x.docx; the list is unchanged since commit 0, the manifest disagrees since commit 1."""
    repo, _ = repo_with(
        tmp_path,
        {
            'x.docx': b'A',
            MANIFEST: manifest({'x.docx': sha(b'A')}),
            'upload_20261025.manifest.tsv': tsv({'x.docx': b'A'}),
        },
        {MANIFEST: manifest({'x.docx': sha(b'B')})},
    )
    with pytest.raises(rebuild.RebuildError, match=re.escape('x.docx')):
        rebuild.build(repo, 'HEAD')


def test_a_version_that_comes_back_is_the_newest_record_again(rebuild, tmp_path):
    repo, shas = repo_with(
        tmp_path,
        {'x.docx': b'A', MANIFEST: manifest({'x.docx': sha(b'A')})},
        {MANIFEST: manifest({'x.docx': sha(b'B')})},
        {MANIFEST: manifest({'x.docx': sha(b'A')})},
    )
    built, report = rebuild.build(repo, 'HEAD')
    assert built == {'x.docx': sha(b'A')}
    assert report['replaced'] == [('x.docx', f'{shas[1][:9]} {MANIFEST}')]


@pytest.mark.parametrize(
    'record',
    [
        {MANIFEST: b'{"algorithm": "sha256", "files": {"gone.docx": "' + b'a' * 64 + b'"}, "files": {}}'},
        {MANIFEST: b'{"files": {"x.docx": "' + b'a' * 64 + b'", "x.docx": "' + b'b' * 64 + b'"}}'},
        {
            'upload_20261025.manifest.tsv': b'key\tsize\tsha256\nx.docx\t1\t'
            + b'a' * 64
            + b'\nx.docx\t1\t'
            + b'b' * 64
            + b'\n'
        },
    ],
    ids=['two-files-objects', 'two-hashes-for-a-path', 'two-rows-for-a-path'],
)
def test_a_record_with_a_duplicate_key_refuses(rebuild, tmp_path, record):
    repo, _ = repo_with(tmp_path, {'x.docx': b'A', **record})
    with pytest.raises(rebuild.RebuildError, match='duplicate'):
        rebuild.records(repo, 'HEAD')


def test_publish_accepts_the_manifest_stored_in_lfs(rebuild, hub_pair):
    hub_pair.api.lfs = True
    data = manifest({'a/x.docx': sha(b'inline')})
    commit = rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, data, 'rebuild')
    assert commit == hub_pair.api.head() != hub_pair.head


def test_a_record_stored_in_lfs_refuses_rather_than_being_read_as_json(rebuild, tmp_path):
    repo, _ = repo_with(tmp_path, {'x.docx': b'A', MANIFEST: pointer(manifest({'x.docx': sha(b'A')}))})
    with pytest.raises(rebuild.RebuildError, match='LFS'):
        rebuild.records(repo, 'HEAD')


def test_an_old_record_not_fetched_yet_is_still_read(rebuild, tmp_path, monkeypatch):
    """A blob-filtered clone lacks the old manifest blob; an inherited GIT_NO_LAZY_FETCH must not hide it."""
    origin, _ = repo_with(
        tmp_path,
        {'x.docx': b'A', 'gone.docx': b'G', MANIFEST: manifest({'x.docx': sha(b'A'), 'gone.docx': sha(b'G')})},
        {MANIFEST: manifest({'x.docx': sha(b'A')})},
    )
    git(origin, 'rm', '-q', f'{PREFIX}/gone.docx')
    git(origin, 'commit', '-q', '-m', 'gone')
    git(origin, 'config', 'uploadpack.allowFilter', 'true')
    clone = tmp_path / 'partial'
    git(tmp_path, 'clone', '-q', '--filter=blob:none', '--no-checkout', f'file://{origin}', str(clone))
    monkeypatch.setenv('GIT_NO_LAZY_FETCH', '1')
    history = [files for _, files in rebuild.records(clone, 'HEAD')]
    assert history[:1] == [{'x.docx': sha(b'A'), 'gone.docx': sha(b'G')}]


def test_a_record_stored_in_lfs_is_read_through_the_fetcher_and_checked(rebuild, tmp_path):
    content = manifest({'x.docx': sha(b'A')})
    repo, shas = repo_with(tmp_path, {'x.docx': b'A', MANIFEST: pointer(content)})
    asked = []

    def fetch(commit, path):
        asked.append((commit, path))
        return content

    assert rebuild.records(repo, 'HEAD', fetch_lfs=fetch) == [(f'{shas[0][:9]} {MANIFEST}', {'x.docx': sha(b'A')})]
    assert asked == [(shas[0], f'{PREFIX}/{MANIFEST}')]
    with pytest.raises(rebuild.RebuildError, match='LFS'):
        rebuild.records(repo, 'HEAD', fetch_lfs=lambda commit, path: manifest({}))


def test_an_upload_list_with_another_header_refuses(rebuild, tmp_path):
    odd = b'key\tsha256\tkey\ngone.docx\t' + sha(b'A').encode() + b'\tx.docx\n'
    repo, _ = repo_with(tmp_path, {'x.docx': b'A', 'upload_20261025.manifest.tsv': odd})
    with pytest.raises(rebuild.RebuildError, match='header'):
        rebuild.records(repo, 'HEAD')


def merge_records(tmp_path, main_files, side_files, resolved):
    repo, shas = repo_with(
        tmp_path,
        {'x.docx': b'A', MANIFEST: manifest({'x.docx': sha(b'A')})},
        {MANIFEST: manifest(main_files) + b'\n'},
    )
    git(repo, 'checkout', '-q', '-b', 'side', shas[0])
    (repo / PREFIX / MANIFEST).write_bytes(manifest(side_files) + b'\n\n')
    git(repo, 'add', '-A')
    git(repo, 'commit', '-q', '--allow-empty', '-m', 'side')
    side = git(repo, 'rev-parse', 'HEAD')
    git(repo, 'checkout', '-q', 'main')
    # Leave the index at main's version, then write the chosen merge resolution.
    git(repo, 'merge', '-q', '--no-ff', '--no-commit', '-s', 'ours', 'side')
    raw = manifest(resolved)
    raw += b'\n' if resolved == main_files else b'\n\n' if resolved == side_files else b''
    (repo / PREFIX / MANIFEST).write_bytes(raw)
    git(repo, 'add', '-A')
    git(repo, 'commit', '-q', '-m', 'merge')
    return repo, shas[1], side


@pytest.mark.parametrize('chosen', ['side', 'main'])
def test_a_merge_reasserts_the_chosen_parent_record(rebuild, tmp_path, chosen):
    good, bad = {'x.docx': sha(b'A')}, {'x.docx': sha(b'B')}
    main, side = (bad, good) if chosen == 'side' else (good, bad)
    repo, c2, f = merge_records(tmp_path, main, side, good)
    labels = [label for label, _ in rebuild.records(repo, 'HEAD')]
    assert f'{git(repo, "rev-parse", "HEAD")[:9]} {MANIFEST}' in labels
    built, report = rebuild.build(repo, 'HEAD')
    assert built == {'x.docx': sha(b'A')}
    replaced = c2 if chosen == 'side' else f
    assert report['replaced'] == [('x.docx', f'{replaced[:9]} {MANIFEST}')]
    api = GitHub(repo)
    clone = tmp_path / 'clone'
    git(tmp_path, 'clone', '-q', f'file://{repo}', str(clone))
    assert rebuild.publish(api, clone, api.head(), manifest(built), 'rebuild') == api.head()


def test_a_disagreeing_merge_resolution_refuses(rebuild, tmp_path):
    good = {'x.docx': sha(b'A')}
    repo, _, _ = merge_records(tmp_path, good, {'x.docx': sha(b'B')}, {'x.docx': sha(b'C')})
    with pytest.raises(rebuild.RebuildError, match='newest record disagrees'):
        rebuild.build(repo, 'HEAD')


def test_a_merge_dropping_a_path_keeps_incomparable_records_newest(rebuild, tmp_path):
    repo, _, _ = merge_records(tmp_path, {'x.docx': sha(b'A')}, {'x.docx': sha(b'B')}, {})
    with pytest.raises(rebuild.RebuildError, match='newest record disagrees'):
        rebuild.build(repo, 'HEAD')


def test_records_from_the_same_commit_are_both_newest(rebuild, tmp_path):
    repo, _ = repo_with(tmp_path, {
        'x.docx': b'A',
        MANIFEST: manifest({'x.docx': sha(b'B')}),
        'upload_20261025.manifest.tsv': tsv({'x.docx': b'A'}),
    })
    with pytest.raises(rebuild.RebuildError, match=rf'1 whose newest record disagrees.*{re.escape(MANIFEST)}'):
        rebuild.build(repo, 'HEAD')


def test_git_failure_has_a_bounded_diagnosis_and_cause(rebuild, tmp_path):
    repo, _ = repo_with(tmp_path, {'x.docx': b'A'})
    args = ('show', '--bad-' + 'x' * 700, 'HEAD', 'ignored')
    with pytest.raises(rebuild.RebuildError) as exc:
        rebuild.git(repo, *args)
    cause = exc.value.__cause__
    assert isinstance(cause, subprocess.CalledProcessError)
    assert str(exc.value) == f'git {" ".join(args[:3])} failed ({cause.returncode}): {cause.stderr.decode().strip()[:500]}'


def test_publish_creates_a_manifest_absent_from_the_tree(rebuild, hub_pair):
    git(hub_pair.api.origin, 'rm', '-q', f'{PREFIX}/{MANIFEST}')
    hub_pair.api.commit({'README.md': b'no manifest yet'}, 'remove manifest')
    git(hub_pair.clone, 'fetch', '-q', 'origin')
    revision = hub_pair.api.head()
    commit = rebuild.publish(hub_pair.api, hub_pair.clone, revision, manifest({}), 'first manifest')
    assert commit == hub_pair.api.head() != revision
    assert len(hub_pair.api.uploads) == 1


@pytest.mark.parametrize('raw', [
    b'not json', b'[]', b'null', b'{}', b'{"files": []}', b'{"files": null}',
    b'{"files": {"x": 1}}', b'{"files": {"x": "short"}}',
    b'{"files": {"x": "' + b'A' * 64 + b'"}}',
    b'{"files": {}, "extra": NaN}', b'{"files": {}, "extra": Infinity}',
    b'{"files": {}, "extra": -Infinity}', b'\xff',
])
def test_invalid_manifest_records_have_a_labeled_diagnosis(rebuild, raw):
    with pytest.raises(rebuild.RebuildError, match='bad-record'):
        rebuild.parse_record(MANIFEST, raw, 'bad-record')


def test_a_malformed_lfs_record_pointer_names_its_record(rebuild):
    with pytest.raises(rebuild.RebuildError, match='bad-pointer-record'):
        rebuild.parse_record(MANIFEST, b'version https://git-lfs-invalid', 'bad-pointer-record')


@pytest.mark.parametrize(('size', 'digest'), [
    ('1', 'short'), ('1', 'A' * 64), ('-1', 'a' * 64), ('1.5', 'a' * 64),
    ('nan', 'a' * 64), ('', 'a' * 64),
])
def test_invalid_tsv_records_have_a_labeled_diagnosis(rebuild, size, digest):
    raw = f'key\tsize\tsha256\nx.docx\t{size}\t{digest}\n'.encode()
    with pytest.raises(rebuild.RebuildError, match='bad-list'):
        rebuild.parse_record('upload_20261025.manifest.tsv', raw, 'bad-list')


def test_the_parse_cache_does_not_share_validation_between_formats(rebuild, tmp_path):
    raw = tsv({'x.docx': b'A'})
    repo, _ = repo_with(tmp_path, {'upload_20261025.manifest.tsv': raw}, {MANIFEST: raw})
    with pytest.raises(rebuild.RebuildError, match=f'{re.escape(MANIFEST)}.*not valid JSON'):
        rebuild.records(repo, 'HEAD')


def test_a_record_naming_the_manifest_itself_excludes_it_from_checks(rebuild, tmp_path):
    repo, _ = repo_with(tmp_path, {
        'x.docx': b'A', MANIFEST: manifest({'x.docx': sha(b'A'), MANIFEST: sha(b'old manifest')}),
    })
    built, report = rebuild.build(repo, 'HEAD')
    assert built == {'x.docx': sha(b'A')}
    assert report['replaced'] == [] and report['first_recorded'] == []


@pytest.mark.parametrize('mode', ['120000', '160000'])
def test_the_tree_refuses_symlinks_and_gitlinks(rebuild, tmp_path, mode):
    repo, shas = repo_with(tmp_path, {'x.docx': b'A'})
    oid = shas[0] if mode == '160000' else git(repo, 'rev-parse', f'HEAD:{PREFIX}/x.docx')
    git(repo, 'update-index', '--add', '--cacheinfo', mode, oid, f'{PREFIX}/odd')
    git(repo, 'commit', '-q', '-m', 'non-regular entry')
    with pytest.raises(rebuild.RebuildError, match=f'odd.*{mode}'):
        rebuild.hub_tree(repo, 'HEAD')


def test_publish_pins_both_api_calls_to_main(rebuild, hub_pair):
    rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, manifest({'x': sha(b'A')}), 'rebuild')
    assert hub_pair.api.info_revisions == ['main']
    assert hub_pair.api.uploads[0]['revision'] == 'main'
    assert hub_pair.api.uploads[0]['parent_commit'] == hub_pair.head


def test_checkout_disables_line_ending_conversion(rebuild, tmp_path, monkeypatch):
    (tmp_path / '.git').mkdir()
    calls = []

    def run_git(checkout, *args):
        calls.append(args)
        return f'{PREFIX}/\n'.encode() if args[:2] == ('sparse-checkout', 'list') else b''

    monkeypatch.setattr(rebuild, 'git', run_git)
    rebuild.checkout_hub(tmp_path, HEAD)
    checkout = calls[-1]
    assert ('-c', 'core.autocrlf=false', '-c', 'core.eol=lf') == checkout[-8:-4]
    assert checkout[-4:] == ('checkout', '-q', '--detach', HEAD)


class Downloads:
    def __init__(self, files, error=None):
        self.files = files
        self.error = error
        self.calls = []

    def __call__(self, repo_id, filename, *, repo_type, revision, local_dir):
        out = Path(local_dir) / filename
        self.calls.append((filename, revision, out))
        if self.error:
            raise self.error
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(self.files[filename])
        return str(out)


def run_main(rebuild, hub_pair, tmp_path, monkeypatch, *args):
    # a reused --checkout is sparse on the run folder, as checkout_hub makes its own clones
    git(hub_pair.clone, 'sparse-checkout', 'set', '--no-cone', f'{PREFIX}/')
    monkeypatch.setattr(hub, 'default_api', lambda: hub_pair.api)
    out = tmp_path / 'out'
    monkeypatch.setattr(sys, 'argv', [
        'rebuild_manifest', '--checkout', str(hub_pair.clone), '--out', str(out), *args,
    ])
    rebuild.main()
    return json.loads((out / 'report.json').read_text())


@pytest.mark.parametrize(('limit', 'seed'), [(None, 0), ('3', 7), ('all', 4), ('0', 1), ('50', 0)])
def test_main_checks_seeded_lfs_downloads_at_the_pinned_commit(rebuild, hub_pair, tmp_path, monkeypatch, limit, seed):
    files = {f'{PREFIX}/{i:02}.docx': f'docx {i}'.encode() for i in range(30)}
    hub_pair.api.commit({p: pointer(data) for p, data in files.items()}, 'LFS files')
    revision = hub_pair.api.head()
    downloads = Downloads(files)
    monkeypatch.setattr(hub_pair.api, 'hf_hub_download', downloads)
    args = [] if limit is None else ['--lfs-check', limit, '--seed', str(seed)]
    try:
        report = run_main(rebuild, hub_pair, tmp_path, monkeypatch, *args)
    except SystemExit:
        pytest.fail('CLI must accept --lfs-check and --seed')
    count = 25 if limit is None else 30 if limit == 'all' else min(int(limit), 30)
    expected = sorted(files) if limit == 'all' else random.Random(seed).sample(sorted(files), count)
    assert [p for p, _, _ in downloads.calls] == expected
    assert all(rev == revision for _, rev, _ in downloads.calls)
    assert all(not path.exists() for _, _, path in downloads.calls)
    assert report['lfs_checked'] == count and report['seed'] == seed


@pytest.mark.parametrize('failure', ['wrong bytes', 'download failure'])
def test_main_refuses_bad_lfs_bytes_before_publishing(rebuild, hub_pair, tmp_path, monkeypatch, failure):
    name = f'{PREFIX}/x.docx'
    hub_pair.api.commit({name: pointer(b'actual content')}, 'LFS file')
    downloads = Downloads({name: b'wrong bytes'}, OSError('download failed') if failure == 'download failure' else None)
    monkeypatch.setattr(hub_pair.api, 'hf_hub_download', downloads)
    with pytest.raises(rebuild.RebuildError, match=r'LFS.*x.docx'):
        run_main(rebuild, hub_pair, tmp_path, monkeypatch, '--publish')
    assert hub_pair.api.uploads == []
    assert all(not path.exists() for _, _, path in downloads.calls)


def test_help_advertises_lfs_check_and_seed(rebuild, monkeypatch, capsys):
    monkeypatch.setattr(sys, 'argv', ['rebuild_manifest', '--help'])
    with pytest.raises(SystemExit) as exc:
        rebuild.main()
    assert exc.value.code == 0
    help_text = capsys.readouterr().out
    assert '--lfs-check' in help_text and '--seed' in help_text


def lfs_record(rebuild, hub_pair):
    hub_pair.api.commit({f'{PREFIX}/x.docx': b'A'}, 'inline file')
    git(hub_pair.clone, 'fetch', '-q', 'origin')
    hub_pair.api.lfs = True
    data = manifest({'x.docx': sha(b'A')})
    revision = rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.api.head(), data, 'LFS record')
    hub_pair.api.uploads.clear()
    return data, revision


def test_the_module_fetcher_resolves_an_lfs_record_and_the_run_proceeds(rebuild, hub_pair, tmp_path, monkeypatch):
    data, revision = lfs_record(rebuild, hub_pair)
    fetch = rebuild.hub_fetcher(hub_pair.api, hub.RESULTS_REPO, revision)
    with fetch(f'{PREFIX}/{MANIFEST}') as got:
        assert got.read_bytes() == data
    assert not got.exists()
    report = run_main(rebuild, hub_pair, tmp_path, monkeypatch)
    assert report['n_files'] == 1 and report['lfs_checked'] == 1
    assert report['revision'] == revision


def test_the_module_fetcher_refuses_an_lfs_record_with_wrong_resolved_bytes(rebuild, hub_pair, tmp_path, monkeypatch):
    data, _ = lfs_record(rebuild, hub_pair)
    hub_pair.api.lfs_contents = {sha(data): manifest({})}
    with pytest.raises(rebuild.RebuildError, match=r'LFS.*fetched bytes do not match'):
        run_main(rebuild, hub_pair, tmp_path, monkeypatch, '--publish')
    assert hub_pair.api.uploads == []


def test_main_publishes_the_bytes_it_built_not_what_the_out_folder_holds(rebuild, hub_pair, tmp_path, monkeypatch):
    out = tmp_path / 'out'
    out.mkdir()
    (out / hub.MANIFEST_NAME).symlink_to(out / 'report.json')  # the manifest path aliases the report
    report = run_main(rebuild, hub_pair, tmp_path, monkeypatch, '--lfs-check', '0', '--publish')
    published = json.loads(git(hub_pair.clone, 'show', f'{hub_pair.api.head()}:{PREFIX}/{MANIFEST}'))
    assert published['files'] == {}
    assert published == json.loads((out / hub.MANIFEST_NAME).read_text())
    assert not (out / hub.MANIFEST_NAME).is_symlink()
    assert report['manifest_sha256'] == sha((out / hub.MANIFEST_NAME).read_bytes())


def add_gitlink(repo: Path, path: str) -> None:
    git(repo, 'update-index', '--add', '--cacheinfo', f'160000,{"1" * 40},{path}')


def test_publish_sees_a_gitlink_the_diff_config_would_hide(rebuild, hub_pair):
    """A foreign commit on the same parent adds the same manifest and a gitlink under the run folder."""
    data = manifest({'a/x.docx': sha(b'inline')})
    git(hub_pair.clone, 'config', 'diff.ignoreSubmodules', 'all')

    def foreign(api):
        (api.origin / PREFIX / MANIFEST).write_bytes(data)
        git(api.origin, 'add', '-A')
        add_gitlink(api.origin, f'{PREFIX}/sub/module')
        git(api.origin, 'commit', '-q', '-m', 'rebuild')

    def returns_theirs(**kw):  # the head create_commit's no-op path returns
        foreign(hub_pair.api)
        return SimpleNamespace(oid=hub_pair.api.head())

    hub_pair.api.create_commit = returns_theirs
    with pytest.raises(rebuild.RebuildError, match=re.escape('sub/module')):
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, data, 'rebuild')


def test_git_ignores_the_users_global_config(rebuild, tmp_path, monkeypatch):
    config = tmp_path / 'gitconfig'
    config.write_text('[core]\n\tabbrev = 12\n')
    monkeypatch.setenv('GIT_CONFIG_GLOBAL', str(config))
    repo, _ = repo_with(tmp_path, {'a/x.docx': b'x'})
    assert len(git(repo, 'log', '-1', '--format=%h', env={'GIT_CONFIG_GLOBAL': str(config)})) == 12
    assert len(rebuild.git(repo, 'log', '-1', '--format=%h').decode().strip()) != 12


def test_build_reads_blob_bytes_not_the_eol_converted_checkout(rebuild, tmp_path):
    text = b'line one\nline two\n'
    repo, _ = repo_with(tmp_path, {'a/x.txt': text, MANIFEST: manifest({'a/x.txt': sha(text)})})
    (repo / '.gitattributes').write_text('*.txt text eol=crlf\n')
    git(repo, 'add', '-A')
    git(repo, 'commit', '-q', '-m', 'attributes')
    revision = git(repo, 'rev-parse', 'HEAD')
    (repo / PREFIX / 'a/x.txt').unlink()
    git(repo, 'checkout', '-q', '--', '.')
    assert (repo / PREFIX / 'a/x.txt').read_bytes() == text.replace(b'\n', b'\r\n')  # the checkout converted it
    built, _ = rebuild.build(repo, revision)
    assert built['a/x.txt'] == sha(text)


@pytest.mark.parametrize('tail', [
    f'x.docx\t1\t"{"a" * 64}',  # an opening quote with no closing one, at the end of the file
    f'x.docx\t1\t"{"a" * 64}"\n',  # a quoted digest
])
def test_quotes_in_an_upload_list_are_not_csv_syntax(rebuild, tail):
    raw = f'key\tsize\tsha256\n{tail}'.encode()
    with pytest.raises(rebuild.RebuildError, match='bad-list'):
        rebuild.parse_record('upload_20261025.manifest.tsv', raw, 'bad-list')


def commit_entry(repo: Path, tmp_path: Path, mode: str, path: str, data: bytes) -> None:
    """Commit ``data`` at ``path`` with ``mode`` straight through the index (a symlink, a name the disk refuses)."""
    blob = tmp_path / 'blob'
    blob.write_bytes(data)
    oid = git(repo, 'hash-object', '-w', str(blob))
    git(repo, 'update-index', '--add', '--cacheinfo', f'{mode},{oid},{path}')
    git(repo, 'commit', '-q', '-m', 'entry')


def test_publish_refuses_a_symlink_manifest_a_foreign_commit_left(rebuild, hub_pair, tmp_path):
    """A foreign commit turns the manifest into a symlink whose target bytes are the manifest before the preupload,
    whose answer then makes the upload a no-op. Round 18: the run says so without calling create_commit, and the
    rerun on the new head names the symlink."""
    data = manifest({'a/x.docx': sha(b'inline')})
    hub_pair.api.before_preupload = lambda api: commit_entry(api.origin, tmp_path, '120000', f'{PREFIX}/{MANIFEST}', data)
    with pytest.raises(rebuild.RebuildError) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, data, 'rebuild')
    assert hub_pair.api.commit_calls == []
    assert type(exc.value).__name__ != 'UnverifiedPublish', exc.value
    assert 'Nothing published by this run' in str(exc.value) and 'rerun' in str(exc.value)
    hub_pair.api.before_preupload = None
    git(hub_pair.clone, 'fetch', '-q', 'origin')
    with pytest.raises(rebuild.RebuildError, match='120000'):
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.api.head(), data, 'rebuild')
    assert hub_pair.api.commit_calls == []


def test_a_symlink_manifest_is_not_the_manifest_already_there(rebuild, hub_pair, tmp_path):
    data = manifest({'a/x.docx': sha(b'inline')})
    commit_entry(hub_pair.api.origin, tmp_path, '120000', f'{PREFIX}/{MANIFEST}', data)
    git(hub_pair.clone, 'fetch', '-q', 'origin')
    revision = hub_pair.api.head()
    with pytest.raises(rebuild.RebuildError):
        rebuild.publish(hub_pair.api, hub_pair.clone, revision, data, 'rebuild')


def test_publish_checks_a_tree_holding_a_name_that_is_not_utf8(rebuild, hub_pair, tmp_path):
    name = 'elsewhere/' + os.fsdecode(b'\xff') + '.txt'  # outside the run folder
    commit_entry(hub_pair.api.origin, tmp_path, '100644', name, b'latin-1 era\n')
    git(hub_pair.clone, 'fetch', '-q', 'origin')
    revision = hub_pair.api.head()
    data = manifest({'a/x.docx': sha(b'inline')})
    commit = rebuild.publish(hub_pair.api, hub_pair.clone, revision, data, 'rebuild')
    assert commit == hub_pair.api.head() != revision


# Review round 8 (#78)


def test_a_check_that_fails_after_the_upload_says_the_hub_may_hold_the_manifest(rebuild, hub_pair):
    data = manifest({'a/x.docx': sha(b'inline')})
    # The upload commits; the fetch that would check it then fails.
    hub_pair.api.before_upload = lambda api: git(hub_pair.clone, 'remote', 'set-url', 'origin', '/nonexistent/hub')
    with pytest.raises(rebuild.RebuildError) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, data, 'rebuild')
    assert type(exc.value).__name__ == 'UnverifiedPublish'
    assert hub_pair.api.head() != hub_pair.head
    assert hub_pair.api.head() in str(exc.value)
    assert 'may hold' in str(exc.value)


def test_a_name_that_is_not_utf8_under_the_run_folder_is_refused_cleanly(rebuild, tmp_path):
    repo, _ = repo_with(tmp_path, {'a/x.docx': b'x', MANIFEST: manifest({'a/x.docx': sha(b'x')})})
    commit_entry(repo, tmp_path, '100644', f'{PREFIX}/a/' + os.fsdecode(b'\xff') + '.docx', b'latin-1 era\n')
    with pytest.raises(rebuild.RebuildError, match='not UTF-8'):
        rebuild.build(repo, git(repo, 'rev-parse', 'HEAD'))


def test_git_never_prompts_for_credentials(rebuild):
    assert rebuild.git_env()['GIT_TERMINAL_PROMPT'] == '0'


def test_records_from_the_same_commit_are_both_newest_the_list_too(rebuild, tmp_path):
    """The manifest agrees with the hub and the upload list from the same commit does not: still refused."""
    repo, _ = repo_with(tmp_path, {
        'x.docx': b'A',
        MANIFEST: manifest({'x.docx': sha(b'A')}),
        'upload_20261025.manifest.tsv': tsv({'x.docx': b'B'}),
    })
    with pytest.raises(rebuild.RebuildError, match=r'1 whose newest record disagrees.*upload_20261025'):
        rebuild.build(repo, 'HEAD')


def test_main_does_not_claim_a_commit_it_cannot_tell_it_made(rebuild, hub_pair, tmp_path, monkeypatch, capsys):
    run_main(rebuild, hub_pair, tmp_path, monkeypatch, '--lfs-check', '0', '--publish')
    printed = capsys.readouterr().out
    assert f'the hub holds this manifest at {hub_pair.api.head()}' in printed
    assert 'published ' not in printed


# Review round 9 (#78)


def test_an_upload_that_fails_after_the_hub_committed_says_the_hub_may_hold_the_manifest(rebuild, hub_pair):
    data = manifest({'a/x.docx': sha(b'inline')})
    real = hub_pair.api.create_commit

    def lost(**kw):
        real(**kw)  # the hub commits; its answer never arrives
        raise httpx2.ReadTimeout('the response never came')

    hub_pair.api.create_commit = lost
    with pytest.raises(rebuild.RebuildError) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, data, 'rebuild')
    assert type(exc.value).__name__ == 'UnverifiedPublish'
    assert hub_pair.api.head() != hub_pair.head
    assert 'may hold' in str(exc.value)
    assert 'the response never came' in str(exc.value)


# Review round 10 (#78)


def test_ctrl_c_during_the_upload_says_the_hub_may_hold_the_manifest(rebuild, hub_pair):
    data = manifest({'a/x.docx': sha(b'inline')})
    real = hub_pair.api.create_commit

    def interrupted(**kw):
        real(**kw)  # the hub commits; Ctrl-C lands while the answer is on its way
        raise KeyboardInterrupt

    hub_pair.api.create_commit = interrupted
    with pytest.raises(KeyboardInterrupt) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, data, 'rebuild')
    assert hub_pair.api.head() != hub_pair.head
    assert 'may hold' in ' '.join(getattr(exc.value, '__notes__', ()))


def test_ctrl_c_while_checking_the_upload_says_the_hub_may_hold_the_manifest(rebuild, hub_pair, monkeypatch):
    data = manifest({'a/x.docx': sha(b'inline')})

    def interrupted(*args, **kw):
        raise KeyboardInterrupt

    monkeypatch.setattr(rebuild, 'verify_upload', interrupted)
    with pytest.raises(KeyboardInterrupt) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, data, 'rebuild')
    assert hub_pair.api.head() != hub_pair.head
    notes = ' '.join(getattr(exc.value, '__notes__', ()))
    assert f'the hub holds {hub_pair.api.head()}' in notes and 'rerun to check it' in notes  # round 16


# Review round 10, mcode (#78)


def preupload_request():
    return httpx2.Request('POST', f'https://huggingface.co/api/datasets/{hub.RESULTS_REPO}/preupload/main')


def commit_request():
    return httpx2.Request('POST', f'https://huggingface.co/api/datasets/{hub.RESULTS_REPO}/commit/main')


@pytest.mark.parametrize('failure', [
    lambda: HfHubHTTPError('503 preupload', response=httpx2.Response(503, request=preupload_request())),
])
def test_a_failure_before_the_commit_request_says_nothing_was_published(rebuild, hub_pair, failure):
    def fails(**kw):
        raise failure()

    hub_pair.api.preupload_lfs_files = fails
    with pytest.raises(rebuild.RebuildError, match='nothing published by this run') as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, manifest({'a/x.docx': sha(b'inline')}), 'rebuild')
    assert type(exc.value).__name__ != 'UnverifiedPublish'
    assert hub_pair.api.uploads == []


def test_a_server_error_on_the_commit_request_says_the_hub_may_hold_the_manifest(rebuild, hub_pair):
    def fails(**kw):
        raise HfHubHTTPError('502 bad gateway', response=httpx2.Response(502, request=commit_request()))

    hub_pair.api.create_commit = fails
    with pytest.raises(rebuild.RebuildError, match='may hold') as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, manifest({'a/x.docx': sha(b'inline')}), 'rebuild')
    assert type(exc.value).__name__ == 'UnverifiedPublish'


def test_a_pointer_to_the_same_content_that_is_not_canonical_is_refused_not_looped(rebuild, tmp_path):
    origin = tmp_path / 'origin'
    origin.mkdir()
    git(origin, 'init', '-q', '-b', 'main')
    git(origin, 'config', 'user.email', 't@example.com')
    git(origin, 'config', 'user.name', 't')
    api = GitHub(origin, lfs=True)
    data = manifest({'a/x.docx': sha(b'inline')})
    odd = pointer(data).replace(f'size {len(data)}'.encode(), f'size {len(data) + 1}'.encode())
    api.commit({f'{PREFIX}/{MANIFEST}': odd}, 'a pointer with the right oid and a wrong size')
    clone = tmp_path / 'clone'
    git(tmp_path, 'clone', '-q', f'file://{origin}', str(clone))
    with pytest.raises(rebuild.RebuildError, match='create_commit would not replace it') as exc:
        rebuild.publish(api, clone, api.head(), data, 'rebuild')
    assert type(exc.value).__name__ != 'UnverifiedPublish'
    assert api.uploads == []


def test_a_reused_checkout_that_is_not_sparse_on_the_run_folder_is_refused(rebuild, hub_pair):
    with pytest.raises(rebuild.RebuildError, match='sparse'):
        rebuild.checkout_hub(hub_pair.clone, hub_pair.head)


def test_a_reused_sparse_checkout_of_the_run_folder_is_used(rebuild, hub_pair):
    git(hub_pair.clone, 'sparse-checkout', 'set', '--no-cone', f'{PREFIX}/')
    rebuild.checkout_hub(hub_pair.clone, hub_pair.head)
    assert git(hub_pair.clone, 'rev-parse', 'HEAD') == hub_pair.head


# Review round 11 (#78)


def test_ctrl_c_between_the_upload_and_its_check_says_the_hub_may_hold_the_manifest(rebuild, hub_pair):
    data = manifest({'a/x.docx': sha(b'inline')})
    real = hub_pair.api.create_commit

    class Interrupted:
        @property
        def oid(self):
            raise KeyboardInterrupt  # Ctrl-C lands as the commit id is read

    def upload(**kw):
        real(**kw)
        return Interrupted()

    hub_pair.api.create_commit = upload
    with pytest.raises(KeyboardInterrupt) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, data, 'rebuild')
    assert hub_pair.api.head() != hub_pair.head
    assert 'may hold' in ' '.join(getattr(exc.value, '__notes__', ()))


# Review round 12, Codex (#78)


@pytest.mark.parametrize('url', [
    # the commit POST, redirected (307 keeps the method) to the commit URL of a renamed repo
    'https://huggingface.co/api/datasets/arthrod/renamed_neurotic_docx_bench/commit/main',
    # the same commit behind an HF_ENDPOINT with a path, or a mirror
    f'https://mirror.example/hf/api/datasets/{hub.RESULTS_REPO}/commit/main?x=1',
])
def test_a_failure_on_a_request_not_known_to_precede_the_commit_says_the_hub_may_hold_the_manifest(
    rebuild, hub_pair, url
):
    def fails(**kw):
        raise httpx2.ReadTimeout('commit accepted; response lost', request=httpx2.Request('POST', url))

    hub_pair.api.create_commit = fails
    with pytest.raises(rebuild.RebuildError, match='may hold') as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, manifest({'a/x.docx': sha(b'inline')}), 'rebuild')
    assert type(exc.value).__name__ == 'UnverifiedPublish'
    assert 'nothing published' not in str(exc.value)


def test_a_failed_lfs_batch_request_still_says_nothing_was_published(rebuild, hub_pair):
    batch = httpx2.Request('POST', f'https://huggingface.co/datasets/{hub.RESULTS_REPO}.git/info/lfs/objects/batch')

    def fails(**kw):
        raise HfHubHTTPError('503 batch', response=httpx2.Response(503, request=batch))

    hub_pair.api.preupload_lfs_files = fails
    with pytest.raises(rebuild.RebuildError, match='nothing published by this run') as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, manifest({'a/x.docx': sha(b'inline')}), 'rebuild')
    assert type(exc.value).__name__ != 'UnverifiedPublish'


# Review round 13, Codex (#78)


def redirected(status, request, *, from_request):
    return httpx2.Response(status, request=request, history=[httpx2.Response(307, request=from_request)])


@pytest.mark.parametrize('failure', [
    # the commit, 307-redirected to a URL that ends like the preupload's, then timed out
    lambda: httpx2.ReadTimeout('commit accepted; response lost', request=httpx2.Request(
        'POST', f'https://proxy.example/redirect/api/datasets/{hub.RESULTS_REPO}/preupload/main?result=commit')),
    # a timeout carries no answer, so nothing says whether its request was a redirect's target
    lambda: httpx2.ReadTimeout('preupload timed out', request=preupload_request()),
    # an answer after a redirect from the commit: a 4xx there does not mean the commit was refused
    lambda: HfHubHTTPError('403 receipt', response=redirected(
        403, httpx2.Request('GET', 'https://huggingface.co/receipt'), from_request=commit_request())),
    # nor does a 5xx at a URL that ends like the preupload's
    lambda: HfHubHTTPError('503', response=redirected(503, preupload_request(), from_request=commit_request())),
])
def test_a_failure_whose_request_may_follow_a_redirect_says_the_hub_may_hold_the_manifest(rebuild, hub_pair, failure):
    def fails(**kw):
        raise failure()

    hub_pair.api.create_commit = fails
    with pytest.raises(rebuild.RebuildError, match='may hold') as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, manifest({'a/x.docx': sha(b'inline')}), 'rebuild')
    assert type(exc.value).__name__ == 'UnverifiedPublish'
    assert 'nothing published' not in str(exc.value)


def test_a_4xx_answer_to_the_commit_itself_says_what_the_hub_said_and_may_hold(rebuild, hub_pair):
    def fails(**kw):
        raise HfHubHTTPError('412 precondition failed', response=httpx2.Response(412, request=commit_request()))

    hub_pair.api.create_commit = fails
    with pytest.raises(rebuild.RebuildError, match=r'412 precondition failed.*may hold') as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, manifest({'a/x.docx': sha(b'inline')}), 'rebuild')
    assert type(exc.value).__name__ == 'UnverifiedPublish'  # round 15: a refusal does not prove nothing landed


# Review round 13, mcode (#78)


def test_an_upload_that_made_no_commit_says_nothing_was_published_and_why(rebuild, hub_pair, tmp_path):
    """A symlink whose target bytes are the manifest: create_commit sees the content id there and commits nothing."""
    data = manifest({'a/x.docx': sha(b'inline')})
    commit_entry(hub_pair.api.origin, tmp_path, '120000', f'{PREFIX}/{MANIFEST}', data)
    git(hub_pair.clone, 'fetch', '-q', 'origin')
    revision = hub_pair.api.head()
    with pytest.raises(rebuild.RebuildError) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, revision, data, 'rebuild')
    assert hub_pair.api.head() == revision
    assert hub_pair.api.commit_calls == []  # round 18: the preupload's answer already says it
    assert type(exc.value).__name__ != 'UnverifiedPublish'
    assert 'nothing published' in str(exc.value).lower()
    assert 'no commit' in str(exc.value) and '120000' in str(exc.value)
    assert 'rerun' not in str(exc.value)


@pytest.mark.parametrize(('call', 'said'), [('preupload_lfs_files', 'nothing published by this run'), ('create_commit', 'may hold')])
def test_a_storage_failure_says_what_the_call_it_failed_in_sent(rebuild, hub_pair, call, said):
    """Since round 16 a failure is placed by the call it came from: the preupload call sends no commit request."""

    def fails(**kw):
        request = httpx2.Request('PUT', 'https://cas-bridge.example/xet/some-chunk?X-Signature=expired')
        raise HfHubHTTPError('403 storage', response=httpx2.Response(403, request=request))

    setattr(hub_pair.api, call, fails)
    with pytest.raises(rebuild.RebuildError, match=said) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, manifest({'a/x.docx': sha(b'inline')}), 'rebuild')
    assert (type(exc.value).__name__ == 'UnverifiedPublish') == (call == 'create_commit')


@pytest.mark.parametrize('where', ['repo_info', 'leaves'])
def test_ctrl_c_before_the_upload_says_nothing_was_published(rebuild, hub_pair, monkeypatch, where):
    def interrupted(*a, **kw):
        raise KeyboardInterrupt

    if where == 'repo_info':
        hub_pair.api.repo_info = interrupted
    else:
        monkeypatch.setattr(rebuild, 'leaves', interrupted)
    with pytest.raises(KeyboardInterrupt) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, manifest({'a/x.docx': sha(b'inline')}), 'rebuild')
    assert hub_pair.api.uploads == []
    notes = ' '.join(getattr(exc.value, '__notes__', ()))
    assert 'nothing published' in notes and 'may hold' not in notes


def test_ctrl_c_while_the_manifest_is_built_says_nothing_was_published(rebuild, hub_pair, tmp_path, monkeypatch):
    def interrupted(*a, **kw):
        raise KeyboardInterrupt

    monkeypatch.setattr(rebuild, 'build', interrupted)
    with pytest.raises(KeyboardInterrupt) as exc:
        run_main(rebuild, hub_pair, tmp_path, monkeypatch, '--publish')
    assert hub_pair.api.uploads == []
    assert 'nothing published' in ' '.join(getattr(exc.value, '__notes__', ()))


# Review round 14, Codex (#78)


@pytest.mark.parametrize('failure', [
    # a response hook raised before httpx2 attached the redirect history: the commit landed, a 307 sent
    # the client to a preupload-shaped URL that answered 503, and the error looks like the preupload's
    lambda: HfHubHTTPError('503', response=httpx2.Response(503, request=preupload_request())),
    # a transport retried the commit after losing the answer to a first attempt that landed
    lambda: HfHubHTTPError('412 parent moved', response=httpx2.Response(412, request=commit_request())),
])
def test_an_error_that_says_nothing_landed_while_the_branch_moved_says_the_hub_may_hold_the_manifest(
    rebuild, hub_pair, failure
):
    real = hub_pair.api.create_commit

    def lands_then_fails(**kw):
        real(**kw)
        raise failure()

    hub_pair.api.create_commit = lands_then_fails
    with pytest.raises(rebuild.RebuildError, match='may hold') as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, manifest({'a/x.docx': sha(b'inline')}), 'rebuild')
    assert hub_pair.api.head() != hub_pair.head
    assert type(exc.value).__name__ == 'UnverifiedPublish'
    assert 'nothing published' not in str(exc.value)


def test_a_412_after_a_foreign_commit_says_the_hub_may_hold_the_manifest(rebuild, hub_pair):
    """A 412 says the branch moved, and the move may be this upload's own first attempt, retried below the SDK."""
    data = manifest({'a/x.docx': sha(b'inline')})
    hub_pair.api.before_upload = lambda api: api.commit({'elsewhere/new.txt': b'someone else\n'}, 'other')
    with pytest.raises(rebuild.RebuildError, match='may hold') as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, data, 'rebuild')
    assert type(exc.value).__name__ == 'UnverifiedPublish'


def test_a_4xx_to_the_commit_while_the_branch_stays_put_says_what_the_hub_said_and_may_hold(rebuild, hub_pair):
    def fails(**kw):
        raise HfHubHTTPError('403 forbidden', response=httpx2.Response(403, request=commit_request()))

    hub_pair.api.create_commit = fails
    with pytest.raises(rebuild.RebuildError, match=r'403 forbidden.*may hold') as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, manifest({'a/x.docx': sha(b'inline')}), 'rebuild')
    assert type(exc.value).__name__ == 'UnverifiedPublish'  # round 15
    assert 'nothing published' not in str(exc.value)
    assert hub_pair.api.head() == hub_pair.head


def test_ctrl_c_while_main_reads_the_head_says_nothing_was_published(rebuild, hub_pair, tmp_path, monkeypatch):
    def interrupted(*a, **kw):
        raise KeyboardInterrupt

    hub_pair.api.repo_info = interrupted
    with pytest.raises(KeyboardInterrupt) as exc:
        run_main(rebuild, hub_pair, tmp_path, monkeypatch, '--publish')
    assert hub_pair.api.uploads == []
    assert 'nothing published' in ' '.join(getattr(exc.value, '__notes__', ()))


def test_ctrl_c_as_publish_is_called_says_the_hub_may_hold_the_manifest(rebuild, hub_pair, tmp_path, monkeypatch):
    """main() cannot tell this instant from the one after publish() returns: the note must hold for both."""

    def interrupted(*a, **kw):
        raise KeyboardInterrupt

    monkeypatch.setattr(rebuild, 'publish', interrupted)
    with pytest.raises(KeyboardInterrupt) as exc:
        run_main(rebuild, hub_pair, tmp_path, monkeypatch, '--publish')
    notes = ' '.join(getattr(exc.value, '__notes__', ()))
    assert 'may hold' in notes and 'nothing published' not in notes


def test_ctrl_c_after_publish_returned_says_the_hub_holds_the_manifest(rebuild, hub_pair, tmp_path, monkeypatch):
    def press_on_success(*a, **kw):
        if a and str(a[0]).startswith('the hub holds this manifest'):
            raise KeyboardInterrupt
        return print(*a, **kw)

    hub_pair.api.commit({f'{PREFIX}/x.docx': b'A'}, 'a file the manifest does not list yet')
    before = hub_pair.api.head()
    monkeypatch.setattr(rebuild, 'print', press_on_success, raising=False)
    with pytest.raises(KeyboardInterrupt) as exc:
        run_main(rebuild, hub_pair, tmp_path, monkeypatch, '--publish')
    notes = ' '.join(getattr(exc.value, '__notes__', ()))
    assert hub_pair.api.head() != before  # published
    assert 'holds this manifest' in notes and hub_pair.api.head() in notes


# Review round 14, mcode (#78)


@contextlib.contextmanager
def sdk_over(handler, hooks=()):
    """huggingface_hub's shared client answered by ``handler`` (an httpx2.MockTransport) inside the block.

    The SDK's factory and session are swapped, not set: ``set_client_factory`` would close the caller's
    session and leave the default factory behind. Both come back as they were; only the mock's client is
    closed. ``hooks`` are the client's response hooks, as a caller's own client factory may install. Like
    the SDK's ``default_client_factory`` (``utils/_http.py`` 331), the client follows redirects.
    """
    from huggingface_hub.utils import _http

    def client():
        return httpx2.Client(
            transport=httpx2.MockTransport(handler), follow_redirects=True, event_hooks={'response': list(hooks)}
        )

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(_http, '_GLOBAL_CLIENT_FACTORY', client)
        mp.setattr(_http, '_GLOBAL_CLIENT', None)
        try:
            yield
        finally:
            if _http._GLOBAL_CLIENT is not None:
                _http._GLOBAL_CLIENT.close()


def sdk_calls(rebuild, handler):
    """``preupload`` then ``commit_manifest`` through the real HfApi over ``handler``, stopping at a RebuildError.

    One ``(requests sent, error type or None)`` per call made.
    """
    from huggingface_hub import CommitOperationAdd, HfApi

    sent = []

    def recording(request):
        sent.append((request.method, request.url.path))
        return handler(request)

    outcome = []
    with sdk_over(recording):
        api = HfApi(endpoint='https://huggingface.co', token='hf_test_not_a_real_token')
        operation = CommitOperationAdd(path_in_repo=f'{PREFIX}/{MANIFEST}', path_or_fileobj=b'{}\n')
        for step in (lambda: rebuild.preupload(api, operation), lambda: rebuild.commit_manifest(api, operation, 'm', 'a' * 40)):
            mark = len(sent)
            try:
                step()
            except rebuild.RebuildError as exc:
                outcome.append((sent[mark:], type(exc).__name__))
                break
            outcome.append((sent[mark:], None))
    return outcome


def committed(request):
    return httpx2.Response(200, json={
        'commitUrl': f'https://huggingface.co/{hub.REPO_TYPE}s/{hub.RESULTS_REPO}/commit/{"b" * 40}',
        'commitOid': 'b' * 40,
    })


PREUPLOAD = ('POST', f'/api/{hub.REPO_TYPE}s/{hub.RESULTS_REPO}/preupload/main')
COMMIT = ('POST', f'/api/{hub.REPO_TYPE}s/{hub.RESULTS_REPO}/commit/main')


def test_the_sdk_sends_the_requests_each_call_is_placed_by(rebuild):
    """The real HfApi against a mock hub: the preupload call sends the preupload and nothing else; the commit call
    sends the commit, once, and nothing else. A failure in the first is a RebuildError, in the second "may hold".

    Fails if a huggingface_hub upgrade sends a commit from preupload_lfs_files, a second preupload from
    create_commit, or retries the commit.
    """

    def answering(statuses):
        def handler(request):
            kind = 'preupload' if '/preupload/' in request.url.path else 'commit'
            status = statuses.get(kind, 200)
            if status != 200:
                return httpx2.Response(status, json={'error': kind}, request=request)
            if kind == 'preupload':
                files = json.loads(request.content)['files']
                return httpx2.Response(200, json={'files': [
                    {'path': f['path'], 'uploadMode': 'regular', 'shouldIgnore': False, 'oid': None} for f in files
                ]})
            return committed(request)

        return handler

    assert sdk_calls(rebuild, answering({})) == [([PREUPLOAD], None), ([COMMIT], None)]
    # a 5xx on the preupload is retried with backoff, each retry still inside the preupload call
    assert sdk_calls(rebuild, answering({'preupload': 400})) == [([PREUPLOAD], 'RebuildError')]
    assert sdk_calls(rebuild, answering({'commit': 412})) == [([PREUPLOAD], None), ([COMMIT], 'UnverifiedPublish')]


# Review round 15, Codex (#78)


def test_a_4xx_to_the_commit_while_an_earlier_attempt_is_still_on_its_way_never_says_nothing_was_published(
    rebuild, hub_pair
):
    """A proxy lost the answer to the commit it forwarded and answered its own retry with 429; the first
    attempt is still pending when the head is read, and lands after the run reported."""
    data = manifest({'a/x.docx': sha(b'inline')})
    real = hub_pair.api.create_commit
    pending = []

    def forwarded_then_refused(**kw):
        pending.append(kw)
        raise HfHubHTTPError('429 too many requests', response=httpx2.Response(429, request=commit_request()))

    hub_pair.api.create_commit = forwarded_then_refused
    with pytest.raises(rebuild.RebuildError) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, data, 'rebuild')
    real(**pending[0])  # the first attempt lands
    assert hub_pair.api.head() != hub_pair.head
    assert 'nothing published' not in str(exc.value)
    assert type(exc.value).__name__ == 'UnverifiedPublish'


def test_sdk_over_gives_back_the_http_client_it_found(rebuild):
    """A caller's own client factory and open session (a proxy, certificates) survive the SDK test's mock."""
    from huggingface_hub.utils import _http

    def factory():
        return httpx2.Client()

    with pytest.MonkeyPatch.context() as mp:
        session = httpx2.Client()
        mp.setattr(_http, '_GLOBAL_CLIENT_FACTORY', factory)
        mp.setattr(_http, '_GLOBAL_CLIENT', session)
        with sdk_over(lambda request: httpx2.Response(200, json={})):
            assert _http.get_session() is not session
        assert _http._GLOBAL_CLIENT_FACTORY is factory
        assert _http._GLOBAL_CLIENT is session and not session.is_closed
        session.close()


@pytest.mark.parametrize(('where', 'after'), [
    ('removing the clone', 'success'),
    ('removing the clone', 'UnverifiedPublish'),
    ('making the clone folder', None),
])
def test_ctrl_c_around_the_temporary_clone_says_what_the_hub_holds_and_keeps_the_error(
    rebuild, hub_pair, tmp_path, monkeypatch, where, after
):
    """Without --checkout the clone is temporary: a press as it is made or removed still gets a note."""
    hub_pair.api.commit({f'{PREFIX}/x.docx': b'A'}, 'a file the manifest does not list yet')
    git(hub_pair.clone, 'sparse-checkout', 'set', '--no-cone', f'{PREFIX}/')
    monkeypatch.setattr(hub, 'default_api', lambda: hub_pair.api)
    real_checkout, real_mkdtemp, real_rmtree = rebuild.checkout_hub, tempfile.mkdtemp, shutil.rmtree

    def checkout(dest, revision):  # a copy of the test's clone stands in for a fresh one; the rest is real
        shutil.copytree(hub_pair.clone, dest, symlinks=True)
        real_checkout(dest, revision)

    def mkdtemp(*a, prefix='', **kw):
        if where == 'making the clone folder' and prefix.startswith('redlines_0929_full_hub_'):
            raise KeyboardInterrupt
        return real_mkdtemp(prefix=prefix, dir=tmp_path)

    def rmtree(path, *a, **kw):
        raise KeyboardInterrupt

    def unverified(*a, **kw):
        raise rebuild.UnverifiedPublish('create_commit failed; the hub may hold the manifest now; rerun to check it')

    monkeypatch.setattr(rebuild, 'checkout_hub', checkout)
    monkeypatch.setattr(tempfile, 'mkdtemp', mkdtemp)
    if where == 'removing the clone':
        monkeypatch.setattr(shutil, 'rmtree', rmtree)
    if after == 'UnverifiedPublish':
        monkeypatch.setattr(rebuild, 'publish', unverified)
    monkeypatch.setattr(sys, 'argv', ['rebuild_manifest', '--out', str(tmp_path / 'out'), '--publish'])
    with pytest.raises(BaseException) as exc:
        rebuild.main()
    monkeypatch.setattr(shutil, 'rmtree', real_rmtree)
    assert exc.type is KeyboardInterrupt, exc.value
    notes = ' '.join(getattr(exc.value, '__notes__', ()))
    if where == 'making the clone folder':
        assert 'nothing published' in notes
    elif after == 'success':
        assert hub_pair.api.head() != hub_pair.head
        assert 'holds this manifest' in notes and hub_pair.api.head() in notes
    else:  # the error the press interrupted is the warning that decides a rerun: it stays in view
        assert 'may hold' in notes and 'UnverifiedPublish' in notes and 'rerun to check it' in notes


# Review round 15, mcode (#78)


def test_with_lfs_storage_the_preupload_call_sends_the_lfs_batch_and_the_commit_call_only_the_commit(
    rebuild, monkeypatch
):
    """The legacy LFS path, taken when hf_xet is not installed: the preupload call sends the preupload and the LFS
    batch, the commit call only the commit (``create_commit`` skips an LFS file already uploaded).

    With hf_xet installed the storage upload leaves httpx for the Xet client, which this mock cannot see; it
    runs inside the preupload call all the same.
    """
    from huggingface_hub import _commit_api

    monkeypatch.setattr(_commit_api, 'is_xet_available', lambda: False)

    def answering(batch_status):
        def handler(request):
            if '/preupload/' in request.url.path:
                files = json.loads(request.content)['files']
                return httpx2.Response(200, json={'files': [
                    {'path': f['path'], 'uploadMode': 'lfs', 'shouldIgnore': False, 'oid': None} for f in files
                ]})
            if request.url.path.endswith('/info/lfs/objects/batch'):
                if batch_status != 200:
                    return httpx2.Response(batch_status, json={'message': 'batch'}, request=request)
                objects = json.loads(request.content)['objects']  # already stored: nothing to upload
                return httpx2.Response(200, json={'objects': [{'oid': o['oid'], 'size': o['size']} for o in objects]})
            return committed(request)

        return handler

    batch = ('POST', f'/{hub.REPO_TYPE}s/{hub.RESULTS_REPO}.git/info/lfs/objects/batch')
    assert sdk_calls(rebuild, answering(200)) == [([PREUPLOAD, batch], None), ([COMMIT], None)]
    assert sdk_calls(rebuild, answering(400)) == [([PREUPLOAD, batch], 'RebuildError')]


@pytest.mark.parametrize('unreadable', [
    lambda: httpx2.ConnectError('no route to the hub'),
    lambda: HfHubHTTPError('500', response=httpx2.Response(500, request=httpx2.Request('GET', 'https://huggingface.co/api'))),
])
def test_a_failure_before_the_commit_request_says_nothing_published_whatever_the_head_would_say(
    rebuild, hub_pair, unreadable
):
    """Round 15 read the head again to confirm; since round 16 the claim rests on the commit request never sent."""
    tried = []

    def fails(**kw):
        tried.append(1)
        raise HfHubHTTPError('400 preupload', response=httpx2.Response(400, request=preupload_request()))

    real_info = hub_pair.api.repo_info

    def info(*a, **kw):
        if tried:  # a read after the failure
            raise unreadable()
        return real_info(*a, **kw)

    hub_pair.api.preupload_lfs_files = fails
    hub_pair.api.repo_info = info
    with pytest.raises(rebuild.RebuildError, match='nothing published by this run') as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, manifest({'a/x.docx': sha(b'inline')}), 'rebuild')
    assert tried
    assert type(exc.value).__name__ != 'UnverifiedPublish'
    assert hub_pair.api.uploads == []


# Review round 16 (#78)


def http_hub(head, sent, *, preupload_status=200, commit_redirects_to_preupload=False, ignored=False, remote_oid=None):
    """A hub over HTTP for the real HfApi: its head read, the preupload and the commit; ``sent`` lists the requests."""
    commit_path = f'/api/{hub.REPO_TYPE}s/{hub.RESULTS_REPO}/commit/main'

    def handler(request):
        path = request.url.path
        sent.append((request.method, path))
        if '/revision/' in path:
            return httpx2.Response(200, json={'id': hub.RESULTS_REPO, 'sha': head})
        if path == commit_path and commit_redirects_to_preupload:  # a proxy forwards it, then redirects
            return httpx2.Response(307, headers={'Location': path.replace('/commit/', '/preupload/')})
        if path == commit_path:
            return httpx2.Response(200, json={
                'commitUrl': f'https://huggingface.co/{hub.REPO_TYPE}s/{hub.RESULTS_REPO}/commit/{"b" * 40}',
                'commitOid': 'b' * 40,
            })
        if ('POST', commit_path) in sent:  # the commit's redirect, at the preupload URL
            return httpx2.Response(400, json={'error': 'not a preupload request'})
        if preupload_status != 200:
            return httpx2.Response(preupload_status, json={'error': 'preupload'})
        files = json.loads(request.content)['files']
        return httpx2.Response(200, json={'files': [
            {'path': f['path'], 'uploadMode': 'regular', 'shouldIgnore': ignored, 'oid': remote_oid} for f in files
        ]})

    return handler


def test_a_commit_redirected_to_a_failing_preupload_url_through_a_raising_hook_says_the_hub_may_hold_the_manifest(
    rebuild, hub_pair
):
    """Codex, round 16: a proxy forwards the commit POST and answers it with a 307 to the preupload URL, which
    answers 400. A response hook raises there, before httpx2 attaches the redirect history (``_client.py``
    1045), so the error carries an answer to a preupload-shaped request with no history."""
    from huggingface_hub import HfApi

    def raising(response):
        if response.status_code >= 400:
            response.read()
            response.raise_for_status()

    sent = []
    with sdk_over(http_hub(hub_pair.head, sent, commit_redirects_to_preupload=True), hooks=[raising]):
        api = HfApi(endpoint='https://huggingface.co', token='hf_test_not_a_real_token')
        with pytest.raises(rebuild.RebuildError) as exc:
            rebuild.publish(api, hub_pair.clone, hub_pair.head, manifest({'a/x.docx': sha(b'inline')}), 'rebuild')
    assert ('POST', f'/api/{hub.REPO_TYPE}s/{hub.RESULTS_REPO}/commit/main') in sent  # the commit request went out
    assert type(exc.value).__name__ == 'UnverifiedPublish'
    assert 'nothing published' not in str(exc.value)


def test_a_failure_before_the_commit_request_says_nothing_was_published_by_this_run_without_a_second_read(
    rebuild, hub_pair
):
    """mcode, round 16: a head read after the failure is no proof (a commit still on its way does not show). The
    claim rests on the commit request never having been sent, and it is a claim about this run."""
    from huggingface_hub import HfApi

    sent = []
    with sdk_over(http_hub(hub_pair.head, sent, preupload_status=400)):
        api = HfApi(endpoint='https://huggingface.co', token='hf_test_not_a_real_token')
        with pytest.raises(rebuild.RebuildError) as exc:
            rebuild.publish(api, hub_pair.clone, hub_pair.head, manifest({'a/x.docx': sha(b'inline')}), 'rebuild')
    assert type(exc.value).__name__ != 'UnverifiedPublish'
    assert 'nothing published by this run' in str(exc.value)
    assert not any('/commit/' in path for _, path in sent)
    assert [path for _, path in sent if '/revision/' in path] == [  # publish's own read, none after the failure
        f'/api/{hub.REPO_TYPE}s/{hub.RESULTS_REPO}/revision/main'
    ]


def test_a_hub_that_moved_since_it_was_read_says_this_run_published_nothing_and_to_rerun(rebuild, hub_pair):
    """mcode, round 16: the new head may be another run's commit of this very manifest, so the claim is this run's."""
    hub_pair.api.commit({f'{PREFIX}/run/RUN.md': b'someone else'}, 'foreign')
    with pytest.raises(rebuild.RebuildError) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, manifest({'a': sha(b'a')}), 'rebuild')
    assert type(exc.value).__name__ != 'UnverifiedPublish'  # this run sent nothing
    assert 'nothing published by this run' in str(exc.value) and 'rerun' in str(exc.value)
    assert hub_pair.api.uploads == []


@pytest.mark.parametrize('stop', [KeyboardInterrupt, lambda: RuntimeError('git fetch failed')])
def test_a_check_that_stops_after_the_commit_came_back_names_the_commit_the_hub_holds(
    rebuild, hub_pair, monkeypatch, stop
):
    """mcode, round 16: once create_commit returned a commit, the hub holds that commit; "may hold" is
    left for what the check had still to show, that it is this manifest's."""

    def stopped(*a, **kw):
        raise stop()

    monkeypatch.setattr(rebuild, 'verify_upload', stopped)
    with pytest.raises(BaseException) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, manifest({'a/x.docx': sha(b'inline')}), 'rebuild')
    said = ' '.join([str(exc.value), *getattr(exc.value, '__notes__', ())])
    assert hub_pair.api.head() != hub_pair.head
    assert f'the hub holds {hub_pair.api.head()}' in said
    assert exc.type is KeyboardInterrupt or type(exc.value).__name__ == 'UnverifiedPublish'


def test_ctrl_c_during_the_warning_that_the_temporary_clone_stayed_still_says_what_the_hub_holds(
    rebuild, hub_pair, tmp_path, monkeypatch
):
    """Codex, round 16: the warning printed when the removal fails is itself a place a press can land."""
    hub_pair.api.commit({f'{PREFIX}/x.docx': b'A'}, 'a file the manifest does not list yet')
    git(hub_pair.clone, 'sparse-checkout', 'set', '--no-cone', f'{PREFIX}/')
    monkeypatch.setattr(hub, 'default_api', lambda: hub_pair.api)
    real_checkout, real_mkdtemp = rebuild.checkout_hub, tempfile.mkdtemp

    def checkout(dest, revision):
        shutil.copytree(hub_pair.clone, dest, symlinks=True)
        real_checkout(dest, revision)

    def rmtree(path, *a, **kw):
        raise OSError(16, 'Resource busy', str(path))

    def press_on_warning(*a, **kw):
        if a and str(a[0]).startswith('could not remove'):
            raise KeyboardInterrupt
        return print(*a, **kw)

    monkeypatch.setattr(rebuild, 'checkout_hub', checkout)
    monkeypatch.setattr(tempfile, 'mkdtemp', lambda *a, prefix='', **kw: real_mkdtemp(prefix=prefix, dir=tmp_path))
    monkeypatch.setattr(rebuild, 'print', press_on_warning, raising=False)
    monkeypatch.setattr(sys, 'argv', ['rebuild_manifest', '--out', str(tmp_path / 'out'), '--publish'])
    with monkeypatch.context() as mp:
        mp.setattr(shutil, 'rmtree', rmtree)
        with pytest.raises(BaseException) as exc:
            rebuild.main()
    assert exc.type is KeyboardInterrupt, exc.value
    notes = ' '.join(getattr(exc.value, '__notes__', ()))
    assert 'removing the temporary clone' in notes
    assert 'holds this manifest' in notes and hub_pair.api.head() in notes


# Review round 17, mcode (#78)


def test_a_no_op_on_a_moved_head_is_never_called_a_commit_request(rebuild, hub_pair, tmp_path):
    """create_commit's no-op path sends no commit request: it reads the head and returns it. Round 18: the run sees
    the no-op in the preupload's answer and never calls it, so nothing it says rests on a head create_commit read."""
    data = manifest({'a/x.docx': sha(b'inline')})
    hub_pair.api.before_preupload = lambda api: commit_entry(api.origin, tmp_path, '120000', f'{PREFIX}/{MANIFEST}', data)
    with pytest.raises(rebuild.RebuildError) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, data, 'rebuild')
    said = str(exc.value)
    assert hub_pair.api.commit_calls == []
    assert 'create_commit was not called' in said, said
    assert 'commit request returned' not in said and 'create_commit returned' not in said


def test_ctrl_c_inside_create_commit_never_says_the_commit_request_was_under_way(rebuild, hub_pair):
    """create_commit works before its request leaves (its checks, the payload); a press there is "in create_commit"."""

    def pressed(**kw):
        raise KeyboardInterrupt

    hub_pair.api.create_commit = pressed
    with pytest.raises(KeyboardInterrupt) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, manifest({'a/x.docx': sha(b'inline')}), 'rebuild')
    notes = ' '.join(getattr(exc.value, '__notes__', ()))
    # mcode, round 18: the press may land before the call, so the note says "calling", not "in"
    assert 'calling create_commit' in notes and 'may hold' in notes, notes
    assert 'during the commit request' not in notes


def test_a_path_the_hub_ignores_is_refused_before_the_commit_request(rebuild, hub_pair):
    """The SDK leaves an ignored file out of the commit's payload but still sends the commit (``_commit_api.py``
    939). The preupload's answer already says the hub ignores the path, so the run stops there."""
    from huggingface_hub import HfApi

    sent = []
    with sdk_over(http_hub(hub_pair.head, sent, ignored=True)):
        api = HfApi(endpoint='https://huggingface.co', token='hf_test_not_a_real_token')
        with pytest.raises(rebuild.RebuildError) as exc:
            rebuild.publish(api, hub_pair.clone, hub_pair.head, manifest({'a/x.docx': sha(b'inline')}), 'rebuild')
    assert type(exc.value).__name__ != 'UnverifiedPublish', exc.value
    assert 'ignores' in str(exc.value) and 'nothing published by this run' in str(exc.value).lower()
    assert not any('/commit/' in path for _, path in sent)


def test_the_commit_request_of_an_inline_manifest_carries_its_bytes(rebuild):
    """What keeps an inline file's bytes for its commit: the payload line built from the operation (``_commit_api.py``
    945). ``free_memory`` frees only an LFS file's bytes, after their upload."""
    import base64

    from huggingface_hub import CommitOperationAdd, HfApi

    bodies = []

    def handler(request):
        if '/commit/' in request.url.path:
            bodies.append(request.content)
        return http_hub('a' * 40, [])(request)

    with sdk_over(handler):
        api = HfApi(endpoint='https://huggingface.co', token='hf_test_not_a_real_token')
        operation = CommitOperationAdd(path_in_repo=f'{PREFIX}/{MANIFEST}', path_or_fileobj=b'{}\n')
        rebuild.preupload(api, operation)
        rebuild.commit_manifest(api, operation, 'm', 'a' * 40)
    (body,) = bodies
    lines = [json.loads(line) for line in body.decode().splitlines()]
    files = [line['value'] for line in lines if line['key'] == 'file']
    assert files == [{'content': base64.b64encode(b'{}\n').decode(), 'path': f'{PREFIX}/{MANIFEST}', 'encoding': 'base64'}]


def test_the_sdk_takes_its_no_op_from_the_preupload_answer_and_sends_no_commit(rebuild):
    """The premise of the run's own no-op check (``hf_api.py`` 5143-5187): after the preupload, an operation whose
    ``_remote_oid`` is its ``_local_oid`` is dropped, and create_commit reads the head and returns it, with no commit
    request and no parent check."""
    from huggingface_hub import CommitOperationAdd, HfApi

    data = b'{}\n'
    blob_id = hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()
    sent = []
    with sdk_over(http_hub('c' * 40, sent, remote_oid=blob_id)):
        api = HfApi(endpoint='https://huggingface.co', token='hf_test_not_a_real_token')
        operation = CommitOperationAdd(path_in_repo=f'{PREFIX}/{MANIFEST}', path_or_fileobj=data)
        rebuild.preupload(api, operation)
        assert operation._remote_oid == operation._local_oid
        mark = len(sent)
        info = api.create_commit(
            repo_id=hub.RESULTS_REPO, operations=[operation], commit_message='m', repo_type=hub.REPO_TYPE,
            revision='main', parent_commit='a' * 40,
        )
    assert info.oid == 'c' * 40
    assert sent[mark:] == [('GET', f'/api/{hub.REPO_TYPE}s/{hub.RESULTS_REPO}/revision/main')]


def test_a_no_op_the_preupload_answer_shows_never_reaches_create_commit(rebuild, hub_pair):
    """Codex and mcode, round 18: the run makes the SDK's no-op check itself, after the preupload, and never calls
    create_commit for one; what it says then rests on no request create_commit might have sent. This pins the run's
    decision; the SDK's own no-op, which that decision copies, is pinned by the premise guards (regular and LFS)."""
    from huggingface_hub import HfApi

    data = manifest({'a/x.docx': sha(b'inline')})
    blob_id = hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()
    sent, calls = [], []
    with sdk_over(http_hub(hub_pair.head, sent, remote_oid=blob_id)):
        api = HfApi(endpoint='https://huggingface.co', token='hf_test_not_a_real_token')
        real = api.create_commit

        def spy(**kw):
            calls.append(kw)
            return real(**kw)

        api.create_commit = spy
        with pytest.raises(rebuild.RebuildError) as exc:
            rebuild.publish(api, hub_pair.clone, hub_pair.head, data, 'rebuild')
    assert calls == []
    assert type(exc.value).__name__ != 'UnverifiedPublish', exc.value
    said = str(exc.value)
    # Codex, round 19: the tree at the revision holds other content there, so it does not explain the answer
    assert 'Nothing published by this run' in said and 'rerun' in said and 'fix the path' not in said, said
    assert not any('/commit/' in path for _, path in sent)


def test_a_no_op_whose_head_check_fails_still_says_nothing_was_published(rebuild, hub_pair, tmp_path):
    """The head is read again after a no-op the preupload shows, only to choose the advice: whatever that read does,
    create_commit was not called, so nothing was published by this run."""
    data = manifest({'a/x.docx': sha(b'inline')})
    commit_entry(hub_pair.api.origin, tmp_path, '120000', f'{PREFIX}/{MANIFEST}', data)
    git(hub_pair.clone, 'fetch', '-q', 'origin')
    revision = hub_pair.api.head()
    real = hub_pair.api.repo_info

    def second_fails(*args, **kw):
        if hub_pair.api.info_revisions:
            raise OSError('network down')
        return real(*args, **kw)

    hub_pair.api.repo_info = second_fails
    with pytest.raises(rebuild.RebuildError) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, revision, data, 'rebuild')
    said = str(exc.value)
    assert hub_pair.api.commit_calls == []
    assert type(exc.value).__name__ != 'UnverifiedPublish', exc.value
    assert 'Nothing published by this run' in said and 'rerun' in said and 'network down' in said, said


def test_the_sdk_leaves_an_ignored_file_out_of_the_commit_it_still_sends(rebuild):
    """mcode, round 18: the premise of the run's refusal of an ignored path. The preupload's ``shouldIgnore`` drops
    the file from the commit payload (``_commit_api.py`` 939), and the commit is sent all the same."""
    from huggingface_hub import CommitOperationAdd, HfApi

    bodies = []

    def handler(request):
        if '/commit/' in request.url.path:
            bodies.append(request.content)
        return http_hub('a' * 40, [], ignored=True)(request)

    with sdk_over(handler):
        api = HfApi(endpoint='https://huggingface.co', token='hf_test_not_a_real_token')
        operation = CommitOperationAdd(path_in_repo=f'{PREFIX}/{MANIFEST}', path_or_fileobj=b'{}\n')
        rebuild.preupload(api, operation)
        assert operation._should_ignore
        api.create_commit(
            repo_id=hub.RESULTS_REPO, operations=[operation], commit_message='m', repo_type=hub.REPO_TYPE,
            revision='main', parent_commit='a' * 40,
        )
    (body,) = bodies
    assert [json.loads(line)['key'] for line in body.decode().splitlines()] == ['header']


def test_with_xet_storage_the_preupload_call_uploads_and_the_commit_call_sends_only_the_commit(rebuild, monkeypatch):
    """The path a real run takes with hf_xet installed: the storage upload goes through the Xet client inside the
    preupload call (``_commit_api.py`` 396), and create_commit, finding the file uploaded, sends only the commit.
    Codex, round 18: the SDK's own adapter runs (``_commit_api.py`` 552); only the hf_xet session it opens is a fake,
    so the write token's refresh URL, the headers and the sha256 it hands over are the SDK's."""
    from huggingface_hub import _commit_api
    from huggingface_hub.utils import _xet

    uploads, opened = [], []

    class Upload:  # what hf_xet's start_upload_bytes hands back
        def __init__(self, data):
            self.data = data

        def result(self):
            return SimpleNamespace(xet_info=SimpleNamespace(sha256=hashlib.sha256(self.data).hexdigest()))

    class UploadCommit:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def start_upload_bytes(self, data, *, sha256):
            uploads.append((data, sha256))
            return Upload(data)

        def start_upload_file(self, path, *, sha256):
            raise AssertionError('the manifest is uploaded from bytes')

    class Session:
        def new_upload_commit(self, **kw):
            opened.append(kw)
            return UploadCommit()

    monkeypatch.setattr(_commit_api, 'is_xet_available', lambda: True)
    monkeypatch.setattr(_xet, 'get_xet_session', lambda: Session())

    def handler(request):
        if '/preupload/' in request.url.path:
            files = json.loads(request.content)['files']
            return httpx2.Response(200, json={'files': [
                {'path': f['path'], 'uploadMode': 'lfs', 'shouldIgnore': False, 'oid': None} for f in files
            ]})
        return committed(request)

    calls = sdk_calls(rebuild, handler)
    assert calls == [([PREUPLOAD], None), ([COMMIT], None)]
    assert uploads == [(b'{}\n', hashlib.sha256(b'{}\n').hexdigest())]  # once, in the preupload call
    (session,) = opened
    assert session['token_refresh_url'] == f'https://huggingface.co/api/{hub.REPO_TYPE}s/{hub.RESULTS_REPO}/xet-write-token/main'
    assert 'authorization' not in {key.lower() for key in session['custom_headers']}




# Review round 19 (#78)


def test_a_head_that_moved_and_came_back_is_never_told_to_fix_the_path(rebuild, hub_pair):
    """Codex, round 19: the preupload sees a head holding this manifest, and the branch is back at the revision
    when the run reads it again. Equal readings do not show the branch stayed put, and the tree at the revision
    does not explain the no-op, so a rerun, not a fix on the hub, comes next."""
    data = manifest({'a/x.docx': sha(b'inline')})
    real = hub_pair.api.preupload_lfs_files

    def there_and_back(**kw):
        hub_pair.api.commit({f'{PREFIX}/{MANIFEST}': data}, 'rebuild elsewhere')
        real(**kw)
        git(hub_pair.api.origin, 'reset', '-q', '--hard', hub_pair.head)

    hub_pair.api.preupload_lfs_files = there_and_back
    with pytest.raises(rebuild.RebuildError) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, data, 'rebuild')
    said = str(exc.value)
    assert hub_pair.api.head() == hub_pair.head and hub_pair.api.commit_calls == []
    assert 'Nothing published by this run' in said and 'rerun' in said and 'fix the path' not in said, said


def test_the_sdk_sends_the_commit_when_the_preupload_names_other_content(rebuild):
    """Codex, round 19: the no-op premise needs its other half. A content id that is not this manifest's must
    leave the operation in, and the commit request carry the manifest."""
    import base64

    from huggingface_hub import CommitOperationAdd, HfApi

    bodies = []

    def handler(request):
        if '/commit/' in request.url.path:
            bodies.append(request.content)
        return http_hub('a' * 40, [], remote_oid='0' * 40)(request)

    with sdk_over(handler):
        api = HfApi(endpoint='https://huggingface.co', token='hf_test_not_a_real_token')
        operation = CommitOperationAdd(path_in_repo=f'{PREFIX}/{MANIFEST}', path_or_fileobj=b'{}\n')
        rebuild.preupload(api, operation)
        assert operation._remote_oid == '0' * 40 != operation._local_oid
        info = api.create_commit(
            repo_id=hub.RESULTS_REPO, operations=[operation], commit_message='m', repo_type=hub.REPO_TYPE,
            revision='main', parent_commit='a' * 40,
        )
    assert info.oid == 'b' * 40
    (body,) = bodies
    files = [json.loads(line)['value'] for line in body.decode().splitlines() if json.loads(line)['key'] == 'file']
    assert files == [{'content': base64.b64encode(b'{}\n').decode(), 'path': f'{PREFIX}/{MANIFEST}', 'encoding': 'base64'}]


class OpenPipe:
    """The stdout of a ``git cat-file --batch`` that keeps running: like ``BufferedReader`` over a pipe, ``read(n)``
    makes its n-byte buffer first, and a read past what git wrote waits for bytes that never come. Measured on
    CPython 3.14.8 (macOS) over a pipe kept open (mcode, round 21): ``MemoryError`` from 2**62 to 2**63-34;
    ``OverflowError('byte string is too large')`` from 2**63-33, ``PyBytes_FromStringAndSize``'s
    ``size > PY_SSIZE_T_MAX - PyBytesObject_SIZE``; above ``sys.maxsize`` the size is no index at all."""

    def __init__(self, answer: bytes):
        import io

        self.data = io.BytesIO(answer)

    def readline(self):
        return self.data.readline()

    def read(self, n=-1):
        if n > sys.maxsize:
            raise OverflowError("cannot fit 'int' into an index-sized integer")
        if n > sys.maxsize - 33:
            raise OverflowError('byte string is too large')
        if n >= 2**62:
            raise MemoryError
        if n < 0 or n > len(self.data.getbuffer()) - self.data.tell():
            raise AssertionError(f'read({n}) waits on the open pipe for bytes git never writes: the run hangs')
        return self.data.read(n)

    def close(self):
        pass


class CatFile:
    """``git cat-file --batch`` answering every request with ``answer``, its pipe left open as git leaves it."""

    def __init__(self, answer: bytes):
        import io

        self.stdin = io.BytesIO()
        self.stdout = OpenPipe(answer)

    def wait(self):
        return 0


@pytest.mark.parametrize('size', [b'+3', b'3_0', b'x', b'-1'])
def test_a_cat_file_header_whose_size_is_not_digits_refuses(rebuild, monkeypatch, tmp_path, size):
    """Jules, round 19: ``int()`` takes a sign and underscores, and raises ValueError on anything else; the size
    git prints is plain digits, and anything else is refused like any malformed answer. mcode, round 20: over a
    pipe git keeps open, the short-read check never sees ``3_0`` or ``-1``: the read waits, so only this check
    refuses them."""
    oid = 'f' * 40
    monkeypatch.setattr(rebuild.subprocess, 'Popen', lambda *a, **kw: CatFile(f'{oid} blob '.encode() + size + b'\n{}\n\n'))
    with rebuild.blob_reader(tmp_path) as read:
        with pytest.raises(Exception) as exc:
            read(oid)
    assert type(exc.value) is rebuild.RebuildError, repr(exc.value)


def test_the_sdk_takes_its_no_op_from_the_preupload_answer_for_an_lfs_file_too(rebuild, monkeypatch):
    """mcode, round 19: the manifest goes to LFS when the hub's .gitattributes says so, and there the content id the
    preupload answers is the sha256 (``_commit_api.py`` 299). The run's no-op check copies the SDK's for both modes, so
    the premise is pinned for both."""
    from huggingface_hub import CommitOperationAdd, HfApi, _commit_api

    monkeypatch.setattr(_commit_api, 'is_xet_available', lambda: False)
    data = b'{}\n'
    revision = f'/api/{hub.REPO_TYPE}s/{hub.RESULTS_REPO}/revision/main'
    sent = []

    def handler(request):
        sent.append((request.method, request.url.path))
        if request.url.path == revision:
            return httpx2.Response(200, json={'id': hub.RESULTS_REPO, 'sha': 'c' * 40})
        if '/preupload/' in request.url.path:
            files = json.loads(request.content)['files']
            return httpx2.Response(200, json={'files': [
                {'path': f['path'], 'uploadMode': 'lfs', 'shouldIgnore': False, 'oid': hashlib.sha256(data).hexdigest()}
                for f in files
            ]})
        if request.url.path.endswith('/info/lfs/objects/batch'):
            objects = json.loads(request.content)['objects']  # already stored: nothing to upload
            return httpx2.Response(200, json={'objects': [{'oid': o['oid'], 'size': o['size']} for o in objects]})
        return committed(request)

    with sdk_over(handler):
        api = HfApi(endpoint='https://huggingface.co', token='hf_test_not_a_real_token')
        operation = CommitOperationAdd(path_in_repo=f'{PREFIX}/{MANIFEST}', path_or_fileobj=data)
        rebuild.preupload(api, operation)
        assert operation._upload_mode == 'lfs'
        assert operation._remote_oid == operation._local_oid == hashlib.sha256(data).hexdigest()
        mark = len(sent)
        info = api.create_commit(
            repo_id=hub.RESULTS_REPO, operations=[operation], commit_message='m', repo_type=hub.REPO_TYPE,
            revision='main', parent_commit='a' * 40,
        )
    assert info.oid == 'c' * 40
    assert sent[mark:] == [('GET', revision)]


def test_a_path_the_hub_ignores_that_already_holds_the_manifest_is_a_no_op_not_an_ignored_path(rebuild, hub_pair):
    """mcode, round 19: the SDK drops a no-op before its payload builder looks at shouldIgnore (``hf_api.py`` 5143,
    ``_commit_api.py`` 939), so a path both ignored and holding this content id gets no commit request at all, and
    the cause the run names is the no-op, not the .gitignore."""
    from huggingface_hub import HfApi

    data = manifest({'a/x.docx': sha(b'inline')})
    blob_id = hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()
    sent = []
    with sdk_over(http_hub(hub_pair.head, sent, ignored=True, remote_oid=blob_id)):
        api = HfApi(endpoint='https://huggingface.co', token='hf_test_not_a_real_token')
        with pytest.raises(rebuild.RebuildError) as exc:
            rebuild.publish(api, hub_pair.clone, hub_pair.head, data, 'rebuild')
    said = str(exc.value)
    assert type(exc.value).__name__ != 'UnverifiedPublish', exc.value
    assert 'ignores' not in said and 'make no commit' in said and 'Nothing published by this run' in said, said
    assert not any('/commit/' in path for _, path in sent)


# Review round 20 (#78)


def symlink_revision(hub_pair, tmp_path, target: bytes) -> str:
    """The head after a commit turning the manifest path into a symlink whose target bytes are ``target``, fetched."""
    commit_entry(hub_pair.api.origin, tmp_path, '120000', f'{PREFIX}/{MANIFEST}', target)
    git(hub_pair.clone, 'fetch', '-q', 'origin')
    return hub_pair.api.head()


def there_and_back(hub_pair, tmp_path, revision: str, held: bytes) -> None:
    """The preupload sees a head whose manifest path is a regular file holding ``held``; then the branch is back."""
    real = hub_pair.api.preupload_lfs_files

    def preupload(**kw):
        commit_entry(hub_pair.api.origin, tmp_path, '100644', f'{PREFIX}/{MANIFEST}', held)
        real(**kw)
        git(hub_pair.api.origin, 'reset', '-q', '--hard', revision)

    hub_pair.api.preupload_lfs_files = preupload


@pytest.mark.parametrize('lfs', [False, True], ids=['regular', 'lfs'])
def test_a_symlink_holding_the_other_mode_s_content_never_explains_a_no_op(rebuild, hub_pair, tmp_path, lfs):
    """Codex, round 20: the content id the preupload matches depends on its upload mode (``_commit_api.py`` 297): a
    regular file's is the git blob sha1 of its bytes, an LFS file's the sha256 its pointer names. At the revision the
    path is a symlink holding the other mode's spelling of the manifest (the pointer for a regular answer, the bytes
    for an LFS one), so the tree this run read does not explain the answer: a rerun comes next, not a fix on the hub."""
    data = manifest({'a/x.docx': sha(b'inline')})
    revision = symlink_revision(hub_pair, tmp_path, data if lfs else pointer(data))
    hub_pair.api.lfs = lfs
    there_and_back(hub_pair, tmp_path, revision, pointer(data) if lfs else data)
    with pytest.raises(rebuild.RebuildError) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, revision, data, 'rebuild')
    said = str(exc.value)
    assert hub_pair.api.head() == revision and hub_pair.api.commit_calls == []
    assert 'Nothing published by this run' in said and 'rerun' in said and 'fix the path' not in said, said


@pytest.mark.parametrize('lfs', [False, True], ids=['regular', 'lfs'])
def test_a_symlink_holding_the_mode_s_own_content_explains_a_no_op(rebuild, hub_pair, tmp_path, lfs):
    """The control: a symlink holding this mode's spelling of the manifest is what the hub matched, so with the head
    still at the revision the path on the hub is what needs fixing."""
    data = manifest({'a/x.docx': sha(b'inline')})
    revision = symlink_revision(hub_pair, tmp_path, pointer(data) if lfs else data)
    hub_pair.api.lfs = lfs
    with pytest.raises(rebuild.RebuildError) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, revision, data, 'rebuild')
    said = str(exc.value)
    assert hub_pair.api.head() == revision and hub_pair.api.commit_calls == []
    assert 'Nothing published by this run' in said and 'fix the path' in said, said


def test_the_sdk_sends_no_commit_for_an_ignored_path_that_already_holds_the_manifest(rebuild):
    """Codex, round 20: the premise of the run's order, no-op before shouldIgnore. The SDK drops a no-op before its
    payload builder looks at shouldIgnore (``hf_api.py`` 5143, ``_commit_api.py`` 939): it reads the head and returns
    it, sending no commit request, not a header-only one."""
    from huggingface_hub import CommitOperationAdd, HfApi

    data = b'{}\n'
    blob_id = hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()
    sent = []
    with sdk_over(http_hub('c' * 40, sent, ignored=True, remote_oid=blob_id)):
        api = HfApi(endpoint='https://huggingface.co', token='hf_test_not_a_real_token')
        operation = CommitOperationAdd(path_in_repo=f'{PREFIX}/{MANIFEST}', path_or_fileobj=data)
        rebuild.preupload(api, operation)
        assert operation._should_ignore and operation._remote_oid == operation._local_oid
        mark = len(sent)
        info = api.create_commit(
            repo_id=hub.RESULTS_REPO, operations=[operation], commit_message='m', repo_type=hub.REPO_TYPE,
            revision='main', parent_commit='a' * 40,
        )
    assert info.oid == 'c' * 40
    assert sent[mark:] == [('GET', f'/api/{hub.REPO_TYPE}s/{hub.RESULTS_REPO}/revision/main')]


def test_the_sdk_sends_the_lfs_commit_when_the_preupload_names_other_lfs_content(rebuild, monkeypatch):
    """Codex, round 20: the LFS half of the differing-id guard. An LFS content id that is not this manifest's sha256
    leaves the operation in, and the commit request carries it as an ``lfsFile`` (``_commit_api.py`` 957)."""
    from huggingface_hub import CommitOperationAdd, HfApi, _commit_api

    monkeypatch.setattr(_commit_api, 'is_xet_available', lambda: False)
    data = b'{}\n'
    bodies = []

    def handler(request):
        if '/preupload/' in request.url.path:
            files = json.loads(request.content)['files']
            return httpx2.Response(200, json={'files': [
                {'path': f['path'], 'uploadMode': 'lfs', 'shouldIgnore': False, 'oid': sha(b'other content')}
                for f in files
            ]})
        if request.url.path.endswith('/info/lfs/objects/batch'):
            objects = json.loads(request.content)['objects']  # already stored: nothing to upload
            return httpx2.Response(200, json={'objects': [{'oid': o['oid'], 'size': o['size']} for o in objects]})
        assert request.url.path.endswith('/commit/main'), request.url.path
        bodies.append(request.content)
        return committed(request)

    with sdk_over(handler):
        api = HfApi(endpoint='https://huggingface.co', token='hf_test_not_a_real_token')
        operation = CommitOperationAdd(path_in_repo=f'{PREFIX}/{MANIFEST}', path_or_fileobj=data)
        rebuild.preupload(api, operation)
        assert operation._upload_mode == 'lfs'
        assert operation._remote_oid == sha(b'other content') != operation._local_oid == sha(data)
        info = api.create_commit(
            repo_id=hub.RESULTS_REPO, operations=[operation], commit_message='m', repo_type=hub.REPO_TYPE,
            revision='main', parent_commit='a' * 40,
        )
    assert info.oid == 'b' * 40
    (body,) = bodies
    lines = [json.loads(line) for line in body.decode().splitlines()]
    assert [x['value'] for x in lines if x['key'] == 'lfsFile'] == [
        {'path': f'{PREFIX}/{MANIFEST}', 'algo': 'sha256', 'oid': sha(data), 'size': len(data)}
    ]


@pytest.mark.parametrize('size', [2**62, 2**63 - 33, 2**64 - 1], ids=['MemoryError', 'too-large', 'no-index'])
def test_a_cat_file_size_too_large_to_read_refuses(rebuild, monkeypatch, tmp_path, size):
    """mcode, round 20: a size of ASCII digits passes the header check, and a read of it fails making its buffer
    (``MemoryError``, ``OverflowError``), which reached the caller uncaught instead of the refusal of a malformed
    answer."""
    oid = 'f' * 40
    monkeypatch.setattr(rebuild.subprocess, 'Popen', lambda *a, **kw: CatFile(f'{oid} blob {size}\n{{}}\n\n'.encode()))
    with rebuild.blob_reader(tmp_path) as read:
        with pytest.raises(Exception) as exc:
            read(oid)
    assert type(exc.value) is rebuild.RebuildError, repr(exc.value)
    assert str(size) in str(exc.value), exc.value


def test_a_folder_at_the_manifest_path_refuses_before_the_preupload(rebuild, hub_pair):
    """mcode, round 20: ``ls-tree -r`` lists no folder, so a folder at the manifest path read as "no file": the run
    sent the preupload and then a commit no hub can make, or blamed a moved head. It is named, before anything is
    sent."""
    data = manifest({'a/x.docx': sha(b'inline')})
    git(hub_pair.api.origin, 'rm', '-q', f'{PREFIX}/{MANIFEST}')
    hub_pair.api.commit({f'{PREFIX}/{MANIFEST}/inner.txt': b'x'}, 'a folder at the manifest path')
    git(hub_pair.clone, 'fetch', '-q', 'origin')
    revision = hub_pair.api.head()
    with pytest.raises(rebuild.RebuildError) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, revision, data, 'rebuild')
    said = str(exc.value)
    assert type(exc.value).__name__ != 'UnverifiedPublish', exc.value
    assert hub_pair.api.preuploads == [] and hub_pair.api.commit_calls == []
    assert 'folder' in said and 'Nothing published by this run' in said, said
    # mcode, round 21: git can replace the folder with the manifest, dropping the files under it; the run declines
    # to, and names what such a commit would drop
    assert 'inner.txt' in said and 'would drop' in said and 'no commit can' not in said, said


@pytest.mark.parametrize('read', [('cat-file', 'blob'), ('ls-tree',)], ids=['blob', 'tree'])
def test_the_symlink_s_bytes_are_read_before_the_preupload(rebuild, hub_pair, tmp_path, monkeypatch, read):
    """mcode, round 20: the bytes of a symlink at the manifest path were read only after the preupload, to explain
    a no-op, so a git failure there came after a request was sent. They are read with the tree, before any.
    mcode, round 21: a failure of either read says that nothing was published, as every other refusal does.
    mcode, round 22: it said "nothing was sent yet", but the head was read from the hub, and the clone fetches a
    blob it lacks; what was not sent is a commit request."""
    data = manifest({'a/x.docx': sha(b'inline')})
    revision = symlink_revision(hub_pair, tmp_path, data)
    real = rebuild.git

    def failing(checkout, *args):
        if args[:len(read)] == read:
            raise rebuild.RebuildError(f'git {" ".join(read)} failed (128): fatal: simulated')
        return real(checkout, *args)

    monkeypatch.setattr(rebuild, 'git', failing)
    with pytest.raises(rebuild.RebuildError) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, revision, data, 'rebuild')
    said = str(exc.value)
    assert 'simulated' in said and 'Nothing published by this run' in said, said
    assert 'nothing was sent' not in said and 'no commit request was sent' in said, said
    assert hub_pair.api.preuploads == [] and hub_pair.api.commit_calls == []


def test_the_folder_refusal_names_what_the_hub_holds_byte_for_byte(rebuild, hub_pair):
    """mcode, round 22: the folder refusal decoded the names under the path with errors='replace', so two invalid
    byte strings read the same and neither is the name the hub holds, and it counted a submodule as a file. Names
    are spelled with backslashreplace, as verify_upload spells them, and files and submodules are counted apart."""
    data = manifest({'a/x.docx': sha(b'inline')})
    origin = hub_pair.api.origin
    git(origin, 'rm', '-q', f'{PREFIX}/{MANIFEST}')
    hub_pair.api.commit({f'{PREFIX}/{MANIFEST}/inner.txt': b'x'}, 'a folder at the manifest path')
    blob = subprocess.run(
        ['git', 'hash-object', '-w', '--stdin'], input=b'y', cwd=origin, capture_output=True, check=True
    ).stdout.strip()
    odd = f'{PREFIX}/{MANIFEST}/'.encode() + b'\xff\xfebad.txt'  # no disk name: git takes any bytes
    subprocess.run([b'git', b'update-index', b'--add', b'--cacheinfo', b'100644,' + blob + b',' + odd], cwd=origin, check=True)
    sub = f'160000,{hub_pair.api.head()},{PREFIX}/{MANIFEST}/sub'
    subprocess.run(['git', 'update-index', '--add', '--cacheinfo', sub], cwd=origin, check=True)
    git(origin, 'commit', '-q', '-m', 'a file without a UTF-8 name and a submodule under the folder')
    git(hub_pair.clone, 'fetch', '-q', 'origin')
    revision = hub_pair.api.head()
    with pytest.raises(rebuild.RebuildError) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, revision, data, 'rebuild')
    said = str(exc.value)
    assert hub_pair.api.preuploads == [] and hub_pair.api.commit_calls == []
    assert '\\xff\\xfebad.txt' in said and '\ufffd' not in said, said
    assert '2 file(s) and 1 submodule(s)' in said, said


def add_raw(origin: Path, path: bytes, data: bytes) -> None:
    """Stage a blob under a path given as bytes: git takes any bytes, a disk may not (APFS refuses non-UTF-8)."""
    blob = subprocess.run(
        ['git', 'hash-object', '-w', '--stdin'], input=data, cwd=origin, capture_output=True, check=True
    ).stdout.strip()
    subprocess.run([b'git', b'update-index', b'--add', b'--cacheinfo', b'100644,' + blob + b',' + path], cwd=origin, check=True)


# an invalid byte and a literal backslash that backslashreplace spells the same: \xffbad.txt
TWINS = (b'\xffbad.txt', b'\\xffbad.txt')


def test_the_folder_refusal_spells_an_invalid_byte_and_a_backslash_apart(rebuild, hub_pair):
    """mcode, round 23: backslashreplace spells the byte 0xff and the four characters backslash, x, f, f the same,
    so the refusal named two different files under the path with one name. Backslashes are doubled first."""
    data = manifest({'a/x.docx': sha(b'inline')})
    origin = hub_pair.api.origin
    git(origin, 'rm', '-q', f'{PREFIX}/{MANIFEST}')
    for name in TWINS:
        add_raw(origin, f'{PREFIX}/{MANIFEST}/'.encode() + name, b'y')
    git(origin, 'commit', '-q', '-m', 'two names under the folder that backslashreplace spells the same')
    git(hub_pair.clone, 'fetch', '-q', 'origin')
    revision = hub_pair.api.head()
    with pytest.raises(rebuild.RebuildError) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, revision, data, 'rebuild')
    said = str(exc.value)
    assert f'{MANIFEST}/\\xffbad.txt' in said and f'{MANIFEST}/\\\\xffbad.txt' in said, said


def test_verify_upload_spells_an_invalid_byte_and_a_backslash_apart(rebuild, hub_pair):
    """mcode, round 23: verify_upload's list of the paths a commit changes has the same spelling, so a commit that
    changed both names listed one name twice."""
    data = manifest({'a/x.docx': sha(b'inline')})
    origin = hub_pair.api.origin
    revision = hub_pair.api.head()
    before = rebuild.leaves(hub_pair.clone, revision)
    (origin / PREFIX / MANIFEST).write_bytes(data)
    git(origin, 'add', '--', f'{PREFIX}/{MANIFEST}')
    for name in TWINS:
        add_raw(origin, f'{PREFIX}/'.encode() + name, b'y')
    git(origin, 'commit', '-q', '-m', 'the manifest and two more names')
    git(hub_pair.clone, 'fetch', '-q', 'origin')
    commit = hub_pair.api.head()
    with pytest.raises(rebuild.RebuildError) as exc:
        rebuild.verify_upload(hub_pair.clone, revision, commit, before, data)
    said = str(exc.value)
    assert 'not only' in said, said
    assert f"'{PREFIX}/\\\\xffbad.txt'" in said and f"'{PREFIX}/\\\\\\\\xffbad.txt'" in said, said


def test_verify_upload_refuses_a_commit_that_removed_the_manifest_with_its_own_sentence(rebuild, hub_pair):
    """mcode, round 24: a commit on the revision that removed the manifest path changes only that path, and
    verify_upload raised KeyError(b'outputs/.../MANIFEST.sha256.json'), which publish() reported as a raw bytes key.
    It says the commit removes the manifest and is not this upload."""
    data = manifest({'a/x.docx': sha(b'inline')})
    origin = hub_pair.api.origin
    revision = hub_pair.api.head()
    before = rebuild.leaves(hub_pair.clone, revision)
    git(origin, 'rm', '-q', '--', f'{PREFIX}/{MANIFEST}')
    git(origin, 'commit', '-q', '-m', 'the manifest removed')
    commit = hub_pair.api.head()
    with pytest.raises(Exception) as exc:
        rebuild.verify_upload(hub_pair.clone, revision, commit, before, data)
    assert isinstance(exc.value, rebuild.RebuildError), repr(exc.value)
    said = str(exc.value)
    assert f'{commit} removes {PREFIX}/{MANIFEST}' in said and 'it is not this upload' in said, said


def test_publish_on_a_given_revision_that_is_not_the_head_refuses_before_the_build_without_saying_the_hub_moved(
    rebuild, hub_pair, tmp_path, monkeypatch
):
    """mcode, round 24: --publish --revision <a commit that is not main's head> built the manifest, then refused with
    "the hub moved to <head> since <revision> was read". Nothing moved: the revision was given, not read, and the
    manifest is committed only on the head. The run says so before it builds anything."""
    older = hub_pair.head
    hub_pair.api.commit({f'{PREFIX}/run/RUN.md': b'later'}, 'later')
    head = hub_pair.api.head()
    git(hub_pair.clone, 'fetch', '-q', 'origin')
    built = []
    real_build = rebuild.build
    monkeypatch.setattr(rebuild, 'build', lambda *a, **kw: built.append(1) or real_build(*a, **kw))
    with pytest.raises(rebuild.RebuildError) as exc:
        run_main(rebuild, hub_pair, tmp_path, monkeypatch, '--publish', '--revision', older)
    said = str(exc.value)
    assert 'moved' not in said, said
    assert f'--revision {older} is not that id' in said and f'its full commit id ({head})' in said, said
    assert 'nothing published by this run' in said, said
    assert built == [] and hub_pair.api.uploads == []


def test_publish_on_a_short_id_of_the_head_names_the_head_and_asks_for_its_full_id(
    rebuild, hub_pair, tmp_path, monkeypatch
):
    """Round 24, found with mcode's fix: "--revision <the head's first 12 hex> is not the head of main (<head>)" read
    as false. The refusal compares commit ids as given, so it says what it compared and how to give the head."""
    head = hub_pair.head
    with pytest.raises(rebuild.RebuildError) as exc:
        run_main(rebuild, hub_pair, tmp_path, monkeypatch, '--publish', '--revision', head[:12])
    said = str(exc.value)
    assert f'--revision {head[:12]} is not that id' in said and f'its full commit id ({head})' in said, said
    assert hub_pair.api.uploads == []


def test_publish_with_revision_main_publishes_on_the_head(rebuild, hub_pair, tmp_path, monkeypatch):
    """Round 24, found with mcode's fix: --revision main names the head, and was refused as "not the head of main"
    (before that, read from the clone's own main and refused as "the hub moved"). It is the head, read from the hub."""
    hub_pair.api.commit({f'{PREFIX}/x.docx': b'A'}, 'a file the manifest does not list yet')
    head = hub_pair.api.head()
    try:
        run_main(rebuild, hub_pair, tmp_path, monkeypatch, '--publish', '--revision', 'main')
    except rebuild.RebuildError as exc:
        raise AssertionError(f'refused: {exc}') from exc
    assert [u['parent_commit'] for u in hub_pair.api.uploads] == [head]
    assert hub_pair.api.head() != head


EMPTY_TREE = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'  # git's empty tree, which an index cannot hold


def tree_with(origin: Path, tree: str, path: bytes, entry: bytes | None) -> str:
    """``tree`` with ``path`` set to ``entry`` (b'<mode> <type> <oid>'), or taken out when None; the new tree's id.
    mktree makes what a commit through the index cannot: an empty folder."""
    head, _, rest = path.partition(b'/')
    listing = subprocess.run(['git', 'ls-tree', '-z', tree], cwd=origin, capture_output=True, check=True).stdout
    entries = {}
    for line in listing.split(b'\0'):
        if line:
            meta, name = line.split(b'\t', 1)
            entries[name] = meta
    if rest:
        below = entries[head].split()[2].decode() if head in entries else EMPTY_TREE
        sub = tree_with(origin, below, rest, entry)
        if sub == EMPTY_TREE and entry is None:  # what taking an entry out leaves empty goes too, as in git
            del entries[head]
        else:
            entries[head] = b'040000 tree ' + sub.encode()
    elif entry is None:
        del entries[head]
    else:
        entries[head] = entry
    data = b''.join(meta + b'\t' + name + b'\0' for name, meta in entries.items())
    made = subprocess.run(['git', 'mktree', '-z'], input=data, cwd=origin, capture_output=True, check=True)
    return made.stdout.strip().decode()


def commit_on(origin: Path, tree: str, parent: str) -> str:
    commit = git(origin, 'commit-tree', tree, '-p', parent, '-m', 'made with mktree')
    git(origin, 'update-ref', 'refs/heads/main', commit)
    return commit


def manifest_blob(origin: Path, data: bytes) -> bytes:
    made = subprocess.run(['git', 'hash-object', '-w', '--stdin'], input=data, cwd=origin, capture_output=True, check=True)
    return b'100644 blob ' + made.stdout.strip()


@pytest.mark.parametrize('folder', [f'{PREFIX}/run/empty', 'elsewhere/empty'])
def test_verify_upload_refuses_a_commit_that_also_adds_an_empty_folder(rebuild, hub_pair, folder):
    """Codex, round 25: ls-tree -r lists blobs and gitlinks, never a tree, so a commit that wrote the manifest and
    also added an empty folder changed "only" the manifest, and verify_upload took it for this upload."""
    data = manifest({'a/x.docx': sha(b'inline')})
    origin = hub_pair.api.origin
    revision = hub_pair.api.head()
    before = rebuild.leaves(hub_pair.clone, revision)
    tree = tree_with(origin, git(origin, 'rev-parse', f'{revision}^{{tree}}'), f'{PREFIX}/{MANIFEST}'.encode(),
                     manifest_blob(origin, data))
    tree = tree_with(origin, tree, folder.encode(), f'040000 tree {EMPTY_TREE}'.encode())
    commit = commit_on(origin, tree, revision)
    with pytest.raises(Exception) as exc:
        rebuild.verify_upload(hub_pair.clone, revision, commit, before, data)
    assert isinstance(exc.value, rebuild.RebuildError), repr(exc.value)
    said = str(exc.value)
    assert 'not only' in said and folder in said, said


def test_verify_upload_calls_a_manifest_replaced_by_an_empty_folder_a_folder(rebuild, hub_pair):
    """Codex, round 25: a commit that replaced the manifest with an empty folder got round 24's sentence for a
    commit that removes it, since ls-tree -r does not list the folder."""
    data = manifest({'a/x.docx': sha(b'inline')})
    origin = hub_pair.api.origin
    revision = hub_pair.api.head()
    before = rebuild.leaves(hub_pair.clone, revision)
    tree = tree_with(origin, git(origin, 'rev-parse', f'{revision}^{{tree}}'), f'{PREFIX}/{MANIFEST}'.encode(),
                     f'040000 tree {EMPTY_TREE}'.encode())
    commit = commit_on(origin, tree, revision)
    with pytest.raises(rebuild.RebuildError) as exc:
        rebuild.verify_upload(hub_pair.clone, revision, commit, before, data)
    said = str(exc.value)
    assert f'the manifest at {commit} is a folder' in said and 'removes' not in said, said


def test_publish_refuses_a_manifest_path_that_is_an_empty_folder(rebuild, hub_pair):
    """Round 25, the same omission before the upload: an empty folder at the manifest path holds no file, so
    publish() saw no manifest there and sent the preupload and the commit request. It refuses, as for a folder
    holding files, before anything is sent."""
    data = manifest({'a/x.docx': sha(b'inline')})
    origin = hub_pair.api.origin
    tree = tree_with(origin, git(origin, 'rev-parse', f'{hub_pair.head}^{{tree}}'), f'{PREFIX}/{MANIFEST}'.encode(),
                     f'040000 tree {EMPTY_TREE}'.encode())
    revision = commit_on(origin, tree, hub_pair.head)
    git(hub_pair.clone, 'fetch', '-q', 'origin')
    with pytest.raises(Exception) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, revision, data, 'rebuild')
    assert isinstance(exc.value, rebuild.RebuildError), repr(exc.value)
    assert type(exc.value).__name__ != 'UnverifiedPublish', repr(exc.value)
    said = str(exc.value)
    assert hub_pair.api.preuploads == [] and hub_pair.api.commit_calls == [], said
    assert f'{PREFIX}/{MANIFEST} at {revision} is an empty folder' in said and 'Nothing published' in said, said


def test_verify_upload_takes_a_commit_that_makes_the_manifest_s_own_folder(rebuild, hub_pair):
    """Round 25's folder check leaves out the manifest's own parents: an upload onto a hub without the run folder
    makes it, and is still this upload."""
    data = manifest({'a/x.docx': sha(b'inline')})
    origin = hub_pair.api.origin
    hub_pair.api.commit({f'{PREFIX}/other.txt': b'keeps the prefix folder'}, 'another file')
    gone = tree_with(origin, git(origin, 'rev-parse', 'HEAD^{tree}'), f'{PREFIX}/{MANIFEST}'.encode(), None)
    revision = commit_on(origin, gone, hub_pair.api.head())
    git(hub_pair.clone, 'fetch', '-q', 'origin')
    assert f'{PREFIX}/run'.encode() not in rebuild.folders(hub_pair.clone, revision)
    before = rebuild.leaves(hub_pair.clone, revision)
    made = tree_with(origin, gone, f'{PREFIX}/{MANIFEST}'.encode(), manifest_blob(origin, data))
    commit = commit_on(origin, made, revision)
    assert rebuild.verify_upload(hub_pair.clone, revision, commit, before, data) == commit


def test_publish_on_a_tag_naming_the_head_is_refused_without_saying_it_is_not_the_head(
    rebuild, hub_pair, tmp_path, monkeypatch
):
    """mcode, round 25: --revision v1.0, a tag on the head, was refused with "--revision v1.0 is not <head>, the
    head of main", which git contradicts. The refusal compares commit ids as given, and says only that."""
    head = hub_pair.head
    git(hub_pair.api.origin, 'tag', 'v1.0', head)
    with pytest.raises(rebuild.RebuildError) as exc:
        run_main(rebuild, hub_pair, tmp_path, monkeypatch, '--publish', '--revision', 'v1.0')
    said = str(exc.value)
    assert f'is not {head}' not in said, said
    assert '--revision v1.0 is not that id' in said and 'nothing published by this run' in said, said
    assert hub_pair.api.uploads == []


def test_publish_on_the_head_s_id_in_capitals_publishes_on_the_head(rebuild, hub_pair, tmp_path, monkeypatch):
    """mcode, round 25: git takes a commit id in capitals as the same id, and the refusal said it was not the head.
    A full id in any case is that id."""
    hub_pair.api.commit({f'{PREFIX}/x.docx': b'A'}, 'a file the manifest does not list yet')
    head = hub_pair.api.head()
    try:
        run_main(rebuild, hub_pair, tmp_path, monkeypatch, '--publish', '--revision', head.upper())
    except rebuild.RebuildError as exc:
        raise AssertionError(f'refused: {exc}') from exc
    assert [u['parent_commit'] for u in hub_pair.api.uploads] == [head]


def test_publish_on_a_gitlink_at_the_manifest_path_does_not_call_it_a_folder(rebuild, hub_pair):
    """Codex, round 26: ls-tree -r -d lists gitlinks beside trees, and folders() kept them, so publish() called a
    gitlink at the manifest path "an empty folder" and asked for it to be removed. folders() lists trees only; a
    gitlink there is replaced by the manifest, as a symlink there is (main()'s build refuses either first)."""
    data = manifest({'a/x.docx': sha(b'inline')})
    origin = hub_pair.api.origin
    key = f'{PREFIX}/{MANIFEST}'.encode()
    tree = tree_with(origin, git(origin, 'rev-parse', f'{hub_pair.head}^{{tree}}'), key,
                     f'160000 commit {hub_pair.head}'.encode())
    revision = commit_on(origin, tree, hub_pair.head)
    git(hub_pair.clone, 'fetch', '-q', 'origin')
    assert key not in rebuild.folders(hub_pair.clone, revision)
    try:
        commit = rebuild.publish(hub_pair.api, hub_pair.clone, revision, data, 'rebuild')
    except rebuild.RebuildError as exc:
        raise AssertionError(f'a gitlink is not a folder: {exc}') from None
    assert rebuild.leaves(hub_pair.clone, commit)[key][:2] == (b'100644', b'blob')
    assert rebuild.git(hub_pair.clone, 'cat-file', 'blob', f'{commit}:{PREFIX}/{MANIFEST}') == data


def test_publish_refusal_names_every_spelling_of_the_head_and_the_revision_as_typed(
    rebuild, hub_pair, tmp_path, monkeypatch
):
    """mcode, round 26: the refusal named the head's spellings as "no --revision or by its full commit id", leaving
    out --revision main, which publishes on the head too, and it printed a full id given in capitals lowercased, a
    spelling the operator never typed."""
    older = hub_pair.head
    hub_pair.api.commit({f'{PREFIX}/x.docx': b'A'}, 'the head moves on')
    with pytest.raises(rebuild.RebuildError) as exc:
        run_main(rebuild, hub_pair, tmp_path, monkeypatch, '--publish', '--revision', older.upper())
    said = str(exc.value)
    assert f'--revision {older.upper()} is not that id' in said, said
    assert f'--revision {rebuild.BRANCH}' in said and f'its full commit id ({hub_pair.api.head()})' in said, said
    assert hub_pair.api.uploads == []
