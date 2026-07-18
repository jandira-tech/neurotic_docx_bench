// SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
//
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, expect, it } from "vitest";

import {
	option,
	resolveModule,
	runMemoryTraceCli,
	selectHeaviestPairs,
	summarizeMemoryTrace,
	traceMemory,
	type MemoryTracePoint,
} from "./wasm-memory-trace.ts";

describe("wasm memory trace helpers", () => {
	it("selects the largest pair deterministically", () => {
		const pairs = [
			{ key: "z", base: "small", next: "medium" },
			{ key: "b", base: "large", next: "medium" },
			{ key: "a", base: "medium", next: "large" },
		];
		const sizes = new Map([
			["small", 1],
			["medium", 10],
			["large", 100],
		]);

		expect(selectHeaviestPairs(pairs, sizes, 2)).toEqual([
			{ ...pairs[2], inputBytes: 110 },
			{ ...pairs[1], inputBytes: 110 },
		]);
	});

	it("rejects invalid limits and missing fixture sizes", () => {
		expect(() => selectHeaviestPairs([], new Map(), 0)).toThrow(
			"positive integer",
		);
		expect(() =>
			selectHeaviestPairs(
				[{ key: "missing", base: "a", next: "b" }],
				new Map([["a", 1]]),
				1,
			),
		).toThrow("missing fixture bytes");
	});

	it("summarizes page growth and byte high-water", () => {
		const base = {
			key: "pair",
			base: "a",
			next: "b",
			inputBytes: 2,
			elapsedMs: 1,
			outputBytes: 1,
		};
		const points: MemoryTracePoint[] = [
			{ ...base, beforePages: 17, afterPages: 20, grewPages: 3 },
			{ ...base, beforePages: 20, afterPages: 20, grewPages: 0 },
			{ ...base, beforePages: 20, afterPages: 24, grewPages: 4 },
		];

		expect(summarizeMemoryTrace(17, points)).toEqual({
			initialPages: 17,
			finalPages: 24,
			peakPages: 24,
			growEvents: 2,
			totalGrownPages: 7,
			initialBytes: 17 * 65_536,
			finalBytes: 24 * 65_536,
			peakBytes: 24 * 65_536,
		});
	});

	it("parses explicit options and falls back for missing values", () => {
		const args = ["node", "trace.ts", "--limit", "7", "--out"];
		expect(option(args, "--limit", "20")).toBe("7");
		expect(option(args, "--out", "trace.json")).toBe("trace.json");
		expect(option(args, "--pairs", "pairs.json")).toBe("pairs.json");
	});

	it("resolves either supported package layout", () => {
		const nested = "/artifact/pkg/jubarte_wasm.js";
		const direct = "/artifact/jubarte_wasm.js";
		expect(resolveModule("/artifact", (path) => path === nested)).toBe(nested);
		expect(resolveModule("/artifact", (path) => path === direct)).toBe(direct);
		expect(() => resolveModule("/missing", () => false)).toThrow(
			"no jubarte_wasm.js",
		);
	});

	it("traces selected pairs with in-memory dependencies", () => {
		const pageReadings = [17, 17, 20, 20, 20];
		const times = [10, 12, 20, 25];
		let initialized = 0;
		const run = traceMemory(
			{
				pairs: [
					{ key: "small", base: "a", next: "b" },
					{ key: "large", base: "b", next: "c" },
				],
			},
			2,
			{
				initPanicHook: () => {
					initialized += 1;
				},
				wasmMemoryPages: () => pageReadings.shift()!,
				compareDocuments: (base, next) =>
					new Uint8Array(base.byteLength + next.byteLength),
			},
			{
				fixtureSize: (name) => ({ a: 1, b: 2, c: 4 })[name]!,
				readFixture: (name) =>
					new Uint8Array(({ a: 1, b: 2, c: 4 })[name]!),
				now: () => times.shift()!,
			},
		);

		expect(initialized).toBe(1);
		expect(run.selectedPairs).toBe(2);
		expect(run.summary).toMatchObject({
			initialPages: 17,
			finalPages: 20,
			peakPages: 20,
			growEvents: 1,
		});
		expect(run.points).toMatchObject([
			{ key: "large", elapsedMs: 2, outputBytes: 6, grewPages: 3 },
			{ key: "small", elapsedMs: 5, outputBytes: 3, grewPages: 0 },
		]);
	});

	it("rejects a non-diagnostic wasm adapter", () => {
		expect(() =>
			traceMemory(
				{ pairs: [] },
				1,
				{ compareDocuments: () => new Uint8Array() },
				{
					fixtureSize: () => 0,
					readFixture: () => new Uint8Array(),
					now: () => 0,
				},
			),
		).toThrow("lacks wasmMemoryPages");
	});

	it("runs the CLI orchestration with in-memory fakes", () => {
		const writes: Array<[string, string]> = [];
		const logs: string[] = [];
		const pageReadings = [17, 17, 18];
		const report = runMemoryTraceCli(
			[
				"node",
				"trace.ts",
				"--wasm-dist",
				"/wasm",
				"--pairs",
				"/data/pairs.json",
				"--out",
				"/results/trace.json",
				"--limit",
				"1",
			],
			{
				exists: (path) => path === "/wasm/pkg/jubarte_wasm.js",
				readText: () =>
					JSON.stringify({
						pairs: [{ key: "pair", base: "a.docx", next: "b.docx" }],
					}),
				fixtureSize: (path) => (path.endsWith("a.docx") ? 1 : 2),
				readFixture: (path) =>
					new Uint8Array(path.endsWith("a.docx") ? 1 : 2),
				loadWasm: () => ({
					wasmMemoryPages: () => pageReadings.shift()!,
					compareDocuments: () => new Uint8Array(4),
				}),
				now: (() => {
					const times = [1, 3];
					return () => times.shift()!;
				})(),
				sha256: () => "abc123",
				writeReport: (path, contents) => writes.push([path, contents]),
				log: (message) => logs.push(message),
			},
		);

		expect(report).toMatchObject({
			wasmDist: "/wasm",
			wasmSha256: "abc123",
			pageBytes: 65_536,
			selectedPairs: 1,
			summary: { initialPages: 17, finalPages: 18 },
		});
		expect(report.points[0]).toMatchObject({
			key: "pair",
			inputBytes: 3,
			elapsedMs: 2,
			outputBytes: 4,
		});
		expect(writes).toHaveLength(1);
		expect(writes[0]?.[0]).toBe("/results/trace.json");
		expect(JSON.parse(writes[0]![1])).toEqual(report);
		expect(logs.at(-1)).toBe("trace: /results/trace.json");
	});
});
