"""Ready-made downloads of what the bench keeps on the Hugging Face hub (issue #79).

``bench hub list`` prints the presets below; ``bench hub get <preset>`` downloads one, and
``bench hub get --repo R --path P --dest D`` anything else. Every download follows four rules:

1. **Pinned.** The revision (default ``main``) is resolved to a commit with ``repo_info`` once;
   the tree listing and every file download read that commit. ``hf_hub_download`` with a branch
   name can serve a stale cached snapshot when its HEAD request fails; a commit cannot be stale.
2. **Verified against the hub's own hashes.** Each downloaded file is compared with the hub's
   record of it at that commit: ``lfs.sha256`` for LFS files, the git blob sha1 for inline ones
   (the check ``hub.verify_uploaded`` makes after an upload). One mismatch or missing file
   refuses the whole download.
3. **Never clobbers.** A file already at the destination with the same bytes is skipped. One
   with different bytes stops the run before anything is downloaded, unless ``on_conflict`` is
   ``overwrite`` (take the hub's) or ``keep-local`` (keep yours, fetch the rest). The destination
   is looked at again after the download, and each file is placed with a hard link that fails on
   an existing file (on a disk without hard links, a copy into a file created with ``O_EXCL``), so
   one written meanwhile is never overwritten either.
4. **Staged, all or nothing.** Files land in ``files/`` of a staging folder on the destination's
   disk (beside it, or inside it when it is a mount or a link to another disk), locked for the run,
   refused if it holds a symlink; a staged file with a second name (a hard link) is fetched again,
   never written into. Files go into place only once all of them verified, each as a second name
   of its staged copy; the staged copies are removed only after the last one is in place. A failed
   or interrupted (Ctrl-C) move withdraws every file already placed and restores every file
   ``overwrite`` replaced, except a file someone else changed after this run placed it, which
   stays; the error names each such file and where the one it replaced is kept. On success the run
   removes what it put in the staging folder and nothing else; on failure the folder is kept (minus
   the files that failed to verify), so a rerun resumes. A rerun also takes the second name off
   any staged file that is one of the destination's files (what a killed move leaves), and names
   the local files an earlier run replaced and left in the staging folder.

Names that one file would have to hold on the destination's disk (``A.txt`` and ``a.txt`` on
case-insensitive APFS), a local file where the hub has a folder, a symlinked folder below the
destination (it would put files, or move replaced ones, outside it), and a destination that is or
holds the staging folder refuse before any download. The folders are looked at again before each
file is moved; one swapped for a symlink in the instant between that look and the move is not
caught. The command runs with your rights in your own folders: it guards against accidents and
other runs, not against a process of yours racing it.

The hub's own ``.gitattributes`` (in any case: APFS treats ``.GITATTRIBUTES`` as the same name) is
never downloaded: under ``corpus/`` it would change how git treats the checkout. A hub folder named
like ``hf_hub_download``'s records of another file (``<file>.metadata/``, ``<file>.lock/``) refuses
before any download, since the two cannot share a staging folder.

``overwrite`` replaces only regular files: a local file that is a symlink refuses before any
download, and one that becomes a symlink meanwhile stops the run before anything moves.

Ctrl-C while files move is held until the step in hand is recorded, then rolls everything back; a
second press stops at once. A press during the rollback lets it finish and then stops; a second one
stops it where it is, and the error names the staging folder that holds what was not put back.
Ctrl-C is held only under Python's own handler in the main thread, so a caller that ignores it or
handles it itself keeps that. A run with nothing to download only tidies a staging folder an earlier
run left, and leaves it alone when another run holds it or anything in it is out of place; either
way it names the local files an earlier run replaced and left there.
"""

from __future__ import annotations

import fcntl
import fnmatch
import os
import re
import shutil
import signal
import stat
import tempfile
import threading
import unicodedata
from collections.abc import Iterable, Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from neurotic_docx_bench import hub

ARCHIVE_REPO = "arthrod/neurotic_docx_bench-git-archive"
BRANCH = "main"
CONFLICT_POLICIES = ("refuse", "overwrite", "keep-local")
DOWNLOADS = Path("hub-downloads")  # git-ignored; for what has no home in the checkout
_COMMIT = re.compile(r"[0-9a-f]{40}")
_NEVER = {".gitattributes"}
_LISTED = 20


class GetError(Exception):
    """A download was refused; nothing was moved into the destination."""


class _Busy(GetError):
    """Another run holds the staging folder's lock."""


class _LeftBehind(GetError):
    """``place`` created its target but could not tell it from a file someone else put there, so it stays."""


@dataclass(frozen=True)
class Preset:
    name: str
    repo_id: str
    path: str  # folder in the repo, "" for the whole repo
    dest: Path  # relative to the checkout unless given otherwise
    about: str
    exclude: tuple[str, ...] = ()  # globs relative to ``path``


def _cohort(name: str, about: str) -> Preset:
    return Preset(name, hub.RESULTS_REPO, f"r2-mirror/{name}", DOWNLOADS / "r2-mirror" / name, about)


