// SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
//
// SPDX-License-Identifier: AGPL-3.0-only

import { createHash } from "node:crypto";
import {
	existsSync,
	mkdirSync,
	readFileSync,
	statSync,
	writeFileSync,
} from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";
import { performance } from "node:perf_hooks";
import { fileURLToPath } from "node:url";

const PAGE_BYTES = 64 * 1024;

export interface PairMeta {
	key: string;
	base: string;
	next: string;
}

export interface PairsFile {
	pairs: PairMeta[];
}

export interface WeightedPair extends PairMeta {
	inputBytes: number;
}

export interface MemoryTracePoint extends WeightedPair {
	beforePages: number;
	afterPages: number;
	grewPages: number;
	elapsedMs: number;
	outputBytes: number;
}

export interface MemoryTraceSummary {
	initialPages: number;
	finalPages: number;
	peakPages: number;
	growEvents: number;
	totalGrownPages: number;
	initialBytes: number;
	finalBytes: number;
	peakBytes: number;
}

export interface WasmAdapter {
	compareDocuments: (
		base: Uint8Array,
		next: Uint8Array,
		author: string,
	) => Uint8Array;
	initPanicHook?: () => void;
	wasmMemoryPages?: () => number;
}

export interface MemoryTraceRuntime {
	fixtureSize: (name: string) => number;
	readFixture: (name: string) => Uint8Array;
	now: () => number;
}

export interface MemoryTraceRun {
	selectedPairs: number;
	summary: MemoryTraceSummary;
	points: MemoryTracePoint[];
}

export interface MemoryTraceReport extends MemoryTraceRun {
	wasmDist: string;
	wasmSha256: string;
	pageBytes: number;
}

export interface MemoryTraceCliDependencies {
	exists: (path: string) => boolean;
	readText: (path: string) => string;
	fixtureSize: (path: string) => number;
	readFixture: (path: string) => Uint8Array;
	loadWasm: (path: string) => WasmAdapter;
	now: () => number;
	sha256: (path: string) => string;
	writeReport: (path: string, contents: string) => void;
	log: (message: string) => void;
}

export function option(
	args: string[],
	flag: string,
	fallback: string,
): string {
	const index = args.indexOf(flag);
	return index >= 0 && index + 1 < args.length
		? args[index + 1]!
		: fallback;
}

export function selectHeaviestPairs(
	pairs: PairMeta[],
	byteSizes: ReadonlyMap<string, number>,
	limit: number,
): WeightedPair[] {
	if (!Number.isInteger(limit) || limit < 1) {
		throw new Error(`limit must be a positive integer, got ${limit}`);
	}
	return pairs
		.map((pair) => {
			const baseBytes = byteSizes.get(pair.base);
			const nextBytes = byteSizes.get(pair.next);
			if (baseBytes === undefined || nextBytes === undefined) {
				throw new Error(`missing fixture bytes for pair ${pair.key}`);
			}
			return { ...pair, inputBytes: baseBytes + nextBytes };
		})
		.sort((a, b) => b.inputBytes - a.inputBytes || a.key.localeCompare(b.key))
		.slice(0, limit);
}

export function summarizeMemoryTrace(
	initialPages: number,
	points: MemoryTracePoint[],
): MemoryTraceSummary {
	const finalPages = points.at(-1)?.afterPages ?? initialPages;
	const peakPages = points.reduce(
		(peak, point) => Math.max(peak, point.beforePages, point.afterPages),
		initialPages,
	);
	return {
		initialPages,
		finalPages,
		peakPages,
		growEvents: points.filter((point) => point.grewPages > 0).length,
		totalGrownPages: finalPages - initialPages,
		initialBytes: initialPages * PAGE_BYTES,
		finalBytes: finalPages * PAGE_BYTES,
		peakBytes: peakPages * PAGE_BYTES,
	};
}

export function resolveModule(
	wasmDist: string,
	exists: (path: string) => boolean = existsSync,
): string {
	const candidates = [
		join(wasmDist, "pkg", "jubarte_wasm.js"),
		join(wasmDist, "jubarte_wasm.js"),
	];
	const found = candidates.find((candidate) => exists(candidate));
	if (!found) {
		throw new Error(`no jubarte_wasm.js under ${wasmDist}`);
	}
	return found;
}

