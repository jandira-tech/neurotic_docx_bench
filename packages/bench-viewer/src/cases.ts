/**
 * The case browsers: the conversion browser and the redline browser.
 *
 * The data is the release's, not a copy of it. `cases/index.json` holds the
 * shard directory, the engine list and the public asset base; one shard per
 * group is fetched when the group is opened, so a page opens on one group
 * instead of the whole corpus.
 *
 * Two layers live here. The **render layer** is pure: a function from data to
 * an HTML string, with every data string through `esc()` (the case id, the
 * group name, the version label, the error message, the asset path — data is
 * not markup). The **wiring** (`mountCasesPage`) fetches, keeps the state and
 * puts the strings where they belong. The tests drive the first layer without
 * a browser.
 *
 * The contract is `bench_ops.models` (CasesIndex, CaseShard, Case): the
 * release writes it, this module reads it.
 */

import { esc } from "./esc.ts";

// ---- the contract ---------------------------------------------------------------------

/** The two kinds of case group the release holds. */
export type Kind = "conversion" | "redline";

/** The metric names a case's scores may carry. */
export type MetricName = "pixel" | "jaccard" | "ssim" | "text_boundary";

/** One engine lane: the key the data uses, the label the page shows. */
export interface Engine {
  key: string;
  label: string;
}

/** One group in the index: where its shard is and how many cases it holds. */
export interface ShardRef {
  kind: Kind;
  group: string;
  count: number;
  path: string;
}

/** `cases/index.json`: the shard directory, the engine list, the asset base. */
export interface CasesIndex {
  version: string;
  generated: string;
  repo: string;
  assets_base: string;
  engines: Engine[];
  groups: ShardRef[];
  /**
   * The public base the case's `files` paths resolve against (the record on
   * Hugging Face). Absent when the release publishes no files.
   */
  files_base?: string;
}

/** The per-lane page diagnostics the release carries. */
export interface MetricDiagnostics {
  ref_pages: number;
  pages: number;
  scored_pages: number;
  max_break_drift: number;
}

/** One case row: the pages, the scores, the versions, the lanes left out. */
export interface Case {
  kind: Kind;
  group: string;
  case: string;
  pages: Record<string, (string | null)[]>;
  page_counts: Record<string, number>;
  scores: Record<string, Partial<Record<MetricName, number | null>>>;
  times: Record<string, number>;
  versions: Record<string, string>;
  dropped: string[];
  reference_app: string;
  pdfs?: Record<string, string>;
  errors?: Record<string, string>;
  metric_diagnostics?: Record<string, MetricDiagnostics>;
  shown?: number[] | null;
  stem?: string | null;
  lang?: string | null;
  type?: string | null;
  set?: string | null;
  sets?: string | null;
  state?: string | null;
  pair?: string | null;
  not_applicable?: string[];
  unavailable?: string[];
  /**
   * One score per shown page, per lane (null = that page could not be
   * scored). Never longer than the lane's shown pages; absent when the
   * release publishes no per-page scores.
   */
  page_scores?: Record<string, (number | null)[]>;
  /**
   * The case's files, per lane, relative to the index's `files_base` (the
   * `~/` sentinel, as in the published data).
   */
  files?: Record<string, string>;
}

