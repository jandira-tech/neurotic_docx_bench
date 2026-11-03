"""The results dataset's ``outputs/`` tree: one staging and upload path (plan 7, #143).

Three uploaders write that tree:

* the conversion lane uploader (``results/convert_860/hub_upload.py``),
* the redline lane uploader (``results/redlines_0929_full/hub_upload.py``),
* the release's own jubarte lane (the ``publish`` stage of
  ``neurotic_docx_bench.jubarte_release_info``).

They share the code here, so the layout, the manifest, the parent-commit check
and the verification are **one** path, not three.

Two layouts live under ``outputs/`` of ``hub.RESULTS_REPO``:

* ``outputs/convert_860/<lane>/`` — the lane's candidate PDFs (``pdf/``), the
  report JSON with the per-document scores (the record) and a
  ``MANIFEST.sha256.json`` over all of it;
* ``outputs/redlines_0929_full/<tool>/`` — the tool's redlines (``docx/``),
  Word's export of them (``pdf_by_word/``) and the lane's own meta files
  (``meta/``).

The release's own lane is published by :func:`publish_release`, which records
the commit it landed on in the release evidence
(``results/release_<v>_evidence/release_info/hub_outputs.json``).  The release
shards' ``files`` links resolve against **that** revision
(:func:`files_base`), never against a moving branch.
"""

from __future__ import annotations

import csv
import json
import os
import re
import shutil
from collections.abc import Collection, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from neurotic_docx_bench import hub

#: The results dataset's conversion lanes.
CONVERT_PREFIX = "outputs/convert_860"
#: The results dataset's redline lanes.
REDLINE_PREFIX = "outputs/redlines_0929_full"
#: The lane folders the redline uploader publishes.
REDLINE_LANE_DIRS = ("docx", "pdf_by_word")
#: The suffixes a lane's own meta files carry (the redline uploader's TOP_SUFFIXES).
META_SUFFIXES = frozenset({".csv", ".json", ".py", ".sh", ".md"})
#: The evidence file the publish stage writes.
EVIDENCE_NAME = "hub_outputs.json"


class LaneError(RuntimeError):
    """A lane cannot be published as it stands."""


class StaleParentError(RuntimeError):
    """Someone else committed to the hub while this run was uploading."""


class PinnedRevisionMissing(RuntimeError):
    """No pinned Hugging Face revision for the release's file links."""


def next_parent(api, parent, info, message):
    """The commit an upload made, or ``parent`` when it made none.

    An upload that changes nothing makes no commit, skips the ``parent_commit``
    check and returns the branch head, which may be someone else's commit. A
    large folder lands as several commits, ``message (part N)``
    (huggingface_hub 2.0), so every commit between ``parent`` and the head must
    carry our message, alone or with its part number (#103).
    """
    if info.oid == parent:
        return parent
    history = api.list_repo_commits(hub.RESULTS_REPO, repo_type=hub.REPO_TYPE, revision=info.oid)
    part = re.compile(rf"{re.escape(message)}( \(part \d+\))?")
    for commit in history:
        if commit.commit_id == parent:
            return info.oid
        if not part.fullmatch(commit.title):
            break
    raise StaleParentError(
        f"the hub moved to {info.oid} while uploading on {parent}; nothing more uploaded"
    )


