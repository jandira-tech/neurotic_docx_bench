"""Carry verified hub files into the run manifest after local pruning."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import httpx2
from huggingface_hub.errors import (
    HfHubHTTPError,
    LocalEntryNotFoundError,
    RemoteEntryNotFoundError,
    RepositoryNotFoundError,
)

from neurotic_docx_bench import hub
from test_hub import FakeHub


@pytest.fixture
def upload():
    spec = importlib.util.spec_from_file_location('hub_upload', 'results/redlines_0929_full/hub_upload.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def remote_missing(path: str) -> RemoteEntryNotFoundError:
    request = httpx2.Request('GET', f'https://huggingface.co/{path}')
    return RemoteEntryNotFoundError(f'404 {path}', response=httpx2.Response(404, request=request))


def repo_missing(repo_id: str) -> RepositoryNotFoundError:
    request = httpx2.Request('GET', f'https://huggingface.co/api/datasets/{repo_id}')
    return RepositoryNotFoundError(f'404 {repo_id}', response=httpx2.Response(404, request=request))


HEAD = 'a' * 40
PREVIOUS = 'b' * 40


def test_previous_entries_are_carried_without_asking_the_hub(upload, tmp_path, monkeypatch):
    """upload_folder is the only hub check before the upload: the previous manifest's entries
    that this run does not restage are carried as they are (Arthur, 2026-11-01)."""
    assert not hasattr(upload, 'carried_entries')
    assert not hasattr(upload, 'ManifestCarryError')


@pytest.fixture
def run(upload, tmp_path, monkeypatch):
    here = tmp_path / 'run'
    (here / 'tool' / 'docx').mkdir(parents=True)
    (here / 'versions.json').write_text('{"tool": "1.0"}')
    (here / 'scores.json').write_text('{"score": 100}')
    (here / 'RUN.md').write_text('# run')
    (here / 'tool' / 'docx' / 'a.docx').write_bytes(b'new redline')
    (here / 'tool' / 'timings.json').write_text('{}')
    monkeypatch.setattr(upload, 'HERE', here)
    monkeypatch.setattr(upload, 'TOOLS', ('tool',))
    monkeypatch.setattr(upload, 'FRESH', tmp_path / 'absent')
    monkeypatch.setattr(upload, 'PRUNE', (here / 'tool' / 'docx',))
    return here


def test_stage_combines_staged_and_carried_files(upload, run, tmp_path, capsys):
    path = 'fresh_compares/a.pdf'
    previous = {path: sha(b'pruned oracle'), 'run/RUN.md': sha(b'old run')}
    root = tmp_path / 'staging'
    subdirs = upload.stage(root, previous=previous)
    files = hub.read_manifest(root / 'run' / hub.MANIFEST_NAME)
    staged = {
        'run/versions.json': sha((run / 'versions.json').read_bytes()),
        'run/scores.json': sha((run / 'scores.json').read_bytes()),
        'run/RUN.md': sha(b'# run'),
        'tool/docx/a.docx': sha(b'new redline'),
        'tool/meta/timings.json': sha(b'{}'),
    }
    assert files == staged | {path: previous[path]}
    assert subdirs == ['tool/docx', 'tool/meta', 'run']
    assert 'manifest: 5 staged + 1 carried from the previous manifest' in capsys.readouterr().out
    upload.stage(root)
    assert hub.read_manifest(root / 'run' / hub.MANIFEST_NAME) == staged


class DownloadHub(FakeHub):
    """Serve downloads from the fake hub's stored bytes, failing the way huggingface_hub 2.0 does."""

    def __init__(self, cache):
        super().__init__()
        self.cache = cache
        self.downloads = []
        self.offline = False
        self.vanished = set()
        self.refs = {None: HEAD, 'previous-good-commit': PREVIOUS}
        self.tree_revisions = []
        self.parents = []
        self.commit_after_manifest = False
        self.foreign_file = None
        self.log = [SimpleNamespace(commit_id=HEAD, title='initial commit')]

    def list_repo_commits(self, repo_id, *, repo_type, revision=None):
        ids = [c.commit_id for c in self.log]
        return self.log[: ids.index(revision) + 1][::-1]

    def repo_info(self, repo_id, *, repo_type, revision=None):
        if repo_id not in self.stored:
            raise repo_missing(repo_id)
        return SimpleNamespace(sha=self.refs[revision])

    def list_repo_tree(self, repo_id, *, repo_type, path_in_repo=None, recursive=True, expand=True, revision=None):
        self.tree_revisions.append(revision)
        if repo_id not in self.stored:
            raise repo_missing(repo_id)
        entries = list(
            super().list_repo_tree(
                repo_id, repo_type=repo_type, path_in_repo=path_in_repo, recursive=recursive, expand=expand
            )
        )
        if path_in_repo and not entries:
            raise remote_missing(path_in_repo)
        yield from entries

    def upload_folder(self, *, parent_commit=None, **kwargs):
        folder, store = Path(kwargs['folder_path']), self.stored.get(kwargs['repo_id'], {})
        files = {
            f'{kwargs["path_in_repo"]}/{p.relative_to(folder)}': p.read_bytes()
            for p in folder.rglob('*')
            if p.is_file()
        }
        if all(store.get(path) == data for path, data in files.items()):
            # huggingface_hub makes no commit, skips the parent check, returns the branch head.
            return SimpleNamespace(oid=self.refs[None])
        if parent_commit is not None and parent_commit != self.refs[None]:
            request = httpx2.Request('POST', 'https://huggingface.co/api/datasets/commit/main')
            raise HfHubHTTPError(
                '412 parent commit is not the head of main', response=httpx2.Response(412, request=request)
            )
        super().upload_folder(**kwargs)
        self.parents.append(parent_commit)
        self.refs[None] = f'{len(self.parents):040x}'
        self.log.append(SimpleNamespace(commit_id=self.refs[None], title=kwargs['commit_message']))
        return SimpleNamespace(oid=self.refs[None])

    def hf_hub_download(self, repo_id, filename, *, repo_type, revision=None):
        self.downloads.append((filename, revision))
        if self.offline:
            raise LocalEntryNotFoundError('offline and not in the cache')
        if filename in self.vanished:
            raise remote_missing(filename)
        try:
            data = self.stored[repo_id][filename]
        except KeyError:
            raise remote_missing(filename) from None
        dest = self.cache / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        if self.commit_after_manifest:
            self.commit_after_manifest = False
            self.refs[None] = 'c' * 40  # another writer commits while this run stages
            self.log.append(SimpleNamespace(commit_id=self.refs[None], title='someone else'))
            if self.foreign_file is not None:
                self.stored[repo_id][self.foreign_file[0]] = self.foreign_file[1]
        return str(dest)


