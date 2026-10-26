"""Carry verified hub files into the run manifest after local pruning."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from types import SimpleNamespace

import pytest
import httpx2
from huggingface_hub.errors import LocalEntryNotFoundError, RemoteEntryNotFoundError

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

    def list_repo_tree(self, repo_id, *, repo_type, path_in_repo=None, recursive=True, expand=True):
        entries = list(
            super().list_repo_tree(
                repo_id, repo_type=repo_type, path_in_repo=path_in_repo, recursive=recursive, expand=expand
            )
        )
        if path_in_repo and not entries:
            raise remote_missing(path_in_repo)
        yield from entries

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
    assert api.downloads[0] == (manifest_path, revision)
    assert {p for p, _ in api.downloads[1:]} == {prefix + p for p in files}
    assert all(rev is None for _, rev in api.downloads[1:])
    assert api.calls[0][0] == 'list_repo_tree'


def test_main_first_upload_without_manifest(upload, run, tmp_path, monkeypatch):
    api = DownloadHub(tmp_path / 'cache')
    monkeypatch.setattr(hub, 'default_api', lambda: api)
    monkeypatch.setattr(sys, 'argv', ['hub_upload', '--staging', str(tmp_path / 'staging')])
    upload.main()
    manifest_path = upload.REPO_PREFIX + '/run/' + hub.MANIFEST_NAME
    files = json.loads(api.stored[hub.RESULTS_REPO][manifest_path])['files']
    assert len(files) == 5
    assert api.downloads == [(manifest_path, None)]


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
