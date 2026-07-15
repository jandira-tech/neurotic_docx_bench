import { describe, it, expect } from "vitest";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import JSZip from "../src/neurotic_docx_bench/utils/docx-redline-js/node_modules/jszip/lib/index.js";
import { loadEngine } from "./generate-native-redlines.ts";
import {
	buildPairs,
	collectFixtures,
	defaultCsharpDist,
	defaultCsharpInprocDist,
	defaultRustInprocDist,
	engineMethodId,
	isNativeCliMethod,
	mulberry32,
	stats,
} from "./redline_speed_bench.ts";

const SOURCE = "corpus/word_based/docx_source";
const haveCorpus = existsSync(SOURCE);

const csharpDist = defaultCsharpDist(process.cwd());
const haveCsharp = existsSync(join(csharpDist, "redline"));
const csharpInprocDist = defaultCsharpInprocDist(process.cwd());
const haveCsharpInproc = existsSync(join(csharpInprocDist, "docxodus-inproc"));
const rustDist = existsSync(
	"src/neurotic_docx_bench/utils/jubarte/jubarte-rust/redline",
)
	? "src/neurotic_docx_bench/utils/jubarte/jubarte-rust"
	: "jubarte-rs-probe";
const haveRust = existsSync(join(rustDist, "redline"));
const rustInprocDist = defaultRustInprocDist(process.cwd());
const haveRustInproc =
	existsSync(join(rustInprocDist, "jubarte-worker")) ||
	existsSync(join(rustInprocDist, "jubarte-inproc"));

const FIXTURE_DIRS = [
	"corpus/word_based/docx_source",
	"corpus/word_based/docx_source_randomized",
	"corpus/word_based/docx_accepted_word",
	"corpus/no_comments_pdf_was_generated_by_word/docx_source",
	"corpus/no_comments_pdf_was_generated_by_word/docx_accepted_word",
	"corpus/word_based/docx_redlines_word",
	"corpus/no_comments_pdf_was_generated_by_word/docx_redlines_word",
];

async function documentXml(bytes: Uint8Array): Promise<string> {
	const zip = await JSZip.loadAsync(bytes);
	return zip.file("word/document.xml")!.async("string");
}

function twoSources(): string[] {
	return readdirSync(SOURCE)
		.filter((f) => f.endsWith(".docx") && !f.startsWith("~$"))
		.slice(0, 2)
		.map((f) => join(SOURCE, f));
}

describe("redline_speed_bench helpers", () => {
	it("engineMethodId maps csharp / rust / wasm aliases", () => {
		expect(engineMethodId("docxodus-csharp")).toBe("docxodus-csharp");
		expect(engineMethodId("docxodus-cs")).toBe("docxodus-csharp");
		expect(engineMethodId("docxodus-csharp-inproc")).toBe(
			"docxodus-csharp-inproc",
		);
		expect(engineMethodId("jubarte-rust-inproc")).toBe("jubarte-rust-inproc");
		expect(engineMethodId("docxodus-wasm")).toBe("docxodus");
		expect(engineMethodId("jubarte-rust")).toBe("jubarte-rust");
		expect(isNativeCliMethod("docxodus-csharp")).toBe(true);
		expect(isNativeCliMethod("docxodus-csharp-inproc")).toBe(false);
		expect(isNativeCliMethod("jubarte-rust-inproc")).toBe(false);
		expect(isNativeCliMethod("docxodus")).toBe(false);
		expect(isNativeCliMethod("jubarte-rust")).toBe(true);
		expect(isNativeCliMethod("jubarte-native")).toBe(false);
	});

	it("mulberry32 is deterministic", () => {
		const a = mulberry32(42);
		const b = mulberry32(42);
		expect([a(), a(), a()]).toEqual([b(), b(), b()]);
	});

	it("stats computes full distribution", () => {
		const s = stats([1, 2, 3, 4, 100]);
		expect(s.n).toBe(5);
		expect(s.min).toBe(1);
		expect(s.max).toBe(100);
		expect(s.median).toBe(3);
		expect(s.throughput_per_s).toBeGreaterThan(0);
	});

	it("buildPairs reaches minPairs with every fixture as base", () => {
		const names = ["a.docx", "b.docx", "c.docx"];
		const bytes = new Map(
			names.map((n) => [n, new Uint8Array([1, 2, 3])] as const),
		);
		const pairs = buildPairs(names, bytes, 10, 7);
		expect(pairs.length).toBe(10);
		const r0Bases = pairs.filter((p) => p.round === 0).map((p) => p.baseName);
		expect(new Set(r0Bases).size).toBe(3);
		expect(pairs.every((p) => p.baseName !== p.nextName)).toBe(true);
	});

	it.runIf(haveCorpus)(
		"collectFixtures gathers unique-by-content fixtures up to target",
		() => {
			const fx = collectFixtures(
				[
					"corpus/word_based/docx_source",
					"corpus/word_based/docx_accepted_word",
				],
				50,
			);
			expect(fx.length).toBe(50);
			expect(new Set(fx.map((f) => f.sha1)).size).toBe(50);
		},
	);

	it.runIf(haveCorpus)(
		"collectFixtures can reach 1000 unique when enough corpus exists",
		() => {
			const fx = collectFixtures(FIXTURE_DIRS, 1000);
			expect(fx.length).toBeGreaterThanOrEqual(1000);
			expect(new Set(fx.map((f) => f.sha1)).size).toBe(fx.length);
		},
	);
});

