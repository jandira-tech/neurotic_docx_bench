import { describe, it, expect } from "vitest";
import {
	existsSync,
	mkdirSync,
	readFileSync,
	readdirSync,
	mkdtempSync,
	rmSync,
	writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import JSZip from "../node_modules/jszip/lib/index.js";
import { parseManifest, loadEngine, runBatch } from "./generate-native-redlines.ts";

const MANIFEST = "corpus/word_based/centralized_mapping.csv";
const SOURCE = "corpus/word_based/docx_source";
const STEMMA_DIST = "src/neurotic_docx_bench/utils/stemma";
const SAFE_DIST = "src/neurotic_docx_bench/utils/safe-docx-compare";
const STEMMA_BIN = join(STEMMA_DIST, "stemma");
const SAFE_ENTRY = join(
	SAFE_DIST,
	"node_modules/@usejunior/docx-compare/dist/index.js",
);
const haveCorpus = existsSync(MANIFEST) && existsSync(SOURCE);
const haveStemma = existsSync(STEMMA_BIN);
const haveSafeDocx = existsSync(SAFE_ENTRY);

async function documentXml(bytes: Uint8Array): Promise<string> {
	const zip = await JSZip.loadAsync(bytes);
	const doc = zip.file("word/document.xml");
	if (!doc) throw new Error("missing word/document.xml");
	return doc.async("string");
}

/** First corpus pair whose base and next DOCX both exist and differ. */
function firstDifferingPair() {
	const pairs = parseManifest(MANIFEST, ["ok"]);
	for (const x of pairs) {
		const bp = join(SOURCE, `${x.base}.docx`);
		const np = join(SOURCE, `${x.next}.docx`);
		if (!existsSync(bp) || !existsSync(np)) continue;
		const a = readFileSync(bp);
		const b = readFileSync(np);
		if (a.equals(b)) continue;
		return {
			pair: x,
			base: new Uint8Array(a),
			next: new Uint8Array(b),
		};
	}
	throw new Error("no differing corpus pair on disk");
}

function writeTinyManifest(
	dir: string,
	rows: Array<{ base: string; next: string }>,
): string {
	const path = join(dir, "manifest.csv");
	const body = ["base,next", ...rows.map((r) => `${r.base},${r.next}`)].join(
		"\n",
	);
	writeFileSync(path, body);
	return path;
}

describe("stemma + safe-docx shipped compare", () => {
	it.runIf(haveCorpus && haveStemma)(
		"stemma compare on a real corpus pair emits native w:ins/w:del",
		async () => {
			const { base, next } = firstDifferingPair();
			const engine = await loadEngine("stemma", STEMMA_DIST);
			const out = await engine(base, next);
			expect(out).toBeInstanceOf(Uint8Array);
			expect(out.length).toBeGreaterThan(1000);
			const xml = await documentXml(out);
			expect(xml.includes("<w:ins") || xml.includes("<w:del")).toBe(true);
		},
		60_000,
	);

	it.runIf(haveCorpus && haveSafeDocx)(
		"safe-docx compareDocuments on a real corpus pair emits native w:ins/w:del",
		async () => {
			const { base, next } = firstDifferingPair();
			const engine = await loadEngine("safe-docx", SAFE_DIST);
			const out = await engine(base, next);
			expect(out).toBeInstanceOf(Uint8Array);
			expect(out.length).toBeGreaterThan(1000);
			const xml = await documentXml(out);
			expect(xml.includes("<w:ins") || xml.includes("<w:del")).toBe(true);
		},
		60_000,
	);

	it.runIf(haveCorpus && haveStemma)(
		"stemma runBatch records a pair failure and continues",
		async () => {
			const { pair } = firstDifferingPair();
			const work = mkdtempSync(join(tmpdir(), "stemma-batch-"));
			try {
				const sourceDir = join(work, "src");
				mkdirSync(sourceDir);
				writeFileSync(
					join(sourceDir, `${pair.base}.docx`),
					readFileSync(join(SOURCE, `${pair.base}.docx`)),
				);
				writeFileSync(
					join(sourceDir, `${pair.next}.docx`),
					readFileSync(join(SOURCE, `${pair.next}.docx`)),
				);
				const manifest = writeTinyManifest(work, [
					{ base: pair.base, next: pair.next },
					{ base: "missing_base_zzz", next: "missing_next_zzz" },
				]);
				const out = join(work, "docx");
				const res = await runBatch({
					method: "stemma",
					dist: STEMMA_DIST,
					out,
					runDir: work,
					manifest,
					sourceDir,
					status: "ok",
					tool: "stemma",
					force: true,
				});
				expect(res.ok).toBeGreaterThanOrEqual(1);
				expect(res.failed.some((f) => f.stage === "missing_source")).toBe(
					true,
				);
				expect(
					res.failed.some((f) => f.doc === "missing_base_zzz_missing_next_zzz"),
				).toBe(true);
				const files = readdirSync(out).filter((f) =>
					f.endsWith("_stemma_redline.docx"),
				);
				expect(files.length).toBe(res.ok);
			} finally {
				rmSync(work, { recursive: true, force: true });
			}
		},
		60_000,
	);

	it.runIf(haveCorpus && haveSafeDocx)(
		"safe-docx runBatch records a pair failure and continues",
		async () => {
			const { pair } = firstDifferingPair();
			const work = mkdtempSync(join(tmpdir(), "safe-batch-"));
			try {
				const sourceDir = join(work, "src");
				mkdirSync(sourceDir);
				writeFileSync(
					join(sourceDir, `${pair.base}.docx`),
					readFileSync(join(SOURCE, `${pair.base}.docx`)),
				);
				writeFileSync(
					join(sourceDir, `${pair.next}.docx`),
					readFileSync(join(SOURCE, `${pair.next}.docx`)),
				);
				const manifest = writeTinyManifest(work, [
					{ base: "missing_base_zzz", next: "missing_next_zzz" },
					{ base: pair.base, next: pair.next },
				]);
				const out = join(work, "docx");
				const res = await runBatch({
					method: "safe-docx",
					dist: SAFE_DIST,
					out,
					runDir: work,
					manifest,
					sourceDir,
					status: "ok",
					tool: "safe-docx-compare",
					force: true,
				});
				expect(res.ok).toBeGreaterThanOrEqual(1);
				expect(res.failed.some((f) => f.stage === "missing_source")).toBe(
					true,
				);
				const files = readdirSync(out).filter((f) =>
					f.endsWith("_safe-docx-compare_redline.docx"),
				);
				expect(files.length).toBe(res.ok);
			} finally {
				rmSync(work, { recursive: true, force: true });
			}
		},
		60_000,
	);
});
