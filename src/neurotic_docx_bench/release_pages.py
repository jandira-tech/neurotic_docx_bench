"""Stage a release's shown pages and write the later R2 upload plan.

The renderer itself is :mod:`neurotic_docx_bench.pages.render`: the first
``min(12, page count)`` pages at 180 DPI, quantised to 16 colours and stored
as lossless WebP.  This module only chooses the release's lanes and cases,
stages their pages under ``out/release-pages/<version>/`` and writes
``r2-plan.json``.

The plan is deliberately not an uploader.  Its keys are exactly the non-null
``Case.pages`` paths of the release shards; every entry records the local
file, its sha256 and its byte count.  A later release step may upload that
plan, but this module never talks to R2.
"""

from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from bench_ops.models import CaseShard, CasesIndex
from neurotic_docx_bench.ledger import cases as cases_emit
from neurotic_docx_bench.ledger.release_cases import ReleaseKind, ReleaseSource
from neurotic_docx_bench.pages import render as pages_render

DEFAULT_FILES_BASE = "https://huggingface.co/datasets/arthrod/neurotic_docx_bench/resolve/main/"

_PAGE_NAME = re.compile(r"^page[-_](\d{3,})\.webp$")


class ReleasePageError(RuntimeError):
    """A release page could not be staged."""