@pytest.mark.parametrize('revision', [None, 'previous-good-commit'])
def test_main_carries_the_previous_manifest_and_reads_nothing_else(upload, run, tmp_path, monkeypatch, revision):
    api = DownloadHub(tmp_path / 'cache')
    prefix = upload.REPO_PREFIX + '/'
    files = {'fresh_compares/a.pdf': b'pruned oracle', 'run/old.md': b'old note'}
    api.stored[hub.RESULTS_REPO] = {prefix + p: data for p, data in files.items()}
    manifest_path = prefix + 'run/' + hub.MANIFEST_NAME
    api.stored[hub.RESULTS_REPO][manifest_path] = json.dumps(
        hub.manifest_document({p: sha(data) for p, data in files.items()})
    ).encode()
    monkeypatch.setattr(hub, 'default_api', lambda: api)
    argv = ['hub_upload', '--staging', str(tmp_path / 'staging')]
    if revision is not None:
        argv += ['--previous-revision', revision]
    monkeypatch.setattr(sys, 'argv', argv)
    upload.main()
    published = json.loads(api.stored[hub.RESULTS_REPO][manifest_path])['files']
    assert all(published[p] == sha(data) for p, data in files.items())
    # Every read is pinned to a commit: a failed HEAD request makes huggingface_hub serve
    # the cached copy of a branch, which can be older than the listing.
    assert api.downloads == [(manifest_path, {None: HEAD, 'previous-good-commit': PREVIOUS}[revision])]
    # No listing and no per-file download: upload_folder alone decides what to send.
    assert api.tree_revisions == []
    # Each commit names its parent, so a writer that commits in between makes the upload fail.
    assert api.parents == [HEAD] + [f'{i:040x}' for i in range(1, len(api.parents))]


