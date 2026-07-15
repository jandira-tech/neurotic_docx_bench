#!/usr/bin/env node
/**
 * Build jubarte under TypeScript 6 and 7, run redline_speed_bench on each
 * dist (native + lossless), run rust once, write a side-by-side comparison.
 *
 * Does NOT leave the jubarte tree on TS6 — package.json + bun.lock restored.
 *
 * Usage (from neurotic_docx_bench OR jubarte root — auto-detects):
 *   node scripts/redline_speed_bench_ts6_vs_ts7.mjs
 *   node scripts/redline_speed_bench_ts6_vs_ts7.mjs --min-pairs 1000 --warmup 10
 *   node scripts/redline_speed_bench_ts6_vs_ts7.mjs --only ts6   # after ts7 already ran
 *   node scripts/redline_speed_bench_ts6_vs_ts7.mjs --skip-rust
 *   node scripts/redline_speed_bench_ts6_vs_ts7.mjs --skip-build  # reuse existing dist slots
 */
import { spawnSync } from "node:child_process";
import {
	copyFileSync,
	cpSync,
	existsSync,
	mkdirSync,
	readFileSync,
	rmSync,
	writeFileSync,
} from "node:fs";
import { createHash } from "node:crypto";
import { homedir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// This script lives in neurotic_docx_bench/scripts/
const BENCH_ROOT = path.resolve(__dirname, "..");
const JUBARTE_ROOT =
	process.env.JUBARTE_ROOT || path.resolve(BENCH_ROOT, "../jubarte-first");
const bun = process.env.BUN_BIN || path.join(homedir(), ".bun/bin/bun");
const outRoot = path.join(BENCH_ROOT, "results/redline_speed_bench/ts6-vs-ts7");

function has(f) {
	return process.argv.includes(f);
}
function arg(f, d) {
	const i = process.argv.indexOf(f);
	if (i === -1) return d;
	const n = process.argv[i + 1];
	if (!n || n.startsWith("--")) return true;
	return n;
}

const only = String(arg("--only", "")); // "", "ts6", "ts7"
const minPairs = String(arg("--min-pairs", "1000"));
const warmup = String(arg("--warmup", "10"));
const reps = String(arg("--reps", "1"));
const seed = String(arg("--seed", "42"));
const skipRust = has("--skip-rust");
const skipBuild = has("--skip-build");
const ts6Spec = String(arg("--ts6", "6.0.2"));
const ts7Spec = String(arg("--ts7", "7.0.2"));

function run(cmd, args, opts = {}) {
	console.log(`\n$ ${cmd} ${args.join(" ")}`);
	const r = spawnSync(cmd, args, {
		encoding: "utf8",
		stdio: "inherit",
		...opts,
	});
	if (r.status !== 0) {
		throw new Error(`${cmd} exited ${r.status}`);
	}
}

function shCapture(cmd, args, opts = {}) {
	return spawnSync(cmd, args, {
		encoding: "utf8",
		...opts,
	});
}

function tsVer() {
	const r = shCapture(process.execPath, [
		"-e",
		"console.log(require('typescript/package.json').version)",
	], { cwd: JUBARTE_ROOT });
	return (r.stdout || "").trim() || "unknown";
}

function hashFile(p) {
	if (!existsSync(p)) return null;
	return createHash("sha256").update(readFileSync(p)).digest("hex").slice(0, 16);
}

function distFp(dir) {
	return {
		"node.mjs": hashFile(path.join(dir, "node.mjs")),
		"node.cjs": hashFile(path.join(dir, "node.cjs")),
		"lossless.node.mjs": hashFile(path.join(dir, "lossless.node.mjs")),
		"lossless.node.cjs": hashFile(path.join(dir, "lossless.node.cjs")),
	};
}

function installTs(spec) {
	const pkgPath = path.join(JUBARTE_ROOT, "package.json");
	const pkg = JSON.parse(readFileSync(pkgPath, "utf8"));
	pkg.devDependencies = pkg.devDependencies || {};
	pkg.devDependencies.typescript = spec.startsWith("^") ? spec : spec;
	// never keep the classic bridge for pure A/B
	delete pkg.devDependencies["@typescript/typescript6"];
	writeFileSync(pkgPath, `${JSON.stringify(pkg, null, 2)}\n`);
	run(bun, ["add", "-d", `typescript@${spec.replace(/^\^/, "")}`], {
		cwd: JUBARTE_ROOT,
	});
	console.log(`typescript → ${tsVer()}`);
}

function buildAndSlot(label) {
	const slot = path.join(BENCH_ROOT, `dist/jubarte-final-${label}`);
	if (!skipBuild) {
		run(bun, ["run", "build"], { cwd: JUBARTE_ROOT });
	}
	const src = path.join(JUBARTE_ROOT, "dist");
	if (!existsSync(path.join(src, "node.cjs"))) {
		throw new Error(`build produced no ${src}/node.cjs`);
	}
	if (existsSync(slot)) rmSync(slot, { recursive: true, force: true });
	mkdirSync(path.dirname(slot), { recursive: true });
	cpSync(src, slot, { recursive: true });
	// also refresh default slot for anything that still points at jubarte-final
	const def = path.join(BENCH_ROOT, "dist/jubarte-final");
	if (existsSync(def)) rmSync(def, { recursive: true, force: true });
	cpSync(src, def, { recursive: true });
	const fp = distFp(slot);
	console.log(`[${label}] dist → ${slot}`, fp);
	writeFileSync(
		path.join(outRoot, `${label}-dist-fingerprint.json`),
		JSON.stringify({ label, typescript: tsVer(), fingerprints: fp }, null, 2),
	);
	return { slot, fp, typescript: tsVer() };
}

function runBench({ label, jubarteDist, methods, outDir }) {
	mkdirSync(outDir, { recursive: true });
	const args = [
		"--import",
		"tsx",
		path.join(BENCH_ROOT, "scripts/redline_speed_bench.ts"),
		"--min-pairs",
		minPairs,
		"--warmup",
		warmup,
		"--reps",
		reps,
		"--seed",
		seed,
		"--jubarte-dist",
		jubarteDist,
		"--methods",
		methods,
		"--out",
		outDir,
	];
	console.log(`\n=== bench ${label} methods=${methods} ===`);
	run(process.execPath, args, { cwd: BENCH_ROOT });
	const summaryPath = path.join(outDir, "summary.json");
	return JSON.parse(readFileSync(summaryPath, "utf8"));
}

function loadRows(dir) {
	const p = path.join(dir, "summary.json");
	if (!existsSync(p)) return [];
	const s = JSON.parse(readFileSync(p, "utf8"));
	return (s.rows || []).filter((r) => typeof r.median === "number");
}

function writeComparison(ts6Dir, ts7Dir, rustDir, meta) {
	const r6 = loadRows(ts6Dir);
	const r7 = loadRows(ts7Dir);
	const rr = rustDir ? loadRows(rustDir) : [];
	const byTool = (rows) => Object.fromEntries(rows.map((r) => [r.tool, r]));
	const m6 = byTool(r6);
	const m7 = byTool(r7);

	const tools = [
		...new Set([...Object.keys(m6), ...Object.keys(m7), ...rr.map((r) => r.tool)]),
	];

	const lines = [];
	lines.push("# redline_speed_bench — TypeScript 6 vs 7 builds + rust");
	lines.push("");
	lines.push(`- **pairs:** ${minPairs} (every fixture × random partner, seed=${seed})`);
	lines.push(`- **warmup:** ${warmup}  **reps:** ${reps}`);
	lines.push(`- **TS6:** ${meta.ts6 || "—"}`);
	lines.push(`- **TS7:** ${meta.ts7 || "—"}`);
	lines.push(
		`- **dist JS fingerprints identical:** ${meta.distIdentical ? "yes" : "NO"}`,
	);
	if (meta.fp6) lines.push(`- **TS6 fingerprints:** \`${JSON.stringify(meta.fp6)}\``);
	if (meta.fp7) lines.push(`- **TS7 fingerprints:** \`${JSON.stringify(meta.fp7)}\``);
	lines.push("");
	lines.push(
		"| tool | build | median ms | mean ms | p95 | p99 | /s | wall s | fail | n |",
	);
	lines.push("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |");

	const jsonRows = [];
	for (const tool of ["jubarte-native", "jubarte-lossless"]) {
		for (const [build, m] of [
			["ts6", m6[tool]],
			["ts7", m7[tool]],
		]) {
			if (!m) continue;
			lines.push(
				`| ${tool} | ${build} | ${m.median} | ${m.mean} | ${m.p95} | ${m.p99} | ${m.throughput_per_s} | ${(m.wall_ms / 1000).toFixed(2)} | ${m.failures} | ${m.n} |`,
			);
			jsonRows.push({ tool, build, ...m });
		}
		if (m6[tool] && m7[tool]) {
			const ratio = m6[tool].median
				? +(m7[tool].median / m6[tool].median).toFixed(3)
				: null;
			const faster = m6[tool].median
				? +(
						((m6[tool].median - m7[tool].median) / m6[tool].median) *
						100
					).toFixed(1)
				: null;
			lines.push(
				`| ${tool} | **TS7/TS6 median** | **${ratio}** |  |  |  | TS7 faster **${faster}%** |  |  |  |`,
			);
		}
	}
	for (const m of rr) {
		lines.push(
			`| ${m.tool} | rust binary | ${m.median} | ${m.mean} | ${m.p95} | ${m.p99} | ${m.throughput_per_s} | ${(m.wall_ms / 1000).toFixed(2)} | ${m.failures} | ${m.n} |`,
		);
		jsonRows.push({ tool: m.tool, build: "rust", ...m });
	}

	lines.push("");
	lines.push("## Profiles");
	lines.push("");
	lines.push("```bash");
	lines.push(`npx speedscope ${path.join(ts6Dir, "cpu/jubarte-native.cpuprofile")}`);
	lines.push(`npx speedscope ${path.join(ts6Dir, "cpu/jubarte-lossless.cpuprofile")}`);
	lines.push(`npx speedscope ${path.join(ts7Dir, "cpu/jubarte-native.cpuprofile")}`);
	lines.push(`npx speedscope ${path.join(ts7Dir, "cpu/jubarte-lossless.cpuprofile")}`);
	if (rustDir) {
		lines.push(`npx speedscope ${path.join(rustDir, "cpu/jubarte-rust.cpuprofile")}`);
	}
	lines.push("```");
	lines.push("");
	if (meta.distIdentical) {
		lines.push(
			"> Dist fingerprints match between TS6 and TS7 builds — rolldown emit is independent of the tsc/tsgo version used for `.d.ts`. Any wall-time delta is noise/cache, not different JS.",
		);
	} else {
		lines.push(
			"> Dist fingerprints **differ** — runtime deltas can be real emit differences.",
		);
	}
	lines.push("");

	const md = lines.join("\n");
	writeFileSync(path.join(outRoot, "comparison.md"), md);
	writeFileSync(
		path.join(outRoot, "comparison.json"),
		JSON.stringify({ meta, rows: jsonRows }, null, 2),
	);
	console.log(md);
	return md;
}

async function main() {
	if (!existsSync(JUBARTE_ROOT)) {
		throw new Error(`jubarte root not found: ${JUBARTE_ROOT}`);
	}
	mkdirSync(outRoot, { recursive: true });

	const pkgPath = path.join(JUBARTE_ROOT, "package.json");
	const lockPath = path.join(JUBARTE_ROOT, "bun.lock");
	const bakPkg = path.join(outRoot, "package.json.bak");
	const bakLock = path.join(outRoot, "bun.lock.bak");
	copyFileSync(pkgPath, bakPkg);
	if (existsSync(lockPath)) copyFileSync(lockPath, bakLock);

	let meta = { ts6: null, ts7: null, fp6: null, fp7: null, distIdentical: null };
	const ts6Out = path.join(outRoot, "ts6");
	const ts7Out = path.join(outRoot, "ts7");
	const rustOut = path.join(outRoot, "rust");

	try {
		// ── TS7 ──────────────────────────────────────────────────────────
		if (!only || only === "ts7") {
			console.log("\n########## TypeScript 7 build + bench ##########");
			installTs(ts7Spec);
			const { slot, fp, typescript } = buildAndSlot("ts7");
			meta.ts7 = typescript;
			meta.fp7 = fp;
			runBench({
				label: "ts7",
				jubarteDist: slot,
				methods: "jubarte-native,jubarte-lossless",
				outDir: ts7Out,
			});
		}

		// ── TS6 ──────────────────────────────────────────────────────────
		if (!only || only === "ts6") {
			console.log("\n########## TypeScript 6 build + bench ##########");
			installTs(ts6Spec);
			const { slot, fp, typescript } = buildAndSlot("ts6");
			meta.ts6 = typescript;
			meta.fp6 = fp;
			runBench({
				label: "ts6",
				jubarteDist: slot,
				methods: "jubarte-native,jubarte-lossless",
				outDir: ts6Out,
			});
		}

		// ── rust (once) ──────────────────────────────────────────────────
		if (!skipRust && (!only || only === "ts7" || only === "ts6")) {
			// only run rust once when doing full A/B or either single side
			if (!only || only === "ts7") {
				console.log("\n########## jubarte-rust (once) ##########");
				runBench({
					label: "rust",
					jubarteDist: path.join(BENCH_ROOT, "dist/jubarte-final"),
					methods: "jubarte-rust",
					outDir: rustOut,
				});
			}
		}
	} finally {
		console.log("\n########## restore TypeScript 7 ##########");
		copyFileSync(bakPkg, pkgPath);
		if (existsSync(bakLock)) copyFileSync(bakLock, lockPath);
		run(bun, ["install"], { cwd: JUBARTE_ROOT });
		console.log(`restored typescript ${tsVer()}`);
		// leave default dist on TS7 build if we have it
		const ts7Slot = path.join(BENCH_ROOT, "dist/jubarte-final-ts7");
		if (existsSync(ts7Slot)) {
			const def = path.join(BENCH_ROOT, "dist/jubarte-final");
			if (existsSync(def)) rmSync(def, { recursive: true, force: true });
			cpSync(ts7Slot, def, { recursive: true });
		}
	}

	// reload fingerprints if only one side ran
	if (existsSync(path.join(outRoot, "ts6-dist-fingerprint.json"))) {
		const j = JSON.parse(
			readFileSync(path.join(outRoot, "ts6-dist-fingerprint.json"), "utf8"),
		);
		meta.ts6 = meta.ts6 || j.typescript;
		meta.fp6 = meta.fp6 || j.fingerprints;
	}
	if (existsSync(path.join(outRoot, "ts7-dist-fingerprint.json"))) {
		const j = JSON.parse(
			readFileSync(path.join(outRoot, "ts7-dist-fingerprint.json"), "utf8"),
		);
		meta.ts7 = meta.ts7 || j.typescript;
		meta.fp7 = meta.fp7 || j.fingerprints;
	}
	if (meta.fp6 && meta.fp7) {
		meta.distIdentical = JSON.stringify(meta.fp6) === JSON.stringify(meta.fp7);
	}

	if (existsSync(path.join(ts6Out, "summary.json")) &&
		existsSync(path.join(ts7Out, "summary.json"))) {
		writeComparison(
			ts6Out,
			ts7Out,
			existsSync(path.join(rustOut, "summary.json")) ? rustOut : null,
			meta,
		);
	} else {
		console.log(
			"One side missing — open results under",
			outRoot,
			"(need both ts6/ and ts7/ summaries for comparison.md)",
		);
	}
}

main().catch((e) => {
	console.error(e);
	process.exit(1);
});
