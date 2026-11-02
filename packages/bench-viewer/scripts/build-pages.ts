#!/usr/bin/env node

/**
 * Build the bench pages.
 *
 *   node packages/bench-viewer/scripts/build-pages.ts <scores.json> <outdir> [--theme <name>]
 *   node packages/bench-viewer/scripts/build-pages.ts --release <dir> <outdir> [--scores <file>] [--fonts <dir>]
 *
 * Two modes, one scores file:
 *
 * - `arthur-law` (the default) writes the leaderboard page: the scores,
 *   ranked, with the leader of every table named above it.
 * - `jubarte` writes the jubarte page: the product's own framing, with the
 *   headline cells, the "ours" rows and the affiliation mark.
 *
 * Both write <outdir>/index.html and copy the stylesheets next to it, so the
 * directory opens as a page on its own. No git operations, no network: the
 * file it reads is the file it prints.
 *
 * The `--release` mode builds the whole site from a release bundle: the
 * leaderboard, the two case browsers (conversion and redlines) and the speed
 * page. The pages fetch the release's own files (the cases index, one shard
 * per group, speed.json) instead of carrying the data inside them, so the
 * bundle is the single copy of the numbers.
 *
 * `--fonts <dir>` (release mode only) copies a font directory — the
 * gh-pages site's `_static/fonts` (Manrope, JetBrains Mono as woff2, plus
 * their licences) — into `<outdir>/_static/fonts/`, where `cases.css`'s
 * @font-face rules expect them. Without the flag nothing is copied: the
 * pages fall back to the system stacks and the package ships no binaries.
 */

import type { Dirent } from "node:fs";
import { copyFile, mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { renderCasesPage } from "../src/cases.ts";
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
import { renderSpeedPage } from "../src/speed.ts";
import type { Scores } from "../src/types.ts";

/** The stylesheets the page links, copied into the output directory. */
const THEMES = ["tokens.css", "arthur-law.css", "jubarte.css", "cases.css"];

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

/** The arguments, as the two modes read them. */
interface Args {
  mode: "scores" | "release";
  /** The release bundle (cases index, shards, speed.json). */
  releaseDir?: string;
  /** The scores file. */
  scoresPath?: string;
  /** A font directory to copy into <outdir>/_static/fonts (release mode). */
  fontsDir?: string;
  /** The output directory. */
  outDir: string;
  theme: Theme;
}

function usage(): never {
  console.error(
    "usage: build-pages.ts <scores.json> <outdir> [--theme arthur-law|jubarte]\n" +
      "       build-pages.ts --release <dir> <outdir> [--scores <file>] [--fonts <dir>]",
  );
  process.exit(2);
}

/** Read the flags and the positionals. */
export function readArgs(argv: string[]): Args {
  let releaseDir: string | undefined;
  let scoresPath: string | undefined;
  let fontsDir: string | undefined;
  let theme: Theme = "arthur-law";
  const positional: string[] = [];
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--theme" || arg === "--release" || arg === "--scores" || arg === "--fonts") {
      const value = argv[i + 1];
      if (value === undefined) {
        console.error(`build-pages.ts: ${arg} needs a value`);
        process.exit(2);
      }
      if (arg === "--theme") {
        if (!THEME_NAMES.includes(value as Theme)) {
          console.error(`build-pages.ts: unknown theme ${value}; use ${THEME_NAMES.join(" or ")}`);
          process.exit(2);
        }
        theme = value as Theme;
      } else if (arg === "--release") {
        releaseDir = value;
      } else if (arg === "--fonts") {
        fontsDir = value;
      } else {
        scoresPath = value;
      }
      i++;
      continue;
    }
    if (arg.startsWith("--theme=")) {
      const value = arg.slice("--theme=".length);
      if (!THEME_NAMES.includes(value as Theme)) {
        console.error(`build-pages.ts: unknown theme ${value}; use ${THEME_NAMES.join(" or ")}`);
        process.exit(2);
      }
      theme = value as Theme;
      continue;
    }
    if (arg.startsWith("--release=")) {
      releaseDir = arg.slice("--release=".length);
      continue;
    }
    if (arg.startsWith("--scores=")) {
      scoresPath = arg.slice("--scores=".length);
      continue;
    }
    if (arg.startsWith("--fonts=")) {
      fontsDir = arg.slice("--fonts=".length);
      continue;
    }
    if (arg.startsWith("-")) {
      console.error(`build-pages.ts: unknown argument ${arg}`);
      process.exit(2);
    }
    positional.push(arg);
  }
  if (releaseDir !== undefined) {
    const outDir = positional[0];
    if (!outDir) usage();
    return {
      mode: "release",
      releaseDir,
      outDir,
      theme,
      ...(scoresPath ? { scoresPath } : {}),
      ...(fontsDir ? { fontsDir } : {}),
    };
  }
  if (fontsDir !== undefined) {
    console.error(
      "build-pages.ts: --fonts needs --release (the stylesheet of the plain mode has no fonts)",
    );
    process.exit(2);
  }
  const scores = positional[0];
  const outDir = positional[1];
  if (!scores || !outDir) usage();
  return { mode: "scores", scoresPath: scores, outDir, theme };
}

