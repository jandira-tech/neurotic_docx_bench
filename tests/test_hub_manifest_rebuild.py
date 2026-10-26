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


class CommitHub:
    """One branch as a list of commits, newest last; each commit maps repo paths to bytes."""

    def __init__(self, files: dict[str, bytes]):
        self.log = [SimpleNamespace(commit_id=HEAD, title='before', files=dict(files))]
        self.uploads: list[dict] = []

    def foreign_commit(self) -> None:
        files = dict(self.log[-1].files) | {f'{PREFIX}/run/RUN.md': b'someone else'}
        self.log.append(SimpleNamespace(commit_id=f'{len(self.log):040x}', title='foreign', files=files))

    def repo_info(self, repo_id, *, repo_type, revision=None):
        return SimpleNamespace(sha=self.log[-1].commit_id)

    def upload_file(self, *, path_or_fileobj, path_in_repo, repo_id, repo_type, commit_message, parent_commit=None):
        self.uploads.append({
            'path_in_repo': path_in_repo,
            'parent_commit': parent_commit,
            'commit_message': commit_message,
        })
        head = self.log[-1]
        if head.files.get(path_in_repo) == path_or_fileobj:
            # huggingface_hub returns the branch head without a commit or a parent check
            return SimpleNamespace(oid=head.commit_id)
        if parent_commit is not None and parent_commit != head.commit_id:
            request = httpx2.Request('POST', 'https://huggingface.co/api/commit')
            raise HfHubHTTPError('412 parent moved', response=httpx2.Response(412, request=request))
        files = dict(head.files) | {path_in_repo: path_or_fileobj}
        self.log.append(SimpleNamespace(commit_id=f'{len(self.log):040x}', title=commit_message, files=files))
        return SimpleNamespace(oid=self.log[-1].commit_id)

    def list_repo_commits(self, repo_id, *, repo_type, revision=None):
        ids = [c.commit_id for c in self.log]
        return [
            SimpleNamespace(commit_id=c.commit_id, title=c.title)
            for c in reversed(self.log[: ids.index(revision) + 1])
        ]

    def hf_hub_download(self, repo_id, filename, *, repo_type, revision=None, local_dir=None):
        files = next(c for c in self.log if c.commit_id == revision).files
        out = Path(local_dir) / filename
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(files[filename])
        return str(out)


def test_publish_commits_on_the_head_it_read_and_reads_it_back(rebuild, tmp_path):
    api = CommitHub({f'{PREFIX}/{MANIFEST}': manifest({})})
    data = manifest({'a/x.docx': sha(b'inline')})
    commit = rebuild.publish(api, HEAD, data, 'rebuild', scratch=tmp_path)
    assert commit == api.log[-1].commit_id != HEAD
    assert api.uploads == [
        {'path_in_repo': f'{PREFIX}/{MANIFEST}', 'parent_commit': HEAD, 'commit_message': 'rebuild'}
    ]
    assert api.log[-1].files[f'{PREFIX}/{MANIFEST}'] == data


def test_publish_refuses_when_the_hub_moved_since_it_was_read(rebuild, tmp_path):
    api = CommitHub({f'{PREFIX}/{MANIFEST}': manifest({})})
    api.foreign_commit()
    with pytest.raises(rebuild.RebuildError, match='moved'):
        rebuild.publish(api, HEAD, manifest({'a/x.docx': sha(b'inline')}), 'rebuild', scratch=tmp_path)
    assert api.uploads == []


def test_publish_with_nothing_to_change_commits_nothing(rebuild, tmp_path):
    data = manifest({'a/x.docx': sha(b'inline')})
    api = CommitHub({f'{PREFIX}/{MANIFEST}': data})
    assert rebuild.publish(api, HEAD, data, 'rebuild', scratch=tmp_path) == HEAD
    assert len(api.log) == 1
