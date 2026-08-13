#!/usr/bin/env node
import { execSync } from "node:child_process";
import { createHash } from "node:crypto";
/**
 * Generate genuinely re-serialized DOCX round-trips for every Node-based tool in
 * bench.yaml, over all files in corpus/word_based/word_working_roundtrip.
 *
 * Per-tool roundtrip route (from the re-serialization analysis):
 *
 *   ┌──────────────────────────┬─────────────────────────────────────────┐
 *   │ Tool                     │ Roundtrip route                          │
 *   ├──────────────────────────┼─────────────────────────────────────────┤
 *   │ jubarte-*-native         │ docxToHtml → htmlToDocx                  │
 *   │                          │ (roundtripDocx is a no-op re-zip:        │
 *   │                          │  word/document.xml stays IDENTICAL)      │
 *   │ jubarte-*-docxodus       │ compareDocx(base, base) self-diff        │
 *   │ docxodus                 │ compareDocuments(base, base) self-diff   │
 *   │ docx-redline-js          │ soffice docx→html→docx                   │
 *   │                          │ (no HTML export of its own)              │
 *   │ superdoc-ts              │ client.open() → save()                   │
 *   └──────────────────────────┴─────────────────────────────────────────┘
 *
 * The Python `superdoc` tool is handled by generate-roundtrips-superdoc.py.
 * The `word-redlines-soffice` sanity run is not a roundtrip tool (excluded).
 *
 * For each input file the script:
 *   1. Reads the DOCX bytes and computes word/document.xml MD5.
 *   2. Runs the tool's roundtrip route.
 *   3. Validates the output is a real DOCX (zip + w:document root).
 *   4. Computes the new word/document.xml MD5 and checks whether the XML
 *      was genuinely re-serialized (different MD5) or a no-op (identical).
 *   5. Writes the output to out/roundtrip/<tool>/<original-filename>.
 *   6. Records failures in out/roundtrip/<tool>/generate_failures.json.
 *
 * Usage:
 *   node scripts/generate-roundtrips.mjs --all
 *   BENCH_TOOLS=docxodus,superdoc node scripts/generate-roundtrips.mjs --all   # scoped --all
 *   node scripts/generate-roundtrips.mjs --tool=jubarte-final-native
 *   node scripts/generate-roundtrips.mjs --tool=jubarte-final-lossless --limit 5
 *   node scripts/generate-roundtrips.mjs --tool=docxodus,docx-redline-js --force
 */
import {
	existsSync,
	mkdirSync,
	readdirSync,
	readFileSync,
	rmSync,
	writeFileSync,
} from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { basename, join, resolve } from "node:path";
import { wireJubarteLosslessAdapter } from "./jubarte-lossless-adapter.mjs";

const require = createRequire(import.meta.url);

// ── Tool registry (mirrors bench.yaml runs, excluding Python superdoc and
//    the word-redlines-soffice sanity run) ────────────────────────────────────
const TOOLS = [
	// jubarte final build (dist/jubarte-final)
	{
		tool: "jubarte-final-native",
		dist: "dist/jubarte-final",
		route: "jubarte-native",
	},
	{
		tool: "jubarte-final-lossless",
		dist: "dist/jubarte-final",
		route: "jubarte-lossless",
	},
	// npm tools
	{ tool: "docxodus", dist: null, route: "docxodus" },
	{ tool: "docx-redline-js", dist: null, route: "docx-redline-js" },
	{ tool: "superdoc-ts", dist: null, route: "superdoc-ts" },
	// folio: FolioDocxReviewer.fromBuffer → toBuffer (genuine re-serialization)
	{ tool: "folio", dist: null, route: "folio" },
];