PRESETS: dict[str, Preset] = {
    p.name: p
    for p in (
        Preset(
            "corpus",
            hub.FIXTURES_REPO,
            "",
            hub.DEFAULT_CORPUS,
            "the whole corpus: documents, Word's PDFs and compares, LibreOffice renders, probes, holdout",
        ),
        Preset("corpus-word", hub.FIXTURES_REPO, hub.WORD_CORPUS, hub.DEFAULT_CORPUS / hub.WORD_CORPUS,
               "corpus/word: the documents, Word's PDFs, compares and accept/reject, the tables"),
        Preset("corpus-libreoffice", hub.FIXTURES_REPO, "libreoffice", hub.DEFAULT_CORPUS / "libreoffice",
               "LibreOffice 26.2.4.2 renders filed under Word's stems (the soffice oracle)"),
        Preset(
            "redlines-0929",
            hub.RESULTS_REPO,
            "outputs/redlines_0929_full",
            Path("results/redlines_0929_full"),
            "the 0929 run: every tool's redlines, Word's PDFs and accept/reject of them, scores",
            exclude=("fresh_compares/*",),  # compare-regen
        ),
        Preset("compare-regen", hub.RESULTS_REPO, hub.FRESH_COMPARES, hub.DEFAULT_COMPARE_REGEN / "out",
               "Word's fresh compares of the 0929 run (scripts/fetch_corpus.py also writes regen_list.csv)"),
        Preset("release-0.13.0-evidence", hub.RESULTS_REPO, "outputs/release_0.13.0_evidence",
               DOWNLOADS / "release_0.13.0_evidence",
               "jubarte 0.13.0 release evidence: conversion work and the soffice sample"),
        Preset("local-extras-20261025", hub.RESULTS_REPO, "outputs/local_extras_20261025",
               DOWNLOADS / "local_extras_20261025",
               "37 docxodus redlines remade for the 0.13.0 evidence, not the run's canonical outputs"),
        _cohort("wordcraft-20261014", "the 2026-10-14 Wordcraft 400+400 cohort as it is on R2"),
        _cohort("wordcraft-20261014-initial", "the cohort's first pass, before the fresh rerun"),
        _cohort("word-driver-ab", "the 2026-10-14 Word driver A/B runs"),
        _cohort("word-driver-smoke", "the 2026-10-14 Word driver smoke runs"),
        _cohort("jubarte-release", "the jubarte release compare-regen objects"),
        Preset("site-mirror", hub.RESULTS_REPO, "site", DOWNLOADS / "site",
               "the review website's R2 objects: page-image tars and the convert/redline viewers"),
        Preset("dataset-tables", hub.RESULTS_REPO, "data", DOWNLOADS / "data",
               "the results dataset's parquet tables (runs, scores, files, site cases)"),
        Preset("git-archive", ARCHIVE_REPO, "", DOWNLOADS / "git-archive",
               "private: bundles of every pre-rewrite git history and the filter-repo maps; needs HF_TOKEN"),
    )
}


@dataclass(frozen=True)
class RemoteFile:
    rel: str  # relative to the preset's path, i.e. to the destination
    repo_path: str
    size: int
    sha256: str | None  # LFS files
    blob_id: str | None  # inline files


@dataclass(frozen=True)
class GetReport:
    repo_id: str
    revision: str
    dest: Path
    n_files: int
    n_bytes: int
    to_download: int
    downloaded: int
    skipped: int
    replaced: int
    kept_local: tuple[str, ...]
    dry_run: bool
    to_download_bytes: int = 0
    conflicts: tuple[str, ...] = field(default=())
    earlier_replaced: tuple[str, ...] = field(default=())  # local files an earlier run replaced and left
    on_conflict: str = "refuse"

    def describe(self) -> str:
        head = f"{self.repo_id}@{self.revision[:12]} → {self.dest}: {self.n_files} files ({human(self.n_bytes)})"
        if self.dry_run:
            dry = (f"dry run: {head}; would download {self.to_download} ({human(self.to_download_bytes)}), "
                   f"{self.skipped} already there, {len(self.conflicts)} differ locally")
            if self.conflicts and self.on_conflict == "refuse":
                dry += "; a real run would refuse: rerun with --overwrite or --keep-local"
            return dry
        done = (f"{head}; downloaded {self.downloaded}, already there {self.skipped}, "
                f"replaced {self.replaced}, kept local {len(self.kept_local)}; every file verified")
        if self.earlier_replaced:
            done += (f". {len(self.earlier_replaced)} local file(s) an earlier run replaced and could not put back "
                     f"are still kept: {_listing(self.earlier_replaced)}")
        return done


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1000 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1000
    raise AssertionError


def free_bytes(path: Path) -> int:
    path = Path(path).absolute()
    while not path.exists():
        path = path.parent
    return shutil.disk_usage(path).free


LOCK = ".lock"  # held while a run uses its staging folder
FILES = "files"  # inside staging: hf_hub_download's local_dir, so no hub path can land on LOCK or _BACKUP
_BACKUP = ".replaced"  # inside staging: the local files --overwrite moved aside, until every move succeeded
_HF_BOOKKEEPING = (".cache", "huggingface")  # what hf_hub_download(local_dir=) writes beside the files
_CHUNK = 1 << 20


