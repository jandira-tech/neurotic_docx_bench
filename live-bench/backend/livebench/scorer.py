# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
import json
import sys
import tempfile
from pathlib import Path

from neurotic_docx_bench import pipeline
from PIL import Image, ImageChops, ImageDraw, ImageOps


def score_pair(oracle: str, candidate: str, dpi: int, evidence: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="livebench-score-") as tmp:
        result = pipeline.score_pdf_pair(Path(oracle), Path(candidate), Path(tmp), dpi=int(dpi))
        target = Path(evidence)
        target.with_suffix(".json").write_text(json.dumps(result, allow_nan=False))
        # Persist a compact inspection view; scoring still uses the unchanged benchmark.
        root = Path(tmp) / Path(candidate).stem
        reference_page = sorted((root / "oracle").glob("page_*.png"))[0]
        candidate_page = sorted((root / "candidate").glob("page_*.png"))[0]
        with Image.open(reference_page) as left, Image.open(candidate_page) as right:
            canvas = Image.new("RGB", (1200, 740), "#f5f5f2")
            draw = ImageDraw.Draw(canvas)
            size = (max(left.width, right.width), max(left.height, right.height))
            a, b = Image.new("RGB", size, "white"), Image.new("RGB", size, "white")
            a.paste(left.convert("RGB"), (0, 0))
            b.paste(right.convert("RGB"), (0, 0))
            diff = ImageOps.colorize(ImageChops.difference(a, b).convert("L"), "#ffffff", "#b12448")
            for x, label, page in (
                (20, "Reference - page 1", a),
                (420, "Candidate - page 1", b),
                (820, "Pixel difference - unaligned", diff),
            ):
                draw.text((x, 18), label, fill="#263a30")
                thumb = ImageOps.contain(page, (360, 485))
                canvas.paste(thumb, (x, 44))
            pages = result.get("pages", [])
            draw.text(
                (20, 550),
                "Technical fidelity by common page (page-count penalties and all metrics in JSON)",
                fill="#263a30",
            )
            draw.line((35, 600, 35, 705, 1175, 705), fill="#6d7770", width=1)
            points = [
                (35 + i * 1140 / max(1, len(pages) - 1), 705 - max(0, min(100, page.get("score", 0))))
                for i, page in enumerate(pages)
            ]
            if len(points) > 1:
                draw.line(points, fill="#3d564a", width=3)
            elif points:
                x, y = points[0]
                draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill="#3d564a")
            draw.text((20, 580), "100", fill="#263a30")
            draw.text((20, 710), "0", fill="#263a30")
            canvas.save(target.with_suffix(".png"))
        metrics = {
            "overall": pipeline.overall_from_result(result),
            **{
                key: result.get(key)
                for key in (
                    "overall_score",
                    "overall_score_pagefair",
                    "page_count_oracle",
                    "page_count_candidate",
                    "page_count_mismatch",
                    "ink_jaccard",
                    "text_boundary",
                    "max_break_drift",
                )
            },
        }
        return metrics


if __name__ == "__main__":
    oracle, candidate, dpi, evidence = sys.argv[1:]
    print(json.dumps(score_pair(oracle, candidate, int(dpi), evidence), allow_nan=False))
