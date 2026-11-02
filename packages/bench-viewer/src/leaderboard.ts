/**
 * The arthur-law page: the scores, ranked.
 *
 * benchmarks.law shows what the bench measured, not what one product sells.
 * So this page has none of jubarte's framing: no headline cells (they are
 * "jubarte vs X"), no "ours" rows, no affiliation dagger, no legend about
 * them. Every tool is in every table, in the order the bench ranked it, and
 * the leader of each table is named above it.
 *
 * What stays: the badge, the corpus states, the method, the provenance and
 * the footer. What moves: the tables come in two groups — the full-corpus
 * tables first, the release's own samples after them, under their own
 * heading.
 */

import { esc } from "./esc.ts";
import { requireHttpUrl } from "./parse.ts";
import {
  renderBadge,
  renderMethod,
  renderProvenance,
  renderRow,
  renderStates,
  renderTableHead,
} from "./render.ts";
import type { MethodPoint, Row, Scores, StateCell, Table } from "./types.ts";

/** The mark that says a tool is the author's own. This page does not use it. */
const AFFILIATION_MARK = "†";

/** The heading over the tables scored on the release's own samples. */
export const SAMPLES_HEADING = "600-document samples";

/** The id of the samples group's heading. */
export const SAMPLES_HEADING_ID = "lb-samples";

export interface LeaderboardPageOptions {
  /** The badge's version tag; the scores' own version by default. */
  tag?: string;
  /** The heading over the sample tables. */
  samplesHeading?: string;
  /** The page's title. */
  title?: string;
  /** The page's meta description. */
  description?: string;
}

/** Drop the affiliation mark: this page ranks tools, not owners. */
export function stripAffiliation(name: string): string {
  return name.replace(/†\s*/g, "").trim();
}

/** A row as this page shows it: no "ours" marking, no affiliation mark. */
function neutralRow(row: Row): Row {
  return {
    rank: row.rank,
    tool: stripAffiliation(row.tool),
    pin: row.pin,
    median: row.median,
    mean: row.mean,
    docs: row.docs,
    failed: row.failed,
    note: row.note,
  };
}

/** The cells as this page shows them: no "ours" marking, no affiliation mark. */
function neutralStates(states: StateCell[]): StateCell[] {
  return states.map((cell) => {
    const neutral: StateCell = {
      name: cell.name,
      n: cell.n,
      rows: cell.rows.map((row) => ({
        tool: stripAffiliation(row.tool),
        median: row.median,
      })),
    };
    if (cell.table !== undefined) neutral.table = cell.table;
    return neutral;
  });
}

/**
 * The method cards, minus the one that explains the affiliation mark: this
 * page marks nothing, so that card would be false here.
 */
function neutralMethod(method: MethodPoint[]): MethodPoint[] {
  return method.filter(
    (point) => !point.t.includes(AFFILIATION_MARK) && !point.d.includes(AFFILIATION_MARK),
  );
}

/** A table scored on the release's own samples. */
function isSampleTable(table: Table): boolean {
  return table.id.endsWith("-sample");
}

/**
 * The row that leads a table: the first one the bench ranked 1, ties
 * included. A calibration row ("cal.") never leads.
 */
function leaderOf(table: Table): Row | undefined {
  return table.rows.find((row) => /^1=?$/.test(row.rank.trim())) ?? table.rows[0];
}

/** The line that names the leader of a table. */
function renderLeader(table: Table): string {
  const leader = leaderOf(table);
  if (!leader) return "";
  return `<p class="lb-leader">Leader: <span class="lb-tool">${esc(stripAffiliation(leader.tool))}</span> — median <span class="mono">${leader.median.toFixed(2)}</span></p>`;
}

/** One ranked table, with its leader named above it. */
function renderLeaderboardTable(table: Table): string {
  const id = esc(table.id);
  return `<section class="mt-72" id="${id}">
<div class="section-head"><h2 id="${id}-title">${esc(table.title)}</h2><span>${esc(table.meta)}</span></div>
<p class="note mt-12">${esc(table.desc)}</p>
${renderLeader(table)}
<div class="scroll-x"><div class="bench-table" role="table" aria-labelledby="${id}-title">
${renderTableHead()}
${table.rows.map((row) => renderRow(neutralRow(row))).join("\n")}
</div></div>
</section>`;
}

/** The heading over the sample tables. */
function renderSamplesHeading(heading: string): string {
  return `<div class="lb-samples-head">
<h2 id="${SAMPLES_HEADING_ID}">${esc(heading)}</h2>
<span>the release samples, scored on the same rules</span>
</div>`;
}

/**
 * The whole leaderboard page. Every text value goes through esc().
 *
 * The tables come in two groups: the full-corpus ones first, the release's
 * own samples after them under their own heading.
 */
export function buildLeaderboardPage(scores: Scores, opts: LeaderboardPageOptions = {}): string {
  const repo = requireHttpUrl(scores.repo, "repo");
  const viewer = requireHttpUrl(scores.viewer, "viewer");
  const heading = opts.samplesHeading ?? SAMPLES_HEADING;
  const full = scores.tables.filter((table) => !isSampleTable(table));
  const samples = scores.tables.filter(isSampleTable);
  const fullTables = full.map((table) => renderLeaderboardTable(table)).join("\n");
  const sampleTables = samples.map((table) => renderLeaderboardTable(table)).join("\n");
  const samplesHeading = samples.length > 0 ? renderSamplesHeading(heading) : "";
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(opts.title ?? "Benchmark · neurotic_docx_bench")}</title>
<meta name="description" content="${esc(opts.description ?? "DOCX conversion and redlines scored against Microsoft Word, failures included.")}">
<meta name="generator" content="@jandira-tech/bench-viewer">
<link rel="stylesheet" href="./tokens.css">
<link rel="stylesheet" href="./arthur-law.css">
</head>
<body>
<main class="wrap">
<header class="mt-56">
${renderBadge(scores, opts.tag)}
<h1 class="h1">Scored against Word, failures included.</h1>
<p class="lead">The oracle is Word’s own PDF export of each document (SHA-pinned). A converter’s PDF is scored 0–100 by pixel similarity; redlines are additionally opened in Word and compared against Word’s own compare. Medians and means count a failed document as 0, so no tool gains by skipping a hard one. Every table is a ranking, and the tool that leads it is named above the table.</p>
</header>
${fullTables}
${samplesHeading}
${sampleTables}
${renderStates(neutralStates(scores.states), { heading: "By corpus state" })}
${renderMethod(neutralMethod(scores.method))}
${renderProvenance(scores.provenance)}
<footer class="mt-72">
<p class="note">Harness and raw records: <a href="${esc(repo)}">neurotic_docx_bench</a>. Per-case viewer: <a href="${esc(viewer)}">${esc(viewer)}</a>. Figures are project-maintained and reproducible, not a neutral third-party benchmark.</p>
</footer>
</main>
</body>
</html>
`;
}
