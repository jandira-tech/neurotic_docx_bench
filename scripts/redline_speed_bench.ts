/**
 * redline_speed_bench — large-N redline generation speed + solid CPU profiles.
 *
 * Builds a pool of unique fixtures (default **1000** by content-hash, drawn from
 * multiple corpus dirs), then forms **5000** deterministic random base→next pairs
 * (every fixture is a base at least once per round). Times each engine call with
 * a full distribution and profiles native CLIs with **samply** (Firefox Profiler
 * format) — V8 inspector only for in-process Node engines.
 *
 * Engines:
 *   - docxodus-csharp  (.NET Docxodus tools/redline CLI — native C#, not WASM)
 *   - jubarte-rust     (canonical jubarte-redlines native CLI)
 *   - jubarte-rust-inproc  (warm in-process jubarte worker — fair algorithm baseline)
 *   - jubarte-wasm     (canonical jubarte-redlines via wasm-pack + wasm-opt -O3 in V8)
 *   - jubarte-native / jubarte-lossless  (optional Node paths; V8 profile)
 *
 * Usage (from neurotic_docx_bench root):
 *   node --import tsx scripts/redline_speed_bench.ts
 *   node --import tsx scripts/redline_speed_bench.ts \
 *     --fixture-count 1000 --min-pairs 5000 --warmup 20 --reps 1 \
 *     --methods docxodus-csharp,jubarte-rust \
 *     --out results/redline_speed_bench
 *
 * Fairness notes:
 *   - Node engines: fixtures preloaded; timed loop is in-memory compare only.
 *   - docxodus-csharp / jubarte-rust: each sample = temp write + spawnSync +
 *     native compare + read output (real end-to-end CLI cost).
 *   - samply profiles the timed loop process tree (parent + child redline bins).
 */
import {
	appendFileSync,
	existsSync,
	mkdirSync,
	readdirSync,
	readFileSync,
	writeFileSync,
} from "node:fs";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import { Session } from "node:inspector/promises";
import { basename, dirname, join, resolve } from "node:path";
import { performance } from "node:perf_hooks";
import { fileURLToPath } from "node:url";
import {
	loadEngine,
	shutdownAllLongLivedWorkers,
} from "./generate-native-redlines.ts";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

// ── CLI ──────────────────────────────────────────────────────────────────────

function arg(flag: string, dflt: string): string {
	const i = process.argv.indexOf(flag);
	return i !== -1 && i + 1 < process.argv.length ? process.argv[i + 1] : dflt;
}
function has(flag: string): boolean {
	return process.argv.includes(flag);
}

const DEFAULT_FIXTURE_DIRS = [
	"corpus/word_based/docx_source",
	"corpus/word_based/docx_source_randomized",
	"corpus/word_based/docx_accepted_word",
	"corpus/no_comments_pdf_was_generated_by_word/docx_source",
	"corpus/no_comments_pdf_was_generated_by_word/docx_accepted_word",
	"corpus/word_based/docx_redlines_word",
	"corpus/no_comments_pdf_was_generated_by_word/docx_redlines_word",
];

const fixtureCount = Number(arg("--fixture-count", "1000"));
const minPairs = Number(arg("--min-pairs", "5000"));
const warmup = Number(arg("--warmup", "20"));
const reps = Number(arg("--reps", "1"));
const seed = Number(arg("--seed", "42"));
const outDir = resolve(ROOT, arg("--out", "results/redline_speed_bench"));
const methods = arg(
	"--methods",
	// Thesis-defense default: warm-vs-warm first (algorithm), then CLI spawn,
	// then WASM. Order does not affect timing (engines run sequentially).
	// The three jubarte lanes always run together so engine compute tax
	// (inproc), deployment reality (CLI spawn+I/O) and the portability lane
	// (WASM) are measured under the same conditions in every run
	// (WASM_PERF_PLAN W7).
	"jubarte-rust-inproc,docxodus-csharp-inproc,jubarte-rust,docxodus-csharp,docxodus,jubarte-wasm",
)
	.split(",")
	.map((s) => s.trim())
	.filter(Boolean);
const topN = Number(arg("--top", "30"));
const skipProfile = has("--no-profile");
const profileSubset = Number(arg("--profile-pairs", "0")); // 0 = full timed set under samply
const jubarteDist = resolve(ROOT, arg("--jubarte-dist", "dist/jubarte-final"));
const rustDist = resolve(
	ROOT,
	arg(
		"--rust-dist",
		existsSync(
			join(ROOT, "src/neurotic_docx_bench/utils/jubarte/jubarte-rust/redline"),
		)
			? "src/neurotic_docx_bench/utils/jubarte/jubarte-rust"
			: existsSync(join(ROOT, "jubarte-rs-probe/redline"))
				? "jubarte-rs-probe"
				: "src/neurotic_docx_bench/utils/jubarte/jubarte-rust",
	),
);
const csharpDist = resolve(
	ROOT,
	arg("--csharp-dist", defaultCsharpDist()),
);
const csharpInprocDist = resolve(
	ROOT,
	arg("--csharp-inproc-dist", defaultCsharpInprocDist()),
);
const rustInprocDist = resolve(
	ROOT,
	arg("--rust-inproc-dist", defaultRustInprocDist()),
);
const wasmDist = resolve(
	ROOT,
	arg("--wasm-dist", defaultJubarteWasmDist()),
);
const fixturesDirArg = arg("--fixtures", "");
const fixturesDirs = fixturesDirArg
	? [resolve(ROOT, fixturesDirArg)]
	: arg("--fixtures-dirs", DEFAULT_FIXTURE_DIRS.join(","))
			.split(",")
			.map((s) => s.trim())
			.filter(Boolean)
			.map((d) => resolve(ROOT, d));

