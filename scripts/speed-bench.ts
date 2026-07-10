/**
 * Meticulous redline-GENERATION speed benchmark for the Node engines.
 *
 * Methodology (fairness + rigor):
 *  - Pairs are read into memory ONCE (Uint8Array), so timings measure the engine's
 *    compare/redline work, not disk I/O.
 *  - Engine init (import / WASM load) is timed SEPARATELY as a one-time cost — never mixed
 *    into per-pair timings.
 *  - Warmup: the first `--warmup` pairs run untimed (JIT / cache warm-up).
 *  - Each of the N pairs runs `--reps` times; every call is timed with `performance.now()`
 *    and recorded individually → full distribution.
 *  - Failed pairs (engine throws) are excluded from timing stats and counted separately,
 *    so a fast-throwing failure can't deflate the mean.
 *  - Same pair set + same order for every method.
 *
 * Output: a JSONL line per method to `--out`, plus a table to stdout.
 *
 * Usage:
 *   node --import tsx scripts/speed-bench.ts --pairs 40 --reps 3 --warmup 3 \
 *     --out results/speed.jsonl [--methods jubarte-native,jubarte-lossless,...]
 */
import { readFileSync, appendFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { performance } from "node:perf_hooks";
import { parseManifest, loadEngine } from "./generate-native-redlines.ts";

interface Stats {
	n: number;
	mean: number;
	median: number;
	p90: number;
	p95: number;
	p99: number;
	min: number;
	max: number;
	std: number;
	total: number;
	throughput_per_s: number;
}

function stats(xs: number[]): Stats {
	const s = [...xs].sort((a, b) => a - b);
	const n = s.length;
	const total = s.reduce((a, b) => a + b, 0);
	const mean = total / n;
	const q = (p: number) =>
		s[Math.min(n - 1, Math.max(0, Math.ceil(p * n) - 1))];
	const variance = s.reduce((a, b) => a + (b - mean) ** 2, 0) / n;
	return {
		n,
		mean,
		median: q(0.5),
		p90: q(0.9),
		p95: q(0.95),
		p99: q(0.99),
		min: s[0],
		max: s[n - 1],
		std: Math.sqrt(variance),
		total,
		throughput_per_s: (1000 * n) / total,
	};
}

interface MethodConfig {
	method: string;
	dist: string;
}

const METHODS: MethodConfig[] = [
	{ method: "jubarte-final-native", dist: "dist/jubarte-final" },
	{ method: "jubarte-final-lossless", dist: "dist/jubarte-final" },
	{ method: "docxodus", dist: "" },
	{ method: "docx-redline-js", dist: "" },
	{ method: "superdoc-ts", dist: "" },
];
// method label → the loadEngine method id (jubarte-final-native still loads via "jubarte-native")
function engineMethod(label: string): string {
	if (label.includes("native")) return "jubarte-native";
	if (label.includes("jubarte")) return "jubarte-lossless";
	return label;
}

function arg(flag: string, dflt: string): string {
	const i = process.argv.indexOf(flag);
	return i !== -1 && i + 1 < process.argv.length ? process.argv[i + 1] : dflt;
}

async function main() {
	const nPairs = Number(arg("--pairs", "40"));
	const reps = Number(arg("--reps", "3"));
	const warmup = Number(arg("--warmup", "3"));
	const outPath = arg("--out", "results/speed.jsonl");
	const manifest = arg(
		"--manifest",
		"corpus/word_based/centralized_mapping.csv",
	);
	const sourceDir = arg("--source-dir", "corpus/word_based/docx_source");
	const only = arg("--methods", "");
	const wanted = only ? new Set(only.split(",")) : null;
	const runTs = arg("--run-ts", "");

	// Load N pairs into memory (both sources present), same set for every method.
	const pairs: { key: string; base: Uint8Array; next: Uint8Array }[] = [];
	for (const p of parseManifest(manifest, ["ok"])) {
		const bp = join(sourceDir, `${p.base}.docx`);
		const np = join(sourceDir, `${p.next}.docx`);
		if (existsSync(bp) && existsSync(np)) {
			pairs.push({
				key: `${p.base}_${p.next}`,
				base: new Uint8Array(readFileSync(bp)),
				next: new Uint8Array(readFileSync(np)),
			});
			if (pairs.length >= nPairs) break;
		}
	}
	console.log(
		`speed-bench: ${pairs.length} pairs in memory, reps=${reps}, warmup=${warmup}\n`,
	);
	mkdirSync(dirname(outPath), { recursive: true });

	const rows: any[] = [];
	for (const mc of METHODS) {
		if (wanted && !wanted.has(mc.method)) continue;
		const t0 = performance.now();
		let engine;
		try {
			engine = await loadEngine(engineMethod(mc.method), mc.dist);
		} catch (e) {
			console.error(`  ${mc.method}: init failed: ${(e as Error).message}`);
			continue;
		}
		const initMs = performance.now() - t0;

		// warmup (untimed)
		for (let w = 0; w < warmup && w < pairs.length; w++) {
			try {
				await engine(pairs[w].base, pairs[w].next);
			} catch {
				/* ignore */
			}
		}
		// timed
		const samples: number[] = [];
		let failures = 0;
		for (let r = 0; r < reps; r++) {
			for (const p of pairs) {
				const s = performance.now();
				try {
					await engine(p.base, p.next);
					samples.push(performance.now() - s);
				} catch {
					failures++;
				}
			}
		}
		if (samples.length === 0) {
			console.error(`  ${mc.method}: all ${failures} calls failed`);
			continue;
		}
		const st = stats(samples);
		const row = {
			schema: 1,
			kind: "speed",
			tool: mc.method,
			runtime: "node",
			run_ts: runTs,
			init_ms: round(initMs),
			failures,
			unit: "ms_per_redline",
			...roundStats(st),
		};
		rows.push(row);
		appendFileSync(outPath, JSON.stringify(row) + "\n");
		console.log(
			`  ${mc.method.padEnd(26)} init ${initMs.toFixed(0).padStart(5)}ms  ` +
				`median ${st.median.toFixed(2).padStart(7)}ms  mean ${st.mean.toFixed(2).padStart(7)}ms  ` +
				`p95 ${st.p95.toFixed(2).padStart(7)}ms  ${st.throughput_per_s.toFixed(1).padStart(6)}/s  ` +
				`(n=${st.n}, fail=${failures})`,
		);
	}
	console.log(`\nwrote ${rows.length} rows → ${outPath}`);
}

function round(x: number): number {
	return Math.round(x * 1000) / 1000;
}
function roundStats(s: Stats): Stats {
	return Object.fromEntries(
		Object.entries(s).map(([k, v]) => [k, round(v as number)]),
	) as unknown as Stats;
}

await main();
