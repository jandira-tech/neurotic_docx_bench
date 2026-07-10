#!/usr/bin/env node
/**
 * Read results/bench.jsonl and update the ranking tables in README.md between
 * RANKING-START and RANKING-END.
 *
 * One row per (vendor, benchmark, tool_version) so pins (e.g. docxodus 6.4 vs
 * 7.0) appear side-by-side. Schema v4 (current): vendor + benchmark + top-level
 * aggregates. Schema v2/v3 (legacy): tool + stage, still accepted for older
 * trend lines.
 */
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const ROOT = resolve(import.meta.dirname, "..");
const BENCH_JSONL = resolve(ROOT, "results", "bench.jsonl");
const README = resolve(ROOT, "README.md");

/** Canonical benchmark names written into the README tables (order matters). */
const BENCHMARKS = [
	"script_redlines",
	"accepted_changes",
	"roundtrip",
	"visual_rendering",
	"visual_redlines",
	"visual_accepted_changes",
] as const;

type Benchmark = (typeof BENCHMARKS)[number];

const BENCHMARK_TITLES: Record<Benchmark, string> = {
	script_redlines: "script_redlines — redline markup vs Word",
	accepted_changes: "accepted_changes — accept all changes, match final doc",
	roundtrip: "roundtrip — self-diff must not invent noise",
	visual_rendering: "visual_rendering — editor render of plain DOCX",
	visual_redlines: "visual_redlines — editor render of redline DOCX",
	visual_accepted_changes:
		"visual_accepted_changes — editor render of accepted DOCX",
};

/** Map legacy stage names → canonical benchmark. */
const LEGACY_STAGE: Record<string, Benchmark> = {
	redline: "script_redlines",
	accepted: "accepted_changes",
	roundtrip: "roundtrip",
	"render-original": "visual_rendering",
	"render-redline": "visual_redlines",
	"render-accepted": "visual_accepted_changes",
};

interface Row {
	vendor: string;
	benchmark: Benchmark;
	tool_version: string | null;
	timestamp: string;
	n_docs: number;
	overall_mean: number;
	overall_median: number;
	exact_100: number;
	n_failures: number;
	/** From environment_config.runs[0].render (soffice | playwright | …). */
	render: string;
}

function isBenchmark(value: string): value is Benchmark {
	return (BENCHMARKS as readonly string[]).includes(value);
}