/** Resolve Docxodus C# CLI dist (Release net8.0 publish layout). */
export function defaultCsharpDist(root: string = ROOT): string {
	const candidates = [
		join(root, "src/neurotic_docx_bench/utils/docxodus/docxodus-csharp"),
		join(root, "../ooxmlsdk/Docxodus/tools/redline/bin/Release/net8.0"),
		join(
			root,
			"../ooxmlsdk/Docxodus/tools/redline/bin/Release/net9.0",
		),
	];
	for (const c of candidates) {
		if (existsSync(join(c, "redline"))) return c;
	}
	return candidates[0]!;
}

/** Long-lived in-process Docxodus worker (docxodus-inproc binary). */
export function defaultCsharpInprocDist(root: string = ROOT): string {
	const candidates = [
		join(
			root,
			"src/neurotic_docx_bench/utils/docxodus/docxodus-csharp-inproc/bin/Release/net8.0",
		),
		join(
			root,
			"src/neurotic_docx_bench/utils/docxodus/docxodus-csharp-inproc",
		),
	];
	for (const c of candidates) {
		if (existsSync(join(c, "docxodus-inproc"))) return c;
	}
	return candidates[0]!;
}

/** Long-lived jubarte-rust worker (`jubarte-worker` / `jubarte-inproc`). */
export function defaultRustInprocDist(root: string = ROOT): string {
	const candidates = [
		join(root, "src/neurotic_docx_bench/utils/jubarte/jubarte-rust"),
		join(
			root,
			"src/neurotic_docx_bench/utils/jubarte/jubarte-rust-inproc/target/release",
		),
		join(
			root,
			"src/neurotic_docx_bench/utils/jubarte/jubarte-rust-inproc",
		),
	];
	for (const c of candidates) {
		if (
			existsSync(join(c, "jubarte-worker")) ||
			existsSync(join(c, "jubarte-inproc"))
		) {
			return c;
		}
	}
	return candidates[0]!;
}

// ── RNG / stats ──────────────────────────────────────────────────────────────

