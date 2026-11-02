#!/usr/bin/env node
/**
 * Build the leaderboard page from a scores.json.
 *
 *   node packages/bench-viewer/scripts/build-pages.ts <scores.json> <outdir>
 *
 * Writes <outdir>/index.html — badge, legend, headlines, every table, the
 * states and the method — and copies themes/tokens.css and
 * themes/arthur-law.css next to it, so the directory opens as a page on its
 * own. No git operations, no network: the file it reads is the file it
 * prints.
 */

import { copyFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  esc,
  parseScores,
  renderBadge,
  renderHeadlines,
  renderLegend,
  renderMethod,
  renderStates,
  renderTable,
} from "../src/index.ts";
import { requireHttpUrl } from "../src/parse.ts";
import type { Scores } from "../src/types.ts";

/** The stylesheets the page links, copied into the output directory. */
const THEMES = ["tokens.css", "arthur-law.css"];

function provenanceBlock(scores: Scores): string {
  const entries = Object.entries(scores.provenance);
  if (entries.length === 0) return "";
  const rows = entries
    .map(
      ([key, values]) =>
        `<li><span class="mono">${esc(key)}</span> <span class="muted">${values.map((v) => esc(v)).join(" · ")}</span></li>`,
    )
    .join("\n");
  return `<section class="mt-72">
<div class="section-head"><h2>Provenance</h2><span>where every number came from</span></div>
<ul class="bench-list mt-12">
${rows}
</ul>
</section>`;
}

/** The whole page. Every text value goes through esc(). */
export function renderPage(scores: Scores): string {
  const repo = requireHttpUrl(scores.repo, "repo");
  const viewer = requireHttpUrl(scores.viewer, "viewer");
  const tables = scores.tables.map((t) => renderTable(t)).join("\n");
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Benchmark · neurotic_docx_bench</title>
<meta name="description" content="DOCX conversion and redlines scored against Microsoft Word, failures included.">
<meta name="generator" content="@jandira-tech/bench-viewer">
<link rel="stylesheet" href="./tokens.css">
<link rel="stylesheet" href="./arthur-law.css">
</head>
<body>
<main class="wrap">
<header class="mt-56">
${renderBadge(scores)}
<h1 class="h1">Scored against Word, failures included.</h1>
<p class="lead">The oracle is Word’s own PDF export of each document (SHA-pinned). A converter’s PDF is scored 0–100 by pixel similarity; redlines are additionally opened in Word and compared against Word’s own compare. Medians and means count a failed document as 0, so no tool gains by skipping a hard one.</p>
</header>
${renderLegend()}
${renderHeadlines(scores.headlines)}
${tables}
${renderStates(scores.states, { heading: "By corpus state" })}
${renderMethod(scores.method)}
${provenanceBlock(scores)}
<footer class="mt-72">
<p class="note">Harness and raw records: <a href="${esc(repo)}">neurotic_docx_bench</a>. Per-case viewer: <a href="${esc(viewer)}">${esc(viewer)}</a>. Figures are project-maintained and reproducible, not a neutral third-party benchmark.</p>
</footer>
</main>
</body>
</html>
`;
}

const [scoresArg, outArg] = process.argv.slice(2);
if (!scoresArg || !outArg) {
  console.error("usage: build-pages.ts <scores.json> <outdir>");
  process.exit(2);
}

const scoresPath = resolve(scoresArg);
const outDir = resolve(outArg);

let parsed: unknown;
try {
  parsed = JSON.parse(await readFile(scoresPath, "utf8"));
} catch (err) {
  console.error(`${scoresPath}: ${(err as Error).message}`);
  process.exit(1);
}

// A scores file that does not hold scores says which field is wrong.
let scores: ReturnType<typeof parseScores>;
try {
  scores = parseScores(parsed);
} catch (err) {
  console.error(`${scoresPath}: ${(err as Error).message}`);
  process.exit(1);
}

await mkdir(outDir, { recursive: true });
await writeFile(join(outDir, "index.html"), renderPage(scores), "utf8");
for (const theme of THEMES) {
  await copyFile(
    fileURLToPath(new URL(`../themes/${theme}`, import.meta.url)),
    join(outDir, theme),
  );
}

console.log(
  `${join(outDir, "index.html")}: ${scores.tables.length} tables, ${scores.headlines.length} headlines, ${scores.states.length} states`,
);