/** One group's shard: `cases/<kind>/<group>.json`. */
export interface CaseShard {
  kind: Kind;
  group: string;
  cases: Case[];
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

function asStringArray(value: unknown, path: string): string[] {
  return asArray(value, path).map((item, i) => asString(item, `${path}[${i}]`));
}

function asNumberArray(value: unknown, path: string): number[] {
  return asArray(value, path).map((item, i) => asNumber(item, `${path}[${i}]`));
}

function asKind(value: unknown, path: string): Kind {
  const kind = asString(value, path);
  if (kind !== "conversion" && kind !== "redline") fail(path, "must be conversion or redline");
  return kind;
}

function asRecordOfStrings(value: unknown, path: string): Record<string, string> {
  const raw = asRecord(value, path);
  const out: Record<string, string> = {};
  for (const [key, item] of Object.entries(raw)) {
    out[key] = asString(item, `${path}.${key}`);
  }
  return out;
}

/** The index: the shard directory, the engine list and the asset base. */
export function parseCasesIndex(value: unknown): CasesIndex {
  const raw = asRecord(value, "cases index");
  const assetsBase = asString(raw.assets_base, "cases index.assets_base");
  if (!(assetsBase.startsWith("https://") && assetsBase.endsWith("/"))) {
    fail("cases index.assets_base", "must be an absolute https:// URL ending in /");
  }
  const engines = asArray(raw.engines, "cases index.engines").map((item, i) => {
    const engine = asRecord(item, `cases index.engines[${i}]`);
    return {
      key: asString(engine.key, `cases index.engines[${i}].key`),
      label: asString(engine.label, `cases index.engines[${i}].label`),
    };
  });
  let filesBase: string | undefined;
  if (raw.files_base !== undefined && raw.files_base !== null) {
    filesBase = asString(raw.files_base, "cases index.files_base");
    // The same shape as the asset base: an absolute https URL ending in "/".
    if (
      !(
        filesBase.startsWith("https://") &&
        filesBase.endsWith("/") &&
        filesBase.slice("https://".length, -1).length > 0
      )
    ) {
      fail("cases index.files_base", "must be an absolute https:// URL ending in /");
    }
  }
  const groups = asArray(raw.groups, "cases index.groups").map((item, i) => {
    const group = asRecord(item, `cases index.groups[${i}]`);
    const count = asNumber(group.count, `cases index.groups[${i}].count`);
    if (!Number.isInteger(count) || count < 0) {
      fail(`cases index.groups[${i}].count`, "must be a non-negative integer");
    }
    return {
      kind: asKind(group.kind, `cases index.groups[${i}].kind`),
      group: asString(group.group, `cases index.groups[${i}].group`),
      count,
      path: asString(group.path, `cases index.groups[${i}].path`),
    };
  });
  return {
    version: asString(raw.version, "cases index.version"),
    generated: asString(raw.generated, "cases index.generated"),
    repo: asString(raw.repo, "cases index.repo"),
    assets_base: assetsBase,
    engines,
    groups,
    ...(filesBase === undefined ? {} : { files_base: filesBase }),
  };
}

/** One shard: the group's cases, in the order the release wrote them. */
export function parseCaseShard(value: unknown): CaseShard {
  const raw = asRecord(value, "case shard");
  const kind = asKind(raw.kind, "case shard.kind");
  const group = asString(raw.group, "case shard.group");
  const cases = asArray(raw.cases, "case shard.cases").map((item, i) =>
    parseCase(item, `case shard.cases[${i}]`, kind, group),
  );
  return { kind, group, cases };
}

/** One case row. */
export function parseCase(value: unknown, path: string, kind?: Kind, group?: string): Case {
  const raw = asRecord(value, path);
  const caseKind = asKind(raw.kind, `${path}.kind`);
  if (kind !== undefined && caseKind !== kind) {
    fail(`${path}.kind`, `must be ${kind} in this shard`);
  }
  const caseGroup = asString(raw.group, `${path}.group`);
  if (group !== undefined && caseGroup !== group) {
    fail(`${path}.group`, `must be ${group} in this shard`);
  }
  const pages: Record<string, (string | null)[]> = {};
  const pageRaw = asRecord(raw.pages ?? {}, `${path}.pages`);
  for (const [key, item] of Object.entries(pageRaw)) {
    pages[key] = asArray(item, `${path}.pages.${key}`).map((slot, i) => {
      if (slot === null) return null;
      return asString(slot, `${path}.pages.${key}[${i}]`);
    });
  }
  const pageCounts: Record<string, number> = {};
  for (const [key, item] of Object.entries(
    asRecord(raw.page_counts ?? {}, `${path}.page_counts`),
  )) {
    pageCounts[key] = asNumber(item, `${path}.page_counts.${key}`);
  }
  const scores: Record<string, Partial<Record<MetricName, number | null>>> = {};
  for (const [key, item] of Object.entries(asRecord(raw.scores ?? {}, `${path}.scores`))) {
    const metricRaw = asRecord(item, `${path}.scores.${key}`);
    const metrics: Partial<Record<MetricName, number | null>> = {};
    for (const [name, value] of Object.entries(metricRaw)) {
      if (value === null) {
        metrics[name as MetricName] = null;
        continue;
      }
      metrics[name as MetricName] = asNumber(value, `${path}.scores.${key}.${name}`);
    }
    scores[key] = metrics;
  }
  const times: Record<string, number> = {};
  for (const [key, item] of Object.entries(asRecord(raw.times ?? {}, `${path}.times`))) {
    times[key] = asNumber(item, `${path}.times.${key}`);
  }
  const versions = asRecordOfStrings(raw.versions ?? {}, `${path}.versions`);
  const pdfs = raw.pdfs === undefined ? undefined : asRecordOfStrings(raw.pdfs, `${path}.pdfs`);
  const errors =
    raw.errors === undefined ? undefined : asRecordOfStrings(raw.errors, `${path}.errors`);
  const pageScores: Record<string, (number | null)[]> = {};
  if (raw.page_scores !== undefined && raw.page_scores !== null) {
    for (const [key, item] of Object.entries(asRecord(raw.page_scores, `${path}.page_scores`))) {
      pageScores[key] = asArray(item, `${path}.page_scores.${key}`).map((score, i) => {
        if (score === null) return null;
        return asNumber(score, `${path}.page_scores.${key}[${i}]`);
      });
    }
  }
  const files =
    raw.files === undefined || raw.files === null
      ? undefined
      : asRecordOfStrings(raw.files, `${path}.files`);
  const diagnostics: Record<string, MetricDiagnostics> = {};
  if (raw.metric_diagnostics !== undefined) {
    for (const [key, item] of Object.entries(
      asRecord(raw.metric_diagnostics, `${path}.metric_diagnostics`),
    )) {
      const d = asRecord(item, `${path}.metric_diagnostics.${key}`);
      diagnostics[key] = {
        ref_pages: asNumber(d.ref_pages, `${path}.metric_diagnostics.${key}.ref_pages`),
        pages: asNumber(d.pages, `${path}.metric_diagnostics.${key}.pages`),
        scored_pages: asNumber(d.scored_pages, `${path}.metric_diagnostics.${key}.scored_pages`),
        max_break_drift: asNumber(
          d.max_break_drift,
          `${path}.metric_diagnostics.${key}.max_break_drift`,
        ),
      };
    }
  }
  const shown =
    raw.shown === undefined || raw.shown === null
      ? undefined
      : asNumberArray(raw.shown, `${path}.shown`);
  const optional = (key: string): string | undefined => {
    const item = raw[key];
    if (item === undefined || item === null) return undefined;
    return asString(item, `${path}.${key}`);
  };
  const case_: Case = {
    kind: caseKind,
    group: caseGroup,
    case: asString(raw.case, `${path}.case`),
    pages,
    page_counts: pageCounts,
    scores,
    times,
    versions,
    dropped: asStringArray(raw.dropped ?? [], `${path}.dropped`),
    reference_app: asString(raw.reference_app ?? "", `${path}.reference_app`),
  };
  if (pdfs !== undefined) case_.pdfs = pdfs;
  if (errors !== undefined) case_.errors = errors;
  if (raw.page_scores !== undefined && raw.page_scores !== null) {
    case_.page_scores = pageScores;
  }
  if (files !== undefined) case_.files = files;
  if (Object.keys(diagnostics).length > 0) case_.metric_diagnostics = diagnostics;
  if (shown !== undefined) case_.shown = shown;
  const stem = optional("stem");
  if (stem !== undefined) case_.stem = stem;
  const lang = optional("lang");
  if (lang !== undefined) case_.lang = lang;
  const type = optional("type");
  if (type !== undefined) case_.type = type;
  const set = optional("set");
  if (set !== undefined) case_.set = set;
  const sets = optional("sets");
  if (sets !== undefined) case_.sets = sets;
  const state = optional("state");
  if (state !== undefined) case_.state = state;
  const pair = optional("pair");
  if (pair !== undefined) case_.pair = pair;
  if (raw.not_applicable !== undefined) {
    case_.not_applicable = asStringArray(raw.not_applicable, `${path}.not_applicable`);
  }
  if (raw.unavailable !== undefined) {
    case_.unavailable = asStringArray(raw.unavailable, `${path}.unavailable`);
  }
  return case_;
}

// ---- the lanes -------------------------------------------------------------------------

/** What a lane holds for one case. */
export type LaneState =
  | "measured" // pages and a score
  | "no-pages" // the lane ran, but the case has no page for it
  | "failed" // the lane ran and failed; the error says why
  | "unavailable" // the cohort lane has no published measurement
  | "not-applicable" // the lane was excluded for cause
  | "dropped"; // the lane is not part of this case at all

/** The label each lane state wears on the page. */
export const LANE_LABEL: Record<LaneState, string> = {
  measured: "",
  "no-pages": "no page",
  failed: "failed",
  unavailable: "not measured",
  "not-applicable": "not applicable",
  dropped: "dropped",
};

/** What a lane holds for one case. */
export function laneState(c: Case, key: string): LaneState {
  // A lane excluded for cause is said so, even when the case also drops it:
  // the reason is the useful part.
  if (c.not_applicable?.includes(key)) return "not-applicable";
  if (c.unavailable?.includes(key)) return "unavailable";
  if (c.dropped?.includes(key)) return "dropped";
  if (c.errors?.[key]) return "failed";
  const pages = c.pages?.[key];
  if (pages?.some((slot) => slot !== null)) return "measured";
  return "no-pages";
}

/** The lanes of one case, in the order the page draws them (Word first). */
export function lanesForCase(c: Case, engines: Engine[]): { engine: Engine; state: LaneState }[] {
  const ordered = [...engines].sort((a, b) => {
    if (a.key === "reference") return -1;
    if (b.key === "reference") return 1;
    return 0;
  });
  return ordered.map((engine) => ({ engine, state: laneState(c, engine.key) }));
}

// ---- the lane order of a group ----------------------------------------------------------

/**
 * The lanes a group's cases mention: the page's kind's lanes, as far as this
 * group shows them. The release writes every lane of the page's kind into
 * each of its cases — a lane it did not run for a case is `dropped`, a cohort
 * lane without a published measurement is `unavailable` — while a lane of the
 * *other* kind is mentioned by no case of this one (no pages, no score, not
 * even dropped). So the union of what the cases mention is exactly the set a
 * page of that kind may show, and a conversion page never shows a
 * redline-only lane (jubarte-rust, superdoc, stemma, docxodus-12.6.5,
 * jubarte-093, …) unless it has data in a conversion case.
 *
 * The index's engine list is sorted by key: that is **storage order, not
 * display order** — `orderLanes` decides which lanes a page shows and in
 * which order.
 */
export function mentionedLanes(cases: Case[], engines: Engine[]): Engine[] {
  const mentioned = new Set<string>();
  for (const c of cases) {
    for (const key of Object.keys(c.pages ?? {})) mentioned.add(key);
    for (const key of Object.keys(c.scores ?? {})) mentioned.add(key);
    for (const key of Object.keys(c.times ?? {})) mentioned.add(key);
    for (const key of Object.keys(c.errors ?? {})) mentioned.add(key);
    for (const key of c.unavailable ?? []) mentioned.add(key);
    for (const key of c.not_applicable ?? []) mentioned.add(key);
    for (const key of c.dropped ?? []) mentioned.add(key);
  }
  return engines.filter((engine) => mentioned.has(engine.key));
}

/**
 * The display order of a group's lanes: Word first, then by the number of
 * cases in the group where the lane has a score (descending), ties by label —
 * compared by code points, so the order never depends on the runtime's
 * collation. Lanes with no data in the group sort last (they have no score);
 * the bar folds them behind "+N more".
 */
export function orderLanes(cases: Case[], engines: Engine[]): Engine[] {
  const scored = new Map<string, number>();
  for (const c of cases) {
    for (const key of Object.keys(c.scores ?? {})) {
      scored.set(key, (scored.get(key) ?? 0) + 1);
    }
  }
  const byLabel = (a: Engine, b: Engine): number =>
    a.label < b.label ? -1 : a.label > b.label ? 1 : 0;
  return mentionedLanes(cases, engines).sort((a, b) => {
    if (a.key === "reference") return -1;
    if (b.key === "reference") return 1;
    const diff = (scored.get(b.key) ?? 0) - (scored.get(a.key) ?? 0);
    return diff !== 0 ? diff : byLabel(a, b);
  });
}

/**
 * The lanes with data in the group: everything the cases give a lane besides
 * dropping it — pages, a score, a time, an error, `unavailable`,
 * `not applicable` — in at least one case. These stay out of the "+N more"
 * fold; the kind's lanes without data (dropped in every case) are folded.
 */
export function lanesWithData(cases: Case[]): Set<string> {
  const withData = new Set<string>();
  for (const c of cases) {
    for (const key of Object.keys(c.pages ?? {})) withData.add(key);
    for (const key of Object.keys(c.scores ?? {})) withData.add(key);
    for (const key of Object.keys(c.times ?? {})) withData.add(key);
    for (const key of Object.keys(c.errors ?? {})) withData.add(key);
    for (const key of c.unavailable ?? []) withData.add(key);
    for (const key of c.not_applicable ?? []) withData.add(key);
  }
  return withData;
}

/**
 * The lane the page puts beside Word by default: the first non-reference
 * lane in the display order — the group's own numbers decide, no product
 * preference.
 */
export function defaultComparisonLane(lanes: Engine[]): Engine | undefined {
  return lanes.find((engine) => engine.key !== "reference");
}

/**
 * The lane the overlay puts over Word by default: the second non-reference
 * lane in the display order, for the same reason.
 */
export function defaultOverlayLane(lanes: Engine[]): Engine | undefined {
  return lanes.filter((engine) => engine.key !== "reference")[1];
}

// ---- the assets ------------------------------------------------------------------------

/**
 * The public URL of one asset. The release stores the path relative to the
 * asset base with a `~/` sentinel; anything that is not an http(s) URL is
 * refused rather than put in an `src`.
 */
export function resolveAssetUrl(assetsBase: string, path: string | null | undefined): string {
  if (!path) return "";
  if (path.startsWith("~/")) return `${assetsBase}${path.slice(2)}`;
  return path;
}

/** The URL of an asset, or the empty string when it is not safe to use. */
export function safeAssetUrl(assetsBase: string, path: string | null | undefined): string {
  const url = resolveAssetUrl(assetsBase, path);
  if (!url) return "";
  if (!/^https?:\/\//i.test(url)) return "";
  return url;
}

/**
 * The URL of a case file: the files base + the path without its `~/`
 * prefix. A path that is not relative to the base is refused — a file link
 * stays inside the record it names.
 */
export function resolveFileUrl(filesBase: string, path: string | null | undefined): string {
  if (!path) return "";
  if (!path.startsWith("~/")) return "";
  return `${filesBase}${path.slice(2)}`;
}

/** The URL of a case file, or the empty string when it is not safe to use. */
export function safeFileUrl(filesBase: string, path: string | null | undefined): string {
  const url = resolveFileUrl(filesBase, path);
  if (!url) return "";
  if (!/^https:\/\//i.test(url)) return "";
  return url;
}

/**
 * The case's own folder on the files base: the longest folder its lanes'
 * files share (the case's folder, the lanes' files hang under it). The
 * empty string when the case publishes no files or the base is unknown.
 */
export function caseFilesUrl(filesBase: string | undefined, c: Case): string {
  if (!filesBase) return "";
  const paths = Object.values(c.files ?? {}).filter(
    (path): path is string => typeof path === "string" && path.startsWith("~/"),
  );
  if (!paths.length) return "";
  const dirs = paths.map((path) => path.slice(2).split("/").slice(0, -1).filter(Boolean));
  let common = dirs[0];
  for (const dir of dirs.slice(1)) {
    let i = 0;
    while (i < common.length && i < dir.length && common[i] === dir[i]) i++;
    common = common.slice(0, i);
  }
  const folder = common.join("/");
  const url = `${filesBase}${folder ? `${folder}/` : ""}`;
  return url.startsWith("https://") ? url : "";
}

/**
 * The URL of a shard, resolved against the release the index came from. The
 * shard path is relative to the release root (`cases/<kind>/<group>.json`);
 * the index sits in `cases/`, so the root is its directory's parent.
 */
export function shardUrl(indexUrl: string, path: string, base?: string): string {
  const index = new URL(indexUrl, base ?? "http://localhost/");
  const dir = index.href.replace(/[^/]*$/, "");
  const root = dir.endsWith("cases/") ? dir.slice(0, -"cases/".length) : dir;
  return new URL(path, root).href;
}

// ---- the hash --------------------------------------------------------------------------

/** The hash of one case: `#<group>/<case>`. */
export function caseHash(group: string, name: string): string {
  return `#${encodeURIComponent(`${group}/${name}`)}`;
}

/**
 * The case a hash names, or null. The group may hold slashes (`v1/clean`), so
 * the known groups are tried first; without them the last slash splits.
 */
export function parseCaseHash(
  hash: string,
  groups?: string[],
): { group: string; case: string } | null {
  const raw = hash.startsWith("#") ? hash.slice(1) : hash;
  if (!raw) return null;
  let decoded: string;
  try {
    decoded = decodeURIComponent(raw);
  } catch {
    return null;
  }
  if (!decoded) return null;
  if (groups && groups.length > 0) {
    const sorted = [...groups].sort((a, b) => b.length - a.length);
    for (const group of sorted) {
      if (decoded.startsWith(`${group}/`)) {
        const name = decoded.slice(group.length + 1);
        if (name) return { group, case: name };
      }
    }
    return null;
  }
  const cut = decoded.lastIndexOf("/");
  if (cut <= 0) return null;
  return { group: decoded.slice(0, cut), case: decoded.slice(cut + 1) };
}

// ---- the metrics -----------------------------------------------------------------------

/** The metrics the score table shows, in the published order. */
export const METRICS: MetricName[] = ["pixel", "jaccard", "ssim", "text_boundary"];

/** The short label each metric wears in a table header. */
export const METRIC_LABEL: Record<MetricName, string> = {
  pixel: "Pixel",
  jaccard: "J",
  ssim: "SSIM",
  text_boundary: "TB",
};

/** What each metric means; the tooltip on its header cell. */
export const METRIC_INFO: Record<MetricName, string> = {
  pixel:
    "Recorded bench pixel score (0–100), not recomputed here. ITT failures count zero. J/SSIM/TB are separate upstream page-metrics. Missing means no published measurement.",
  jaccard:
    "Jaccard on ink pixels: both pages rendered at 150 DPI, a pixel is ink when its luma is below 200, score = ink in both ÷ ink in either. Exact placement matters: a one-line vertical shift sends it toward zero.",
  ssim: "Structural similarity on 8×8 luma windows, each window allowed to search ±8 px vertically for its best match, so small vertical drift is forgiven. Only windows that contain ink count. Measures shape and texture rather than exact position.",
  text_boundary:
    "Text boundary: share of text lines (mutool extraction) whose first and last word match the reference line at the same position. Pages whose line counts differ by more than 15% are skipped. Measures line breaking and pagination, independent of fonts and pixels.",
};

/** The metrics a score table shows, time last. */
export type ScoreColumn = MetricName | "time";

/** The label each score column wears in a table header. */
export const SCORE_LABEL: Record<ScoreColumn, string> = {
  pixel: "Pixel",
  jaccard: "J",
  ssim: "SSIM",
  text_boundary: "TB",
  time: "s",
};

/** The palette the lane colours come from, in the published order. */
export const LANE_COLORS = [
  "#0A0A0A",
  "#FFD400",
  "#00274C",
  "#FF5C00",
  "#1F8A5B",
  "#2A6FDB",
  "#6B6B6B",
  "#8C6A00",
  "#7D4085",
  "#B4232F",
  "#0E7C86",
];

/** The colour of one lane, by its position in the engine list. */
export function laneColor(engines: Engine[], key: string): string {
  const index = engines.findIndex((engine) => engine.key === key);
  const at = Math.max(index, 0);
  return LANE_COLORS[at % LANE_COLORS.length];
}

/** A score as the page shows it: one decimal and a percent sign. */
export function formatScore(value: number | null | undefined): string {
  if (value === null || value === undefined) return "–";
  return `${value.toFixed(1)}%`;
}

/**
 * A page score as the page shows it: one decimal, or a dash when the page
 * could not be scored.
 */
export function formatPageScore(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return value.toFixed(1);
}

/**
 * The score of one shown page, under the page it belongs to. A lane
 * without per-page scores draws none at all.
 */
function renderPageScore(value: number | null | undefined, pageNo: number): string {
  if (value === null || value === undefined) {
    return `<div class="page-score" title="Page ${esc(pageNo)} was not scored">—</div>`;
  }
  return `<div class="page-score" title="Page ${esc(pageNo)} score (0–100)">${esc(
    formatPageScore(value),
  )}</div>`;
}

/** A duration as the page shows it: seconds with two decimals. */
export function formatTime(value: number | null | undefined): string {
  if (value === null || value === undefined) return "–";
  return `${value.toFixed(2)} s`;
}

// ---- the render layer ------------------------------------------------------------------

/** One lane's column of pages. */
export interface CaseStripOptions {
  /** The case the strip belongs to. */
  case: Case;
  /** The lane the strip shows. */
  engine: Engine;
  /** The public base every `~/` asset path resolves against. */
  assetsBase: string;
  /** How many pages to show (the "more pages" step). */
  limit?: number;
  /** The page numbers the slots stand for (the case's own `shown`). */
  shown?: number[] | null;
  /** The mobile layout: crop the page to its top half. */
  half?: boolean;
}

/**
 * One lane's column of pages: the images, or the label that says why there
 * are none. The pages come from the release; the label comes from the lane's
 * state.
 */
export function renderCaseStrip(opts: CaseStripOptions): string {
  const c = opts.case;
  const key = opts.engine.key;
  const state = laneState(c, key);
  const label = opts.engine.label;
  const pages = c.pages?.[key] ?? [];
  const limit = Math.max(1, opts.limit ?? pages.length);
  const shown = opts.shown ?? c.shown ?? null;

  if (state === "unavailable" || state === "not-applicable" || state === "dropped") {
    return `<div class="col" data-lane="${esc(key)}" data-state="${esc(state)}">
<div class="page"><div class="missing">${esc(LANE_LABEL[state])}</div></div>
</div>`;
  }

  const slots = pages.slice(0, limit);
  const pageScores = c.page_scores?.[key];
  const items = slots
    .map((path, i) => {
      const pageNo = shown?.[i] ?? i + 1;
      const src = safeAssetUrl(opts.assetsBase, path);
      const className = opts.half ? "page half" : "page";
      if (!src) {
        return `<div class="${className}"><div class="missing">no page ${esc(pageNo)}</div></div>`;
      }
      const score =
        pageScores && i < pageScores.length ? renderPageScore(pageScores[i], pageNo) : "";
      return `<div class="${className}"><img src="${esc(src)}" width="1020" height="1320" loading="lazy" decoding="async" alt="${esc(label)}, page ${esc(pageNo)}"></div>${score}`;
    })
    .join("");

  const error = c.errors?.[key];
  const errorNote = error ? `<div class="lane-error">${esc(error)}</div>` : "";
  return `<div class="col" data-lane="${esc(key)}" data-state="${esc(state)}">
${items || `<div class="page"><div class="missing">${esc(LANE_LABEL[state])}</div></div>`}
${errorNote}
</div>`;
}

/** One lane's header: the name, the version, the page count, the scores. */
export interface CaseHeadOptions {
  case: Case;
  engine: Engine;
  assetsBase: string;
  /** The engine list, for the lane's colour. */
  engines?: Engine[];
  /** The compact header the mobile layout wears. */
  compact?: boolean;
  /** The public base the case's files resolve against (Hugging Face). */
  filesBase?: string;
}

/** One lane's header. */
export function renderCaseHead(opts: CaseHeadOptions): string {
  const c = opts.case;
  const key = opts.engine.key;
  const label = opts.engine.label;
  const scores = c.scores?.[key] ?? {};
  const shown = (c.pages?.[key] ?? []).filter((slot) => slot !== null).length;
  const pages = c.page_counts?.[key] ?? shown;
  const version = c.versions?.[key] ?? "";
  const color = opts.engines ? laneColor(opts.engines, key) : LANE_COLORS[0];
  // A reference PDF printed by another producer is not Word's own export; say so.
  const odd =
    key === "reference" && c.reference_app && c.reference_app !== "Microsoft Word"
      ? ` (${c.reference_app})`
      : "";
  const ver = `${version}${odd}${c.errors?.[key] ? " · no scored PDF" : ""}`;
  const pdf = c.pdfs?.[key];
  const pdfUrl = safeAssetUrl(opts.assetsBase, pdf);
  const metricText = METRICS.filter((metric) => scores[metric] != null)
    .map(
      (metric) =>
        ` · <span title="${esc(METRIC_INFO[metric])}">${esc(METRIC_LABEL[metric])} ${esc(
          formatScore(scores[metric]),
        )}</span>`,
    )
    .join("");
  const count = c.shown
    ? pages > shown
      ? ` (${shown} shown)`
      : ""
    : pages > shown
      ? ` (first ${shown} shown)`
      : "";
  const state = laneState(c, key);

  const fileUrl = opts.filesBase ? safeFileUrl(opts.filesBase, c.files?.[key]) : "";
  const filesLink = fileUrl
    ? ` <a class="files" href="${esc(fileUrl)}" target="_blank" rel="noopener" title="The case's files on Hugging Face">files ↗</a>`
    : "";

  if (opts.compact) {
    const first = METRICS.find((metric) => scores[metric] != null);
    const score = first ? ` · ${METRIC_LABEL[first]} ${formatScore(scores[first])}` : "";
    return `<h3 class="colhead" style="border-top:2px solid ${esc(color)}"><b>${esc(label)}</b>${filesLink} · ${esc(
      pages,
    )} p${esc(score)}</h3>`;
  }

  return `<h3 class="colhead" style="border-top:2px solid ${esc(color)}"><b>${esc(label)}</b>${
    pdfUrl
      ? ` <a href="${esc(pdfUrl)}" target="_blank" rel="noopener" title="Shown pages as a PDF">PDF</a>`
      : ""
  }${filesLink}${ver ? ` <span class="ver">${esc(ver)}</span>` : ""} · ${esc(pages)} p${esc(count)}${metricText}${
    state === "unavailable" || state === "not-applicable" || state === "dropped"
      ? ` · <span class="lane-note">${esc(LANE_LABEL[state])}</span>`
      : ""
  }</h3>`;
}

/** The whole grid: every lane's header, then every lane's column. */
export interface CaseGridOptions {
  case: Case;
  /** The lanes to draw, in order. */
  lanes: { engine: Engine; state: LaneState }[];
  assetsBase: string;
  /** The engine list, for the lane colours. */
  engines?: Engine[];
  /** How many pages to show. */
  limit?: number;
  /** The compact headers the mobile layout wears. */
  compact?: boolean;
  /** The mobile layout: crop the page to its top half. */
  half?: boolean;
  /** The public base the case's files resolve against (Hugging Face). */
  filesBase?: string;
}

/** The whole grid. */
export function renderCaseGrid(opts: CaseGridOptions): string {
  const heads = opts.lanes
    .map((lane) =>
      renderCaseHead({
        case: opts.case,
        engine: lane.engine,
        assetsBase: opts.assetsBase,
        ...(opts.engines ? { engines: opts.engines } : {}),
        ...(opts.compact ? { compact: true } : {}),
        ...(opts.filesBase ? { filesBase: opts.filesBase } : {}),
      }),
    )
    .join("");
  const cols = opts.lanes
    .map((lane) =>
      renderCaseStrip({
        case: opts.case,
        engine: lane.engine,
        assetsBase: opts.assetsBase,
        ...(opts.limit === undefined ? {} : { limit: opts.limit }),
        ...(opts.case.shown === undefined ? {} : { shown: opts.case.shown }),
        ...(opts.half ? { half: true } : {}),
      }),
    )
    .join("");
  // The case's own files, on the record: one link for the whole case, above
  // the lanes' columns.
  const filesUrl = opts.filesBase ? caseFilesUrl(opts.filesBase, opts.case) : "";
  const filesLink = filesUrl
    ? `<div class="case-files" style="grid-column:1 / -1"><a href="${esc(filesUrl)}" target="_blank" rel="noopener" title="The case's files on Hugging Face">files on Hugging Face ↗</a></div>`
    : "";
  return `${filesLink}${heads}${cols}`;
}

/** The overlay: one page of Word with one page of an engine over it. */
export interface OverlayOptions {
  case: Case;
  /** The lane under. */
  under: Engine;
  /** The lane over. */
  over: Engine;
  assetsBase: string;
  /** How many pages to show. */
  limit?: number;
  /** The blend mode ("normal", "difference", "multiply"). */
  blend?: string;
  /** The opacity of the lane over, in percent. */
  alpha?: number;
}

/** The overlay. */
export function renderOverlay(opts: OverlayOptions): string {
  const c = opts.case;
  const pages = Math.max(
    1,
    ...[opts.under.key, opts.over.key].map((key) => (c.pages?.[key] ?? []).length),
  );
  const limit = Math.max(1, opts.limit ?? pages);
  const shown = c.shown ?? null;
  const blend = opts.blend ?? "normal";
  const alpha = opts.alpha ?? 50;
  const under = c.pages?.[opts.under.key] ?? [];
  const over = c.pages?.[opts.over.key] ?? [];
  const pageScores = c.page_scores?.[opts.over.key];
  const items = Array.from({ length: Math.min(limit, pages) }, (_, i) => {
    const a = safeAssetUrl(opts.assetsBase, under[i]);
    const b = safeAssetUrl(opts.assetsBase, over[i]);
    const pageNo = shown?.[i] ?? i + 1;
    const score = pageScores && i < pageScores.length ? renderPageScore(pageScores[i], pageNo) : "";
    return `<div class="ovl-page" style="position:relative;margin-bottom:8px">${
      a
        ? `<img src="${esc(a)}" width="1020" height="1320" alt="${esc(opts.under.label)}, page ${esc(pageNo)}">`
        : '<div class="missing">no page</div>'
    }${
      b
        ? `<img class="top" src="${esc(b)}" width="1020" height="1320" alt="${esc(opts.over.label)}, page ${esc(pageNo)}" style="opacity:${alpha / 100};mix-blend-mode:${esc(blend)}">`
        : ""
    }${score}</div>`;
  }).join("");
  return items;
}

/** The case list in the side panel. */
export interface CaseListOptions {
  cases: Case[];
  /** The id of the selected case. */
  selected?: string;
  /** The text filter, already applied by the caller. */
  filter?: string;
}

/** The case list. */
export function renderCaseList(opts: CaseListOptions): string {
  return opts.cases
    .map(
      (c) =>
        `<div class="case${opts.selected === c.case ? " sel" : ""}" data-case="${esc(c.case)}"><span class="name" title="${esc(c.case)}">${esc(c.case)}</span><span class="grp">${esc(c.group)}</span></div>`,
    )
    .join("");
}

/** The group picker: one option per group of this kind. */
export function renderGroupOptions(groups: ShardRef[], selected?: string): string {
  return groups
    .map(
      (group) =>
        `<option value="${esc(group.group)}"${group.group === selected ? " selected" : ""}>${esc(
          group.group,
        )} (${esc(group.count)})</option>`,
    )
    .join("");
}

/** The engine toggles: one per lane, the ones without data folded away. */
export interface EngineToggleOptions {
  /** Every lane of the release — the lane colours come from its order. */
  engines: Engine[];
  /**
   * The lanes to draw, in display order (`orderLanes` of the group on
   * screen). Defaults to `engines`, storage order and all.
   */
  lanes?: Engine[];
  /** Which lanes are on. */
  on: Record<string, boolean>;
  /** The lanes that have data in the group on screen. */
  active?: Set<string>;
  /** The version each lane wears (the case's own, or the group's). */
  versions?: Record<string, string>;
  /** What each lane holds for the case on screen. */
  states?: Record<string, LaneState>;
}

/** The engine toggles. */
export function renderEngineToggles(opts: EngineToggleOptions): string {
  const lanes = opts.lanes ?? opts.engines;
  const active = opts.active;
  const items = lanes.map((engine, i) => {
    const legacy = active ? !active.has(engine.key) : false;
    const version = opts.versions?.[engine.key] ?? "";
    const state = opts.states?.[engine.key];
    const note =
      state && state !== "measured" && state !== "no-pages" ? ` · ${LANE_LABEL[state]}` : "";
    return `<label${legacy ? ' class="legacy"' : ""} title="${esc(version)}"><input type="checkbox" data-e="${esc(
      engine.key,
    )}"${opts.on[engine.key] ? " checked" : ""}> <span class="sw" style="background:${esc(
      laneColor(opts.engines, engine.key),
    )}"></span> ${esc(engine.label)}${version ? ` <small class="ver">${esc(version)}</small>` : ""}${esc(
      note,
    )}${i < 9 ? ` <kbd>${esc(i + 1)}</kbd>` : ""}</label>`;
  });
  const legacyCount = active ? lanes.filter((engine) => !active.has(engine.key)).length : 0;
  const more = legacyCount
    ? `<button id="moreEng" type="button" aria-expanded="false" data-count="${esc(legacyCount)}">+${esc(
        legacyCount,
      )} more</button>`
    : "";
  return `${items.join("")}${more}`;
}

/** The score table: one row per case, one column per lane and metric. */
export interface ScoresTableOptions {
  cases: Case[];
  /** Every lane of the release — the lane colours come from its order. */
  engines: Engine[];
  /**
   * The lanes that get columns, in display order (`orderLanes` of the group
   * on screen). Defaults to `engines`.
   */
  lanes?: Engine[];
  /** The selected case's id. */
  selected?: string;
  /** The column the table is sorted by, and the way. */
  sort?: { col: number; dir: number };
}

/** The score table. */
export function renderScoresTable(opts: ScoresTableOptions): string {
  const cases = opts.cases;
  const laneList = opts.lanes ?? opts.engines;
  const engines = laneList.filter((engine) =>
    cases.some((c) => laneState(c, engine.key) !== "dropped" && c.scores?.[engine.key]),
  );
  const columns: ScoreColumn[] = [...METRICS, "time"];
  const shown = columns.filter(
    (column) =>
      column === "time" ||
      cases.some((c) => engines.some((engine) => c.scores?.[engine.key]?.[column] != null)),
  );
  const value = (c: Case, key: string, column: ScoreColumn): number | null => {
    if (column === "time") return c.times?.[key] ?? null;
    return c.scores?.[key]?.[column] ?? null;
  };
  const sort = opts.sort ?? { col: 0, dir: 1 };
  const rows = cases.map((c, i) => ({ c, i }));
  // The metric columns, in the order they are drawn: one per lane, per metric.
  const flat: { engine: Engine; column: ScoreColumn }[] = [];
  for (const engine of engines) {
    for (const column of shown) flat.push({ engine, column });
  }
  const cols: { get: (row: { c: Case; i: number }) => number | string | null; num: boolean }[] = [
    { get: (row) => row.c.case, num: false },
    { get: (row) => row.c.group, num: false },
    {
      get: (row) => row.c.page_counts?.reference ?? (row.c.pages?.reference ?? []).length,
      num: true,
    },
  ];
  for (const cell of flat) {
    cols.push({ get: (row) => value(row.c, cell.engine.key, cell.column), num: true });
  }
  const sortCol = cols[sort.col] ?? cols[0];
  rows.sort((a, b) => {
    const x = sortCol.get(a);
    const y = sortCol.get(b);
    if (x === null || x === undefined) return 1;
    if (y === null || y === undefined) return -1;
    if (typeof x === "string" && typeof y === "string") return sort.dir * x.localeCompare(y);
    if (typeof x === "number" && typeof y === "number") return sort.dir * (x - y);
    return 0;
  });
  const mean = (get: (row: { c: Case; i: number }) => number | string | null): number | null => {
    const values = rows.map(get).filter((v): v is number => typeof v === "number");
    if (!values.length) return null;
    return values.reduce((a, b) => a + b, 0) / values.length;
  };
  const head = (index: number, label: string, cls = "") =>
    `<th data-c="${esc(index)}" class="${esc(cls)}${index === sort.col ? " sorted" : ""}">${esc(
      label,
    )}${index === sort.col ? (sort.dir > 0 ? " ▲" : " ▼") : ""}</th>`;

  let html = `<div class="note">${esc(rows.length)} cases · click a column to sort, a row to open it · green = best engine for that column (highest score, lowest time)</div><table><thead>`;
  html += `<tr>${head(0, "case")}${head(1, "group")}${head(2, "pages", "num")}`;
  html += engines
    .map(
      (engine) =>
        `<th class="eng" colspan="${esc(shown.length)}" style="border-top:2px solid ${esc(
          laneColor(opts.engines, engine.key),
        )}">${esc(engine.label)}</th>`,
    )
    .join("");
  html += "</tr>";
  html +=
    "<tr><th></th><th></th><th></th>" +
    flat
      .map((cell, j) => {
        const title =
          cell.column === "time" ? "Conversion time, in seconds" : METRIC_INFO[cell.column];
        return `<th class="num${j % shown.length === 0 ? " first" : ""}" data-c="${esc(
          j + 3,
        )}" title="${esc(title)}">${esc(SCORE_LABEL[cell.column])}</th>`;
      })
      .join("") +
    "</tr>";
  html +=
    '<tr class="mean"><td>mean</td><td></td><td></td>' +
    cols
      .slice(3)
      .map((col, j) => {
        const cell = flat[j];
        const m = mean(col.get);
        const text = cell.column === "time" ? formatTime(m) : formatScore(m);
        return `<td class="num${j % shown.length === 0 ? " first" : ""}">${esc(text)}</td>`;
      })
      .join("") +
    "</tr></thead><tbody>";

  for (const row of rows) {
    const best: Partial<Record<ScoreColumn, number | null>> = {};
    for (const column of shown) {
      const values = engines
        .map((engine) => value(row.c, engine.key, column))
        .filter((v): v is number => v !== null && v !== undefined);
      best[column] = values.length
        ? column === "time"
          ? Math.min(...values)
          : Math.max(...values)
        : null;
    }
    html += `<tr data-case="${esc(row.c.case)}"${row.c.case === opts.selected ? ' class="sel"' : ""}>`;
    html += cols
      .map((col, j) => {
        const cell = j < 3 ? null : flat[j - 3];
        const v = cell ? value(row.c, cell.engine.key, cell.column) : null;
        const isBest = cell && v !== null && best[cell.column] !== null && v === best[cell.column];
        const cls = [
          col.num ? "num" : "",
          cell && j % shown.length === 3 ? "first" : "",
          isBest ? "best" : "",
        ]
          .filter(Boolean)
          .join(" ");
        const text =
          j === 0
            ? row.c.case
            : j === 1
              ? row.c.group
              : j === 2
                ? String(row.c.page_counts?.reference ?? (row.c.pages?.reference ?? []).length)
                : cell?.column === "time"
                  ? formatTime(v)
                  : formatScore(v);
        return `<td class="${esc(cls)}">${esc(text)}</td>`;
      })
      .join("");
    html += "</tr>";
  }
  return `${html}</tbody></table>`;
}

/** The legend: what the scores mean, as an accordion of notes. */
export interface CasesLegendOptions {
  kind: Kind;
  /** The number of cases the release holds. */
  count?: number;
}

/** The legend. */
export function renderCasesLegend(opts: CasesLegendOptions): string {
  const what =
    opts.kind === "redline"
      ? "Redlines produced by the engines below, rendered beside Microsoft Word's own compare and scored per page."
      : "Documents converted to PDF by the engines below, rendered beside Microsoft Word's own export and scored per page.";
  const items: { title: string; sub: string; body: string }[] = [
    {
      title: "What this is",
      sub: "",
      body: esc(
        `${what} The scores are the bench's own recorded numbers; they are not recomputed here.`,
      ),
    },
    ...METRICS.map((metric) => ({
      title: SCORE_LABEL[metric],
      sub: "",
      body: esc(METRIC_INFO[metric]),
    })),
    {
      title: "Lanes left out",
      sub: "",
      body: esc(
        "A lane marked dropped is not part of this case; not measured means the cohort has no published measurement for it; not applicable means the lane was excluded for cause. A lane that failed keeps its error under its pages.",
      ),
    },
  ];
  const links = `<a href="../index.html">DOCX → PDF</a><a href="../redlines/index.html">Redlines</a><a href="../speed/index.html">Speed</a>`;
  return `<details class="about"><summary><span class="chev">&#9656;</span><span class="ttl">About these scores</span><span class="hint">${esc(
    items.length,
  )} notes</span>${links}</summary><div class="items">${items
    .map(
      (item) =>
        `<details class="item"><summary><span class="chev">&#9656;</span><span class="dot" style="background:var(--mark)"></span><b>${esc(
          item.title,
        )}</b>${item.sub ? `<span class="sub">${esc(item.sub)}</span>` : ""}</summary><div>${item.body}</div></details>`,
    )
    .join("")}</div></details>`;
}

// ---- the page --------------------------------------------------------------------------

/** The page the browsers wear. */
export interface CasesPageOptions {
  /** Which browser this is. */
  kind: Kind;
  /** The index the page fetches, relative to the page. */
  indexUrl: string;
  /** The module the page imports, relative to the page. */
  moduleUrl: string;
  /** The stylesheet the page links, relative to the page. */
  stylesheet?: string;
  /** The page's title. */
  title?: string;
  /** The page's meta description. */
  description?: string;
  /** The link to the conversion browser. */
  conversionHref?: string;
  /** The link to the redline browser. */
  redlinesHref?: string;
  /** The link to the speed page. */
  speedHref?: string;
  /** The link to the leaderboard. */
  indexHref?: string;
}

/** The whole page: the shell the wiring fills in. No data in it. */
export function renderCasesPage(opts: CasesPageOptions): string {
  const title =
    opts.title ??
    (opts.kind === "redline"
      ? "neurotic_docx_bench: Redlines vs Microsoft Word"
      : "neurotic_docx_bench: DOCX to PDF vs Microsoft Word");
  const description =
    opts.description ??
    (opts.kind === "redline"
      ? "Redlines produced by jubarte, docxodus and SuperDoc, rendered beside Microsoft Word's compare and scored per page by neurotic_docx_bench."
      : "Side-by-side pages of DOCX to PDF engines against Microsoft Word's own export, scored per page by neurotic_docx_bench.");
  const stylesheet = opts.stylesheet ?? "../cases.css";
  const conversionHref = opts.conversionHref ?? "../cases/index.html";
  const redlinesHref = opts.redlinesHref ?? "../redlines/index.html";
  const speedHref = opts.speedHref ?? "../speed/index.html";
  const indexHref = opts.indexHref ?? "../index.html";
  const modeValue = opts.kind === "redline" ? redlinesHref : conversionHref;
  const crumb =
    opts.kind === "redline" ? "Redlines vs Microsoft Word" : "DOCX → PDF vs Microsoft Word";

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)}</title>
<meta name="description" content="${esc(description)}">
<meta name="generator" content="@jandira-tech/bench-viewer">
<link rel="stylesheet" href="${esc(stylesheet)}">
</head>
<body class="viewer">
<header id="brand"><a class="logo" href="${esc(indexHref)}">NEUROTIC.DOCX.BENCH</a><span class="crumb">/ ${esc(
    crumb,
  )}</span><span class="links"><a href="${esc(indexHref)}">Scores</a><a href="${esc(
    speedHref,
  )}">Speed</a><a href="https://github.com/jandira-tech/neurotic_docx_bench">Bench repo ↗</a></span></header>