@dataclass(frozen=True)
class PageStageReport:
    """What the staging run produced."""

    index: CasesIndex
    shards: list[CaseShard]
    plan: dict[str, dict[str, object]]
    plan_path: Path
    rendered: int
    pages: int
    bytes: int
    page_scores: dict[str, object]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _underscore_render(out_dir: Path, shown: tuple[int, ...]) -> list[Path]:
    """Give a rendered lane the release's ``page_NNN.webp`` spelling.

    ``pages.render`` writes ``page-NNN.webp`` and records those names in its
    manifest.  The release contract's paths use the historical underscore
    spelling, so the files and the manifest are renamed together.  The
    manifest therefore still describes the bytes on disk and the render stays
    resumable.
    """
    manifest_path = out_dir / pages_render.MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    keep_pages = set(shown)
    entries = [
        entry for entry in (manifest.get("images") or []) if int(entry.get("page", 0)) in keep_pages
    ]
    renamed: list[Path] = []
    for entry in entries:
        old = out_dir / str(entry["name"])
        new = out_dir / old.name.replace("-", "_", 1)
        if old != new:
            old.replace(new)
        entry["name"] = new.name
        renamed.append(new)
    keep = {path.name for path in renamed}
    for path in sorted(out_dir.glob("page*.webp")):
        if path.name not in keep:
            path.unlink(missing_ok=True)
    manifest["shown"] = list(shown)
    manifest["images"] = entries
    manifest_path.write_text(
        json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return renamed


def _render_source(task: tuple[ReleaseSource, Path]) -> dict[str, object]:
    """Render one lane (a process-pool task)."""
    source, out_root = task
    lane_dir = out_root / source.kind / source.case / source.lane
    if source.pdf is None:
        return {
            "kind": source.kind,
            "case": source.case,
            "lane": source.lane,
            "error": "the local source PDF is missing",
            "images": [],
        }
    try:
        result = pages_render.render_pdf(source.pdf, lane_dir)
        keep = result.shown[: source.pages]
        if len(keep) != source.pages:
            raise pages_render.RenderError(
                f"the PDF rendered {len(result.shown)} page(s), the shard needs {source.pages}"
            )
        if len(keep) < len(result.shown):
            # The reference defines the case's shown vector.  A candidate may
            # have more pages, but the release shard (and its upload plan)
            # carry only the reference's shown pages.
            pages_pdf = lane_dir / pages_render.PAGES_PDF_NAME
            pages_pdf.unlink(missing_ok=True)
            pages_render.write_pages_pdf(
                source.pdf,
                pages_pdf,
                keep,
                result.input_sha256,
            )
            manifest_path = lane_dir / pages_render.MANIFEST_NAME
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["pages_pdf"] = {
                "name": pages_render.PAGES_PDF_NAME,
                "bytes": pages_pdf.stat().st_size,
                "sha256": _sha256(pages_pdf),
            }
            manifest_path.write_text(
                json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8"
            )
        images = _underscore_render(lane_dir, keep)
    except Exception as exc:  # noqa: BLE001 - one bad lane must not kill the pool
        return {
            "kind": source.kind,
            "case": source.case,
            "lane": source.lane,
            "error": f"{type(exc).__name__}: {exc}",
            "images": [],
        }
    return {
        "kind": source.kind,
        "case": source.case,
        "lane": source.lane,
        "error": None,
        "images": [
            {
                "page": image.page,
                "path": str(path),
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
            for image, path in zip(result.images[: len(images)], images, strict=True)
        ],
    }


def _expected_assets(
    shards: list[CaseShard],
) -> dict[tuple[str, str, str], list[str | None]]:
    expected: dict[tuple[str, str, str], list[str | None]] = {}
    for shard in shards:
        kind = "convert" if shard.kind == "conversion" else "redline"
        for case in shard.cases:
            for lane, pages in case.pages.items():
                expected[(kind, case.case, lane)] = list(pages)
    return expected


def stage_release_pages(
    root: Path,
    version: str,
    *,
    out: Path | None = None,
    files_base: str = DEFAULT_FILES_BASE,
    vendor_root: Path | None = None,
    kinds: tuple[ReleaseKind, ...] = ("convert", "redline"),
    limit: int | None = None,
    jobs: int = 1,
) -> PageStageReport:
    """Render every shown page of a release and write its R2 upload plan.

    Args:
        root: the bench root.
        version: the jubarte release version.
        out: the staging root; ``<root>/out/release-pages/<version>`` by default.
        files_base: the Hugging Face base the release shards' file links use.
        vendor_root: the root holding the vendor refresh work directories;
            ``root`` by default.
        kinds: ``convert`` and/or ``redline``.
        limit: the first N rows of each set (the full sets by default).
        jobs: how many PDFs to render concurrently.

    Returns:
        The stage report, including the exact plan that was written.

    Raises:
        ReleasePageError: when a lane with pages has no local PDF, or a PDF
            rendered a different number of pages than the shard records.
    """
    root = Path(root).resolve()
    out = Path(out) if out is not None else root / "out" / "release-pages" / version
    out = out.resolve()
    bundle = cases_emit.build_release(
        root,
        version,
        files_base=files_base,
        vendor_root=vendor_root,
        kinds=kinds,
        limit=limit,
    )
    expected = _expected_assets(bundle.shards)

    tasks: list[tuple[ReleaseSource, Path]] = []
    errors: list[str] = []
    for source in bundle.sources:
        paths = expected.get((source.kind, source.case, source.lane), [])
        wanted = [path for path in paths if path is not None]
        if not wanted:
            continue
        if source.pdf is None:
            errors.append(
                f"{source.kind}/{source.case}/{source.lane}: the local source PDF is missing"
            )
            continue
        tasks.append((source, out))

    outcomes: list[dict[str, object]] = []
    if jobs > 1 and len(tasks) > 1:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            outcomes = list(pool.map(_render_source, tasks))
    else:
        outcomes = [_render_source(task) for task in tasks]

    plan: dict[str, dict[str, object]] = {}
    rendered = 0
    page_count = 0
    total_bytes = 0
    for outcome in outcomes:
        kind = str(outcome["kind"])
        case = str(outcome["case"])
        lane = str(outcome["lane"])
        error = outcome.get("error")
        if error:
            errors.append(f"{kind}/{case}/{lane}: {error}")
            continue
        images = cast(list[dict[str, object]], outcome.get("images") or [])
        paths = expected.get((kind, case, lane), [])
        wanted = [path for path in paths if path is not None]
        if len(images) != len(wanted):
            errors.append(
                f"{kind}/{case}/{lane}: rendered {len(images)} page(s), the shard records {len(wanted)}"
            )
            continue
        for image in images:
            page = image.get("page")
            byte_count = image.get("bytes")
            if not isinstance(page, int) or not isinstance(byte_count, int):
                errors.append(f"{kind}/{case}/{lane}: the renderer returned an invalid image row")
                continue
            key = wanted[page - 1]
            plan[key] = {
                "path": str(image["path"]),
                "sha256": str(image["sha256"]),
                "bytes": byte_count,
            }
            page_count += 1
            total_bytes += byte_count
        rendered += 1

    if errors:
        raise ReleasePageError("; ".join(errors))

    expected_keys = {path for paths in expected.values() for path in paths if path is not None}
    if set(plan) != expected_keys:
        missing = sorted(expected_keys - set(plan))
        extra = sorted(set(plan) - expected_keys)
        raise ReleasePageError(
            f"the R2 plan does not match the shard assets: {len(missing)} missing, {len(extra)} extra"
        )

    out.mkdir(parents=True, exist_ok=True)
    # The validated shards travel with the staged pages: the release flow can
    # publish this exact bundle without rebuilding it from a different input.
    texts = cases_emit.release_texts(bundle.index, bundle.shards)
    for relative, text in texts.items():
        path = out / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    plan_path = out / "r2-plan.json"
    plan_path.write_text(
        json.dumps(plan, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return PageStageReport(
        index=bundle.index,
        shards=bundle.shards,
        plan=plan,
        plan_path=plan_path,
        rendered=rendered,
        pages=page_count,
        bytes=total_bytes,
        page_scores=cast(dict[str, object], bundle.report.get("page_scores") or {}),
    )
