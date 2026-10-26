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
   an existing file (on a disk without hard links, a copy made in the staging folder that takes its
   name with a rename refusing an existing file: ``renamex_np(RENAME_EXCL)`` on macOS,
   ``renameat2(RENAME_NOREPLACE)`` on Linux; a disk with neither refuses before any download), so
   one written meanwhile is never overwritten either, and a kill never leaves a part-written or
   empty file in the destination.
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
destination (it would put files, or move replaced ones, outside it), a folder below the destination
on another disk (a mount), and a destination that is or holds the staging folder refuse before any
download. The folders are looked at again before each
file is moved; one swapped for a symlink in the instant between that look and the move is not
caught. The command runs with your rights in your own folders: it guards against accidents and
other runs, not against a process of yours racing it.

The hub's own ``.gitattributes`` (in any case: APFS treats ``.GITATTRIBUTES`` as the same name) is
never downloaded: under ``corpus/`` it would change how git treats the checkout. A hub folder named
like ``hf_hub_download``'s records of another file (``<file>.metadata/``, ``<file>.lock/``) refuses
before any download, since the two cannot share a staging folder.

``overwrite`` replaces only regular files: a local file that is a symlink refuses before any
download, and one that becomes a symlink meanwhile stops the run before anything moves.

Ctrl-C is held from taking the staging lock to letting it go, and every press stops the run with an
error that says where it stopped. During the download it drops the queued downloads and lets the
running ones end, keeping the staging folder for a rerun; a second press stops waiting for them (a
request may never come back), and the staging folder stays locked until they end or the process
exits, so no other run takes a folder they still write into. Two presses that reach the process as
one (the kernel delivers a pending signal once) count as one: press again. While files move, a press waits until the step in hand is
recorded, then rolls everything back; a second press waits too, so no step goes unrecorded. A press
during the rollback lets it finish and then stops; a second one stops it before its next step, and
the error names the files not put back and the staging folder that holds the files they replaced.
Ctrl-C is held only under Python's own handler in the main thread, so a caller that ignores it or
handles it itself keeps that. A run with nothing to download only tidies a staging folder an earlier
run left, and leaves it alone when another run holds it or anything in it is out of place; either
way it names what an earlier run left there (local files it replaced, files it took back).
"""

from __future__ import annotations

import ctypes
import errno
import fcntl
import fnmatch
import functools
import os
import re
import shutil
import signal
import stat
import sys
import tempfile
import threading
import unicodedata
from collections import deque
from collections.abc import Callable, Iterable, Iterator, Sequence
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
               "Word's fresh compares of the 0929 run; not regen_list.csv, which bench jubarte-release reads: "
               "set that lane up with scripts/fetch_corpus.py"),
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
    earlier_replaced: tuple[str, ...] = field(default=())  # what an earlier run left in the staging folder
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
            done += (f". {len(self.earlier_replaced)} file(s) an earlier run left in its staging folder (local files "
                     f"it replaced, or files it took back) are still kept: {_listing(self.earlier_replaced)}")
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
# Inside staging: the hard-link probe, and on a disk without hard links each copy as it is made.
# A run empties it under the lock before using it and removes it on success: a kill leaves nothing
# there that outlives the next run.
_SCRATCH = ".scratch"
_HF_BOOKKEEPING = (".cache", "huggingface")  # what hf_hub_download(local_dir=) writes beside the files
# Staging locks of runs whose downloads a second Ctrl-C left running: each is let go once those
# downloads end, or as the process exits, which ends them too.
_KEPT_LOCKS: list[int] = []
# Every staging lock this process holds, a run's or a kept one. A forked child closes its copies
# (_drop_inherited_locks): a copy shares the lock (flock(2)) and, left open, would hold the staging
# folder after this process exits, for as long as the child lives.
_HELD_LOCKS: set[int] = set()
# Taken to open, list, unlock or look up a lock, so a lock is unlocked and off both lists in one step
# (a run that meets one being let go waits that step out, never sees it held and not kept), and
# across a fork, so no descriptor is copied between being opened and being listed.
_LOCKS_GUARD = threading.RLock()
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


@functools.cache
def _libc() -> ctypes.CDLL:
    return ctypes.CDLL(None, use_errno=True)


_RENAME_EXCL = 0x4  # macOS <stdio.h>: renamex_np fails with EEXIST on an existing name
_RENAME_NOREPLACE = 0x1  # Linux <fcntl.h>: renameat2 does the same
_AT_FDCWD = -100


def _rename_new(src: Path, dst: Path) -> None:
    """Rename ``src`` to ``dst`` in one step that fails with ``FileExistsError`` on an existing ``dst``.

    ``os.rename`` replaces ``dst``; this is macOS's ``renamex_np(RENAME_EXCL)`` or Linux's
    ``renameat2(RENAME_NOREPLACE)``. Elsewhere, or on a disk without it, an OSError.
    """
    old, new = os.fsencode(src), os.fsencode(dst)
    libc = _libc()
    if sys.platform == "darwin":
        call = libc.renamex_np
        call.argtypes, call.restype = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint], ctypes.c_int
        done = call(old, new, _RENAME_EXCL)
    elif sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        call = libc.renameat2
        call.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        call.restype = ctypes.c_int
        done = call(_AT_FDCWD, old, _AT_FDCWD, new, _RENAME_NOREPLACE)
    else:
        raise OSError(errno.ENOTSUP, "no rename that refuses to replace a file here", str(src), None, str(dst))
    if done != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err), str(src), None, str(dst))  # EEXIST makes a FileExistsError


def _copy_new(staged: Path, target: Path, scratch: Path) -> Identity:
    """Copy ``staged`` to ``target``, where no file may be; the new file's identity.

    The bytes go into a file in ``scratch``, which then takes the name ``target`` with ``_rename_new``:
    in one step that refuses an existing file, so nothing at ``target`` is ever overwritten and a kill
    leaves ``target`` absent or whole. The copy gets the mode and times of ``staged``, as a hard link
    would (a restored file keeps them).
    """
    scratch.mkdir(exist_ok=True)
    fd, name = tempfile.mkstemp(dir=scratch)
    copy = Path(name)
    try:
        with open(fd, "wb") as out:
            with open(staged, "rb") as src:
                shutil.copyfileobj(src, out, _CHUNK)
                out.flush()
                was = os.fstat(src.fileno())
            os.fchmod(out.fileno(), stat.S_IMODE(was.st_mode))
            os.utime(out.fileno(), ns=(was.st_atime_ns, was.st_mtime_ns))
            placed = identity(os.fstat(out.fileno()))
        try:
            _rename_new(copy, target)
        except FileExistsError as exc:
            raise GetError(f"{target} appeared while files were being moved into place") from exc
    except BaseException:
        try:
            copy.unlink(missing_ok=True)  # in the staging folder, which a failed run keeps anyway
        except OSError:
            pass
        raise
    return placed


def place(staged: Path, target: Path, scratch: Path) -> Identity:
    """Give ``target`` the bytes of ``staged`` without ever overwriting a file there; the new file's identity.

    A hard link, or on a disk without them a copy made in ``scratch`` that takes the name ``target`` in
    one step refusing an existing file.
    ``staged`` keeps its name: it is removed once every file of the run is in place, so a rollback
    only has to withdraw ``target`` and a rerun still finds the bytes.
    """
    placed = identity(os.lstat(staged))  # before the link, which changes neither inode, size nor mtime
    try:
        os.link(staged, target)  # fails on an existing target, even one written a moment ago
    except FileExistsError as exc:
        raise GetError(f"{target} appeared while files were being moved into place") from exc
    except OSError:  # a disk without hard links
        return _copy_new(staged, target, scratch)
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
            place(hold, target, staging / _SCRATCH)
        except GetError:
            return f"{target} changed while this run took it back; that file is now at {hold}"
        os.unlink(hold)
        hold.parent.rmdir()
        return f"{target} changed after this run moved it there; left as it is"
    os.unlink(hold)
    hold.parent.rmdir()
    return None


def _links_work(scratch: Path) -> bool:
    """Whether ``scratch``'s disk takes hard links; without them ``place`` copies every file.

    A disk without hard links must take ``_rename_new``, which puts each copy in place, or the run
    refuses here, before any download. ``scratch`` is emptied under the lock before the run uses it,
    so nothing an earlier run left there fails a probe; a probe that cannot be written is a refusal,
    like any disk too full.
    """
    names = ("link-probe", "link-probe-2", "link-probe-3")
    probe, second, third = (scratch / n for n in names)
    try:
        scratch.mkdir(exist_ok=True)
        probe.touch(exist_ok=False)
    except OSError as exc:
        raise GetError(f"cannot write in the staging folder ({probe}): {exc}") from exc
    try:
        try:
            os.link(probe, second)
        except OSError:
            pass
        else:
            return True
        try:
            second.touch(exist_ok=False)
        except OSError as exc:
            raise GetError(f"cannot write in the staging folder ({second}): {exc}") from exc
        refusal = (
            f"the disk of {scratch} takes no hard links, so each file would be copied into place, but it "
            "has no rename that refuses to replace a file"
        )
        try:
            try:
                _rename_new(probe, second)
            except FileExistsError:
                pass
            else:
                raise GetError(f"{refusal} (one replaced {second}); a file written meanwhile could be lost")
            _rename_new(probe, third)
        except OSError as exc:
            raise GetError(f"{refusal} ({exc})") from exc
        return False
    finally:
        for p in (probe, second, third):
            try:
                p.unlink()
            except OSError:
                pass


def _staged_size(path: Path) -> int | None:
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return None
    return st.st_size if stat.S_ISREG(st.st_mode) else None


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
        if parts[-1].casefold() in _NEVER or (include and not _matches(rel, include)) or _matches(rel, exclude):
            continue
        # A file at .cache, or anything under .cache/huggingface, in any case (one name on APFS):
        # hf_hub_download needs that folder for its records. Only a file the run fetches is in the way.
        if _fold(PurePosixPath(repo_path).parts[:2]) in (_HF_BOOKKEEPING, _HF_BOOKKEEPING[:1]):
            raise GetError(f"refusing {repo_path}: hf_hub_download keeps its own records in {'/'.join(_HF_BOOKKEEPING)}")
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
    a folder below ``dest`` is a symlink (it would put the file, or move a replaced one, outside ``dest``),
    or one is on another disk than ``dest`` (a mount: a file there could only be copied, and a rollback
    could not take it back into the staging folder). ``dest`` itself may be a symlink or a mount."""
    if (dest.exists() or dest.is_symlink()) and not dest.is_dir():
        return f"{dest} is a file where the hub has a folder"
    home = device(dest)
    path = dest
    for part in PurePosixPath(rel).parts[:-1]:
        path = path / part
        if path.is_symlink():
            return f"{path} is a symlink, and files only go into real folders below {dest}"
        if path.exists() and not path.is_dir():
            return f"{path} is a file where the hub has a folder"
        if path.is_dir() and device(path) != home:
            return f"{path} is on another disk than {dest} (a mount), and files only go into folders on its disk"
    return None