// ── CLI ──────────────────────────────────────────────────────────────────────
function parseArgs(argv) {
	const get = (flag, dflt) => {
		const i = argv.indexOf(flag);
		if (i !== -1 && i + 1 < argv.length) return argv[i + 1];
		const eq = argv.find((a) => a.startsWith(`${flag}=`));
		return eq ? eq.slice(flag.length + 1) : dflt;
	};
	return {
		all: argv.includes("--all"),
		tool: get("--tool", ""),
		sourceDir: get("--source-dir", "corpus/word_based/word_working_roundtrip"),
		out: get("--out", "out/roundtrip"),
		limit: Number(get("--limit", "0")) || 0,
		force: argv.includes("--force"),
	};
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const readBytes = (p) => new Uint8Array(readFileSync(p));

/** Normalise various return shapes into a Uint8Array. */
const toBytes = async (out) => {
	if (out instanceof Uint8Array) return out;
	if (out?.docx instanceof Uint8Array) return out.docx;
	if (out?.bytes instanceof Uint8Array) return out.bytes;
	if (out?.output instanceof Uint8Array) return out.output;
	if (typeof out?.arrayBuffer === "function")
		return new Uint8Array(await out.arrayBuffer());
	if (out?.value instanceof Uint8Array) return out.value;
	return new Uint8Array(out);
};

/** jubarte's NodeDocxInput wrapper. */
const docxIn = (bytes) => ({ buffer: bytes });

/** Resolve `filename` under a build dir, tolerating an extra nested `dist/` level
 *  (some jubarte builds unpack as `<dist>/dist/*.cjs` instead of `<dist>/*.cjs`) —
 *  fail loudly with both checked paths if neither exists. */
function resolveDistFile(distPath, filename) {
	const direct = resolve(distPath, filename);
	if (existsSync(direct)) return direct;
	const nested = resolve(distPath, "dist", filename);
	if (existsSync(nested)) return nested;
	throw new Error(
		`cannot find ${filename} under ${distPath} (checked ${direct} and ${nested})`,
	);
}

/** MD5 of the word/document.xml entry inside a DOCX (Uint8Array). */
async function docXmlMd5(bytes) {
	const JSZip = (
		await import(
			"../src/neurotic_docx_bench/utils/docx-redline-js/node_modules/jszip/lib/index.js"
		)
	).default;
	const zip = await JSZip.loadAsync(bytes);
	const xml = await zip.file("word/document.xml").async("uint8array");
	return createHash("md5").update(xml).digest("hex");
}

/** Quick validity check: is this a plausible DOCX? (zip with word/document.xml) */
async function isValidDocx(bytes) {
	try {
		const JSZip = (
			await import(
				"../src/neurotic_docx_bench/utils/docx-redline-js/node_modules/jszip/lib/index.js"
			)
		).default;
		const zip = await JSZip.loadAsync(bytes);
		const doc = zip.file("word/document.xml");
		if (!doc) return { ok: false, reason: "missing word/document.xml" };
		const xml = await doc.async("string");
		if (!xml.includes("<w:document"))
			return { ok: false, reason: "no <w:document> root" };
		return { ok: true, size: bytes.byteLength };
	} catch (e) {
		return { ok: false, reason: e.message?.slice(0, 120) };
	}
}

/** soffice headless convert; returns output path or null. */
function sofficeConvert(srcPath, fmt, outDir, infilter) {
	outDir = resolve(outDir);
	const expected = join(
		outDir,
		basename(srcPath).replace(/\.[^.]+$/, `.${fmt}`),
	);
	rmSync(expected, { force: true });
	const filterFlag = infilter ? `--infilter='${infilter}' ` : "";
	execSync(
		`soffice --headless ${filterFlag}--convert-to ${fmt} --outdir "${outDir}" "${resolve(srcPath)}"`,
		{ stdio: "pipe", timeout: 60_000 },
	);
	return existsSync(expected) ? expected : null;
}

/** Find all .docx files (excluding ~$ Word lock files) in a directory. */
function findDocxFiles(dir) {
	return readdirSync(dir)
		.filter((f) => f.endsWith(".docx") && !f.startsWith("~$"))
		.sort()
		.map((f) => join(dir, f));
}

// ── Engine loaders ───────────────────────────────────────────────────────────
/**
 * Load a roundtrip engine for the given route.
 * Returns async (inputBytes: Uint8Array) => Promise<Uint8Array>.
 */
async function loadEngine(route, dist) {
	// jubarte-native: docxToHtml → htmlToDocx (genuine re-serialization).
	// roundtripDocx is a no-op re-zip — word/document.xml stays byte-identical —
	// so we route through jubarte's own HTML converter to force re-serialization.
	if (route === "jubarte-native") {
		const mod = await import(resolveDistFile(dist, "node.cjs"));
		return async (input) => {
			const htmlOut = await mod.docxToHtml(docxIn(input));
			const htmlStr =
				typeof htmlOut === "string"
					? htmlOut
					: (htmlOut?.html ?? String(htmlOut));
			return toBytes(await mod.htmlToDocx(htmlStr));
		};
	}

	// jubarte-lossless: DocumentComparer.CompareDocuments(base, base) self-diff, via
	// jubarte's "lossless" WmlComparer port (replaces the old node.cjs compareDocx).
	// The self-diff genuinely re-serializes word/document.xml (different from
	// the input), so the direct route is the right roundtrip.
	if (route === "jubarte-lossless") {
		const losslessPath = resolveDistFile(dist, "lossless.node.cjs");
		const mod = require(losslessPath);
		wireJubarteLosslessAdapter(mod, losslessPath);
		return async (input) => {
			const out = mod.DocumentComparer.CompareDocuments(
				input,
				input,
				"jubarte-lossless",
			);
			const bytes = out instanceof Uint8Array ? out : new Uint8Array(out);
			// CompareDocuments catches its own internal errors and returns an EMPTY
			// array instead of throwing — fail fast rather than write a 0-byte "roundtrip".
			if (bytes.length === 0) {
				throw new Error(
					"jubarte lossless DocumentComparer.CompareDocuments returned empty output " +
						"(comparison failed internally)",
				);
			}
			return bytes;
		};
	}

	// docxodus (npm): compareDocuments(base, base) self-diff.
	// WASM engine; one-time initialize() loads the .NET runtime.
	if (route === "docxodus") {
		const { installDocxodusNodeCompat, resolveDocxodusEntry } = await import(
			"./docxodus-node-compat.mjs"
		);
		installDocxodusNodeCompat();
		const dox = await import(resolveDocxodusEntry());
		if (dox.initialize) await dox.initialize();
		const engine = dox.ComparisonEngine?.DocxDiff;
		if (typeof engine !== "number") {
			throw new Error(
				"docxodus: ComparisonEngine.DocxDiff missing — cannot pin the roundtrip engine",
			);
		}
		return async (input) => {
			const out = await dox.compareDocuments(input, input, { engine });
			return out instanceof Uint8Array ? out : new Uint8Array(out);
		};
	}

	// docx-redline-js: no HTML export of its own → soffice docx→html→docx.
	// The self-diff (applyRedlineToOxml with identical text) is also a no-op,
	// so we use LibreOffice for both legs to force a genuine re-serialization.
	if (route === "docx-redline-js") {
		const tmp = join(tmpdir(), `rt-drx-${process.pid}`);
		mkdirSync(tmp, { recursive: true });
		let ctr = 0;
		return async (input) => {
			const i = ctr++;
			const stem = `drx${i}`;
			const srcDocx = join(tmp, `${stem}.docx`);
			writeFileSync(srcDocx, input);
			try {
				// DOCX → HTML (soffice)
				const htmlPath = sofficeConvert(srcDocx, "html", tmp);
				if (!htmlPath) throw new Error("soffice docx→html failed");
				// HTML → DOCX (soffice, StarWriter infilter required for HTML import)
				// This overwrites srcDocx (same stem), but input is already in memory.
				const docxPath = sofficeConvert(
					htmlPath,
					"docx",
					tmp,
					"HTML (StarWriter)",
				);
				if (!docxPath) throw new Error("soffice html→docx failed");
				return readBytes(docxPath);
			} finally {
				rmSync(join(tmp, `${stem}.docx`), { force: true });
				rmSync(join(tmp, `${stem}.html`), { force: true });
			}
		};
	}

	// superdoc-ts: client.open() → save() (genuinely re-serialized).
	// File-path based, so we round-trip through temp files.
	if (route === "superdoc-ts") {
		const [{ SuperDocClient }, os, fs, path] = await Promise.all([
			import(
				"../src/neurotic_docx_bench/utils/superdoc/node_modules/@superdoc-dev/sdk"
			),
			import("node:os"),
			import("node:fs"),
			import("node:path"),
		]);
		const client = new SuperDocClient({
			user: { name: "bench", email: "bench@example.com" },
		});
		const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "sdts-rt-"));
		let ctr = 0;
		return async (input) => {
			const i = ctr++;
			const ip = path.join(tmp, `in${i}.docx`);
			const op = path.join(tmp, `out${i}.docx`);
			fs.writeFileSync(ip, input);
			try {
				const s = await client.open({ sessionId: `rt${i}`, doc: ip });
				await s.save({ out: op, force: true });
				await s.close({});
				return new Uint8Array(fs.readFileSync(op));
			} finally {
				for (const f of [ip, op]) fs.rmSync(f, { force: true });
			}
		};
	}

	// folio (@stll/folio-core): FolioDocxReviewer.fromBuffer → toBuffer.
	// The headless reviewer re-serializes on save (toBuffer does a selective patch
	// with a full-repack fallback), so this is a genuine round-trip — not a no-op zip.
	// folio's APIs take ArrayBuffer; copy the Uint8Array into a fresh slab (Node
	// Buffers share a larger underlying ArrayBuffer that would corrupt the slice).
	if (route === "folio") {
		// FOLIO_MODULE_ROOT (absolute node_modules dir) swaps in a different folio
		// build for comparison runs; unset = the pinned vendored tree.
		const folioModuleRoot =
			process.env.FOLIO_MODULE_ROOT ??
			resolve(
				import.meta.dirname,
				"../src/neurotic_docx_bench/utils/folio/node_modules",
			);
		const { FolioDocxReviewer } = await import(
			join(folioModuleRoot, "@stll/folio-core/dist/server.js")
		);
		const toAB = (u) =>
			u.buffer.slice(u.byteOffset, u.byteOffset + u.byteLength);
		return async (input) => {
			const reviewer = await FolioDocxReviewer.fromBuffer(toAB(input), {
				author: "folio-roundtrip",
			});
			const out = await reviewer.toBuffer();
			return out instanceof Uint8Array ? out : new Uint8Array(out);
		};
	}

	throw new Error(`unknown route: ${route}`);
}

