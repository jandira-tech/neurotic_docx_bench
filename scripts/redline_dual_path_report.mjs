/**
 * Aggregate redline_dual_path_bench output into a speed + quality report.
 *
 * Usage:
 *   node scripts/redline_dual_path_report.mjs <runDir> [--update-docs]
 *
 * `--update-docs` rewrites the generated sections of RESULTS.md,
 * docs/RESULTS.md and docs/SPEED.md between their markers (idempotent — rerun
 * after a fresh sweep and only the numbers move). Provenance (jubarte-first
 * pin, corpus vintage, bench commit, Node version) is stamped into each
 * section, matching this repo's A-4 hard-pin rule: a table without a pin
 * cannot identify the build it measured.
 */
import { readFileSync, readdirSync, writeFileSync, existsSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { execFileSync } from "node:child_process";

const dir = process.argv[2];
if (!dir) throw new Error("usage: redline_dual_path_report.mjs <runDir> [--update-docs]");
const UPDATE_DOCS = process.argv.includes("--update-docs");
const ROOT = resolve(dirname(new URL(import.meta.url).pathname), "..");
const JF = process.env.JUBARTE_FIRST_DIR || resolve(ROOT, "../jubarte-first");

const git = (cwd, ...args) => {
  try {
    return execFileSync("git", ["-C", cwd, ...args], { encoding: "utf8" }).trim();
  } catch {
    return "unknown";
  }
};
const PROV = {
  jubarteFirst: git(JF, "rev-parse", "--short=7", "HEAD"),
  bench: git(ROOT, "rev-parse", "--short=7", "HEAD"),
  corpus: git(ROOT, "log", "-1", "--format=%h", "--", "corpus/word_based"),
  node: process.version,
};

const load = (f) =>
  readFileSync(join(dir, f), "utf8")
    .trim()
    .split("\n")
    .filter(Boolean)
    .map((l) => JSON.parse(l));

const files = readdirSync(dir).filter((f) => f.endsWith(".jsonl"));
const byEngine = new Map();
for (const f of files) {
  const rows = load(f);
  if (rows.length) byEngine.set(rows[0].engine, rows);
}

const pct = (sorted, p) => sorted[Math.min(sorted.length - 1, Math.floor((p / 100) * sorted.length))];
const num = (n, d = 1) => (n == null || Number.isNaN(n) ? "—" : n.toFixed(d));

const L = [];
L.push("# Redline dual-path bench — jubarte-first lossless vs via-AST\n");
L.push(`Run dir: \`${dir}\`  ·  Node ${process.version}\n`);

// ── speed ──────────────────────────────────────────────────────────────────
L.push("## Speed (compare() only — accept/reject and judging excluded)\n");
const speedTable = [
  "| engine | pairs timed | mean ms | median | p90 | p99 | max | total s | pairs/s | MB/s in |",
  "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
];
L.push(...speedTable);
const speed = new Map();
for (const [engine, rows] of byEngine) {
  const timed = rows.filter((r) => typeof r.compareMs === "number");
  const ms = timed.map((r) => r.compareMs).sort((a, b) => a - b);
  const total = ms.reduce((a, b) => a + b, 0);
  const bytes = timed.reduce((a, r) => a + (r.bytesIn || 0), 0);
  speed.set(engine, { n: ms.length, mean: total / ms.length, total });
  const row =
    `| ${engine} | ${ms.length} | ${num(total / ms.length)} | ${num(pct(ms, 50))} | ${num(pct(ms, 90))} | ` +
    `${num(pct(ms, 99))} | ${num(ms[ms.length - 1])} | ${num(total / 1000)} | ` +
    `${num(ms.length / (total / 1000), 2)} | ${num(bytes / 1e6 / (total / 1000), 2)} |`;
  speedTable.push(row);
  L.push(row);
}
const [e1, e2] = [...speed.keys()];
if (e1 && e2) {
  const r = speed.get(e1).mean / speed.get(e2).mean;
  L.push(
    `\n**${r > 1 ? e2 : e1} is ${num(r > 1 ? r : 1 / r, 2)}× faster on mean compare time** ` +
      `(${num(speed.get(e1).mean)}ms vs ${num(speed.get(e2).mean)}ms).\n`,
  );
}

// ── quality ────────────────────────────────────────────────────────────────
L.push("## Quality — acceptance gate + well-formedness\n");
L.push("`ok` requires ALL of: every XML part well-formed, text(accept(redline)) == text(next), text(reject(redline)) == text(base).\n");
const qualityTable = [
  "| engine | pairs | ok | ok % | well-formed | accept ok | reject ok | compare threw |",
  "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
];
L.push(...qualityTable);
for (const [engine, rows] of byEngine) {
  const n = rows.length;
  const c = (f) => rows.filter(f).length;
  const row =
    `| ${engine} | ${n} | ${c((r) => r.ok)} | ${num((100 * c((r) => r.ok)) / n)}% | ` +
    `${c((r) => r.wellFormed)} | ${c((r) => r.acceptOk)} | ${c((r) => r.rejectOk)} | ${c((r) => r.compareError)} |`;
  qualityTable.push(row);
  L.push(row);
}
L.push("");

// ── failure classes ────────────────────────────────────────────────────────
L.push("## Failure classes\n");
for (const [engine, rows] of byEngine) {
  const fails = rows.filter((r) => !r.ok);
  L.push(`### ${engine} — ${fails.length} failing pair(s)\n`);
  const classify = (r) => {
    if (r.compareError) return `compare threw: ${r.compareError.split("\n")[0].slice(0, 90)}`;
    if (!r.wellFormed) return `malformed XML: ${(r.malformed?.[0] || "").slice(0, 90)}`;
    if (!r.acceptOk && !r.rejectOk) return "accept AND reject diverge";
    if (!r.acceptOk) return r.acceptError ? `accept threw: ${r.acceptError.slice(0, 80)}` : "accept text != next";
    return r.rejectError ? `reject threw: ${r.rejectError.slice(0, 80)}` : "reject text != base";
  };
  const groups = new Map();
  for (const r of fails) {
    const k = classify(r);
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(r.pair);
  }
  const sorted = [...groups].sort((a, b) => b[1].length - a[1].length);
  L.push("| count | class | example pairs |");
  L.push("| ---: | --- | --- |");
  for (const [k, pairs] of sorted) {
    L.push(`| ${pairs.length} | ${k.replace(/\|/g, "\\|")} | ${pairs.slice(0, 2).map((p) => `\`${p.slice(0, 40)}\``).join(", ")} |`);
  }
  L.push("");
}

// ── head to head ───────────────────────────────────────────────────────────
if (byEngine.size === 2) {
  const [a, b] = [...byEngine.keys()];
  const ma = new Map(byEngine.get(a).map((r) => [r.pair, r]));
  const mb = new Map(byEngine.get(b).map((r) => [r.pair, r]));
  const onlyA = [], onlyB = [], bothFail = [];
  for (const [pair, ra] of ma) {
    const rb = mb.get(pair);
    if (!rb) continue;
    if (ra.ok && !rb.ok) onlyA.push(pair);
    else if (!ra.ok && rb.ok) onlyB.push(pair);
    else if (!ra.ok && !rb.ok) bothFail.push(pair);
  }
  L.push("## Head-to-head\n");
  L.push(`- passes **only** in \`${a}\`: **${onlyA.length}**`);
  L.push(`- passes **only** in \`${b}\`: **${onlyB.length}**`);
  L.push(`- fails in **both** (shared defect or judge strictness): **${bothFail.length}**\n`);
  const show = (label, arr) => {
    if (!arr.length) return;
    L.push(`<details><summary>${label} (${arr.length})</summary>\n`);
    for (const p of arr.slice(0, 40)) L.push(`- \`${p}\``);
    L.push("\n</details>\n");
  };
  show(`only ${a} passes`, onlyA);
  show(`only ${b} passes`, onlyB);
  show("both fail", bothFail);
}

