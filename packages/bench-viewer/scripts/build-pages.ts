#!/usr/bin/env node
/**
 * Build a bench page from a scores.json.
 *
 *   node packages/bench-viewer/scripts/build-pages.ts <scores.json> <outdir> [--theme <name>]
 *
 * Two themes, one scores file:
 *
 * - `arthur-law` (the default) writes the leaderboard page: the scores,
 *   ranked, with the leader of every table named above it.
 * - `jubarte` writes the jubarte page: the product's own framing, with the
 *   headline cells, the "ours" rows and the affiliation mark.
 *
 * Both write <outdir>/index.html and copy the stylesheets next to it, so the
 * directory opens as a page on its own. No git operations, no network: the
 * file it reads is the file it prints.
 */

import { copyFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  buildLeaderboardPage,
  esc,
  parseScores,
  renderBadge,
  renderHeadlines,
  renderLegend,
  renderMethod,
  renderProvenance,
  renderStates,
  renderTable,
} from "../src/index.ts";
import { requireHttpUrl } from "../src/parse.ts";
import type { Scores } from "../src/types.ts";

/** The stylesheets the page links, copied into the output directory. */
const THEMES = ["tokens.css", "arthur-law.css", "jubarte.css"];

/** The skins the page can wear. */
const THEME_NAMES = ["arthur-law", "jubarte"] as const;

type Theme = (typeof THEME_NAMES)[number];

/** The stylesheet each theme links. */
const THEME_STYLESHEET: Record<Theme, string> = {
  "arthur-law": "arthur-law.css",
  jubarte: "jubarte.css",
};

/** The whole page. Every text value goes through esc(). */
export function renderPage(scores: Scores, stylesheet = "arthur-law.css"): string {
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
<link rel="stylesheet" href="./${esc(stylesheet)}">
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
${renderProvenance(scores.provenance)}
<footer class="mt-72">
<p class="note">Harness and raw records: <a href="${esc(repo)}">neurotic_docx_bench</a>. Per-case viewer: <a href="${esc(viewer)}">${esc(viewer)}</a>. Figures are project-maintained and reproducible, not a neutral third-party benchmark.</p>
</footer>
</main>
</body>
</html>
`;
}

/** The page a theme wears. */
function renderThemePage(scores: Scores, theme: Theme): string {
  if (theme === "jubarte") return renderPage(scores, THEME_STYLESHEET.jubarte);
  return buildLeaderboardPage(scores);
}

/** Read the flags: the theme is the only one there is. */
function readTheme(args: string[]): Theme {
  let theme: string = "arthur-law";
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === "--theme") {
      const value = args[i + 1];
      if (value === undefined) {
        console.error("build-pages.ts: --theme needs a theme name");
        process.exit(2);
      }
      theme = value;
      i++;
    } else if (arg.startsWith("--theme=")) {
      theme = arg.slice("--theme=".length);
    } else {
      console.error(`build-pages.ts: unknown argument ${arg}`);
      process.exit(2);
    }
  }
  if (!THEME_NAMES.includes(theme as Theme)) {
    console.error(`build-pages.ts: unknown theme ${theme}; use ${THEME_NAMES.join(" or ")}`);
    process.exit(2);
  }
  return theme as Theme;
}

const [scoresArg, outArg, ...flagArgs] = process.argv.slice(2);
if (!scoresArg || !outArg) {
  console.error("usage: build-pages.ts <scores.json> <outdir> [--theme arthur-law|jubarte]");
  process.exit(2);
}

const theme = readTheme(flagArgs);
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
await writeFile(join(outDir, "index.html"), renderThemePage(scores, theme), "utf8");
for (const stylesheet of THEMES) {
  await copyFile(
    fileURLToPath(new URL(`../themes/${stylesheet}`, import.meta.url)),
    join(outDir, stylesheet),
  );
}

const summary =
  theme === "jubarte"
    ? `${scores.tables.length} tables, ${scores.headlines.length} headlines, ${scores.states.length} states`
    : `${scores.tables.length} tables, ${scores.tables.filter((t) => t.id.endsWith("-sample")).length} sample tables, ${scores.states.length} states`;
console.log(`${join(outDir, "index.html")}: ${summary}`);
