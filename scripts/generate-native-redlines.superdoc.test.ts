/**
 * superdoc-ts adapter — SDK resolution + the Document Engine diff flow.
 *
 * Separate from generate-native-redlines.test.ts on purpose: that file imports jszip
 * through utils/docx-redline-js/node_modules, a sub-install that is not present in every
 * checkout, so the whole suite fails to load when it is missing. These tests only need
 * the root-level deps.
 */
import { describe, it, expect } from "vitest";
import {
	existsSync,
	readFileSync,
	writeFileSync,
	mkdtempSync,
	rmSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import JSZip from "jszip";
import {
	parseManifest,
	loadEngine,
	resolveSuperDocSdkDir,
} from "./generate-native-redlines.ts";

const MANIFEST = "corpus/word_based/centralized_mapping.csv";
const SOURCE = "corpus/word_based/docx_source";
const haveCorpus = existsSync(MANIFEST) && existsSync(SOURCE);

async function documentXml(bytes: Uint8Array): Promise<string> {
	const zip = await JSZip.loadAsync(bytes);
	return zip.file("word/document.xml")!.async("string");
}

describe("superdoc-ts SDK resolution", () => {
	// tool_updater.update_npm_package runs `npm install @superdoc-dev/sdk@<pin>` with
	// cwd = repo root (cli.py passes Path.cwd()), so the copy the bench actually
	// benchmarks lands in <repo>/node_modules — NOT utils/superdoc/node_modules.
	// Resolving elsewhere kills the run with ERR_MODULE_NOT_FOUND at engine-load
	// time, before the first pair, and scores the vendor zero.
	it("resolves the copy the tool updater installs (repo-root node_modules)", () => {
		expect(existsSync("node_modules/@superdoc-dev/sdk/package.json")).toBe(true);
		const dir = resolveSuperDocSdkDir();
		expect(dir).toContain("/node_modules/@superdoc-dev/sdk");
		expect(existsSync(join(dir, "package.json"))).toBe(true);
	});

	it("SUPERDOC_SDK_DIR overrides the search order", () => {
		const dir = mkdtempSync(join(tmpdir(), "sdk-override-"));
		try {
			writeFileSync(join(dir, "package.json"), '{"name":"stub","main":"i.js"}');
			expect(resolveSuperDocSdkDir({ SUPERDOC_SDK_DIR: dir })).toBe(dir);
		} finally {
			rmSync(dir, { recursive: true, force: true });
		}
	});

	it("names every candidate it searched when the SDK is absent", () => {
		const empty = mkdtempSync(join(tmpdir(), "sdk-missing-"));
		try {
			expect(() => resolveSuperDocSdkDir({ SUPERDOC_SDK_DIR: join(empty, "nope") }))
				.toThrow(/@superdoc-dev\/sdk/);
		} finally {
			rmSync(empty, { recursive: true, force: true });
		}
	});

	it("loadEngine('superdoc-ts') builds an engine instead of throwing", async () => {
		await expect(loadEngine("superdoc-ts", "")).resolves.toBeTypeOf("function");
	}, 60_000);
});

describe("superdoc-ts diff flow", () => {
	it.runIf(haveCorpus)(
		"capture → compare → apply(tracked) → save produces w:ins/w:del",
		async () => {
			const pairs = parseManifest(MANIFEST, ["ok"]);
			const p = pairs.find(
				(x) =>
					existsSync(join(SOURCE, `${x.base}.docx`)) &&
					existsSync(join(SOURCE, `${x.next}.docx`)),
			)!;
			const engine = await loadEngine("superdoc-ts", "");
			const out = await engine(
				new Uint8Array(readFileSync(join(SOURCE, `${p.base}.docx`))),
				new Uint8Array(readFileSync(join(SOURCE, `${p.next}.docx`))),
			);
			expect(out).toBeInstanceOf(Uint8Array);
			expect(out.length).toBeGreaterThan(1000);
			const xml = await documentXml(out);
			expect(xml.includes("<w:ins") || xml.includes("<w:del")).toBe(true);
		},
		120_000,
	);
});