def _collisions(files: Sequence[RemoteFile], dest: Path) -> list[list[str]]:
    """Hub names that one name on the destination's disk would have to hold: two files, or a file and a
    folder (``A`` and ``a/x``). Folders end in ``/``; two folders that fold together are one folder."""
    def groups(key) -> list[list[str]]:
        seen: dict[str, list[str]] = {}
        for f in files:
            parts = f.rel.split("/")
            for depth in range(1, len(parts)):
                folder = "/".join(parts[:depth])
                names = seen.setdefault(key(folder), [])
                if f"{folder}/" not in names:
                    names.append(f"{folder}/")
            seen.setdefault(key(f.rel), []).append(f.rel)
        return [names for names in seen.values() if len(names) > 1 and any(not n.endswith("/") for n in names)]

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
    """An exclusive lock on ``staging``'s lock file, held until ``_unlock`` lets go of the returned descriptor.

    A run that finishes removes the lock file while it holds the lock, so a lock taken on a file no
    longer at the lock path is let go and taken again on the file that is there now.
    """
    while True:
        with _LOCKS_GUARD:
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
                if _kept_here(staging):
                    raise _Busy(
                        f"downloads that a second Ctrl-C left running in this process still write into {staging}; "
                        "rerun once they end, or in a new process"
                    ) from exc
                raise _Busy(f"another bench hub get is using {staging}; wait for it to finish") from exc
            except OSError as exc:  # a disk without locks, among others
                os.close(fd)
                raise GetError(f"cannot take the lock {staging / LOCK}: {exc}") from exc
            except BaseException:
                os.close(fd)
                raise
            if now is not None and now[:2] == (mine.st_dev, mine.st_ino):
                _HELD_LOCKS.add(fd)
                return fd
            os.close(fd)