/** Read a JSON file, naming the file when it is not JSON. */
async function readJson(path: string): Promise<unknown> {
  let text: string;
  try {
    text = await readFile(path, "utf8");
  } catch (err) {
    console.error(`${path}: ${(err as Error).message}`);
    process.exit(1);
  }
  try {
    return JSON.parse(text);
  } catch (err) {
    console.error(`${path}: ${(err as Error).message}`);
    process.exit(1);
  }
}

/** Copy the stylesheets next to the pages. */
async function copyThemes(outDir: string): Promise<void> {
  for (const stylesheet of THEMES) {
    await copyFile(
      fileURLToPath(new URL(`../themes/${stylesheet}`, import.meta.url)),
      join(outDir, stylesheet),
    );
  }
}

/** The compiled modules the pages import. */
const MODULES = ["cases.js", "esc.js", "speed.js"];

/** Copy the compiled modules the pages import. */
async function copyModules(outDir: string): Promise<void> {
  const from = fileURLToPath(new URL("../dist/", import.meta.url));
  const to = join(outDir, "js");
  await mkdir(to, { recursive: true });
  for (const module of MODULES) {
    try {
      await copyFile(join(from, module), join(to, module));
    } catch {
      console.error(
        `${join(from, module)}: missing — build the package first (pnpm --filter @jandira-tech/bench-viewer build)`,
      );
      process.exit(1);
    }
  }
}

/** The release bundle's own files: the index, the shards and speed.json. */
interface ReleaseIndex {
  groups: { kind: string; group: string; count: number; path: string }[];
}

/** Copy the release files the pages fetch. */
async function copyRelease(releaseDir: string, outDir: string): Promise<void> {
  const index = (await readJson(join(releaseDir, "cases", "index.json"))) as ReleaseIndex;
  await mkdir(join(outDir, "release", "cases"), { recursive: true });
  await copyFile(
    join(releaseDir, "cases", "index.json"),
    join(outDir, "release", "cases", "index.json"),
  );
  for (const group of index.groups ?? []) {
    const to = join(outDir, "release", group.path);
    await mkdir(dirname(to), { recursive: true });
    await copyFile(join(releaseDir, group.path), to);
  }
  await copyFile(join(releaseDir, "speed.json"), join(outDir, "release", "speed.json"));
}

/**
 * Copy a font directory into <outdir>/_static/fonts — the gh-pages site's
 * `_static/fonts` (Manrope, JetBrains Mono as woff2, and their licences),
 * which `cases.css`'s @font-face rules point at. The package itself ships
 * no binaries: without --fonts the pages simply fall back to the system
 * stacks.
 */
async function copyFonts(fontsDir: string, outDir: string): Promise<void> {
  let entries: Dirent[];
  try {
    entries = await readdir(fontsDir, { withFileTypes: true });
  } catch (err) {
    console.error(`${fontsDir}: ${(err as Error).message}`);
    process.exit(1);
  }
  const files = entries
    .filter((entry) => entry.isFile())
    .map((entry) => entry.name)
    .sort();
  if (!files.length) {
    console.error(`${fontsDir}: no font files to copy`);
    process.exit(1);
  }
  const to = join(outDir, "_static", "fonts");
  await mkdir(to, { recursive: true });
  for (const name of files) {
    await copyFile(join(fontsDir, name), join(to, name));
  }
  console.log(`${to}: ${files.length} files (${files.join(", ")})`);
}