const md = L.join("\n");
writeFileSync(join(dir, "REPORT.md"), md);
console.log(md);

// ─── generated doc sections ────────────────────────────────────────────────

/** Replace the block between BEGIN/END markers; append the block if absent. */
const spliceSection = (path, marker, body) => {
  if (!existsSync(path)) return `skip (absent): ${path}`;
  const BEGIN = `<!-- ${marker}:BEGIN -->`;
  const END = `<!-- ${marker}:END -->`;
  const block = `${BEGIN}\n${body}\n${END}`;
  const current = readFileSync(path, "utf8");
  let next;
  if (current.includes(BEGIN) && current.includes(END)) {
    next =
      current.slice(0, current.indexOf(BEGIN)) +
      block +
      current.slice(current.indexOf(END) + END.length);
  } else {
    next = `${current.trimEnd()}\n\n${block}\n`;
  }
  if (next === current) return `unchanged: ${path}`;
  writeFileSync(path, next);
  return `updated: ${path}`;
};

if (UPDATE_DOCS) {
  const stamp =
    `_Generated by \`scripts/redline_dual_path_report.mjs\` from \`${dir}\`. ` +
    `jubarte-first \`${PROV.jubarteFirst}\` · corpus \`${PROV.corpus}\` · ` +
    `bench \`${PROV.bench}\` · Node ${PROV.node}._`;

  const speedBody = [
    "## jubarte-first dual-path redline speed (lossless vs via-AST)",
    "",
    stamp,
    "",
    "Both TypeScript paths in `jubarte-first` over the same base→next pairs from",
    "`centralized_mapping.csv` + `centralized_mapping_randomized.csv`. Timing covers the",
    "`compare()` call only — accept/reject and judging are excluded, so this is the redline",
    "engine and not the harness. Single process, sequential, no warmup.",
    "",
    ...speedTable,
  ].join("\n");

  const qualityBody = [
    "## jubarte-first dual-path redline quality (lossless vs via-AST)",
    "",
    stamp,
    "",
    "Acceptance gate over the same pairs, judged identically for both engines with the",
    "package-level accept/reject: a pair is `ok` only when every XML part of the redline is",
    "well-formed AND `text(accept(redline)) == text(next)` AND `text(reject(redline)) == text(base)`.",
    "Malformed XML is counted as a hard fail because Word reports it as unreadable content.",
    "",
    ...qualityTable,
  ].join("\n");

  console.log("\n─── doc updates ───");
  for (const p of ["RESULTS.md", "docs/RESULTS.md"]) {
    console.log(spliceSection(join(ROOT, p), "DUAL_PATH_QUALITY", qualityBody));
  }
  console.log(spliceSection(join(ROOT, "docs/SPEED.md"), "DUAL_PATH_SPEED", speedBody));

  // `runs/` is gitignored, so the failure-class + head-to-head detail would not
  // survive the run dir. Keep the full report as a committed doc.
  const full = `${md.replace(/^# .*$/m, "# Redline dual-path bench — jubarte-first lossless vs via-AST\n\n" + stamp)}\n`;
  const fullPath = join(ROOT, "docs/DUAL_PATH_REDLINE.md");
  const prev = existsSync(fullPath) ? readFileSync(fullPath, "utf8") : null;
  if (prev !== full) {
    writeFileSync(fullPath, full);
    console.log(`updated: ${fullPath}`);
  } else {
    console.log(`unchanged: ${fullPath}`);
  }
}
