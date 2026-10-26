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
   an existing file, so one written meanwhile is never overwritten either.
4. **Staged, all or nothing.** Files land in a staging folder on the destination's disk (beside it,
   or inside it when it is a mount or a link to another disk), locked for the run, refused if it
   holds a symlink. They move into place only once all of them verified; a failed move puts back
   every file already moved and restores every file ``overwrite`` replaced. On success the run
   removes what it put in the staging folder and nothing else; on failure the folder is kept
   (minus the files that failed to verify), so a rerun resumes.

Names that one file would have to hold on the destination's disk (``A.txt`` and ``a.txt`` on
case-insensitive APFS) and a local file where the hub has a folder refuse before any download.

The hub's own ``.gitattributes`` is never downloaded: under ``corpus/`` it would change how git
treats the checkout.
"""

from __future__ import annotations

import fcntl
import fnmatch
import os
import re
import shutil
import tempfile
import unicodedata
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
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
            exclude=("README.md",),  # the dataset card, not corpus/README.md
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

    def describe(self) -> str:
        head = f"{self.repo_id}@{self.revision[:12]} → {self.dest}: {self.n_files} files ({human(self.n_bytes)})"
        if self.dry_run:
            return (f"dry run: {head}; would download {self.to_download} ({human(self.to_download_bytes)}), "
                    f"{self.skipped} already there, {len(self.conflicts)} differ locally")
        return (f"{head}; downloaded {self.downloaded}, already there {self.skipped}, "
                f"replaced {self.replaced}, kept local {len(self.kept_local)}; every file verified")


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
_BACKUP = ".replaced"  # inside staging: the local files --overwrite moved aside, until every move succeeded
_HF_BOOKKEEPING = Path(".cache") / "huggingface"  # what hf_hub_download(local_dir=) writes beside the files


def device(path: Path) -> int:
    path = Path(path).absolute()
    while not path.exists():
        path = path.parent
    return os.stat(path).st_dev


def case_insensitive(path: Path) -> bool:
    """Whether the disk holding ``path`` treats names that differ only by case as one (APFS's default)."""
    path = Path(path).absolute()
    while not path.is_dir():
        path = path.parent
    with tempfile.NamedTemporaryFile(prefix=".hubcase-", dir=path) as probe:
        name = Path(probe.name)
        return (name.parent / name.name.upper()).exists()


def place(staged: Path, target: Path) -> None:
    """Move ``staged`` to ``target`` without ever overwriting a file that is there."""
    try:
        os.link(staged, target)  # fails on an existing target, even one written a moment ago
    except FileExistsError as exc:
        raise GetError(f"{target} appeared while files were being moved into place") from exc
    except OSError:  # a disk without hard links
        if target.exists() or target.is_symlink():
            raise GetError(f"{target} appeared while files were being moved into place") from None
        os.rename(staged, target)
        return
    os.unlink(staged)


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
    for entry in api.list_repo_tree(
        repo_id, repo_type=hub.REPO_TYPE, path_in_repo=path or None, recursive=True, expand=False, revision=revision
    ):
        if not hasattr(entry, "blob_id"):  # a folder
            continue
        repo_path = str(entry.path)
        if not repo_path.startswith(prefix):
            raise GetError(f"the hub listed {repo_path} under {path}")
        rel = repo_path[len(prefix):]
        parts = PurePosixPath(rel).parts
        if not parts or ".." in parts or PurePosixPath(rel).is_absolute():
            raise GetError(f"refusing a hub path that leaves the destination: {repo_path}")
        if parts[-1] in _NEVER or (include and not _matches(rel, include)) or _matches(rel, exclude):
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


def _blocker(dest: Path, rel: str) -> Path | None:
    """The first of ``dest`` and the folders above ``rel`` that exists but is not a folder."""
    path = dest
    for part in ("", *PurePosixPath(rel).parts[:-1]):
        path = path / part if part else path
        if (path.exists() or path.is_symlink()) and not path.is_dir():
            return path
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


def _symlinks(staging: Path) -> list[Path]:
    if staging.is_symlink():
        return [staging]
    found = []
    for root, dirs, names in os.walk(staging):
        found += [Path(root) / n for n in (*dirs, *names) if (Path(root) / n).is_symlink()]
    return found


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

    todo: list[RemoteFile] = []
    skipped = 0
    conflicts: list[RemoteFile] = []
    for f in files:
        local = dest / f.rel
        blocker = _blocker(dest, f.rel)
        if blocker is not None:
            raise GetError(f"{blocker} is a file where {where} has a folder (for {f.rel}); nothing downloaded")
        if not (local.exists() or local.is_symlink()):
            todo.append(f)
        elif not local.is_file():
            raise GetError(f"{local} is not a file but the hub has a file there; nothing downloaded")
        elif same_bytes(local, f):
            skipped += 1
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
        to_download=len(todo), to_download_bytes=sum(f.size for f in todo), conflicts=differ,
    )
    if dry_run or not todo:
        return GetReport(**report, skipped=skipped, kept_local=tuple(kept), downloaded=0, replaced=0, dry_run=dry_run)

    staging = staging_dir(dest, sha)
    if staging.is_symlink():
        raise GetError(f"{staging} is a symlink; remove it and rerun")
    staging.mkdir(parents=True, exist_ok=True)
    with open(staging / LOCK, "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise GetError(f"another bench hub get is using {staging}; wait for it to finish") from exc
        links = _symlinks(staging)
        if links:
            raise GetError(f"{staging} holds symlinks ({_listing([str(x) for x in links])}); remove it and rerun")
        staged = sum(f.size for f in todo if (staging / f.repo_path).is_file())
        need = report["to_download_bytes"] - staged
        if need > free_bytes(staging):
            raise GetError(f"{human(need)} to download but only {human(free_bytes(staging))} free on the disk of {dest}")

        def fetch(f: RemoteFile) -> str | None:
            try:
                api.hf_hub_download(preset.repo_id, f.repo_path, repo_type=hub.REPO_TYPE, revision=sha, local_dir=staging)
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
            got = staging / f.repo_path
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
                raise GetError(f"{blocker} became a file while downloading (for {f.rel}); nothing moved, {staging} kept")
            if not (target.exists() or target.is_symlink()):
                moves.append((f, False))
            elif not target.is_file():
                raise GetError(f"{target} became a folder while downloading; nothing moved, {staging} kept")
            elif same_bytes(target, f):
                late_same += 1
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

        done: list[tuple[Path, Path, Path | None]] = []
        made: list[Path] = []
        current = None
        try:
            for f, replacing in moves:
                target, src = dest / f.rel, staging / f.repo_path
                backup = staging / _BACKUP / f.rel if replacing else None
                current = (target, backup)
                if backup is not None:
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(target, backup)
                missing = [d for d in (target.parent, *target.parent.parents) if not d.exists()]
                for d in reversed(missing):
                    d.mkdir()
                    made.append(d)
                place(src, target)
                done.append((target, src, backup))
                current = None
        except (OSError, GetError) as exc:
            if current is not None and current[1] is not None and not current[0].exists():
                os.replace(current[1], current[0])
            for target, src, backup in reversed(done):
                os.replace(target, src)
                if backup is not None:
                    os.replace(backup, target)
            for d in reversed(made):
                try:
                    d.rmdir()
                except OSError:
                    pass
            raise GetError(
                f"moving into {dest} failed ({exc}); every file already moved was put back and every replaced "
                f"file restored. {staging} is kept so a rerun resumes"
            ) from exc

        # Remove what this run put in the staging folder, nothing else.
        for _target, _src, backup in done:
            if backup is not None:
                backup.unlink()
        for f in files:
            mine = staging / f.repo_path
            if mine.is_file() and not mine.is_symlink():
                mine.unlink()
        shutil.rmtree(staging / _HF_BOOKKEEPING, ignore_errors=True)
        (staging / LOCK).unlink()
    _prune(staging)
    return GetReport(
        **report, skipped=skipped + late_same, kept_local=tuple(kept), downloaded=len(done), replaced=sum(1 for *_x, b in done if b is not None),
        dry_run=False,
    )