def test_main_refuses_when_the_hub_moved_after_reading(upload, run, tmp_path, monkeypatch):
    api = DownloadHub(tmp_path / 'cache')
    prefix = upload.REPO_PREFIX + '/'
    files = {'fresh_compares/a.pdf': b'pruned oracle'}
    api.stored[hub.RESULTS_REPO] = {prefix + p: data for p, data in files.items()}
    manifest_path = prefix + 'run/' + hub.MANIFEST_NAME
    manifest = json.dumps(hub.manifest_document({p: sha(data) for p, data in files.items()})).encode()
    api.stored[hub.RESULTS_REPO][manifest_path] = manifest
    api.commit_after_manifest = True
    monkeypatch.setattr(hub, 'default_api', lambda: api)
    monkeypatch.setattr(sys, 'argv', ['hub_upload', '--staging', str(tmp_path / 'staging')])
    with pytest.raises(HfHubHTTPError, match='412'):
        upload.main()
    assert api.stored[hub.RESULTS_REPO][manifest_path] == manifest
    assert api.parents == []


def test_main_refuses_a_no_op_that_reports_someone_elses_commit(upload, run, tmp_path, monkeypatch):
    api = DownloadHub(tmp_path / 'cache')
    api.stored[hub.RESULTS_REPO] = {}
    monkeypatch.setattr(hub, 'default_api', lambda: api)
    monkeypatch.setattr(sys, 'argv', ['hub_upload', '--staging', str(tmp_path / 'staging')])
    upload.main()  # the hub now holds this run's files
    note = upload.REPO_PREFIX + '/run/RUN.md'
    newer = b'# run, as someone else rewrote it'
    api.foreign_file = (note, newer)
    api.commit_after_manifest = True
    commits = len(api.parents)
    # tool/docx is unchanged, so its upload is a no-op that returns the other writer's head.
    with pytest.raises(upload.StaleParentError):
        upload.main()
    assert api.stored[hub.RESULTS_REPO][note] == newer
    assert len(api.parents) == commits


def test_main_first_upload_without_manifest(upload, run, tmp_path, monkeypatch):
    api = DownloadHub(tmp_path / 'cache')
    api.stored[hub.RESULTS_REPO] = {'README.md': b'other runs live here'}
    monkeypatch.setattr(hub, 'default_api', lambda: api)
    monkeypatch.setattr(sys, 'argv', ['hub_upload', '--staging', str(tmp_path / 'staging')])
    upload.main()
    manifest_path = upload.REPO_PREFIX + '/run/' + hub.MANIFEST_NAME
    files = json.loads(api.stored[hub.RESULTS_REPO][manifest_path])['files']
    assert len(files) == 5
    assert api.downloads == [(manifest_path, HEAD)]


def test_main_creates_an_absent_dataset(upload, run, tmp_path, monkeypatch):
    api = DownloadHub(tmp_path / 'cache')
    monkeypatch.setattr(hub, 'default_api', lambda: api)
    monkeypatch.setattr(sys, 'argv', ['hub_upload', '--staging', str(tmp_path / 'staging')])
    upload.main()
    manifest_path = upload.REPO_PREFIX + '/run/' + hub.MANIFEST_NAME
    assert len(json.loads(api.stored[hub.RESULTS_REPO][manifest_path])['files']) == 5


def test_main_offline_manifest_read_uploads_nothing(upload, run, tmp_path, monkeypatch):
    api = DownloadHub(tmp_path / 'cache')
    prefix = upload.REPO_PREFIX + '/'
    api.stored[hub.RESULTS_REPO] = {prefix + 'fresh_compares/a.pdf': b'pruned oracle'}
    api.offline = True
    monkeypatch.setattr(hub, 'default_api', lambda: api)
    monkeypatch.setattr(sys, 'argv', ['hub_upload', '--staging', str(tmp_path / 'staging')])
    with pytest.raises(LocalEntryNotFoundError):
        upload.main()
    assert set(api.stored[hub.RESULTS_REPO]) == {prefix + 'fresh_compares/a.pdf'}
    assert not any(name == 'upload_folder' for name, _ in api.calls)


def test_prune_deletes_only_after_every_file_verified(upload, run, tmp_path, monkeypatch):
    api = DownloadHub(tmp_path / 'cache')
    api.stored[hub.RESULTS_REPO] = {}
    monkeypatch.setattr(hub, 'default_api', lambda: api)
    monkeypatch.setattr(sys, 'argv', ['hub_upload', '--prune', '--staging', str(tmp_path / 'staging')])
    upload.main()
    assert api.tree_revisions == [None]  # verify_uploaded reads the hub once, after the upload
    assert not (run / 'tool' / 'docx').exists()


