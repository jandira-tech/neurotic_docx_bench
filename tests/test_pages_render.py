"""The shown-page renderer (plan 7.4, issue #131).

The gh-pages `_build` rendering moved onto main: the first ``min(12, page count)``
pages of a PDF, rasterised by MuPDF at 180 DPI, quantised to 16 colours (median
cut) and stored as lossless WebP (method 4). The ``pages.pdf`` the renderer once
wrote beside them is gone (#149): the source PDF is already linked on Hugging
Face, so the second copy only added release size.

Everything here runs on synthetic PDFs built with PyMuPDF under ``tmp_path``: no
corpus, no Word, no network, no mutool.
"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pytest
from PIL import Image

from neurotic_docx_bench import cli
from neurotic_docx_bench.pages import render as pages_render
from neurotic_docx_bench.pages.render import RenderError, render_lane, render_pages

LETTER = (612.0, 792.0)  # US letter in points


def make_pdf(path: Path, pages: int = 1, size: tuple[float, float] = LETTER) -> Path:
    """A synthetic PDF: ``pages`` letter pages, each with a word and a filled box."""
    import pymupdf

    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page(width=size[0], height=size[1])
        page.insert_text((72, 72), f"page {i + 1}", fontsize=24)
        page.draw_rect(pymupdf.Rect(72, 100, 300, 200), fill=(0.75, 0.75, 0.75))
    doc.save(path)
    doc.close()
    return path


def webp_chunks(data: bytes) -> list[str]:
    """The RIFF chunk four-codes of a WebP file (``VP8L`` is the lossless one)."""
    chunks: list[str] = []
    offset = 12
    while offset + 8 <= len(data):
        code = data[offset : offset + 4].decode("ascii", "replace")
        size = int.from_bytes(data[offset + 4 : offset + 8], "little")
        chunks.append(code)
        offset += 8 + size + (size & 1)
    return chunks


def lane_csv(path: Path, rows: list[tuple[str, str]]) -> Path:
    """A lane CSV: a ``case`` column and the PDF path column the renderer reads."""
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["case", "word_pdf"])
        writer.writerows(rows)
    return path


# -- the single PDF ----------------------------------------------------------------------


def test_render_caps_at_twelve_pages(tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "fifteen.pdf", pages=15)
    result = render_pages(pdf, tmp_path / "out")
    assert result.page_count == 15
    assert result.shown == tuple(range(1, 13))
    assert len(result.images) == 12
    assert [image.name for image in result.images] == [f"page-{i:03d}.webp" for i in range(1, 13)]
    on_disk = sorted(p.name for p in (tmp_path / "out").glob("page-*.webp"))
    assert on_disk == [f"page-{i:03d}.webp" for i in range(1, 13)]


def test_render_keeps_every_page_of_a_short_pdf(tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "two.pdf", pages=2)
    result = render_pages(pdf, tmp_path / "out")
    assert result.page_count == 2
    assert result.shown == (1, 2)
    assert len(result.images) == 2
    assert (tmp_path / "out" / "page-002.webp").is_file()


def test_render_rasterises_at_180_dpi(tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "letter.pdf", pages=1)
    result = render_pages(pdf, tmp_path / "out")
    assert result.dpi == 180
    with Image.open(tmp_path / "out" / "page-001.webp") as image:
        assert abs(image.width - 1530) <= 1  # 8.5in at 180 DPI
        assert abs(image.height - 1980) <= 1  # 11in at 180 DPI


def test_images_hold_at_most_sixteen_colours(tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "colour.pdf", pages=2)
    render_pages(pdf, tmp_path / "out")
    for image in sorted((tmp_path / "out").glob("page-*.webp")):
        with Image.open(image) as opened:
            colours = opened.convert("RGB").getcolors(maxcolors=4096)
        assert colours is not None, f"{image.name} holds more than 4096 colours"
        assert len(colours) <= 16


def test_images_are_lossless_webp(tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "lossless.pdf", pages=1)
    render_pages(pdf, tmp_path / "out")
    data = (tmp_path / "out" / "page-001.webp").read_bytes()
    assert data[:4] == b"RIFF"
    assert data[8:12] == b"WEBP"
    chunks = webp_chunks(data)
    assert "VP8L" in chunks, f"not a lossless WebP: {chunks}"
    assert "VP8 " not in chunks
    with Image.open(tmp_path / "out" / "page-001.webp") as image:
        assert image.format == "WEBP"


def test_render_is_deterministic(tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "same.pdf", pages=3)
    first = render_pages(pdf, tmp_path / "a")
    second = render_pages(pdf, tmp_path / "b")
    assert [image.sha256 for image in first.images] == [image.sha256 for image in second.images]
    for image in first.images:
        assert (tmp_path / "a" / image.name).read_bytes() == (tmp_path / "b" / image.name).read_bytes()


def test_render_writes_no_pages_pdf(tmp_path: Path) -> None:
    """#149: the render directory holds the page images and the manifest only."""
    pdf = make_pdf(tmp_path / "one.pdf", pages=2)
    result = render_pages(pdf, tmp_path / "out")
    assert sorted(path.name for path in (tmp_path / "out").iterdir()) == [
        "page-001.webp",
        "page-002.webp",
        "render.json",
    ]
    manifest = json.loads((tmp_path / "out" / "render.json").read_text(encoding="utf-8"))
    assert "pages_pdf" not in manifest
    assert not hasattr(result, "pdf_bytes"), "the report must not carry PDF fields"


