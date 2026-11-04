"""The pages package: the shown-page renderer (plan 7.4, issue #131).

``neurotic_docx_bench.pages.render`` is the gh-pages ``_build`` rendering moved
onto main: the first ``min(12, page count)`` pages of a PDF at 180 DPI, 16
colours, lossless WebP. The ``pages.pdf`` it once wrote beside them is gone
(#149). The imports are lazy on purpose — ``neurotic_docx_bench.pages`` stays
cheap to import.
"""

from __future__ import annotations

from neurotic_docx_bench.pages.render import (
    COLORS,
    DEFAULT_DPI,
    IMAGE_NAME,
    MANIFEST_NAME,
    MAX_PAGES,
    WEBP_METHOD,
    CaseResult,
    LaneReport,
    PageImage,
    RenderError,
    RenderResult,
    encode_webp,
    page_count,
    render_lane,
    render_pages,
    sha256_file,
    shown_pages,
)

__all__ = [
    "COLORS",
    "DEFAULT_DPI",
    "IMAGE_NAME",
    "MANIFEST_NAME",
    "MAX_PAGES",
    "WEBP_METHOD",
    "CaseResult",
    "LaneReport",
    "PageImage",
    "RenderError",
    "RenderResult",
    "encode_webp",
    "page_count",
    "render_lane",
    "render_pages",
    "sha256_file",
    "shown_pages",
]
