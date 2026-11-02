/**
 * The speed page: the 10,000-input speed benchmark, as the release holds it.
 *
 * `speed.json` is the page's view of the per-pair rows: the tasks, their
 * coverage, their tables and their notes. The notes are plain text, and a
 * `backtick` span in them means inline code — so every string is escaped
 * first and the backticks are read afterwards, never the other way round.
 *
 * The render layer is pure (`renderSpeed`): data in, HTML out. The wiring
 * (`mountSpeedPage`) fetches the file and puts the string on the page.
 */

import { esc } from "./esc.ts";

// ---- the contract ---------------------------------------------------------------------

/** How much of a lane's plan it covered. */
export interface SpeedCoverage {
  tool: string;
  completed: number;
  planned: number;
}

/** One tool's timings in one bucket. */
export interface SpeedRow {
  tool: string;
  bucket: string;
  n: number;
  ok: number;
  failed: number;
  median_ms: number | null;
  mean_ms: number | null;
  p95_ms: number | null;
  p99_ms: number | null;
  max_ms: number | null;
  ok_total_s: number | null;
}

/** One table: a bucket per tool. */
export interface SpeedTable {
  id: string;
  title: string;
  bucket_header: string;
  rows: SpeedRow[];
}

/** One note: a heading, paragraphs and bullets, all plain text. */
export interface SpeedNote {
  heading: string;
  paragraphs: string[];
  bullets: string[];
}

/** One measured task (redlines, DOCX to PDF). */
export interface SpeedTask {
  id: string;
  title: string;
  description: string;
  available: boolean;
  planned?: number | null;
  timeout_ms?: number | null;
  quartile_cuts_bytes: number[];
  coverage: SpeedCoverage[];
  tables: SpeedTable[];
  notes: SpeedNote[];
}

/** `speed.json`: the whole page. */
export interface Speed {
  version: string;
  generated: string;
  repo: string;
  title: string;
  intro: string;
  tasks: SpeedTask[];
}

// ---- parsing ---------------------------------------------------------------------------

function fail(path: string, message: string): never {
  throw new TypeError(`${path}: ${message}`);
}

function asRecord(value: unknown, path: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    fail(path, "must be an object");
  }
  return value as Record<string, unknown>;
}

function asArray(value: unknown, path: string): unknown[] {
  if (!Array.isArray(value)) fail(path, "must be an array");
  return value;
}

function asString(value: unknown, path: string): string {
  if (typeof value !== "string") fail(path, "must be a string");
  return value;
}

function asNumber(value: unknown, path: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) fail(path, "must be a finite number");
  return value;
}

function asOptionalNumber(value: unknown, path: string): number | null {
  if (value === undefined || value === null) return null;
  return asNumber(value, path);
}

function asStringArray(value: unknown, path: string): string[] {
  return asArray(value, path).map((item, i) => asString(item, `${path}[${i}]`));
}

function asNumberArray(value: unknown, path: string): number[] {
  return asArray(value, path).map((item, i) => asNumber(item, `${path}[${i}]`));
}

