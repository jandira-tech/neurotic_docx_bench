"""Hugging Face hub round trip for the two bench datasets.

Two dataset repositories:

* ``FIXTURES_REPO`` holds the source fixtures (the ``corpus/`` tree) with a sha256
  manifest; ``bench fixtures download`` refuses a snapshot whose files do not match it.
* ``RESULTS_REPO`` holds, per bench version, the result stores, the published pages,
  the registry, a ``fixtures-used.json`` index (every oracle file each docset was
  scored against, with its sha256), the oracle files themselves under ``fixtures/``
  and, on request, the raw run outputs under ``outputs/``.

Uploads go through ``HfApi.upload_folder`` (``upload_large_folder`` was removed in
huggingface_hub 2.0; ``upload_folder`` is its replacement). Local run outputs are
pruned only when asked (``prune_local=True``), only when they were uploaded, and
only after every uploaded file's hash was read back from the hub and matched.

Every network call goes through the ``api`` argument so tests inject a fake.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from neurotic_docx_bench.version import bench_version

FIXTURES_REPO = "arthrod/neurotic_docx_bench-fixtures"
RESULTS_REPO = "arthrod/neurotic_docx_bench"
REPO_TYPE = "dataset"
MANIFEST_NAME = "MANIFEST.sha256.json"
LICENSE_ID = "odc-by"

DEFAULT_CORPUS = Path("corpus")
DEFAULT_STAGING = Path("results/hub")
RESULTS_FILES = ("bench.jsonl", "converters.jsonl", "docsets.json")
RESULTS_DIRS = ("detail", "archive", "docx_to_pdf_speed")
PAGE_FILES = ("RESULTS.md", "RESULTS_DETAILED.md", "bench.registry.yaml")
_SKIP_SUFFIXES = {".lock", ".log"}
_SKIP_NAMES = {".DS_Store"}
_CHUNK = 1 << 20


class ManifestError(Exception):
    """A manifest is missing or the files on disk do not match it."""


class HubApi(Protocol):
    """The slice of ``huggingface_hub.HfApi`` this module uses."""

    def create_repo(
        self, repo_id: str, *, repo_type: str, exist_ok: bool = False
    ) -> Any: ...

    def upload_folder(
        self,
        *,
        repo_id: str,
        folder_path: str | Path,
        repo_type: str,
        path_in_repo: str | None = None,
        commit_message: str | None = None,
        ignore_patterns: list[str] | None = None,
    ) -> Any: ...

    def snapshot_download(
        self,
        repo_id: str,
        *,
        repo_type: str,
        revision: str | None = None,
        local_dir: str | Path | None = None,
    ) -> str: ...

    def list_repo_tree(
        self,
        repo_id: str,
        *,
        repo_type: str,
        path_in_repo: str | None = None,
        recursive: bool = True,
        expand: bool = True,
    ) -> Iterable[Any]: ...


def default_api() -> HubApi:
    """The real client; imported lazily so the module stays cheap to import."""
    from huggingface_hub import HfApi

    return HfApi()


# --- hashing ---------------------------------------------------------------


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob_sha1(path: Path) -> str:
    """The git object id the hub reports for files stored inline (not LFS/Xet)."""
    size = path.stat().st_size
    h = hashlib.sha1(b"blob %d\0" % size)
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_noise(path: Path) -> bool:
    return path.name in _SKIP_NAMES or path.suffix in _SKIP_SUFFIXES


def iter_files(root: Path, *, exclude: Iterable[str] = ()) -> list[Path]:
    """Every regular file under ``root``, sorted by posix relative path, noise skipped."""
    skip = set(exclude)
    out = [
        p
        for p in root.rglob("*")
        if p.is_file()
        and not _is_noise(p)
        and p.relative_to(root).as_posix() not in skip
    ]
    return sorted(out, key=lambda p: p.relative_to(root).as_posix())


# --- manifests -------------------------------------------------------------


def build_manifest(
    root: Path, *, exclude: Iterable[str] = (MANIFEST_NAME,)
) -> dict[str, str]:
    """``{posix relative path: sha256}`` for every file under ``root``, sorted."""
    root = Path(root)
    return {
        p.relative_to(root).as_posix(): sha256_file(p)
        for p in iter_files(root, exclude=exclude)
    }


def manifest_document(files: dict[str, str]) -> dict[str, Any]:
    return {
        "algorithm": "sha256",
        "n_files": len(files),
        "files": dict(sorted(files.items())),
    }


def write_manifest(
    root: Path, *, path: Path | None = None, files: dict[str, str] | None = None
) -> Path:
    """Write ``MANIFEST.sha256.json`` for ``root`` (or the given ``files`` map) and return its path."""
    root = Path(root)
    out = path or (root / MANIFEST_NAME)
    data = manifest_document(files if files is not None else build_manifest(root))
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return out


def read_manifest(path: Path) -> dict[str, str]:
    if not path.exists():
        raise ManifestError(f"no {MANIFEST_NAME} at {path.parent}")
    try:
        data = json.loads(path.read_text())
        files = data["files"]
    except (ValueError, KeyError, TypeError) as exc:
        raise ManifestError(f"unreadable {MANIFEST_NAME} at {path}: {exc}") from exc
    if not isinstance(files, dict):
        raise ManifestError(
            f"unreadable {MANIFEST_NAME} at {path}: 'files' is not a mapping"
        )
    return {str(k): str(v) for k, v in files.items()}


@dataclass(frozen=True)
class ManifestReport:
    checked: int
    missing: tuple[str, ...] = ()
    mismatched: tuple[str, ...] = ()
    extra: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not (self.missing or self.mismatched or self.extra)

    def describe(self) -> str:
        if self.ok:
            return f"verified {self.checked} files"
        parts = [f"verified {self.checked} files"]
        if self.missing:
            parts.append("missing: " + ", ".join(self.missing))
        if self.mismatched:
            parts.append("mismatched: " + ", ".join(self.mismatched))
        if self.extra:
            parts.append("extra: " + ", ".join(self.extra))
        return "; ".join(parts)


def verify_manifest(
    root: Path, manifest: dict[str, str] | None = None
) -> ManifestReport:
    """Compare the files under ``root`` with the manifest (read from ``root`` when not given)."""
    root = Path(root)
    expected = manifest if manifest is not None else read_manifest(root / MANIFEST_NAME)
    present = {
        p.relative_to(root).as_posix(): p
        for p in iter_files(root, exclude=(MANIFEST_NAME,))
    }
    missing = tuple(sorted(k for k in expected if k not in present))
    mismatched = tuple(
        sorted(
            k
            for k in expected
            if k in present and sha256_file(present[k]) != expected[k]
        )
    )
    extra = tuple(sorted(k for k in present if k not in expected))
    return ManifestReport(
        checked=len(expected), missing=missing, mismatched=mismatched, extra=extra
    )


# --- fixtures repo ---------------------------------------------------------


@dataclass(frozen=True)
class UploadReport:
    repo_id: str
    root: Path
    n_files: int
    uploaded: tuple[str, ...] = ()
    verified: bool = False
    mismatched: tuple[str, ...] = ()
    pruned: tuple[Path, ...] = ()
    version: str | None = None
    dry_run: bool = False


def _dataset_card(kind: str) -> str:
    if kind == "fixtures":
        body = (
            "# neurotic-docx-bench fixtures\n\n"
            "Source fixtures of the neurotic-docx-bench benchmark: input DOCX files and the\n"
            "Microsoft Word oracle renders they are scored against. Every file is listed in\n"
            f"`{MANIFEST_NAME}` with its sha256; `bench fixtures download` refuses a snapshot\n"
            "that does not match it.\n"
        )
    else:
        body = (
            "# neurotic-docx-bench results\n\n"
            "Per bench version (`v<version>/`): the result stores (`bench.jsonl`,\n"
            "`converters.jsonl`, `docsets.json`, `detail/`, `archive/`), the published pages,\n"
            "the tool registry and `fixtures-used.json`, which lists every oracle file each\n"
            "document set was scored against with its sha256. Those oracle files are under\n"
            "`fixtures/`; raw run outputs, when uploaded, are under `outputs/v<version>/`.\n"
            f"Each version folder carries a `{MANIFEST_NAME}` covering the files uploaded with it.\n"
        )
    return f"---\nlicense: {LICENSE_ID}\npretty_name: neurotic-docx-bench {kind}\n---\n\n{body}"


def write_dataset_card(
    root: Path, kind: str, *, overwrite: bool = False
) -> Path | None:
    out = Path(root) / "README.md"
    if out.exists() and not overwrite:
        return None
    out.write_text(_dataset_card(kind))
    return out


def upload_fixtures(
    root: Path = DEFAULT_CORPUS,
    *,
    api: HubApi,
    repo_id: str = FIXTURES_REPO,
    dry_run: bool = False,
) -> UploadReport:
    """Write the manifest and dataset card into ``root``, then upload the whole folder."""
    root = Path(root)
    files = build_manifest(root)
    n_files = len(files) + 1  # + the manifest itself
    if not (root / "README.md").exists():
        n_files += 1  # + the dataset card written below
    if dry_run:
        return UploadReport(repo_id=repo_id, root=root, n_files=n_files, dry_run=True)
    if write_dataset_card(root, "fixtures") is not None:
        files["README.md"] = sha256_file(root / "README.md")
    write_manifest(root, files=files)
    api.create_repo(repo_id, repo_type=REPO_TYPE, exist_ok=True)
    api.upload_folder(
        repo_id=repo_id,
        folder_path=root,
        repo_type=REPO_TYPE,
        commit_message=f"fixtures: {len(files)} files, bench {bench_version()}",
        ignore_patterns=[f"*{s}" for s in _SKIP_SUFFIXES] + sorted(_SKIP_NAMES),
    )
    mismatched = verify_uploaded(root, api=api, repo_id=repo_id)
    uploaded = tuple(p.relative_to(root).as_posix() for p in iter_files(root))
    return UploadReport(
        repo_id=repo_id,
        root=root,
        n_files=len(uploaded),
        uploaded=uploaded,
        verified=not mismatched,
        mismatched=mismatched,
    )


def download_fixtures(
    dest: Path = DEFAULT_CORPUS,
    *,
    api: HubApi,
    repo_id: str = FIXTURES_REPO,
    revision: str | None = None,
) -> ManifestReport:
    """Snapshot the fixtures repo into ``dest`` and verify it against its manifest."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    api.snapshot_download(
        repo_id, repo_type=REPO_TYPE, revision=revision, local_dir=dest
    )
    report = verify_manifest(dest)
    if not report.ok:
        raise ManifestError(
            f"{repo_id}@{revision or 'main'} does not match its manifest: {report.describe()}"
        )
    return report


