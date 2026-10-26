"""Rebuild the redlines_0929_full run manifest from the hub's own git tree (issue #76)."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import random
import re
import subprocess
import sys
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
    """The hub's commit API over a real git repository standing in for the dataset."""

    def __init__(self, origin: Path, before_upload=None, lfs: bool = False):
        self.origin = origin
        self.before_upload = before_upload
        self.lfs = lfs  # the hub's preupload picked LFS storage for the upload
        self.uploads: list[dict] = []
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

    def upload_file(self, *, path_or_fileobj, path_in_repo, repo_id, repo_type, commit_message, parent_commit=None, revision=None):
        assert revision == 'main'
        self.uploads.append({
            'path_in_repo': path_in_repo,
            'parent_commit': parent_commit,
            'commit_message': commit_message,
            'revision': revision,
        })
        if self.before_upload:
            self.before_upload(self)
        stored = pointer(path_or_fileobj) if self.lfs else path_or_fileobj
        if self.lfs:
            self.lfs_contents[sha(path_or_fileobj)] = path_or_fileobj
        current = subprocess.run(['git', 'cat-file', 'blob', f'HEAD:{path_in_repo}'], cwd=self.origin, capture_output=True)
        if current.returncode == 0 and current.stdout == stored:
            # huggingface_hub compares content oids only (not modes) and returns the branch head
            # without a commit or a parent check
            return SimpleNamespace(oid=self.head())
        if parent_commit is not None and parent_commit != self.head():
            request = httpx2.Request('POST', 'https://huggingface.co/api/commit')
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


def test_publish_refuses_a_no_op_that_returns_someone_elses_commit(rebuild, hub_pair):
    """Another writer commits the same manifest plus a file, under the same title, just before the upload."""
    data = manifest({'a/x.docx': sha(b'inline')})

    def foreign(api):
        api.commit({f'{PREFIX}/{MANIFEST}': data, f'{PREFIX}/new/unlisted.docx': b'not in the manifest'}, 'rebuild')

    hub_pair.api.before_upload = foreign
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
        return b''

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

    hub_pair.api.before_upload = foreign
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
    """A foreign commit turns the manifest into a symlink whose target bytes are the manifest; the upload is a no-op."""
    data = manifest({'a/x.docx': sha(b'inline')})
    hub_pair.api.before_upload = lambda api: commit_entry(api.origin, tmp_path, '120000', f'{PREFIX}/{MANIFEST}', data)
    with pytest.raises(rebuild.RebuildError, match='120000'):
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, data, 'rebuild')


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
    real = hub_pair.api.upload_file

    def lost(**kw):
        real(**kw)  # the hub commits; its answer never arrives
        raise httpx2.ReadTimeout('the response never came')

    hub_pair.api.upload_file = lost
    with pytest.raises(rebuild.RebuildError) as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, data, 'rebuild')
    assert type(exc.value).__name__ == 'UnverifiedPublish'
    assert hub_pair.api.head() != hub_pair.head
    assert 'may hold' in str(exc.value)
    assert 'the response never came' in str(exc.value)


def test_an_upload_the_hub_refused_is_reported_as_refused(rebuild, hub_pair):
    """A 4xx answer (here 412: the branch moved) means the hub committed nothing."""
    data = manifest({'a/x.docx': sha(b'inline')})
    hub_pair.api.before_upload = lambda api: api.commit({'elsewhere/new.txt': b'someone else\n'}, 'other')
    with pytest.raises(rebuild.RebuildError, match=r'refused.*412.*nothing published') as exc:
        rebuild.publish(hub_pair.api, hub_pair.clone, hub_pair.head, data, 'rebuild')
    assert type(exc.value).__name__ != 'UnverifiedPublish'
