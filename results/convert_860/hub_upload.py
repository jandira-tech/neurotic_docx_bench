"""Upload the convert_860 lane's DOCX→PDF outputs and scores to the results dataset (#129).

    PYTHONPATH=src .venv/bin/python results/convert_860/hub_upload.py --lane soffice_26.8.2.2 \
        --pdf-dir results/soffice_26.8.2.2_work/candidate \
        --report results/docx_to_pdf_soffice_26.8.2.2_set-convert_860.json

One lane per vendor/version. The lane's files land under
``outputs/convert_860/<lane>/`` of ``hub.RESULTS_REPO``: ``pdf/`` (the 860 candidate
PDFs the vendor wrote, named ``<state>__<stem>.pdf``), the report JSON with the
per-document scores (the record), this script and ``MANIFEST.sha256.json`` over all
of it. Word's PDFs, the oracle, are corpus files (the fixtures dataset) and are not
uploaded here.

``upload_folder`` is the only check before the upload (huggingface_hub 2.0 removed
``upload_large_folder``); it batches and resumes. The upload's parent commit is the
head read before staging, so a concurrent upload is not silently overwritten. Every
file is then checked with ``hub.verify_uploaded``, which reads the hub's own tree
listing and compares hashes. Nothing local is deleted.

The staging, the upload and the verification live in
``neurotic_docx_bench.hub_outputs`` — the same path the redline lane uploader and
the release's own jubarte lane use, so there is one upload path, not three.
"""

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

from neurotic_docx_bench import hub, hub_outputs

HERE = Path(__file__).resolve().parent
REPO_PREFIX = hub_outputs.CONVERT_PREFIX

# lane -> (the report JSON under results/, a one-line note for the commit message)
LANES: dict[str, str] = {
    "soffice_26.8.2.2": "LibreOffice 26.8.2.2",
    "docxide-pdf_0.18.4": "docxide-pdf 0.18.4",
    "docxodus_15.0.0": "@docxodus/export 15.0.0 (docxodus 15.0.0)",
    "apryse_12.2.1": "apryse-sdk 12.2.1 (demo key: output watermarked)",
}


def stage(root: Path, lane: str, pdf_dir: Path, report: Path) -> int:
    """The lane's files, hardlinked into a staging tree, with its manifest.

    The PDF count is the report's own: a vendor that refused some documents
    (docxodus 15.0.0 verifies what it prints and writes no PDF for 38 of the
    860) wrote fewer PDFs than the set has, and those documents are scored 0
    under intent-to-treat. The manifest and the report together say so.
    """
    hub_outputs.stage_convert_lane(
        root, pdf_dir=pdf_dir, report=report, script=HERE / "hub_upload.py"
    )
    return sum(1 for _ in hub.iter_files(root))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lane", required=True, choices=sorted(LANES))
    ap.add_argument("--pdf-dir", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not a.report.is_file():
        raise SystemExit(f"report not found: {a.report}")
    lane = a.lane
    root = Path(tempfile.mkdtemp(prefix=f"hub-convert860-{lane}.", dir=HERE.parent))
    try:
        try:
            n = stage(root, lane, a.pdf_dir, a.report)
        except hub_outputs.LaneError as exc:
            raise SystemExit(str(exc)) from exc
        size = sum(p.stat().st_size for p in hub.iter_files(root))
        print(f"staged {n} files, {size / 1e6:.0f} MB", flush=True)
        if a.dry_run:
            return
        api = hub.default_api()
        head = api.repo_info(hub.RESULTS_REPO, repo_type=hub.REPO_TYPE).sha
        hub_outputs.upload_folder(
            api=api,
            folder=root,
            path_in_repo=f"{REPO_PREFIX}/{lane}",
            message=f"convert_860: {LANES[lane]} on the 860-document set ({n} files)",
            parent_commit=head,
        )
        bad = hub_outputs.verify_lane(
            api=api, folder=root, path_in_repo=f"{REPO_PREFIX}/{lane}"
        )
        if bad:
            raise SystemExit(f"{len(bad)} file(s) missing or different on the hub: {bad[:10]}")
        print(f"verified {n} files on {hub.RESULTS_REPO}/{REPO_PREFIX}/{lane}", flush=True)
    finally:
        shutil.rmtree(root)


if __name__ == "__main__":
    main()