def device(path: Path) -> int:
    path = Path(path).absolute()
    while not path.exists():
        path = path.parent
    return os.stat(path).st_dev


def case_insensitive(path: Path) -> bool:
    """Whether the disk holding ``path`` treats names that differ only by case as one (APFS's default).

    Decided without writing: a folder on the way, on the same disk as its parent, is looked up under
    its name in the other case. With no such folder the answer is yes, the one that refuses more.
    """
    path = Path(path).absolute()
    while not path.is_dir():
        path = path.parent
    disk = os.stat(path).st_dev
    for folder in (path, *path.parents):
        if folder == folder.parent or os.stat(folder.parent).st_dev != disk:
            break
        other = folder.parent / folder.name.swapcase()
        if other.name != folder.name:
            try:
                return os.path.samefile(other, folder)
            except OSError:  # no such name: the disk tells the cases apart
                return False
    return True


Identity = tuple[int, int, int, int]


def identity(st: os.stat_result) -> Identity:
    """Which file, and which version of it: a file someone replaced or rewrote no longer matches."""
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)


def _identity_at(path: Path) -> Identity | None:
    try:
        return identity(os.lstat(path))
    except FileNotFoundError:
        return None


def _copy_new(staged: Path, target: Path) -> Identity:
    """Copy ``staged`` into a new file at ``target`` that only this call can have created; its identity.

    The copy gets the mode and times of ``staged``, as a hard link would (a restored file keeps them).
    """
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise GetError(f"{target} appeared while files were being moved into place") from exc
    try:
        made = os.fstat(fd)
    except OSError as exc:
        os.close(fd)
        raise _LeftBehind(
            f"{target} was created empty, but the disk would not say which file it is ({exc}), so it stays: "
            "remove it before a rerun"
        ) from exc
    except BaseException:
        os.close(fd)
        raise
    try:
        with open(fd, "wb") as out, open(staged, "rb") as src:
            shutil.copyfileobj(src, out, _CHUNK)
            out.flush()
            was = os.fstat(src.fileno())
            os.fchmod(out.fileno(), stat.S_IMODE(was.st_mode))
            os.utime(out.fileno(), ns=(was.st_atime_ns, was.st_mtime_ns))
            return identity(os.fstat(out.fileno()))
    except BaseException as exc:
        try:
            now = _identity_at(target)
            if now is not None and now[:2] == (made.st_dev, made.st_ino):  # still this call's half-made copy
                os.unlink(target)
        except OSError as stuck:
            raise _LeftBehind(
                f"{target} holds a partial copy this run could not remove ({stuck}), so it stays: "
                "remove it before a rerun"
            ) from exc
        raise


def place(staged: Path, target: Path) -> Identity:
    """Give ``target`` the bytes of ``staged`` without ever overwriting a file there; the new file's identity.

    A hard link, or on a disk without them a copy into a file only this call can have created.
    ``staged`` keeps its name: it is removed once every file of the run is in place, so a rollback
    only has to withdraw ``target`` and a rerun still finds the bytes.
    """
    placed = identity(os.lstat(staged))  # before the link, which changes neither inode, size nor mtime
    try:
        os.link(staged, target)  # fails on an existing target, even one written a moment ago
    except FileExistsError as exc:
        raise GetError(f"{target} appeared while files were being moved into place") from exc
    except OSError:  # a disk without hard links
        return _copy_new(staged, target)
    return placed


def _withdraw(target: Path, placed: Identity, staging: Path) -> str | None:
    """Remove the file this run placed at ``target``; None, or why something stays there.

    The file is renamed to a fresh private name before it is looked at, so one that someone else
    put there in the meantime is never deleted: it is given back with ``place``.
    """
    if _identity_at(target) != placed:
        return f"{target} changed after this run moved it there; left as it is"
    hold = Path(tempfile.mkdtemp(prefix=".withdrawn-", dir=staging)) / "file"
    os.rename(target, hold)  # a fresh name in a fresh folder: nothing there to overwrite
    if _identity_at(hold) != placed:  # replaced in the instant between the look and the rename
        try:
            place(hold, target)
        except GetError:
            return f"{target} changed while this run took it back; that file is now at {hold}"
        os.unlink(hold)
        hold.parent.rmdir()
        return f"{target} changed after this run moved it there; left as it is"
    os.unlink(hold)
    hold.parent.rmdir()
    return None


def staging_dir(dest: Path, revision: str) -> Path:
    """Beside ``dest``, or inside it when ``dest`` is on another disk than its parent (a mount, a link)."""
    dest = Path(dest)
    name = f"hub-{revision[:12]}"
    if dest.is_dir() and device(dest) != device(dest.absolute().parent):
        return dest / f".{name}"
    return dest.parent / f".{dest.name}.{name}"


def resolve_revision(api: Any, repo_id: str, revision: str | None = None) -> str:
    rev = revision or BRANCH
    try:
        info = api.repo_info(repo_id, repo_type=hub.REPO_TYPE, revision=rev)
    except Exception as exc:  # the hub's errors carry the reason; a private repo needs a token
        raise GetError(f"{repo_id}@{rev}: {exc} (a private repo needs HF_TOKEN or `hf auth login`)") from exc
    sha = getattr(info, "sha", None)
    if not isinstance(sha, str) or not _COMMIT.fullmatch(sha):
        raise GetError(f"{repo_id}@{rev} did not resolve to a commit (got {sha!r})")
    return sha