def _kept_here(staging: Path) -> bool:
    """Whether this process keeps ``staging``'s lock for downloads a second Ctrl-C left running."""
    now = _identity_at(staging / LOCK)
    with _LOCKS_GUARD:  # every descriptor listed is open: it is unlocked and taken off in one step
        return now is not None and any(now[:2] == (os.fstat(fd).st_dev, os.fstat(fd).st_ino) for fd in _KEPT_LOCKS)


def _unlock(lock: int) -> None:
    """Unlock, then close. The unlock frees the lock even where a copy of the descriptor outlives this
    process's (flock(2)), such as a child forked by a path that skips the at-fork hook below."""
    with _LOCKS_GUARD:
        _HELD_LOCKS.discard(lock)
        try:
            fcntl.flock(lock, fcntl.LOCK_UN)
        finally:
            os.close(lock)


def _let_go(lock: int, running: Sequence[threading.Thread]) -> None:
    """Let go of the staging lock ``lock`` now, or once the downloads ``running`` end."""
    if not running:
        _unlock(lock)
        return
    with _LOCKS_GUARD:
        _KEPT_LOCKS.append(lock)

    def once_they_end() -> None:
        for t in running:
            t.join()
        with _LOCKS_GUARD:
            if lock not in _KEPT_LOCKS:  # whoever takes it off the list lets it go
                return
            _unlock(lock)
            _KEPT_LOCKS.remove(lock)

    threading.Thread(target=once_they_end, name="hub-get-let-go", daemon=True).start()