# --- results repo ----------------------------------------------------------


def fixtures_used(root: Path) -> dict[str, dict[str, Any]]:
    """Per docset id: benchmark, source dirs and every file in them with its sha256."""
    root = Path(root)
    docsets_path = root / "results" / "docsets.json"
    docsets = json.loads(docsets_path.read_text()) if docsets_path.exists() else {}
    out: dict[str, dict[str, Any]] = {}
    for docset_id, entry in sorted(docsets.items()):
        dirs = list(entry.get("source_dirs") or [])
        files: list[dict[str, str]] = []
        for d in dirs:
            src = root / d
            if not src.is_dir():
                continue
            for p in iter_files(src):
                files.append(
                    {"path": p.relative_to(root).as_posix(), "sha256": sha256_file(p)}
                )
        out[docset_id] = {
            "benchmark": entry.get("benchmark"),
            "holdout_mode": entry.get("holdout_mode"),
            "n": entry.get("n"),
            "source_dirs": dirs,
            "files": files,
        }
    return out


@dataclass(frozen=True)
class StagedResults:
    root: Path
    version: str
    files: tuple[str, ...]
    run_dirs: tuple[Path, ...] = field(default_factory=tuple)


def _link_or_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def _stage_tree(src: Path, dst: Path, rel_prefix: str, out: list[str]) -> None:
    for p in iter_files(src):
        rel = p.relative_to(src).as_posix()
        _link_or_copy(p, dst / rel)
        out.append(f"{rel_prefix}/{rel}")