/** Mulberry32 — deterministic, fast. */
export function mulberry32(a: number): () => number {
	return () => {
		let t = (a += 0x6d2b79f5);
		t = Math.imul(t ^ (t >>> 15), t | 1);
		t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
}

export interface Stats {
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

export function stats(xs: number[]): Stats {
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

export function round(x: number, d = 3): number {
	const m = 10 ** d;
	return Math.round(x * m) / m;
}

// ── fixtures → pairs ─────────────────────────────────────────────────────────

export interface FixtureFile {
	/** Stable display key (basename, disambiguated on collision). */
	name: string;
	path: string;
	sha1: string;
}

export interface Pair {
	key: string;
	baseName: string;
	nextName: string;
	base: Uint8Array;
	next: Uint8Array;
	round: number;
}

export function listDocx(dir: string): string[] {
	if (!existsSync(dir)) return [];
	return readdirSync(dir)
		.filter((f) => f.toLowerCase().endsWith(".docx") && !f.startsWith("~$"))
		.sort((a, b) => a.localeCompare(b));
}

/**
 * Collect up to `targetCount` unique fixtures by content SHA-1, walking dirs
 * in order (first-seen wins). Names are basenames; collisions get a short hash
 * suffix so pair keys stay unique.
 */
export function collectFixtures(
	dirs: string[],
	targetCount: number,
): FixtureFile[] {
	const byHash = new Map<string, FixtureFile>();
	const usedNames = new Set<string>();

	for (const dir of dirs) {
		if (byHash.size >= targetCount) break;
		if (!existsSync(dir)) continue;
		for (const f of listDocx(dir)) {
			if (byHash.size >= targetCount) break;
			const path = join(dir, f);
			const buf = readFileSync(path);
			const sha1 = createHash("sha1").update(buf).digest("hex");
			if (byHash.has(sha1)) continue;
			let name = f;
			if (usedNames.has(name)) {
				name = `${f.replace(/\.docx$/i, "")}__${sha1.slice(0, 8)}.docx`;
			}
			usedNames.add(name);
			byHash.set(sha1, { name, path, sha1 });
		}
	}
	return [...byHash.values()].sort((a, b) => a.name.localeCompare(b.name));
}

/**
 * Every fixture is a base at least once per round; each base is paired with a
 * random *different* fixture. Rounds repeat until `minPairs` is reached.
 */
export function buildPairs(
	files: string[],
	bytes: Map<string, Uint8Array>,
	min: number,
	seedVal: number,
): Pair[] {
	if (files.length < 2) {
		throw new Error(
			`need ≥2 fixtures to form random pairs (found ${files.length})`,
		);
	}
	const rng = mulberry32(seedVal >>> 0);
	const pairs: Pair[] = [];
	let round = 0;
	while (pairs.length < min) {
		for (const baseName of files) {
			let nextName = baseName;
			let guard = 0;
			while (nextName === baseName && guard++ < 32) {
				nextName = files[Math.floor(rng() * files.length)]!;
			}
			if (nextName === baseName) {
				nextName = files[(files.indexOf(baseName) + 1) % files.length]!;
			}
			const base = bytes.get(baseName)!;
			const next = bytes.get(nextName)!;
			pairs.push({
				key: `${baseName.replace(/\.docx$/i, "")}__${nextName.replace(/\.docx$/i, "")}__r${round}`,
				baseName,
				nextName,
				base,
				next,
				round,
			});
			if (pairs.length >= min) break;
		}
		round++;
	}
	return pairs;
}

// ── engine resolution ────────────────────────────────────────────────────────

export function isNativeCliMethod(method: string): boolean {
	const id = engineMethodId(method);
	// True CLI-per-call engines (spawn per redline).
	return id === "docxodus-csharp" || id === "jubarte-rust";
}

/** Engines whose timed work is mostly outside V8 — profile with samply. */
export function usesSamplyProfile(method: string): boolean {
	const id = engineMethodId(method);
	return (
		id === "docxodus-csharp" ||
		id === "docxodus-csharp-inproc" ||
		id === "jubarte-rust" ||
		id === "jubarte-rust-inproc"
	);
}

export function engineMethodId(method: string): string {
	if (
		method === "docxodus-cs-inproc" ||
		method === "docxodus-csharp-inproc"
	) {
		return "docxodus-csharp-inproc";
	}
	if (method === "docxodus-cs" || method === "docxodus-csharp") {
		return "docxodus-csharp";
	}
	if (
		method === "jubarte-rust-inproc" ||
		method === "jubarte-rs-inproc"
	) {
		return "jubarte-rust-inproc";
	}
	// Before generic "rust" match — jubarte-rust-wasm would otherwise collapse.
	if (
		method === "jubarte-wasm" ||
		method === "jubarte-rs-wasm" ||
		method === "jubarte-rust-wasm"
	) {
		return "jubarte-wasm";
	}
	if (method.includes("native") && method.includes("jubarte")) {
		return "jubarte-native";
	}
	if (method.includes("lossless")) return "jubarte-lossless";
	if (method.includes("rust") || method.includes("ooxmlsdk")) {
		return "jubarte-rust";
	}
	if (method === "docxodus" || method === "docxodus-wasm") {
		return "docxodus";
	}
	return method;
}

/**
 * The three jubarte lanes that must always run together (WASM_PERF_PLAN W7):
 * `jubarte-rust-inproc` (warm native — the fair algorithm baseline),
 * `jubarte-rust` (CLI — deployment reality), and `jubarte-wasm` (V8 portability
 * lane). Comparing only a subset conflates engine compute tax with CLI
 * spawn+I/O overhead.
 */
const JUBARTE_LANES = new Set([
	"jubarte-rust-inproc",
	"jubarte-rust",
	"jubarte-wasm",
]);
{
	const requested = new Set(
		methods
			.map((m) => engineMethodId(m))
			.filter((id) => JUBARTE_LANES.has(id)),
	);
	if (requested.size > 0 && requested.size < JUBARTE_LANES.size) {
		const missing = [...JUBARTE_LANES].filter(
			(id) => !requested.has(id),
		);
		console.error(
			`error: --methods includes jubarte lanes ${[...requested].join(", ")} ` +
				`but is missing ${missing.join(", ")}. The three jubarte lanes ` +
				`(jubarte-rust-inproc, jubarte-rust, jubarte-wasm) must always run ` +
				`together so engine compute tax, CLI spawn overhead, and the WASM ` +
				`portability lane are measured under the same conditions ` +
				`(WASM_PERF_PLAN W7). To override, pass all three explicitly.`,
		);
		process.exit(2);
	}
}

export function defaultJubarteWasmDist(root: string = ROOT): string {
	const candidates = [
		join(root, "src/neurotic_docx_bench/utils/jubarte/jubarte-wasm"),
		join(root, "src/neurotic_docx_bench/utils/jubarte/jubarte-wasm/pkg"),
	];
	for (const c of candidates) {
		if (
			existsSync(join(c, "pkg/jubarte_wasm.js")) ||
			existsSync(join(c, "jubarte_wasm.js"))
		) {
			return c;
		}
	}
	return candidates[0]!;
}

export function distFor(
	method: string,
	opts: {
		jubarteDist: string;
		rustDist: string;
		csharpDist: string;
		csharpInprocDist: string;
		rustInprocDist: string;
		wasmDist?: string;
	},
): string {
	const id = engineMethodId(method);
	if (id === "jubarte-rust") return opts.rustDist;
	if (id === "jubarte-rust-inproc") return opts.rustInprocDist;
	if (id === "docxodus-csharp") return opts.csharpDist;
	if (id === "docxodus-csharp-inproc") return opts.csharpInprocDist;
	if (id === "jubarte-wasm") return opts.wasmDist ?? defaultJubarteWasmDist();
	return opts.jubarteDist;
}

// ── CPU profilers ────────────────────────────────────────────────────────────

interface HotFrame {
	name: string;
	url: string;
	line: number | null;
	hits: number;
	pct: number;
}

function analyzeCpuProfile(profile: {
	nodes?: Array<{
		id: number;
		hitCount?: number;
		callFrame?: {
			functionName?: string;
			url?: string;
			lineNumber?: number;
		};
	}>;
	samples?: number[];
	startTime?: number;
	endTime?: number;
}): { totalHits: number; durationMs: number | null; top: HotFrame[] } {
	const nodes = profile.nodes || [];
	const byId = new Map(nodes.map((n) => [n.id, n]));
	const selfHits = new Map<number, number>();
	if (Array.isArray(profile.samples) && profile.samples.length) {
		for (const id of profile.samples) {
			selfHits.set(id, (selfHits.get(id) || 0) + 1);
		}
	} else {
		for (const n of nodes) {
			if (n.hitCount) selfHits.set(n.id, n.hitCount);
		}
	}
	let totalHits = 0;
	const merged = new Map<string, HotFrame>();
	for (const [id, hits] of selfHits) {
		totalHits += hits;
		const n = byId.get(id);
		const cf = n?.callFrame || {};
		const name = cf.functionName || "(anonymous)";
		const url = (cf.url || "").replace(/^file:\/\//, "");
		const line = cf.lineNumber != null ? cf.lineNumber + 1 : null;
		const key = `${name}\0${url}`;
		const prev = merged.get(key);
		if (prev) prev.hits += hits;
		else
			merged.set(key, {
				name,
				url,
				line,
				hits,
				pct: 0,
			});
	}
	const top = [...merged.values()]
		.sort((a, b) => b.hits - a.hits)
		.slice(0, topN)
		.map((r) => ({
			...r,
			pct: totalHits ? round((100 * r.hits) / totalHits, 2) : 0,
		}));
	const durationMs =
		profile.startTime != null && profile.endTime != null
			? (profile.endTime - profile.startTime) / 1000
			: null;
	return { totalHits, durationMs, top };
}

async function withV8CpuProfile<T>(
	enabled: boolean,
	fn: () => Promise<T>,
): Promise<{ result: T; profile: object | null }> {
	if (!enabled) {
		return { result: await fn(), profile: null };
	}
	const session = new Session();
	session.connect();
	try {
		await session.post("Profiler.enable");
		await session.post("Profiler.setSamplingInterval", { interval: 1000 });
		await session.post("Profiler.start");
		const result = await fn();
		const { profile } = (await session.post("Profiler.stop")) as {
			profile: object;
		};
		return { result, profile };
	} finally {
		try {
			session.disconnect();
		} catch {
			/* ignore */
		}
	}
}

function findSamply(): string | null {
	const which = spawnSync("which", ["samply"], { encoding: "utf8" });
	if (which.status === 0 && which.stdout.trim()) return which.stdout.trim();
	const home = process.env.HOME;
	if (home) {
		const cargo = join(home, ".cargo", "bin", "samply");
		if (existsSync(cargo)) return cargo;
	}
	return null;
}

/**
 * Run `fn` as a separate process under samply so native child redline CLIs
 * appear in the profile. Inner process is this same script with --inner-run.
 */
function runUnderSamply(opts: {
	method: string;
	engId: string;
	dist: string;
	pairsMetaPath: string;
	bytesDir: string;
	pairKeys: string[];
	warmup: number;
	reps: number;
	profilePath: string;
	samplesPath: string;
	keysPath: string;
}): { ok: boolean; error?: string } {
	const samply = findSamply();
	if (!samply) {
		return {
			ok: false,
			error:
				"samply not found on PATH (install: cargo install --locked samply)",
		};
	}
	mkdirSync(dirname(opts.profilePath), { recursive: true });
	// Keys go to a file — 5000 keys blow ARG_MAX if inlined on the CLI.
	writeFileSync(opts.keysPath, JSON.stringify(opts.pairKeys));
	const nodeArgs = [
		"--import",
		"tsx",
		join(HERE, "redline_speed_bench.ts"),
		"--inner-run",
		"--method",
		opts.method,
		"--engine-id",
		opts.engId,
		"--dist",
		opts.dist,
		"--pairs-meta",
		opts.pairsMetaPath,
		"--bytes-dir",
		opts.bytesDir,
		"--pair-keys-file",
		opts.keysPath,
		"--warmup",
		String(opts.warmup),
		"--reps",
		String(opts.reps),
		"--samples-out",
		opts.samplesPath,
	];
	const r = spawnSync(
		samply,
		[
			"record",
			"--save-only",
			"--no-open",
			"-r",
			"1000",
			"-o",
			opts.profilePath,
			"--",
			process.execPath,
			...nodeArgs,
		],
		{
			encoding: "utf8",
			cwd: ROOT,
			env: process.env,
			stdio: ["ignore", "inherit", "inherit"],
		},
	);
	if (r.status !== 0) {
		return {
			ok: false,
			error: `samply exit ${r.status}: ${(r.stderr || "").trim() || "see stdout"}`,
		};
	}
	return { ok: true };
}

// ── timed loop (shared by outer + inner) ─────────────────────────────────────

async function timedLoop(
	engine: (base: Uint8Array, next: Uint8Array) => Promise<Uint8Array>,
	pairs: Pair[],
	repsN: number,
	warmupN: number,
): Promise<{
	samples: number[];
	failures: { key: string; error: string }[];
	outSizes: number[];
	wallMs: number;
}> {
	for (let w = 0; w < warmupN && w < pairs.length; w++) {
		try {
			await engine(pairs[w]!.base, pairs[w]!.next);
		} catch {
			/* ignore warmup failures */
		}
	}
	const samples: number[] = [];
	const failures: { key: string; error: string }[] = [];
	const outSizes: number[] = [];
	const wall0 = performance.now();
	for (let r = 0; r < repsN; r++) {
		for (const p of pairs) {
			const s = performance.now();
			try {
				const out = await engine(p.base, p.next);
				samples.push(performance.now() - s);
				outSizes.push(out.byteLength);
			} catch (e) {
				failures.push({
					key: p.key,
					error: (e as Error).message || String(e),
				});
			}
		}
	}
	return {
		samples,
		failures,
		outSizes,
		wallMs: performance.now() - wall0,
	};
}

// ── inner worker (spawned under samply) ──────────────────────────────────────

async function innerMain(): Promise<void> {
	const method = arg("--method", "");
	const engId = arg("--engine-id", engineMethodId(method));
	const dist = arg("--dist", "");
	const pairsMetaPath = arg("--pairs-meta", "");
	const bytesDir = arg("--bytes-dir", "");
	const keysFile = arg("--pair-keys-file", "");
	const warmupN = Number(arg("--warmup", "0"));
	const repsN = Number(arg("--reps", "1"));
	const samplesOut = arg("--samples-out", "");

	const meta: {
		pairs: Array<{ key: string; base: string; next: string; round: number }>;
	} = JSON.parse(readFileSync(pairsMetaPath, "utf8"));
	const wantedKeys: string[] = keysFile
		? (JSON.parse(readFileSync(keysFile, "utf8")) as string[])
		: meta.pairs.map((p) => p.key);
	const wanted = new Set(wantedKeys);
	const byKey = new Map(meta.pairs.map((p) => [p.key, p]));
	const keys = meta.pairs.map((p) => p.key).filter((k) => wanted.has(k));

	const bytes = new Map<string, Uint8Array>();
	const loadName = (name: string) => {
		if (bytes.has(name)) return;
		const p = join(bytesDir, name);
		bytes.set(name, new Uint8Array(readFileSync(p)));
	};

	const pairs: Pair[] = [];
	for (const key of keys) {
		const m = byKey.get(key);
		if (!m) continue;
		loadName(m.base);
		loadName(m.next);
		pairs.push({
			key: m.key,
			baseName: m.base,
			nextName: m.next,
			base: bytes.get(m.base)!,
			next: bytes.get(m.next)!,
			round: m.round,
		});
	}

	const engine = await loadEngine(engId, dist);
	try {
		const result = await timedLoop(engine, pairs, repsN, warmupN);
		writeFileSync(
			samplesOut,
			JSON.stringify({
				samples: result.samples,
				failures: result.failures,
				outSizes: result.outSizes,
				wallMs: result.wallMs,
				n_pairs: pairs.length,
			}),
		);
		if (result.samples.length === 0) {
			console.error(
				`inner: all failed — ${result.failures[0]?.error ?? "unknown"}`,
			);
			shutdownAllLongLivedWorkers();
			process.exit(2);
		}
		console.error(
			`inner ${method}: n=${result.samples.length} fail=${result.failures.length} wall=${round(result.wallMs)}ms`,
		);
	} finally {
		// Critical: long-lived workers hold stdio pipes open → Node never exits
		// → samply never finalizes the .profile.json.gz. Kill them and hard-exit.
		shutdownAllLongLivedWorkers();
	}
	process.exit(0);
}

// ── outer main ───────────────────────────────────────────────────────────────

async function main() {
	if (has("--inner-run")) {
		await innerMain();
		// innerMain process.exit's; this is a safety net.
		shutdownAllLongLivedWorkers();
		return;
	}

	mkdirSync(outDir, { recursive: true });
	mkdirSync(join(outDir, "cpu"), { recursive: true });
	mkdirSync(join(outDir, "fixtures_bytes"), { recursive: true });

	console.log(`redline_speed_bench: collecting up to ${fixtureCount} fixtures`);
	console.log(`  dirs:\n    ${fixturesDirs.join("\n    ")}`);
	const fixtures = collectFixtures(fixturesDirs, fixtureCount);
	console.log(`  unique fixtures: ${fixtures.length} (target ${fixtureCount})`);
	if (fixtures.length < 2) {
		throw new Error("need ≥2 unique fixtures");
	}
	if (fixtures.length < fixtureCount) {
		console.warn(
			`  ⚠ only ${fixtures.length} unique fixtures available (asked ${fixtureCount})`,
		);
	}

	const tLoad0 = performance.now();
	const bytes = new Map<string, Uint8Array>();
	const bytesDir = join(outDir, "fixtures_bytes");
	let totalBytes = 0;
	for (const fx of fixtures) {
		const buf = new Uint8Array(readFileSync(fx.path));
		bytes.set(fx.name, buf);
		// Persist for samply inner worker (same names as Map keys).
		writeFileSync(join(bytesDir, fx.name), buf);
		totalBytes += buf.byteLength;
	}
	const loadMs = performance.now() - tLoad0;
	console.log(
		`  loaded ${(totalBytes / 1024 / 1024).toFixed(1)} MiB in ${round(loadMs)}ms`,
	);

	const names = fixtures.map((f) => f.name);
	const pairs = buildPairs(names, bytes, minPairs, seed);
	console.log(
		`  pairs=${pairs.length} (min=${minPairs}, seed=${seed}, rounds≈${(pairs[pairs.length - 1]?.round ?? 0) + 1})`,
	);
	console.log(
		`  methods=${methods.join(", ")} warmup=${warmup} reps=${reps} profile=${!skipProfile}`,
	);
	console.log(`  jubarte-dist=${jubarteDist}`);
	console.log(`  rust-dist=${rustDist}`);
	console.log(`  csharp-dist=${csharpDist}`);
	console.log(`  csharp-inproc-dist=${csharpInprocDist}`);
	console.log(`  rust-inproc-dist=${rustInprocDist}`);
	console.log(`  wasm-dist=${wasmDist}`);
	console.log(`  out=${outDir}\n`);

	const pairsMeta = {
		seed,
		minPairs,
		fixtureCount: fixtures.length,
		fixtureTarget: fixtureCount,
		fixturesDirs,
		pairCount: pairs.length,
		pairs: pairs.map((p) => ({
			key: p.key,
			base: p.baseName,
			next: p.nextName,
			round: p.round,
		})),
		fixtures: fixtures.map((f) => ({
			name: f.name,
			path: f.path,
			sha1: f.sha1,
		})),
	};
	const pairsMetaPath = join(outDir, "pairs.json");
	writeFileSync(pairsMetaPath, JSON.stringify(pairsMeta, null, 2));

	const runTs = new Date().toISOString();
	const rows: Record<string, unknown>[] = [];
	const jsonlPath = join(outDir, "speed.jsonl");
	const distOpts = {
		jubarteDist,
		rustDist,
		csharpDist,
		csharpInprocDist,
		rustInprocDist,
		wasmDist,
	};

	for (const method of methods) {
		const engId = engineMethodId(method);
		const dist = distFor(engId, distOpts);
		const native = isNativeCliMethod(method);
		process.stdout.write(
			`▶ ${method} (engine=${engId}, dist=${dist}, native=${native})\n`,
		);

		const tInit0 = performance.now();
		let engine: (base: Uint8Array, next: Uint8Array) => Promise<Uint8Array>;
		try {
			engine = await loadEngine(engId, dist);
		} catch (e) {
			console.error(`  INIT FAILED: ${(e as Error).message}`);
			rows.push({
				schema: 1,
				kind: "redline_speed_bench",
				tool: method,
				engine: engId,
				error: (e as Error).message,
				run_ts: runTs,
			});
			continue;
		}
		const initMs = performance.now() - tInit0;
		console.log(`  init ${round(initMs)}ms`);

		let samples: number[] = [];
		let failures: { key: string; error: string }[] = [];
		let outSizes: number[] = [];
		let wallMs = 0;
		let profilePath: string | null = null;
		let profileTool: string | null = null;
		let hot: ReturnType<typeof analyzeCpuProfile> | null = null;

		const useSamply = !skipProfile && usesSamplyProfile(method);
		const useV8 = !skipProfile && !usesSamplyProfile(method);

		if (useSamply) {
			const samplyOut = join(outDir, "cpu", `${method}.profile.json.gz`);
			const samplesPath = join(outDir, "cpu", `${method}.samples.json`);
			const profileKeys =
				profileSubset > 0
					? pairs.slice(0, profileSubset).map((p) => p.key)
					: pairs.map((p) => p.key);
			console.log(
				`  profiling with samply (${profileKeys.length} pairs, rate=1000Hz)…`,
			);
			// Primary path: timed loop runs under samply so child CLIs are in the profile.
			const pr = runUnderSamply({
				method,
				engId,
				dist,
				pairsMetaPath,
				bytesDir,
				pairKeys: profileKeys,
				warmup,
				reps,
				profilePath: samplyOut,
				samplesPath,
				keysPath: join(outDir, "cpu", `${method}.profile_keys.json`),
			});
			if (pr.ok && existsSync(samplesPath)) {
				const body = JSON.parse(readFileSync(samplesPath, "utf8")) as {
					samples: number[];
					failures: { key: string; error: string }[];
					outSizes: number[];
					wallMs: number;
				};
				samples = body.samples;
				failures = body.failures;
				outSizes = body.outSizes;
				wallMs = body.wallMs;
				profilePath = samplyOut;
				profileTool = "samply";
			} else {
				console.warn(
					`  samply path failed (${pr.error ?? "no samples"}) — falling back to unprofiled loop`,
				);
				const timed = await timedLoop(engine, pairs, reps, warmup);
				samples = timed.samples;
				failures = timed.failures;
				outSizes = timed.outSizes;
				wallMs = timed.wallMs;
			}
		} else {
			const { result: timed, profile } = await withV8CpuProfile(
				useV8,
				async () => timedLoop(engine, pairs, reps, warmup),
			);
			samples = timed.samples;
			failures = timed.failures;
			outSizes = timed.outSizes;
			wallMs = timed.wallMs;
			if (profile) {
				profilePath = join(outDir, "cpu", `${method}.cpuprofile`);
				writeFileSync(profilePath, JSON.stringify(profile));
				hot = analyzeCpuProfile(
					profile as Parameters<typeof analyzeCpuProfile>[0],
				);
				writeFileSync(
					join(outDir, "cpu", `${method}.hot.json`),
					JSON.stringify(hot, null, 2),
				);
				profileTool = "v8-inspector";
			}
		}

		if (samples.length === 0) {
			console.error(
				`  ALL ${failures.length} calls failed — sample: ${failures[0]?.error}`,
			);
			rows.push({
				schema: 1,
				kind: "redline_speed_bench",
				tool: method,
				engine: engId,
				init_ms: round(initMs),
				failures: failures.length,
				error: "all calls failed",
				sample_error: failures[0]?.error,
				run_ts: runTs,
			});
			continue;
		}

		const st = stats(samples);
		const row = {
			schema: 1,
			kind: "redline_speed_bench",
			tool: method,
			engine: engId,
			dist,
			runtime:
				engId === "docxodus-csharp" || engId === "docxodus-csharp-inproc"
					? "dotnet"
					: engId === "jubarte-rust" || engId === "jubarte-rust-inproc"
						? "rust"
						: engId === "docxodus"
							? "dotnet-wasm"
							: engId === "jubarte-wasm"
								? "rust-wasm"
								: "node",
			run_ts: runTs,
			seed,
			fixture_count: fixtures.length,
			fixture_target: fixtureCount,
			pair_count: pairs.length,
			reps,
			warmup,
			init_ms: round(initMs),
			wall_ms: round(wallMs),
			failures: failures.length,
			unit: "ms_per_redline",
			n: st.n,
			mean: round(st.mean),
			median: round(st.median),
			p90: round(st.p90),
			p95: round(st.p95),
			p99: round(st.p99),
			min: round(st.min),
			max: round(st.max),
			std: round(st.std),
			total_ms: round(st.total),
			throughput_per_s: round(st.throughput_per_s, 1),
			mean_out_bytes: outSizes.length
				? Math.round(outSizes.reduce((a, b) => a + b, 0) / outSizes.length)
				: null,
			profile: profilePath ? basename(profilePath) : null,
			profile_tool: profileTool,
			top_cpu: hot?.top.slice(0, 12) ?? null,
			failure_samples: failures.slice(0, 5),
		};
		rows.push(row);
		appendFileSync(jsonlPath, `${JSON.stringify(row)}\n`);
		// Also append to the global speed trend log.
		const globalSpeed = join(ROOT, "results", "speed.jsonl");
		mkdirSync(dirname(globalSpeed), { recursive: true });
		appendFileSync(
			globalSpeed,
			`${JSON.stringify({ ...row, kind: "speed_redlines" })}\n`,
		);

		console.log(
			`  wall ${round(wallMs / 1000, 2)}s  ` +
				`median ${st.median.toFixed(2)}ms  mean ${st.mean.toFixed(2)}ms  ` +
				`p95 ${st.p95.toFixed(2)}ms  p99 ${st.p99.toFixed(2)}ms  ` +
				`${st.throughput_per_s.toFixed(1)}/s  ` +
				`(n=${st.n}, fail=${failures.length})` +
				(profilePath
					? `  profile=${basename(profilePath)} (${profileTool})`
					: ""),
		);
		if (hot?.top?.length) {
			console.log("  top CPU (self):");
			for (const t of hot.top.slice(0, 8)) {
				const loc = t.url
					? `${basename(t.url)}${t.line != null ? `:${t.line}` : ""}`
					: "";
				console.log(
					`    ${String(t.pct).padStart(5)}%  ${t.name.slice(0, 48)}  ${loc}`,
				);
			}
		}
		console.log("");
		// Drop long-lived workers from this method (esp. init engine under samply
		// path) so they don't leak into the next method / keep the process alive.
		shutdownAllLongLivedWorkers();
	}

	const ok = rows.filter((r) => typeof r.median === "number") as Array<
		Record<string, unknown> & {
			tool: string;
			median: number;
			mean: number;
			throughput_per_s: number;
			p95: number;
			n: number;
			failures: number;
			wall_ms: number;
			init_ms: number;
			profile_tool?: string;
		}
	>;
	ok.sort((a, b) => a.median - b.median);

	const md: string[] = [];
	md.push("# redline_speed_bench (speed_redlines)");
	md.push("");
	md.push(
		`- **fixtures:** ${fixtures.length} unique (target ${fixtureCount}) from ${fixturesDirs.length} dirs`,
	);
	md.push(
		`- **pairs:** ${pairs.length} (every fixture × random partner, seed=${seed}, min=${minPairs})`,
	);
	md.push(`- **warmup:** ${warmup}  **reps:** ${reps}`);
	md.push(`- **run_ts:** ${runTs}`);
	md.push("");
	md.push(
		"| rank | tool | median ms | mean ms | p95 | p99 | /s | wall s | fail | n | profile |",
	);
	md.push(
		"| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
	);
	ok.forEach((r, i) => {
		md.push(
			`| ${i + 1} | ${r.tool} | ${r.median} | ${r.mean} | ${r.p95} | ${(r as { p99?: number }).p99 ?? "—"} | ${r.throughput_per_s} | ${round((r.wall_ms as number) / 1000, 2)} | ${r.failures} | ${r.n} | ${r.profile_tool ?? "—"} |`,
		);
	});
	md.push("");
	md.push("## Profiles");
	md.push("");
	md.push("Native engines use **samply** (open in Firefox Profiler / samply load):");
	md.push("");
	md.push("```bash");
	for (const m of methods) {
		if (isNativeCliMethod(m)) {
			md.push(`samply load ${join(outDir, "cpu", `${m}.profile.json.gz`)}`);
		} else {
			md.push(`npx speedscope ${join(outDir, "cpu", `${m}.cpuprofile`)}`);
		}
	}
	md.push("```");
	md.push("");
	md.push("## Fairness");
	md.push("");
	md.push(
		"- **docxodus-csharp / jubarte-rust:** CLI — **one process per redline** (spawn + I/O + compare). C# pays large .NET cold-start; Rust starts in a few ms.",
	);
	md.push(
		"- **docxodus-csharp-inproc / jubarte-rust-inproc:** **warm process** — same algorithms as the CLIs (`DocxDiffOps.Compare` / `compare_documents`), long-lived stdin worker. **This is the fair algorithm comparison.**",
	);
	md.push(
		"- **docxodus:** npm WASM package (`compareDocuments`) — Mono/.NET WASM in-process after one-time `initialize()`.",
	);
	md.push(
		"- **jubarte-wasm:** canonical jubarte-redlines source via **wasm-pack** + **wasm-opt -O3** (`wasm32-unknown-unknown` + wasm-bindgen). Same `compare_documents` as native Rust, hosted in V8 WASM — fair peer of docxodus WASM.",
	);
	md.push(
		"- **jubarte-native / jubarte-lossless:** in-memory Node Uint8Array compare when included.",
	);
	md.push("");

	writeFileSync(
		join(outDir, "summary.json"),
		JSON.stringify(
			{
				runTs,
				rows,
				fixtures: fixtures.length,
				pairs: pairs.length,
				seed,
				methods,
			},
			null,
			2,
		),
	);
	writeFileSync(join(outDir, "report.md"), md.join("\n"));
	console.log(md.join("\n"));
	console.log(`\n✔ ${join(outDir, "report.md")}`);
	console.log(`✔ ${join(outDir, "summary.json")}`);
	console.log(`✔ ${jsonlPath}`);
	console.log(`✔ results/speed.jsonl (appended kind=speed_redlines)`);
}

// Only auto-run when executed as a script (not when vitest imports helpers).
const isDirectRun =
	typeof process.argv[1] === "string" &&
	(process.argv[1].endsWith("redline_speed_bench.ts") ||
		process.argv[1].endsWith("redline_speed_bench.js"));
if (isDirectRun) {
	main().catch((err) => {
		console.error(err);
		process.exit(1);
	});
}