function readRows(path: string): Row[] {
	const text = readFileSync(path, "utf8");
	const out: Row[] = [];
	for (const line of text.split(/\r?\n/)) {
		if (!line.trim()) continue;
		let data: Record<string, unknown>;
		try {
			data = JSON.parse(line) as Record<string, unknown>;
		} catch {
			continue;
		}

		// v4
		let vendor = String(data.vendor ?? data.tool ?? "");
		let benchmarkRaw = String(data.benchmark ?? "");
		if (!benchmarkRaw && typeof data.stage === "string") {
			benchmarkRaw = LEGACY_STAGE[data.stage] ?? data.stage;
		}
		if (!benchmarkRaw) benchmarkRaw = "script_redlines";
		if (!vendor || !isBenchmark(benchmarkRaw)) continue;

		// Prefer top-level v4 fields; fall back to nested aggregate (v3).
		const agg = (data.aggregate ?? {}) as Record<string, unknown>;
		const n_docs = num(data.n_docs ?? agg.n_docs);
		const overall_mean = num(data.overall_mean ?? agg.overall_mean);
		const overall_median = num(data.overall_median ?? agg.overall_median);
		const exact_100 = num(data.exact_100 ?? agg.exact_100);
		const failures = data.failures;
		const n_failures = Array.isArray(failures)
			? failures.length
			: num(data.n_failures);

		// Drop tiny smoke / partial runs (matches export-results-md for docxodus).
		if (vendor === "docxodus" && n_docs <= 100) continue;
		// Sanity baseline (1-doc identity check) is not a competitive ranking entry.
		if (vendor === "prebaked") continue;

		const env = (data.environment_config ?? {}) as Record<string, unknown>;
		const runs = Array.isArray(env.runs) ? env.runs : [];
		const firstRun =
			runs.length > 0 && typeof runs[0] === "object" && runs[0] !== null
				? (runs[0] as Record<string, unknown>)
				: {};
		const render = String(firstRun.render ?? "");

		out.push({
			vendor,
			benchmark: benchmarkRaw,
			tool_version:
				data.tool_version == null ? null : String(data.tool_version),
			timestamp: String(data.timestamp ?? data.run_ts ?? ""),
			n_docs,
			overall_mean,
			overall_median,
			exact_100,
			n_failures,
			render,
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

/**
 * One line per (vendor, benchmark, tool_version) so pins (e.g. docxodus 6.4 vs
 * 7.0) can be compared. When the same triple appears multiple times, prefer the
 * render path that matches the benchmark family, then higher n_docs / mean /
 * newer timestamp (same policy as scripts/export-results-md.py).
 */
function bestPerVendorBenchmarkVersion(rows: Row[]): Map<string, Row> {
	const best = new Map<string, Row>();
	for (const row of rows) {
		const version = row.tool_version?.trim() || "—";
		const key = `${row.vendor}__${row.benchmark}__${version}`;
		const cur = best.get(key);
		if (!cur || rankRow(row) > rankRow(cur)) best.set(key, row);
	}
	return best;
}

/** Higher is better. */
function rankRow(row: Row): [number, number, number, string] {
	const isVisual = row.benchmark.startsWith("visual");
	const renderFit = isVisual
		? row.render === "playwright"
			? 1
			: 0
		: row.render === "playwright"
			? 0
			: 1;
	return [renderFit, row.n_docs, row.overall_mean, row.timestamp];
}

function fmt(n: number, digits = 2): string {
	return n.toFixed(digits);
}

function buildTable(best: Map<string, Row>, benchmark: Benchmark): string {
	const rows = Array.from(best.values())
		.filter((r) => r.benchmark === benchmark)
		.sort((a, b) => {
			if (b.overall_median !== a.overall_median) {
				return b.overall_median - a.overall_median;
			}
			if (b.overall_mean !== a.overall_mean) {
				return b.overall_mean - a.overall_mean;
			}
			// Stable tie-break: vendor then version (so 6.4 and 7.0 stay readable).
			const v = a.vendor.localeCompare(b.vendor);
			if (v !== 0) return v;
			return (a.tool_version ?? "").localeCompare(b.tool_version ?? "");
		});

	const title = BENCHMARK_TITLES[benchmark];
	if (rows.length === 0) {
		return `### ${title}\n\n_No data yet._`;
	}

	const header =
		"| Rank | Vendor | Version | Docs | Mean | Median | Perfect (100) | Failures |\n" +
		"| --- | --- | --- | --- | --- | --- | --- | --- |";
	const body = rows
		.map((r, i) => {
			return (
				`| ${i + 1} | ${r.vendor} | ${r.tool_version ?? "—"} | ` +
				`${r.n_docs} | ${fmt(r.overall_mean)} | ${fmt(r.overall_median)} | ` +
				`${r.exact_100} | ${r.n_failures} |`
			);
		})
		.join("\n");

	return (
		`### ${title}\n\n` +
		`Sorted by median score (0–100, higher is closer to the oracle). ` +
		`Multiple **versions** of the same vendor are listed separately.\n\n` +
		`${header}\n${body}`
	);
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
	const rows = readRows(BENCH_JSONL);
	if (rows.length === 0) {
		console.error("No usable bench entries found in", BENCH_JSONL);
		process.exit(1);
	}
	const best = bestPerVendorBenchmarkVersion(rows);
	const tables = BENCHMARKS.map((b) => buildTable(best, b));
	updateReadme(tables);

	const vendors = new Set(Array.from(best.values()).map((r) => r.vendor));
	console.log(
		`Updated README.md ranking for ${vendors.size} vendor(s), ${best.size} vendor×benchmark×version cell(s).`,
	);
	for (const vendor of Array.from(vendors).sort()) {
		const vendorRows = Array.from(best.values()).filter((r) => r.vendor === vendor);
		const versions = [
			...new Set(vendorRows.map((r) => r.tool_version ?? "—")),
		].sort();
		for (const ver of versions) {
			const parts = BENCHMARKS.map((b) => {
				const r = best.get(`${vendor}__${b}__${ver}`);
				return r ? `${b}=${fmt(r.overall_median)}` : null;
			}).filter(Boolean);
			if (parts.length) console.log(`  ${vendor}@${ver}: ${parts.join(", ")}`);
		}
	}
}

main();