<div id="mbar"><button id="mMenu" type="button" aria-label="Open the case list" aria-expanded="false" aria-controls="side">&#9776;</button><select id="mMode" aria-label="Which bench"></select><button id="mLayout" type="button">Layout</button></div>
<div id="mhead"><span id="mCase"></span><span id="mPos"></span><label>vs <select id="mSecond" aria-label="Engine compared with Word"></select></label><button id="mExpand" type="button" class="hidden">Whole page</button></div>
<div id="bar">
  <button id="sideToggle" aria-label="Hide or show the case list" title="hide / show the case list (s)">&#9776;</button>
  <span class="grp"><select id="mode" autocomplete="off" title="what to compare"><option value="${esc(
    conversionHref,
  )}">Convert DOCX → PDF</option><option value="${esc(
    redlinesHref,
  )}"${opts.kind === "redline" ? " selected" : ""}>Compare (redline) two documents</option></select></span>
  <span class="grp" id="nav"><button id="navPrev" title="previous case (&uarr;)">&lsaquo; prev</button><button id="navRand" title="random case (r)">random</button><button id="navNext" title="next case (&darr;)">next &rsaquo;</button><span id="navPos"></span></span>
  <span class="grp"><span id="pageinfo"></span></span>
  <span class="grp"><label>zoom <input type="range" id="zoom" min="200" max="1400" value="600" step="20"></label></span>
  <span class="grp"><label><input type="checkbox" id="ovl"> overlay</label><select id="ovlA" aria-label="Engine under"></select> under <select id="ovlB" aria-label="Engine over"></select><select id="blend" aria-label="Blend mode"><option value="normal">opacity</option><option value="difference">difference</option><option value="multiply">multiply</option></select><input type="range" id="alpha" aria-label="Overlay opacity" min="0" max="100" value="50"></span>
  <span class="grp"><button id="viewToggle">Scores table</button></span>
  <span id="keys" class="hidden"><kbd>1</kbd>-<kbd>9</kbd> engines &nbsp;<kbd>&uarr;</kbd><kbd>&darr;</kbd> cases &nbsp;<kbd>r</kbd> random &nbsp;<kbd>s</kbd> side panel &nbsp;<kbd>o</kbd> overlay &nbsp;<kbd>m</kbd> more pages &nbsp;<kbd>t</kbd> scores table</span>
