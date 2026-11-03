"""Upload this run's tool outputs, Word PDFs and scores to the results dataset; verify; prune.

    uv run python results/redlines_0929_full/hub_upload.py --dry-run
    uv run python results/redlines_0929_full/hub_upload.py            # upload + verify
    uv run python results/redlines_0929_full/hub_upload.py --prune    # upload + verify + delete

Everything lands under ``outputs/redlines_0929_full/`` of ``hub.RESULTS_REPO``:

- ``<tool>/docx``: each tool's redlines; ``<tool>/pdf_by_word``: those redlines rendered by Word.
- ``<tool>/{accepted,rejected}/src``: the redlines of the track selections;
  ``<tool>/{accepted,rejected}/by_word``: Word's accept-all / reject-all of them, docx + PDF.
- ``<tool>/meta``: the tool folder's own JSON/CSV (generate failures and timings, shard lists).
- ``fresh_compares``: the Word compares made again for this run (``compare_regen/out``, docx+pdf),
  the oracles of the ``fresh`` rows. The other oracles are ``corpus/word`` files, not uploaded here.
- the run's CSVs, score JSONs, scripts and ``RUN.md``; ``MANIFEST.sha256.json`` over all of it.

Files are hard-linked into a staging folder and uploaded one ``upload_folder`` commit per
subfolder; ``upload_folder`` is the only hub check, sending what the hub does not hold. ``--prune``
then checks every file with ``hub.verify_uploaded`` (LFS sha256 or git blob sha1) and deletes the
tool outputs (``PRUNE``) only when every file verified; Word's own files (``corpus/word``,
``compare_regen``) are never touched.
The manifest carries the previous manifest's entries this run does not restage, as they are.

The staging, the upload and the verification live in ``neurotic_docx_bench.hub_outputs`` — the
same path the conversion lane uploader and the release's own jubarte lane use, so there is one
upload path, not three.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from neurotic_docx_bench import hub, hub_outputs
from neurotic_docx_bench.hub_outputs import StaleParentError, next_parent

HERE = Path(__file__).parent
REPO_PREFIX = hub_outputs.REDLINE_PREFIX
FRESH = Path.home() / 'temp/T/compare_regen/out'
# Every tool of the run: the keys of versions.json (to_scores_jsonl.py reads the same).
TOOLS = tuple(json.loads((HERE / 'versions.json').read_text()))
TOOL_DIRS = ('docx', 'pdf_by_word', 'accepted/src', 'accepted/by_word', 'rejected/src', 'rejected/by_word')
TOP_SUFFIXES = hub_outputs.META_SUFFIXES
# docx_rest and docx_sample500 hold symlinks into docxodus/docx; pdf_staged is a byte-identical
# subset of docxodus/pdf_by_word (checked 2026-09-30).
PRUNE = tuple(HERE / t / d for t in TOOLS for d in TOOL_DIRS) + tuple(
    HERE / 'docxodus' / d for d in ('docx_rest', 'docx_sample500', 'pdf_staged'))

__all__ = ['StaleParentError', 'main', 'next_parent', 'stage']


def stage(root: Path, previous=None) -> list[str]:
    """Hard-link every file to upload under ``root``; return the subfolders (one commit each)."""
    if root.exists():
        shutil.rmtree(root)
    subdirs = []
    for t in TOOLS:
        for d in TOOL_DIRS:
            if (HERE / t / d).is_dir():
                subdirs.append(f'{t}/{d}')
        # A tool whose folder is not in this checkout (its outputs were deleted after
        # its upload, or the lane never ran here) has nothing to stage: the hub copy
        # stands, and the manifest carries its entries.
        if (HERE / t).is_dir():
            subdirs.append(f'{t}/meta')
        hub_outputs.stage_redline_lane(root, lane=t, lane_dir=HERE / t, dirs=TOOL_DIRS)
    # Gone locally once uploaded (2026-10-25): the hub copy stands.
    if FRESH.is_dir():
        hub_outputs.stage_tree(root, 'fresh_compares', FRESH)
        subdirs.append('fresh_compares')
    hub_outputs.stage_tree(root, 'run', HERE, suffixes=TOP_SUFFIXES, exclude=('.partial.json',))
    staged = hub.build_manifest(root)
    # upload_folder is the only hub check before the upload: unrestaged entries carry as they are.
    carried = {path: digest for path, digest in (previous or {}).items() if path not in staged}
    hub.write_manifest(root, path=root / 'run' / hub.MANIFEST_NAME, files=staged | carried)
    if previous is not None:
        print(f'manifest: {len(staged)} staged + {len(carried)} carried from the previous manifest', flush=True)
    return subdirs + ['run']


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--staging', type=Path, default=HERE.parent / 'hub_redlines_0929_full')
    ap.add_argument('--dry-run', action='store_true', help='stage and count, upload nothing')
    ap.add_argument('--prune', action='store_true', help='after a clean verify, delete the tool outputs')
    ap.add_argument('--previous-revision', default=None, help='revision of the previous manifest')
    a = ap.parse_args()
    if a.dry_run:
        subdirs = stage(a.staging)
    else:
        # Only the hub saying "not there" means empty; LocalEntryNotFoundError (offline,
        # cache miss) also subclasses EntryNotFoundError and must stop the upload.
        from huggingface_hub.errors import RemoteEntryNotFoundError

        api = hub.default_api()
        api.create_repo(hub.RESULTS_REPO, repo_type=hub.REPO_TYPE, exist_ok=True)
        # Pin every read to a commit: when its HEAD request fails, huggingface_hub serves the
        # cached copy of a branch, which can be older than the listing; a commit's copy cannot.
        head = api.repo_info(hub.RESULTS_REPO, repo_type=hub.REPO_TYPE).sha
        baseline = (
            api.repo_info(hub.RESULTS_REPO, repo_type=hub.REPO_TYPE, revision=a.previous_revision).sha
            if a.previous_revision
            else head
        )
        try:
            local = api.hf_hub_download(
                hub.RESULTS_REPO, f'{REPO_PREFIX}/run/{hub.MANIFEST_NAME}', repo_type=hub.REPO_TYPE, revision=baseline
            )
        except RemoteEntryNotFoundError:
            previous = {}
        else:
            previous = hub.read_manifest(Path(local))

        subdirs = stage(a.staging, previous=previous)
    counts = {s: sum(1 for p in (a.staging / s).iterdir()) for s in subdirs}
    size = sum(p.stat().st_size for p in hub.iter_files(a.staging))
    print(f'staged {sum(counts.values())} files, {size / 1e9:.2f} GB: {counts}', flush=True)
    if a.dry_run:
        return
    # Each commit names its parent: if anyone committed since `head` was read, the hub refuses
    # (412) instead of taking a manifest built from the older commit.
    parent = head
    for s in subdirs:
        message = f'redlines_0929_full: {s} ({counts[s]} files)'
        parent = hub_outputs.upload_folder(
            api=api,
            folder=a.staging / s,
            path_in_repo=f'{REPO_PREFIX}/{s}',
            message=message,
            parent_commit=parent,
        )
        print(f'uploaded {s}', flush=True)
    if a.prune:
        # Local files are deleted only once every staged file is proven on the hub.
        bad = hub.verify_uploaded(a.staging, api=api, repo_id=hub.RESULTS_REPO, path_in_repo=REPO_PREFIX)
        if bad:
            raise SystemExit(f'{len(bad)} file(s) missing or different on the hub, nothing deleted: {bad[:10]}')
        print(f'verified {sum(counts.values())} files on {hub.RESULTS_REPO}/{REPO_PREFIX}', flush=True)
        for d in PRUNE:
            if d.is_dir():
                shutil.rmtree(d)
                print(f'deleted {d}', flush=True)
        shutil.rmtree(a.staging)


if __name__ == '__main__':
    main()