describe("docxodus-csharp engine", () => {
	it.runIf(haveCorpus && haveCsharp)(
		"produces a redline docx with tracked changes via native C# CLI",
		async () => {
			const sources = twoSources();
			expect(sources.length).toBe(2);
			const engine = await loadEngine("docxodus-csharp", csharpDist);
			const out = await engine(
				new Uint8Array(readFileSync(sources[0]!)),
				new Uint8Array(readFileSync(sources[1]!)),
			);
			expect(out).toBeInstanceOf(Uint8Array);
			expect(out.length).toBeGreaterThan(500);
			const xml = await documentXml(out);
			expect(xml.includes("<w:ins") || xml.includes("<w:del")).toBe(true);
		},
		30_000,
	);

	it.runIf(haveCorpus && haveCsharpInproc)(
		"produces a redline via long-lived in-process C# worker",
		async () => {
			const sources = twoSources();
			expect(sources.length).toBe(2);
			const engine = await loadEngine(
				"docxodus-csharp-inproc",
				csharpInprocDist,
			);
			const out = await engine(
				new Uint8Array(readFileSync(sources[0]!)),
				new Uint8Array(readFileSync(sources[1]!)),
			);
			expect(out).toBeInstanceOf(Uint8Array);
			expect(out.length).toBeGreaterThan(500);
			const xml = await documentXml(out);
			expect(xml.includes("<w:ins") || xml.includes("<w:del")).toBe(true);
		},
		30_000,
	);
});

describe("jubarte-rust engine (speed bench path)", () => {
	it.runIf(haveCorpus && haveRust)(
		"produces a redline docx with tracked changes via Rust CLI",
		async () => {
			const sources = twoSources();
			expect(sources.length).toBe(2);
			const engine = await loadEngine("jubarte-rust", rustDist);
			const out = await engine(
				new Uint8Array(readFileSync(sources[0]!)),
				new Uint8Array(readFileSync(sources[1]!)),
			);
			expect(out).toBeInstanceOf(Uint8Array);
			expect(out.length).toBeGreaterThan(500);
			const xml = await documentXml(out);
			expect(xml.includes("<w:ins") || xml.includes("<w:del")).toBe(true);
		},
		30_000,
	);

	it.runIf(haveCorpus && haveRustInproc)(
		"produces a redline via long-lived warm jubarte-inproc worker",
		async () => {
			const sources = twoSources();
			expect(sources.length).toBe(2);
			const engine = await loadEngine(
				"jubarte-rust-inproc",
				rustInprocDist,
			);
			const out = await engine(
				new Uint8Array(readFileSync(sources[0]!)),
				new Uint8Array(readFileSync(sources[1]!)),
			);
			expect(out).toBeInstanceOf(Uint8Array);
			expect(out.length).toBeGreaterThan(500);
			const xml = await documentXml(out);
			expect(xml.includes("<w:ins") || xml.includes("<w:del")).toBe(true);
		},
		30_000,
	);
});

describe("speed_redlines pair plan", () => {
	it.runIf(haveCorpus)(
		"1000 fixtures × buildPairs yields exactly 5000 pairs",
		() => {
			const fx = collectFixtures(FIXTURE_DIRS, 1000);
			expect(fx.length).toBeGreaterThanOrEqual(1000);
			const slice = fx.slice(0, 1000);
			const bytes = new Map(
				slice.map((f) => [f.name, new Uint8Array([0])] as const),
			);
			const pairs = buildPairs(
				slice.map((f) => f.name),
				bytes,
				5000,
				42,
			);
			expect(pairs.length).toBe(5000);
		},
	);
});