</div>
<div id="engines" aria-label="Engines"></div>
<div id="legend"></div>
<aside id="side" aria-label="Cases"><div id="sidehead"><input id="filter" type="search" autocomplete="off" aria-label="Filter cases" placeholder="filter cases (name, group)…"><div id="fx">
  <label for="fxGroup">group</label><select id="fxGroup"></select>
  <label for="fxPages">pages</label><select id="fxPages"><option value="">any</option><option value="1-1">1</option><option value="2-3">2–3</option><option value="4-10">4–10</option><option value="11-">11+</option></select>
  <label for="fxEng">score</label><span class="row"><select id="fxEng"></select><select id="fxMetric" aria-label="Score metric"></select> ≤ <input type="number" id="fxMax" aria-label="Maximum score" min="0" max="100" step="1" placeholder="any"></span>
  <label for="fxDiffer">pages</label><span class="row"><label><input type="checkbox" id="fxDiffer"> differ from Word</label></span>
  <span class="foot"><span id="fxn"></span><button id="fxRand" title="open a random case of this list (r)">random</button><button id="fxClear" title="clear every filter">clear</button></span>
</div></div><div id="list"><div class="case" aria-busy="true"><span class="name">Loading cases…</span></div></div></aside>
<main id="main"><div id="grid"></div><div id="overlay" class="hidden"></div><button id="more" class="hidden">more pages</button><div id="scores" class="hidden"></div></main>
<div id="mfoot"><button id="mPrev" type="button">&lsaquo; Prev</button><button id="mRand" type="button">Random</button><button id="mNext" type="button">Next &rsaquo;</button><button id="mOvl" type="button" aria-pressed="false">Overlay</button></div>
<div id="scrim"></div>
<dialog id="msheet" aria-labelledby="msheetTitle"><form method="dialog"><h2 id="msheetTitle"><span class="sq"></span> Mobile layout</h2>
<label class="opt"><input type="radio" name="ml" value="half"><span><b>Side by side, top half</b><small>Word and one engine, cropped to the top of each page so text stays legible. Tap “Whole page” to see the rest.</small></span></label>
<label class="opt"><input type="radio" name="ml" value="overlay"><span><b>Overlay, Word under the engine</b><small>One page, both renders stacked. “Overlay” in the bottom bar clears it.</small></span></label>
<label class="opt"><input type="radio" name="ml" value="tiny"><span><b>Side by side, whole pages</b><small>Two small full pages. Best for spotting pagination drift.</small></span></label>
<div class="row"><label>Blend <select id="mBlend"><option value="normal">opacity</option><option value="difference">difference</option><option value="multiply">multiply</option></select></label><label>Mix <input type="range" id="mAlpha" min="0" max="100" value="50"></label></div>
<button type="submit">Done</button></form></dialog>
<footer class="site"><span class="mono">neurotic_docx_bench · © MMXXVI</span><span>Maintained by <a href="https://arthur.law/" rel="noopener">Arthur Souza Rodrigues</a>, author of jubarte, one of the engines compared.</span><a href="${esc(
    indexHref,
  )}">Scores →</a><a href="${esc(speedHref)}">Speed</a><a href="https://github.com/jandira-tech/neurotic_docx_bench" rel="noopener">Bench repo →</a></footer>
