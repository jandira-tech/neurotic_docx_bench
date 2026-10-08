// SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
// SPDX-License-Identifier: AGPL-3.0-only
import type { PDFDocumentLoadingTask, PDFDocumentProxy } from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
import { pdfGeometry } from '../lib/view-model';

export function mountPdf(slot: HTMLElement, url: string, title: string, prefix: string, interact: () => void): () => void {
  let disposed = false;
  let loading: PDFDocumentLoadingTask | undefined;
  let document: PDFDocumentProxy | undefined;
  let pageNumber = 1;
  let rendering = false;
  const controls = window.document.createElement('div'); controls.className = 'pdf-controls';
  const previous = window.document.createElement('button'); previous.textContent = '←'; previous.setAttribute('aria-label', `Previous page in ${title}`);
  const next = window.document.createElement('button'); next.textContent = '→'; next.setAttribute('aria-label', `Next page in ${title}`);
  const status = window.document.createElement('span'); status.textContent = 'Loading PDF…'; status.setAttribute('role', 'status');
  controls.append(previous, status, next);
  const paper = window.document.createElement('div'); paper.className = 'pdf-paper';
  const canvas = window.document.createElement('canvas'); canvas.setAttribute('role', 'img'); paper.append(canvas);
  slot.replaceChildren(controls, paper); slot.dataset.state = 'loading';
  previous.disabled = next.disabled = true;

  async function render() {
    if (!document || disposed || rendering) return;
    rendering = true; previous.disabled = next.disabled = true;
    try {
      const page = await document.getPage(pageNumber);
      if (disposed) return;
      const original = page.getViewport({ scale: 1 });
      const geometry = pdfGeometry(original.width, original.height, slot.clientWidth - 24, window.devicePixelRatio);
      const viewport = page.getViewport({ scale: geometry.scale });
      canvas.width = Math.ceil(viewport.width); canvas.height = Math.ceil(viewport.height);
      canvas.style.width = `${geometry.width}px`; canvas.style.height = `${geometry.height}px`;
      canvas.setAttribute('aria-label', `${title}, page ${pageNumber} of ${document.numPages}`);
      await page.render({ canvas, viewport }).promise;
      if (disposed) return;
      status.textContent = `Page ${pageNumber} of ${document.numPages}`; slot.dataset.state = 'ready';
      previous.disabled = pageNumber <= 1; next.disabled = pageNumber >= document.numPages;
      page.cleanup();
    } catch {
      if (!disposed) { status.textContent = 'Preview unavailable · use Open PDF'; slot.dataset.state = 'error'; }
    } finally { rendering = false; }
  }
  previous.addEventListener('click', () => { if (pageNumber > 1 && !rendering) { interact(); pageNumber--; void render(); } });
  next.addEventListener('click', () => { if (document && pageNumber < document.numPages && !rendering) { interact(); pageNumber++; void render(); } });
  const observer = new ResizeObserver(() => void render()); observer.observe(slot);
  void (async () => {
    try {
      const pdfjs = await import('pdfjs-dist');
      if (disposed) return;
      pdfjs.GlobalWorkerOptions.workerSrc = workerUrl.startsWith('/_astro/') ? prefix + workerUrl : workerUrl;
      loading = pdfjs.getDocument({ url, maxImageSize: 20_000_000,
        cMapUrl: `${prefix}/_astro/pdfjs/cmaps/`, cMapPacked: true,
        standardFontDataUrl: `${prefix}/_astro/pdfjs/standard_fonts/`, wasmUrl: `${prefix}/_astro/pdfjs/wasm/` });
      document = await loading.promise;
      if (disposed) return;
      if (document.numPages > 500) throw new Error('PDF page limit exceeded');
      await render();
    } catch {
      if (!disposed) { status.textContent = 'Preview unavailable · use Open PDF'; slot.dataset.state = 'error'; }
    }
  })();
  return () => { disposed = true; observer.disconnect(); void loading?.destroy().catch(() => {}); };
}
