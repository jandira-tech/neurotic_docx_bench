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

Files are hard-linked into a staging folder, uploaded one ``upload_folder`` commit per subfolder,
then checked by ``hub.verify_uploaded`` (LFS sha256 or git blob sha1 of every file). ``--prune``
deletes the tool outputs (``PRUNE``) only when every file verified; Word's own files
(``corpus/word``, ``compare_regen``) are never touched.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

from neurotic_docx_bench import hub

HERE = Path(__file__).parent
REPO_PREFIX = 'outputs/redlines_0929_full'
FRESH = Path.home() / 'temp/T/compare_regen/out'
# Every tool of the run: the keys of versions.json (to_scores_jsonl.py reads the same).
TOOLS = tuple(json.loads((HERE / 'versions.json').read_text()))
TOOL_DIRS = ('docx', 'pdf_by_word', 'accepted/src', 'accepted/by_word', 'rejected/src', 'rejected/by_word')
TOP_SUFFIXES = {'.csv', '.json', '.py', '.sh', '.md'}
# docx_rest and docx_sample500 hold symlinks into docxodus/docx; pdf_staged is a byte-identical
# subset of docxodus/pdf_by_word (checked 2026-09-30).
PRUNE = tuple(HERE / t / d for t in TOOLS for d in TOOL_DIRS) + tuple(
    HERE / 'docxodus' / d for d in ('docx_rest', 'docx_sample500', 'pdf_staged'))


def stage(root: Path) -> list[str]:
    """Hard-link every file to upload under ``root``; return the subfolders (one commit each)."""
    if root.exists():
        shutil.rmtree(root)
    parts = []
    for t in TOOLS:
        for d in TOOL_DIRS:
            if (HERE / t / d).is_dir():
                parts.append((HERE / t / d, f'{t}/{d}'))
    parts.append((FRESH, 'fresh_compares'))
    for t in TOOLS:
        meta = root / t / 'meta'
        meta.mkdir(parents=True)
        for f in sorted((HERE / t).iterdir()):
            if f.is_file() and f.suffix in TOP_SUFFIXES:
                os.link(f, meta / f.name)
        parts.append((None, f'{t}/meta'))
    for src, rel in parts:
        if src is None:
            continue
        dst = root / rel
        dst.mkdir(parents=True)
        for f in sorted(src.iterdir()):
            if f.is_file() and not f.name.startswith(('.', '~$')):
                os.link(f, dst / f.name)
    top = root / 'run'
    top.mkdir()
    for f in sorted(HERE.iterdir()):
        if f.is_file() and f.suffix in TOP_SUFFIXES and not f.name.endswith('.partial.json'):
            os.link(f, top / f.name)
    hub.write_manifest(root, path=top / hub.MANIFEST_NAME)
    return [rel for _, rel in parts] + ['run']


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--staging', type=Path, default=HERE.parent / 'hub_redlines_0929_full')
    ap.add_argument('--dry-run', action='store_true', help='stage and count, upload nothing')
    ap.add_argument('--prune', action='store_true', help='after a clean verify, delete the tool outputs')
    a = ap.parse_args()
    subdirs = stage(a.staging)
    counts = {s: sum(1 for p in (a.staging / s).iterdir()) for s in subdirs}
    size = sum(p.stat().st_size for p in hub.iter_files(a.staging))
    print(f'staged {sum(counts.values())} files, {size / 1e9:.2f} GB: {counts}', flush=True)
    if a.dry_run:
        return
    api = hub.default_api()
    api.create_repo(hub.RESULTS_REPO, repo_type=hub.REPO_TYPE, exist_ok=True)
    for s in subdirs:
        api.upload_folder(repo_id=hub.RESULTS_REPO, repo_type=hub.REPO_TYPE, folder_path=a.staging / s,
                          path_in_repo=f'{REPO_PREFIX}/{s}',
                          commit_message=f'redlines_0929_full: {s} ({counts[s]} files)')
        print(f'uploaded {s}', flush=True)
    bad = hub.verify_uploaded(a.staging, api=api, repo_id=hub.RESULTS_REPO, path_in_repo=REPO_PREFIX)
    if bad:
        raise SystemExit(f'{len(bad)} file(s) missing or different on the hub, nothing deleted: {bad[:10]}')
    print(f'verified {sum(counts.values())} files on {hub.RESULTS_REPO}/{REPO_PREFIX}', flush=True)
    if a.prune:
        for d in PRUNE:
            if d.is_dir():
                shutil.rmtree(d)
                print(f'deleted {d}', flush=True)
        shutil.rmtree(a.staging)


if __name__ == '__main__':
    main()
