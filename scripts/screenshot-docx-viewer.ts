#!/usr/bin/env node
/**
 * Screenshot documents rendered by Office Online.
 *
 * Navigates directly to the Office Online viewer (not the wrapper page) so
 * the screenshot contains ONLY the document — no header, dropdown, or chrome
 * from our worker. Uses full-page capture to scroll through all pages.
 *
 * Usage:
 *   npx tsx scripts/screenshot-docx-viewer.ts --out screenshots/ --docs 5
 *   npx tsx scripts/screenshot-docx-viewer.ts --paths "word_based/docx_source/Strict01.docx"
 *   npx tsx scripts/screenshot-docx-viewer.ts --viewport-only    # visible area only
 *
 * Without --docs or --paths, screenshots all documents in the manifest.
 */

import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { resolve, basename } from "node:path";

const VIEWER_URL = "https://docx-viewer.cicero-im.workers.dev";

// ── arg parsing ──────────────────────────────────────────────
function parseArgs() {
  const args = process.argv.slice(2);
  const opts: {
    out: string;
    docs?: number;
    paths?: string[];
    viewportOnly: boolean;
    width: number;
    height: number;
    wait: number;
  } = { out: "screenshots", viewportOnly: false, width: 1280, height: 1600, wait: 8000 };

  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--out") opts.out = args[++i];
    else if (args[i] === "--docs") opts.docs = parseInt(args[++i], 10);
    else if (args[i] === "--paths") opts.paths = args[++i].split(",");
    else if (args[i] === "--viewport-only") opts.viewportOnly = true;
    else if (args[i] === "--width") opts.width = parseInt(args[++i], 10);
    else if (args[i] === "--height") opts.height = parseInt(args[++i], 10);
    else if (args[i] === "--wait") opts.wait = parseInt(args[++i], 10);
  }
  return opts;
}

async function main() {
  const opts = parseArgs();
  const outDir = resolve(opts.out);
  mkdirSync(outDir, { recursive: true });

  // fetch manifest
  const manifest: string[] = await fetch(`${VIEWER_URL}/manifest.json`).then(
    (r) => r.json(),
  );
  console.log(`Manifest: ${manifest.length} documents`);

  // pick documents
  let targets: string[];
  if (opts.paths) {
    targets = opts.paths;
  } else if (opts.docs) {
    const step = Math.max(1, Math.floor(manifest.length / opts.docs));
    targets = manifest.filter((_, i) => i % step === 0).slice(0, opts.docs);
  } else {
    targets = manifest;
  }
  console.log(`Screenshotting ${targets.length} documents`);
  console.log(`Mode: ${opts.viewportOnly ? "viewport-only" : "full-page (scroll)"}`);

  const browser = await chromium.launch({ headless: true });
  let ok = 0;
  let fail = 0;

  for (let idx = 0; idx < targets.length; idx++) {
    const doc = targets[idx];
    const name = basename(doc, ".docx");
    const shotPath = resolve(outDir, `${name}.png`);

    const srcUrl = `${VIEWER_URL}/${doc}`;
    const ooUrl =
      "https://view.officeapps.live.com/op/view.aspx?src=" +
      encodeURIComponent(srcUrl);

    const tag = `[${idx + 1}/${targets.length}]`;
    console.log(`${tag} ${name}`);

    const page = await browser.newPage({
      viewport: { width: opts.width, height: opts.height },
    });

    try {
      // Navigate directly to Office Online — no wrapper chrome.
      await page.goto(ooUrl, { waitUntil: "load", timeout: 45000 });

      // Wait for the document canvas to appear inside the viewer.
      // OO renders pages as <img> or <canvas> inside a scroll container.
      await page.waitForSelector("canvas, img[src*='Graphic'], .WACImageContainer", {
        timeout: 30000,
      }).catch(() => {});

      // Extra settle time for lazy-rendered pages.
      await page.waitForTimeout(opts.wait);

      if (!opts.viewportOnly) {
        // Gradually scroll through the document to force lazy page rendering,
        // then scroll back to top before the full-page screenshot.
        await autoScroll(page);
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.waitForTimeout(2000);

        await page.screenshot({ path: shotPath, fullPage: true });
      } else {
        await page.screenshot({ path: shotPath, fullPage: false });
      }

      console.log(`  saved ${shotPath}`);
      ok++;
    } catch (err) {
      console.error(`  FAILED: ${(err as Error).message}`);
      try {
        await page.screenshot({ path: shotPath });
        console.log(`  saved (partial) ${shotPath}`);
      } catch {
        console.error(`  could not save screenshot`);
      }
      fail++;
    } finally {
      await page.close();
    }
  }

  await browser.close();
  console.log(`\nDone. ${ok} succeeded, ${fail} failed.`);
}

/** Scroll through the entire page in steps to trigger lazy rendering. */
async function autoScroll(page: import("playwright").Page) {
  await page.evaluate(async () => {
    await new Promise<void>((resolve) => {
      let scrolled = 0;
      const step = window.innerHeight * 0.8;
      const timer = setInterval(() => {
        window.scrollBy(0, step);
        scrolled += step;
        if (scrolled >= document.body.scrollHeight) {
          clearInterval(timer);
          resolve();
        }
      }, 500);
    });
  });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