def test_render_removes_a_stale_pages_pdf(tmp_path: Path) -> None:
    """A pages.pdf left by a pre-#149 render does not survive a re-render."""
    pdf = make_pdf(tmp_path / "one.pdf", pages=1)
    out = tmp_path / "out"
    out.mkdir()
    (out / "pages.pdf").write_bytes(b"stale")
    render_pages(pdf, out)
    assert not (out / "pages.pdf").exists()


def test_render_resumes_from_a_manifest_that_still_lists_pages_pdf(tmp_path: Path) -> None:
    """A pre-#149 render directory (its manifest carries ``pages_pdf``) still
    resumes: the reuse check reads the images, never the dropped PDF."""
    pdf = make_pdf(tmp_path / "one.pdf", pages=1)
    out = tmp_path / "out"
    first = render_pages(pdf, out)
    manifest_path = out / "render.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["pages_pdf"] = {"name": "pages.pdf", "bytes": 3, "sha256": "0" * 64}
    manifest_path.write_text(
        json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    second = render_pages(pdf, out)
    assert second.reused
    assert [image.sha256 for image in second.images] == [
        image.sha256 for image in first.images
    ]


def test_render_records_the_input_hash_and_sizes(tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "one.pdf", pages=1)
    result = render_pages(pdf, tmp_path / "out")
    assert result.input_sha256 == pages_render.sha256_file(pdf)
    for image in result.images:
        path = tmp_path / "out" / image.name
        assert image.bytes == path.stat().st_size
        assert image.sha256 == pages_render.sha256_file(path)
    assert result.image_bytes == sum(image.bytes for image in result.images)


# -- the lane -----------------------------------------------------------------------------


def test_render_lane_renders_a_lane(tmp_path: Path) -> None:
    root = tmp_path / "root"
    (root / "corpus").mkdir(parents=True)
    for name in ("a", "b", "c"):
        make_pdf(root / "corpus" / f"{name}.pdf", pages=2)
    lane = lane_csv(tmp_path / "lane.csv", [(name, f"corpus/{name}.pdf") for name in ("a", "b", "c")])
    out = tmp_path / "out"
    report = render_lane(lane, "word_pdf", out, 2, root=root)
    assert report.rows == 3
    assert report.rendered == 3
    assert report.reused == 0
    assert report.failed == 0
    assert report.pages == 6
    for name in ("a", "b", "c"):
        assert (out / name / "page-001.webp").is_file()
        assert not (out / name / "pages.pdf").exists()


def test_render_lane_accounts_the_image_bytes(tmp_path: Path) -> None:
    root = tmp_path / "root"
    (root / "corpus").mkdir(parents=True)
    make_pdf(root / "corpus" / "a.pdf", pages=3)
    lane = lane_csv(tmp_path / "lane.csv", [("one", "corpus/a.pdf")])
    out = tmp_path / "out"
    report = render_lane(lane, "word_pdf", out, 1, root=root)
    images = sum(p.stat().st_size for p in (out / "one").glob("page-*.webp"))
    assert report.image_bytes == images
    assert report.bytes == images
    assert not hasattr(report, "pdf_bytes"), "the lane report must not carry PDF fields"


def test_render_lane_resumes_and_skips_unchanged_input(tmp_path: Path) -> None:
    root = tmp_path / "root"
    (root / "corpus").mkdir(parents=True)
    make_pdf(root / "corpus" / "a.pdf", pages=2)
    lane = lane_csv(tmp_path / "lane.csv", [("one", "corpus/a.pdf")])
    out = tmp_path / "out"
    first = render_lane(lane, "word_pdf", out, 1, root=root)
    assert (first.rendered, first.reused) == (1, 0)
    stamp = (out / "one" / "page-001.webp").stat().st_mtime_ns
    second = render_lane(lane, "word_pdf", out, 1, root=root)
    assert (second.rendered, second.reused) == (0, 1)
    assert (out / "one" / "page-001.webp").stat().st_mtime_ns == stamp


def test_render_lane_rerenders_a_changed_input(tmp_path: Path) -> None:
    root = tmp_path / "root"
    (root / "corpus").mkdir(parents=True)
    make_pdf(root / "corpus" / "a.pdf", pages=3)
    lane = lane_csv(tmp_path / "lane.csv", [("one", "corpus/a.pdf")])
    out = tmp_path / "out"
    render_lane(lane, "word_pdf", out, 1, root=root)
    assert (out / "one" / "page-003.webp").is_file()
    # the same path, new bytes: fewer pages
    make_pdf(root / "corpus" / "a.pdf", pages=2)
    report = render_lane(lane, "word_pdf", out, 1, root=root)
    assert (report.rendered, report.reused) == (1, 0)
    assert report.pages == 2
    assert not (out / "one" / "page-003.webp").exists(), "a stale page image must not survive"


def test_render_lane_reports_a_missing_pdf(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    lane = lane_csv(tmp_path / "lane.csv", [("one", "corpus/missing.pdf")])
    report = render_lane(lane, "word_pdf", tmp_path / "out", 1, root=root)
    assert report.failed == 1
    assert report.errors and "missing.pdf" in report.errors[0][1]


# -- the backends -------------------------------------------------------------------------


def test_missing_mutool_is_reported_clearly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BENCH_MUTOOL", str(tmp_path / "no-such-mutool"))
    pdf = make_pdf(tmp_path / "one.pdf", pages=1)
    with pytest.raises(RenderError) as excinfo:
        render_pages(pdf, tmp_path / "out", backend="mutool")
    message = str(excinfo.value)
    assert "mutool" in message
    assert "no-such-mutool" in message


# -- the CLI ------------------------------------------------------------------------------


def test_cli_pages_render_writes_the_pages(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    root = tmp_path / "root"
    (root / "corpus").mkdir(parents=True)
    make_pdf(root / "corpus" / "a.pdf", pages=2)
    lane = lane_csv(tmp_path / "lane.csv", [("one", "corpus/a.pdf")])
    out = tmp_path / "out"
    result = CliRunner().invoke(
        cli.app,
        ["pages", "render", "--set", str(lane), "--column", "word_pdf",
         "--root", str(root), "--out", str(out), "--jobs", "1"],
    )
    assert result.exit_code == 0, result.output
    assert "rendered" in result.output
    assert "pages.pdf" not in result.output
    assert (out / "one" / "page-001.webp").is_file()
    assert not (out / "one" / "pages.pdf").exists()


# -- the ledger reads both spellings -------------------------------------------------------


def test_page_numbers_reads_both_spellings(tmp_path: Path) -> None:
    directory = tmp_path / "assets"
    directory.mkdir()
    (directory / "page_001.webp").write_bytes(b"webp")
    (directory / "page-002.webp").write_bytes(b"webp")
    assert pages_render.page_numbers(directory) == [1, 2]
    (directory / "page_003.webp").write_bytes(b"webp")
    assert pages_render.page_numbers(directory) == [1, 2, 3]
