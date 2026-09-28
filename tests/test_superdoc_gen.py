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


def test_parse_manifest_reads_the_pool_key(tmp_path):
    """A Word-corpus pool (`pools/<set>_pairs.csv`) carries the Word stem as `key`."""
    pool = tmp_path / "sources_pairs.csv"
    pool.write_text(
        "key,base,next,base_name,next_name,docx,pdf,state\n"
        "0123456789_a__vs__abcdef0123_b_redline_fedcba9876,clean/docx/0123456789_a,clean/docx/abcdef0123_b,a,b,"
        "clean/docx/0123456789_a__vs__abcdef0123_b_redline_fedcba9876.docx,clean/pdf/0123456789_a__vs__abcdef0123_b_redline_fedcba9876.pdf,clean\n"
    )
    (pair,) = superdoc_gen.parse_manifest(pool, {"ok"})
    assert (pair.base, pair.next) == ("clean/docx/0123456789_a", "clean/docx/abcdef0123_b")
    assert pair.key == "0123456789_a__vs__abcdef0123_b_redline_fedcba9876"


def test_output_name_is_the_key_plus_the_tool_when_the_pool_has_a_key():
    key = "0123456789_a__vs__abcdef0123_b_redline_fedcba9876"
    keyed = superdoc_gen.Pair(base="clean/docx/0123456789_a", next="clean/docx/abcdef0123_b", key=key)
    assert superdoc_gen.output_names(keyed, "superdoc") == [f"{key}_superdoc.docx"]
    legacy = superdoc_gen.Pair(base="a_x", next="b_y")
    assert superdoc_gen.output_names(legacy, "superdoc") == ["a_x_b_y_superdoc_redline.docx"]