def _drop_inherited_locks() -> None:
    """In a forked child: close the copies of this process's staging locks, and give Ctrl-C back to
    Python's handler if a run was holding it.

    Closing a copy leaves the parent's lock as it is (only an unlock, or the last descriptor closing,
    frees it); keeping it would hold the staging folder past the parent's exit, for the child's life.
    The hold is the parent's run's: in the child nothing would ever raise the presses it holds, and a
    run of the child's own would take it for a caller's handler and leave it in place.
    """
    global _LOCKS_GUARD
    _LOCKS_GUARD = threading.RLock()  # the parent's stays held by the thread that forked
    for fd in _HELD_LOCKS:
        try:
            os.close(fd)
        except OSError:
            pass
    _HELD_LOCKS.clear()
    _KEPT_LOCKS.clear()
    if isinstance(getattr(signal.getsignal(signal.SIGINT), "__self__", None), _CtrlC):
        try:
            signal.signal(signal.SIGINT, signal.default_int_handler)  # what a hold replaces, and only that
        except ValueError:  # not the main thread of the main interpreter
            pass


os.register_at_fork(
    before=lambda: _LOCKS_GUARD.acquire(),
    after_in_parent=lambda: _LOCKS_GUARD.release(),
    after_in_child=_drop_inherited_locks,
)


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
    """The Ctrl-C presses held while files move or are put back; a press never splits a step.

    Raising a press at once could land between a finished rename or link and its journal entry, and
    the rollback would not know about that step. So while files move, ``check`` raises a held press
    once the step in hand is recorded; during the rollback one press lets it finish, and a second
    stops it before its next step (``stop_rollback``).
    """

    def __init__(self) -> None:
        self.held: list[int] = []
        self.left_running: list[threading.Thread] = []  # downloads still running when a second press stopped the wait

    def hold(self, signum: int, _frame: object) -> None:
        if len(self.held) < 2:
            self.held.append(signum)

    def check(self, note: str | None = None) -> None:
        """Raise one held press, with ``note`` saying where the run stopped; a second one stays held."""
        if self.held:
            self.held.pop(0)
            raise _interrupted(note) if note else KeyboardInterrupt

    def stop_rollback(self) -> None:
        if len(self.held) > 1:
            raise KeyboardInterrupt