def _link_or_copy(src: Path, dst: Path) -> None:
    """Hardlink ``src`` onto ``dst``, or copy the bytes when the link fails."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dst)
        return
    except OSError:
        pass
    shutil.copyfile(src, dst)


# ---- the conversion lane --------------------------------------------------


def convert_lane_pdfs(pdf_dir: Path, report: Path, *, tool: str | None = None) -> list[Path]:
    """The lane's candidate PDFs, checked against the report's own count.

    The PDF count is the report's own: a vendor that refused some documents
    (docxodus 15.0.0 verifies what it prints and writes no PDF for 38 of the
    860) wrote fewer PDFs than the set has, and those documents are scored 0
    under intent-to-treat. The manifest and the report together say so.
    """
    data = json.loads(Path(report).read_text(encoding="utf-8"))
    tools = data.get("tools") or {}
    row = tools.get(tool) if tool else None
    if row is None and tools:
        row = next(iter(tools.values()))
    expected = int((row or {}).get("n_scored") or 0)
    pdf_dir = Path(pdf_dir)
    pdfs = sorted(
        p for p in pdf_dir.iterdir() if p.suffix == ".pdf" and not p.name.startswith(".")
    )
    if len(pdfs) != expected:
        raise LaneError(f"{pdf_dir}: {len(pdfs)} PDFs, the report scored {expected}")
    return pdfs


def stage_convert_lane(
    root: Path,
    *,
    pdf_dir: Path,
    report: Path,
    script: Path | None = None,
) -> list[str]:
    """The conversion lane's files, hardlinked into ``root``.

    ``pdf/`` holds the lane's candidate PDFs, the report JSON (the record), the
    uploader script (when given) and ``MANIFEST.sha256.json`` over all of it.
    The lane's name is the caller's business: it is the folder this tree is
    published under (``outputs/convert_860/<lane>/``).
    Returns the staged paths, relative to ``root``.
    """
    root = Path(root)
    report = Path(report)
    pdfs = convert_lane_pdfs(pdf_dir, report)
    (root / "pdf").mkdir(parents=True, exist_ok=True)
    staged: list[str] = []
    for pdf in pdfs:
        _link_or_copy(pdf, root / "pdf" / pdf.name)
        staged.append(f"pdf/{pdf.name}")
    _link_or_copy(report, root / report.name)
    staged.append(report.name)
    if script is not None:
        script = Path(script)
        _link_or_copy(script, root / script.name)
        staged.append(script.name)
    hub.write_manifest(root, path=root / hub.MANIFEST_NAME, files=hub.build_manifest(root))
    staged.append(hub.MANIFEST_NAME)
    return staged


def convert_case_files(staging: Path) -> set[str]:
    """The staged conversion lane's case files: the candidate PDFs, one per case.

    These are the paths the release shards' ``files`` links name, so a lane
    whose staged PDFs and linked files differ is a link that would 404.
    """
    staging = Path(staging)
    return {
        p.relative_to(staging).as_posix()
        for p in sorted((staging / "pdf").glob("*.pdf"))
        if p.is_file()
    }


# ---- the redline lane -----------------------------------------------------


def stage_redline_lane(
    root: Path,
    *,
    lane: str,
    lane_dir: Path,
    dirs: Sequence[str] = REDLINE_LANE_DIRS,
) -> list[str]:
    """The redline lane's files, hardlinked into ``root``.

    ``<lane>/docx`` and ``<lane>/pdf_by_word`` are the lane's redlines and
    Word's export of them; ``<lane>/meta`` holds the lane's own JSON/CSV. A
    folder the lane does not have is left out (the hub copy stands).
    Returns the staged paths, relative to ``root``.
    """
    root = Path(root)
    lane_dir = Path(lane_dir)
    staged: list[str] = []
    for name in dirs:
        src = lane_dir / name
        if not src.is_dir():
            continue
        dst = root / lane / name
        dst.mkdir(parents=True, exist_ok=True)
        for f in sorted(src.iterdir()):
            if f.is_file() and not f.name.startswith((".", "~$")):
                _link_or_copy(f, dst / f.name)
                staged.append(f"{lane}/{name}/{f.name}")
    if lane_dir.is_dir():
        meta = root / lane / "meta"
        meta.mkdir(parents=True, exist_ok=True)
        for f in sorted(lane_dir.iterdir()):
            if f.is_file() and f.suffix in META_SUFFIXES:
                _link_or_copy(f, meta / f.name)
                staged.append(f"{lane}/meta/{f.name}")
    return staged


def redline_case_files(staging: Path, lane: str | None = None) -> set[str]:
    """The staged redline lane's case files: Word's export of each redline.

    These are the paths the release shards' ``files`` links name, so a lane
    whose staged PDFs and linked files differ is a link that would 404.
    """
    staging = Path(staging)
    out: set[str] = set()
    for pdf in sorted(staging.glob("*/pdf_by_word/*.pdf")):
        rel = pdf.relative_to(staging).as_posix()
        if lane is None or rel.startswith(f"{lane}/"):
            out.add(rel)
    return out


def stage_tree(
    root: Path,
    rel: str,
    src: Path,
    *,
    suffixes: Collection[str] | None = None,
    exclude: Sequence[str] = (),
) -> list[str]:
    """Every file under ``src``, hardlinked into ``root/rel``.

    ``suffixes`` keeps only those extensions; ``exclude`` drops the files whose
    name ends with one of the given strings. Returns the staged paths,
    relative to ``root``.
    """
    root = Path(root)
    src = Path(src)
    dst = root / rel
    dst.mkdir(parents=True, exist_ok=True)
    staged: list[str] = []
    for f in sorted(src.iterdir()):
        if not f.is_file() or f.name.startswith((".", "~$")):
            continue
        if suffixes is not None and f.suffix not in suffixes:
            continue
        if any(f.name.endswith(suffix) for suffix in exclude):
            continue
        _link_or_copy(f, dst / f.name)
        staged.append(f"{rel}/{f.name}")
    return staged


# ---- the upload ------------------------------------------------------------


def upload_folder(
    *,
    api,
    folder: Path,
    path_in_repo: str,
    message: str,
    parent_commit: str,
) -> str:
    """Upload one folder as one commit; return the commit it landed on.

    The commit's parent is the one the caller read: a concurrent upload is
    refused (412) instead of silently overwritten. An upload that changes
    nothing makes no commit and keeps the parent.
    """
    info = api.upload_folder(
        repo_id=hub.RESULTS_REPO,
        repo_type=hub.REPO_TYPE,
        folder_path=folder,
        path_in_repo=path_in_repo,
        commit_message=message,
        parent_commit=parent_commit,
    )
    return next_parent(api, parent_commit, info, message)


def verify_lane(*, api, folder: Path, path_in_repo: str) -> tuple[str, ...]:
    """The staged files the hub does not hold (or holds differently)."""
    return hub.verify_uploaded(
        folder, api=api, repo_id=hub.RESULTS_REPO, path_in_repo=path_in_repo
    )


# ---- the release's own lane -----------------------------------------------


def release_convert_lane(version: str) -> str:
    """The hub folder of the release's own conversion lane."""
    return f"jubarte_{version}"


