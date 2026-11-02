"""Upload Apryse's DOCX→PDF outputs on fixture set v1 to the results dataset; verify (#100).

    PYTHONPATH=src .venv/bin/python results/docx_to_pdf_v1_apryse/hub_upload.py --pdf-dir DIR [--dry-run]

Lands under ``outputs/docx_to_pdf_v1_apryse/`` of ``hub.RESULTS_REPO``: ``pdf/`` (the 2,925
PDFs ``bench docx-to-pdf --tool apryse`` wrote, named ``<state>__<stem>.pdf``, demo-key
watermark included), ``full.json`` (the raw scores, the record), ``stamp_matched.json`` (the
labelled normalisation), this script and ``MANIFEST.sha256.json`` over all of it. Word's PDFs,
the oracle, are fixture-set files (``bench fixtures get v1``) and are not uploaded here.
One ``upload_folder`` commit whose parent is the head read before staging; then every file is
checked with ``hub.verify_uploaded``. Nothing local is deleted.
"""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path

from neurotic_docx_bench import hub

HERE = Path(__file__).resolve().parent
REPO_PREFIX = 'outputs/docx_to_pdf_v1_apryse'
EXPECTED = 2925


def stage(root: Path, pdf_dir: Path) -> int:
    pdfs = sorted(p for p in pdf_dir.iterdir() if p.suffix == '.pdf' and not p.name.startswith('.'))
    if len(pdfs) != EXPECTED:
        raise SystemExit(f'{pdf_dir}: {len(pdfs)} PDFs, expected {EXPECTED}')
    (root / 'pdf').mkdir(parents=True)
    for p in pdfs:
        os.link(p, root / 'pdf' / p.name)
    for name in ('full.json', 'stamp_matched.json', 'hub_upload.py'):
        os.link(HERE / name, root / name)
    hub.write_manifest(root, path=root / hub.MANIFEST_NAME, files=hub.build_manifest(root))
    return sum(1 for _ in hub.iter_files(root))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pdf-dir', type=Path, required=True)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    root = Path(tempfile.mkdtemp(prefix='hub-d2p-apryse.', dir=HERE.parent))
    try:
        n = stage(root, a.pdf_dir)
        size = sum(p.stat().st_size for p in hub.iter_files(root))
        print(f'staged {n} files, {size / 1e6:.0f} MB', flush=True)
        if a.dry_run:
            return
        api = hub.default_api()
        head = api.repo_info(hub.RESULTS_REPO, repo_type=hub.REPO_TYPE).sha
        api.upload_folder(repo_id=hub.RESULTS_REPO, repo_type=hub.REPO_TYPE, folder_path=root,
                          path_in_repo=REPO_PREFIX, parent_commit=head,
                          commit_message=f'docx_to_pdf_v1_apryse: apryse-sdk 12.2.1 on fixture set v1 ({n} files)')
        bad = hub.verify_uploaded(root, api=api, repo_id=hub.RESULTS_REPO, path_in_repo=REPO_PREFIX)
        if bad:
            raise SystemExit(f'{len(bad)} file(s) missing or different on the hub: {bad[:10]}')
        print(f'verified {n} files on {hub.RESULTS_REPO}/{REPO_PREFIX}', flush=True)
    finally:
        shutil.rmtree(root)


if __name__ == '__main__':
    main()
