#!/usr/bin/env bun
/**
 * Folio benchmark generators (Task 9).
 *
 * NOTE: the active ``script_redlines`` redline generator for folio now lives in
 * ``scripts/generate-native-redlines.ts:loadEngine("folio")`` (composes
 * ``@stll/folio-agents.compareDocxVersions`` with
 * ``FolioDocxReviewer.applyOperations({mode:"tracked-changes"})``) and is wired
 * via the ``folio`` run in ``bench.yaml``. The bench invokes it through the
 * shared dispatcher, NOT through this standalone script.
 *
 * This file retains the standalone accept-all / roundtrip scaffolding for
 * routes NOT yet covered by the dispatcher. The bench currently drives
 * accept-changes via the shared Python ``accept_changes.py`` path and roundtrips
 * via ``generate-roundtrips*.mjs/py``, so the stubs below are not on the active
 * run path — they remain as a documented seam for future Node-side variants.
 *
 * Folio is npm-pinned (``@stll/folio-core`` / ``@stll/folio-agents`` in
 * package.json) and installed via ``bun install`` — never vendored.
 *
 * Usage: bun run scripts/generate-folio.ts --out=$RUN_DIR/docx --tool=folio [--accept|--roundtrip]
 */

import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { basename, join } from "node:path";

interface FolioResult {
	ok: number;
	fail: number;
	files: string[];
	errors: string[];
}

/**
 * Stub — real implementation needs the npm-pinned folio packages.
 * When folio is wired (add @stll/folio-core to package.json, `bun install`),
 * replace with:
 *
 *   import { FolioDocxReviewer } from "@stll/folio-core/server";
 *   const reviewer = FolioDocxReviewer.fromBuffer(buf);
 *   reviewer.acceptAll();
 *   const out = reviewer.toBuffer();
 */
async function acceptAllFolioChanges(
	_sourceDir: string,
	_outDir: string,
	_opts?: { limit?: number },
): Promise<FolioResult> {
	// Stub: the bench currently drives accept-changes via the shared Python
	// accept_changes.py path, so this Node-side variant is not on the active run
	// path. Implement (import from "@stll/folio-core/server") only if a Node-side
	// accept variant is needed.
	console.warn(
		"generate-folio: folio accept-all not wired (bench uses accept_changes.py)",
	);
	return { ok: 0, fail: 0, files: [], errors: ["not wired"] };
}

async function roundtripFolio(
	_sourceDir: string,
	_outDir: string,
	_opts?: { limit?: number },
): Promise<FolioResult> {
	console.warn(
		"generate-folio: folio roundtrip not wired (bench uses generate-roundtrips.mjs)",
	);
	return { ok: 0, fail: 0, files: [], errors: ["not wired"] };
}

/** Parse CLI args minimally — real wiring will replace this. */
function parseArgs(): {
	out: string;
	tool: string;
	mode: "accept" | "roundtrip";
	runDir: string;
	sourceDir: string;
} {
	const args = process.argv.slice(2);
	const get = (flag: string) => {
		const idx = args.indexOf(flag);
		return idx >= 0 ? args[idx + 1] : "";
	};
	const mode = args.includes("--accept")
		? "accept"
		: args.includes("--roundtrip")
			? "roundtrip"
			: "roundtrip";
	return {
		out: get("--out") || "out/folio",
		tool: get("--tool") || "folio",
		mode,
		runDir: get("--run-dir") || "",
		sourceDir: get("--source") || "corpus/word_based/docx_source",
	};
}

// Self-executing. Gated behind an explicit env-var opt-in: the stubs below
// are not real generators (they return errors=["not wired"]), so if this script
// were accidentally wired into bench.yaml or generate-native-redlines.ts it
// would flood generate_failures.json and trip the gate's below_50 counters on
// every pair. Refuse to run unless BENCH_FOLIO_STUBS=1 is set.
const isMain = import.meta.main;
if (isMain) {
	if (process.env.BENCH_FOLIO_STUBS !== "1") {
		console.error(
			"generate-folio: stubs are not wired (return 'not wired' for every pair). " +
				"Set BENCH_FOLIO_STUBS=1 to run anyway, or use the real folio engine via " +
				"scripts/generate-native-redlines.ts:loadEngine('folio').",
		);
		process.exit(2);
	}
	const opts = parseArgs();
	const result =
		opts.mode === "accept"
			? await acceptAllFolioChanges(opts.sourceDir, opts.out)
			: await roundtripFolio(opts.sourceDir, opts.out);

	// Write generate_failures.json if any failures
	if (opts.runDir && result.errors.length > 0) {
		const failuresPath = join(opts.runDir, "generate_failures.json");
		const failures = result.errors.map((err, i) => ({
			doc: `folio_${i}`,
			stage: "generate",
			error: err,
		}));
		writeFileSync(failuresPath, JSON.stringify(failures, null, 2));
	}

	console.log(`folio ${opts.mode}: ${result.ok} ok, ${result.fail} fail`);
}