def _matches(rel: str, globs: Iterable[str]) -> bool:
    """fnmatch, so ``*`` also matches ``/``: ``*.docx`` takes ``sub/a.docx`` too, and ``fresh_compares/*``
    the whole folder."""
    return any(fnmatch.fnmatchcase(rel, g) for g in globs)


def remote_files(
    api: Any,
    repo_id: str,
    revision: str,
    path: str,
    include: Sequence[str] = (),
    exclude: Sequence[str] = (),
) -> list[RemoteFile]:
    """The files under ``path`` at ``revision``, filtered by globs relative to ``path``."""
    prefix = f"{path}/" if path else ""
    files = []
    try:  # every page, before any is used: a missing folder or a failed page refuses with the hub's reason
        entries = list(api.list_repo_tree(
            repo_id, repo_type=hub.REPO_TYPE, path_in_repo=path or None, recursive=True, expand=False,
            revision=revision,
        ))
    except Exception as exc:
        raise GetError(f"{repo_id}@{revision[:12]}: cannot list {path or '/'}: {exc}") from exc
    for entry in entries:
        if not hasattr(entry, "blob_id"):  # a folder
            continue
        repo_path = str(entry.path)
        if not repo_path.startswith(prefix):
            raise GetError(f"the hub listed {repo_path} under {path}")
        rel = repo_path[len(prefix):]
        parts = PurePosixPath(rel).parts
        if not parts or ".." in parts or PurePosixPath(rel).is_absolute():
            raise GetError(f"refusing a hub path that leaves the destination: {repo_path}")
        if PurePosixPath(repo_path).parts[:2] == _HF_BOOKKEEPING:
            raise GetError(f"refusing {repo_path}: hf_hub_download keeps its own records in {'/'.join(_HF_BOOKKEEPING)}")
        if parts[-1].casefold() in _NEVER or (include and not _matches(rel, include)) or _matches(rel, exclude):
            continue
        lfs = getattr(entry, "lfs", None)
        sha256 = (lfs.get("sha256") if isinstance(lfs, dict) else getattr(lfs, "sha256", None)) if lfs else None
        blob_id = None if sha256 else getattr(entry, "blob_id", None)
        if not sha256 and not blob_id:
            raise GetError(f"the hub gave no hash for {repo_path}")
        files.append(RemoteFile(rel, repo_path, int(entry.size), sha256, blob_id))
    return sorted(files, key=lambda f: f.rel)


def same_bytes(path: Path, f: RemoteFile) -> bool:
    if path.stat().st_size != f.size:
        return False
    if f.sha256:
        return hub.sha256_file(path) == f.sha256
    return hub.git_blob_sha1(path) == f.blob_id


def _listing(rels: Sequence[str]) -> str:
    more = f" and {len(rels) - _LISTED} more" if len(rels) > _LISTED else ""
    return ", ".join(rels[:_LISTED]) + more


def _blocker(dest: Path, rel: str) -> str | None:
    """Why ``rel`` cannot go under ``dest``: ``dest`` or a folder above ``rel`` exists but is not a folder,
    or a folder below ``dest`` is a symlink (it would put the file, or move a replaced one, outside ``dest``).
    ``dest`` itself may be a symlink."""
    if (dest.exists() or dest.is_symlink()) and not dest.is_dir():
        return f"{dest} is a file where the hub has a folder"
    path = dest
    for part in PurePosixPath(rel).parts[:-1]:
        path = path / part
        if path.is_symlink():
            return f"{path} is a symlink, and files only go into real folders below {dest}"
        if path.exists() and not path.is_dir():
            return f"{path} is a file where the hub has a folder"
    return None


def _collisions(files: Sequence[RemoteFile], dest: Path) -> list[list[str]]:
    """Hub names that one file on the destination's disk would have to hold."""
    def groups(key) -> list[list[str]]:
        seen: dict[str, list[str]] = {}
        for f in files:
            seen.setdefault(key(f.rel), []).append(f.rel)
        return [names for names in seen.values() if len(names) > 1]

    normalized = groups(lambda rel: unicodedata.normalize("NFC", rel))
    folded = groups(lambda rel: unicodedata.normalize("NFC", rel).casefold())
    return folded if folded and case_insensitive(dest) else normalized


def _below(path: Path, folder: Path) -> tuple[str, ...] | None:
    """The parts of ``path`` below ``folder`` when, on disk, ``path`` is ``folder`` or inside it; else None.

    Folders are compared by device and inode, so a symlink, ``..`` or a name in the other case
    (case-insensitive APFS) does not hide the overlap.
    """
    try:
        target = os.stat(folder)
    except FileNotFoundError:
        return None
    path = path.resolve()
    for depth, above in enumerate((path, *path.parents)):
        try:
            st = os.stat(above)
        except FileNotFoundError:
            continue
        if (st.st_dev, st.st_ino) == (target.st_dev, target.st_ino):
            return path.parts[len(path.parts) - depth:]
    return None