// ── Main ─────────────────────────────────────────────────────────────────────

const opts = parseArgs(process.argv.slice(2));

// Select tools
let selected = TOOLS;
if (opts.tool) {
	const wanted = opts.tool
		.split(",")
		.map((s) => s.trim())
		.filter(Boolean);
	selected = TOOLS.filter((t) => wanted.includes(t.tool));
	if (!selected.length) {
		console.error(
			`Unknown tool: ${opts.tool}\nAvailable: ${TOOLS.map((t) => t.tool).join(", ")}`,
		);
		process.exit(1);
	}
} else if (opts.all) {
	// A scoped bench invocation exports $BENCH_TOOLS (comma-separated run names);
	// only roundtrip the tools that are actually running. Non-Node tools in the
	// list (superdoc, word-redlines-soffice) are simply not ours to handle.
	const benchTools = (process.env.BENCH_TOOLS ?? "")
		.split(",")
		.map((s) => s.trim())
		.filter(Boolean);
	if (benchTools.length) {
		selected = TOOLS.filter((t) => benchTools.includes(t.tool));
		if (!selected.length) {
			// Nothing to do — exit with 100 (the CLI's "skip" sentinel) so the rule
			// and headline banner are suppressed.
			process.exit(100);
		}
	}
} else {
	console.error("Specify --all or --tool=<name>\n");
	console.error("Available tools:");
	for (const t of TOOLS)
		console.error(`  ${t.tool.padEnd(30)} route: ${t.route}`);
	process.exit(1);
}