/** The whole site, from one release bundle. */
async function buildRelease(args: Args): Promise<void> {
  const releaseDir = resolve(args.releaseDir as string);
  const outDir = resolve(args.outDir);
  let scoresPath = args.scoresPath;
  if (!scoresPath) {
    for (const candidate of [
      join(releaseDir, "scores.json"),
      join(releaseDir, "..", "scores.json"),
    ]) {
      try {
        await readFile(candidate, "utf8");
        scoresPath = candidate;
        break;
      } catch {
        /* try the next one */
      }
    }
  }
  if (!scoresPath) {
    console.error(
      `${releaseDir}: no scores.json beside it — pass --scores <file> (the leaderboard needs it)`,
    );
    process.exit(1);
  }

  let scores: ReturnType<typeof parseScores>;
  try {
    scores = parseScores(await readJson(resolve(scoresPath)));
  } catch (err) {
    console.error(`${scoresPath}: ${(err as Error).message}`);
    process.exit(1);
  }

  await mkdir(outDir, { recursive: true });
  await copyThemes(outDir);
  await copyModules(outDir);
  await copyRelease(releaseDir, outDir);
  if (args.fontsDir) await copyFonts(resolve(args.fontsDir), outDir);

  await writeFile(join(outDir, "index.html"), buildLeaderboardPage(scores), "utf8");
  await mkdir(join(outDir, "cases"), { recursive: true });
  await writeFile(
    join(outDir, "cases", "index.html"),
    renderCasesPage({
      kind: "conversion",
      indexUrl: "../release/cases/index.json",
      moduleUrl: "../js/cases.js",
      stylesheet: "../cases.css",
      title: "neurotic_docx_bench: DOCX to PDF vs Microsoft Word",
    }),
    "utf8",
  );
  await mkdir(join(outDir, "redlines"), { recursive: true });
  await writeFile(
    join(outDir, "redlines", "index.html"),
    renderCasesPage({
      kind: "redline",
      indexUrl: "../release/cases/index.json",
      moduleUrl: "../js/cases.js",
      stylesheet: "../cases.css",
      title: "neurotic_docx_bench: Redlines vs Microsoft Word",
    }),
    "utf8",
  );
  await mkdir(join(outDir, "speed"), { recursive: true });
  await writeFile(
    join(outDir, "speed", "index.html"),
    renderSpeedPage({
      speedUrl: "../release/speed.json",
      moduleUrl: "../js/speed.js",
      stylesheet: "../cases.css",
    }),
    "utf8",
  );

  const index = (await readJson(join(releaseDir, "cases", "index.json"))) as ReleaseIndex;
  console.log(
    `${join(outDir, "index.html")}: ${scores.tables.length} tables, ${scores.tables.filter((t) => t.id.endsWith("-sample")).length} sample tables, ${scores.states.length} states`,
  );
  console.log(
    `${join(outDir, "cases", "index.html")}: ${(index.groups ?? []).filter((g) => g.kind === "conversion").length} conversion groups`,
  );
  console.log(
    `${join(outDir, "redlines", "index.html")}: ${(index.groups ?? []).filter((g) => g.kind === "redline").length} redline groups`,
  );
  console.log(`${join(outDir, "speed", "index.html")}: the speed page`);
}

const args = readArgs(process.argv.slice(2));

if (args.mode === "release") {
  await buildRelease(args);
} else {
  const scoresPath = resolve(args.scoresPath as string);
  const outDir = resolve(args.outDir);
  let scores: ReturnType<typeof parseScores>;
  try {
    scores = parseScores(await readJson(scoresPath));
  } catch (err) {
    console.error(`${scoresPath}: ${(err as Error).message}`);
    process.exit(1);
  }
  await mkdir(outDir, { recursive: true });
  await writeFile(join(outDir, "index.html"), renderThemePage(scores, args.theme), "utf8");
  await copyThemes(outDir);
  const summary =
    args.theme === "jubarte"
      ? `${scores.tables.length} tables, ${scores.headlines.length} headlines, ${scores.states.length} states`
      : `${scores.tables.length} tables, ${scores.tables.filter((t) => t.id.endsWith("-sample")).length} sample tables, ${scores.states.length} states`;
  console.log(`${join(outDir, "index.html")}: ${summary}`);
}