/** The speed release, validated field by field. */
export function parseSpeed(value: unknown): Speed {
  const raw = asRecord(value, "speed");
  const tasks = asArray(raw.tasks, "speed.tasks").map((item, i) => {
    const path = `speed.tasks[${i}]`;
    const task = asRecord(item, path);
    const coverage = asArray(task.coverage ?? [], `${path}.coverage`).map((entry, j) => {
      const cov = asRecord(entry, `${path}.coverage[${j}]`);
      return {
        tool: asString(cov.tool, `${path}.coverage[${j}].tool`),
        completed: asNumber(cov.completed, `${path}.coverage[${j}].completed`),
        planned: asNumber(cov.planned, `${path}.coverage[${j}].planned`),
      };
    });
    const tables = asArray(task.tables ?? [], `${path}.tables`).map((entry, j) => {
      const table = asRecord(entry, `${path}.tables[${j}]`);
      return {
        id: asString(table.id, `${path}.tables[${j}].id`),
        title: asString(table.title, `${path}.tables[${j}].title`),
        bucket_header: asString(table.bucket_header, `${path}.tables[${j}].bucket_header`),
        rows: asArray(table.rows ?? [], `${path}.tables[${j}].rows`).map((row, k) => {
          const rowPath = `${path}.tables[${j}].rows[${k}]`;
          const rowRaw = asRecord(row, rowPath);
          return {
            tool: asString(rowRaw.tool, `${rowPath}.tool`),
            bucket: asString(rowRaw.bucket, `${rowPath}.bucket`),
            n: asNumber(rowRaw.n, `${rowPath}.n`),
            ok: asNumber(rowRaw.ok, `${rowPath}.ok`),
            failed: asNumber(rowRaw.failed, `${rowPath}.failed`),
            median_ms: asOptionalNumber(rowRaw.median_ms, `${rowPath}.median_ms`),
            mean_ms: asOptionalNumber(rowRaw.mean_ms, `${rowPath}.mean_ms`),
            p95_ms: asOptionalNumber(rowRaw.p95_ms, `${rowPath}.p95_ms`),
            p99_ms: asOptionalNumber(rowRaw.p99_ms, `${rowPath}.p99_ms`),
            max_ms: asOptionalNumber(rowRaw.max_ms, `${rowPath}.max_ms`),
            ok_total_s: asOptionalNumber(rowRaw.ok_total_s, `${rowPath}.ok_total_s`),
          };
        }),
      };
    });
    const notes = asArray(task.notes ?? [], `${path}.notes`).map((entry, j) => {
      const note = asRecord(entry, `${path}.notes[${j}]`);
      return {
        heading: asString(note.heading, `${path}.notes[${j}].heading`),
        paragraphs: asStringArray(note.paragraphs ?? [], `${path}.notes[${j}].paragraphs`),
        bullets: asStringArray(note.bullets ?? [], `${path}.notes[${j}].bullets`),
      };
    });
    const available = task.available === undefined ? true : task.available;
    if (typeof available !== "boolean") fail(`${path}.available`, "must be a boolean");
    const out: SpeedTask = {
      id: asString(task.id, `${path}.id`),
      title: asString(task.title, `${path}.title`),
      description: asString(task.description ?? "", `${path}.description`),
      available,
      quartile_cuts_bytes: asNumberArray(
        task.quartile_cuts_bytes ?? [],
        `${path}.quartile_cuts_bytes`,
      ),
      coverage,
      tables,
      notes,
    };
    if (task.planned !== undefined && task.planned !== null) {
      out.planned = asNumber(task.planned, `${path}.planned`);
    }
    if (task.timeout_ms !== undefined && task.timeout_ms !== null) {
      out.timeout_ms = asNumber(task.timeout_ms, `${path}.timeout_ms`);
    }
    return out;
  });
  return {
    version: asString(raw.version, "speed.version"),
    generated: asString(raw.generated, "speed.generated"),
    repo: asString(raw.repo, "speed.repo"),
    title: asString(raw.title, "speed.title"),
    intro: asString(raw.intro, "speed.intro"),
    tasks,
  };
}

// ---- the render layer ------------------------------------------------------------------

/**
 * One text value, escaped, with its `backtick` spans read as inline code.
 * The escaping happens first: the backticks are the contract's, and what is
 * between them is still data.
 */