def _fold(parts: Sequence[str]) -> tuple[str, ...]:
    return tuple(unicodedata.normalize("NFC", p).casefold() for p in parts)


def _overlap(staging: Path, dest: Path, files: Sequence[RemoteFile]) -> str | None:
    """Why ``staging`` and ``dest`` would share files: ``dest`` is in the staging folder, or hub files would
    land in it. The cleanup removes staged copies by name, so either would delete files of ``dest``."""
    if _below(dest, staging) is not None:
        return f"{dest} is the staging folder {staging} or inside it"
    inside = _below(staging, dest)
    if inside is not None:
        clash = [f.rel for f in files if _fold(PurePosixPath(f.rel).parts[: len(inside)]) == _fold(inside)]
        if clash:
            return f"{_listing(clash)} would land in the staging folder {staging}"
    return None


def _lock(staging: Path) -> int:
    """An exclusive lock on ``staging``'s lock file, held until the returned descriptor is closed.

    A run that finishes removes the lock file while it holds the lock, so a lock taken on a file no
    longer at the lock path is let go and taken again on the file that is there now.
    """
    while True:
        try:
            staging.mkdir(parents=True, exist_ok=True)  # a run that just finished may have removed it
            fd = os.open(staging / LOCK, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o666)
        except FileNotFoundError:
            continue
        except OSError as exc:  # a symlink at the lock path, a file at the staging path, among others
            raise GetError(f"cannot take the lock {staging / LOCK}: {exc}") from exc
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            mine, now = os.fstat(fd), _identity_at(staging / LOCK)
        except BlockingIOError as exc:
            os.close(fd)
            raise _Busy(f"another bench hub get is using {staging}; wait for it to finish") from exc
        except OSError as exc:  # a disk without locks, among others
            os.close(fd)
            raise GetError(f"cannot take the lock {staging / LOCK}: {exc}") from exc
        except BaseException:
            os.close(fd)
            raise
        if now is not None and now[:2] == (mine.st_dev, mine.st_ino):
            return fd
        os.close(fd)


def _record_clashes(files: Sequence[RemoteFile]) -> list[str]:
    """Hub folders where hf_hub_download keeps another file's records.

    It keeps the records of ``<path>`` at ``.cache/huggingface/download/<path>.metadata`` and
    ``<path>.lock`` (``huggingface_hub/_local_folder.py``, ``get_local_download_paths``), so a hub
    folder ``<path>.metadata/`` or ``<path>.lock/`` cannot be downloaded into the same folder.
    """
    folders: dict[tuple[str, ...], str] = {}
    for f in files:
        parts = PurePosixPath(f.repo_path).parts
        for i in range(1, len(parts)):
            folders.setdefault(_fold(parts[:i]), "/".join(parts[:i]))
    return [
        f"{f.repo_path} and {folders[key]}/"
        for f in files
        for suffix in (".metadata", ".lock")
        if (key := _fold(PurePosixPath(f.repo_path + suffix).parts)) in folders
    ]


class _CtrlC:
    """The Ctrl-C presses held while files move: ``check`` raises a held one, a second press raises at once."""

    def __init__(self) -> None:
        self.held: list[int] = []

    def hold(self, signum: int, _frame: object) -> None:
        if self.held:  # pressed again before the step in hand was recorded: stop now
            raise KeyboardInterrupt
        self.held.append(signum)

    def check(self) -> None:
        if self.held:
            self.held.clear()
            raise KeyboardInterrupt


@contextmanager
def _ctrl_c_between_steps() -> Iterator[_CtrlC]:
    """Hold Ctrl-C (SIGINT) while the block runs; the ``_CtrlC`` it yields raises a held one.

    A filesystem step and its journal entry then happen together: a Ctrl-C that lands as a rename
    or a link returns waits for the next check, so the rollback knows about that step. Ctrl-C is
    held only under Python's own handler, in the main thread: a caller that ignores Ctrl-C or
    handles it itself keeps that, and its ``check`` never raises.
    """
    ctrl_c = _CtrlC()
    previous = signal.getsignal(signal.SIGINT)
    if threading.current_thread() is not threading.main_thread() or previous is not signal.default_int_handler:
        yield ctrl_c
        return
    signal.signal(signal.SIGINT, ctrl_c.hold)
    try:
        yield ctrl_c
    finally:
        signal.signal(signal.SIGINT, previous)


def _earlier(staging: Path) -> tuple[str, ...]:
    """The local files an earlier run replaced and left in ``staging``; looked at, never followed or changed."""
    backups = staging / _BACKUP
    if staging.is_symlink() or backups.is_symlink() or not backups.is_dir():
        return ()
    found = []
    for root, dirs, names in os.walk(backups):  # lists a symlinked folder among ``dirs`` but does not enter it
        found += [str(Path(root) / n) for n in names]
        found += [str(Path(root) / d) for d in dirs if (Path(root) / d).is_symlink()]
    return tuple(sorted(found))


