#!/usr/bin/env node
/**
 * Read results/bench.jsonl (+ speed.jsonl) and update the ranking tables in
 * README.md between RANKING-START and RANKING-END.
 *
 * Fidelity: one competitive row per (vendor, benchmark, tool_version), then
 * **collapse** the three Jubarte families to **best + worst only** (by ITT
 * median) so the README stays readable while still showing the range of each
 * pin line.
 *
 * Ranking is intent-to-treat (ITT): every failed doc counts as a 0 score, so a
 * tool cannot climb the table by crashing on hard docs. Server-emitted itt_*
 * fields win when present; otherwise ITT is computed here from per-doc scores
 * plus failures, and approximated (marked `~`) for old lines without scores.
 *
 * Families:
 *   - jubarte-final          (vendor jubarte, native / non-lossless runs)
 *   - jubarte-final-lossless (vendor jubarte, run name / method lossless)
 *   - jubarte-rs             (vendor jubarte-rust)
 *
 * Other vendors: keep every version pin (docxodus 6.4 vs 7.0, etc.).
 *
 * Speed: listed as its own benchmark table (lower median ms = better). Rows
 * come from results/speed.jsonl + redline_speed_bench summaries via the same
 * pooling used by export-results-md (best by n, then lower median).
 */
import { existsSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { basename, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(import.meta.dirname, "..");
const BENCH_JSONL = resolve(ROOT, "results", "bench.jsonl");
const SPEED_JSONL = resolve(ROOT, "results", "speed.jsonl");
const REDLINE_SPEED_DIR = resolve(ROOT, "results", "redline_speed_bench");
const README = resolve(ROOT, "README.md");

/** Canonical fidelity benchmark names (order matters). */
const FIDELITY_BENCHMARKS = [
	"script_redlines",
	"accepted_changes",
	"roundtrip",
	"visual_rendering",
	"visual_redlines",
	"visual_accepted_changes",
] as const;

type FidelityBenchmark = (typeof FIDELITY_BENCHMARKS)[number];

const FIDELITY_TITLES: Record<FidelityBenchmark, string> = {
	script_redlines: "script_redlines — redline markup vs Word",
	accepted_changes: "accepted_changes — accept all changes, match final doc",
	roundtrip: "roundtrip — self-diff must not invent noise",
	visual_rendering: "visual_rendering — editor render of plain DOCX",
	visual_redlines: "visual_redlines — editor render of redline DOCX",
	visual_accepted_changes:
		"visual_accepted_changes — editor render of accepted DOCX",
};

const LEGACY_STAGE: Record<string, FidelityBenchmark> = {
	redline: "script_redlines",
	accepted: "accepted_changes",
	roundtrip: "roundtrip",
	"render-original": "visual_rendering",
	"render-redline": "visual_redlines",
	"render-accepted": "visual_accepted_changes",
};

/** Display family for Jubarte collapse (best+worst only). */
type JubarteFamily =
	| "jubarte-final"
	| "jubarte-final-lossless"
	| "jubarte-rs";

export interface FidelityRow {
	vendor: string;
	benchmark: FidelityBenchmark;
	tool_version: string | null;
	timestamp: string;
	n_docs: number;
	overall_mean: number;
	overall_median: number;
	exact_100: number;
	n_failures: number;
	/** Intent-to-treat: failed docs count as 0 instead of leaving the pool. */
	itt_median: number;
	itt_mean: number;
	itt_n: number;
	/** True when ITT was approximated from summary stats (no per-doc scores). */
	itt_approx: boolean;
	render: string;
	/** Run name from environment_config when available (e.g. jubarte-final-lossless). */
	run_name: string;
	family: JubarteFamily | null;
	/** Oracle-manifest fingerprint; null on lines predating the 403-pair corpus. */
	corpus_revision: string | null;
}

interface SpeedRow {
	tool: string;
	runtime: string;
	n: number;
	median: number;
	mean: number;
	p95: number | null;
	throughput_per_s: number | null;
	failures: number;
	fixture_count: number | null;
	pair_count: number | null;
	kind: string;
	unit: string;
	run_ts: string;
}

function isFidelityBenchmark(value: string): value is FidelityBenchmark {
	return (FIDELITY_BENCHMARKS as readonly string[]).includes(value);
}

function jubarteFamily(
	vendor: string,
	runName: string,
	version: string,
	generate: string,
): JubarteFamily | null {
	const v = vendor.toLowerCase();
	const blob = `${runName} ${version} ${generate}`.toLowerCase();
	if (v === "jubarte-rust" || v === "jubarte-rs") return "jubarte-rs";
	if (v === "jubarte") {
		// Lossless runs are named jubarte-final-lossless or method=jubarte-lossless.
		if (
			blob.includes("lossless") ||
			blob.includes("method=jubarte-lossless") ||
			blob.includes("method=jubarte_lossless")
		) {
			return "jubarte-final-lossless";
		}
		return "jubarte-final";
	}
	return null;
}

function runMetaFromEnv(data: Record<string, unknown>): {
	run_name: string;
	generate: string;
	render: string;
} {
	const env = (data.environment_config ?? {}) as Record<string, unknown>;
	const runs = Array.isArray(env.runs) ? env.runs : [];
	const first =
		runs.length > 0 && typeof runs[0] === "object" && runs[0] !== null
			? (runs[0] as Record<string, unknown>)
			: {};
	return {
		run_name: String(first.name ?? data.tool ?? ""),
		generate: String(first.generate ?? ""),
		render: String(first.render ?? ""),
	};
}

/** Lexicographic compare of rank tuples (higher is better). */
function cmpRank(
	a: readonly (number | string)[],
	b: readonly (number | string)[],
): number {
	const n = Math.max(a.length, b.length);
	for (let i = 0; i < n; i++) {
		const x = a[i] ?? 0;
		const y = b[i] ?? 0;
		if (x === y) continue;
		if (typeof x === "number" && typeof y === "number") return x - y;
		return String(x).localeCompare(String(y));
	}
	return 0;
}

export function median(values: readonly number[]): number {
	if (values.length === 0) return 0;
	const sorted = [...values].sort((a, b) => a - b);
	const mid = Math.floor(sorted.length / 2);
	return sorted.length % 2 === 1
		? sorted[mid]!
		: (sorted[mid - 1]! + sorted[mid]!) / 2;
}

export function mean(values: readonly number[]): number {
	if (values.length === 0) return 0;
	return values.reduce((acc, v) => acc + v, 0) / values.length;
}

export interface IttStats {
	itt_median: number;
	itt_mean: number;
	itt_n: number;
	itt_approx: boolean;
}

/**
 * Intent-to-treat stats for one bench line. Server-emitted itt_* fields are
 * authoritative when present (keyed on itt_median). Otherwise merge per-doc
 * scores with one 0 per unique failed doc — a doc that is both scored and
 * listed as a failure keeps its score. Lines without per-doc scores are
 * approximated as overall_median × n_docs plus a 0 per failure and flagged
 * itt_approx so the table can mark them `~`.
 */
export function computeIttStats(
	data: Record<string, unknown>,
	completed: { n_docs: number; overall_median: number; n_failures: number },
): IttStats {
	if (data.itt_median != null) {
		return {
			itt_median: num(data.itt_median),
			itt_mean: num(data.itt_mean),
			itt_n: num(data.itt_n_docs),
			itt_approx: false,
		};
	}

	const scores =
		data.scores &&
		typeof data.scores === "object" &&
		!Array.isArray(data.scores)
			? (data.scores as Record<string, unknown>)
			: null;
	const scoredDocs = scores ? Object.keys(scores) : [];

	if (scores && scoredDocs.length > 0) {
		const values = scoredDocs.map((doc) => num(scores[doc]));
		const scoredSet = new Set(scoredDocs);
		const failedDocs = new Set<string>();
		const failures = Array.isArray(data.failures) ? data.failures : [];
		for (const f of failures) {
			if (f && typeof f === "object" && "doc" in f) {
				failedDocs.add(String((f as Record<string, unknown>).doc));
			}
		}
		for (const doc of failedDocs) {
			if (!scoredSet.has(doc)) values.push(0);
		}
		return {
			itt_median: median(values),
			itt_mean: mean(values),
			itt_n: values.length,
			itt_approx: false,
		};
	}

	const values: number[] = [];
	for (let i = 0; i < completed.n_docs; i++) {
		values.push(completed.overall_median);
	}
	for (let i = 0; i < completed.n_failures; i++) values.push(0);
	return {
		itt_median: median(values),
		itt_mean: mean(values),
		itt_n: values.length,
		itt_approx: true,
	};
}

export function readFidelityRows(path: string): FidelityRow[] {
	const text = readFileSync(path, "utf8");
	const out: FidelityRow[] = [];
	for (const line of text.split(/\r?\n/)) {
		if (!line.trim()) continue;
		let data: Record<string, unknown>;
		try {
			data = JSON.parse(line) as Record<string, unknown>;
		} catch {
			continue;
		}

		const vendor = String(data.vendor ?? data.tool ?? "");
		let benchmarkRaw = String(data.benchmark ?? "");
		if (!benchmarkRaw && typeof data.stage === "string") {
			benchmarkRaw = LEGACY_STAGE[data.stage] ?? data.stage;
		}
		if (!benchmarkRaw) benchmarkRaw = "script_redlines";
		if (!vendor || !isFidelityBenchmark(benchmarkRaw)) continue;

		const agg = (data.aggregate ?? {}) as Record<string, unknown>;
		const n_docs = num(data.n_docs ?? agg.n_docs);
		const overall_mean = num(data.overall_mean ?? agg.overall_mean);
		const overall_median = num(data.overall_median ?? agg.overall_median);
		const exact_100 = num(data.exact_100 ?? agg.exact_100);
		const failures = data.failures;
		const n_failures = Array.isArray(failures)
			? failures.length
			: num(data.n_failures);

		if (vendor === "docxodus" && n_docs <= 100) continue;
		if (vendor === "prebaked") continue;

		const meta = runMetaFromEnv(data);
		const tool_version =
			data.tool_version == null ? null : String(data.tool_version);
		const family = jubarteFamily(
			vendor,
			meta.run_name,
			tool_version ?? "",
			meta.generate,
		);
		const itt = computeIttStats(data, { n_docs, overall_median, n_failures });

		out.push({
			vendor,
			benchmark: benchmarkRaw,
			tool_version,
			timestamp: String(data.timestamp ?? data.run_ts ?? ""),
			n_docs,
			overall_mean,
			overall_median,
			exact_100,
			n_failures,
			itt_median: itt.itt_median,
			itt_mean: itt.itt_mean,
			itt_n: itt.itt_n,
			itt_approx: itt.itt_approx,
			render: meta.render,
			run_name: meta.run_name,
			family,
			corpus_revision:
				data.corpus_revision == null ? null : String(data.corpus_revision),
		});
	}
	return out;
}

function num(value: unknown): number {
	if (typeof value === "number" && Number.isFinite(value)) return value;
	if (typeof value === "string" && value.trim() !== "" && !Number.isNaN(+value)) {
		return +value;
	}
	return 0;
}

function rankFidelity(row: FidelityRow): [number, number, number, string] {
	const isVisual = row.benchmark.startsWith("visual");
	const renderFit = isVisual
		? row.render === "playwright"
			? 1
			: 0
		: row.render === "playwright"
			? 0
			: 1;
	// Winner selection keys on itt_median so the "best pin" shown IS the ITT-best pin
	// (the table sorts by ITT median — selecting by raw mean here would let a
	// crashy-but-high-completed-mean line represent the vendor).
	return [renderFit, row.n_docs, row.itt_median, row.timestamp];
}

/**
 * One line per (family-or-vendor, benchmark, tool_version).
 * Family is included so jubarte-final-native and jubarte-final-lossless with the
 * same content-hash pin do not overwrite each other.
 */
export function bestPerVendorBenchmarkVersion(
	rows: FidelityRow[],
): Map<string, FidelityRow> {
	const best = new Map<string, FidelityRow>();
	for (const row of rows) {
		const version = row.tool_version?.trim() || "—";
		const fam = row.family ?? row.vendor;
		const key = `${fam}__${row.benchmark}__${version}`;
		const cur = best.get(key);
		if (!cur || cmpRank(rankFidelity(row), rankFidelity(cur)) > 0) {
			best.set(key, row);
		}
	}
	return best;
}

/**
 * For jubarte-final / jubarte-final-lossless / jubarte-rs: keep only the best
 * and worst pin by ITT median (tie-break ITT mean, n_docs). Other vendors:
 * keep all.
 */
export function collapseJubarteFamilies(
	best: Map<string, FidelityRow>,
	benchmark: FidelityBenchmark,
): FidelityRow[] {
	const all = Array.from(best.values()).filter((r) => r.benchmark === benchmark);
	const families: JubarteFamily[] = [
		"jubarte-final",
		"jubarte-final-lossless",
		"jubarte-rs",
	];
	const kept: FidelityRow[] = [];
	const nonJubarte: FidelityRow[] = [];

	for (const r of all) {
		if (r.family) continue;
		nonJubarte.push(r);
	}

	for (const fam of families) {
		const members = all.filter((r) => r.family === fam);
		if (members.length === 0) continue;
		if (members.length === 1) {
			kept.push(members[0]!);
			continue;
		}
		const byMedian = [...members].sort((a, b) => {
			if (b.itt_median !== a.itt_median) {
				return b.itt_median - a.itt_median;
			}
			if (b.itt_mean !== a.itt_mean) {
				return b.itt_mean - a.itt_mean;
			}
			return b.n_docs - a.n_docs;
		});
		const bestR = byMedian[0]!;
		const worstR = byMedian[byMedian.length - 1]!;
		if (bestR === worstR) {
			kept.push(bestR);
		} else {
			// Label range in version column for clarity (impartial: both ends).
			kept.push({
				...bestR,
				tool_version: `${bestR.tool_version ?? "—"} (best)`,
			});
			kept.push({
				...worstR,
				tool_version: `${worstR.tool_version ?? "—"} (worst)`,
			});
		}
	}

	return [...kept, ...nonJubarte].sort((a, b) => {
		if (b.itt_median !== a.itt_median) {
			return b.itt_median - a.itt_median;
		}
		if (b.itt_mean !== a.itt_mean) {
			return b.itt_mean - a.itt_mean;
		}
		const v = a.vendor.localeCompare(b.vendor);
		if (v !== 0) return v;
		return (a.tool_version ?? "").localeCompare(b.tool_version ?? "");
	});
}

function fmt(n: number, digits = 2): string {
	return n.toFixed(digits);
}

const FIDELITY_HEADER =
	"| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |\n" +
	"| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |";

function fidelityBody(rows: FidelityRow[]): string {
	return rows
		.map((r, i) => {
			const displayVendor =
				r.family === "jubarte-final-lossless"
					? "jubarte (lossless)"
					: r.family === "jubarte-final"
						? "jubarte (final)"
						: r.family === "jubarte-rs"
							? "jubarte-rust"
							: r.vendor;
			const approx = r.itt_approx ? "~" : "";
			return (
				`| ${i + 1} | ${displayVendor} | ${r.tool_version ?? "—"} | ` +
				`${r.n_docs} | ${r.itt_n} | ` +
				`${fmt(r.itt_mean)}${approx} | ${fmt(r.itt_median)}${approx} | ` +
				`${fmt(r.overall_mean)} | ${fmt(r.overall_median)} | ` +
				`${r.exact_100} | ${r.n_failures} |`
			);
		})
		.join("\n");
}

export function buildFidelityTable(
	best: Map<string, FidelityRow>,
	benchmark: FidelityBenchmark,
): string {
	const title = FIDELITY_TITLES[benchmark];
	// Corpus regimes are not comparable: lines stamped with corpus_revision ran
	// on the current (403-pair) corpus; older lines ran on smaller corpora and
	// their means/medians must not rank against current runs.
	const currentBest = new Map(
		[...best].filter(([, r]) => r.corpus_revision != null),
	);
	const legacyBest = new Map(
		[...best].filter(([, r]) => r.corpus_revision == null),
	);
	const currentRows = collapseJubarteFamilies(currentBest, benchmark);
	const legacyRows = collapseJubarteFamilies(legacyBest, benchmark);
	if (currentRows.length === 0 && legacyRows.length === 0) {
		return `### ${title}\n\n_No data yet._`;
	}

	const header = FIDELITY_HEADER;
	// Rows with different ITT Docs are different measurements, not noisier ones
	// (plan Chapter 6, D1). The counts were always printed, but only as a column,
	// and a reader ranking by score does not audit it — jubarte-wasm once sat at
	// #1 on n=195 above jubarte-rust on n=763, i.e. ahead on an easier subset.
	// State it in prose instead of trusting the column to be noticed.
	const coverageNote = (rows: FidelityRow[]): string => {
		const counts = [...new Set(rows.map((r) => r.itt_n))].sort((a, b) => b - a);
		if (counts.length < 2) return "";
		return (
			`\n\n> ⚠️ **Rows below cover different document counts (${counts.join(", ")}) — ` +
			`they are not the same measurement.** A tool scored on fewer documents ran a ` +
			`different, usually easier, subset; its rank is not comparable with a row ` +
			`covering more. Compare only rows whose \`ITT Docs\` match.`
		);
	};
	let body: string;
	if (currentRows.length > 0 && legacyRows.length > 0) {
		body =
			`**Current corpus** (lines stamped with \`corpus_revision\`)` +
			`${coverageNote(currentRows)}\n\n${header}\n${fidelityBody(currentRows)}\n\n` +
			`**Legacy corpus** (older, smaller corpora — not comparable with the ` +
			`rows above; kept for history until each tool re-runs):` +
			`${coverageNote(legacyRows)}\n\n` +
			`${header}\n${fidelityBody(legacyRows)}`;
	} else {
		const only = currentRows.length > 0 ? currentRows : legacyRows;
		body = `${coverageNote(only)}\n\n${header}\n${fidelityBody(only)}`.trimStart();
	}

	return (
		`### ${title}\n\n` +
		`Sorted by **ITT median** (intent-to-treat: every failed doc scores 0, so ` +
		`crashing on hard docs is penalized, not rewarded; 0–100, higher is closer ` +
		`to the oracle). Mean/Median cover completed docs only. \`~\` marks ITT ` +
		`stats approximated from summary numbers (older runs without per-doc ` +
		`scores). Jubarte families (**final**, **final-lossless**, **rust**) show ` +
		`only the **best** and **worst** version pin for this benchmark; other ` +
		`vendors list each pin.\n\n` +
		`${body}`
	);
}

// ── Speed (as a ranking benchmark) ───────────────────────────────────────────

function speedRank(row: SpeedRow): [number, number, string] {
	// Prefer larger n, then lower median (faster), then newer.
	return [row.n, -row.median, row.run_ts];
}

function betterSpeed(a: SpeedRow, b: SpeedRow): boolean {
	return cmpRank(speedRank(a), speedRank(b)) > 0;
}

function normalizeSpeed(data: Record<string, unknown>): SpeedRow | null {
	let kind = String(data.kind ?? "speed");
	if (kind === "redline_speed_bench") kind = "speed_redlines";
	const unit = String(data.unit ?? "ms_per_redline");
	if (unit !== "ms_per_redline") return null;
	if (kind !== "speed" && kind !== "speed_redlines") return null;
	const tool = String(data.tool ?? data.engine ?? "");
	if (!tool) return null;
	if (data.error && data.median == null) return null;
	const median = num(data.median);
	const mean = num(data.mean);
	const n = num(data.n);
	if (!n || (median === 0 && mean === 0 && data.median == null)) return null;
	if (kind === "speed_redlines" && n < 10) return null;
	return {
		tool,
		runtime: String(data.runtime ?? "—"),
		n,
		median,
		mean,
		p95: data.p95 == null ? null : num(data.p95),
		throughput_per_s:
			data.throughput_per_s == null ? null : num(data.throughput_per_s),
		failures: num(data.failures),
		fixture_count:
			data.fixture_count == null && data.fixture_target == null
				? null
				: num(data.fixture_count ?? data.fixture_target),
		pair_count: data.pair_count == null ? null : num(data.pair_count),
		kind,
		unit,
		run_ts: String(data.run_ts ?? data.timestamp ?? ""),
	};
}

function readSpeedRows(): SpeedRow[] {
	const best = new Map<string, SpeedRow>();
	const ingest = (row: SpeedRow) => {
		const key = `${row.kind}__${row.tool}`;
		const cur = best.get(key);
		if (!cur || betterSpeed(row, cur)) best.set(key, row);
	};

	if (existsSync(SPEED_JSONL)) {
		for (const line of readFileSync(SPEED_JSONL, "utf8").split(/\r?\n/)) {
			if (!line.trim()) continue;
			try {
				const row = normalizeSpeed(JSON.parse(line) as Record<string, unknown>);
				if (row) ingest(row);
			} catch {
				/* skip */
			}
		}
	}

	if (existsSync(REDLINE_SPEED_DIR)) {
		const walk = (dir: string) => {
			for (const ent of readdirSync(dir, { withFileTypes: true })) {
				const p = join(dir, ent.name);
				if (ent.isDirectory()) walk(p);
				else if (ent.name === "summary.json") {
					try {
						const payload = JSON.parse(readFileSync(p, "utf8")) as {
							rows?: unknown[];
							pairs?: number;
							fixtures?: number;
						};
						for (const raw of payload.rows ?? []) {
							if (!raw || typeof raw !== "object") continue;
							const data = { ...(raw as Record<string, unknown>) };
							if (!data.kind) data.kind = "speed_redlines";
							const row = normalizeSpeed(data);
							if (!row) continue;
							if (row.pair_count == null && payload.pairs != null) {
								row.pair_count = payload.pairs;
							}
							if (row.fixture_count == null && payload.fixtures != null) {
								row.fixture_count = payload.fixtures;
							}
							ingest(row);
						}
					} catch {
						/* skip */
					}
				}
			}
		};
		walk(REDLINE_SPEED_DIR);
	}

	return Array.from(best.values()).sort((a, b) => {
		// Large-N first, then by median ascending (faster first).
		if (a.kind !== b.kind) {
			return a.kind === "speed_redlines" ? -1 : 1;
		}
		return a.median - b.median;
	});
}

function buildSpeedTable(rows: SpeedRow[]): string {
	const title = "speed_redlines — generation time (ms per redline)";
	if (rows.length === 0) {
		return (
			`### ${title}\n\n` +
			`_No speed data yet. Run \`scripts/redline_speed_bench.ts\` or ` +
			`\`scripts/speed-bench.ts\` and re-export._`
		);
	}

	const large = rows.filter((r) => r.kind === "speed_redlines");
	const micro = rows.filter((r) => r.kind === "speed");

	const sections: string[] = [
		`### ${title}\n`,
		`Sorted by median **ms per redline** (lower is faster). ` +
			`Large-N warm rows (\`*-inproc\`) measure algorithm cost in a long-lived process; ` +
			`CLI rows include process spawn. Prefer warm rows for engine comparisons. ` +
			`Methodology: [Speed methodology](#speed-methodology). ` +
			`Raw log: \`results/speed.jsonl\`.\n`,
	];

	if (large.length) {
		sections.push(
			"**Large-N** (`kind: speed_redlines` — often 1000 fixtures → 5000 pairs):\n",
		);
		sections.push(
			"| Rank | Tool | Runtime | Fixtures | Pairs | Median ms | Mean ms | p95 | /s | n | Failures |\n" +
				"| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
		);
		large.forEach((r, i) => {
			sections.push(
				`| ${i + 1} | ${r.tool} | ${r.runtime || "—"} | ` +
					`${r.fixture_count ?? "—"} | ${r.pair_count ?? "—"} | ` +
					`${fmt(r.median, 2)} | ${fmt(r.mean, 2)} | ` +
					`${r.p95 == null ? "—" : fmt(r.p95, 2)} | ` +
					`${r.throughput_per_s == null ? "—" : fmt(r.throughput_per_s, 1)} | ` +
					`${r.n} | ${r.failures} |`,
			);
		});
		sections.push("");
	}

	if (micro.length) {
		sections.push(
			"**Microbench** (`kind: speed` — typically ~30–40 pairs × 3 reps):\n",
		);
		sections.push(
			"| Rank | Tool | Runtime | Median ms | Mean ms | p95 | /s | n | Failures |\n" +
				"| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
		);
		micro.forEach((r, i) => {
			sections.push(
				`| ${i + 1} | ${r.tool} | ${r.runtime || "—"} | ` +
					`${fmt(r.median, 2)} | ${fmt(r.mean, 2)} | ` +
					`${r.p95 == null ? "—" : fmt(r.p95, 2)} | ` +
					`${r.throughput_per_s == null ? "—" : fmt(r.throughput_per_s, 1)} | ` +
					`${r.n} | ${r.failures} |`,
			);
		});
		sections.push("");
	}

	return sections.join("\n").trimEnd();
}

function updateReadme(tables: string[]): void {
	const readme = readFileSync(README, "utf8");
	const startMarker = "<!-- RANKING-START -->";
	const endMarker = "<!-- RANKING-END -->";
	const start = readme.indexOf(startMarker);
	const end = readme.indexOf(endMarker);
	if (start === -1 || end === -1 || end <= start) {
		throw new Error(
			`README.md must contain both ${startMarker} and ${endMarker} markers in the correct order.`,
		);
	}
	const before = readme.slice(0, start + startMarker.length);
	const after = readme.slice(end);
	const body = `\n${tables.join("\n\n")}\n`;
	writeFileSync(README, `${before}${body}${after}`, "utf8");
}

function main() {
	const rows = readFidelityRows(BENCH_JSONL);
	if (rows.length === 0) {
		console.error("No usable bench entries found in", BENCH_JSONL);
		process.exit(1);
	}
	const best = bestPerVendorBenchmarkVersion(rows);
	const fidelityTables = FIDELITY_BENCHMARKS.map((b) =>
		buildFidelityTable(best, b),
	);
	const speedTable = buildSpeedTable(readSpeedRows());
	// Speed listed as a peer benchmark after fidelity tables.
	updateReadme([...fidelityTables, speedTable]);

	console.log(
		`Updated README.md: ${FIDELITY_BENCHMARKS.length} fidelity tables (Jubarte best/worst) + speed.`,
	);
}

// Same guard as redline_scoreboard.ts: run only when executed directly, so the
// test suite can import the helpers without rewriting README.md.
function isMain(): boolean {
	const argv1 = process.argv[1];
	if (!argv1) return false;
	// Normalize both sides so Windows drive letters / relative invocations match.
	const scriptPath = resolve(fileURLToPath(import.meta.url));
	const invokedPath = resolve(argv1);
	if (invokedPath === scriptPath) return true;
	return basename(invokedPath) === basename(scriptPath);
}

if (isMain()) {
	main();
}
