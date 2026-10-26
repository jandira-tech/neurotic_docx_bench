"""Rebuild the redlines_0929_full run manifest from the hub's own git tree (issue #76)."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
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
    built, report = rebuild.rebuild(tree_of(rebuild, files), history, files.__getitem__)
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
    ],
    ids=['no-sha256-prefix', 'two-oids', 'trailing-text', 'crlf'],
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

    def __init__(self, origin: Path, before_upload=None):
        self.origin = origin
        self.before_upload = before_upload
        self.uploads: list[dict] = []

    def head(self) -> str:
        return git(self.origin, 'rev-parse', 'HEAD')

    def commit(self, files: dict[str, bytes], message: str) -> None:
        for rel, data in files.items():
            path = self.origin / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        git(self.origin, 'add', '-A')
        git(self.origin, 'commit', '-q', '-m', message)

    def repo_info(self, repo_id, *, repo_type, revision=None):
        return SimpleNamespace(sha=self.head())

    def upload_file(self, *, path_or_fileobj, path_in_repo, repo_id, repo_type, commit_message, parent_commit=None):
        self.uploads.append({
            'path_in_repo': path_in_repo,
            'parent_commit': parent_commit,
            'commit_message': commit_message,
        })
        if self.before_upload:
            self.before_upload(self)
        if (self.origin / path_in_repo).read_bytes() == path_or_fileobj:
            # huggingface_hub returns the branch head without a commit or a parent check
            return SimpleNamespace(oid=self.head())
        if parent_commit is not None and parent_commit != self.head():
            request = httpx2.Request('POST', 'https://huggingface.co/api/commit')
            raise HfHubHTTPError('412 parent moved', response=httpx2.Response(412, request=request))
        self.commit({path_in_repo: path_or_fileobj}, commit_message)
        return SimpleNamespace(oid=self.head())

    def list_repo_commits(self, repo_id, *, repo_type, revision=None):
        log = git(self.origin, 'log', '--format=%H %s', revision).splitlines()
        return [SimpleNamespace(commit_id=line[:40], title=line[41:]) for line in log]

    def hf_hub_download(self, repo_id, filename, *, repo_type, revision=None, local_dir=None):
        out = Path(local_dir) / filename
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(
            subprocess.run(
                ['git', 'show', f'{revision}:{filename}'], cwd=self.origin, check=True, capture_output=True
            ).stdout
        )
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
        {'path_in_repo': f'{PREFIX}/{MANIFEST}', 'parent_commit': hub_pair.head, 'commit_message': 'rebuild'}
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
