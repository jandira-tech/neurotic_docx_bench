import type {
  Headline,
  HomeBar,
  HomeGroup,
  MethodPoint,
  Row,
  Scores,
  StateCell,
  StateRow,
  Table,
} from "./types.ts";

/**
 * Runtime validation of a `scores.json` document.
 *
 * Hand-written guards, no schema library: the package ships no runtime
 * dependency. Every failure is a `TypeError` naming the path of the bad
 * field (`tables[0].rows[0].median`), so a broken scores file says which
 * field to fix.
 */

function fail(path: string, expected: string): never {
  throw new TypeError(`scores: ${path} must be ${expected}`);
}

function obj(value: unknown, path: string, allowed?: readonly string[]): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    fail(path, "an object");
  }
  const record = value as Record<string, unknown>;
  if (allowed) {
    for (const key of Object.keys(record)) {
      if (!allowed.includes(key)) fail(`${path}.${key}`, "a known field");
    }
  }
  return record;
}

function str(value: unknown, path: string): string {
  if (typeof value !== "string") fail(path, "a string");
  return value;
}

function score(value: unknown, path: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) fail(path, "a finite number");
  if (value < 0 || value > 100) fail(path, "a number between 0 and 100");
  return value;
}

function count(value: unknown, path: string): number {
  if (
    typeof value !== "number" ||
    !Number.isFinite(value) ||
    !Number.isInteger(value) ||
    value < 0
  ) {
    fail(path, "a non-negative integer");
  }
  return value;
}

function bool(value: unknown, path: string): boolean {
  if (typeof value !== "boolean") fail(path, "a boolean");
  return value;
}

function list(value: unknown, path: string): unknown[] {
  if (!Array.isArray(value)) fail(path, "an array");
  return value;
}

/** An optional boolean: absent means "not ours". */
function optionalBool(value: unknown, path: string): boolean | undefined {
  if (value === undefined) return undefined;
  return bool(value, path);
}

/** Validate an absolute HTTP(S) URL before it can reach an href attribute. */
export function requireHttpUrl(value: unknown, path: string): string {
  const text = str(value, path);
  if (!/^https?:\/\//i.test(text)) fail(path, "an absolute http(s) URL");
  let url: URL;
  try {
    url = new URL(text);
  } catch {
    fail(path, "an absolute http(s) URL");
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    fail(path, "an absolute http(s) URL");
  }
  return text;
}

function parseRow(value: unknown, path: string): Row {
  const o = obj(value, path, [
    "rank",
    "tool",
    "pin",
    "median",
    "mean",
    "docs",
    "failed",
    "note",
    "ours",
  ]);
  const row: Row = {
    rank: str(o.rank, `${path}.rank`),
    tool: str(o.tool, `${path}.tool`),
    pin: str(o.pin, `${path}.pin`),
    median: score(o.median, `${path}.median`),
    mean: score(o.mean, `${path}.mean`),
    docs: count(o.docs, `${path}.docs`),
    failed: count(o.failed, `${path}.failed`),
    note: str(o.note, `${path}.note`),
  };
  const ours = optionalBool(o.ours, `${path}.ours`);
  if (ours !== undefined) row.ours = ours;
  return row;
}

function parseTable(value: unknown, path: string): Table {
  const o = obj(value, path, ["id", "title", "meta", "desc", "rows"]);
  return {
    id: str(o.id, `${path}.id`),
    title: str(o.title, `${path}.title`),
    meta: str(o.meta, `${path}.meta`),
    desc: str(o.desc, `${path}.desc`),
    rows: list(o.rows, `${path}.rows`).map((r, i) => parseRow(r, `${path}.rows[${i}]`)),
  };
}

function parseHeadline(value: unknown, path: string): Headline {
  const o = obj(value, path, ["label", "value", "vs", "sub"]);
  return {
    label: str(o.label, `${path}.label`),
    value: str(o.value, `${path}.value`),
    vs: str(o.vs, `${path}.vs`),
    sub: str(o.sub, `${path}.sub`),
  };
}

function parseStateRow(value: unknown, path: string): StateRow {
  const o = obj(value, path, ["tool", "median", "ours"]);
  const row: StateRow = {
    tool: str(o.tool, `${path}.tool`),
    median: score(o.median, `${path}.median`),
  };
  const ours = optionalBool(o.ours, `${path}.ours`);
  if (ours !== undefined) row.ours = ours;
  return row;
}

function parseStateCell(value: unknown, path: string): StateCell {
  const o = obj(value, path, ["name", "n", "rows", "table"]);
  const cell: StateCell = {
    name: str(o.name, `${path}.name`),
    n: str(o.n, `${path}.n`),
    rows: list(o.rows, `${path}.rows`).map((r, i) => parseStateRow(r, `${path}.rows[${i}]`)),
  };
  if (o.table !== undefined) {
    cell.table = o.table === null ? null : str(o.table, `${path}.table`);
  }
  return cell;
}

function parseHomeBar(value: unknown, path: string): HomeBar {
  const o = obj(value, path, ["name", "v", "ours"]);
  const bar: HomeBar = {
    name: str(o.name, `${path}.name`),
    v: score(o.v, `${path}.v`),
  };
  const ours = optionalBool(o.ours, `${path}.ours`);
  if (ours !== undefined) bar.ours = ours;
  return bar;
}

function parseHomeGroup(value: unknown, path: string): HomeGroup {
  const o = obj(value, path, ["title", "meta", "rows", "note"]);
  const group: HomeGroup = {
    title: str(o.title, `${path}.title`),
    meta: str(o.meta, `${path}.meta`),
    rows: list(o.rows, `${path}.rows`).map((r, i) => parseHomeBar(r, `${path}.rows[${i}]`)),
  };
  if (o.note !== undefined && o.note !== null) {
    group.note = str(o.note, `${path}.note`);
  } else if (o.note === null) {
    group.note = null;
  }
  return group;
}

function parseMethodPoint(value: unknown, path: string): MethodPoint {
  const o = obj(value, path, ["t", "d"]);
  return {
    t: str(o.t, `${path}.t`),
    d: str(o.d, `${path}.d`),
  };
}

function parseProvenance(value: unknown, path: string): Record<string, string[]> {
  const o = obj(value, path);
  const out: Record<string, string[]> = {};
  for (const [key, raw] of Object.entries(o)) {
    out[key] = list(raw, `${path}.${key}`).map((v, i) => str(v, `${path}.${key}[${i}]`));
  }
  return out;
}

/** Validate a parsed `scores.json` document and return it as `Scores`. */
export function parseScores(json: unknown): Scores {
  const o = obj(json, "scores", [
    "version",
    "generated",
    "repo",
    "viewer",
    "provenance",
    "tables",
    "headlines",
    "states",
    "home_groups",
    "method",
  ]);
  return {
    version: str(o.version, "version"),
    generated: str(o.generated, "generated"),
    repo: requireHttpUrl(o.repo, "repo"),
    viewer: requireHttpUrl(o.viewer, "viewer"),
    tables: list(o.tables, "tables").map((t, i) => parseTable(t, `tables[${i}]`)),
    headlines: list(o.headlines, "headlines").map((h, i) => parseHeadline(h, `headlines[${i}]`)),
    states: list(o.states, "states").map((s, i) => parseStateCell(s, `states[${i}]`)),
    home_groups: list(o.home_groups, "home_groups").map((g, i) =>
      parseHomeGroup(g, `home_groups[${i}]`),
    ),
    method: list(o.method, "method").map((m, i) => parseMethodPoint(m, `method[${i}]`)),
    provenance: parseProvenance(o.provenance, "provenance"),
  };
}
