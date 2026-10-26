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
    # a dataset card is not the checkout's README
    assert "README.md" in hub_get.PRESETS["corpus"].exclude
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


def test_a_failure_after_the_link_restores_the_replaced_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    with pytest.raises(hub_get.GetError, match="cannot be removed"):
        hub_get.get(preset(dest), api=PinnedHub(FILES), on_conflict="overwrite")
    assert failed
    assert (dest / "RUN.md").read_bytes() == b"ORIGINAL\n"
    assert sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*")) == ["RUN.md"]


def test_one_rollback_error_does_not_stop_the_others(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest = tmp_path / "dest"
    real_place, real_replace = hub_get.place, os.replace

    def flaky(staged, target):
        if target.name == "b.pdf":
            raise OSError("disk went away")
        return real_place(staged, target)

    def replace(src, dst, *args, **kw):
        if Path(src) == dest / "a.docx":
            raise OSError(errno.EIO, "a.docx cannot be moved back")
        return real_replace(src, dst, *args, **kw)

    monkeypatch.setattr(hub_get, "place", flaky)
    monkeypatch.setattr(os, "replace", replace)
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