def stage_results(
    root: Path,
    staging: Path,
    *,
    version: str,
    run_dirs: Sequence[Path] = (),
) -> StagedResults:
    """Build the upload folder for the results repo from scratch (hardlinks where possible)."""
    root = Path(root)
    staging = Path(staging)
    if staging.exists():
        shutil.rmtree(staging)
    vdir = staging / f"v{version}"
    vdir.mkdir(parents=True)
    staged: list[str] = []
    results = root / "results"
    for name in RESULTS_FILES:
        src = results / name
        if src.exists():
            _link_or_copy(src, vdir / name)
            staged.append(f"v{version}/{name}")
    for name in RESULTS_DIRS:
        src = results / name
        if src.is_dir():
            _stage_tree(src, vdir / name, f"v{version}/{name}", staged)
    for name in PAGE_FILES:
        src = root / name
        if src.exists():
            _link_or_copy(src, vdir / name)
            staged.append(f"v{version}/{name}")
    used = fixtures_used(root)
    (vdir / "fixtures-used.json").write_text(
        json.dumps(used, indent=2, sort_keys=True) + "\n"
    )
    staged.append(f"v{version}/fixtures-used.json")
    seen: set[str] = set()
    for entry in used.values():
        for f in entry["files"]:
            rel = f["path"]
            if rel in seen:
                continue
            seen.add(rel)
            _link_or_copy(root / rel, staging / "fixtures" / rel)
            staged.append(f"fixtures/{rel}")
    kept_runs: list[Path] = []
    for run in run_dirs:
        run = Path(run)
        if not run.is_dir():
            continue
        prefix = f"outputs/v{version}/{run.name}"
        _stage_tree(run, staging / prefix, prefix, staged)
        kept_runs.append(run)
    card = write_dataset_card(staging, "results")
    if card is not None:
        staged.append("README.md")
    manifest = {rel: sha256_file(staging / rel) for rel in staged}
    write_manifest(staging, path=vdir / MANIFEST_NAME, files=manifest)
    staged.append(f"v{version}/{MANIFEST_NAME}")
    return StagedResults(
        root=staging,
        version=version,
        files=tuple(sorted(staged)),
        run_dirs=tuple(kept_runs),
    )


