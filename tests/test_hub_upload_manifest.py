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


@pytest.mark.parametrize('lfs', [dict, SimpleNamespace])
def test_carries_pruned_lfs_file(upload, lfs):
    path = 'jubarte-093/docx/a.docx'
    previous = {path: sha(b'pruned')}
    remote = {path: SimpleNamespace(lfs=lfs(sha256=previous[path]))}
    assert upload.carried_entries(previous, {}, remote, {}.__getitem__) == previous


@pytest.mark.parametrize('remote', [{}, {'run/RUN.md': SimpleNamespace(lfs={'sha256': 'different'})}])
def test_restaged_path_is_never_carried(upload, remote):
    assert (
        upload.carried_entries({'run/RUN.md': sha(b'old')}, {'run/RUN.md': sha(b'new')}, remote, {}.__getitem__) == {}
    )


def test_missing_previous_path_raises(upload):
    path = 'fresh_compares/a.pdf'
    with pytest.raises(upload.ManifestCarryError, match=r'1 missing.*fresh_compares/a.pdf'):
        upload.carried_entries({path: sha(b'old')}, {}, {}, {}.__getitem__)
    assert issubclass(upload.ManifestCarryError, RuntimeError)


@pytest.mark.parametrize('lfs', [dict, SimpleNamespace])
def test_lfs_mismatch_raises(upload, lfs):
    path = 'jubarte-093/docx/a.docx'
    with pytest.raises(upload.ManifestCarryError, match=r'1 mismatched.*jubarte-093/docx/a.docx'):
        upload.carried_entries(
            {path: sha(b'old')}, {}, {path: SimpleNamespace(lfs=lfs(sha256=sha(b'changed')))}, {}.__getitem__
        )


def test_inline_bytes_are_verified(upload):
    path = 'run/old.md'
    files = {path: b'inline file'}
    previous = {path: sha(files[path])}
    remote = {path: SimpleNamespace(lfs=None, blob_id='git sha1 is not sha256')}
    assert upload.carried_entries(previous, {}, remote, files.__getitem__) == previous
    files[path] = b'changed'
    with pytest.raises(upload.ManifestCarryError, match=r'1 mismatched.*run/old.md'):
        upload.carried_entries(previous, {}, remote, files.__getitem__)


def test_inline_file_gone_before_fetch_is_missing(upload):
    path = 'run/old.md'
    remote = {path: SimpleNamespace(lfs=None, blob_id='listed, then deleted')}
    with pytest.raises(upload.ManifestCarryError, match=r'1 missing.*run/old.md'):
        upload.carried_entries({path: sha(b'old')}, {}, remote, lambda rel: None)


def test_error_counts_all_paths_but_lists_only_first_ten(upload):
    missing = {f'missing/{i:02}.pdf': sha(b'old') for i in range(12)}
    mismatched = {f'mismatched/{i:02}.pdf': sha(b'old') for i in range(12)}
    remote = {p: SimpleNamespace(lfs={'sha256': sha(b'changed')}) for p in mismatched}
    with pytest.raises(upload.ManifestCarryError) as exc:
        upload.carried_entries(missing | mismatched, {}, remote, {}.__getitem__)
    message = str(exc.value)
    assert '12 missing' in message
    assert '12 mismatched' in message
    for paths in (missing, mismatched):
        assert all(p in message for p in list(paths)[:10])
        assert all(p not in message for p in list(paths)[10:])


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
    remote = {path: SimpleNamespace(lfs={'sha256': previous[path]})}
    root = tmp_path / 'staging'
    subdirs = upload.stage(root, previous=previous, remote=remote, fetch={}.__getitem__)
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
        self.commit_after_listing = False
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
        if self.commit_after_listing:
            self.commit_after_listing = False
            self.refs[None] = 'c' * 40  # another writer commits while this run stages
            self.log.append(SimpleNamespace(commit_id=self.refs[None], title='someone else'))
            if self.foreign_file is not None:
                self.stored[repo_id][self.foreign_file[0]] = self.foreign_file[1]

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
        return str(dest)


@pytest.mark.parametrize('revision', [None, 'previous-good-commit'])
def test_main_reads_previous_manifest_and_fetches_inline_files(upload, run, tmp_path, monkeypatch, revision):
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
    assert api.downloads[0] == (manifest_path, {None: HEAD, 'previous-good-commit': PREVIOUS}[revision])
    assert {p for p, _ in api.downloads[1:]} == {prefix + p for p in files}
    assert all(rev == HEAD for _, rev in api.downloads[1:])
    # The carry listing is pinned; verify_uploaded then reads the commit the upload made.
    assert api.tree_revisions == [HEAD, None]
    names = [name for name, _ in api.calls]
    assert names.index('list_repo_tree') < names.index('upload_folder')
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
    api.commit_after_listing = True
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
    api.commit_after_listing = True
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


def test_main_inline_file_gone_before_fetch_refuses(upload, run, tmp_path, monkeypatch):
    api = DownloadHub(tmp_path / 'cache')
    prefix = upload.REPO_PREFIX + '/'
    files = {'run/old.md': b'old note'}
    api.stored[hub.RESULTS_REPO] = {prefix + p: data for p, data in files.items()}
    manifest_path = prefix + 'run/' + hub.MANIFEST_NAME
    api.stored[hub.RESULTS_REPO][manifest_path] = json.dumps(
        hub.manifest_document({p: sha(data) for p, data in files.items()})
    ).encode()
    api.vanished = {prefix + 'run/old.md'}
    monkeypatch.setattr(hub, 'default_api', lambda: api)
    monkeypatch.setattr(sys, 'argv', ['hub_upload', '--staging', str(tmp_path / 'staging')])
    with pytest.raises(upload.ManifestCarryError, match=r'1 missing.*run/old.md'):
        upload.main()
    assert not any(name == 'upload_folder' for name, _ in api.calls)


def test_main_dry_run_is_offline(upload, run, tmp_path, monkeypatch):
    def no_api():
        pytest.fail('dry run reached the hub')

    monkeypatch.setattr(hub, 'default_api', no_api)
    monkeypatch.setattr(sys, 'argv', ['hub_upload', '--dry-run', '--staging', str(tmp_path / 'staging')])
    upload.main()
    assert len(hub.read_manifest(tmp_path / 'staging' / 'run' / hub.MANIFEST_NAME)) == 5
