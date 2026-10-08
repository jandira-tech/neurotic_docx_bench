# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""Reject unusable PDFs and packages whose raster cost exceeds the safety budget."""

import sys

import pymupdf


def inspect_pdf(path: str, dpi: int = 144) -> dict:
    with pymupdf.open(path) as document:
        if document.needs_pass or not 1 <= len(document) <= 500:
            raise ValueError("PDF is encrypted, empty, or exceeds 500 pages")
        pixels = 0
        for page in document:
            rect = page.rect
            area = rect.width * rect.height * (dpi / 72) ** 2
            if area <= 0 or area > 20_000_000:
                raise ValueError("PDF page exceeds raster safety limit")
            pixels += area
            if pixels > 400_000_000:
                raise ValueError("PDF document exceeds raster safety limit")
            page.get_displaylist()
        return {"pages": len(document), "raster_pixels": round(pixels), "dpi": dpi}


if __name__ == "__main__":
    inspect_pdf(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 144)
