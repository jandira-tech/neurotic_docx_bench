"""HTML report generation for visual comparisons."""

from __future__ import annotations

import base64
import json
import os
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from PIL import Image

from neurotic_docx_bench.diff import build_diff_overlay

DEFAULT_DIFF_TOLERANCE = 10
DEFAULT_THRESHOLD_PERCENT = 0.0
MISSING_OVERLAY_ALPHA = 0.5
MISSING_IN_BASELINE_COLOR = (0, 100, 255)
MISSING_IN_RESULTS_COLOR = (255, 0, 0)

HTML_TEMPLATE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Word comparison report</title>
    <style>
      :root {
        color-scheme: light;
        --ink-900: #0b1123;
        --ink-800: #111a35;
        --ink-700: #1b2748;
        --ink-600: #273356;
        --ink-200: #d6dbe5;
        --ink-100: #eef1f6;
        --canvas: #b8bfca;
        --card: #ffffff;
        --shadow: 0 8px 30px rgba(10, 18, 38, 0.12);
        --accent: #6ba3ff;
        --accent-strong: #3c7cff;
        --warn: #ffb347;
        --danger: #ff6b6b;
        --ok: #52d4a6;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        font-family: "Inter", "SF Pro Text", "Segoe UI", sans-serif;
        background: var(--canvas);
        color: var(--ink-900);
      }

      header {
        background: linear-gradient(120deg, #0b132b 0%, #101a38 45%, #0e1630 100%);
        color: #f7f9ff;
        padding: 20px 28px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 20px;
      }

      .brand {
        display: flex;
        align-items: center;
        gap: 16px;
      }

      .logo {
        width: 44px;
        height: 44px;
        border-radius: 12px;
        background: radial-gradient(circle at 30% 30%, #8ad1ff 0%, #5f87ff 50%, #5a5edb 100%);
        display: grid;
        place-items: center;
        font-weight: 700;
        letter-spacing: 0.5px;
        color: #f7f9ff;
        overflow: hidden;
      }

      .logo img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }

      .title {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }

      .title .kicker {
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 1.2px;
        color: #a7b3d6;
      }

      .title .name {
        font-size: 20px;
        font-weight: 600;
      }

      .title .run-name {
        font-size: 12px;
        color: #a7b3d6;
        letter-spacing: 0.3px;
      }

      .meta {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
        justify-content: flex-end;
      }

      .pill {
        padding: 6px 12px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.08);
        font-size: 12px;
        color: #e7edff;
      }

      .pill strong {
        color: #ffffff;
        font-weight: 600;
      }

      .controls {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 16px 28px;
        background: rgba(255, 255, 255, 0.72);
        backdrop-filter: blur(8px);
        position: sticky;
        top: 0;
        z-index: 10;
        border-bottom: 1px solid rgba(15, 25, 45, 0.1);
      }

      .search {
        flex: 1;
        max-width: 420px;
        position: relative;
      }

      .search input {
        width: 100%;
        padding: 10px 14px;
        border-radius: 10px;
        border: 1px solid rgba(15, 25, 45, 0.2);
        background: #ffffff;
        font-size: 14px;
      }

      .actions {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
      }

      button {
        border: none;
        border-radius: 10px;
        padding: 10px 14px;
        background: var(--ink-700);
        color: #f2f5ff;
        font-weight: 600;
        cursor: pointer;
        font-size: 13px;
      }

      button.secondary {
        background: #f0f3fa;
        color: var(--ink-700);
        border: 1px solid rgba(15, 25, 45, 0.1);
      }

      main {
        padding: 24px 28px 60px;
      }

      .empty {
        margin-top: 24px;
        padding: 32px;
        background: rgba(255, 255, 255, 0.8);
        border-radius: 18px;
        text-align: center;
        box-shadow: var(--shadow);
      }

      details.group {
        background: var(--card);
        border-radius: 18px;
        padding: 0;
        margin-bottom: 18px;
        box-shadow: var(--shadow);
        border: 1px solid rgba(15, 25, 45, 0.08);
      }

      details.group[open] summary {
        border-bottom: 1px solid rgba(15, 25, 45, 0.08);
      }

      summary {
        list-style: none;
        cursor: pointer;
        padding: 16px 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
      }

      summary::-webkit-details-marker {
        display: none;
      }

      .group-title {
        font-size: 16px;
        font-weight: 600;
        color: var(--ink-700);
      }

      .group-count {
        font-size: 12px;
        padding: 6px 12px;
        background: var(--ink-100);
        border-radius: 999px;
        color: var(--ink-700);
      }

      .group-body {
        padding: 20px;
        display: grid;
        gap: 18px;
      }

      .diff-card {
        background: #fdfdff;
        border-radius: 16px;
        border: 1px solid rgba(15, 25, 45, 0.08);
        padding: 16px;
      }

      .diff-card[data-reason="missing_in_baseline"] {
        border-color: rgba(255, 179, 71, 0.35);
      }

      .diff-card[data-reason="missing_in_results"] {
        border-color: rgba(255, 107, 107, 0.35);
      }

      .diff-card[data-reason="dimension_mismatch"] {
        border-color: rgba(91, 163, 255, 0.35);
      }

      .diff-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 12px;
      }

      .diff-path {
        font-weight: 600;
        color: var(--ink-700);
        font-size: 14px;
      }

      .badges {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
      }

      .badge {
        font-size: 11px;
        padding: 4px 8px;
        border-radius: 999px;
        background: #e7ecf8;
        color: var(--ink-700);
        text-transform: uppercase;
        letter-spacing: 0.6px;
      }

      .badge.diff {
        background: rgba(107, 163, 255, 0.2);
        color: #2c5bd4;
      }

      .badge.warn {
        background: rgba(255, 179, 71, 0.25);
        color: #a05d12;
      }

      .badge.danger {
        background: rgba(255, 107, 107, 0.2);
        color: #b03c3c;
      }

      .badge.mute {
        background: rgba(15, 25, 45, 0.08);
        color: #47506a;
      }

      .image-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
      }

      .image-cell {
        display: grid;
        gap: 8px;
      }

      .image-label {
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #5a678a;
        font-weight: 600;
      }

      .image-frame {
        background: #f0f3fa;
        border-radius: 14px;
        border: 1px solid rgba(15, 25, 45, 0.08);
        padding: 8px;
        display: grid;
        place-items: center;
        min-height: 140px;
      }

      .image-frame img {
        width: 100%;
        height: auto;
        border-radius: 10px;
        box-shadow: 0 10px 24px rgba(15, 25, 45, 0.12);
        background: #ffffff;
      }

      .image-missing {
        font-size: 12px;
        color: #7782a0;
        text-align: center;
      }

      .footer {
        margin-top: 32px;
        text-align: center;
        color: #5f6a86;
        font-size: 12px;
      }

      @media (max-width: 980px) {
        header {
          flex-direction: column;
          align-items: flex-start;
        }

        .controls {
          flex-direction: column;
          align-items: stretch;
        }

        .image-grid {
          grid-template-columns: 1fr;
        }
      }
    </style>
  </head>
  <body>
    <header>
      <div class="brand">
        <div class="logo">__LOGO_MARKUP__</div>
        <div class="title">
          <div class="kicker">SuperDoc Labs</div>
          <div class="name">Word comparison report</div>
          <div class="run-name" id="run-name"></div>
        </div>
      </div>
      <div class="meta" id="meta-pills"></div>
    </header>

    <section class="controls">
      <div class="search">
        <input id="search-input" type="search" placeholder="Filter by path..." />
      </div>
      <div class="actions">
        <button class="secondary" id="expand-all">Expand all</button>
        <button class="secondary" id="collapse-all">Collapse all</button>
      </div>
    </section>

    <main>
      <div id="groups"></div>
      <div class="footer">Generated by SuperDoc Visual Benchmarks</div>
    </main>

    <script id="report-data" type="application/json">__REPORT_JSON__</script>
    <script>
      const report = JSON.parse(document.getElementById('report-data').textContent);
      const assetPrefix = (() => {
        const raw = (report.assetPrefix || '').replace(/\\\\/g, '/');
        if (!raw) return '';
        return raw.endsWith('/') ? raw : raw + '/';
      })();

      const groupsContainer = document.getElementById('groups');
      const metaContainer = document.getElementById('meta-pills');
      const searchInput = document.getElementById('search-input');

      const diffs = report.results.filter((item) => !item.passed);
      const groupMap = new Map();

      const resultsFolderName = (report.resultsFolder || '').replace(/\\\\/g, '/');
      const resultsPrefix = resultsFolderName ? resultsFolderName + '/' : '';

      diffs.forEach((item) => {
        const normalizedPath = item.relativePath.replace(/\\\\/g, '/');
        let trimmedPath = normalizedPath.startsWith(resultsPrefix)
          ? normalizedPath.slice(resultsPrefix.length)
          : normalizedPath;
        const segments = trimmedPath.split('/');
        if (segments[0] === resultsFolderName) {
          segments.shift();
          trimmedPath = segments.join('/');
        }
        const lastSlash = trimmedPath.lastIndexOf('/');
        const dir = lastSlash >= 0 ? trimmedPath.slice(0, lastSlash) : '.';
        const file = lastSlash >= 0 ? trimmedPath.slice(lastSlash + 1) : trimmedPath;
        const baseName = file.replace(/\\.[^.]+$/, '');

        if (!groupMap.has(dir)) {
          groupMap.set(dir, []);
        }

        groupMap.get(dir).push({
          relPath: trimmedPath,
          dir,
          file,
          baseName,
          reason: item.reason || 'pixel_diff',
          diffPercent: item.diffPercent,
          hasDiff: Boolean(item.diffPath),
        });
      });

      const groupEntries = Array.from(groupMap.entries()).sort((a, b) => a[0].localeCompare(b[0]));

      function createMetaPill(label, value) {
        if (value === undefined || value === null || value === '') {
          return null;
        }
        const pill = document.createElement('div');
        pill.className = 'pill';
        pill.innerHTML = label + ' <strong>' + value + '</strong>';
        return pill;
      }

      const metaItems = [
        createMetaPill('Document', report.document || ''),
        createMetaPill('Baseline', report.baselineFolder),
        createMetaPill('SuperDoc', report.superdocVersion || ''),
        createMetaPill('Threshold', report.threshold + '%'),
        createMetaPill('Diffs', diffs.length),
      ].filter(Boolean);

      metaItems.forEach((pill) => metaContainer.appendChild(pill));

      if (report.summary.missingInBaseline) {
        metaContainer.appendChild(createMetaPill('Missing baseline', report.summary.missingInBaseline));
      }
      if (report.summary.missingInResults) {
        metaContainer.appendChild(createMetaPill('Missing results', report.summary.missingInResults));
      }
      const runNameEl = document.getElementById('run-name');
      if (runNameEl) {
        runNameEl.textContent = resultsFolderName || 'run';
      }

      function createBadge(text, className) {
        const badge = document.createElement('span');
        badge.className = 'badge ' + (className || '');
        badge.textContent = text;
        return badge;
      }


      function buildImageCell(label, src, isMissing) {
        const cell = document.createElement('div');
        cell.className = 'image-cell';

        const cellLabel = document.createElement('div');
        cellLabel.className = 'image-label';
        cellLabel.textContent = label;

        const frame = document.createElement('div');
        frame.className = 'image-frame';

        if (isMissing) {
          const missing = document.createElement('div');
          missing.className = 'image-missing';
          missing.textContent = 'Missing';
          frame.appendChild(missing);
        } else if (!src) {
          const missing = document.createElement('div');
          missing.className = 'image-missing';
          missing.textContent = 'Not generated';
          frame.appendChild(missing);
        } else {
          const img = document.createElement('img');
          img.src = src;
          img.alt = label;
          img.loading = 'lazy';
          frame.appendChild(img);
        }

        cell.appendChild(cellLabel);
        cell.appendChild(frame);
        return cell;
      }

      if (diffs.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'empty';
        empty.textContent = 'No diffs detected for this run.';
        groupsContainer.appendChild(empty);
      }

      const fallbackName = report.document || 'Pages';
      const timestamp = report.timestamp ? new Date(report.timestamp) : null;
      const timeLabel = timestamp && !Number.isNaN(timestamp.getTime())
        ? timestamp.toLocaleString()
        : '';
      const rootLabel = timeLabel ? fallbackName + ' · ' + timeLabel : fallbackName;

      groupEntries.forEach(([dir, items]) => {
        const details = document.createElement('details');
        details.className = 'group';
        details.open = false;

        const summary = document.createElement('summary');
        const title = document.createElement('div');
        title.className = 'group-title';
        title.textContent = dir === '.' ? rootLabel : dir;

        const count = document.createElement('div');
        count.className = 'group-count';
        count.textContent = items.length + (items.length === 1 ? ' diff' : ' diffs');

        summary.appendChild(title);
        summary.appendChild(count);
        details.appendChild(summary);

        const body = document.createElement('div');
        body.className = 'group-body';

        items.forEach((item) => {
          const card = document.createElement('article');
          card.className = 'diff-card';
          card.dataset.path = item.relPath.toLowerCase();
          card.dataset.group = dir.toLowerCase();
          card.dataset.reason = item.reason;

          const header = document.createElement('div');
          header.className = 'diff-header';

          const pathLabel = document.createElement('div');
          pathLabel.className = 'diff-path';
          pathLabel.textContent = item.file;

          const badges = document.createElement('div');
          badges.className = 'badges';

          badges.appendChild(createBadge('DIFF', 'diff'));

          header.appendChild(pathLabel);
          header.appendChild(badges);

          const grid = document.createElement('div');
          grid.className = 'image-grid';

          const baseDir = item.dir === '.' ? '' : item.dir + '/';
          const assetBase = assetPrefix + baseDir;
          const diffSrc = item.hasDiff ? assetBase + item.baseName + '-diff.png' : '';
          const baselineSrc = assetBase + item.baseName + '-baseline.png';
          const actualSrc = assetBase + item.baseName + '-actual.png';

          const missingBaseline = item.reason === 'missing_in_baseline';
          const missingActual = item.reason === 'missing_in_results';

          grid.appendChild(buildImageCell('Word', baselineSrc, missingBaseline));
          grid.appendChild(buildImageCell('Diff', diffSrc, !item.hasDiff));
          grid.appendChild(buildImageCell('SuperDoc', actualSrc, missingActual));

          card.appendChild(header);
          card.appendChild(grid);
          body.appendChild(card);
        });

        details.appendChild(body);
        groupsContainer.appendChild(details);
      });

      function applyFilter() {
        const query = searchInput.value.trim().toLowerCase();
        const groups = groupsContainer.querySelectorAll('details.group');
        let visibleCards = 0;

        groups.forEach((group) => {
          const cards = Array.from(group.querySelectorAll('.diff-card'));
          let anyVisible = false;

          cards.forEach((card) => {
            const matches =
              !query ||
              card.dataset.path.includes(query) ||
              card.dataset.group.includes(query);
            card.hidden = !matches;
            if (matches) {
              anyVisible = true;
              visibleCards += 1;
            }
          });

          group.hidden = !anyVisible;
        });
      }

      searchInput.addEventListener('input', applyFilter);

      document.getElementById('expand-all').addEventListener('click', () => {
        document.querySelectorAll('details.group').forEach((group) => {
          group.open = true;
        });
      });

      document.getElementById('collapse-all').addEventListener('click', () => {
        document.querySelectorAll('details.group').forEach((group) => {
          group.open = false;
        });
      });
    </script>
  </body>