// Find source files
const files = findDocxFiles(opts.sourceDir);
if (!files.length) {
	console.error(`No .docx files found in ${opts.sourceDir}`);
	process.exit(1);
}
const processFiles = opts.limit ? files.slice(0, opts.limit) : files;
console.log(
	`Source: ${opts.sourceDir}  (${files.length} docx files, processing ${processFiles.length})`,
);
console.log(`Output: ${opts.out}/<tool>/\n`);

const summary = [];

for (const t of selected) {
	const toolOut = join(opts.out, t.tool);
	mkdirSync(toolOut, { recursive: true });
	const failures = [];
	let ok = 0;
	let reserialized = 0;
	let identical = 0;

	console.log(
		`\n▶ ${t.tool}  (route: ${t.route}${t.dist ? ", dist: " + t.dist : ""})`,
	);

	// Load engine
	let engine;
	try {
		engine = await loadEngine(t.route, t.dist);
	} catch (e) {
		console.log(`  ❌ engine load failed: ${e.message?.slice(0, 200)}`);
		failures.push({ doc: "*", stage: "engine_load", error: e.message });
		writeFileSync(
			join(toolOut, "generate_failures.json"),
			JSON.stringify(failures, null, 2),
		);
		summary.push({
			tool: t.tool,
			ok: 0,
			failed: processFiles.length,
			reserialized: 0,
			identical: 0,
		});
		continue;
	}

	// Process each file
	for (let fi = 0; fi < processFiles.length; fi++) {
		const file = processFiles[fi];
		const name = basename(file);
		const outPath = join(toolOut, name);

		if (!opts.force && existsSync(outPath)) {
			ok++;
			continue;
		}

		try {
			const input = readBytes(file);
			const origMd5 = await docXmlMd5(input);
			const output = await engine(input);
			const v = await isValidDocx(output);
			if (!v.ok) throw new Error(`invalid output: ${v.reason}`);
			writeFileSync(outPath, output);
			ok++;
			// Best-effort re-serialization check
			try {
				const newMd5 = await docXmlMd5(output);
				if (newMd5 !== origMd5) reserialized++;
				else identical++;
			} catch {
				// Can't determine — not counted as either
			}
		} catch (e) {
			failures.push({
				doc: name,
				stage: "roundtrip",
				error: e.message?.slice(0, 200),
			});
			rmSync(outPath, { force: true });
		}

		// Progress
		if ((fi + 1) % 20 === 0 || fi + 1 === processFiles.length) {
			console.log(`  ${fi + 1}/${processFiles.length} processed`);
		}
	}

	writeFileSync(
		join(toolOut, "generate_failures.json"),
		JSON.stringify(failures, null, 2),
	);
	console.log(
		`  ✅ ${ok} ok, ❌ ${failures.length} failed, ` +
			`re-serialized: ${reserialized}, identical: ${identical}` +
			(failures.length ? `  → ${join(toolOut, "generate_failures.json")}` : ""),
	);
	summary.push({
		tool: t.tool,
		ok,
		failed: failures.length,
		reserialized,
		identical,
	});
}

