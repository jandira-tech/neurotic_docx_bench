"""`bench hub list|get`: named, pinned, hash-verified downloads from the hub (issue #79).

``PinnedHub`` plays a dataset repo back at fixed commits: ``repo_info`` resolves a branch to
its commit, ``list_repo_tree`` and ``hf_hub_download`` read the commit they are given and
fail on a branch name, so a download that did not pin its revision fails loudly.
"""

from __future__ import annotations

import errno
import hashlib
import os
import re
import shutil
import signal
import stat
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from neurotic_docx_bench import hub, hub_get

runner = CliRunner()
SHA = "a" * 40
OTHER = "b" * 40
REPO = hub.RESULTS_REPO


def blob_id(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


class PinnedHub:
    """One dataset repo; files over 64 bytes are LFS, the rest inline."""

    def __init__(self, files: dict[str, bytes], commits: dict[str, str] | None = None) -> None:
        self.trees = {SHA: dict(files)}
        self.branches = commits or {"main": SHA}
        self.served: dict[str, bytes] = {}  # what a download returns instead of the stored bytes
        self.calls: list[tuple[str, dict]] = []

    def repo_info(self, repo_id: str, *, repo_type: str, revision: str | None = None):
        self.calls.append(("repo_info", {"repo_id": repo_id, "revision": revision}))
        rev = revision or "main"
        sha = self.branches.get(rev, rev if rev in self.trees else None)
        if sha is None:
            raise LookupError(f"no revision {rev}")
        return SimpleNamespace(sha=sha)

    def _tree(self, revision: str | None) -> dict[str, bytes]:
        assert revision in self.trees, f"unpinned read: revision={revision!r}"
        return self.trees[revision]

    def list_repo_tree(self, repo_id, *, repo_type, path_in_repo=None, recursive=True, expand=True, revision=None):
        self.calls.append(("list_repo_tree", {"path_in_repo": path_in_repo, "revision": revision}))
        prefix = (path_in_repo or "").strip("/")
        folders = set()
        for rel, data in sorted(self._tree(revision).items()):
            if prefix and not rel.startswith(prefix + "/"):
                continue
            parts = rel.split("/")
            for i in range(1, len(parts)):
                folders.add("/".join(parts[:i]))
            if len(data) > 64:
                yield SimpleNamespace(path=rel, size=len(data), blob_id="f" * 40,
                                      lfs={"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)})
            else:
                yield SimpleNamespace(path=rel, size=len(data), blob_id=blob_id(data), lfs=None)
        for f in sorted(folders):
            if not prefix or f.startswith(prefix + "/"):
                yield SimpleNamespace(path=f, tree_id="e" * 40)

    def hf_hub_download(self, repo_id, filename, *, repo_type, revision=None, local_dir=None):
        self.calls.append(("hf_hub_download", {"filename": filename, "revision": revision}))
        data = self.served.get(filename, self._tree(revision)[filename])
        out = Path(local_dir) / filename
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        return str(out)

    def downloads(self) -> list[str]:
        return [c["filename"] for name, c in self.calls if name == "hf_hub_download"]


BIG = b"L" * 200  # an LFS file
FILES = {
    "outputs/run/a.docx": BIG,
    "outputs/run/sub/b.pdf": BIG + b"2",
    "outputs/run/RUN.md": b"# run\n",
    "outputs/other/c.txt": b"not ours\n",
    "README.md": b"card\n",
}


def preset(dest: Path, **kw) -> hub_get.Preset:
    return hub_get.Preset(name="t", repo_id=REPO, path="outputs/run", dest=dest, about="test", **kw)


def test_get_downloads_the_folder_at_the_pinned_commit(tmp_path: Path) -> None:
    api = PinnedHub(FILES)
    report = hub_get.get(preset(tmp_path / "dest"), api=api)

    assert report.revision == SHA
    assert (tmp_path / "dest/a.docx").read_bytes() == BIG
    assert (tmp_path / "dest/sub/b.pdf").read_bytes() == BIG + b"2"
    assert (tmp_path / "dest/RUN.md").read_bytes() == b"# run\n"
    assert not (tmp_path / "dest/c.txt").exists()
    assert (report.downloaded, report.skipped, report.n_files) == (3, 0, 3)
    assert report.n_bytes == len(BIG) * 2 + 1 + len(b"# run\n")
    # main was resolved once; everything after read the commit
    assert [c for c in api.calls if c[0] == "repo_info"] == [("repo_info", {"repo_id": REPO, "revision": "main"})]
    assert {c[1]["revision"] for c in api.calls if c[0] != "repo_info"} == {SHA}
    # the staging folder is gone and nothing else was left beside the destination
    assert sorted(p.name for p in tmp_path.iterdir()) == ["dest"]


def test_get_passes_an_explicit_revision_through_repo_info(tmp_path: Path) -> None:
    api = PinnedHub(FILES, commits={"main": OTHER, "v1": SHA})
    report = hub_get.get(preset(tmp_path / "d"), api=api, revision="v1")
    assert report.revision == SHA
    assert ("repo_info", {"repo_id": REPO, "revision": "v1"}) in api.calls


def test_get_refuses_a_revision_that_is_not_a_commit(tmp_path: Path) -> None:
    class Odd(PinnedHub):
        def repo_info(self, repo_id, *, repo_type, revision=None):
            return SimpleNamespace(sha="main")

    with pytest.raises(hub_get.GetError, match="commit"):
        hub_get.get(preset(tmp_path / "d"), api=Odd(FILES))


@pytest.mark.parametrize("bad", ["outputs/run/a.docx", "outputs/run/RUN.md"])
def test_a_download_that_does_not_hash_like_the_hub_refuses_and_moves_nothing(tmp_path: Path, bad: str) -> None:
    api = PinnedHub(FILES)
    api.served[bad] = FILES[bad][:-1] + b"X"
    with pytest.raises(hub_get.GetError, match=re.escape(bad.removeprefix("outputs/run/"))):
        hub_get.get(preset(tmp_path / "dest"), api=api)
    assert not (tmp_path / "dest").exists() or not any((tmp_path / "dest").rglob("*.*"))


def test_a_failed_download_keeps_its_staging_folder_for_a_rerun(tmp_path: Path) -> None:
    api = PinnedHub(FILES)
    api.served["outputs/run/RUN.md"] = b"tampered\n"
    with pytest.raises(hub_get.GetError):
        hub_get.get(preset(tmp_path / "dest"), api=api)
    staging = hub_get.staging_dir(tmp_path / "dest", SHA)
    assert staging.is_dir()
    api.served.clear()
    report = hub_get.get(preset(tmp_path / "dest"), api=api)
    assert report.downloaded == 3
    assert not staging.exists()


def test_identical_local_files_are_skipped_and_not_downloaded(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    (dest / "sub").mkdir(parents=True)
    (dest / "a.docx").write_bytes(BIG)
    (dest / "RUN.md").write_bytes(b"# run\n")
    api = PinnedHub(FILES)
    report = hub_get.get(preset(dest), api=api)
    assert (report.downloaded, report.skipped) == (1, 2)
    assert api.downloads() == ["outputs/run/sub/b.pdf"]


def test_a_different_local_file_stops_the_run_before_any_download(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "RUN.md").write_bytes(b"# my local edits\n")
    api = PinnedHub(FILES)
    with pytest.raises(hub_get.GetError, match=re.escape("RUN.md")) as exc:
        hub_get.get(preset(dest), api=api)
    assert "--overwrite" in str(exc.value) and "--keep-local" in str(exc.value)
    assert api.downloads() == []
    assert (dest / "RUN.md").read_bytes() == b"# my local edits\n"


def test_overwrite_replaces_a_different_local_file(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "RUN.md").write_bytes(b"# my local edits\n")
    report = hub_get.get(preset(dest), api=PinnedHub(FILES), on_conflict="overwrite")
    assert (dest / "RUN.md").read_bytes() == b"# run\n"
    assert report.replaced == 1


def test_keep_local_keeps_a_different_local_file_and_downloads_the_rest(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "RUN.md").write_bytes(b"# my local edits\n")
    api = PinnedHub(FILES)
    report = hub_get.get(preset(dest), api=api, on_conflict="keep-local")
    assert (dest / "RUN.md").read_bytes() == b"# my local edits\n"
    assert (dest / "a.docx").read_bytes() == BIG
    assert report.kept_local == ("RUN.md",)
    assert "outputs/run/RUN.md" not in api.downloads()


def test_include_narrows_and_exclude_drops(tmp_path: Path) -> None:
    api = PinnedHub(FILES)
    report = hub_get.get(preset(tmp_path / "d"), api=api, include=["sub/*"])
    assert api.downloads() == ["outputs/run/sub/b.pdf"]
    assert report.n_files == 1

    api = PinnedHub(FILES)
    hub_get.get(preset(tmp_path / "e", exclude=("sub/*",)), api=api)
    assert sorted(api.downloads()) == ["outputs/run/RUN.md", "outputs/run/a.docx"]


def test_include_that_matches_nothing_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(hub_get.GetError, match="nothing"):
        hub_get.get(preset(tmp_path / "d"), api=PinnedHub(FILES), include=["*.xlsx"])


def test_the_hub_attributes_file_is_never_downloaded(tmp_path: Path) -> None:
    api = PinnedHub({**FILES, ".gitattributes": b"*.docx filter=lfs\n"})
    p = hub_get.Preset(name="all", repo_id=REPO, path="", dest=tmp_path / "all", about="whole repo")
    hub_get.get(p, api=api)
    assert ".gitattributes" not in api.downloads()
    assert (tmp_path / "all/outputs/run/a.docx").exists()


def test_dry_run_downloads_nothing_and_writes_nothing(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "a.docx").write_bytes(BIG)
    api = PinnedHub(FILES)
    report = hub_get.get(preset(dest), api=api, dry_run=True)
    assert api.downloads() == []
    assert sorted(p.name for p in tmp_path.iterdir()) == ["dest"]
    assert sorted(p.name for p in dest.iterdir()) == ["a.docx"]
    assert (report.n_files, report.skipped, report.downloaded) == (3, 1, 0)
    assert report.to_download == 2


def test_not_enough_disk_refuses_before_downloading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hub_get, "free_bytes", lambda path: 10)
    api = PinnedHub(FILES)
    with pytest.raises(hub_get.GetError, match="disk"):
        hub_get.get(preset(tmp_path / "d"), api=api)
    assert api.downloads() == []


def test_presets_cover_the_three_datasets_and_resolve_destinations(tmp_path: Path) -> None:
    names = set(hub_get.PRESETS)
    assert {"corpus", "corpus-word", "redlines-0929", "wordcraft-20261014", "git-archive"} <= names
    assert {p.repo_id for p in hub_get.PRESETS.values()} == {hub.FIXTURES_REPO, hub.RESULTS_REPO, hub_get.ARCHIVE_REPO}
    for p in hub_get.PRESETS.values():
        assert not p.dest.is_absolute(), p.name
        assert not p.path.endswith("/"), p.name
    # the fixtures repo's card is corpus/README.md (scripts/hf_fixtures/hf_fixtures.py writes it there)
    assert hub_get.PRESETS["corpus"].exclude == ()
    # the fresh compares have their own preset and destination
    assert "fresh_compares/*" in hub_get.PRESETS["redlines-0929"].exclude
    assert hub_get.PRESETS["compare-regen"].dest == Path("results/compare_regen/out")


def test_remote_files_skip_folders(tmp_path: Path) -> None:
    api = PinnedHub(FILES)
    files = hub_get.remote_files(api, REPO, SHA, "outputs")
    assert [f.rel for f in files] == ["other/c.txt", "run/RUN.md", "run/a.docx", "run/sub/b.pdf"]


def test_cli_hub_list_and_get(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from neurotic_docx_bench.cli import app

    api = PinnedHub(FILES)
    monkeypatch.setattr(hub, "default_api", lambda: api)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["hub", "list"])
    assert result.exit_code == 0, result.output
    for name in ("corpus", "redlines-0929", "git-archive"):
        assert name in result.output

    result = runner.invoke(app, ["hub", "get", "--repo", REPO, "--path", "outputs/run", "--dest", "got"])
    assert result.exit_code == 0, result.output
    assert SHA[:12] in result.output
    assert (tmp_path / "got/a.docx").read_bytes() == BIG

    (tmp_path / "got/RUN.md").write_bytes(b"edited\n")
    result = runner.invoke(app, ["hub", "get", "--repo", REPO, "--path", "outputs/run", "--dest", "got"])
    assert result.exit_code == 1
    assert "RUN.md" in result.output

    result = runner.invoke(app, ["hub", "get", "no-such-preset"])
    assert result.exit_code == 2
    assert "no-such-preset" in result.output


def test_cli_hub_get_a_preset_dry_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from neurotic_docx_bench.cli import app

    api = PinnedHub({"word/x.docx": BIG, "word/MANIFEST.sha256.json": b"{}"})
    monkeypatch.setattr(hub, "default_api", lambda: api)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["hub", "get", "corpus-word", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "2 files" in result.output
    assert api.downloads() == []
    assert not (tmp_path / "corpus").exists()


class LateWriter(PinnedHub):
    """Writes a local file into the destination while the download runs."""

    def __init__(self, files, dest: Path, rel: str, data: bytes) -> None:
        super().__init__(files)
        self.late = (dest / rel, data)

    def hf_hub_download(self, repo_id, filename, *, repo_type, revision=None, local_dir=None):
        path, data = self.late
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return super().hf_hub_download(repo_id, filename, repo_type=repo_type, revision=revision, local_dir=local_dir)


def test_a_file_written_during_the_download_is_not_clobbered_and_nothing_moves(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    api = LateWriter(FILES, dest, "RUN.md", b"written meanwhile\n")
    with pytest.raises(hub_get.GetError, match=re.escape("RUN.md")):
        hub_get.get(preset(dest), api=api)
    assert (dest / "RUN.md").read_bytes() == b"written meanwhile\n"
    assert sorted(p.name for p in dest.rglob("*")) == ["RUN.md"]
    assert hub_get.staging_dir(dest, SHA).is_dir()


def test_keep_local_keeps_a_file_written_during_the_download(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    api = LateWriter(FILES, dest, "RUN.md", b"written meanwhile\n")
    report = hub_get.get(preset(dest), api=api, on_conflict="keep-local")
    assert (dest / "RUN.md").read_bytes() == b"written meanwhile\n"
    assert (dest / "a.docx").read_bytes() == BIG
    assert report.kept_local == ("RUN.md",)


def test_a_file_written_during_the_download_with_the_hub_bytes_is_fine(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    report = hub_get.get(preset(dest), api=LateWriter(FILES, dest, "RUN.md", b"# run\n"))
    assert (dest / "RUN.md").read_bytes() == b"# run\n"
    assert (dest / "a.docx").read_bytes() == BIG
    assert not hub_get.staging_dir(dest, SHA).exists()
    assert report.n_files == 3


def test_staging_sits_on_the_destination_device(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest = tmp_path / "mount"
    dest.mkdir()
    assert hub_get.staging_dir(dest, SHA) == tmp_path / f".mount.hub-{SHA[:12]}"
    monkeypatch.setattr(hub_get, "device", lambda p: 2 if Path(p).absolute() == dest.absolute() else 1)
    assert hub_get.staging_dir(dest, SHA) == dest / f".hub-{SHA[:12]}"
    report = hub_get.get(preset(dest), api=PinnedHub(FILES))
    assert report.downloaded == 3
    assert sorted(p.name for p in dest.iterdir()) == ["RUN.md", "a.docx", "sub"]


def test_cli_hub_list_sizes_marks_a_preset_it_cannot_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from neurotic_docx_bench.cli import app

    class NoToken(PinnedHub):
        def repo_info(self, repo_id, *, repo_type, revision=None):
            if repo_id == hub_get.ARCHIVE_REPO:
                raise PermissionError("401 Unauthorized")
            return super().repo_info(repo_id, repo_type=repo_type, revision=revision)

    monkeypatch.setattr(hub, "default_api", lambda: NoToken(FILES))
    result = runner.invoke(app, ["hub", "list", "--sizes"])
    assert result.exit_code == 0, result.output
    line = next(ln for ln in result.output.splitlines() if ln.startswith("git-archive"))
    assert "unavailable" in line and "401" in line


class ReusingHub(PinnedHub):
    """Like hf_hub_download(local_dir=...): a file already in local_dir is returned as it is."""

    def hf_hub_download(self, repo_id, filename, *, repo_type, revision=None, local_dir=None):
        out = Path(local_dir) / filename
        if out.exists() or out.is_symlink():
            self.calls.append(("hf_hub_download", {"filename": filename, "revision": revision}))
            return str(out)
        return super().hf_hub_download(repo_id, filename, repo_type=repo_type, revision=revision, local_dir=local_dir)


def test_a_reused_staged_file_is_hashed_again_and_a_bad_one_refetched(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    staged = hub_get.staging_dir(dest, SHA) / hub_get.FILES / "outputs/run/RUN.md"
    staged.parent.mkdir(parents=True)
    staged.write_bytes(b"stale\n")
    api = ReusingHub(FILES)
    with pytest.raises(hub_get.GetError, match=re.escape("RUN.md")):
        hub_get.get(preset(dest), api=api)
    assert not staged.exists()
    assert hub_get.get(preset(dest), api=api).downloaded == 3
    assert (dest / "RUN.md").read_bytes() == b"# run\n"


def test_a_symlink_in_staging_is_refused_and_its_target_untouched(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    outside = tmp_path / "outside.md"
    outside.write_bytes(b"# run\n")  # hashes like the hub's RUN.md
    staged = hub_get.staging_dir(dest, SHA) / hub_get.FILES / "outputs/run/RUN.md"
    staged.parent.mkdir(parents=True)
    staged.symlink_to(outside)
    with pytest.raises(hub_get.GetError, match="symlink"):
        hub_get.get(preset(dest), api=ReusingHub(FILES))
    assert outside.read_bytes() == b"# run\n"
    assert not (dest / "RUN.md").exists()


def test_a_symlinked_staging_folder_never_deletes_outside_it(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "RUN.md").write_bytes(b"user file\n")  # does not hash like the hub's
    staging = hub_get.staging_dir(dest, SHA)
    (staging / hub_get.FILES / "outputs").mkdir(parents=True)
    (staging / hub_get.FILES / "outputs/run").symlink_to(elsewhere)
    with pytest.raises(hub_get.GetError, match="symlink"):
        hub_get.get(preset(dest), api=ReusingHub(FILES))
    assert (elsewhere / "RUN.md").read_bytes() == b"user file\n"


def test_a_local_file_where_the_hub_has_a_folder_refuses_before_downloading(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "sub").write_bytes(b"a file named sub\n")
    api = PinnedHub(FILES)
    with pytest.raises(hub_get.GetError, match="sub"):
        hub_get.get(preset(dest), api=api)
    assert api.downloads() == []
    assert sorted(p.name for p in dest.iterdir()) == ["sub"]


def test_a_failed_move_puts_back_everything_already_moved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "RUN.md").write_bytes(b"old\n")
    real = hub_get.place
    calls = []

    def flaky(staged, target):
        calls.append(target)
        if len(calls) == 3:
            raise OSError("disk went away")
        return real(staged, target)

    monkeypatch.setattr(hub_get, "place", flaky)
    with pytest.raises(hub_get.GetError, match="disk went away"):
        hub_get.get(preset(dest), api=PinnedHub(FILES), on_conflict="overwrite")
    assert sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*")) == ["RUN.md"]
    assert (dest / "RUN.md").read_bytes() == b"old\n"
    staging = hub_get.staging_dir(dest, SHA) / hub_get.FILES
    assert {p.relative_to(staging).as_posix() for p in staging.rglob("*") if p.is_file()} >= {
        "outputs/run/a.docx", "outputs/run/sub/b.pdf", "outputs/run/RUN.md"}


def test_success_leaves_unrelated_files_in_the_staging_folder_alone(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    staging = hub_get.staging_dir(dest, SHA)
    staging.mkdir(parents=True)
    (staging / "notes.txt").write_bytes(b"mine\n")
    report = hub_get.get(preset(dest), api=PinnedHub(FILES))
    assert report.downloaded == 3
    assert (staging / "notes.txt").read_bytes() == b"mine\n"
    assert sorted(p.name for p in staging.iterdir()) == ["notes.txt"]


def test_a_second_run_on_the_same_staging_folder_is_refused(tmp_path: Path) -> None:
    import fcntl

    dest = tmp_path / "dest"
    staging = hub_get.staging_dir(dest, SHA)
    staging.mkdir(parents=True)
    with open(staging / hub_get.LOCK, "w") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        api = PinnedHub(FILES)
        with pytest.raises(hub_get.GetError, match="another"):
            hub_get.get(preset(dest), api=api)
    assert api.downloads() == []


def test_names_that_collide_on_a_case_insensitive_disk_refuse_before_downloading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hub_get, "case_insensitive", lambda path: True)
    api = PinnedHub({**FILES, "outputs/run/Run.md": b"other\n"})
    with pytest.raises(hub_get.GetError, match=r"RUN\.md.*Run\.md|Run\.md.*RUN\.md"):
        hub_get.get(preset(tmp_path / "dest"), api=api)
    assert api.downloads() == []


def test_case_insensitive_probe_matches_this_disk(tmp_path: Path) -> None:
    (tmp_path / "probe").write_bytes(b"x")
    assert hub_get.case_insensitive(tmp_path) == (tmp_path / "PROBE").exists()
    assert list(tmp_path.iterdir()) == [tmp_path / "probe"]


# Review round 2 (#80)


def test_the_no_hard_link_fallback_never_overwrites_a_file_that_appears(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A disk without hard links; another writer creates the target in the instant before the move."""
    staged, target = tmp_path / "staged", tmp_path / "target"
    staged.write_bytes(b"REMOTE")
    real_rename, real_replace, real_open = os.rename, os.replace, os.open

    def writer_first(path) -> None:
        if Path(path) == target and not target.exists():
            target.write_bytes(b"USER FILE")

    def no_links(src, dst, **kw):
        raise OSError(errno.EOPNOTSUPP, "no hard links on this disk")

    def rename(src, dst, **kw):
        writer_first(dst)
        return real_rename(src, dst, **kw)

    def replace(src, dst, **kw):
        writer_first(dst)
        return real_replace(src, dst, **kw)

    def open_(path, flags, mode=0o777, **kw):
        writer_first(path)
        return real_open(path, flags, mode, **kw)

    monkeypatch.setattr(os, "link", no_links)
    monkeypatch.setattr(os, "rename", rename)
    monkeypatch.setattr(os, "replace", replace)
    monkeypatch.setattr(os, "open", open_)
    with pytest.raises(hub_get.GetError, match="appeared"):
        hub_get.place(staged, target)
    assert target.read_bytes() == b"USER FILE"
    assert staged.read_bytes() == b"REMOTE"


def test_rollback_leaves_a_file_another_process_put_there_after_the_move(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "dest"
    real = hub_get.place

    def flaky(staged, target):
        if target.name == "b.pdf":  # moves run in order: RUN.md, a.docx, sub/b.pdf
            theirs = dest / "a.docx.theirs"
            theirs.write_bytes(b"USER FILE")
            os.replace(theirs, dest / "a.docx")  # another process replaces a file this run moved
            raise OSError("disk went away")
        return real(staged, target)

    monkeypatch.setattr(hub_get, "place", flaky)
    with pytest.raises(hub_get.GetError, match=re.escape(str(dest / "a.docx"))):
        hub_get.get(preset(dest), api=PinnedHub(FILES))
    assert (dest / "a.docx").read_bytes() == b"USER FILE"
    assert not (dest / "RUN.md").exists()


def test_a_staged_copy_that_cannot_be_removed_is_reported_once_every_file_is_in_place(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Staged copies are removed only after every move; a failure there leaves nothing half done."""
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "RUN.md").write_bytes(b"ORIGINAL\n")
    staging = hub_get.staging_dir(dest, SHA)
    real_unlink = os.unlink
    failed = []

    def unlink(path, *args, **kw):
        p = Path(path)
        if p.name == "RUN.md" and p.is_relative_to(staging) and not failed:
            failed.append(p)
            raise PermissionError(errno.EACCES, "the staged copy cannot be removed")
        return real_unlink(path, *args, **kw)

    monkeypatch.setattr(os, "unlink", unlink)
    with pytest.raises(hub_get.GetError, match=r"every file is in place.*cannot be removed"):
        hub_get.get(preset(dest), api=PinnedHub(FILES), on_conflict="overwrite")
    assert failed
    assert (dest / "RUN.md").read_bytes() == b"# run\n"
    assert {p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file()} == {"RUN.md", "a.docx", "sub/b.pdf"}


def test_one_rollback_error_does_not_stop_the_others(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest = tmp_path / "dest"
    real_place, real_replace = hub_get.place, os.replace

    def flaky(staged, target):
        if target.name == "b.pdf":
            raise OSError("disk went away")
        return real_place(staged, target)

    real_link, real_rename = os.link, os.rename

    def refuse_a(src) -> None:
        if Path(src) == dest / "a.docx":
            raise OSError(errno.EIO, "a.docx cannot be moved back")

    def replace(src, dst, *args, **kw):
        refuse_a(src)
        return real_replace(src, dst, *args, **kw)

    def link(src, dst, *args, **kw):
        refuse_a(src)
        return real_link(src, dst, *args, **kw)

    def rename(src, dst, *args, **kw):
        refuse_a(src)
        return real_rename(src, dst, *args, **kw)

    monkeypatch.setattr(hub_get, "place", flaky)
    monkeypatch.setattr(os, "replace", replace)
    monkeypatch.setattr(os, "link", link)
    monkeypatch.setattr(os, "rename", rename)
    with pytest.raises(hub_get.GetError, match="cannot be moved back"):
        hub_get.get(preset(dest), api=PinnedHub(FILES))
    assert not (dest / "RUN.md").exists()  # put back although a.docx could not be
    assert (dest / "a.docx").read_bytes() == BIG


def test_hub_files_named_like_the_lock_or_the_backup_folder_download_fine(tmp_path: Path) -> None:
    files = {".lock": b"REMOTE LOCK\n", ".replaced/x.txt": b"X\n", "a.txt": b"A\n"}
    dest = tmp_path / "dest"
    whole = hub_get.Preset(name="t", repo_id=REPO, path="", dest=dest, about="test")
    report = hub_get.get(whole, api=PinnedHub(files))
    assert report.downloaded == 3
    assert {p.relative_to(dest).as_posix(): p.read_bytes() for p in dest.rglob("*") if p.is_file()} == files
    assert sorted(p.name for p in tmp_path.iterdir()) == ["dest"]


def test_a_hub_path_inside_the_download_bookkeeping_is_refused(tmp_path: Path) -> None:
    api = PinnedHub({".cache/huggingface/download/a.txt.metadata": b"x\n", "a.txt": b"A\n"})
    whole = hub_get.Preset(name="t", repo_id=REPO, path="", dest=tmp_path / "dest", about="test")
    with pytest.raises(hub_get.GetError, match=re.escape(".cache/huggingface")):
        hub_get.get(whole, api=api)
    assert api.downloads() == []


def test_dry_run_never_writes_a_probe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest = tmp_path / "dest"
    dest.mkdir()

    def read_only(*args, **kw):
        raise PermissionError(errno.EROFS, "read-only file system")

    monkeypatch.setattr(tempfile, "NamedTemporaryFile", read_only)
    monkeypatch.setattr(tempfile, "mkstemp", read_only)
    api = PinnedHub({**FILES, "outputs/run/Run.md": b"other\n"})
    try:
        hub_get.get(preset(dest), api=api, dry_run=True)
    except hub_get.GetError as exc:  # a case-insensitive disk refuses the pair, which is fine
        assert "one file" in str(exc)
    assert list(dest.iterdir()) == []
    assert api.downloads() == []


def test_a_replaced_file_a_failed_rollback_kept_is_never_overwritten(tmp_path: Path) -> None:
    """A rollback that could not restore a file leaves it in the staging folder; the next run must not clobber it."""
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "RUN.md").write_bytes(b"newer local\n")
    kept = hub_get.staging_dir(dest, SHA) / ".replaced" / "RUN.md"
    kept.parent.mkdir(parents=True)
    kept.write_bytes(b"the only copy of the original\n")
    with pytest.raises(hub_get.GetError, match=re.escape(str(kept))):
        hub_get.get(preset(dest), api=PinnedHub(FILES), on_conflict="overwrite")
    assert kept.read_bytes() == b"the only copy of the original\n"
    assert (dest / "RUN.md").read_bytes() == b"newer local\n"



# Review round 3 (#80)


def test_a_failed_copy_never_removes_a_file_that_replaced_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    staged, target = tmp_path / "staged", tmp_path / "target"
    staged.write_bytes(b"REMOTE")

    def no_links(src, dst, **kw):
        raise OSError(errno.EOPNOTSUPP, "no hard links on this disk")

    def copy_then_fail(src, dst, *args, **kw):
        theirs = tmp_path / "theirs"
        theirs.write_bytes(b"USER FILE")
        os.replace(theirs, target)  # another writer replaces the half-made copy
        raise OSError(errno.ENOSPC, "disk full")

    monkeypatch.setattr(os, "link", no_links)
    monkeypatch.setattr(shutil, "copyfileobj", copy_then_fail)
    with pytest.raises(OSError, match="disk full"):
        hub_get.place(staged, target)
    assert target.read_bytes() == b"USER FILE"
    assert staged.read_bytes() == b"REMOTE"


def test_a_staged_file_with_another_name_is_never_written_through(tmp_path: Path) -> None:
    """``PinnedHub`` writes into an existing file, as hf_hub_download's copy from the hub cache does."""
    dest = tmp_path / "dest"
    outside = tmp_path / "outside.md"
    outside.write_bytes(b"USER ORIGINAL\n")
    staged = hub_get.staging_dir(dest, SHA) / hub_get.FILES / "outputs/run/RUN.md"
    staged.parent.mkdir(parents=True)
    os.link(outside, staged)
    report = hub_get.get(preset(dest), api=PinnedHub(FILES))
    assert report.downloaded == 3
    assert outside.read_bytes() == b"USER ORIGINAL\n"
    assert (dest / "RUN.md").read_bytes() == b"# run\n"


def test_a_failed_identity_lookup_never_leaves_a_file_placed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest = tmp_path / "dest"
    staged_a = hub_get.staging_dir(dest, SHA) / hub_get.FILES / "outputs/run/a.docx"
    real_lstat = os.lstat

    def lstat(path, *args, **kw):
        if Path(path) == staged_a and (dest / "a.docx").exists():  # only once a.docx is linked into place
            raise OSError(errno.EIO, "lstat failed")
        return real_lstat(path, *args, **kw)

    monkeypatch.setattr(os, "lstat", lstat)
    try:
        report = hub_get.get(preset(dest), api=PinnedHub(FILES))
    except hub_get.GetError:
        assert not dest.exists() or not any(p.is_file() for p in dest.rglob("*"))
    else:
        assert report.downloaded == 3


def test_ctrl_c_while_moving_puts_everything_back(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest = tmp_path / "dest"
    local = {"RUN.md": b"old run\n", "a.docx": b"old a\n", "sub/b.pdf": b"old b\n"}
    for rel, data in local.items():
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        (dest / rel).write_bytes(data)
    real = hub_get.place
    pressed = []

    def interrupted(staged, target):
        if target.name == "b.pdf" and not pressed:  # once, after its backup was made
            pressed.append(target)
            raise KeyboardInterrupt
        return real(staged, target)

    monkeypatch.setattr(hub_get, "place", interrupted)
    with pytest.raises((KeyboardInterrupt, hub_get.GetError)):
        hub_get.get(preset(dest), api=PinnedHub(FILES), on_conflict="overwrite")
    assert {p.relative_to(dest).as_posix(): p.read_bytes() for p in dest.rglob("*") if p.is_file()} == local


def test_rollback_never_overwrites_a_file_that_appeared_in_staging(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest = tmp_path / "dest"
    staged_a = hub_get.staging_dir(dest, SHA) / hub_get.FILES / "outputs/run/a.docx"
    real = hub_get.place

    def flaky(staged, target):
        if target.name == "b.pdf":
            new = staged_a.with_name("new")
            new.write_bytes(b"NEW FILE IN STAGING")
            os.replace(new, staged_a)  # a new file takes the staged name
            raise OSError("disk went away")
        return real(staged, target)

    monkeypatch.setattr(hub_get, "place", flaky)
    with pytest.raises(hub_get.GetError, match="disk went away"):
        hub_get.get(preset(dest), api=PinnedHub(FILES))
    assert staged_a.read_bytes() == b"NEW FILE IN STAGING"
    assert not any(p.is_file() for p in dest.rglob("*"))


# CodeRabbit, review of 2026-10-26 19:00 (#80)


def test_a_listing_failure_is_a_get_error(tmp_path: Path) -> None:
    class Missing(PinnedHub):
        def list_repo_tree(self, *args, **kw):
            yield SimpleNamespace(path="outputs/run/RUN.md", size=6, blob_id=blob_id(b"# run\n"), lfs=None)
            raise LookupError("404: outputs/run is not in the repo")  # a later page fails

    with pytest.raises(hub_get.GetError, match=r"cannot list outputs/run.*404"):
        hub_get.get(preset(tmp_path / "dest"), api=Missing(FILES))


def test_a_symlinked_folder_below_the_destination_is_refused(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    dest.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "b.pdf").write_bytes(b"outside, not ours\n")
    (dest / "sub").symlink_to(outside)
    api = PinnedHub(FILES)
    with pytest.raises(hub_get.GetError, match=re.escape(f"{dest / 'sub'} is a symlink")):
        hub_get.get(preset(dest), api=api, on_conflict="overwrite")
    assert (outside / "b.pdf").read_bytes() == b"outside, not ours\n"
    assert api.downloads() == []


# Review round 4, mcode (#80)


def test_a_symlinked_folder_that_appears_while_moving_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest = tmp_path / "dest"
    outside = tmp_path / "outside"
    outside.mkdir()
    real = hub_get.place
    calls = []

    def racing(staged, target):
        calls.append(target)
        if len(calls) == 2:  # after the checks before the moves, while RUN.md is already in place
            (dest / "sub").symlink_to(outside)
        return real(staged, target)

    monkeypatch.setattr(hub_get, "place", racing)
    with pytest.raises(hub_get.GetError, match=re.escape(f"{dest / 'sub'} is a symlink")):
        hub_get.get(preset(dest), api=PinnedHub(FILES))
    assert list(outside.iterdir()) == []
    assert not (dest / "RUN.md").exists() and not (dest / "a.docx").exists()


def test_the_staging_folder_is_pruned_while_the_lock_is_held(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest = tmp_path / "dest"
    staging = hub_get.staging_dir(dest, SHA)
    real = hub_get._prune
    seen = []

    def prune(root):
        seen.append((staging / hub_get.LOCK).exists())
        return real(root)

    monkeypatch.setattr(hub_get, "_prune", prune)
    hub_get.get(preset(dest), api=PinnedHub(FILES))
    assert seen and all(seen)
    assert not staging.exists()


def test_a_lock_taken_on_a_file_no_longer_at_the_lock_path_is_taken_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Another run removed the lock file between this run's open and its flock."""
    dest = tmp_path / "dest"
    staging = hub_get.staging_dir(dest, SHA)
    real = hub_get.fcntl.flock
    calls = []

    def flock(fd, op):
        calls.append(op)
        if len(calls) == 1:
            (staging / hub_get.LOCK).unlink()
            (staging / hub_get.LOCK).write_bytes(b"")  # a third run's fresh lock file
        return real(fd, op)

    monkeypatch.setattr(hub_get.fcntl, "flock", flock)
    assert hub_get.get(preset(dest), api=PinnedHub(FILES)).downloaded == 3
    assert len([op for op in calls if op & hub_get.fcntl.LOCK_EX]) == 2


def test_a_rerun_tells_of_replaced_files_an_earlier_run_left_and_unlinks_its_staged_second_names(tmp_path: Path) -> None:
    """What a run killed in the middle of its moves leaves: placed files with a staged second name, and backups."""
    dest = tmp_path / "dest"
    hub_get.get(preset(dest), api=PinnedHub(FILES))
    staging = hub_get.staging_dir(dest, SHA)
    staged = staging / hub_get.FILES / "outputs/run/a.docx"
    staged.parent.mkdir(parents=True)
    os.link(dest / "a.docx", staged)
    backup = staging / ".replaced" / "RUN.md"
    backup.parent.mkdir(parents=True)
    backup.write_bytes(b"the user's old RUN.md\n")
    report = hub_get.get(preset(dest), api=PinnedHub(FILES))
    assert report.downloaded == 0
    assert getattr(report, "earlier_replaced", None) == (str(backup),)
    assert str(backup) in report.describe()
    assert backup.read_bytes() == b"the user's old RUN.md\n"
    assert not staged.exists()
    assert os.stat(dest / "a.docx").st_nlink == 1


def test_the_corpus_preset_downloads_the_corpus_readme() -> None:
    """The fixtures repo's README.md is corpus/README.md (the same bytes); it is not a separate card."""
    assert not hub_get._matches("README.md", hub_get.PRESETS["corpus"].exclude)


def test_cli_dry_run_with_keep_local_does_not_say_it_kept_anything(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from neurotic_docx_bench.cli import app

    api = PinnedHub({"word/x.docx": BIG, "word/MANIFEST.sha256.json": b"{}"})
    monkeypatch.setattr(hub, "default_api", lambda: api)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "corpus/word").mkdir(parents=True)
    (tmp_path / "corpus/word/MANIFEST.sha256.json").write_bytes(b"{ }")
    result = runner.invoke(app, ["hub", "get", "corpus-word", "--dry-run", "--keep-local"])
    assert result.exit_code == 0, result.output
    assert "kept local:" not in result.output
    assert "would keep local: MANIFEST.sha256.json" in result.output


# Review round 4, Codex (#80)


def test_a_destination_inside_the_staging_folder_is_refused(tmp_path: Path) -> None:
    """``dest`` a symlink to the staging folder's files/: the cleanup would delete the file it kept."""
    dest = tmp_path / "dest"
    staging = hub_get.staging_dir(dest, SHA)
    (staging / hub_get.FILES).mkdir(parents=True)
    dest.symlink_to(staging / hub_get.FILES)
    (dest / "a.txt").write_bytes(b"mine\n")
    whole = hub_get.Preset(name="t", repo_id=REPO, path="", dest=dest, about="test")
    api = PinnedHub({"a.txt": b"remote a\n", "b.txt": b"remote b\n"})
    with pytest.raises(hub_get.GetError, match="staging folder"):
        hub_get.get(whole, api=api, on_conflict="keep-local")
    assert (dest / "a.txt").read_bytes() == b"mine\n"
    assert api.downloads() == []


def test_hub_files_that_would_land_in_a_staging_folder_inside_the_destination_are_refused(tmp_path: Path) -> None:
    """``dest`` a symlink to its own parent puts the staging folder inside it."""
    dest = tmp_path / "dest"
    dest.symlink_to(tmp_path)
    staging = hub_get.staging_dir(dest, SHA)
    whole = hub_get.Preset(name="t", repo_id=REPO, path="", dest=dest, about="test")
    api = PinnedHub({"a.txt": b"remote a\n", f"{staging.name}/files/a.txt": b"remote a again\n"})
    with pytest.raises(hub_get.GetError, match="staging folder"):
        hub_get.get(whole, api=api)
    assert api.downloads() == []


def test_a_folder_swapped_for_a_symlink_while_moving_never_moves_files_outside(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "dest"
    local = {"RUN.md": b"old run\n", "a.docx": b"old a\n", "sub/b.pdf": b"old b\n"}
    for rel, data in local.items():
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        (dest / rel).write_bytes(data)
    outside, aside = tmp_path / "outside", tmp_path / "sub-aside"
    outside.mkdir()
    (outside / "b.pdf").write_bytes(b"outside, not ours\n")
    real = hub_get.place

    def racing(staged, target):
        if target.name == "a.docx" and not aside.exists():  # after every check before the moves
            (dest / "sub").rename(aside)
            (dest / "sub").symlink_to(outside)
        return real(staged, target)

    monkeypatch.setattr(hub_get, "place", racing)
    with pytest.raises(hub_get.GetError, match=re.escape(f"{dest / 'sub'} is a symlink")):
        hub_get.get(preset(dest), api=PinnedHub(FILES), on_conflict="overwrite")
    assert sorted(p.name for p in outside.iterdir()) == ["b.pdf"]
    assert (outside / "b.pdf").read_bytes() == b"outside, not ours\n"
    assert (dest / "RUN.md").read_bytes() == b"old run\n"
    assert (dest / "a.docx").read_bytes() == b"old a\n"
    assert (aside / "b.pdf").read_bytes() == b"old b\n"


def test_a_file_restored_on_a_disk_without_hard_links_keeps_its_mode_and_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "dest"
    dest.mkdir()
    mine = dest / "RUN.md"
    mine.write_bytes(b"old run\n")
    os.chmod(mine, 0o600)
    os.utime(mine, ns=(1_000_000_000, 1_000_000_000))
    real = hub_get.place

    def no_links(src, dst, *args, **kw):
        raise OSError(errno.EOPNOTSUPP, "no hard links on this disk")

    def flaky(staged, target):
        if target.name == "b.pdf":
            raise OSError("disk went away")
        return real(staged, target)

    monkeypatch.setattr(os, "link", no_links)
    monkeypatch.setattr(hub_get, "place", flaky)
    with pytest.raises(hub_get.GetError, match="disk went away"):
        hub_get.get(preset(dest), api=PinnedHub(FILES), on_conflict="overwrite")
    st = os.stat(mine)
    assert mine.read_bytes() == b"old run\n"
    assert stat.S_IMODE(st.st_mode) == 0o600
    assert st.st_mtime_ns == 1_000_000_000


def test_a_copy_whose_identity_cannot_be_read_is_named_as_left_behind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "dest"
    real_open, real_fstat = os.open, os.fstat
    watched, failed = set(), []

    def no_links(src, dst, *args, **kw):
        raise OSError(errno.EOPNOTSUPP, "no hard links on this disk")

    def open_(path, flags, mode=0o777, **kw):
        fd = real_open(path, flags, mode, **kw)
        if Path(path) == dest / "a.docx":
            watched.add(fd)
        return fd

    def fstat(fd):
        if fd in watched and not failed:
            failed.append(fd)
            raise OSError(errno.EIO, "fstat failed")
        return real_fstat(fd)

    monkeypatch.setattr(os, "link", no_links)
    monkeypatch.setattr(os, "open", open_)
    monkeypatch.setattr(os, "fstat", fstat)
    with pytest.raises(hub_get.GetError) as info:
        hub_get.get(preset(dest), api=PinnedHub(FILES))
    message = str(info.value)
    assert failed
    assert "every file already moved was put back" not in message
    assert f"{dest / 'a.docx'}" in message and "stays" in message
    assert not (dest / "RUN.md").exists()


# Review round 5, Codex (#80)


def _write(dest: Path, files: dict[str, bytes]) -> None:
    for rel, data in files.items():
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        (dest / rel).write_bytes(data)


def _tree(dest: Path) -> dict[str, bytes]:
    return {p.relative_to(dest).as_posix(): p.read_bytes() for p in dest.rglob("*") if p.is_file()}


def test_ctrl_c_the_moment_a_local_file_is_moved_aside_puts_it_back(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest = tmp_path / "dest"
    local = {"RUN.md": b"old run\n", "a.docx": b"old a\n", "sub/b.pdf": b"old b\n"}
    _write(dest, local)
    real = os.replace
    sent = []

    def replace(src, dst, *args, **kw):
        done = real(src, dst, *args, **kw)
        if hub_get._BACKUP in Path(dst).parts and not sent:
            sent.append(dst)
            os.kill(os.getpid(), signal.SIGINT)  # a real Ctrl-C, delivered as the rename returns
        return done

    monkeypatch.setattr(os, "replace", replace)
    with pytest.raises((KeyboardInterrupt, hub_get.GetError)):
        hub_get.get(preset(dest), api=PinnedHub(FILES), on_conflict="overwrite")
    assert sent
    assert _tree(dest) == local


def test_ctrl_c_the_moment_a_file_is_placed_takes_it_back(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest = tmp_path / "dest"
    real = hub_get.place
    sent = []

    def place(staged, target):
        placed = real(staged, target)
        if target.name == "a.docx" and not sent:
            sent.append(target)
            os.kill(os.getpid(), signal.SIGINT)
        return placed

    monkeypatch.setattr(hub_get, "place", place)
    with pytest.raises((KeyboardInterrupt, hub_get.GetError)):
        hub_get.get(preset(dest), api=PinnedHub(FILES))
    assert sent
    assert _tree(dest) == {}


def test_a_failed_look_at_the_lock_file_lets_go_of_the_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest = tmp_path / "dest"
    lock = hub_get.staging_dir(dest, SHA) / hub_get.LOCK
    real = hub_get._identity_at
    failed = []

    def identity_at(path):
        if Path(path) == lock and not failed:
            failed.append(path)
            raise OSError(errno.EIO, "lstat failed")
        return real(path)

    monkeypatch.setattr(hub_get, "_identity_at", identity_at)
    with pytest.raises((OSError, hub_get.GetError), match="lstat failed"):
        hub_get.get(preset(dest), api=PinnedHub(FILES))
    assert hub_get.get(preset(dest), api=PinnedHub(FILES)).downloaded == 3


def test_a_case_variant_of_the_attributes_file_is_never_downloaded(tmp_path: Path) -> None:
    api = PinnedHub({**FILES, "outputs/run/.GITATTRIBUTES": b"* -text\n", "outputs/run/sub/.GitAttributes": b"x\n"})
    report = hub_get.get(preset(tmp_path / "dest"), api=api)
    assert report.downloaded == 3
    assert not any(name.casefold().endswith(".gitattributes") for name in api.downloads())


@pytest.mark.parametrize("folder", ["RUN.md.metadata", "sub/b.pdf.lock", "RUN.MD.Metadata"])
def test_hub_folders_named_like_the_downloads_records_refuse_before_downloading(tmp_path: Path, folder: str) -> None:
    """hf_hub_download keeps a file's records at .cache/huggingface/download/<path>.metadata and <path>.lock."""
    api = PinnedHub({**FILES, f"outputs/run/{folder}/x.txt": b"x\n"})
    with pytest.raises(hub_get.GetError, match=re.escape(folder)):
        hub_get.get(preset(tmp_path / "dest"), api=api)
    assert api.downloads() == []


# Review round 5, mcode (#80)


def test_a_file_where_the_staging_folder_goes_is_refused_cleanly(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    hub_get.staging_dir(dest, SHA).write_bytes(b"not a folder\n")
    with pytest.raises(hub_get.GetError, match="staging folder"):
        hub_get.get(preset(dest), api=PinnedHub(FILES))


def test_a_run_with_nothing_to_download_is_not_refused_by_a_leftover_staging_folder(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    hub_get.get(preset(dest), api=PinnedHub(FILES))
    staging = hub_get.staging_dir(dest, SHA)
    (staging / "elsewhere").mkdir(parents=True)
    (staging / "link").symlink_to(tmp_path / "elsewhere")
    assert hub_get.get(preset(dest), api=PinnedHub(FILES)).skipped == 3  # a symlink in it
    (staging / "link").unlink()
    with open(staging / hub_get.LOCK, "a") as held:
        hub_get.fcntl.flock(held, hub_get.fcntl.LOCK_EX | hub_get.fcntl.LOCK_NB)
        assert hub_get.get(preset(dest), api=PinnedHub(FILES)).skipped == 3  # another run holds it


def test_a_lock_error_other_than_busy_is_refused_and_lets_go_of_the_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_locks(fd, op):
        raise OSError(errno.ENOLCK, "no locks available")

    monkeypatch.setattr(hub_get.fcntl, "flock", no_locks)
    before = len(os.listdir("/dev/fd"))
    with pytest.raises(hub_get.GetError, match="no locks available"):
        hub_get.get(preset(tmp_path / "dest"), api=PinnedHub(FILES))
    assert len(os.listdir("/dev/fd")) == before


def test_a_local_file_that_becomes_a_folder_before_it_is_replaced_stays(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "dest"
    local = {"RUN.md": b"old run\n", "a.docx": b"old a\n", "sub/b.pdf": b"old b\n"}
    _write(dest, local)
    real = hub_get.place

    def racing(staged, target):
        if target.name == "RUN.md" and (dest / "a.docx").is_file():
            (dest / "a.docx").unlink()
            (dest / "a.docx").mkdir()
            (dest / "a.docx" / "important.txt").write_bytes(b"notes\n")
        return real(staged, target)

    monkeypatch.setattr(hub_get, "place", racing)
    with pytest.raises(hub_get.GetError, match=re.escape(str(dest / "a.docx"))):
        hub_get.get(preset(dest), api=PinnedHub(FILES), on_conflict="overwrite")
    assert _tree(dest) == {"RUN.md": b"old run\n", "a.docx/important.txt": b"notes\n", "sub/b.pdf": b"old b\n"}


def test_a_dry_run_says_the_real_run_would_be_refused(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    _write(dest, {"RUN.md": b"mine\n"})
    report = hub_get.get(preset(dest), api=PinnedHub(FILES), dry_run=True)
    assert "would refuse" in report.describe()
    assert "would refuse" not in hub_get.get(preset(dest), api=PinnedHub(FILES), dry_run=True,
                                             on_conflict="keep-local").describe()


# Review round 6, mcode and Codex (#80)


def _spin() -> None:
    for _ in range(1000):  # lets the interpreter run a pending signal handler
        pass


def test_overwrite_refuses_a_symlinked_local_file_before_downloading(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    dest.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_bytes(b"theirs\n")
    (dest / "RUN.md").symlink_to(outside)
    api = PinnedHub(FILES)
    with pytest.raises(hub_get.GetError, match=re.escape(f"{dest / 'RUN.md'} is a symlink")):
        hub_get.get(preset(dest), api=api, on_conflict="overwrite")
    assert api.downloads() == []
    assert (dest / "RUN.md").is_symlink() and outside.read_bytes() == b"theirs\n"


@pytest.mark.parametrize("obstacle", ["symlink", "busy"])
def test_a_run_with_nothing_to_download_still_names_an_earlier_runs_replaced_files(tmp_path: Path, obstacle: str) -> None:
    dest = tmp_path / "dest"
    hub_get.get(preset(dest), api=PinnedHub(FILES))
    staging = hub_get.staging_dir(dest, SHA)
    backup = staging / hub_get._BACKUP / "RUN.md"
    backup.parent.mkdir(parents=True)
    backup.write_bytes(b"the user's old RUN.md\n")
    if obstacle == "symlink":
        (staging / "link").symlink_to(tmp_path)
        report = hub_get.get(preset(dest), api=PinnedHub(FILES))
    else:
        with open(staging / hub_get.LOCK, "a") as held:
            hub_get.fcntl.flock(held, hub_get.fcntl.LOCK_EX | hub_get.fcntl.LOCK_NB)
            report = hub_get.get(preset(dest), api=PinnedHub(FILES))
    assert report.skipped == 3
    assert report.earlier_replaced == (str(backup),)
    assert str(backup) in report.describe()
    assert backup.read_bytes() == b"the user's old RUN.md\n"


def _overwrite_that_fails_on_b(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, dict[str, bytes]]:
    dest = tmp_path / "dest"
    local = {"RUN.md": b"old run\n", "a.docx": b"old a\n", "sub/b.pdf": b"old b\n"}
    _write(dest, local)
    real = hub_get.place

    def flaky(staged, target):
        if target.name == "b.pdf" and hub_get._BACKUP not in staged.parts:  # the move, not the restore
            raise OSError("disk went away")
        return real(staged, target)

    monkeypatch.setattr(hub_get, "place", flaky)
    return dest, local


def test_one_ctrl_c_during_the_rollback_lets_it_finish_then_stops(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest, local = _overwrite_that_fails_on_b(tmp_path, monkeypatch)
    real = hub_get._withdraw
    sent = []

    def withdraw(target, placed, staging):
        if not sent:
            sent.append(target)
            os.kill(os.getpid(), signal.SIGINT)
            _spin()
        return real(target, placed, staging)

    monkeypatch.setattr(hub_get, "_withdraw", withdraw)
    with pytest.raises(KeyboardInterrupt) as exc:
        hub_get.get(preset(dest), api=PinnedHub(FILES), on_conflict="overwrite")
    assert sent
    assert _tree(dest) == local
    assert "put back" in " ".join(getattr(exc.value, "__notes__", ()))


def test_a_second_ctrl_c_during_the_rollback_stops_it_and_names_the_staging_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest, _ = _overwrite_that_fails_on_b(tmp_path, monkeypatch)
    real = hub_get._withdraw
    sent = []

    def withdraw(target, placed, staging):
        if not sent:
            sent.append(target)
            os.kill(os.getpid(), signal.SIGINT)
            _spin()
            os.kill(os.getpid(), signal.SIGINT)
            _spin()
        return real(target, placed, staging)

    monkeypatch.setattr(hub_get, "_withdraw", withdraw)
    with pytest.raises(KeyboardInterrupt) as exc:
        hub_get.get(preset(dest), api=PinnedHub(FILES), on_conflict="overwrite")
    assert sent
    assert str(hub_get.staging_dir(dest, SHA)) in " ".join(getattr(exc.value, "__notes__", ()))


@pytest.mark.parametrize("policy", ["ignore", "custom"])
def test_a_ctrl_c_policy_the_caller_set_is_kept_while_files_move(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, policy: str
) -> None:
    dest = tmp_path / "dest"
    real = hub_get.place
    seen, sent = [], []

    def place(staged, target):
        placed = real(staged, target)
        if not sent:
            sent.append(target)
            os.kill(os.getpid(), signal.SIGINT)
            _spin()
        return placed

    monkeypatch.setattr(hub_get, "place", place)
    previous = signal.signal(signal.SIGINT, signal.SIG_IGN if policy == "ignore" else lambda *a: seen.append(a[0]))
    try:
        report = hub_get.get(preset(dest), api=PinnedHub(FILES))
    finally:
        signal.signal(signal.SIGINT, previous)
    assert sent and report.downloaded == 3
    assert seen == ([] if policy == "ignore" else [signal.SIGINT])


def test_a_partial_copy_that_cannot_be_removed_is_named_as_left_behind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "dest"
    real_unlink = os.unlink

    def no_links(src, dst, *args, **kw):
        raise OSError(errno.EOPNOTSUPP, "no hard links on this disk")

    real_copy = shutil.copyfileobj

    def partial(src, dst, *args, **kw):
        if not src.name.endswith("a.docx"):
            return real_copy(src, dst, *args, **kw)
        dst.write(b"REM")
        raise OSError(errno.ENOSPC, "disk full")

    def unlink(path, *args, **kw):
        if Path(path) == dest / "a.docx":
            raise OSError(errno.EIO, "unlink failed")
        return real_unlink(path, *args, **kw)

    monkeypatch.setattr(os, "link", no_links)
    monkeypatch.setattr(shutil, "copyfileobj", partial)
    monkeypatch.setattr(os, "unlink", unlink)
    with pytest.raises(hub_get.GetError) as info:
        hub_get.get(preset(dest), api=PinnedHub(FILES))
    message = str(info.value)
    assert "every file already moved was put back" not in message
    assert f"{dest / 'a.docx'}" in message and "stays" in message


# Review round 7, Codex (#80)


@pytest.mark.parametrize("step", ["backup", "place"])
def test_a_second_ctrl_c_while_files_move_waits_until_the_step_is_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, step: str
) -> None:
    dest = tmp_path / "dest"
    local = {"RUN.md": b"old run\n", "a.docx": b"old a\n", "sub/b.pdf": b"old b\n"}
    _write(dest, local)
    sent = []

    def press_twice() -> None:
        sent.append(step)
        for _ in range(2):
            os.kill(os.getpid(), signal.SIGINT)
            _spin()

    if step == "backup":  # the local file is moved aside, its journal entry not yet updated
        real_replace = os.replace

        def replace(src, dst, *args, **kw):
            real_replace(src, dst, *args, **kw)
            if not sent and hub_get._BACKUP in Path(dst).parts:
                press_twice()

        monkeypatch.setattr(os, "replace", replace)
    else:  # the hub's file is linked into place, its identity not yet recorded
        real_place = hub_get.place

        def place(staged, target):
            placed = real_place(staged, target)
            if not sent:
                press_twice()
            return placed

        monkeypatch.setattr(hub_get, "place", place)
    with pytest.raises(BaseException) as exc:
        hub_get.get(preset(dest), api=PinnedHub(FILES), on_conflict="overwrite")
    assert sent
    assert exc.type is KeyboardInterrupt, exc.value
    assert _tree(dest) == local
    assert "every replaced file restored" in " ".join(getattr(exc.value, "__notes__", ()))


def test_cli_hub_get_prints_what_a_ctrl_c_left_behind_and_exits_130(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from neurotic_docx_bench.cli import app

    def interrupted(*args, **kw):
        stop = KeyboardInterrupt()
        stop.add_note("moving into got failed (KeyboardInterrupt); the file it replaced is kept at .got.hub-x/.replaced/RUN.md")
        raise stop

    monkeypatch.setattr(hub, "default_api", lambda: PinnedHub(FILES))
    monkeypatch.setattr(hub_get, "get", interrupted)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["hub", "get", "--repo", REPO, "--path", "outputs/run", "--dest", "got"])
    assert result.exit_code == 130
    assert ".got.hub-x/.replaced/RUN.md" in result.output
    assert "Ctrl-C" in result.output


# Review round 7, mcode (#80)


def _press_twice() -> None:
    for _ in range(2):
        os.kill(os.getpid(), signal.SIGINT)
        _spin()


def test_a_second_ctrl_c_during_the_rollback_never_splits_a_step(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest, local = _overwrite_that_fails_on_b(tmp_path, monkeypatch)
    real_rename = os.rename
    sent = []

    def rename(src, dst, *args, **kw):  # _withdraw has just taken the hub's a.docx out of the destination
        real_rename(src, dst, *args, **kw)
        if not sent and Path(dst).parent.name.startswith(".withdrawn-"):
            sent.append(dst)
            _press_twice()

    monkeypatch.setattr(os, "rename", rename)
    with pytest.raises(BaseException) as exc:
        hub_get.get(preset(dest), api=PinnedHub(FILES), on_conflict="overwrite")
    assert sent
    assert exc.type is KeyboardInterrupt, exc.value
    staging = hub_get.staging_dir(dest, SHA)
    assert list(staging.glob(".withdrawn-*")) == []
    assert (dest / "a.docx").read_bytes() == local["a.docx"]  # its step was finished
    notes = " ".join(getattr(exc.value, "__notes__", ()))
    assert str(dest / "RUN.md") in notes  # the step the rollback did not reach
    assert str(staging) in notes


def test_a_run_names_a_file_an_earlier_run_took_back_and_left(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    hub_get.get(preset(dest), api=PinnedHub(FILES))
    staging = hub_get.staging_dir(dest, SHA)
    left = staging / ".withdrawn-x1y2z3" / "file"
    left.parent.mkdir(parents=True)
    left.write_bytes(b"taken back from the destination\n")
    report = hub_get.get(preset(dest), api=PinnedHub(FILES))
    assert str(left) in report.earlier_replaced
    assert str(left) in report.describe()
    assert left.read_bytes() == b"taken back from the destination\n"


def test_a_second_ctrl_c_after_the_rollback_does_not_say_it_stopped_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "dest"
    real_place = hub_get.place

    def flaky(staged, target):
        if target.name == "b.pdf":
            raise OSError("disk went away")
        return real_place(staged, target)

    real_rmdir = Path.rmdir
    sent = []

    def rmdir(self):  # the folders this run made, removed after the rollback
        if not sent and self == dest / "sub":
            sent.append(self)
            _press_twice()
        return real_rmdir(self)

    monkeypatch.setattr(hub_get, "place", flaky)
    monkeypatch.setattr(Path, "rmdir", rmdir)
    with pytest.raises(BaseException) as exc:
        hub_get.get(preset(dest), api=PinnedHub(FILES))
    assert sent
    assert exc.type is KeyboardInterrupt, exc.value
    notes = " ".join(getattr(exc.value, "__notes__", ()))
    assert "stopped putting back" not in notes
    assert "every file already moved was put back" in notes
    assert not dest.exists() or _tree(dest) == {}


def test_ctrl_c_that_reaches_a_download_thread_stops_the_queued_downloads(tmp_path: Path) -> None:
    import threading
    import time

    dest = tmp_path / "dest"
    api = PinnedHub({f"outputs/run/f{i:02}.txt": f"file {i}\n".encode() for i in range(20)})
    real = api.hf_hub_download

    def slow(repo_id, filename, **kw):
        out = real(repo_id, filename, **kw)
        if filename.endswith("f01.txt"):  # Ctrl-C lands in this download thread, not the main one
            signal.pthread_kill(threading.get_ident(), signal.SIGINT)
            time.sleep(1)  # the main thread looks every 0.25 s: it stops the queue before this ends
        elif filename.endswith("f00.txt"):
            time.sleep(2)
        else:
            time.sleep(0.05)
        return out

    api.hf_hub_download = slow
    with pytest.raises(KeyboardInterrupt) as exc:
        hub_get.get(preset(dest), api=api, workers=2)
    # Only the two running downloads end; unseen, the press would let the other thread fetch the 18 left
    assert len(api.downloads()) == 2
    assert not dest.exists() or _tree(dest) == {}
    notes = " ".join(getattr(exc.value, "__notes__", ()))
    assert str(hub_get.staging_dir(dest, SHA)) in notes and "rerun" in notes


def test_the_records_of_a_file_and_of_a_folder_named_like_them_collide_in_the_sdk(tmp_path: Path) -> None:
    """The premise of _record_clashes, read from the installed huggingface_hub (mcode round 7 #1, pushed back)."""
    from huggingface_hub._local_folder import get_local_download_paths

    a = get_local_download_paths(tmp_path, "corpus/a.txt")
    b = get_local_download_paths(tmp_path, "corpus/a.txt.metadata/b")
    c = get_local_download_paths(tmp_path, "corpus/a.txt.lock/c")
    assert b.metadata_path.parent == a.metadata_path  # a folder where a.txt's record file goes
    assert c.metadata_path.parent == a.lock_path  # and where its lock file goes
    with pytest.raises(IsADirectoryError):
        a.metadata_path.write_text("{}")


# Review round 8, Codex (#80)


def _hub_of_slow_files(n: int = 3) -> PinnedHub:
    return PinnedHub({f"outputs/run/f{i:02}.txt": f"file {i}\n".encode() for i in range(n)})


def test_ctrl_c_while_a_download_thread_starts_leaves_no_thread_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import threading
    import time

    api = _hub_of_slow_files()
    real_download = api.hf_hub_download

    def slow(*args, **kw):
        time.sleep(0.5)
        return real_download(*args, **kw)

    api.hf_hub_download = slow
    started: list[threading.Thread] = []
    real_start = threading.Thread.start

    def start(self, *args, **kw):  # the executor registers the thread only after start() returns
        real_start(self, *args, **kw)
        if self.name.startswith("hub-get-download") and not started:
            started.append(self)
            os.kill(os.getpid(), signal.SIGINT)
            _spin()

    monkeypatch.setattr(threading.Thread, "start", start)
    with pytest.raises(BaseException) as exc:
        hub_get.get(preset(tmp_path / "dest"), api=api, workers=1)
    assert started
    alive = started[0].is_alive()
    started[0].join()
    assert exc.type is KeyboardInterrupt, exc.value
    assert not alive  # a thread still writing into the staging folder whose lock was let go
    assert "rerun" in " ".join(getattr(exc.value, "__notes__", ()))


def test_a_ctrl_c_after_the_last_move_is_not_lost(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest = tmp_path / "dest"
    real = hub_get._move_held
    sent = []

    def move_held(*args, **kw):
        journal = real(*args, **kw)
        sent.append(1)
        os.kill(os.getpid(), signal.SIGINT)  # after the last check, before the handler is given back
        _spin()
        return journal

    monkeypatch.setattr(hub_get, "_move_held", move_held)
    with pytest.raises(BaseException) as exc:
        hub_get.get(preset(dest), api=PinnedHub(FILES))
    assert sent
    assert exc.type is KeyboardInterrupt, exc.value
    notes = " ".join(getattr(exc.value, "__notes__", ()))
    assert str(dest) in notes and "every file" in notes


def test_a_stopped_rollback_names_a_partial_copy_it_left(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest = tmp_path / "dest"
    real_unlink = os.unlink
    real_copy = shutil.copyfileobj

    def no_links(src, dst, *args, **kw):
        raise OSError(errno.EOPNOTSUPP, "no hard links on this disk")

    def partial(src, dst, *args, **kw):
        if not src.name.endswith("a.docx"):
            return real_copy(src, dst, *args, **kw)
        dst.write(b"REM")
        raise OSError(errno.ENOSPC, "disk full")

    def unlink(path, *args, **kw):
        if Path(path) == dest / "a.docx":
            raise OSError(errno.EIO, "unlink failed")
        return real_unlink(path, *args, **kw)

    real_stop = hub_get._CtrlC.stop_rollback
    sent = []

    def stop(self):  # two presses before the rollback's first step
        if not sent:
            sent.append(1)
            _press_twice()
        return real_stop(self)

    monkeypatch.setattr(os, "link", no_links)
    monkeypatch.setattr(shutil, "copyfileobj", partial)
    monkeypatch.setattr(os, "unlink", unlink)
    monkeypatch.setattr(hub_get._CtrlC, "stop_rollback", stop)
    with pytest.raises(BaseException) as exc:
        hub_get.get(preset(dest), api=PinnedHub(FILES))
    assert sent
    assert exc.type is KeyboardInterrupt, exc.value
    notes = " ".join(getattr(exc.value, "__notes__", ()))
    assert str(dest / "RUN.md") in notes
    assert str(dest / "a.docx") in notes and "partial copy" in notes


# Review round 8, mcode (#80)


@pytest.mark.parametrize("name", [".cache", ".CACHE", ".Cache/HuggingFace/download/x.metadata"])
def test_a_hub_file_where_the_downloads_records_go_refuses_before_downloading(tmp_path: Path, name: str) -> None:
    api = PinnedHub({"a.txt": b"a\n", name: b"x\n"})
    whole = hub_get.Preset(name="t", repo_id=REPO, path="", dest=tmp_path / "dest", about="test")
    with pytest.raises(hub_get.GetError, match="keeps its own records"):
        hub_get.get(whole, api=api)
    assert api.downloads() == []


# Review round 9, Codex (#80)


def _drop_kept_locks() -> None:
    """Let go of the locks kept for downloads left running; the run lets each go itself once they end."""
    with hub_get._LOCKS_GUARD:
        while hub_get._KEPT_LOCKS:
            hub_get._unlock(hub_get._KEPT_LOCKS.pop())  # whoever takes it off the list lets it go


def _held_by_another_run(staging: Path) -> bool:
    try:
        fd = hub_get._lock(staging)
    except hub_get.GetError:
        return True
    hub_get._unlock(fd)
    return False


class _Presses:
    """Ctrl-C presses sent to the main thread one at a time, each waiting until the run's handler saw it.

    Two presses sent before the handler runs can reach it as one: the kernel delivers a pending
    signal once, and CPython calls a Python handler once for every delivery it has not handled yet.
    A test of what a second press does must not depend on the scheduler keeping them apart.
    """

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import threading

        self.seen = 0
        self.cond = threading.Condition()
        self.main = threading.main_thread().ident
        real = hub_get._CtrlC.hold

        def hold(ctrl_c, signum, frame):
            real(ctrl_c, signum, frame)
            with self.cond:
                self.seen += 1
                self.cond.notify_all()

        monkeypatch.setattr(hub_get._CtrlC, "hold", hold)

    def press(self, timeout: float = 5.0) -> None:
        with self.cond:
            target = self.seen + 1
        signal.pthread_kill(self.main, signal.SIGINT)
        with self.cond:
            assert self.cond.wait_for(lambda: self.seen >= target, timeout), "the run's handler never saw the press"


def test_a_second_ctrl_c_stops_waiting_for_a_download_that_never_ends(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stalled request (the SDK's Xet token request has no timeout) must not make Ctrl-C wait forever.

    The second press stops waiting. The download left running ends with the process, which keeps the
    staging folder locked until then: no other run takes a folder a thread still writes into (round 8).
    """
    import threading
    import time

    dest = tmp_path / "dest"
    staging = hub_get.staging_dir(dest, SHA)
    api = _hub_of_slow_files()
    real_download = api.hf_hub_download
    presses = _Presses(monkeypatch)
    release = threading.Event()
    stalled: list[threading.Thread] = []
    calls: list[str] = []

    def stall(*args, **kw):
        calls.append(args[1])
        if not stalled:
            stalled.append(threading.current_thread())
            release.wait(6)  # a request that does not come back
        return real_download(*args, **kw)

    def press_twice() -> None:
        time.sleep(0.3)
        presses.press()
        time.sleep(0.5)
        presses.press()

    api.hf_hub_download = stall
    presser = threading.Thread(target=press_twice)
    presser.start()
    try:
        with pytest.raises(BaseException) as exc:
            hub_get.get(preset(dest), api=api, workers=1)
        fetched = len(calls)
        locked = _held_by_another_run(staging)
        running = bool(stalled) and stalled[0].is_alive()
    finally:
        release.set()
        presser.join()
        for t in stalled:
            t.join()
    assert exc.type is KeyboardInterrupt, exc.value
    assert fetched == 1  # only the stalled download started; the queued ones never did
    assert running and locked
    notes = " ".join(getattr(exc.value, "__notes__", ()))
    assert str(staging) in notes and "still running" in notes and "rerun" in notes
    _drop_kept_locks()


@pytest.mark.parametrize("how", ["include", "exclude"])
def test_a_hub_file_where_the_records_go_is_no_obstacle_when_the_run_does_not_fetch_it(
    tmp_path: Path, how: str
) -> None:
    api = PinnedHub({"a.txt": b"a\n", ".CACHE": b"x\n"})
    whole = hub_get.Preset(
        name="t", repo_id=REPO, path="", dest=tmp_path / "dest", about="test",
        exclude=(".CACHE",) if how == "exclude" else (),
    )
    hub_get.get(whole, api=api, include=("a.txt",) if how == "include" else ())
    assert _tree(tmp_path / "dest") == {"a.txt": b"a\n"}


# Review round 9, mcode (#80)


@pytest.mark.parametrize("where", ["staged", "dest"])
def test_ctrl_c_while_the_download_is_checked_says_nothing_moved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, where: str
) -> None:
    dest = tmp_path / "dest"
    staging = hub_get.staging_dir(dest, SHA)
    api = PinnedHub(FILES)
    if where == "dest":  # a local file appears with the hub's bytes while the files download
        real_download = api.hf_hub_download

        def appear(repo_id, filename, **kw):
            if filename.endswith("RUN.md"):
                _write(dest, {"RUN.md": FILES["outputs/run/RUN.md"]})
            return real_download(repo_id, filename, **kw)

        api.hf_hub_download = appear
    real_same = hub_get.same_bytes
    sent = []

    def same_bytes(path, f):
        if not sent and Path(path).is_relative_to(dest if where == "dest" else staging):
            sent.append(1)
            os.kill(os.getpid(), signal.SIGINT)
            _spin()
        return real_same(path, f)

    monkeypatch.setattr(hub_get, "same_bytes", same_bytes)
    with pytest.raises(BaseException) as exc:
        hub_get.get(preset(dest), api=api)
    assert sent
    assert exc.type is KeyboardInterrupt, exc.value
    notes = " ".join(getattr(exc.value, "__notes__", ()))
    assert str(staging) in notes and "rerun" in notes and "nothing moved" in notes
    assert _tree(dest) == ({"RUN.md": FILES["outputs/run/RUN.md"]} if where == "dest" else {}) or not dest.exists()


def test_a_ctrl_c_the_moment_the_handler_is_given_back_says_where_the_run_was(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "dest"
    real_signal = signal.signal
    sent = []

    def give_back(signum, handler):
        previous = real_signal(signum, handler)
        if signum == signal.SIGINT and handler is signal.default_int_handler and not sent:
            sent.append(1)
            os.kill(os.getpid(), signal.SIGINT)  # the instant Python's own handler is back
            _spin()
        return previous

    monkeypatch.setattr(signal, "signal", give_back)
    with pytest.raises(BaseException) as exc:
        hub_get.get(preset(dest), api=PinnedHub(FILES))
    assert sent
    assert exc.type is KeyboardInterrupt, exc.value
    notes = " ".join(getattr(exc.value, "__notes__", ()))
    assert str(dest) in notes
    # The handler is given back once, after the run's last step: the note says so, and it is true
    assert "every file is in place" in notes
    assert _tree(dest) == {k.removeprefix("outputs/run/"): v for k, v in FILES.items() if k.startswith("outputs/run/")}


# Review round 10, Codex (#80)


def test_two_presses_before_the_first_check_still_stop_waiting_for_a_stalled_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both presses land in one 0.25 s wait slice: the first stops the queue, the second the wait."""
    import threading
    import time

    dest = tmp_path / "dest"
    api = _hub_of_slow_files()
    real_download = api.hf_hub_download
    presses = _Presses(monkeypatch)
    release = threading.Event()
    stalled: list[threading.Thread] = []

    def stall(*args, **kw):
        if not stalled:
            stalled.append(threading.current_thread())
            time.sleep(0.1)  # the main thread is in its first wait slice
            presses.press()
            presses.press()  # seen by the handler before the slice ends: both are held at the check
            release.wait(6)  # a request that does not come back
        return real_download(*args, **kw)

    api.hf_hub_download = stall
    try:
        with pytest.raises(BaseException) as exc:
            hub_get.get(preset(dest), api=api, workers=1)
        running = bool(stalled) and stalled[0].is_alive()  # the run did not wait for it
    finally:
        release.set()
        for t in stalled:
            t.join()
    assert exc.type is KeyboardInterrupt, exc.value
    assert running
    assert "still running" in " ".join(getattr(exc.value, "__notes__", ()))
    _drop_kept_locks()


def test_a_press_the_moment_the_staging_lock_is_taken_lets_it_go_and_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "dest"
    staging = hub_get.staging_dir(dest, SHA)
    real_lock = hub_get._lock
    sent = []

    def lock(path):
        fd = real_lock(path)
        sent.append(fd)
        os.kill(os.getpid(), signal.SIGINT)  # after the lock is taken, before the run holds it in a try
        _spin()
        return fd

    monkeypatch.setattr(hub_get, "_lock", lock)
    with pytest.raises(BaseException) as exc:
        hub_get.get(preset(dest), api=PinnedHub(FILES))
    monkeypatch.setattr(hub_get, "_lock", real_lock)
    assert sent
    assert exc.type is KeyboardInterrupt, exc.value
    leaked = _held_by_another_run(staging)
    if leaked:
        hub_get._unlock(sent[0])
    assert not leaked
    notes = " ".join(getattr(exc.value, "__notes__", ()))
    assert str(dest) in notes


def test_a_download_that_raises_outside_exception_fails_the_run_even_with_a_good_staged_copy(
    tmp_path: Path,
) -> None:
    """A staged copy an earlier run left verifies, but this run's download of it never finished."""
    dest = tmp_path / "dest"
    staged = hub_get.staging_dir(dest, SHA) / hub_get.FILES / "outputs/run/RUN.md"
    staged.parent.mkdir(parents=True)
    staged.write_bytes(FILES["outputs/run/RUN.md"])
    api = PinnedHub(FILES)
    real_download = api.hf_hub_download

    def cancelled(repo_id, filename, **kw):
        if filename.endswith("RUN.md"):
            raise KeyboardInterrupt("download cancelled")
        return real_download(repo_id, filename, **kw)

    api.hf_hub_download = cancelled
    with pytest.raises(hub_get.GetError, match=r"RUN\.md"):
        hub_get.get(preset(dest), api=api)
    assert not dest.exists() or _tree(dest) == {}


# Review round 10, mcode (#80)


def test_a_press_as_the_staging_lock_is_let_go_says_every_file_is_in_place(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "dest"
    real_lock, real_close = hub_get._lock, os.close
    locks: list[int] = []
    sent = []

    def lock(path):
        locks.append(real_lock(path))
        return locks[-1]

    def close(fd):
        real_close(fd)
        if fd in locks and not sent:  # the run lets its staging lock go
            sent.append(fd)
            os.kill(os.getpid(), signal.SIGINT)
            _spin()

    monkeypatch.setattr(hub_get, "_lock", lock)
    monkeypatch.setattr(os, "close", close)
    with pytest.raises(BaseException) as exc:
        hub_get.get(preset(dest), api=PinnedHub(FILES))
    monkeypatch.setattr(os, "close", real_close)
    assert sent
    assert exc.type is KeyboardInterrupt, exc.value
    assert "every file is in place" in " ".join(getattr(exc.value, "__notes__", ()))
    assert _tree(dest) == {k.removeprefix("outputs/run/"): v for k, v in FILES.items() if k.startswith("outputs/run/")}


def test_the_lock_a_second_press_kept_goes_once_the_downloads_left_running_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A caller that catches the KeyboardInterrupt can run again here once those downloads are over."""
    import threading
    import time

    dest = tmp_path / "dest"
    staging = hub_get.staging_dir(dest, SHA)
    api = _hub_of_slow_files()
    real_download = api.hf_hub_download
    presses = _Presses(monkeypatch)
    release = threading.Event()
    stalled: list[threading.Thread] = []

    def stall(*args, **kw):
        if not stalled:
            stalled.append(threading.current_thread())
            release.wait(6)
        return real_download(*args, **kw)

    def press_twice() -> None:
        time.sleep(0.3)
        presses.press()
        time.sleep(0.5)
        presses.press()

    api.hf_hub_download = stall
    presser = threading.Thread(target=press_twice)
    presser.start()
    try:
        with pytest.raises(KeyboardInterrupt):
            hub_get.get(preset(dest), api=api, workers=1)
        with pytest.raises(hub_get.GetError) as busy:  # while the download left running still writes
            hub_get.get(preset(dest), api=api, workers=1)
    finally:
        release.set()
        presser.join()
        for t in stalled:
            t.join()
    assert "Ctrl-C" in str(busy.value)  # not only "another bench hub get"
    deadline = time.monotonic() + 3
    while _held_by_another_run(staging) and time.monotonic() < deadline:
        time.sleep(0.05)
    held = _held_by_another_run(staging)
    _drop_kept_locks()
    assert not held
    hub_get.get(preset(dest), api=api, workers=1)
    assert sorted(_tree(dest)) == ["f00.txt", "f01.txt", "f02.txt"]


def test_a_press_held_as_the_handler_is_given_back_is_raised_not_dropped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A press after the run's last check but before Python's handler is back is still held: raised then."""
    dest = tmp_path / "dest"
    real_signal = signal.signal
    sent = []

    def give_back(signum, handler):
        if signum == signal.SIGINT and handler is signal.default_int_handler and not sent:
            sent.append(1)
            os.kill(os.getpid(), signal.SIGINT)  # the run's hold still catches it
            _spin()
        return real_signal(signum, handler)

    monkeypatch.setattr(signal, "signal", give_back)
    with pytest.raises(BaseException) as exc:
        hub_get.get(preset(dest), api=PinnedHub(FILES))
    assert sent
    assert exc.type is KeyboardInterrupt, exc.value
    assert "every file is in place" in " ".join(getattr(exc.value, "__notes__", ()))


# Review round 11, Codex (#80)


@pytest.mark.parametrize("left_running", [False, True])
def test_a_child_forked_while_a_lock_is_held_does_not_keep_it_once_the_run_lets_go(
    tmp_path: Path, left_running: bool
) -> None:
    """A fork copies the lock's descriptor; letting go must unlock it, not only close this process's copy."""
    import threading
    import time
    import warnings

    staging = tmp_path / ".dest.hub-aaaaaaaaaaaa"
    lock = hub_get._lock(staging)
    release = threading.Event()
    running = [threading.Thread(target=release.wait, args=(5,), daemon=True)] if left_running else []
    for t in running:
        t.start()
    r, w = os.pipe()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)  # a fork with threads alive, as the finding has it
        pid = os.fork()
    if pid == 0:  # the child: holds its copies until told to go
        os.close(w)
        os.read(r, 1)
        os._exit(0)
    os.close(r)
    try:
        hub_get._let_go(lock, running)
        release.set()
        for t in running:
            t.join()
        deadline = time.monotonic() + 3  # round 12: wait on the lock itself, not on the list
        held = _held_by_another_run(staging)
        while held and time.monotonic() < deadline:
            time.sleep(0.02)
            held = _held_by_another_run(staging)
    finally:
        os.write(w, b"x")
        os.close(w)
        os.waitpid(pid, 0)
        _drop_kept_locks()
    assert not held


# Review round 11, mcode (#80)


def test_a_file_whose_download_failed_over_a_bad_staged_copy_is_counted_once(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    staged = hub_get.staging_dir(dest, SHA) / hub_get.FILES / "outputs/run/RUN.md"
    staged.parent.mkdir(parents=True)
    staged.write_bytes(b"left by an earlier run, not the hub's bytes\n")
    api = PinnedHub(FILES)
    real_download = api.hf_hub_download

    def reset(repo_id, filename, **kw):
        if filename.endswith("RUN.md"):
            raise OSError("connection reset")
        return real_download(repo_id, filename, **kw)

    api.hf_hub_download = reset
    with pytest.raises(hub_get.GetError) as exc:
        hub_get.get(preset(dest), api=api)
    message = str(exc.value)
    assert message.count("RUN.md") == 1, message
    assert "1 failed to download" in message and "do not hash" not in message
    assert not staged.exists()  # a rerun fetches it again


# Review round 12 (#80)


def test_a_child_forked_from_a_run_does_not_hold_its_lock_once_the_runs_process_exits(tmp_path: Path) -> None:
    """Codex, round 12: exit closes the owner's descriptor, not a forked child's copy, which shares the lock
    (flock(2)); the note promises the staging folder is free once the process that ran it exits."""
    import subprocess
    import sys
    import textwrap

    staging = tmp_path / ".dest.hub-aaaaaaaaaaaa"
    script = textwrap.dedent(
        """
        import os, sys, threading, warnings
        from pathlib import Path
        from neurotic_docx_bench import hub_get

        go, ready = int(sys.argv[2]), int(sys.argv[3])
        lock = hub_get._lock(Path(sys.argv[1]))
        stalled = threading.Thread(target=threading.Event().wait, daemon=True)  # a download that never ends
        stalled.start()
        hub_get._let_go(lock, [stalled])
        warnings.simplefilter("ignore", DeprecationWarning)  # a fork with threads alive
        if os.fork() == 0:  # the child outlives the run's process
            os.write(ready, b"r")
            os.read(go, 1)
            os._exit(0)
        os._exit(0)  # the run's process exits, its download still running
        """
    )
    go_r, go_w = os.pipe()
    ready_r, ready_w = os.pipe()
    try:
        owner = subprocess.run(
            [sys.executable, "-c", script, str(staging), str(go_r), str(ready_w)],
            pass_fds=(go_r, ready_w),
            timeout=60,
        )
        os.close(ready_w)
        ready_w = -1
        assert owner.returncode == 0
        assert os.read(ready_r, 1) == b"r"  # the child is alive, past the fork
        held = _held_by_another_run(staging)
    finally:
        os.write(go_w, b"x")
        for fd in (go_r, go_w, ready_r, ready_w):
            if fd >= 0:
                os.close(fd)
    assert not held


def test_a_run_meeting_a_kept_lock_as_it_is_let_go_never_blames_another_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """mcode, round 12: the helper took the lock off the kept list before unlocking it, so a run in the same
    process that met the lock in between was told another bench hub get held it."""
    import threading

    staging = tmp_path / ".dest.hub-aaaaaaaaaaaa"
    lock = hub_get._lock(staging)
    real_unlock = hub_get._unlock
    reached, go = threading.Event(), threading.Event()

    def unlock_when_told(fd: int) -> None:
        if fd == lock:
            reached.set()
            go.wait(5)
        real_unlock(fd)

    monkeypatch.setattr(hub_get, "_unlock", unlock_when_told)
    ended = threading.Thread(target=lambda: None)
    ended.start()
    ended.join()
    hub_get._let_go(lock, [ended])  # kept, and let go at once by its helper, which stops before unlocking
    assert reached.wait(5)
    outcome: list = []

    def take() -> None:
        try:
            outcome.append(hub_get._lock(staging))
        except hub_get.GetError as exc:
            outcome.append(exc)

    taker = threading.Thread(target=take)
    taker.start()
    taker.join(0.3)
    go.set()
    taker.join(5)
    (got,) = outcome
    assert isinstance(got, int), got
    real_unlock(got)


# chatgpt-codex-connector, after round 11 (#80)


def test_a_file_and_a_folder_whose_names_fold_together_refuse_before_downloading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """On a disk that folds case, a file ``Sub`` and a file ``sub/b.pdf`` need ``sub`` to be a file and a folder."""
    monkeypatch.setattr(hub_get, "case_insensitive", lambda path: True)
    api = PinnedHub({**FILES, "outputs/run/Sub": b"a file where sub/ is a folder\n"})
    with pytest.raises(Exception) as exc:
        hub_get.get(preset(tmp_path / "dest"), api=api)
    assert type(exc.value) is hub_get.GetError, exc.value
    assert re.search(r"Sub.*sub/|sub/.*Sub", str(exc.value)), exc.value
    assert api.downloads() == []


def test_two_folders_whose_names_fold_together_are_one_folder_and_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A guard: ``Sub/x.md`` and ``sub/b.pdf`` share one folder on such a disk, and no file is lost."""
    monkeypatch.setattr(hub_get, "case_insensitive", lambda path: True)
    files = {**FILES, "outputs/run/Sub/x.md": b"x\n"}
    report = hub_get.get(preset(tmp_path / "dest"), api=PinnedHub(files), dest=tmp_path / "dest")
    assert report.downloaded == 4


def test_a_disk_without_hard_links_needs_room_for_the_copies_too(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """There ``place`` copies, and the staged files stay until the last one is in place: twice the bytes."""
    total = sum(len(b) for k, b in FILES.items() if k.startswith("outputs/run/"))
    monkeypatch.setattr(hub_get, "free_bytes", lambda path: total + total // 2)  # one copy fits, two do not

    def no_links(src, dst, *a, **kw):
        raise OSError(errno.EPERM, "Operation not permitted")

    monkeypatch.setattr(os, "link", no_links)
    api = PinnedHub(FILES)
    with pytest.raises(Exception) as exc:
        hub_get.get(preset(tmp_path / "d"), api=api)
    assert type(exc.value) is hub_get.GetError and "disk" in str(exc.value), exc.value
    assert api.downloads() == []


def test_a_staged_file_of_the_wrong_size_counts_for_no_room(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A partial left in staging is fetched again, so the room it seemed to save is needed after all."""
    dest = tmp_path / "dest"
    staged = hub_get.staging_dir(dest, SHA) / hub_get.FILES / "outputs/run/a.docx"
    staged.parent.mkdir(parents=True)
    staged.write_bytes(b"")
    total = sum(len(b) for k, b in FILES.items() if k.startswith("outputs/run/"))
    monkeypatch.setattr(hub_get, "free_bytes", lambda path: total - len(BIG) + 1)  # all but a.docx fits
    api = PinnedHub(FILES)
    with pytest.raises(Exception) as exc:
        hub_get.get(preset(dest), api=api)
    assert type(exc.value) is hub_get.GetError and "free on the disk" in str(exc.value), exc.value
    assert api.downloads() == []


def test_ctrl_c_during_the_moves_stays_a_ctrl_c_when_the_rollback_leaves_a_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The rollback's problems go into the note; the run still ends as a Ctrl-C (exit 130), not as a refusal."""
    dest = tmp_path / "dest"
    real_place, real_replace, real_link, real_rename = hub_get.place, os.replace, os.link, os.rename
    sent: list[Path] = []

    def pressed(staged, target):
        placed = real_place(staged, target)
        if not sent:
            sent.append(Path(target))
            os.kill(os.getpid(), signal.SIGINT)  # held until this move is recorded
            _spin()
        return placed

    def refuse(src) -> None:
        if sent and Path(src) == sent[0]:
            raise OSError(errno.EIO, f"{sent[0].name} cannot be moved back")

    def replace(src, dst, *a, **kw):
        refuse(src)
        return real_replace(src, dst, *a, **kw)

    def link(src, dst, *a, **kw):
        refuse(src)
        return real_link(src, dst, *a, **kw)

    def rename(src, dst, *a, **kw):
        refuse(src)
        return real_rename(src, dst, *a, **kw)

    monkeypatch.setattr(hub_get, "place", pressed)
    monkeypatch.setattr(os, "replace", replace)
    monkeypatch.setattr(os, "link", link)
    monkeypatch.setattr(os, "rename", rename)
    with pytest.raises(BaseException) as exc:
        hub_get.get(preset(dest), api=PinnedHub(FILES))
    assert sent
    assert exc.type is KeyboardInterrupt, exc.value
    assert "cannot be moved back" in " ".join(getattr(exc.value, "__notes__", ()))


def test_no_queued_download_starts_once_ctrl_c_stopped_the_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A worker that saw no stop, then waited for the queue while Ctrl-C stopped the run, must not take a file."""
    import threading
    import types

    first = threading.Event()

    class Stale(threading.Event):
        def is_set(self) -> bool:
            was = super().is_set()
            if not was and first.is_set() and threading.current_thread().name.startswith("hub-get-download"):
                self.wait(5)  # descheduled between its look at the flag and the queue, while the press lands
            return was

    proxy = types.SimpleNamespace(**{k: getattr(threading, k) for k in dir(threading) if not k.startswith("__")})
    proxy.Event = Stale
    monkeypatch.setattr(hub_get, "threading", proxy)
    api = PinnedHub(FILES)
    real_download = api.hf_hub_download

    def download(*args, **kw):
        got = real_download(*args, **kw)
        if not first.is_set():
            first.set()
            os.kill(os.getpid(), signal.SIGINT)
        return got

    api.hf_hub_download = download
    with pytest.raises(BaseException) as exc:
        hub_get.get(preset(tmp_path / "dest"), api=api, workers=1)
    assert exc.type is KeyboardInterrupt, exc.value
    assert len(api.downloads()) == 1, api.downloads()