def _symlinks(staging: Path) -> list[Path]:
    if staging.is_symlink():
        return [staging]
    found = []
    for root, dirs, names in os.walk(staging):
        found += [Path(root) / n for n in (*dirs, *names) if (Path(root) / n).is_symlink()]
    return found


@dataclass
class _Move:
    target: Path
    src: Path
    backup: Path | None
    backed_up: bool = False
    placed: Identity | None = None


def _roll_back(journal: Sequence[_Move], staging: Path) -> list[str]:
    """Undo ``journal`` newest first, each move on its own; what could not be undone, and where its files are."""
    problems = []
    for m in reversed(journal):
        kept = f"; the file it replaced is kept at {m.backup}" if m.backed_up else ""
        try:
            if m.placed is not None:
                why = _withdraw(m.target, m.placed, staging)
                if why is not None:
                    problems.append(why + kept)
                    continue
            if m.backed_up:
                place(m.backup, m.target)
                m.backed_up = False
                m.backup.unlink()
        except (OSError, GetError) as exc:
            kept = f"; the file it replaced is kept at {m.backup}" if m.backed_up else ""
            problems.append(f"{m.target}: {exc}{kept}")
    return problems


def _prune(root: Path) -> None:
    """Remove the empty folders under ``root``, and ``root`` itself if it ends up empty."""
    for folder, _dirs, _names in sorted(os.walk(root), key=lambda w: -len(Path(w[0]).parts)):
        try:
            Path(folder).rmdir()
        except OSError:
            pass


def get(
    preset: Preset,
    *,
    api: hub.HubApi,
    revision: str | None = None,
    dest: Path | None = None,
    include: Sequence[str] = (),
    on_conflict: str = "refuse",
    dry_run: bool = False,
    workers: int = 8,
) -> GetReport:
    """Download ``preset`` into ``dest`` (default: the preset's) under the four rules above."""
    if on_conflict not in CONFLICT_POLICIES:
        raise ValueError(f"on_conflict must be one of {CONFLICT_POLICIES}, not {on_conflict!r}")
    dest = Path(dest if dest is not None else preset.dest)
    sha = resolve_revision(api, preset.repo_id, revision)
    files = remote_files(api, preset.repo_id, sha, preset.path, include, preset.exclude)
    where = f"{preset.repo_id}@{sha[:12]}"
    if not files:
        what = f" matching {', '.join(include)}" if include else ""
        raise GetError(f"{where} has nothing under {preset.path or '/'}{what}")
    for names in _collisions(files, dest):
        raise GetError(f"{where} has names that would be one file on the disk of {dest}: {', '.join(names)}")
    clashes = _record_clashes(files)
    if clashes:
        raise GetError(
            f"{where} has folders where hf_hub_download keeps the records of another file: {_listing(clashes)}; "
            "they cannot be downloaded into one folder"
        )

    todo: list[RemoteFile] = []
    skipped = 0
    conflicts: list[RemoteFile] = []
    for f in files:
        local = dest / f.rel
        blocker = _blocker(dest, f.rel)
        if blocker is not None:
            raise GetError(f"{blocker} (for {f.rel} of {where}); nothing downloaded")
        if not (local.exists() or local.is_symlink()):
            todo.append(f)
        elif not local.is_file():
            what = "a symlink to no file" if local.is_symlink() else "not a file"
            raise GetError(f"{local} is {what} but the hub has a file there; nothing downloaded")
        elif same_bytes(local, f):
            skipped += 1
        elif on_conflict == "overwrite" and local.is_symlink():
            raise GetError(
                f"{local} is a symlink; --overwrite replaces only regular files, never a link or what it points "
                "to. Nothing downloaded"
            )
        else:
            conflicts.append(f)
    differ = tuple(f.rel for f in conflicts)
    if conflicts and on_conflict == "refuse" and not dry_run:
        raise GetError(
            f"{len(conflicts)} file(s) in {dest} differ from {where}: {_listing(differ)}. Nothing was downloaded; "
            "rerun with --overwrite to take the hub's copies or --keep-local to keep yours and fetch the rest"
        )
    kept = list(differ) if on_conflict == "keep-local" else []
    if on_conflict == "overwrite":
        todo += conflicts
    todo.sort(key=lambda f: f.rel)
    report = dict(
        repo_id=preset.repo_id, revision=sha, dest=dest, n_files=len(files), n_bytes=sum(f.size for f in files),
        to_download=len(todo), to_download_bytes=sum(f.size for f in todo), conflicts=differ, on_conflict=on_conflict,
    )
    staging = staging_dir(dest, sha)
    # With nothing to download the run only tidies what an earlier run left, and is never refused for it.
    tidy = not todo
    plain = GetReport(
        **report, skipped=skipped, kept_local=tuple(kept), downloaded=0, replaced=0, dry_run=dry_run,
        earlier_replaced=_earlier(staging),
    )
    if dry_run or (tidy and not (staging.is_dir() and not staging.is_symlink())):
        return plain

    if staging.is_symlink():
        raise GetError(f"{staging} is a symlink; remove it and rerun")
    if staging.exists() and not staging.is_dir():
        raise GetError(f"{staging} is a file where the staging folder goes; remove it and rerun")
    created = not staging.exists()
    try:
        staging.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise GetError(f"cannot make the staging folder {staging}: {exc}") from exc
    clash = _overlap(staging, dest, files)
    if clash is not None:
        if created:
            try:
                staging.rmdir()
            except OSError:
                pass
        if tidy:
            return plain
        raise GetError(f"{clash}; nothing downloaded")
    try:
        lock = _lock(staging)
    except GetError:
        if tidy:  # another run holds it, or its lock cannot be taken: leave it alone
            return plain
        raise
    try:
        journal, late_same, earlier = _locked_run(
            api, preset.repo_id, sha, files, todo, conflicts, kept, dest, staging, on_conflict, workers
        )
    finally:
        os.close(lock)
    try:
        staging.rmdir()  # only when nothing else is left in it
    except OSError:
        pass
    return GetReport(
        **report, skipped=skipped + late_same, kept_local=tuple(kept), downloaded=len(journal),
        replaced=sum(1 for m in journal if m.backup is not None), dry_run=False, earlier_replaced=earlier,
    )