export function inlineCode(text: string): string {
  return esc(text).replace(/`([^`]+)`/g, "<code>$1</code>");
}

/** A number as the speed page shows it: one decimal, or a dash. */
export function formatMs(value: number | null | undefined): string {
  if (value === null || value === undefined) return "–";
  return value.toFixed(1);
}

/** The coverage of one lane, as the page words it. */
export function renderCoverage(coverage: SpeedCoverage): string {
  return `<li>${esc(coverage.tool)}: ${esc(coverage.completed)} of ${esc(
    coverage.planned,
  )} planned pairs</li>`;
}

/** One table of timings. */
export function renderSpeedTable(table: SpeedTable): string {
  const head = [
    "tool",
    table.bucket_header,
    "n",
    "ok",
    "failed",
    "median ms",
    "mean ms",
    "p95 ms",
    "p99 ms",
    "max ms",
    "ok total s",
  ];
  const body = table.rows
    .map(
      (row) =>
        `<tr><td>${esc(row.tool)}</td><td>${esc(row.bucket)}</td><td class="n">${esc(row.n)}</td><td class="n">${esc(
          row.ok,
        )}</td><td class="n">${esc(row.failed)}</td><td class="n">${esc(
          formatMs(row.median_ms),
        )}</td><td class="n">${esc(formatMs(row.mean_ms))}</td><td class="n">${esc(
          formatMs(row.p95_ms),
        )}</td><td class="n">${esc(formatMs(row.p99_ms))}</td><td class="n">${esc(
          formatMs(row.max_ms),
        )}</td><td class="n">${esc(formatMs(row.ok_total_s))}</td></tr>`,
    )
    .join("");
  return `<div class="tbl"><table><thead><tr>${head
    .map((name) => `<th>${esc(name)}</th>`)
    .join("")}</tr></thead><tbody>${body}</tbody></table></div>`;
}

/**
 * The paragraph the common table wears: a failed call is counted apart and
 * left out of every statistic, so each tool's sample is its own `ok` count.
 */
export function renderSampleNote(table: SpeedTable): string {
  const counts = table.rows.map((row) => `${row.ok.toLocaleString("en-US")} for ${row.tool}`);
  if (!counts.length) return "";
  const list =
    counts.length === 1
      ? counts[0]
      : `${counts.slice(0, -1).join(", ")} and ${counts[counts.length - 1]}`;
  return `<p>Times are per successful call. A failed or timed-out call is counted in <code>failed</code> and left out of the median, mean, percentiles, maximum and total, so each tool's timing sample is its own <code>ok</code> count: ${list}.</p>`;
}

/** One note: its heading, its paragraphs and its bullets. */
export function renderSpeedNote(note: SpeedNote): string {
  const paragraphs = note.paragraphs.map((text) => `<p>${inlineCode(text)}</p>`).join("");
  const bullets = note.bullets.length
    ? `<ul>${note.bullets.map((text) => `<li>${inlineCode(text)}</li>`).join("")}</ul>`
    : "";
  return `<h4>${esc(note.heading)}</h4>${paragraphs}${bullets}`;
}

/** One task: its heading, its description, its coverage, its tables, its notes. */
export function renderSpeedTask(task: SpeedTask): string {
  const planned =
    task.planned !== undefined && task.planned !== null
      ? ` · ${task.planned.toLocaleString("en-US")} planned`
      : "";
  if (!task.available) {
    return `<section id="${esc(task.id)}"><h2>${esc(task.title)}</h2><p>${inlineCode(
      task.description || "Not measured yet.",
    )}</p></section>`;
  }
  const coverage = task.coverage.length
    ? `<h3>Coverage</h3><ul>${task.coverage.map(renderCoverage).join("")}</ul>`
    : "";
  const tables = task.tables
    .map((table) => {
      const note = table.id === "common" ? renderSampleNote(table) : "";
      return `<h3>${esc(table.title)}</h3>${note}${renderSpeedTable(table)}`;
    })
    .join("");
  const notes = task.notes.length
    ? `<h3>${esc(task.title)} run, notes</h3>${task.notes.map(renderSpeedNote).join("")}`
    : "";
  return `<section id="${esc(task.id)}"><h2>${esc(task.title)}${esc(planned)}</h2><p>${inlineCode(
    task.description,
  )}</p>${coverage}${tables}${notes}</section>`;
}

