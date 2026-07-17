import { describe, expect, it } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join, resolve } from "node:path";
import { parseManifest } from "./generate-native-redlines.ts";

// §14.0 export contract (DOCX-ENGINE-RECONCILIATION-PLAN.md): the wasm adapter
// must expose the full four-function surface folio-core's RedlineEngine port
// consumes — compareDocuments, acceptRevisions, rejectRevisions, getRevisions.
// getRevisions returns a JSON array string in the same object shape as the CLI
// `jubarte revisions --json` lines.

const PKG = resolve(
	"src/neurotic_docx_bench/utils/jubarte/jubarte-wasm/pkg/jubarte_wasm.js",
);
const MANIFEST = "corpus/word_based/centralized_mapping.csv";
const SOURCE = "corpus/word_based/docx_source";
const havePkg = existsSync(PKG);
const haveCorpus = existsSync(MANIFEST) && existsSync(SOURCE);

const loadWasm = (): Record<string, unknown> => {
	const req = createRequire(import.meta.url);
	const mod = req(PKG);
	if (typeof mod.initPanicHook === "function") mod.initPanicHook();
	return mod;
};

describe.runIf(havePkg)("jubarte-wasm export contract", () => {
	it("exposes the four RedlineEngine port functions", () => {
		const mod = loadWasm();
		expect(typeof mod.compareDocuments).toBe("function");
		expect(typeof mod.acceptRevisions).toBe("function");
		expect(typeof mod.rejectRevisions).toBe("function");
		expect(typeof mod.getRevisions).toBe("function");
	});

	it.runIf(haveCorpus)(
		"compare → getRevisions lists revisions; accept-all and reject-all drain them",
		() => {
			const mod = loadWasm() as {
				compareDocuments: (
					a: Uint8Array,
					b: Uint8Array,
					author: string,
				) => Uint8Array;
				acceptRevisions: (docx: Uint8Array) => Uint8Array;
				rejectRevisions: (docx: Uint8Array) => Uint8Array;
				getRevisions: (docx: Uint8Array) => string;
			};
			const pairs = parseManifest(MANIFEST, ["ok"]);
			const p = pairs.find(
				(x) =>
					existsSync(join(SOURCE, `${x.base}.docx`)) &&
					existsSync(join(SOURCE, `${x.next}.docx`)),
			);
			expect(p).toBeTruthy();
			if (!p) return;
			const base = new Uint8Array(readFileSync(join(SOURCE, `${p.base}.docx`)));
			const next = new Uint8Array(readFileSync(join(SOURCE, `${p.next}.docx`)));

			const redline = mod.compareDocuments(base, next, "contract-test");
			expect(redline.length).toBeGreaterThan(1000);

			const revisions = JSON.parse(mod.getRevisions(redline));
			expect(Array.isArray(revisions)).toBe(true);
			expect(revisions.length).toBeGreaterThan(0);
			for (const r of revisions) {
				// CLI `revisions --json` object shape.
				expect(typeof r.type).toBe("string");
				expect("author" in r).toBe(true);
				expect("date" in r).toBe(true);
				expect("part" in r).toBe(true);
				expect("text" in r).toBe(true);
			}

			// Identity-property corollaries: accept-all and reject-all both yield
			// documents with zero remaining tracked revisions.
			const accepted = mod.acceptRevisions(redline);
			expect(accepted.length).toBeGreaterThan(1000);
			expect(JSON.parse(mod.getRevisions(accepted))).toHaveLength(0);

			const rejected = mod.rejectRevisions(redline);
			expect(rejected.length).toBeGreaterThan(1000);
			expect(JSON.parse(mod.getRevisions(rejected))).toHaveLength(0);
		},
		60_000,
	);
});