def _locked_run(
    api: hub.HubApi,
    repo_id: str,
    sha: str,
    files: Sequence[RemoteFile],
    todo: Sequence[RemoteFile],
    conflicts: Sequence[RemoteFile],
    kept: list[str],
    dest: Path,
    staging: Path,
    on_conflict: str,
    workers: int,
) -> tuple[list[_Move], int, tuple[str, ...]]:
    """Download ``todo`` into ``staging``, verify it and move it into ``dest``, holding the staging lock.

    The moves made, the files found in place with the hub's bytes meanwhile, and the local files an
    earlier run replaced and left in ``staging``. ``kept`` gains the files that appeared meanwhile and
    are kept under ``keep-local``.
    """
    staged_files = staging / FILES
    links = _symlinks(staging)
    if links and not todo:  # nothing to download: leave the folder as it is
        return [], 0, _earlier(staging)
    if links:
        raise GetError(f"{staging} holds symlinks ({_listing([str(x) for x in links])}); remove it and rerun")
    for f in files:
        got = staged_files / f.repo_path
        # A staged file with another name (a hard link) is never reused: hf_hub_download copies a
        # cached file into an existing one, which would write through to that other name. The other
        # name may be the destination's file, linked there by a run killed before its cleanup.
        if got.is_file() and os.lstat(got).st_nlink != 1:
            got.unlink()
    held = [str(staging / _BACKUP / f.rel) for f in conflicts if (staging / _BACKUP / f.rel).exists()]
    if held and on_conflict == "overwrite":
        raise GetError(
            f"{_listing(held)} hold(s) local files an earlier run replaced and could not put back; "
            "move them somewhere safe and rerun. Nothing downloaded"
        )
    journal: list[_Move] = []
    late_same = 0
    if todo:
        moves, late_same = _download(api, repo_id, sha, todo, kept, dest, staging, on_conflict, workers)
        journal = _move(moves, dest, staging)

    # Every file is in place. Remove what this run put in the staging folder, nothing else.
    try:
        for m in journal:
            if m.backup is not None:
                m.backup.unlink()
        for f in files:
            mine = staged_files / f.repo_path
            if mine.is_file() and not mine.is_symlink():
                mine.unlink()
        shutil.rmtree(staged_files.joinpath(*_HF_BOOKKEEPING), ignore_errors=True)
        earlier = _earlier(staging)
        _prune(staging)  # under the lock, so no other run's fresh folders go
        (staging / LOCK).unlink()
    except OSError as exc:
        raise GetError(f"every file is in place in {dest}, but cleaning {staging} failed: {exc}") from exc
    return journal, late_same, earlier


