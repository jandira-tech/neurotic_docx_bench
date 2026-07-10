"""Native SuperDoc (Python SDK) redline generator."""

from __future__ import annotations

import asyncio
import zipfile

import pytest
from helpers import CORPUS

from neurotic_docx_bench import superdoc_gen

MANIFEST = CORPUS / "centralized_mapping.csv"
SOURCE = CORPUS / "docx_source"

try:
    import superdoc  # noqa: F401

    _HAVE_SUPERDOC = True
except Exception:  # pragma: no cover
    _HAVE_SUPERDOC = False

requires_superdoc = pytest.mark.skipif(not _HAVE_SUPERDOC, reason="superdoc-sdk not installed")
requires_manifest = pytest.mark.skipif(not MANIFEST.is_file(), reason="corpus manifest absent")


@requires_manifest
def test_parse_manifest_returns_pairs():
    pairs = superdoc_gen.parse_manifest(MANIFEST, {"ok"})
    assert pairs and all(p.base and p.next for p in pairs)


@requires_superdoc
@requires_manifest
def test_run_batch_produces_tracked_redline(tmp_path):
    ok, failed, _timings = asyncio.run(
        superdoc_gen.run_batch(
            out=tmp_path,
            manifest=MANIFEST,
            source_dir=SOURCE,
            statuses={"ok"},
            limit=1,
            tool="superdoc",
            author="superdoc",
            force=True,
        ),
    )
    assert ok >= 1, failed
    outs = list(tmp_path.glob("*_superdoc_redline.docx"))
    assert len(outs) == 1
    with zipfile.ZipFile(outs[0]) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    assert "<w:ins" in xml or "<w:del" in xml