@contextmanager
def _ctrl_c_between_steps() -> Iterator[_CtrlC]:
    """Hold Ctrl-C (SIGINT) while the block runs; the ``_CtrlC`` it yields raises a held one.

    A filesystem step and its journal entry then happen together: a Ctrl-C that lands as a rename
    or a link returns waits for the next check, so the rollback knows about that step. A run holds
    it once, from taking the staging lock to letting it go, so Python's handler is given back only
    after the run ends; a press still held then is raised as the block ends without an error.
    Ctrl-C is held only under Python's own handler, in the main thread: a caller that ignores Ctrl-C
    or handles it itself keeps that, and its ``check`` never raises.
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
    ctrl_c.check()  # pressed after the block's last check


def _earlier(staging: Path) -> tuple[str, ...]:
    """What an earlier run left in ``staging``: the local files it replaced (``.replaced/``) and the files
    it took back from the destination (``.withdrawn-*/``); looked at, never followed or changed."""
    if staging.is_symlink() or not staging.is_dir():
        return ()
    found = []
    for top in (staging / _BACKUP, *sorted(staging.glob(".withdrawn-*"))):
        if top.is_symlink() or not top.is_dir():
            continue
        for root, dirs, names in os.walk(top):  # lists a symlinked folder among ``dirs`` but does not enter it
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


def _roll_back(journal: Sequence[_Move], staging: Path, between: Callable[[], None] = lambda: None) -> list[str]:
    """Undo ``journal`` newest first, each move on its own; what could not be undone, and where its files are.

    ``between`` runs before each move is undone; what it raises stops the rollback there.
    """
    problems = []
    for m in reversed(journal):
        between()
        kept = f"; the file it replaced is kept at {m.backup}" if m.backed_up else ""
        try:
            if m.placed is not None:
                why = _withdraw(m.target, m.placed, staging)
                if why is not None:
                    problems.append(why + kept)
                    continue
                m.placed = None
            if m.backed_up:
                place(m.backup, m.target, staging / _SCRATCH)
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
        raise GetError(f"{where} has names that would be one name on the disk of {dest}: {', '.join(names)}")
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
    nothing_moved = f"stopped before anything was downloaded: nothing moved into {dest}"
    finished = f"stopped after the run finished: every file is in place in {dest}"
    done = False
    try:
        with _ctrl_c_between_steps() as ctrl_c:  # one hold, from taking the staging lock to letting it go
            try:
                lock = _lock(staging)
            except GetError:
                if not tidy:
                    raise
                ctrl_c.check(nothing_moved)
                return plain  # another run holds it, or its lock cannot be taken: leave it alone
            try:
                ctrl_c.check(nothing_moved)
                journal, late_same, earlier = _locked_run(
                    api, preset.repo_id, sha, files, todo, conflicts, kept, dest, staging, on_conflict, workers, ctrl_c
                )
            finally:
                _let_go(lock, ctrl_c.left_running)
            done = True
            try:
                staging.rmdir()  # only when nothing else is left in it
            except OSError:
                pass
            ctrl_c.check(finished)
        return GetReport(
            **report, skipped=skipped + late_same, kept_local=tuple(kept), downloaded=len(journal),
            replaced=sum(1 for m in journal if m.backup is not None), dry_run=False, earlier_replaced=earlier,
        )
    except KeyboardInterrupt as exc:
        if not getattr(exc, "__notes__", None):  # not raised by a check: before the hold, or as it was given back
            context = exc.__context__
            if done:
                exc.add_note(finished)
            elif context is not None:  # the run was already stopping: say why
                for note in getattr(context, "__notes__", None) or [str(context) or type(context).__name__]:
                    exc.add_note(note)
            else:
                exc.add_note(nothing_moved)
        raise


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
    ctrl_c: _CtrlC,
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
    shutil.rmtree(staging / _SCRATCH, ignore_errors=True)  # under the lock: what a killed run left there
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
        moves, late_same = _download(api, repo_id, sha, todo, kept, dest, staging, on_conflict, workers, ctrl_c)
        journal = _move_held(moves, dest, staging, ctrl_c)
        # every file is in place: a press since the last move stops the run before the cleanup
        ctrl_c.check(
            f"stopped after every file was moved into {dest} and verified; {staging} still holds the staged "
            f"copies and any local files --overwrite replaced ({staging / _BACKUP}): a rerun removes the copies "
            "and names those files"
        )

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
        shutil.rmtree(staging / _SCRATCH, ignore_errors=True)
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
    ctrl_c: _CtrlC,
) -> tuple[list[tuple[RemoteFile, bool]], int]:
    """Download and verify ``todo``, then look at ``dest`` again; the moves to make (file, replacing) and
    the number of files that appeared meanwhile with the hub's bytes."""
    where = f"{repo_id}@{sha[:12]}"
    staged_files = staging / FILES
    # A staged file saves its download only when it is whole; a partial one is fetched again.
    staged = sum(f.size for f in todo if _staged_size(staged_files / f.repo_path) == f.size)
    need = sum(f.size for f in todo) - staged
    if need > free_bytes(staging):
        raise GetError(f"{human(need)} to download but only {human(free_bytes(staging))} free on the disk of {dest}")
    if not _links_work(staging / _SCRATCH):  # each file is copied; the staged copies stay until the last is in place
        need += sum(f.size for f in todo)
        if need > free_bytes(staging):
            raise GetError(
                f"{human(need)} to download and copy (this disk takes no hard links) but only "
                f"{human(free_bytes(staging))} free on the disk of {dest}"
            )

    def fetch(f: RemoteFile) -> str | None:
        try:
            api.hf_hub_download(repo_id, f.repo_path, repo_type=hub.REPO_TYPE, revision=sha, local_dir=staged_files)
        except BaseException as exc:  # reported with the others below; the staging folder is kept
            return f"{f.rel}: {str(exc) or type(exc).__name__}"
        return None

    stopped = f"stopped while downloading: nothing moved into {dest}; {staging} is kept so a rerun resumes"
    left = deque(todo)
    results: dict[str, str | None] = {}
    taking = threading.Lock()
    stop = threading.Event()

    def work() -> None:
        while not stop.is_set():
            with taking:
                if stop.is_set() or not left:  # a stop set while this thread waited for the queue
                    return
                f = left.popleft()
            results[f.rel] = fetch(f)

    # Daemon threads: a download left running when a second press stops the wait ends with the
    # process, which keeps the staging lock until then, instead of keeping the process alive.
    threads = [
        threading.Thread(target=work, name=f"hub-get-download-{i}", daemon=True)
        for i in range(max(1, min(workers, len(todo))))
    ]
    try:
        for t in threads:  # Ctrl-C is held: it never lands between a thread's start and this list
            t.start()
        while alive := [t for t in threads if t.is_alive()]:
            ctrl_c.check(stopped)
            alive[0].join(0.25)  # in slices, so a press is seen during a long download
        ctrl_c.check(stopped)
    except BaseException as exc:
        with taking:  # so no worker is between its look at ``stop`` and the queue
            stop.set()  # the queued downloads never start; the running ones end
        while alive := [t for t in threads if t.is_alive()]:
            if ctrl_c.held:  # pressed again: stop waiting (a request may never come back)
                ctrl_c.held.clear()
                ctrl_c.left_running = alive
                break
            try:
                alive[0].join(0.25)
            except KeyboardInterrupt:  # a caller's own Ctrl-C handler raised again
                ctrl_c.left_running = alive
                break
        if ctrl_c.left_running:
            exc.add_note(
                f"{len(ctrl_c.left_running)} download(s) still running were left to end; {staging} stays locked "
                "until they end or this process exits, and a rerun after that resumes"
            )
        raise
    checking = f"stopped while checking the downloaded files: nothing moved into {dest}; {staging} is kept so a rerun resumes"
    failed = [e for e in results.values() if e]
    links = _symlinks(staging)
    if links:
        raise GetError(f"{staging} holds symlinks ({_listing([str(x) for x in links])}); remove it and rerun")
    bad = []
    failed += [f"{f.rel}: its download never finished" for f in todo if f.rel not in results]
    failing = {f.rel for f in todo if results.get(f.rel, "never finished")}  # each file is named once
    for f in todo:
        ctrl_c.check(checking)
        got = staged_files / f.repo_path
        if got.is_file() and not same_bytes(got, f):
            got.unlink()  # so a rerun fetches it again
            if f.rel not in failing:
                bad.append(f.rel)
        elif not got.is_file() and f.rel not in failing:
            failed.append(f"{f.rel}: not in {staging} after the download")
    if failed or bad:
        found = [f"{len(bad)} file(s) do not hash like {where}: {_listing(bad)}"] if bad else []
        found += [f"{len(failed)} failed to download: {_listing(failed)}"] if failed else []
        raise GetError(f"{'; '.join(found)}. Nothing moved into {dest}; {staging} is kept so a rerun resumes")

    # The destination may have changed while the files downloaded: look again before moving anything.
    moves, late, late_same = [], [], 0
    for f in todo:
        ctrl_c.check(checking)
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
    ctrl_c.check(checking)
    if late:
        raise GetError(
            f"{len(late)} file(s) appeared in {dest} while downloading and differ from {where}: {_listing(late)}. "
            f"Nothing moved; {staging} is kept: rerun with --overwrite or --keep-local"
        )
    return moves, late_same