/** The whole speed page's body. */
export function renderSpeed(speed: Speed): string {
  const tasks = speed.tasks.map(renderSpeedTask).join("\n");
  return `<h1>${esc(speed.title)}</h1>
<p>${inlineCode(speed.intro)}</p>
${tasks}`;
}

// ---- the page --------------------------------------------------------------------------

/** The page the speed view wears. */
export interface SpeedPageOptions {
  /** The file the page fetches, relative to the page. */
  speedUrl: string;
  /** The module the page imports, relative to the page. */
  moduleUrl: string;
  /** The stylesheet the page links, relative to the page. */
  stylesheet?: string;
  /** The page's title. */
  title?: string;
  /** The page's meta description. */
  description?: string;
  /** The links in the breadcrumb. */
  links?: { href: string; label: string }[];
}

/** The whole speed page: the shell the wiring fills in. No data in it. */
export function renderSpeedPage(opts: SpeedPageOptions): string {
  const stylesheet = opts.stylesheet ?? "../cases.css";
  const crumbs: { href: string; label: string }[] = opts.links ?? [
    { href: "../index.html", label: "DOCX to PDF engines" },
    { href: "../redlines/index.html", label: "Redlines vs Microsoft Word" },
    { href: "../speed/index.html", label: "Speed" },
  ];
  const links = crumbs
    .map((link, i) =>
      i === crumbs.length - 1
        ? `${esc(link.label)}`
        : `<a href="${esc(link.href)}">${esc(link.label)}</a> &middot; `,
    )
    .join("");
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(opts.title ?? "neurotic_docx_bench: Speed on 10,000 inputs")}</title>
<meta name="description" content="${esc(
    opts.description ??
      "Per-call timings of the engines on 10,000 planned inputs, one tool at a time on one machine.",
  )}">
<meta name="generator" content="@jandira-tech/bench-viewer">
<link rel="stylesheet" href="${esc(stylesheet)}">
</head>
<body class="doc">
<header id="brand"><a class="logo" href="../index.html">NEUROTIC.DOCX.BENCH</a><span class="crumb">/ Speed on 10,000 inputs</span><span class="links"><a href="../index.html">Scores</a><a href="../cases/index.html">Cases</a><a href="../redlines/index.html">Redlines</a><a href="https://github.com/jandira-tech/neurotic_docx_bench">Bench repo ↗</a></span></header>
<nav class="crumbs" aria-label="Breadcrumb">${links}</nav>
<main id="main"><p class="loading">Loading speed.json…</p></main>
<footer class="site"><span class="mono">neurotic_docx_bench · © MMXXVI</span><span>Maintained by <a href="https://arthur.law/" rel="noopener">Arthur Souza Rodrigues</a>, author of jubarte, one of the engines compared.</span><a href="../index.html">Scores →</a><a href="https://github.com/jandira-tech/neurotic_docx_bench" rel="noopener">Bench repo →</a></footer>
<script type="module">
import { mountSpeedPage } from "${esc(opts.moduleUrl)}";
mountSpeedPage({ speedUrl: "${esc(opts.speedUrl)}" });
</script>
</body>
</html>
`;
}

// ---- the wiring ------------------------------------------------------------------------

/** How the speed page is told where its data is. */
export interface MountSpeedOptions {
  /** The file the page fetches. */
  speedUrl: string;
  /** The document the page lives in. */
  root?: Document;
}

/** Fetch the speed release and put it on the page. */
export async function mountSpeedPage(opts: MountSpeedOptions): Promise<void> {
  const doc = opts.root ?? document;
  const main = doc.querySelector("#main");
  if (!main) return;
  try {
    const response = await fetch(opts.speedUrl);
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    const speed = parseSpeed(await response.json());
    main.innerHTML = renderSpeed(speed);
  } catch (err) {
    main.innerHTML = `<p class="loading">speed.json did not load: ${esc((err as Error).message)}</p>`;
  }
}
