"""The legacy_cases snapshot as a recorded input: a committed pointer file.

The adapter-produced snapshot (``cases_adapter.write_legacy``, run once) is ~22 MB,
so it is not committed — it lives, content-addressed, on the results dataset at
``inputs/legacy_cases/<sha256>.jsonl``. What git carries is the pointer
``results/legacy_cases.ref.json`` (:class:`LegacyCasesRef`, strict): the repo, the
content-addressed path, the 40-hex revision whose tree holds exactly those bytes,
the sha256, the size and the source line.

* :func:`ensure_legacy` is what ``bench report`` calls before building: the local
  snapshot (``results/legacy_cases.jsonl`` when it was small enough to commit,
  else git-ignored ``results/release/legacy_cases.jsonl``) wins when it exists;
  otherwise the pointer is satisfied through :mod:`neurotic_docx_bench.hub_get`'s
  pinned, hash-verified download machinery and the bytes land at the release
  location. A pointer that cannot be satisfied — the hub copy is absent or hashes
  differently, the download fails, the placed file does not hash to the pin — is
  a :class:`CasesRefError` with a one-line message: a release is never emitted
  without the cases the pointer promises. ``None`` means neither the snapshot nor
  a pointer exists; the caller decides whether a release without cases is allowed
  (``bench report --allow-no-cases``).
* :func:`snapshot_upload` is ``bench cases snapshot-upload``: upload the local
  snapshot once to its content-addressed path (never over a moved head), verify
  it through the plain tree listing (``expand=False``) at the revision it lands
  on, and write/update the pointer.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from neurotic_docx_bench import hub, hub_get
from neurotic_docx_bench.ledger import cases as cases_mod

#: Where the pointer lives, committed (``root / REF_FILE``).
REF_FILE = Path("results") / "legacy_cases.ref.json"

#: The folder of content-addressed snapshots on the results dataset.
HUB_DIR = "inputs/legacy_cases"

#: The local file name the report reads (under ``results/`` or ``results/release/``).
LEGACY_NAME = "legacy_cases.jsonl"

#: The default pointer ``source``: the adapter run of the published gh-pages pages.
_SOURCE_PREFIX = "cases_adapter.from_published of site/index.html + site/redlines/index.html"
_COMMIT = re.compile(r"[0-9a-f]{40}")


class CasesRefError(Exception):
    """The legacy_cases snapshot cannot be recorded or obtained; nothing was emitted."""


class LegacyCasesRef(BaseModel):
    """The committed pointer to the content-addressed snapshot on the hub.

    Strict on purpose: unknown keys, a revision that is not a 40-hex commit, a
    sha256 that is not 64 hex, a non-positive size, and a path that is not the
    content-addressed location of that very hash are all refused.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    repo: str
    path: str
    revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bytes: int = Field(gt=0)
    source: str = Field(min_length=1)

    @model_validator(mode="after")
    def _content_addressed(self) -> LegacyCasesRef:
        want = f"{HUB_DIR}/{self.sha256}.jsonl"
        if self.path != want:
            raise ValueError(f"path must be the content-addressed {want}, not {self.path!r}")
        return self


def ref_file(root: Path) -> Path:
    return Path(root) / REF_FILE


