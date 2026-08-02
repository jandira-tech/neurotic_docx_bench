"""Chrome-DevTools (CDP) instrumentation pass for the folio viewer harness.

Drives the same harness contract as the bench's PlaywrightRenderer (goto →
set_input_files → wait for __folioReady/error) but instead of printing PDFs it
captures per-document DevTools metrics:

  - render_ms          upload → readiness wall time
  - page_load_ms       navigation → load event (per fresh context, mirrors bench)
  - Performance.getMetrics before GC (post-render) and after a forced GC
    (HeapProfiler.collectGarbage): JSHeapUsedSize/JSHeapTotalSize, ScriptDuration,
    LayoutDuration, RecalcStyleDuration, TaskDuration, Nodes, JSEventListeners
  - layout_pages       number of .layout-page elements

One JSON line per document → --out. Fresh browser context per doc (same isolation
as the bench renderer, so a stale readiness flag can never leak between docs).

Usage:
  uv run python scripts/cdp_folio_measure.py \
    --url http://127.0.0.1:5175/harness.html \
    --docx-dir corpus/word_based/docx_source \
    --tool folio-base --benchmark visual_rendering \
    --out results-compare/cdp_folio-base_visual_rendering.jsonl [--workers 4]
"""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

READINESS_JS = (
    "window.__folioReady === true || "
    "document.querySelectorAll('.layout-page').length > 0"
)
ERROR_JS = "window.__folioError"
METRIC_KEYS = (
    "JSHeapUsedSize",
    "JSHeapTotalSize",
    "ScriptDuration",
    "LayoutDuration",
    "RecalcStyleDuration",
    "TaskDuration",
    "Nodes",
    "JSEventListeners",
    "Documents",
    "Frames",
)


def _metrics(cdp) -> dict:
    got = {m["name"]: m["value"] for m in cdp.send("Performance.getMetrics")["metrics"]}
    return {k: got.get(k) for k in METRIC_KEYS}


def measure_one(browser, url: str, docx: Path, timeout_ms: int) -> dict:
    row: dict = {"doc": docx.stem, "input_bytes": docx.stat().st_size, "ok": False}
    ctx = browser.new_context()
    try:
        page = ctx.new_page()
        cdp = ctx.new_cdp_session(page)
        cdp.send("Performance.enable")
        t_nav = time.perf_counter()
        page.goto(url, wait_until="load")
        row["page_load_ms"] = round((time.perf_counter() - t_nav) * 1000, 1)
        row["metrics_baseline"] = _metrics(cdp)

        t0 = time.perf_counter()
        page.set_input_files("#fileInput", str(docx))
        settled = page.wait_for_function(
            f"() => {{ const e = ({ERROR_JS}); if (e) return 'error'; "
            f"if ({READINESS_JS}) return 'ready'; return false; }}",
            timeout=timeout_ms,
        )
        row["render_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        tag = settled.json_value()
        if tag == "error":
            row["error"] = page.evaluate(f"String({ERROR_JS} || '')")[:400]
            return row
        row["layout_pages"] = page.evaluate(
            "document.querySelectorAll('.layout-page').length",
        )
        row["metrics_after_render"] = _metrics(cdp)
        cdp.send("HeapProfiler.enable")
        cdp.send("HeapProfiler.collectGarbage")
        row["metrics_after_gc"] = _metrics(cdp)
        row["ok"] = True
    except Exception as exc:  # noqa: BLE001 — one bad doc must not kill the batch
        row.setdefault("error", str(exc)[:400])
    finally:
        ctx.close()
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--docx-dir", required=True)
    ap.add_argument("--tool", required=True)
    ap.add_argument("--benchmark", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--timeout-ms", type=int, default=90000)
    args = ap.parse_args()

    docs = sorted(Path(args.docx_dir).glob("*.docx"))
    if args.limit:
        docs = docs[: args.limit]
    if not docs:
        print("no docx found")
        return 1

    from playwright.sync_api import sync_playwright

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []

    def worker(shard: list[Path]) -> list[dict]:
        got: list[dict] = []
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                for d in shard:
                    got.append(measure_one(browser, args.url, d, args.timeout_ms))
            finally:
                browser.close()
        return got

    n = max(1, min(args.workers, len(docs)))
    shards: list[list[Path]] = [[] for _ in range(n)]
    for i, d in enumerate(docs):
        shards[i % n].append(d)
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=n) as pool:
        for res in pool.map(worker, shards):
            rows.extend(res)
    wall_s = time.perf_counter() - t0

    stamp = {"tool": args.tool, "benchmark": args.benchmark}
    with out.open("w") as fh:
        for r in sorted(rows, key=lambda r: r["doc"]):
            fh.write(json.dumps({**stamp, **r}) + "\n")

    ok = [r for r in rows if r["ok"]]
    fails = len(rows) - len(ok)
    if ok:
        med = sorted(r["render_ms"] for r in ok)[len(ok) // 2]
        heap = sorted(r["metrics_after_gc"]["JSHeapUsedSize"] for r in ok)[len(ok) // 2]
        print(
            f"{args.tool}/{args.benchmark}: n={len(ok)} fail={fails} "
            f"median render {med:.0f}ms · median post-GC heap {heap / 1e6:.1f}MB "
            f"· wall {wall_s:.0f}s → {out}",
        )
    else:
        print(f"{args.tool}/{args.benchmark}: ALL {fails} failed → {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