<script type="module">
import { mountCasesPage } from "${esc(opts.moduleUrl)}";
mountCasesPage({ kind: ${JSON.stringify(opts.kind)}, indexUrl: "${esc(opts.indexUrl)}", modeUrl: "${esc(
    modeValue,
  )}" });
</script>
</body>
</html>
`;
}

// ---- the wiring ------------------------------------------------------------------------

/** How the wiring is told which browser it is. */
export interface MountCasesOptions {
  /** Which browser this is. */
  kind: Kind;
  /** The index the page fetches. */
  indexUrl: string;
  /** The other browser's URL, for the mode picker. */
  modeUrl?: string;
  /** The document the page lives in. */
  root?: Document;
  /**
   * The source of the random draw (the random case on open, the random
   * button). `Math.random` by default; a seeded generator makes the page
   * deterministic under test.
   */
  random?: () => number;
}

interface ViewerState {
  on: Record<string, boolean>;
  shown: number;
  zoom: number;
  ovl: boolean;
  ovlA: string;
  ovlB: string;
  blend: string;
  alpha: number;
  filter: string;
  view: "viewer" | "scores";
  sort: { col: number; dir: number };
  fx: { pages: string; eng: string; metric: string; max: string; differ: boolean };
  mobile: {
    layout: "half" | "overlay" | "tiny";
    second: string;
    blend: string;
    alpha: number;
    ovl: boolean | null;
    exp: boolean;
  };
}

/**
 * How many pages the grid shows before "more pages". The release shows up
 * to 12 pages of a case (the producer's own cap), so the page opens on all
 * of them.
 */
export const PAGE_STEP = 12;

/**
 * The index a random draw lands on, for a list of `length` items. -1 when
 * the list is empty; a draw outside [0, 1) lands on the first item.
 */
export function randomIndex(length: number, random: () => number = Math.random): number {
  if (length <= 0) return -1;
  const index = Math.floor(random() * length);
  return index >= 0 && index < length ? index : 0;
}

/**
 * A random item of the list, or undefined when the list is empty. The
 * random source is a parameter, so a seeded generator makes the choice
 * reproducible (the old viewer's `pickRandom`).
 */
export function pickRandomCase<T>(cases: T[], random: () => number = Math.random): T | undefined {
  const index = randomIndex(cases.length, random);
  return index < 0 ? undefined : cases[index];
}

function loadState(kind: Kind): ViewerState {
  const base: ViewerState = {
    on: {},
    shown: PAGE_STEP,
    zoom: 600,
    ovl: false,
    ovlA: "reference",
    ovlB: "",
    blend: "normal",
    alpha: 50,
    filter: "",
    view: "viewer",
    sort: { col: 0, dir: 1 },
    fx: { pages: "", eng: "", metric: "pixel", max: "", differ: false },
    mobile: { layout: "half", second: "", blend: "normal", alpha: 50, ovl: null, exp: false },
  };
  try {
    const saved = JSON.parse(localStorage.getItem(`ec.cases.${kind}`) ?? "null");
    if (saved && typeof saved === "object") Object.assign(base, saved);
  } catch {
    /* a broken state is a fresh state */
  }
  return base;
}

function saveState(kind: Kind, state: ViewerState): void {
  try {
    localStorage.setItem(`ec.cases.${kind}`, JSON.stringify(state));
  } catch {
    /* a full store is not a reason to stop */
  }
}

/**
 * Wire the page: fetch the index, open one group, and keep the page in step
 * with the state. The render layer does the markup; this does the fetching,
 * the events and the hash.
 */
export async function mountCasesPage(opts: MountCasesOptions): Promise<void> {
  const doc = opts.root ?? document;
  const $ = <T extends Element = HTMLElement>(selector: string): T | null =>
    doc.querySelector<T>(selector);
  const state = loadState(opts.kind);
  const shards = new Map<string, CaseShard>();
  let index: CasesIndex;
  let group = "";
  let sel = 0;
  let mobile = false;
  let loaded = false;
  /** The display order of the open group's lanes (`orderLanes`). */
  let laneOrder: Engine[] = [];
  /** The open group's lanes that have data (`lanesWithData`). */
  let laneData = new Set<string>();
  /** The last selection render() saw, to scroll the list only when it moves. */
  let lastSelKey = "";

  const engineByKey = (key: string): Engine =>
    index.engines.find((engine) => engine.key === key) ?? { key, label: key };

  try {
    const response = await fetch(opts.indexUrl);
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    index = parseCasesIndex(await response.json());
  } catch (err) {
    const list = $("#list");
    if (list) {
      list.innerHTML = `<div class="case"><span class="name">cases/index.json did not load</span><span class="grp">${esc(
        (err as Error).message,
      )}</span></div>`;
    }
    return;
  }

  const groups = index.groups.filter((group_) => group_.kind === opts.kind);
  if (!groups.length) {
    const list = $("#list");
    if (list) {
      list.innerHTML = `<div class="case"><span class="name">no ${esc(opts.kind)} group in this release</span></div>`;
    }
    return;
  }
  for (const engine of index.engines) {
    if (state.on[engine.key] === undefined) state.on[engine.key] = true;
  }
  if (!state.ovlA) state.ovlA = "reference";

  const groupSelect = $<HTMLSelectElement>("#fxGroup");
  if (groupSelect) groupSelect.innerHTML = renderGroupOptions(groups, group);

  const metricSelect = $<HTMLSelectElement>("#fxMetric");
  if (metricSelect) {
    metricSelect.innerHTML = METRICS.map(
      (metric) =>
        `<option value="${esc(metric)}" title="${esc(METRIC_INFO[metric])}">${esc(METRIC_LABEL[metric])}</option>`,
    ).join("");
    metricSelect.value = state.fx.metric;
  }
  // The lane pickers (#fxEng, #ovlA, #ovlB) are filled per group
  // (refreshPickers, from openGroup): a page shows only the lanes of its
  // kind, in the group's display order.
  const legend = $("#legend");
  if (legend) legend.innerHTML = renderCasesLegend({ kind: opts.kind });

  const cases = (): Case[] => shards.get(group)?.cases ?? [];
  const current = (): Case | undefined => cases()[sel];

  const visibleCases = (): Case[] => {
    const filter = state.filter.toLowerCase();
    return cases().filter((c) => {
      if (filter && !`${c.case} ${c.group}`.toLowerCase().includes(filter)) return false;
      const fx = state.fx;
      if (fx.pages) {
        const [lo, hi] = fx.pages
          .split("-")
          .map((x) => (x === "" ? Number.POSITIVE_INFINITY : Number(x)));
        const n = c.page_counts?.reference ?? (c.pages?.reference ?? []).length;
        if (n < lo || n > hi) return false;
      }
      if (fx.max !== "" && fx.max !== undefined) {
        const value = c.scores?.[fx.eng]?.[fx.metric as MetricName];
        if (value === null || value === undefined || value > Number(fx.max)) return false;
      }
      if (fx.differ) {
        const n = c.page_counts?.[fx.eng];
        const reference = c.page_counts?.reference ?? (c.pages?.reference ?? []).length;
        if (n === null || n === undefined || n === reference) return false;
      }
      return true;
    });
  };

  const versionOf = (key: string): string => {
    const versions = new Set<string>();
    for (const c of cases()) {
      if (laneState(c, key) === "dropped") continue;
      const version = c.versions?.[key];
      if (version) versions.add(version);
    }
    if (versions.size > 1) return "varies by case";
    return [...versions][0] ?? "";
  };

  const mEngines = (c: Case): Engine[] =>
    laneOrder.filter(
      (engine) =>
        engine.key !== "reference" &&
        laneState(c, engine.key) !== "dropped" &&
        (c.pages?.[engine.key] ?? []).some((slot) => slot !== null),
    );

  const secondEngine = (c: Case): string => {
    const list = mEngines(c);
    return list.some((engine) => engine.key === state.mobile.second)
      ? state.mobile.second
      : (list[0]?.key ?? "");
  };

  const overlayTop = (c: Case, want: string): string => {
    const has = (key: string) =>
      key !== "reference" && laneState(c, key) !== "dropped" && (c.pages?.[key] ?? []).length > 0;
    if (has(want)) return want;
    return laneOrder.find((engine) => has(engine.key))?.key ?? "";
  };

  const mobileOverlay = (): boolean => state.mobile.ovl ?? state.mobile.layout === "overlay";

  const setMobile = (): void => {
    const query = new URLSearchParams(doc.defaultView?.location.search ?? "");
    const forced = query.get("mobile");
    const narrow = doc.defaultView?.matchMedia?.("(max-width: 720px)").matches ?? false;
    mobile = forced === "1" || (forced !== "0" && narrow);
    doc.body?.classList.toggle("mobile", mobile);
  };

  const renderNow = (): void => {
    saveState(opts.kind, state);
    const list = $("#list");
    const shown = visibleCases();
    const at = shown.findIndex((c) => c.case === current()?.case);
    const count = $("#fxn");
    if (count) count.textContent = `${shown.length} of ${cases().length} cases`;
    const navPos = $("#navPos");
    if (navPos) navPos.textContent = `${at < 0 ? "–" : at + 1} / ${shown.length}`;
    if (list) list.innerHTML = renderCaseList({ cases: shown, selected: current()?.case });

    const enginesBar = $("#engines");
    if (enginesBar) {
      const c = current();
      enginesBar.innerHTML = renderEngineToggles({
        engines: index.engines,
        lanes: laneOrder,
        on: state.on,
        active: laneData,
        versions: Object.fromEntries(
          laneOrder.map((engine) => [engine.key, versionOf(engine.key)]),
        ),
        ...(c
          ? {
              states: Object.fromEntries(
                laneOrder.map((engine) => [engine.key, laneState(c, engine.key)]),
              ),
            }
          : {}),
      });
    }

    const c = current();
    if (!c) return;

    const table = state.view === "scores";
    const toggle = $("#viewToggle");
    if (toggle) toggle.textContent = table ? "Viewer" : "Scores table";
    const hash = table ? "#scores" : caseHash(c.group, c.case);
    if (doc.defaultView && doc.defaultView.location.hash !== hash) {
      doc.defaultView.history.replaceState(null, "", hash);
    }
    const scores = $("#scores");
    const grid = $("#grid");
    const overlay = $("#overlay");
    const more = $("#more");
    if (scores) scores.classList.toggle("hidden", !table);
    if (table) {
      grid?.classList.add("hidden");
      overlay?.classList.add("hidden");
      more?.classList.add("hidden");
      const pageinfo = $("#pageinfo");
      if (pageinfo) pageinfo.textContent = "";
      if (scores) {
        scores.innerHTML = renderScoresTable({
          cases: shown,
          engines: index.engines,
          lanes: laneOrder,
          selected: c.case,
          sort: state.sort,
        });
      }
      return;
    }
    grid?.classList.remove("hidden");
    scores?.classList.add("hidden");

    const lanes = lanesForCase(c, laneOrder).filter((lane) => lane.state !== "dropped");
    const on = mobile
      ? lanes.filter(
          (lane) => lane.engine.key === "reference" || lane.engine.key === secondEngine(c),
        )
      : lanes.filter((lane) => state.on[lane.engine.key]);
    const maxPages = Math.max(1, ...Object.values(c.pages ?? {}).map((pages) => pages.length));
    state.shown = Math.min(Math.max(PAGE_STEP, state.shown), maxPages);
    const pageinfo = $("#pageinfo");
    if (pageinfo) {
      pageinfo.textContent = `pages 1–${state.shown} of ${c.page_counts?.reference ?? maxPages}`;
    }
    const left = maxPages - state.shown;
    if (more) {
      more.classList.toggle("hidden", left <= 0);
      more.textContent = `more pages (${left} left)`;
    }

    const overlayOn = mobile ? mobileOverlay() : state.ovl;
    const under = mobile ? "reference" : state.ovlA;
    // The lane over Word defaults to the display order's second non-reference
    // lane until the visitor picks one (no product preference: the group's own
    // scored-case counts decide).
    const overKey =
      state.ovlB && laneOrder.some((engine) => engine.key === state.ovlB)
        ? state.ovlB
        : (defaultOverlayLane(laneOrder)?.key ?? "");
    const over = mobile ? secondEngine(c) : overlayTop(c, overKey);
    const blend = mobile ? state.mobile.blend : state.blend;
    const alpha = mobile ? state.mobile.alpha : state.alpha;
    const overSelect = $<HTMLSelectElement>("#ovlB");
    if (overSelect && over) overSelect.value = over;

    grid?.classList.toggle("hidden", overlayOn);
    overlay?.classList.toggle("hidden", !overlayOn);
    if (overlayOn) {
      if (overlay) {
        overlay.style.width = mobile ? "" : `${state.zoom}px`;
        overlay.innerHTML = renderOverlay({
          case: c,
          under: engineByKey(under),
          over: engineByKey(over),
          assetsBase: index.assets_base,
          limit: state.shown,
          blend,
          alpha,
        });
      }
      return;
    }

    if (grid) {
      grid.style.gridTemplateColumns = mobile
        ? `repeat(${on.length}, minmax(0,1fr))`
        : `repeat(${on.length}, ${state.zoom}px)`;
      grid.innerHTML = renderCaseGrid({
        case: c,
        lanes: on,
        assetsBase: index.assets_base,
        engines: index.engines,
        limit: state.shown,
        compact: mobile,
        half: mobile && state.mobile.layout === "half",
        ...(index.files_base ? { filesBase: index.files_base } : {}),
      });
    }
    if (mobile) renderMobile(c, shown, at);
  };

  /**
   * Scroll the selected case to the middle of the list area, below the sticky
   * filters — the hardened copy's behaviour, so the case the hash, prev/next
   * or random picked is always in view.
   */
  const showSel = (): void => {
    const side = $("#side");
    const selected = side?.querySelector<HTMLElement>(".sel");
    const head = $("#sidehead");
    if (!side || !head) return;
    $("#list")?.style.setProperty("--headh", `${head.offsetHeight}px`);
    if (!selected) return;
    const room = side.clientHeight - head.offsetHeight;
    side.scrollTop +=
      selected.getBoundingClientRect().top -
      side.getBoundingClientRect().top -
      head.offsetHeight -
      Math.max(0, (room - selected.offsetHeight) / 2);
  };

  /**
   * Fill the lane pickers for the group on screen: only the lanes of the
   * page's kind, in the group's display order, Word first. A saved pick that
   * is not one of them falls back to the display order's default.
   */
  const refreshPickers = (): void => {
    const options = laneOrder
      .map((engine) => `<option value="${esc(engine.key)}">${esc(engine.label)}</option>`)
      .join("");
    const under = $<HTMLSelectElement>("#ovlA");
    if (under) {
      under.innerHTML = options;
      const value = laneOrder.some((engine) => engine.key === state.ovlA)
        ? state.ovlA
        : "reference";
      under.value = value;
      state.ovlA = value;
    }
    const over = $<HTMLSelectElement>("#ovlB");
    if (over) over.innerHTML = options;
    const fx = $<HTMLSelectElement>("#fxEng");
    if (fx) {
      fx.innerHTML = laneOrder
        .filter((engine) => engine.key !== "reference")
        .map((engine) => `<option value="${esc(engine.key)}">${esc(engine.label)}</option>`)
        .join("");
      if (!state.fx.eng || !laneOrder.some((engine) => engine.key === state.fx.eng)) {
        state.fx.eng = defaultComparisonLane(laneOrder)?.key ?? "";
      }
      fx.value = state.fx.eng;
    }
  };

  const render = (): void => {
    const before = lastSelKey;
    renderNow();
    const c = current();
    const key = c ? `${group}/${c.case}` : "";
    if (key !== before) {
      lastSelKey = key;
      showSel();
    }
  };

  const renderMobile = (c: Case, shown: Case[], at: number): void => {
    const name = $("#mCase");
    if (name) {
      name.textContent = c.case;
      name.title = `${c.group}/${c.case}`;
    }
    const position = $("#mPos");
    if (position) position.textContent = `${at < 0 ? "–" : at + 1} / ${shown.length}`;
    const select = $<HTMLSelectElement>("#mSecond");
    if (select) {
      select.innerHTML = mEngines(c)
        .map((engine) => `<option value="${esc(engine.key)}">${esc(engine.label)}</option>`)
        .join("");
      select.value = secondEngine(c);
    }
    const overlayButton = $("#mOvl");
    if (overlayButton) overlayButton.setAttribute("aria-pressed", String(mobileOverlay()));
    const expand = $("#mExpand");
    if (expand) {
      expand.classList.toggle("hidden", mobileOverlay() || state.mobile.layout !== "half");
      expand.textContent = state.mobile.exp ? "Top half" : "Whole page";
    }
    doc.body?.classList.toggle("mexp", state.mobile.exp);
    const sheet = doc.querySelector<HTMLInputElement>('#msheet input[name="ml"]');
    if (sheet) sheet.checked = sheet.value === state.mobile.layout;
  };

  const step = (delta: number): void => {
    const shown = visibleCases();
    if (!shown.length) return;
    const at = shown.findIndex((c) => c.case === current()?.case);
    const next = at < 0 ? 0 : (at + delta + shown.length) % shown.length;
    sel = cases().findIndex((c) => c.case === shown[next].case);
    state.view = "viewer";
    state.shown = PAGE_STEP;
    render();
  };

  const pickRandom = (): void => {
    const chosen = pickRandomCase(visibleCases(), opts.random);
    if (!chosen) return;
    sel = cases().findIndex((c) => c.case === chosen.case);
    state.view = "viewer";
    state.shown = PAGE_STEP;
  };

  const openGroup = async (name: string, caseId?: string): Promise<void> => {
    const ref = groups.find((entry) => entry.group === name);
    if (!ref) return;
    group = name;
    const groupSelectNow = $<HTMLSelectElement>("#fxGroup");
    if (groupSelectNow) groupSelectNow.value = name;
    if (!shards.has(name)) {
      const url = shardUrl(opts.indexUrl, ref.path, doc.defaultView?.location.href);
      const response = await fetch(url);
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      shards.set(name, parseCaseShard(await response.json()));
    }
    const list = cases();
    laneOrder = orderLanes(list, index.engines);
    laneData = lanesWithData(list);
    refreshPickers();
    const at = caseId ? list.findIndex((c) => c.case === caseId) : 0;
    sel = Math.max(at, 0);
    state.shown = PAGE_STEP;
    loaded = true;
    render();
  };

  const applyHash = async (): Promise<boolean> => {
    const hash = doc.defaultView?.location.hash ?? "";
    if (hash === "#scores") {
      state.view = "scores";
      return true;
    }
    const parsed = parseCaseHash(
      hash,
      groups.map((entry) => entry.group),
    );
    if (!parsed) return false;
    state.view = "viewer";
    if (parsed.group !== group) await openGroup(parsed.group, parsed.case);
    else {
      const at = cases().findIndex((c) => c.case === parsed.case);
      if (at >= 0) sel = at;
    }
    return true;
  };

  // ---- the events

  const list = $("#list");
  list?.addEventListener("click", (event) => {
    const target = (event.target as Element | null)?.closest<HTMLElement>("[data-case]");
    if (!target) return;
    const id = target.dataset.case;
    const at = cases().findIndex((c) => c.case === id);
    if (at < 0) return;
    sel = at;
    state.view = "viewer";
    state.shown = PAGE_STEP;
    closeDrawer();
    render();
  });

  const scores = $("#scores");
  scores?.addEventListener("click", (event) => {
    const target = event.target as HTMLElement | null;
    const head = target?.closest<HTMLElement>("th[data-c]");
    if (head) {
      const col = Number(head.dataset.c);
      state.sort = {
        col,
        dir: col === state.sort.col ? -state.sort.dir : col >= 3 ? -1 : 1,
      };
      render();
      return;
    }
    const row = target?.closest<HTMLElement>("tr[data-case]");
    if (row?.dataset.case) {
      const at = cases().findIndex((c) => c.case === row.dataset.case);
      if (at >= 0) {
        sel = at;
        state.view = "viewer";
        state.shown = PAGE_STEP;
        render();
      }
    }
  });

  const enginesBar = $("#engines");
  enginesBar?.addEventListener("change", (event) => {
    const box = event.target as HTMLInputElement | null;
    if (!box?.dataset.e) return;
    state.on[box.dataset.e] = box.checked;
    render();
  });
  enginesBar?.addEventListener("click", (event) => {
    const button = (event.target as Element | null)?.closest<HTMLElement>("#moreEng");
    if (!button) return;
    const open = doc.body?.classList.toggle("alleng") ?? false;
    button.setAttribute("aria-expanded", String(open));
    button.textContent = open ? "fewer" : `+${button.dataset.count ?? "0"} more`;
  });

  const groupSelectNow = $<HTMLSelectElement>("#fxGroup");
  groupSelectNow?.addEventListener("change", (event) => {
    const value = (event.target as HTMLSelectElement).value;
    void openGroup(value).catch(() => undefined);
  });

  $("#navPrev")?.addEventListener("click", () => step(-1));
  $("#navNext")?.addEventListener("click", () => step(1));
  $("#navRand")?.addEventListener("click", () => {
    pickRandom();
    render();
  });
  $("#more")?.addEventListener("click", () => {
    state.shown += PAGE_STEP;
    render();
  });
  $("#viewToggle")?.addEventListener("click", () => {
    state.view = state.view === "scores" ? "viewer" : "scores";
    render();
  });
  const zoom = $<HTMLInputElement>("#zoom");
  zoom?.addEventListener("input", (event) => {
    state.zoom = Number((event.target as HTMLInputElement).value);
    render();
  });
  const overlayBox = $<HTMLInputElement>("#ovl");
  overlayBox?.addEventListener("change", (event) => {
    state.ovl = (event.target as HTMLInputElement).checked;
    render();
  });
  const underSelect = $<HTMLSelectElement>("#ovlA");
  underSelect?.addEventListener("change", (event) => {
    state.ovlA = (event.target as HTMLSelectElement).value;
    render();
  });
  const overSelect = $<HTMLSelectElement>("#ovlB");
  overSelect?.addEventListener("change", (event) => {
    state.ovlB = (event.target as HTMLSelectElement).value;
    render();
  });
  const blendSelect = $<HTMLSelectElement>("#blend");
  blendSelect?.addEventListener("change", (event) => {
    state.blend = (event.target as HTMLSelectElement).value;
    render();
  });
  const alpha = $<HTMLInputElement>("#alpha");
  alpha?.addEventListener("input", (event) => {
    state.alpha = Number((event.target as HTMLInputElement).value);
    render();
  });
  const filter = $<HTMLInputElement>("#filter");
  filter?.addEventListener("input", (event) => {
    state.filter = (event.target as HTMLInputElement).value;
    render();
  });
  const fxPages = $<HTMLSelectElement>("#fxPages");
  fxPages?.addEventListener("change", (event) => {
    state.fx.pages = (event.target as HTMLSelectElement).value;
    render();
  });
  const fxEngine = $<HTMLSelectElement>("#fxEng");
  fxEngine?.addEventListener("change", (event) => {
    state.fx.eng = (event.target as HTMLSelectElement).value;
    render();
  });
  const fxMetric = $<HTMLSelectElement>("#fxMetric");
  fxMetric?.addEventListener("change", (event) => {
    state.fx.metric = (event.target as HTMLSelectElement).value;
    render();
  });
  const fxMax = $<HTMLInputElement>("#fxMax");
  fxMax?.addEventListener("input", (event) => {
    state.fx.max = (event.target as HTMLInputElement).value;
    render();
  });
  const fxDiffer = $<HTMLInputElement>("#fxDiffer");
  fxDiffer?.addEventListener("change", (event) => {
    state.fx.differ = (event.target as HTMLInputElement).checked;
    render();
  });
  $("#fxClear")?.addEventListener("click", () => {
    Object.assign(state.fx, { pages: "", max: "", differ: false });
    state.filter = "";
    if (filter) filter.value = "";
    if (fxPages) fxPages.value = "";
    if (fxMax) fxMax.value = "";
    if (fxDiffer) fxDiffer.checked = false;
    render();
  });

  const modeSelect = $<HTMLSelectElement>("#mode");
  modeSelect?.addEventListener("change", (event) => {
    const value = (event.target as HTMLSelectElement).value;
    if (value && doc.defaultView) doc.defaultView.location.href = value;
  });
  const mobileMode = $<HTMLSelectElement>("#mMode");
  if (mobileMode && modeSelect) {
    mobileMode.innerHTML = modeSelect.innerHTML;
    mobileMode.addEventListener("change", (event) => {
      const value = (event.target as HTMLSelectElement).value;
      if (value && doc.defaultView) doc.defaultView.location.href = value;
    });
  }

  const sideToggle = $("#sideToggle");
  sideToggle?.addEventListener("click", () => {
    doc.body?.classList.toggle("noside");
    render();
    showSel();
  });
  const menu = $("#mMenu");
  menu?.addEventListener("click", () => {
    const open = doc.body?.classList.toggle("drawer") ?? false;
    menu.setAttribute("aria-expanded", String(open));
    if (open) showSel();
  });
  $("#scrim")?.addEventListener("click", () => closeDrawer());
  $("#mPrev")?.addEventListener("click", () => step(-1));
  $("#mNext")?.addEventListener("click", () => step(1));
  $("#mRand")?.addEventListener("click", () => {
    pickRandom();
    render();
  });
  $("#mOvl")?.addEventListener("click", () => {
    state.mobile.ovl = !mobileOverlay();
    render();
  });
  $("#mExpand")?.addEventListener("click", () => {
    state.mobile.exp = !state.mobile.exp;
    render();
  });
  const mSecond = $<HTMLSelectElement>("#mSecond");
  mSecond?.addEventListener("change", (event) => {
    state.mobile.second = (event.target as HTMLSelectElement).value;
    render();
  });
  $("#mLayout")?.addEventListener("click", () => {
    const sheet = doc.querySelector<HTMLDialogElement>("#msheet");
    sheet?.showModal?.();
  });
  doc.querySelectorAll<HTMLInputElement>('#msheet input[name="ml"]').forEach((radio) => {
    radio.addEventListener("change", () => {
      state.mobile.layout = radio.value as ViewerState["mobile"]["layout"];
      state.mobile.ovl = null;
      state.mobile.exp = false;
      render();
    });
  });
  const mBlend = $<HTMLSelectElement>("#mBlend");
  mBlend?.addEventListener("change", (event) => {
    state.mobile.blend = (event.target as HTMLSelectElement).value;
    render();
  });
  const mAlpha = $<HTMLInputElement>("#mAlpha");
  mAlpha?.addEventListener("input", (event) => {
    state.mobile.alpha = Number((event.target as HTMLInputElement).value);
    render();
  });

  function closeDrawer(): void {
    doc.body?.classList.remove("drawer");
    menu?.setAttribute("aria-expanded", "false");
  }

  doc.addEventListener("keydown", (event) => {
    const keyboard = event as KeyboardEvent;
    if (keyboard.ctrlKey || keyboard.metaKey || keyboard.altKey) return;
    const target = keyboard.target as HTMLInputElement | null;
    const tag = target?.tagName ?? "";
    if (tag === "SELECT" || tag === "TEXTAREA") return;
    if (
      tag === "INPUT" &&
      ["text", "search", "number", "range", "radio"].includes(target?.type ?? "")
    ) {
      return;
    }
    const shown = visibleCases();
    const at = shown.findIndex((c) => c.case === current()?.case);
    if (keyboard.key === "ArrowDown") {
      const next = shown[Math.min(at + 1, shown.length - 1)];
      if (next) sel = cases().findIndex((c) => c.case === next.case);
    } else if (keyboard.key === "ArrowUp") {
      const previous = shown[Math.max(at - 1, 0)];
      if (previous) sel = cases().findIndex((c) => c.case === previous.case);
    } else if (keyboard.key === "r") {
      pickRandom();
    } else if (keyboard.key === "s") {
      doc.body?.classList.toggle("noside");
      showSel();
    } else if (keyboard.key === "o") {
      state.ovl = !state.ovl;
    } else if (keyboard.key === "m") {
      state.shown += PAGE_STEP;
    } else if (keyboard.key === "t") {
      state.view = state.view === "scores" ? "viewer" : "scores";
    } else if (/^[1-9]$/.test(keyboard.key)) {
      // The kbd hints sit on the displayed lanes, so the key follows the
      // display order too.
      const engine = laneOrder[Number(keyboard.key) - 1];
      if (engine) state.on[engine.key] = !state.on[engine.key];
    } else {
      return;
    }
    keyboard.preventDefault();
    render();
  });

  doc.defaultView?.addEventListener("hashchange", () => {
    void applyHash().then((ok) => {
      if (ok) render();
    });
  });
  doc.defaultView?.addEventListener("resize", () => {
    setMobile();
    render();
  });

  // ---- the first paint

  setMobile();
  if (zoom) zoom.value = String(state.zoom);
  if (overlayBox) overlayBox.checked = state.ovl;
  if (underSelect) underSelect.value = state.ovlA;
  if (blendSelect) blendSelect.value = state.blend;
  if (alpha) alpha.value = String(state.alpha);
  if (filter) filter.value = state.filter;
  if (fxPages) fxPages.value = state.fx.pages;
  if (fxMax) fxMax.value = state.fx.max;
  if (fxDiffer) fxDiffer.checked = state.fx.differ;

  const linked = await applyHash();
  if (!linked) {
    await openGroup(groups[0].group);
    pickRandom();
  }
  if (!loaded) await openGroup(groups[0].group);
  render();
}