def load_ref(root: Path) -> LegacyCasesRef | None:
    """The pointer a repo carries, or None when it has none. An unreadable or
    invalid pointer is an error, never a silent fall-through to zero cases."""
    path = ref_file(root)
    if not path.is_file():
        return None
    try:
        ref = LegacyCasesRef.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except ValidationError as exc:
        why = "; ".join(
            f"{'.'.join(str(k) for k in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        raise CasesRefError(f"{REF_FILE} does not validate: {why}") from exc
    except ValueError as exc:
        raise CasesRefError(f"{REF_FILE} is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise CasesRefError(f"{REF_FILE} cannot be read: {exc}") from exc
    return ref


def write_ref(root: Path, ref: LegacyCasesRef) -> Path:
    """Write the pointer, sorted and pretty: a committed file must be diff-stable."""
    path = ref_file(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(ref.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def local_snapshot(root: Path) -> Path | None:
    """The local snapshot, at either location ``ledger.cases`` reads, else None."""
    for candidate in cases_mod.legacy_candidates(root):
        if candidate.is_file():
            return candidate
    return None


def ensure_legacy(root: Path, *, api=None) -> Path | None:
    """The legacy_cases input for ``bench report``; None when there is none.

    The local snapshot wins when it exists. Otherwise the pointer is satisfied
    through ``hub_get``: the plain listing at the pinned revision must hold the
    pinned bytes under the content-addressed path, the download is staged and
    hub-hash-verified by ``hub_get.get``, the placed file must hash to the pin,
    and only then does it take the name ``results/release/legacy_cases.jsonl``.
    """
    root = Path(root)
    if (local := local_snapshot(root)) is not None:
        return local
    ref = load_ref(root)
    if ref is None:
        return None
    api = api if api is not None else hub.default_api()
    name = f"{ref.sha256}.jsonl"
    dest_dir = root / "results" / "release"
    where = f"{ref.repo}@{ref.revision[:12]}"
    try:
        listed = hub_get.remote_files(api, ref.repo, ref.revision, HUB_DIR, exact=(name,))
    except hub_get.GetError as exc:
        raise CasesRefError(f"legacy cases: {where} cannot list {HUB_DIR}/: {exc}") from exc
    remote = next((f for f in listed if f.rel == name), None)
    if remote is None:
        raise CasesRefError(
            f"legacy cases: {where} has no {ref.path} that {REF_FILE} pins; "
            "no release without cases (rerun `bench cases snapshot-upload`)"
        )
    if (remote.sha256 is not None and remote.sha256 != ref.sha256) or remote.size != ref.bytes:
        raise CasesRefError(
            f"legacy cases: {where} {ref.path} holds {remote.size} bytes"
            + (f" hashing {remote.sha256}" if remote.sha256 else " as an inline blob")
            + f", but {REF_FILE} pins {ref.bytes} bytes hashing {ref.sha256}"
        )
    preset = hub_get.Preset(
        name="legacy-cases",
        repo_id=ref.repo,
        path=HUB_DIR,
        dest=dest_dir,
        about="the legacy_cases snapshot that results/legacy_cases.ref.json records",
    )
    try:
        hub_get.get(preset, api=api, revision=ref.revision, exact=(name,))
    except hub_get.GetError as exc:
        raise CasesRefError(
            f"legacy cases: {where} {ref.path} cannot be downloaded: {exc}"
        ) from exc
    got = dest_dir / name
    if not got.is_file():
        raise CasesRefError(f"legacy cases: {where} {ref.path} did not land at {got}")
    digest = hub.sha256_file(got)
    if digest != ref.sha256 or got.stat().st_size != ref.bytes:
        raise CasesRefError(
            f"legacy cases: the downloaded {got.name} hashes {digest}, "
            f"but {REF_FILE} pins {ref.sha256}; no release without cases"
        )
    dest = dest_dir / LEGACY_NAME
    dest.parent.mkdir(parents=True, exist_ok=True)
    got.replace(dest)
    return dest


# ---- snapshot-upload --------------------------------------------------------------------


def _same_remote(remote: hub_get.RemoteFile, digest: str, size: int, local: Path) -> bool:
    """Whether a listing entry holds exactly the local snapshot's bytes."""
    if remote.size != size:
        return False
    if remote.sha256 is not None:  # an LFS file: the pointer's own hash
        return remote.sha256 == digest
    return remote.blob_id == hub.git_blob_sha1(local)  # inline: the git blob id


def _site_dir(root: Path) -> Path | None:
    """The published gh-pages site: NDB_SITE_DIR, ``<root>/site``, or the
    registered gh-pages worktree (the adapter's pages, test_ledger_cases has the
    same lookup)."""
    env = os.environ.get("NDB_SITE_DIR")
    if env and (Path(env) / "index.html").is_file():
        return Path(env)
    cand = Path(root) / "site"
    if (cand / "index.html").is_file():
        return cand
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for block in out.split("\n\n"):
        if "refs/heads/gh-pages" in block:
            for line in block.splitlines():
                if line.startswith("worktree "):
                    p = Path(line[len("worktree ") :])
                    if (p / "index.html").is_file():
                        return p
    return None


def default_source(root: Path) -> str | None:
    """The pointer's ``source`` line from the gh-pages worktree's commit, else None."""
    site = _site_dir(root)
    if site is None:
        return None
    try:
        out = subprocess.run(
            ["git", "-C", str(site), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return f"{_SOURCE_PREFIX} at gh-pages {out}" if _COMMIT.fullmatch(out) else None


def _list(api, repo: str, revision: str) -> list[hub_get.RemoteFile]:
    try:
        return hub_get.remote_files(api, repo, revision, HUB_DIR)
    except hub_get.GetError as exc:
        raise CasesRefError(f"{repo}@{revision[:12]}: {exc}") from exc


def snapshot_upload(
    root: Path,
    *,
    api=None,
    repo: str = hub.RESULTS_REPO,
    source: str | None = None,
) -> tuple[LegacyCasesRef, bool]:
    """Upload the local snapshot to its content-addressed hub path; write the pointer.

    The path is ``inputs/legacy_cases/<sha256>.jsonl``: same bytes, same path, so
    an upload never overwrites another snapshot (and the upload itself is pinned
    to the head it listed, refusing over a concurrently moved one). When the path
    already holds these bytes nothing is uploaded. The copy is verified through
    the plain tree listing (``expand=False``) at the revision recorded in the
    pointer, and the pointer is written only then. Returns ``(pointer, uploaded)``.
    """
    root = Path(root)
    legacy = local_snapshot(root)
    if legacy is None:
        raise CasesRefError(
            "no legacy_cases input under results/ (produce it once with "
            "cases_adapter.write_legacy; see neurotic_docx_bench/ledger/cases_adapter.py)"
        )
    api = api if api is not None else hub.default_api()
    src = source if source is not None else default_source(root)
    if src is None:
        raise CasesRefError(
            "no gh-pages site worktree found to source the pointer from "
            "(set NDB_SITE_DIR or pass --source)"
        )
    digest = hub.sha256_file(legacy)
    size = legacy.stat().st_size
    name = f"{digest}.jsonl"
    repo_path = f"{HUB_DIR}/{name}"
    try:
        head = hub_get.resolve_revision(api, repo)
    except hub_get.GetError as exc:
        raise CasesRefError(str(exc)) from exc
    remote = next((f for f in _list(api, repo, head) if f.rel == name), None)
    if remote is not None:
        if not _same_remote(remote, digest, size, legacy):
            raise CasesRefError(
                f"{repo}@{head[:12]} {repo_path} holds different bytes than {legacy}; "
                "content-addressed paths are never overwritten"
            )
        revision = head  # these bytes are already recorded: re-pin the head
        uploaded = False
    else:
        revision = _upload_one(api, repo, head, legacy, name, digest, size, repo_path)
        uploaded = True
    ref = LegacyCasesRef(
        repo=repo, path=repo_path, revision=revision, sha256=digest, bytes=size, source=src
    )
    write_ref(root, ref)
    return ref, uploaded


def _upload_one(
    api,
    repo: str,
    head: str,
    legacy: Path,
    name: str,
    digest: str,
    size: int,
    repo_path: str,
) -> str:
    """Stage the one file, upload it pinned to ``head``, verify it by the plain
    listing at the new head; the revision the copy verified at."""
    try:
        with tempfile.TemporaryDirectory(prefix="legacy-cases-upload-") as tmp:
            stage = Path(tmp) / name
            shutil.copyfile(legacy, stage)
            api.create_repo(repo, repo_type=hub.REPO_TYPE, exist_ok=True)
            api.upload_folder(
                repo_id=repo,
                folder_path=Path(tmp),
                repo_type=hub.REPO_TYPE,
                path_in_repo=HUB_DIR,
                commit_message=f"legacy_cases snapshot {digest[:12]} ({hub_get.human(size)})",
                parent_commit=head,
            )
        listed = hub_get.resolve_revision(api, repo)
    except (hub_get.GetError, OSError) as exc:
        raise CasesRefError(f"{repo}: uploading {repo_path} failed: {exc}") from exc
    remote = next((f for f in _list(api, repo, listed) if f.rel == name), None)
    if remote is None or not _same_remote(remote, digest, size, legacy):
        raise CasesRefError(
            f"{repo}@{listed[:12]} does not list {repo_path} with the uploaded bytes; "
            f"{REF_FILE} not written"
        )
    return listed