def _download(
    api: hub.HubApi,
    repo_id: str,
    sha: str,
    todo: Sequence[RemoteFile],
    kept: list[str],
    dest: Path,
    staging: Path,
    on_conflict: str,
    workers: int,
) -> tuple[list[tuple[RemoteFile, bool]], int]:
    """Download and verify ``todo``, then look at ``dest`` again; the moves to make (file, replacing) and
    the number of files that appeared meanwhile with the hub's bytes."""
    where = f"{repo_id}@{sha[:12]}"
    staged_files = staging / FILES
    staged = sum(f.size for f in todo if (staged_files / f.repo_path).is_file())
    need = sum(f.size for f in todo) - staged
    if need > free_bytes(staging):
        raise GetError(f"{human(need)} to download but only {human(free_bytes(staging))} free on the disk of {dest}")

    def fetch(f: RemoteFile) -> str | None:
        try:
            api.hf_hub_download(repo_id, f.repo_path, repo_type=hub.REPO_TYPE, revision=sha, local_dir=staged_files)
        except Exception as exc:  # reported with the others below; the staging folder is kept
            return f"{f.rel}: {exc}"
        return None

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        failed = [e for e in pool.map(fetch, todo) if e]
    links = _symlinks(staging)
    if links:
        raise GetError(f"{staging} holds symlinks ({_listing([str(x) for x in links])}); remove it and rerun")
    bad = []
    for f in todo:
        got = staged_files / f.repo_path
        if got.is_file() and not same_bytes(got, f):
            got.unlink()  # so a rerun fetches it again
            bad.append(f.rel)
        elif not got.is_file() and not any(e.startswith(f"{f.rel}: ") for e in failed):
            failed.append(f"{f.rel}: not in {staging} after the download")
    if failed or bad:
        raise GetError(
            f"{len(bad)} file(s) do not hash like {where}: {_listing(bad)}; {len(failed)} failed to download: "
            f"{_listing(failed)}. Nothing moved into {dest}; {staging} is kept so a rerun resumes"
        )

    # The destination may have changed while the files downloaded: look again before moving anything.
    moves, late, late_same = [], [], 0
    for f in todo:
        target = dest / f.rel
        blocker = _blocker(dest, f.rel)
        if blocker is not None:
            raise GetError(f"while downloading, {blocker} (for {f.rel}); nothing moved, {staging} kept")
        if not (target.exists() or target.is_symlink()):
            moves.append((f, False))
        elif not target.is_file():
            what = "a symlink to no file" if target.is_symlink() else "something other than a file"
            raise GetError(f"{target} became {what} while downloading; nothing moved, {staging} kept")
        elif same_bytes(target, f):
            late_same += 1
        elif on_conflict == "overwrite" and target.is_symlink():
            raise GetError(
                f"{target} became a symlink while downloading; --overwrite replaces only regular files. "
                f"Nothing moved, {staging} kept"
            )
        elif on_conflict == "overwrite":
            moves.append((f, True))
        elif on_conflict == "keep-local":
            kept.append(f.rel)
        else:
            late.append(f.rel)
    if late:
        raise GetError(
            f"{len(late)} file(s) appeared in {dest} while downloading and differ from {where}: {_listing(late)}. "
            f"Nothing moved; {staging} is kept: rerun with --overwrite or --keep-local"
        )
    return moves, late_same


def _move(moves: Sequence[tuple[RemoteFile, bool]], dest: Path, staging: Path) -> list[_Move]:
    """Move each staged file into ``dest``, all or nothing; the moves made."""
    with _ctrl_c_between_steps() as ctrl_c:
        return _move_held(moves, dest, staging, ctrl_c)


def _move_held(
    moves: Sequence[tuple[RemoteFile, bool]], dest: Path, staging: Path, ctrl_c: _CtrlC
) -> list[_Move]:
    staged_files = staging / FILES
    journal: list[_Move] = []
    made: list[Path] = []
    try:
        for f, replacing in moves:
            ctrl_c.check()
            blocker = _blocker(dest, f.rel)  # again for each file: a folder may have changed since the look
            if blocker is not None:
                raise GetError(f"while moving, {blocker} (for {f.rel})")
            m = _Move(dest / f.rel, staged_files / f.repo_path, staging / _BACKUP / f.rel if replacing else None)
            journal.append(m)
            if m.backup is not None:
                if m.backup.exists() or m.backup.is_symlink():
                    raise GetError(f"{m.backup} holds a local file an earlier run replaced; nothing overwrites it")
                if m.target.is_symlink():
                    raise GetError(f"{m.target} became a symlink; --overwrite replaces only regular files, so it stays")
                if not m.target.is_file():
                    raise GetError(f"{m.target} is no longer a regular file; it stays as it is")
                m.backup.parent.mkdir(parents=True, exist_ok=True)
                os.replace(m.target, m.backup)
                m.backed_up = True
                ctrl_c.check()
            missing = [d for d in (m.target.parent, *m.target.parent.parents) if not d.exists()]
            for d in reversed(missing):
                d.mkdir()
                made.append(d)
            m.placed = place(m.src, m.target)
        ctrl_c.check()
    except BaseException as exc:  # Ctrl-C included: put everything back before stopping
        ctrl_c.held.clear()  # a press that stopped the moves is not one pressed during the rollback
        try:
            problems = _roll_back(journal, staging)
            for d in reversed(made):
                try:
                    d.rmdir()
                except OSError:
                    pass
        except KeyboardInterrupt as stop:  # pressed twice: the rollback stops where it is
            stop.add_note(
                f"Ctrl-C stopped putting back the files moved into {dest}: some may still be there, and "
                f"{staging / _BACKUP} holds the local files they replaced. {staging} is kept"
            )
            raise
        if isinstance(exc, _LeftBehind):
            problems.insert(0, str(exc))
        why = str(exc) or type(exc).__name__
        if problems:
            outcome = (
                f"moving into {dest} failed ({why}); everything else was put back, but: {'; '.join(problems)}. "
                f"{staging} is kept"
            )
        else:
            outcome = (
                f"moving into {dest} failed ({why}); every file already moved was put back and every replaced "
                f"file restored. {staging} is kept so a rerun resumes"
            )
        if ctrl_c.held:  # pressed once during the rollback: it finished, now stop
            ctrl_c.held.clear()
            stop = KeyboardInterrupt()
            stop.add_note(outcome)
            raise stop from exc
        if not problems and not isinstance(exc, Exception):
            exc.add_note(outcome)
            raise
        raise GetError(outcome) from exc
    return journal