</html>
"""


@dataclass(frozen=True)
class DocumentReportInput:
    name: str
    word_pages: list[Path]
    jubarte_pages: list[Path]
    assets_dir: Path
    score_path: Path | None = None


def _copy_image(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _get_logo_data_uri() -> str | None:
    # Package lives at <repo>/src/neurotic_docx_bench/; repo root is parents[2].
    # Guard against shallow paths so this always fails soft (falls back to text logo).
    _parents = Path(__file__).resolve().parents
    repo_root = _parents[2] if len(_parents) > 2 else Path.cwd()
    candidates = [
        os.environ.get("SUPERDOC_REPORT_LOGO"),
        str(Path.cwd() / "superdoc-logo.png"),
        str(Path.cwd() / "assets" / "superdoc-logo.png"),
        str(Path.cwd() / "scripts" / "assets" / "superdoc-logo.png"),
        str(repo_root / "assets" / "superdoc-logo.png"),
    ]

    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if not path.exists():
            continue
        ext = path.suffix.lower()
        mime = "image/png"
        if ext == ".svg":
            mime = "image/svg+xml"
        elif ext in (".jpg", ".jpeg"):
            mime = "image/jpeg"
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{data}"

    return None


def _compute_diff_metrics(word_img: Image.Image, superdoc_img: Image.Image, tolerance: int) -> tuple[int, int, float]:
    word_arr = np.asarray(word_img, dtype=np.int16)
    superdoc_arr = np.asarray(superdoc_img, dtype=np.int16)
    diff = np.abs(word_arr - superdoc_arr)
    diff_mask = np.any(diff > tolerance, axis=2)
    diff_pixels = int(diff_mask.sum())
    total_pixels = int(diff_mask.size)
    diff_percent = (diff_pixels / total_pixels) * 100 if total_pixels else 0.0
    return diff_pixels, total_pixels, diff_percent


def _generate_missing_overlay(
    source: Image.Image, color: tuple[int, int, int], alpha: float = MISSING_OVERLAY_ALPHA,
) -> Image.Image:
    overlay_alpha = max(0, min(int(alpha * 255), 255))
    overlay = Image.new("RGBA", source.size, (*color, overlay_alpha))
    base = source.convert("RGBA")
    blended = Image.alpha_composite(base, overlay)
    return blended.convert("RGB")


def _load_page_scores(score_path: Path | None) -> dict[int, float]:
    if score_path is None or not score_path.exists():
        return {}

    try:
        payload = json.loads(score_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    scores: dict[int, float] = {}
    for page in payload.get("pages", []) or []:
        page_num = page.get("page")
        score = page.get("score")
        if isinstance(page_num, int) and isinstance(score, (int, float)):
            scores[page_num] = float(score)
    return scores


def _build_document_results(
    document: DocumentReportInput, threshold_percent: float, diff_tolerance: int,
) -> tuple[list[dict], dict]:
    results = []
    passed = 0
    failed = 0
    missing_in_baseline = 0
    missing_in_results = 0

    document.assets_dir.mkdir(parents=True, exist_ok=True)
    max_pages = max(len(document.word_pages), len(document.jubarte_pages))
    page_scores = _load_page_scores(document.score_path)

    for idx in range(max_pages):
        word_path = document.word_pages[idx] if idx < len(document.word_pages) else None
        superdoc_path = document.jubarte_pages[idx] if idx < len(document.jubarte_pages) else None
        page_label = f"page_{idx + 1:04d}.png"
        relative_label = f"{document.name}/{page_label}"
        base_name = f"page_{idx + 1:04d}"
        baseline_dst = document.assets_dir / f"{base_name}-baseline.png"
        actual_dst = document.assets_dir / f"{base_name}-actual.png"
        diff_dst = document.assets_dir / f"{base_name}-diff.png"

        if word_path is None and superdoc_path is None:
            continue

        if word_path is None and superdoc_path is not None:
            missing_in_baseline += 1
            failed += 1
            _copy_image(superdoc_path, actual_dst)
            with Image.open(superdoc_path) as img:
                diff_img = _generate_missing_overlay(img, MISSING_IN_BASELINE_COLOR)
                diff_img.save(diff_dst)
                total_pixels = img.size[0] * img.size[1]
            results.append({
                "relativePath": relative_label,
                "passed": False,
                "diffPixels": int(total_pixels),
                "totalPixels": int(total_pixels),
                "diffPercent": 100.0,
                "diffPath": diff_dst.name,
                "reason": "missing_in_baseline",
                "score": page_scores.get(idx + 1),
            })
            continue

        if superdoc_path is None and word_path is not None:
            missing_in_results += 1
            failed += 1
            _copy_image(word_path, baseline_dst)
            with Image.open(word_path) as img:
                diff_img = _generate_missing_overlay(img, MISSING_IN_RESULTS_COLOR)
                diff_img.save(diff_dst)
                total_pixels = img.size[0] * img.size[1]
            results.append({
                "relativePath": relative_label,
                "passed": False,
                "diffPixels": int(total_pixels),
                "totalPixels": int(total_pixels),
                "diffPercent": 100.0,
                "diffPath": diff_dst.name,
                "reason": "missing_in_results",
                "score": page_scores.get(idx + 1),
            })
            continue

        assert word_path is not None
        assert superdoc_path is not None

        with Image.open(word_path) as word_img, Image.open(superdoc_path) as superdoc_img:
            if word_img.size != superdoc_img.size:
                failed += 1
                _copy_image(word_path, baseline_dst)
                _copy_image(superdoc_path, actual_dst)
                diff_img = build_diff_overlay(word_img, superdoc_img)
                diff_img.save(diff_dst)
                total_pixels = word_img.size[0] * word_img.size[1]
                results.append({
                    "relativePath": relative_label,
                    "passed": False,
                    "diffPixels": -1,
                    "totalPixels": int(total_pixels),
                    "diffPercent": 100.0,
                    "diffPath": diff_dst.name,
                    "reason": "dimension_mismatch",
                    "score": page_scores.get(idx + 1),
                })
                continue

            diff_pixels, total_pixels, diff_percent = _compute_diff_metrics(word_img, superdoc_img, diff_tolerance)
            is_passed = diff_percent <= threshold_percent
            if is_passed:
                passed += 1
                # Always refresh the copied rasters — a page passing this cycle
                # must not leave a previous cycle's -actual.png behind (stale
                # rasters have misled visual diagnosis before).
                _copy_image(word_path, baseline_dst)
                _copy_image(superdoc_path, actual_dst)
                results.append({
                    "relativePath": relative_label,
                    "passed": True,
                    "diffPixels": diff_pixels,
                    "totalPixels": total_pixels,
                    "diffPercent": diff_percent,
                    "diffPath": None,
                    "reason": None,
                    "score": page_scores.get(idx + 1),
                })
                continue

            failed += 1
            _copy_image(word_path, baseline_dst)
            _copy_image(superdoc_path, actual_dst)
            diff_img = build_diff_overlay(word_img, superdoc_img)
            diff_img.save(diff_dst)
            results.append({
                "relativePath": relative_label,
                "passed": False,
                "diffPixels": diff_pixels,
                "totalPixels": total_pixels,
                "diffPercent": diff_percent,
                "diffPath": diff_dst.name,
                "reason": "pixel_diff",
                "score": page_scores.get(idx + 1),
            })

    summary = {
        "passed": passed,
        "failed": failed,
        "missingInBaseline": missing_in_baseline,
        "missingInResults": missing_in_results,
        "total": len(results),
    }
    return results, summary


def generate_html_report(
    documents: list[DocumentReportInput],
    version_label: str,
    report_dir: Path,
    run_label: str,
    threshold_percent: float = DEFAULT_THRESHOLD_PERCENT,
    diff_tolerance: int = DEFAULT_DIFF_TOLERANCE,
) -> Path:
    """Generate an HTML diff report and supporting artifacts for a run.

    Returns:
        Path to the generated report.html.
    """
    if not documents:
        raise RuntimeError("No documents provided for HTML report.")

    viewer_dir = report_dir / "report-viewer"
    viewer_dir.mkdir(parents=True, exist_ok=True)

    results = []
    summary = {"passed": 0, "failed": 0, "missingInBaseline": 0, "missingInResults": 0, "total": 0}

    for document in documents:
        doc_results, doc_summary = _build_document_results(
            document, threshold_percent=threshold_percent, diff_tolerance=diff_tolerance,
        )
        results.extend(doc_results)
        summary["passed"] += doc_summary["passed"]
        summary["failed"] += doc_summary["failed"]
        summary["missingInBaseline"] += doc_summary["missingInBaseline"]
        summary["missingInResults"] += doc_summary["missingInResults"]
        summary["total"] += doc_summary["total"]

    document_label = documents[0].name if len(documents) == 1 else f"{len(documents)} documents"
    asset_prefix = os.path.relpath(report_dir, viewer_dir).replace(os.sep, "/")
    if asset_prefix == ".":
        asset_prefix = ""
    elif not asset_prefix.endswith("/"):
        asset_prefix += "/"

    report = {
        "resultsFolder": run_label,
        "baselineFolder": "Word",
        "superdocVersion": version_label,
        "document": document_label,
        "threshold": float(threshold_percent),
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "results": results,
        "summary": summary,
        "assetPrefix": asset_prefix,
    }

    report_json = json.dumps(report).replace("<", "\\u003c")
    logo_data = _get_logo_data_uri()
    if logo_data:
        logo_markup = f'<img src="{logo_data}" alt="SuperDoc logo" />'
    else:
        logo_markup = "SD"

    html = HTML_TEMPLATE.replace("__LOGO_MARKUP__", logo_markup).replace("__REPORT_JSON__", report_json)
    report_path = viewer_dir / "report.html"
    report_path.write_text(html, encoding="utf-8")

    report_json_path = viewer_dir / "report.json"
    report_json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return report_path