// ── Overall summary ──────────────────────────────────────────────────────────
// Skip the multi-tool summary block when only one tool ran (its per-tool
// section already printed the same numbers); collapse to a single line.
const totalOk = summary.reduce((a, s) => a + s.ok, 0);
const totalFail = summary.reduce((a, s) => a + s.failed, 0);
const totalReser = summary.reduce((a, s) => a + s.reserialized, 0);
const totalIdent = summary.reduce((a, s) => a + s.identical, 0);
if (summary.length > 1) {
	console.log(
		`\nROUNDTRIP SUMMARY — ${summary.length} tools, ${totalOk} ok, ${totalFail} failed, ${totalReser} re-serialized, ${totalIdent} identical`,
	);
	for (const s of summary) {
		console.log(
			`  ${s.tool.padEnd(30)} ok=${s.ok} fail=${s.failed} re-serialized=${s.reserialized} identical=${s.identical}`,
		);
	}
} else if (summary.length === 1) {
	console.log(
		`ROUNDTRIP — ${summary[0].tool}: ${totalOk} ok, ${totalFail} failed, ${totalReser} re-serialized, ${totalIdent} identical`,
	);
}
// Only fail if every tool produced zero outputs (total wipeout)
process.exit(totalOk === 0 && totalFail > 0 ? 1 : 0);
