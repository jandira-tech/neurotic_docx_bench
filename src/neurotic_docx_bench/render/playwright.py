"""Selector-driven Playwright renderer — render a DOCX in a real web editor/viewer and
print each page to PDF.

Any web editor becomes a bench backend by supplying a ``harness`` profile (no new code),
per PLAN item (1):

    harness:
      url: "http://127.0.0.1:5173/harness/"   # a dev server the user has running
      file_input: "#fileInput"                # <input type=file> selector
      page_selector: ".superdoc-page"         # element that appears once a page is laid out
      readiness_js: "window.__superdocReady"  # JS expression that becomes truthy when stable
      error_js: "window.__rdvError"           # optional: truthy string when the viewer failed
      content_js: "window.__rdvHasContent"    # optional: must be truthy (or omitted) after ready
      reject_blank: true                      # reject near-empty page shells (default true)
      hide: [".comments-layer"]               # optional selectors to hide before capture

For each DOCX: open ``url`` → upload via ``file_input`` → wait for readiness **or** a
harness error (fail-fast) → optional content/blank checks → hide ``hide`` selectors →
``page.pdf()`` → ``<stem>.pdf``.

Timeouts that only wait for page chrome are a common false diagnosis: many viewers set
an error flag (e.g. WASM ``ArgumentNull…part``) long before the page selector appears.
``error_js`` short-circuits those into a real error instead of a 60s TimeoutError.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from neurotic_docx_bench.render.base import RenderReport, RenderResult

if TYPE_CHECKING:
    from playwright.sync_api import Browser, Page


# Default DOM probe used when harness does not supply content_js: non-empty text or
# common content-bearing nodes inside page boxes (or the whole document).
_DEFAULT_CONTENT_JS = """(() => {
  const roots = document.querySelectorAll(
    '[data-page-number], .layout-page, .page, .superdoc-page'
  );
  const nodes = roots.length ? [...roots] : [document.body];
  for (const el of nodes) {
    if (!el) continue;
    if ((el.innerText || '').trim().length > 0) return true;
    if (el.querySelector('img, svg, canvas, table, video')) return true;
  }
  return false;
})()"""


class PlaywrightRenderer:
    name = "playwright"
    harness: dict[str, Any]

    def __init__(self, harness: dict[str, Any] | None) -> None:
        if not harness or not harness.get("url") or not harness.get("file_input"):
            raise ValueError(
                "playwright render requires a harness profile with at least 'url' and "
                "'file_input'",
            )
        self.harness = harness

    def _render_one(
        self, page: Page, docx: Path, out_dir: Path, *, force: bool,
    ) -> RenderResult:
        pdf = out_dir / f"{docx.stem}.pdf"
        t0 = time.perf_counter_ns()
        if not force and pdf.exists():
            return RenderResult(
                source=docx, pdf=pdf, ok=True, skipped=True,
                duration_ns=time.perf_counter_ns() - t0,
            )
        h = self.harness
        timeout_ms = int(h.get("timeout_ms", 30000))
        console_errors: list[str] = []
        page_errors: list[str] = []

        def _on_console(msg: Any) -> None:
            try:
                if msg.type in ("error", "warning"):
                    console_errors.append(f"{msg.type}: {msg.text}"[:400])
            except Exception:  # noqa: BLE001 — never let logging kill the render
                pass

        def _on_pageerror(exc: Any) -> None:
            page_errors.append(str(exc)[:400])

        page.on("console", _on_console)
        page.on("pageerror", _on_pageerror)

        try:
            page.goto(h["url"], wait_until="load")
            page.set_input_files(h["file_input"], str(docx))

            error_js = h.get("error_js")
            readiness_js = h.get("readiness_js")
            page_selector = h.get("page_selector")

            # Fail-fast: resolve as soon as the harness reports ready *or* error.
            # Without this, WASM conversion errors sit in window.__rdvError while
            # Playwright burns the full timeout waiting for [data-page-number].
            if error_js and readiness_js:
                settled = page.wait_for_function(
                    f"() => {{ const e = ({error_js}); "
                    f"if (e) return 'error'; "
                    f"if ({readiness_js}) return 'ready'; "
                    f"return false; }}",
                    timeout=timeout_ms,
                )
                # wait_for_function returns JSHandle; extract the string tag.
                tag = settled.json_value() if hasattr(settled, "json_value") else settled
                if tag == "error" or (isinstance(tag, str) and tag == "error"):
                    err_val = page.evaluate(f"String({error_js} || '')")
                    raise RuntimeError(f"viewer error: {err_val or 'unknown'}")
            else:
                if page_selector:
                    # state="visible" (not "attached"): we rasterise pages, so we need
                    # the element laid out, not merely present in the DOM. "attached"
                    # fires before layout and can produce blank snapshots for redline
                    # badges that exist but haven't rendered yet.
                    page.wait_for_selector(
                        page_selector,
                        timeout=timeout_ms,
                        state="visible",
                    )
                if readiness_js:
                    page.wait_for_function(readiness_js, timeout=timeout_ms)
                # Late error check even without error_js in the wait race.
                if error_js:
                    err_val = page.evaluate(f"String({error_js} || '')")
                    if err_val:
                        raise RuntimeError(f"viewer error: {err_val}")

            # Content gate: reject white page-chrome shells that never painted ink.
            reject_blank = h.get("reject_blank", True)
            content_js = h.get("content_js")
            if reject_blank:
                probe = content_js if content_js else _DEFAULT_CONTENT_JS
                has_content = page.evaluate(probe)
                if not has_content:
                    raise RuntimeError(
                        "blank render: page chrome present but no text/media content"
                    )

            for sel in h.get("hide", []) or []:
                page.eval_on_selector_all(
                    sel, "els => els.forEach(e => (e.style.visibility='hidden'))",
                )
            page.pdf(path=str(pdf), print_background=True)
        except Exception as exc:  # one bad doc must not kill the batch
            detail = str(exc)
            # Attach the last console/page errors so JSONL failures name the real cause
            # (e.g. ArgumentNull…part) instead of only "TimeoutError".
            extras: list[str] = []
            if page_errors:
                extras.append("pageerror=" + page_errors[-1])
            if console_errors:
                extras.append("console=" + console_errors[-1])
            if extras and all(x not in detail for x in extras):
                detail = detail + " | " + " | ".join(extras)
            return RenderResult(
                source=docx, pdf=None, ok=False, error=detail,
                duration_ns=time.perf_counter_ns() - t0,
            )
        elapsed = time.perf_counter_ns() - t0
        if pdf.exists():
            return RenderResult(source=docx, pdf=pdf, ok=True, duration_ns=elapsed)
        return RenderResult(
            source=docx, pdf=None, ok=False, error="no pdf produced", duration_ns=elapsed,
        )

    def to_pdfs(
        self,
        source_dir: Path,
        work_dir: Path,
        *,
        force: bool = False,
        jobs: int = 4,
        timeout: float = 1200.0,
    ) -> RenderReport:
        """Render every ``*.docx`` under ``source_dir`` to ``work_dir/pdf``.

        ``jobs`` is the number of **parallel browser workers**. Playwright's sync
        API is not thread-safe across a shared browser, so each worker owns its own
        ``sync_playwright()`` + Chromium instance and a shard of the corpus.
        ``timeout`` is reserved for future overall-batch budgets (per-doc timeout
        still comes from ``harness.timeout_ms``).
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        from playwright.sync_api import sync_playwright

        del timeout  # per-doc harness.timeout_ms; batch budget not yet applied

        out_dir = work_dir / "pdf"
        out_dir.mkdir(parents=True, exist_ok=True)
        docs: list[Path] = sorted(source_dir.glob("*.docx"))
        if not docs:
            return RenderReport(pdf_dir=out_dir, results=[])

        n_workers = max(1, min(int(jobs), len(docs)))
        # Stable order for the returned RenderReport: index → result.
        ordered: list[RenderResult | None] = [None] * len(docs)

        def _worker(shard: list[tuple[int, Path]]) -> list[tuple[int, RenderResult]]:
            """One thread: one Playwright/Chromium, sequential docs within the shard."""
            shard_out: list[tuple[int, RenderResult]] = []
            with sync_playwright() as pw:
                browser: Browser = pw.chromium.launch()
                try:
                    for idx, docx in shard:
                        context = browser.new_context()
                        try:
                            page: Page = context.new_page()
                            shard_out.append(
                                (idx, self._render_one(page, docx, out_dir, force=force)),
                            )
                        finally:
                            context.close()
                finally:
                    browser.close()
            return shard_out

        # Round-robin shards so slow docs don't all land on worker 0.
        shards: list[list[tuple[int, Path]]] = [[] for _ in range(n_workers)]
        for i, docx in enumerate(docs):
            shards[i % n_workers].append((i, docx))
        shards = [s for s in shards if s]

        if n_workers == 1:
            for idx, result in _worker(shards[0]):
                ordered[idx] = result
        else:
            with ThreadPoolExecutor(max_workers=n_workers) as pool:
                futures = [pool.submit(_worker, shard) for shard in shards]
                for fut in as_completed(futures):
                    for idx, result in fut.result():
                        ordered[idx] = result

        results = [r for r in ordered if r is not None]
        return RenderReport(pdf_dir=out_dir, results=results)