def verify_uploaded(
    local_root: Path, *, api: HubApi, repo_id: str, path_in_repo: str = ""
) -> tuple[str, ...]:
    """Relative paths under ``local_root`` whose hub copy is absent or hashes differently."""
    local_root = Path(local_root)
    remote: dict[str, Any] = {}
    for entry in api.list_repo_tree(
        repo_id,
        repo_type=REPO_TYPE,
        path_in_repo=path_in_repo or None,
        recursive=True,
        expand=True,
    ):
        path = getattr(entry, "path", None)
        if path is None:
            continue
        remote[str(path)] = entry
    prefix = path_in_repo.strip("/")
    bad: list[str] = []
    for p in iter_files(local_root):
        rel = p.relative_to(local_root).as_posix()
        key = f"{prefix}/{rel}" if prefix else rel
        entry = remote.get(key)
        if entry is None:
            bad.append(rel)
            continue
        lfs = getattr(entry, "lfs", None)
        if lfs:
            expected = (
                lfs.get("sha256")
                if isinstance(lfs, dict)
                else getattr(lfs, "sha256", None)
            )
            if expected != sha256_file(p):
                bad.append(rel)
            continue
        blob = getattr(entry, "blob_id", None)
        if blob != git_blob_sha1(p):
            bad.append(rel)
    return tuple(sorted(bad))


def prune_run_dirs(run_dirs: Iterable[Path]) -> tuple[Path, ...]:
    pruned: list[Path] = []
    for run in run_dirs:
        run = Path(run)
        if run.is_dir():
            shutil.rmtree(run)
            pruned.append(run)
    return tuple(pruned)


def upload_results(
    root: Path = Path("."),
    *,
    api: HubApi,
    repo_id: str = RESULTS_REPO,
    version: str | None = None,
    with_outputs: bool = False,
    run_dirs: Sequence[Path] | None = None,
    prune_local: bool = False,
    staging: Path | None = None,
    dry_run: bool = False,
) -> UploadReport:
    """Stage, upload, verify by hash; prune local run outputs only when all three hold."""
    root = Path(root)
    ver = version or bench_version()
    staging_dir = Path(staging) if staging is not None else root / DEFAULT_STAGING
    runs: Sequence[Path] = ()
    if with_outputs:
        if run_dirs is None:
            runs_root = root / "runs"
            runs = (
                sorted(p for p in runs_root.iterdir() if p.is_dir())
                if runs_root.is_dir()
                else ()
            )
        else:
            runs = [Path(r) for r in run_dirs]
    staged = stage_results(root, staging_dir, version=ver, run_dirs=runs)
    if dry_run:
        return UploadReport(
            repo_id=repo_id,
            root=staging_dir,
            n_files=len(staged.files),
            uploaded=staged.files,
            version=ver,
            dry_run=True,
        )
    api.create_repo(repo_id, repo_type=REPO_TYPE, exist_ok=True)
    api.upload_folder(
        repo_id=repo_id,
        folder_path=staging_dir,
        repo_type=REPO_TYPE,
        commit_message=f"results: bench {ver}, {len(staged.files)} files"
        + (f", outputs of {len(staged.run_dirs)} runs" if staged.run_dirs else ""),
    )
    mismatched = verify_uploaded(staging_dir, api=api, repo_id=repo_id)
    verified = not mismatched
    pruned: tuple[Path, ...] = ()
    if prune_local and with_outputs and verified and staged.run_dirs:
        pruned = prune_run_dirs(staged.run_dirs)
    return UploadReport(
        repo_id=repo_id,
        root=staging_dir,
        n_files=len(staged.files),
        uploaded=staged.files,
        verified=verified,
        mismatched=mismatched,
        pruned=pruned,
        version=ver,
    )