def test_prune_keeps_everything_when_a_file_does_not_verify(upload, run, tmp_path, monkeypatch):
    api = DownloadHub(tmp_path / 'cache')
    api.stored[hub.RESULTS_REPO] = {}
    monkeypatch.setattr(hub, 'default_api', lambda: api)
    monkeypatch.setattr(hub, 'verify_uploaded', lambda *a, **k: ['tool/docx/a.docx'])
    monkeypatch.setattr(sys, 'argv', ['hub_upload', '--prune', '--staging', str(tmp_path / 'staging')])
    with pytest.raises(SystemExit, match='nothing deleted'):
        upload.main()
    assert (run / 'tool' / 'docx' / 'a.docx').exists()


def test_main_dry_run_is_offline(upload, run, tmp_path, monkeypatch):
    def no_api():
        pytest.fail('dry run reached the hub')

    monkeypatch.setattr(hub, 'default_api', no_api)
    monkeypatch.setattr(sys, 'argv', ['hub_upload', '--dry-run', '--staging', str(tmp_path / 'staging')])
    upload.main()
    assert len(hub.read_manifest(tmp_path / 'staging' / 'run' / hub.MANIFEST_NAME)) == 5


def test_main_rerun_with_nothing_new_commits_nothing(upload, run, tmp_path, monkeypatch):
    api = DownloadHub(tmp_path / 'cache')
    api.stored[hub.RESULTS_REPO] = {}
    monkeypatch.setattr(hub, 'default_api', lambda: api)
    monkeypatch.setattr(sys, 'argv', ['hub_upload', '--staging', str(tmp_path / 'staging')])
    upload.main()
    commits, head = len(api.parents), api.refs[None]
    upload.main()  # every upload is a no-op that returns this run's own head
    assert (len(api.parents), api.refs[None]) == (commits, head)


class _Commits:
    """list_repo_commits over a fixed history, newest first (#103)."""

    def __init__(self, *history: tuple[str, str]) -> None:
        self.history = [SimpleNamespace(commit_id=c, title=t) for c, t in history]

    def list_repo_commits(self, repo_id, repo_type=None, revision=None):
        ids = [c.commit_id for c in self.history]
        return self.history[ids.index(revision):]


MESSAGE = 'redlines_0929_full: jubarte-0.17.0/docx (2611 files)'


def test_a_folder_split_into_part_commits_is_ours(upload) -> None:
    # huggingface_hub 2.0 (_upload_pipeline.py:650): the first commit carries the bare
    # message, the later ones ' (part 2)', ' (part 3)', ...
    api = _Commits(*[(f'p{n}', f'{MESSAGE} (part {n})') for n in range(8, 1, -1)],
                   ('p1', MESSAGE), ('base', 'before'))
    assert upload.next_parent(api, 'base', SimpleNamespace(oid='p8'), MESSAGE) == 'p8'


def test_one_commit_with_our_message_is_ours(upload) -> None:
    api = _Commits(('c1', MESSAGE), ('base', 'before'))
    assert upload.next_parent(api, 'base', SimpleNamespace(oid='c1'), MESSAGE) == 'c1'


def test_a_no_op_upload_keeps_the_parent(upload) -> None:
    assert upload.next_parent(_Commits(('base', 'before')), 'base', SimpleNamespace(oid='base'), MESSAGE) == 'base'


@pytest.mark.parametrize(
    'history',
    [
        # someone else's commit between our parts
        [('p2', f'{MESSAGE} (part 2)'), ('x', 'someone else'), ('p1', f'{MESSAGE} (part 1)'), ('base', 'before')],
        # the head is someone else's (a no-op upload returned the branch head)
        [('x', 'someone else'), ('base', 'before')],
        # our message on another folder's commit does not count
        [('p1', f'{MESSAGE}x (part 1)'), ('base', 'before')],
        # the parent is not in the history at all
        [('p1', f'{MESSAGE} (part 1)'), ('other', 'before')],
    ],
    ids=['interleaved', 'foreign head', 'other message', 'parent missing'],
)
def test_anything_else_is_a_stale_parent(upload, history) -> None:
    api = _Commits(*history)
    with pytest.raises(upload.StaleParentError):
        upload.next_parent(api, 'base', SimpleNamespace(oid=history[0][0]), MESSAGE)