def release_redline_lane(version: str) -> str:
    """The hub folder of the release's own redline lane."""
    return f"jubarte-{version}"


def publish_release(
    root: Path,
    version: str,
    *,
    api=None,
    staging: Path | None = None,
) -> dict[str, Any]:
    """Upload the release's own jubarte outputs; verify; record the revision.

    Two lanes, the layout the vendor lanes use:

    * ``outputs/convert_860/jubarte_<v>/`` — the conversion set's candidate
      PDFs (``pdf/``), the report JSON (the record) and a
      ``MANIFEST.sha256.json``;
    * ``outputs/redlines_0929_full/jubarte-<v>/`` — the redline set's redlines
      (``docx/``), Word's export of them (``pdf_by_word/``) and the lane's own
      meta files (``meta/``).

    Every file is verified with ``hub.verify_uploaded``; the commit the upload
    landed on is recorded in the release evidence
    (``results/release_<v>_evidence/release_info/hub_outputs.json``), so the
    release shards' file links resolve against a pinned revision.
    """
    root = Path(root)
    api = api or hub.default_api()
    ev = root / "results" / f"release_{version}_evidence"
    convert_dir = ev / "convert_work" / "jubarte" / "candidate"
    convert_report = ev / f"docx_to_pdf_jubarte_{version}_sample.json"
    redline_dir = root / "results" / "redlines_0929_full" / release_redline_lane(version)
    convert_lane = release_convert_lane(version)
    redline_lane = release_redline_lane(version)
    staging = Path(staging) if staging is not None else root / "results" / "hub" / f"jubarte-{version}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    paths: list[str] = []
    files = 0
    revision = api.repo_info(hub.RESULTS_REPO, repo_type=hub.REPO_TYPE).sha

    # the conversion lane: one folder, one commit
    convert_root = staging / "convert_860"
    staged = stage_convert_lane(
        convert_root,
        pdf_dir=convert_dir,
        report=convert_report,
    )
    _refuse_stray_renders(ev, version, convert_dir, staged)
    convert_path = f"{CONVERT_PREFIX}/{convert_lane}"
    revision = upload_folder(
        api=api,
        folder=convert_root,
        path_in_repo=convert_path,
        message=(
            f"convert_860: jubarte {version} on the fixed conversion set "
            f"({len(staged)} files)"
        ),
        parent_commit=revision,
    )
    bad = verify_lane(api=api, folder=convert_root, path_in_repo=convert_path)
    if bad:
        raise LaneError(
            f"{len(bad)} file(s) missing or different on the hub under {convert_path}: {list(bad)[:10]}"
        )
    paths.append(convert_path)
    files += len(staged)

    # the redline lane: the redlines, Word's export of them, the lane's meta
    redline_root = staging / "redlines"
    staged = stage_redline_lane(redline_root, lane=redline_lane, lane_dir=redline_dir)
    for name in (*REDLINE_LANE_DIRS, "meta"):
        sub = redline_root / redline_lane / name
        if not sub.is_dir():
            continue
        rel = f"{REDLINE_PREFIX}/{redline_lane}/{name}"
        count = sum(1 for _ in hub.iter_files(sub))
        revision = upload_folder(
            api=api,
            folder=sub,
            path_in_repo=rel,
            message=f"redlines_0929_full: {redline_lane}/{name} ({count} files)",
            parent_commit=revision,
        )
        bad = verify_lane(api=api, folder=sub, path_in_repo=rel)
        if bad:
            raise LaneError(
                f"{len(bad)} file(s) missing or different on the hub under {rel}: {list(bad)[:10]}"
            )
        paths.append(rel)
        files += count

    evidence = {
        "repo": hub.RESULTS_REPO,
        "revision": revision,
        "paths": paths,
        "verified": True,
        "n_files": files,
        "uploaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    write_evidence(root, version, evidence)
    # the staged copies are throwaway: the hub copy and the local originals stand
    shutil.rmtree(staging, ignore_errors=True)
    return evidence


def _refuse_stray_renders(ev: Path, version: str, candidate: Path, staged: Sequence[str]) -> None:
    """Refuse a render the release's own set does not name.

    The release shards link the set's fixtures, one file each: a render left
    over from another run would be published and linked by nobody (and the
    set's own renders are the ones the cases point at).
    """
    listing = ev / f"sample_conversion_{version}.csv"
    if not listing.is_file():
        return
    with listing.open(newline="", encoding="utf-8") as handle:
        stems = {row.get("stem") or "" for row in csv.DictReader(handle)}
    stray = sorted(
        path.removeprefix("pdf/").removesuffix(".pdf")
        for path in staged
        if path.startswith("pdf/") and path.removeprefix("pdf/").removesuffix(".pdf") not in stems
    )
    if stray:
        raise LaneError(
            f"{candidate}: {len(stray)} render(s) are not in the release's own set "
            f"(first: {stray[0]}) — a stale render would be published and linked by nobody; "
            "re-run the convert stage or remove it"
        )


# ---- the release evidence -------------------------------------------------


def evidence_path(root: Path, version: str) -> Path:
    """Where the release's hub evidence lives (its own evidence folder)."""
    return (
        Path(root)
        / "results"
        / f"release_{version}_evidence"
        / "release_info"
        / EVIDENCE_NAME
    )


def write_evidence(root: Path, version: str, evidence: dict[str, Any]) -> Path:
    """Write the release's hub evidence; return the file written."""
    path = evidence_path(root, version)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return path


def read_evidence(root: Path, version: str) -> dict[str, Any] | None:
    """The release's hub evidence, or None when there is none."""
    path = evidence_path(root, version)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def pinned_revision(root: Path, version: str) -> str | None:
    """The hub commit the release's outputs landed on, or None."""
    data = read_evidence(root, version) or {}
    revision = data.get("revision")
    return str(revision) if revision else None


def files_base(root: Path, version: str) -> str:
    """The public resolve base of the release's pinned revision.

    Never a moving branch: the links in the release shards must not drift when
    the dataset moves. A release with no recorded revision is refused — the
    caller may pass the base explicitly instead.
    """
    revision = pinned_revision(root, version)
    if not revision:
        raise PinnedRevisionMissing(
            f"no pinned Hugging Face revision for release {version}: "
            f"{evidence_path(root, version)} records none — publish the release's outputs "
            "(the publish stage of the release-info flow) or pass the files base explicitly"
        )
    return f"https://huggingface.co/datasets/{hub.RESULTS_REPO}/resolve/{revision}/"