function fileSha256(path: string): string {
	return createHash("sha256").update(readFileSync(path)).digest("hex");
}

export function traceMemory(
	pairsFile: PairsFile,
	limit: number,
	wasm: WasmAdapter,
	runtime: MemoryTraceRuntime,
): MemoryTraceRun {
	const fixtureNames = new Set(
		pairsFile.pairs.flatMap((pair) => [pair.base, pair.next]),
	);
	const byteSizes = new Map(
		[...fixtureNames].map((name) => [name, runtime.fixtureSize(name)]),
	);
	const selected = selectHeaviestPairs(pairsFile.pairs, byteSizes, limit);

	wasm.initPanicHook?.();
	const memoryPages = wasm.wasmMemoryPages;
	if (typeof memoryPages !== "function") {
		throw new Error(
			"diagnostic artifact lacks wasmMemoryPages; rebuild with --features memory-metrics",
		);
	}

	const initialPages = memoryPages();
	const points: MemoryTracePoint[] = [];
	for (const pair of selected) {
		const base = runtime.readFixture(pair.base);
		const next = runtime.readFixture(pair.next);
		const beforePages = memoryPages();
		const started = runtime.now();
		const output = wasm.compareDocuments(base, next, "wasm-memory-trace");
		const elapsedMs = runtime.now() - started;
		const afterPages = memoryPages();
		points.push({
			...pair,
			beforePages,
			afterPages,
			grewPages: afterPages - beforePages,
			elapsedMs,
			outputBytes: output.byteLength,
		});
	}

	return {
		selectedPairs: selected.length,
		summary: summarizeMemoryTrace(initialPages, points),
		points,
	};
}

export function runMemoryTraceCli(
	args: string[],
	dependencies: MemoryTraceCliDependencies,
): MemoryTraceReport {
	const wasmDist = resolve(option(args, "--wasm-dist", ""));
	const pairsPath = resolve(option(args, "--pairs", ""));
	const bytesDir = resolve(
		option(args, "--bytes-dir", join(dirname(pairsPath), "fixtures_bytes")),
	);
	const outPath = resolve(option(args, "--out", "wasm-memory-trace.json"));
	const limit = Number(option(args, "--limit", "20"));

	const pairsFile = JSON.parse(dependencies.readText(pairsPath)) as PairsFile;
	const modulePath = resolveModule(wasmDist, dependencies.exists);
	const wasm = dependencies.loadWasm(modulePath);
	const run = traceMemory(pairsFile, limit, wasm, {
		fixtureSize: (name) => dependencies.fixtureSize(join(bytesDir, name)),
		readFixture: (name) => dependencies.readFixture(join(bytesDir, name)),
		now: dependencies.now,
	});

	const wasmPath = join(dirname(modulePath), "jubarte_wasm_bg.wasm");
	const report: MemoryTraceReport = {
		wasmDist,
		wasmSha256: dependencies.sha256(wasmPath),
		pageBytes: PAGE_BYTES,
		...run,
	};
	dependencies.writeReport(outPath, `${JSON.stringify(report, null, 2)}\n`);
	dependencies.log(JSON.stringify(report.summary, null, 2));
	dependencies.log(`trace: ${outPath}`);
	return report;
}

function main(): void {
	const req = createRequire(import.meta.url);
	runMemoryTraceCli(process.argv, {
		exists: existsSync,
		readText: (path) => readFileSync(path, "utf8"),
		fixtureSize: (path) => statSync(path).size,
		readFixture: (path) => new Uint8Array(readFileSync(path)),
		loadWasm: (path) => req(path) as WasmAdapter,
		now: () => performance.now(),
		sha256: fileSha256,
		writeReport: (path, contents) => {
			mkdirSync(dirname(path), { recursive: true });
			writeFileSync(path, contents);
		},
		log: console.log,
	});
}

const invokedPath = process.argv[1] ? resolve(process.argv[1]) : "";
if (invokedPath === fileURLToPath(import.meta.url)) {
	main();
}