def _interrupted(note: str) -> KeyboardInterrupt:
    stop = KeyboardInterrupt()
    stop.add_note(note)
    return stop


def _move_held(
    moves: Sequence[tuple[RemoteFile, bool]], dest: Path, staging: Path, ctrl_c: _CtrlC
) -> list[_Move]:
    """Move each staged file into ``dest``, all or nothing, with Ctrl-C held; the moves made."""
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
            m.placed = place(m.src, m.target, staging / _SCRATCH)
        ctrl_c.check()
    except BaseException as exc:  # Ctrl-C included: put everything back before stopping
        ctrl_c.held.clear()  # a press that stopped the moves is not one pressed during the rollback
        try:
            problems = _roll_back(journal, staging, ctrl_c.stop_rollback)
        except KeyboardInterrupt as stop:  # pressed twice: the rollback stops before its next step
            left = [str(m.target) for m in journal if m.placed is not None or m.backed_up]
            failed = f" (the move failed: {exc})" if isinstance(exc, Exception) else ""
            stop.add_note(
                f"Ctrl-C stopped putting back the files moved into {dest}{failed}; not put back: "
                f"{_listing(left) if left else 'none'}. {staging / _BACKUP} holds the local files they replaced; "
                f"{staging} is kept"
            )
            raise
        for d in reversed(made):
            try:
                d.rmdir()
            except OSError:
                pass
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
        if not isinstance(exc, Exception):  # a Ctrl-C stays one, whatever the rollback left
            exc.add_note(outcome)
            raise
        raise GetError(outcome) from exc
    return journal
