/**
 * Generate tracked-change redlines for every base→next pair in the corpus manifest,
 * using a native engine (jubarte for now; docxodus / docx-redline-js added in later PRs),
 * writing one `<base>_<next>_<tool>_redline.docx` per pair so the Python bench can render
 * and score it against the Word oracle `<base>_<next>_redline.pdf`.
 *
 * Usage:
 *   node --import tsx scripts/generate-native-redlines.ts \
 *     --method jubarte --dist dist/jubarte --out $RUN_DIR/docx --run-dir $RUN_DIR \
 *     [--manifest corpus/word_based/centralized_mapping.csv] \
 *     [--source-dir corpus/word_based/docx_source] [--status ok] [--limit N] [--tool NAME]
 */
import {
	readFileSync,
	writeFileSync,
	mkdirSync,
	existsSync,
	mkdtempSync,
	rmSync,
} from "node:fs";
import { createRequire } from "node:module";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { tmpdir } from "node:os";
import { spawnSync } from "node:child_process";
import { parse } from "csv-parse/sync";
import { docxIn, toBytes } from "./docx-utils.mjs";
import { wireJubarteLosslessAdapter } from "./jubarte-lossless-adapter.mjs";
import { runSuperDocVitest } from "./prosemirror-headless-editor-server.ts";

// Per-reply timeout for the long-lived inproc worker (READY handshake + each
// COMPARE reply). The 15s default is ample for the normal corpus (median
// ~17ms) but too short for pathological run-fragmented inputs like the 276k-run
// dissertation, whose single compare takes ~35s natively (WASM_PERF_PLAN /
// jubarte TODO §1). Override with WORKER_REPLY_TIMEOUT_MS for large-doc runs so
// the inproc "fair algorithm" lane reports instead of spuriously timing out.
const WORKER_REPLY_TIMEOUT_MS =
	Number(process.env.WORKER_REPLY_TIMEOUT_MS) || 15_000;

export interface Pair {
	base: string;
	next: string;
	status: string;
	redlineDocx?: string;
	redlineDocxWord?: string;
}

export interface GenOptions {
	method: string;
	dist: string;
	out: string;
	runDir: string;
	manifest: string;
	sourceDir: string;
	status: string;
	limit?: number;
	tool: string;
	force: boolean;
}

/** Parse the committed centralized_mapping.csv into base→next pairs. */
export function parseManifest(csvPath: string, statuses: string[]): Pair[] {
	const rows: Record<string, string>[] = parse(readFileSync(csvPath, "utf8"), {
		columns: true,
		skip_empty_lines: true,
	});
	const wanted = new Set(statuses);
	const pairs: Pair[] = [];
	for (const r of rows) {
		const base = (r.base || "").trim();
		const next = (r.next || "").trim();
		const status = (r.batch_status || "").trim();
		const redlineDocx = (r.redline_docx || "").trim();
		const redlineDocxWord = (r.redline_docx_word || "").trim();
		if (!base || !next) continue;
		// Only filter when the manifest carries a status (older schema); the current manifest
		// dropped batch_status, so an empty status means "include".
		if (wanted.size && status && !wanted.has(status)) continue;
		pairs.push({ base, next, status, redlineDocx, redlineDocxWord });
	}
	return pairs;
}

/** Resolve `filename` under a build dir, tolerating an extra nested `dist/`
 *  level (some jubarte builds unpack as `<dist>/dist/*.cjs` instead of
 *  `<dist>/*.cjs`) — fail loudly with both checked paths if neither exists. */
export function resolveDistFile(distPath: string, filename: string): string {
	const direct = resolve(distPath, filename);
	if (existsSync(direct)) return direct;
	const nested = resolve(distPath, "dist", filename);
	if (existsSync(nested)) return nested;
	throw new Error(
		`cannot find ${filename} under ${distPath} (checked ${direct} and ${nested})`,
	);
}

/** Directory of the `@superdoc-dev/sdk` copy the bench actually benchmarks.
 *
 *  `tool_updater.update_npm_package` runs `npm install @superdoc-dev/sdk@<pin>` with
 *  cwd = repo root (cli.py passes `Path.cwd()`) and reads the resolved version back out
 *  of `<repo>/node_modules/@superdoc-dev/sdk/package.json`. So repo-root node_modules is
 *  the ONE copy whose version lands in the JSONL as `tool_version`; importing any other
 *  copy would benchmark a version we do not report. It is also where `bun install`
 *  (the repo's package manager) puts the root `package.json` dependency.
 *
 *  `utils/superdoc/node_modules` stays as a fallback for checkouts that still carry the
 *  old sub-install. `SUPERDOC_SDK_DIR` overrides both (mirrors FOLIO_MODULE_ROOT).
 */
export function resolveSuperDocSdkDir(
	env: Record<string, string | undefined> = process.env,
): string {
	const PKG = "@superdoc-dev/sdk";
	const override = env.SUPERDOC_SDK_DIR;
	// import.meta.dirname is unreliable under some test transforms; cwd is the repo root
	// for every bench invocation (bench.yaml commands all use repo-relative paths).
	const roots = [process.cwd(), resolve(import.meta.dirname, "..")];
	const candidates = override
		? [override]
		: roots.flatMap((root) => [
				resolve(root, "node_modules", PKG),
				resolve(
					root,
					"src/neurotic_docx_bench/utils/superdoc/node_modules",
					PKG,
				),
			]);
	const found = candidates.find((d) => existsSync(join(d, "package.json")));
	if (!found) {
		throw new Error(
			`superdoc-ts: ${PKG} not found (checked ${candidates.join(", ")}). ` +
				`Run \`bun install\` at the repo root, or set SUPERDOC_SDK_DIR.`,
		);
	}
	return found;
}

/** ESM entry of an installed package dir, read from its package.json.
 *
 *  Importing the *directory* only works under loaders that add CJS-style directory
 *  resolution (tsx does, plain Node ESM and vitest do not), and the CJS `main` loses
 *  named exports on some bundles — so resolve the declared ESM entry explicitly. */
function packageEntryUrl(pkgDir: string): string {
	const pkg = JSON.parse(readFileSync(join(pkgDir, "package.json"), "utf8"));
	const dot = pkg.exports?.["."];
	const entry =
		(typeof dot === "string" ? dot : (dot?.import ?? dot?.default)) ??
		pkg.module ??
		pkg.main;
	if (!entry) {
		throw new Error(`no import entry declared in ${join(pkgDir, "package.json")}`);
	}
	return pathToFileURL(resolve(pkgDir, entry)).href;
}

/** compare(base,next) → docx bytes, plus optional teardown for engines that hold a
 *  long-lived resource. An engine backed by a persistent child process keeps the event
 *  loop alive, so without `dispose` the batch writes every redline and then hangs
 *  forever instead of exiting — `runBatch` calls it in a `finally`. */
export type RedlineEngine = ((
	base: Uint8Array,
	next: Uint8Array,
) => Promise<Uint8Array>) & { dispose?: () => Promise<void> };

/** Load the redline engine for `method` and return compare(base,next)->docx bytes. */
/**
 * Directory to import `@stll/folio-core` from.
 *
 * Prefers the repo-root `node_modules` because that is the ONE copy the
 * bench.yaml `package:` pin installs into and whose version is read back as
 * `tool_version`. Three copies exist on disk (root, `utils/folio`,
 * `harness/folio-viewer-current`) at three different versions, so importing by
 * convenience rather than by the pin means recording one version and running
 * another (plan Chapter 6 D5).
 */
function resolveFolioModuleRoot(): string {
	const root = resolve(import.meta.dirname, "../node_modules");
	if (existsSync(join(root, "@stll/folio-core/dist/server.js"))) return root;
	return resolve(
		import.meta.dirname,
		"../src/neurotic_docx_bench/utils/folio/node_modules",
	);
}

export async function loadEngine(
	method: string,
	distPath: string,
): Promise<RedlineEngine> {
	// jubarte ships TWO redline routes; the bench tests both:
	//  - native:   redlineDocx (CriticMarkup) → redlineToDocx
	//  - docxodus: DocumentComparer.CompareDocuments, the JS-friendly wrapper around
	//    jubarte's "lossless" WmlComparer port (replaces the old node.cjs compareDocx —
	//    jubarte moved this route off its docxodus port onto the lossless comparer).
	//
	// jubarte's signature takes a NodeDocxInput ({ buffer } | { path } | { file }).
	// We pass { buffer } — the documented form since the jubarte-final build, and
	// accepted by every earlier build too (output is byte-identical to raw bytes).
	if (method === "jubarte-native" || method === "jubarte") {
		const mod: any = await import(resolveDistFile(distPath, "node.cjs"));
		return async (base, next) => {
			const cm = await mod.redlineDocx(docxIn(base), docxIn(next), {
				author: "jubarte-native",
			});
			// Newer jubarte builds wrap the result as { criticmarkup, handle };
			// older ones return the handle bare. redlineToDocx wants the handle
			// either way, and a null result/handle means "no differences".
			const handle =
				cm != null && typeof cm === "object" && "handle" in cm ? cm.handle : cm;
			if (handle == null) return base; // no differences → identity
			return toBytes(await mod.redlineToDocx(handle));
		};
	}
	if (method === "jubarte-lossless") {
		// Load via require (not import()) so the adapter's internal-chunk scan
		// (findInternalPrimitives) sees the exact same require.cache entry.
		const losslessPath = resolveDistFile(distPath, "lossless.node.cjs");
		const req = createRequire(import.meta.url);
		const mod: any = req(losslessPath);
		wireJubarteLosslessAdapter(mod, losslessPath);
		return async (base, next) => {
			const out = mod.DocumentComparer.CompareDocuments(
				base,
				next,
				"jubarte-lossless",
			);
			const bytes = out instanceof Uint8Array ? out : new Uint8Array(out);
			// CompareDocuments catches its own internal errors and returns an EMPTY array
			// instead of throwing — fail fast here rather than silently writing a 0-byte
			// "redline" that only surfaces as a mysterious render/score failure downstream.
			if (bytes.length === 0) {
				throw new Error(
					"jubarte lossless DocumentComparer.CompareDocuments returned empty output " +
						"(comparison failed internally — see jubarte's own error, not surfaced here)",
				);
			}
			return bytes;
		};
	}
	if (method === "docxodus") {
		// WASM engine (JSv4/docxodus, MIT); one-time initialize() loads the .NET runtime.
		const dox: any = await import(
			// Point at dist/index.js: Node ESM rejects bare directory imports under
			// node_modules when the package uses an "exports" map (docxodus ≥7).
			"../src/neurotic_docx_bench/utils/docxodus/node_modules/docxodus/dist/index.js"
		);
		if (dox.initialize) await dox.initialize();
		// NAME the comparison engine. `compareDocuments(base, next)` with no options
		// resolves the engine from whatever the installed version defaults to, and that
		// default is not stable across majors: docxodus 7.0.0 shipped
		// `options?.engine ?? ComparisonEngine.WmlComparer`, 9.0.0 ships
		// `options?.engine ?? ComparisonEngine.DocxDiff`. Same call, different engine,
		// no error — an upgrade would silently move every docxodus score with nothing in
		// the run recording why.
		//
		// We pin docxodus's OWN current default (DocxDiff) rather than freezing the
		// legacy engine: the bench measures what a real docxodus 9 user gets. Reading the
		// value off the shipped enum (never a hardcoded 0/1) keeps us on the package's
		// wire contract, and generate-native-redlines.test.ts fails if a future release
		// moves that default out from under this pin.
		const engine = dox.ComparisonEngine?.DocxDiff;
		if (typeof engine !== "number") {
			throw new Error(
				"docxodus: ComparisonEngine.DocxDiff missing from the installed package — " +
					"cannot pin the comparison engine, and an unpinned engine makes the " +
					"benchmarked engine a property of the installed version.",
			);
		}
		const options = { engine };
		return async (base, next) => {
			const out = await dox.compareDocuments(base, next, options);
			return out instanceof Uint8Array ? out : new Uint8Array(out);
		};
	}
	// Canonical jubarte-redlines source → wasm-bindgen package (wasm-pack + wasm-opt -O3).
	// Dist dir is the crate root (contains pkg/jubarte_wasm.js) or pkg/ itself.
	if (
		method === "jubarte-wasm" ||
		method === "jubarte-rs-wasm" ||
		method === "jubarte-rust-wasm"
	) {
		const req = createRequire(import.meta.url);
		const candidates = [
			resolve(distPath, "pkg/jubarte_wasm.js"),
			resolve(distPath, "jubarte_wasm.js"),
			resolve(
				distPath,
				"../jubarte-wasm/pkg/jubarte_wasm.js",
			),
		];
		const modPath = candidates.find((p) => existsSync(p));
		if (!modPath) {
			throw new Error(
				`jubarte-wasm: no pkg at ${candidates[0]}. ` +
					`Run: cd utils/jubarte/jubarte-wasm && wasm-pack build --target nodejs --release`,
			);
		}
		const mod: any = req(modPath);
		if (typeof mod.initPanicHook === "function") mod.initPanicHook();
		return async (base, next) => {
			const out = mod.compareDocuments(base, next, "jubarte-wasm");
			const bytes = out instanceof Uint8Array ? out : new Uint8Array(out);
			if (bytes.length === 0) {
				throw new Error("jubarte-wasm compareDocuments returned empty output");
			}
			return bytes;
		};
	}
	if (method === "docx-redline-js") {
		// @ansonlai/docx-redline-js (MIT) reconciles TEXT edits into w:ins/w:del on OOXML.
		// Best practices: use extractReplacementNodesFromOoxml for result.oxml,
		// ensureNumberingArtifactsInZip for numbering, and validateDocxPackage before output.
		const [JSZipMod, xmldom, rl]: [any, any, any] = await Promise.all([
			import(
				"../src/neurotic_docx_bench/utils/docx-redline-js/node_modules/jszip/lib/index.js"
			),
			import(
				"../src/neurotic_docx_bench/utils/docx-redline-js/node_modules/@xmldom/xmldom"
			),
			import(
				"../src/neurotic_docx_bench/utils/docx-redline-js/node_modules/@ansonlai/docx-redline-js"
			),
		]);
		const JSZip = JSZipMod.default ?? JSZipMod;
		rl.configureXmlProvider({
			DOMParser: xmldom.DOMParser,
			XMLSerializer: xmldom.XMLSerializer,
		});
		const toText = (xml: string): string => {
			const t = rl.ingestWordOoxmlToPlainText(xml);
			return typeof t === "string" ? t : (t?.text ?? "");
		};
		// extractReplacementNodesFromOoxml returns { replacementNodes: Element[] } — DOM
		// nodes meant to REPLACE the base body's content, never a document.xml string.
		// Splice them into the base document (keeping its sectPr) and serialize.
		const spliceIntoBase = (baseXml: string, nodes: any[]): string => {
			const doc = new xmldom.DOMParser().parseFromString(
				baseXml,
				"application/xml",
			);
			const body = doc.getElementsByTagNameNS("*", "body")[0];
			if (!body) throw new Error("base document.xml has no <w:body>");
			const sectPrs = Array.from(body.childNodes as any).filter(
				(n: any) => n.nodeType === 1 && /(^|:)sectPr$/.test(n.nodeName),
			);
			while (body.firstChild) body.removeChild(body.firstChild);
			for (const n of nodes) body.appendChild(doc.importNode(n, true));
			for (const s of sectPrs) body.appendChild(s);
			return new xmldom.XMLSerializer().serializeToString(doc);
		};
		return async (base, next) => {
			const baseZip = await JSZip.loadAsync(base);
			const baseXml: string = await baseZip
				.file("word/document.xml")
				.async("string");
			const nextZip = await JSZip.loadAsync(next);
			const nextXml: string = await nextZip
				.file("word/document.xml")
				.async("string");
			const res: any = await rl.applyRedlineToOxml(
				baseXml,
				toText(baseXml),
				toText(nextXml),
				{
					generateRedlines: true,
					author: "docx-redline-js",
				},
			);
			const oxml: string = res.oxml ?? res.ooxml;
			// Use extractReplacementNodesFromOoxml to normalize the output shape.
			// Guard: a missing/empty replacementNodes (no-op redline, or an unexpected
			// full-document payload) must NOT be spliced into the base — spliceIntoBase
			// wipes the body first, so an empty array would silently erase the document
			// and an undefined value throws a confusing TypeError. Fail this pair loudly.
			const normalized: any = rl.extractReplacementNodesFromOoxml(oxml);
			if (
				!normalized?.replacementNodes ||
				normalized.replacementNodes.length === 0
			) {
				throw new Error(
					`docx-redline-js: extractReplacementNodesFromOoxml returned no replacementNodes ` +
						`(sourceType=${normalized?.sourceType ?? "unknown"})`,
				);
			}
			const docXml = spliceIntoBase(baseXml, normalized.replacementNodes);
			baseZip.file("word/document.xml", docXml);
			// Merge numbering artifacts using the proper helper
			if (normalized.numberingXml) {
				await rl.ensureNumberingArtifactsInZip(
					baseZip,
					normalized.numberingXml,
				);
			}
			// Validate package structure before generating output
			await rl.validateDocxPackage(baseZip);
			return baseZip.generateAsync({ type: "uint8array" });
		};
	}
	if (method === "folio") {
		// @stll/folio-core (Apache-2.0; stella/folio) ships a single base+next→redline
		// call as of 0.13.0: `generateRedlineDocx(base, revised, { author })` returns
		// the base package with tracked changes across every matched story. We call it
		// directly — no diff translation, no op synthesis, no fallback of ours. Folio's
		// score on script_redlines is folio's own output; see docs/FOLIO.md.
		//
		// This replaced a hand-rolled composition of
		// @stll/folio-agents.compareDocxVersions + FolioDocxReviewer.applyOperations
		// that was silently wrong: it fed a `modified` diff entry's `blockId` straight
		// into replaceInBlock, but folio emits the diff in REVISED-side order and that
		// id is the revised-side id, so no base block ever matched, every modification
		// op was dropped, and pairs differing only by modified text returned the BASE
		// document unchanged. 0.15.13 also adds diff kinds the old translation had no
		// branch for at all (formatChanged / movedFrom / movedTo) and stories beyond
		// the main body (headers, footers, footnotes), all of which generateRedlineDocx
		// handles natively. Pinned regression: the "modification-only pair" case in
		// scripts/generate-native-redlines.test.ts.
		//
		// FOLIO_MODULE_ROOT (absolute path to a node_modules dir) lets a comparison
		// run swap in a different folio build; unset = the pinned vendored tree.
		// Resolve from the tree the bench.yaml pin actually installs into (repo
		// root), falling back to the vendored sub-install. Getting this backwards
		// is plan Chapter 6 D5: `bench.yaml` pins @stll/folio-core@0.15.13, the
		// updater installs it at the repo root and reports THAT version as
		// tool_version, but this adapter used to import
		// utils/folio/node_modules — which still holds 0.3.1. The run therefore
		// recorded 0.15.13 while executing 0.3.1, and since generateRedlineDocx
		// only exists from 0.13.0 the whole run died with "generateRedlineDocx is
		// not a function" — attributed to folio, caused by us.
		const folioModuleRoot =
			process.env.FOLIO_MODULE_ROOT ?? resolveFolioModuleRoot();
		const { generateRedlineDocx }: any = await import(
			join(folioModuleRoot, "@stll/folio-core/dist/server.js")
		);
		// Copy a Uint8Array's bytes into a fresh ArrayBuffer (folio's APIs take
		// ArrayBuffer; the engine contract hands us Uint8Array, often a Node Buffer
		// whose .buffer is a larger slab shared with other data).
		const toAB = (u: Uint8Array): ArrayBuffer =>
			u.buffer.slice(u.byteOffset, u.byteOffset + u.byteLength) as ArrayBuffer;
		return async (base, next) => {
			// generateRedlineDocx parses via folio's strict native reader — a few corpus
			// DOCX with empty comment authors throw here (e.g.
			// vfdsdfcacawesd_suggesting_mixed_edits). That's folio-native, not our
			// adapter; see docs/FOLIO.md.
			const result: any = await generateRedlineDocx(toAB(base), toAB(next), {
				author: "folio",
			});
			// A zero-change comparison still returns a real package from folio, so there
			// is no identity fallback here: whatever folio emits is what gets scored.
			return new Uint8Array(result.buffer);
		};
	}
	if (method === "folio-wasm") {
		// folio's orchestrator with jubarte-wasm FORCED as the sole engine — the
		// exact wiring of the playground redline tool (packages/playground/src/
		// redline/engine.ts): generateRedlineDocx with engines:[jubarte-wasm] and
		// selfCheck:"engine-lossless". No fallback rung: an engine/self-check
		// failure throws RedlineEngineExhaustedError and the pair is recorded as
		// a generate failure, never silently downgraded to another engine.
		//
		// FOLIO_MODULE_ROOT must point at a folio build whose core exports
		// createJubarteWasmRedlineEngine (the current staged build; 0.3.1 predates
		// it). JUBARTE_WASM_DIR points at the wasm-pack output folio ships in the
		// playground (web target; init accepts raw bytes under Node).
		const folioModuleRoot =
			process.env.FOLIO_MODULE_ROOT ??
			resolve(
				import.meta.dirname,
				"../src/neurotic_docx_bench/utils/folio-current/node_modules",
			);
		const wasmDir =
			process.env.JUBARTE_WASM_DIR ??
			resolve(
				import.meta.dirname,
				"../src/neurotic_docx_bench/utils/jubarte/jubarte-wasm/pkg",
			);
		const [{ generateRedlineDocx, createJubarteWasmRedlineEngine }, glueRaw] =
			await Promise.all([
				import(join(folioModuleRoot, "@stll/folio-core/dist/server.js")),
				import(join(wasmDir, "jubarte_wasm.js")),
			]);
		// wasm-pack targets differ in glue shape: `web` exports a default init
		// function (call it with the binary bytes — no fetch under Node); `nodejs`
		// is CJS whose exports are ready immediately (default = exports object).
		let glue: any = glueRaw;
		if (typeof glueRaw.default === "function") {
			await glueRaw.default({
				module_or_path: readFileSync(join(wasmDir, "jubarte_wasm_bg.wasm")),
			});
		} else if (glueRaw.default && typeof glueRaw.default === "object") {
			glue = { ...glueRaw.default, ...glueRaw };
		}
		glue.initPanicHook?.();
		const wasmEngine = createJubarteWasmRedlineEngine({
			compareDocuments: glue.compareDocuments,
			acceptRevisions: glue.acceptRevisions,
			rejectRevisions: glue.rejectRevisions,
			getRevisions: glue.getRevisions,
		});
		const toAB = (u: Uint8Array): ArrayBuffer =>
			u.buffer.slice(u.byteOffset, u.byteOffset + u.byteLength) as ArrayBuffer;
		return async (base, next) => {
			try {
				const result: any = await generateRedlineDocx(toAB(base), toAB(next), {
					engines: [wasmEngine],
					author: "folio",
					selfCheck: "engine-lossless",
				});
				return new Uint8Array(result.buffer);
			} catch (err: any) {
				// Surface the per-rung attempt log (engine/phase/message) so JSONL
				// failures name the real cause, not just "every engine failed".
				const attempts: any[] = err?.attempts;
				if (Array.isArray(attempts) && attempts.length > 0) {
					const detail = attempts
						.map((a) => `${a.engine}/${a.phase}: ${a.message}`)
						.join(" | ");
					throw new Error(`${err.message} — ${detail}`.slice(0, 600));
				}
				throw err;
			}
		};
	}
	if (method === "superdoc-ts") {
		// Native SuperDoc via the TypeScript SDK (@superdoc-dev/sdk), driving the same
		// Document Engine diff flow as the Python SDK:
		//   target.diff.capture({}) → base.diff.compare({targetSnapshot})
		//   → base.diff.apply({diff, changeMode:"tracked"}) → base.save({out, force})
		// (@superdoc-dev/sdk 1.21.3 dist/generated/client.d.ts:89841-89843 —
		//  capture/compare/apply on the bound `doc.diff` namespace.)
		// File-path based, so we round-trip through temp files. One client reused across
		// pairs; unique session ids.
		const [{ SuperDocClient }, os, fs, path]: [any, any, any, any] =
			await Promise.all([
				import(packageEntryUrl(resolveSuperDocSdkDir())),
				import("node:os"),
				import("node:fs"),
				import("node:path"),
			]);
		const client = new SuperDocClient({
			user: { name: "bench", email: "bench@example.com" },
		});
		const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "sdts-"));
		let ctr = 0;
		const engine: RedlineEngine = async (base, next) => {
			const i = ctr++;
			const bp = path.join(tmp, `b${i}.docx`);
			const np = path.join(tmp, `n${i}.docx`);
			const op = path.join(tmp, `o${i}.docx`);
			fs.writeFileSync(bp, base);
			fs.writeFileSync(np, next);
			let b: any, t: any;
			try {
				b = await client.open({ sessionId: `b${i}`, doc: bp });
				t = await client.open({ sessionId: `t${i}`, doc: np });
				const snapshot = await t.diff.capture({});
				await t.close({});
				t = undefined;
				const diff = await b.diff.compare({ targetSnapshot: snapshot });
				await b.diff.apply({ diff, changeMode: "tracked" });
				await b.save({ out: op, force: true });
				await b.close({});
				b = undefined;
				return new Uint8Array(fs.readFileSync(op));
			} finally {
				if (t) await t.close({}).catch(() => {});
				if (b) await b.close({}).catch(() => {});
				for (const f of [bp, np, op]) fs.rmSync(f, { force: true });
			}
		};
		// SuperDocClient backs onto a long-lived `superdoc host --stdio` child process
		// (dist/runtime/process.js) whose stdio pipes keep the event loop alive.
		// SuperDocClient.dispose() is the only public teardown — 1.19.2 needed it too,
		// but the run never got that far: it died at import (ERR_MODULE_NOT_FOUND).
		engine.dispose = async () => {
			await client.dispose().catch(() => {});
			fs.rmSync(tmp, { recursive: true, force: true });
		};
		return engine;
	}
	// jubarte-redlines CLI (Rust). Dist dir holds the release `redline` binary
	// (also copied as `jubarte` for older examples). Invoked as:
	//   redline <base> <next> -o <out> --force --quiet
	if (method === "jubarte-rust" || method === "jubarte-redlines") {
		const binCandidates = ["redline", "jubarte"].map((n) =>
			resolve(distPath, n),
		);
		const bin = binCandidates.find((p) => existsSync(p));
		if (!bin) {
			throw new Error(
				`jubarte-rust: no redline binary under ${distPath} ` +
					`(checked ${binCandidates.join(", ")}). ` +
					`Build ~/T/jubarte-redlines and copy target/release/jubarte there as redline.`,
			);
		}
		let ctr = 0;
		return async (base, next) => {
			const dir = mkdtempSync(join(tmpdir(), "jr-"));
			const i = ctr++;
			const bp = join(dir, `b${i}.docx`);
			const np = join(dir, `n${i}.docx`);
			const op = join(dir, `o${i}.docx`);
			try {
				writeFileSync(bp, base);
				writeFileSync(np, next);
				const r = spawnSync(
					bin,
					[bp, np, "-o", op, "--force", "--quiet"],
					{ encoding: "utf8" },
				);
				if (r.status !== 0) {
					throw new Error(
						`jubarte-rust redline failed (exit ${r.status}): ` +
							`${(r.stderr || r.stdout || "").trim() || "no output"}`,
					);
				}
				if (!existsSync(op)) {
					throw new Error(
						`jubarte-rust redline produced no output at ${op}`,
					);
				}
				return new Uint8Array(readFileSync(op));
			} finally {
				rmSync(dir, { recursive: true, force: true });
			}
		};
	}
	// Docxodus C# CLI (native .NET, NOT the WASM npm package). Dist dir holds the
	// published `redline` apphost + Docxodus.dll from Docxodus/tools/redline.
	// Invoked as: redline <original.docx> <modified.docx> <output.docx>
	// NOTE: every call is a cold process start (.NET runtime + JIT) — typically
	// 200–800ms even when the in-process compare is ~4ms. Prefer
	// `docxodus-csharp-inproc` for algorithm-only timing.
	if (method === "docxodus-csharp" || method === "docxodus-cs") {
		const bin = resolve(distPath, "redline");
		if (!existsSync(bin)) {
			throw new Error(
				`docxodus-csharp: no redline binary at ${bin}. ` +
					`Build Docxodus/tools/redline (Release) and point --dist at ` +
					`bin/Release/net8.0 (or copy that dir under utils/docxodus/docxodus-csharp).`,
			);
		}
		let ctr = 0;
		return async (base, next) => {
			const dir = mkdtempSync(join(tmpdir(), "dxcs-"));
			const i = ctr++;
			const bp = join(dir, `b${i}.docx`);
			const np = join(dir, `n${i}.docx`);
			const op = join(dir, `o${i}.docx`);
			try {
				writeFileSync(bp, base);
				writeFileSync(np, next);
				const r = spawnSync(bin, [bp, np, op], { encoding: "utf8" });
				if (r.status !== 0) {
					throw new Error(
						`docxodus-csharp redline failed (exit ${r.status}): ` +
							`${(r.stderr || r.stdout || "").trim() || "no output"}`,
					);
				}
				if (!existsSync(op)) {
					throw new Error(
						`docxodus-csharp redline produced no output at ${op}`,
					);
				}
				return new Uint8Array(readFileSync(op));
			} finally {
				rmSync(dir, { recursive: true, force: true });
			}
		};
	}
	// Docxodus C# *in-process* worker — one long-lived `docxodus-inproc` process,
	// DocxDiffOps.Compare over stdin protocol. Isolates algorithm cost from the
	// per-call .NET cold-start tax that `docxodus-csharp` pays.
	if (
		method === "docxodus-csharp-inproc" ||
		method === "docxodus-cs-inproc"
	) {
		return loadLongLivedCompareWorker({
			label: "docxodus-csharp-inproc",
			binCandidates: [
				resolve(distPath, "docxodus-inproc"),
				resolve(distPath, "bin/Release/net8.0/docxodus-inproc"),
				resolve(
					distPath,
					"../docxodus-csharp-inproc/bin/Release/net8.0/docxodus-inproc",
				),
			],
			tmpPrefix: "dxcsip-",
			buildHint: "Build utils/docxodus/docxodus-csharp-inproc.",
		});
	}
	// jubarte-rust *in-process* worker — same `compare_documents` as the CLI,
	// one long-lived process. Fair warm-process counterpart to csharp-inproc
	// (spawn tax on the CLI is tiny for Rust, but thesis comparisons must be
	// warm-vs-warm to be airtight).
	if (
		method === "jubarte-rust-inproc" ||
		method === "jubarte-rs-inproc"
	) {
		// Prefer `jubarte-worker`: on some macOS setups a binary literally named
		// `jubarte-inproc` sitting next to the `jubarte` CLI is SIGKILL'd at
		// launch (exit 137, no stdout). Same bytes under another name work.
		return loadLongLivedCompareWorker({
			label: "jubarte-rust-inproc",
			binCandidates: [
				resolve(distPath, "jubarte-worker"),
				resolve(distPath, "jubarte-inproc"),
				resolve(distPath, "target/release/jubarte-inproc"),
				resolve(
					distPath,
					"../jubarte-rust-inproc/target/release/jubarte-inproc",
				),
				resolve(
					distPath,
					"../jubarte-rust-inproc/target/release/jubarte-worker",
				),
			],
			tmpPrefix: "jrip-",
			buildHint:
				"cargo build --release -p jubarte-rust-inproc " +
				"(utils/jubarte/jubarte-rust-inproc), then copy to " +
				"utils/jubarte/jubarte-rust/jubarte-worker.",
		});
	}
	throw new Error(`unknown method: ${method}`);
}

/** Active long-lived workers — must be shut down or the Node process never
 *  exits (stdin pipes keep the event loop alive). That hung samply forever
 *  after the timed loop on docxodus-csharp-inproc / jubarte-rust-inproc. */
const _longLivedShutdowns: Array<() => void> = [];

/** Kill every long-lived compare worker started by this process. Safe to call
 *  repeatedly. Call at end of speed-bench methods and after `--inner-run`. */
export function shutdownAllLongLivedWorkers(): void {
	while (_longLivedShutdowns.length) {
		const fn = _longLivedShutdowns.pop();
		try {
			fn?.();
		} catch {
			/* ignore */
		}
	}
}

/**
 * Shared long-lived compare worker: stdin protocol
 *   READY / COMPARE base next out → OK n ms | ERR … / QUIT → BYE
 * Used by both docxodus-csharp-inproc and jubarte-rust-inproc so warm-vs-warm
 * timing is methodologically identical.
 */
async function loadLongLivedCompareWorker(opts: {
	label: string;
	binCandidates: string[];
	tmpPrefix: string;
	buildHint: string;
}): Promise<(base: Uint8Array, next: Uint8Array) => Promise<Uint8Array>> {
	const { spawn } = await import("node:child_process");
	const bin = opts.binCandidates.find((p) => existsSync(p));
	if (!bin) {
		throw new Error(
			`${opts.label}: no worker binary ` +
				`(checked ${opts.binCandidates.join(", ")}). ${opts.buildHint}`,
		);
	}
	const child = spawn(bin, [], { stdio: ["pipe", "pipe", "pipe"] });
	let buf = "";
	const waiters: Array<(line: string) => void> = [];
	let spawnExit: { code: number | null; signal: NodeJS.Signals | null } | null =
		null;
	let stderrAcc = "";
	const pushLine = (line: string) => {
		const w = waiters.shift();
		if (w) w(line);
		else buf = buf ? `${buf}\n${line}` : line;
	};
	child.stdout!.setEncoding("utf8");
	child.stderr!.setEncoding("utf8");
	child.stderr!.on("data", (chunk: string) => {
		stderrAcc += chunk;
	});
	let acc = "";
	child.stdout!.on("data", (chunk: string) => {
		acc += chunk;
		let idx: number;
		while ((idx = acc.indexOf("\n")) >= 0) {
			const line = acc.slice(0, idx).replace(/\r$/, "");
			acc = acc.slice(idx + 1);
			pushLine(line);
		}
	});
	child.on("exit", (code, signal) => {
		spawnExit = { code, signal };
		// Unblock any waiter so we fail fast instead of 120s hang.
		const msg = `${opts.label}: worker exited before reply (code=${code} signal=${signal}) bin=${bin}`;
		while (waiters.length) {
			const w = waiters.shift();
			// reject via throwing into the waiter channel as a special line
			w?.(`__EXIT__ ${msg}`);
		}
	});
	const readLine = (): Promise<string> =>
		new Promise((resolveLine, reject) => {
			if (buf) {
				const lines = buf.split("\n");
				const first = lines.shift()!;
				buf = lines.join("\n");
				resolveLine(first);
				return;
			}
			if (spawnExit) {
				reject(
					new Error(
						`${opts.label}: worker already exited (code=${spawnExit.code} signal=${spawnExit.signal}) bin=${bin}` +
							(stderrAcc ? ` stderr=${stderrAcc.trim()}` : ""),
					),
				);
				return;
			}
			const timer = setTimeout(
				() =>
					reject(
						new Error(
							`${opts.label}: timeout waiting for worker reply bin=${bin}` +
								(spawnExit
									? ` exit=${spawnExit.code}/${spawnExit.signal}`
									: "") +
								(stderrAcc ? ` stderr=${stderrAcc.trim()}` : ""),
						),
					),
				WORKER_REPLY_TIMEOUT_MS,
			);
			waiters.push((line) => {
				clearTimeout(timer);
				if (line.startsWith("__EXIT__ ")) {
					reject(new Error(line.slice("__EXIT__ ".length)));
				} else {
					resolveLine(line);
				}
			});
		});
	const ready = await readLine();
	if (ready !== "READY") {
		child.kill();
		throw new Error(
			`${opts.label}: expected READY, got ${ready} bin=${bin}` +
				(stderrAcc ? ` stderr=${stderrAcc.trim()}` : ""),
		);
	}
	const workDir = mkdtempSync(join(tmpdir(), opts.tmpPrefix));
	let ctr = 0;
	let dead = false;
	const shutdown = () => {
		if (dead) return;
		dead = true;
		try {
			child.stdin!.write("QUIT\n");
			child.stdin!.end();
		} catch {
			/* ignore */
		}
		try {
			child.kill("SIGTERM");
		} catch {
			/* ignore */
		}
		// Hard kill if QUIT ignored (should not happen).
		setTimeout(() => {
			try {
				child.kill("SIGKILL");
			} catch {
				/* ignore */
			}
		}, 500).unref?.();
		try {
			rmSync(workDir, { recursive: true, force: true });
		} catch {
			/* ignore */
		}
	};
	_longLivedShutdowns.push(shutdown);
	process.on("exit", shutdown);
	return async (base, next) => {
		if (dead) {
			throw new Error(`${opts.label}: worker already shut down`);
		}
		const i = ctr++;
		const bp = join(workDir, `b${i}.docx`);
		const np = join(workDir, `n${i}.docx`);
		const op = join(workDir, `o${i}.docx`);
		writeFileSync(bp, base);
		writeFileSync(np, next);
		child.stdin!.write(`COMPARE ${bp} ${np} ${op}\n`);
		const reply = await readLine();
		if (reply.startsWith("ERR ")) {
			throw new Error(`${opts.label}: ${reply.slice(4)}`);
		}
		if (!reply.startsWith("OK ")) {
			throw new Error(`${opts.label}: bad reply ${reply}`);
		}
		if (!existsSync(op)) {
			throw new Error(`${opts.label}: no output at ${op}`);
		}
		return new Uint8Array(readFileSync(op));
	};
}

/** The output filename for a pair — must normalize (via redline_key) back to `<base>_<next>`. */
export function outputName(pair: Pair, tool: string): string {
	return `${pair.base}_${pair.next}_${tool}_redline.docx`;
}

/** Output filenames for a pair — always the single canonical `<base>_<next>_<tool>_redline.docx`
 *  name, regardless of which oracle DOCX variant (`redline_docx` / `redline_docx_word`) the
 *  manifest carries for this pair. The oracle PDF is always named `<base>_<next>_redline.pdf`
 *  (never `..._word_redline.pdf`), so deriving the candidate name from the oracle *DOCX*
 *  filename (which sometimes carries a `_word` infix) produced a candidate key that never
 *  matched the oracle PDF key — silently dropping ~43/207 pairs from every tool's score. */
export function outputNames(pair: Pair, tool: string): string[] {
	return [outputName(pair, tool)];
}

export interface Failure {
	doc: string;
	stage: string;
	error: string;
}

/**
 * SuperDoc's native engine (`Editor.commands.compareDocuments` +
 * `replayDifferences`) only runs inside SuperDoc's own Vite/vitest toolchain
 * (Vite path aliases + happy-dom), not under plain Node — so unlike the other
 * engines it can't be a `compare(base,next)=>bytes` closure called per pair.
 * Instead we build a REDLINE_PLAN batch (all pairs in one `npx vitest`
 * process — starting Vite per pair would be far too slow) and check which
 * outputs it actually wrote afterwards.
 */
async function runSuperDocNativeBatch(
	opts: GenOptions,
): Promise<{ ok: number; failed: Failure[]; timings: Record<string, number> }> {
	mkdirSync(opts.out, { recursive: true });
	let pairs = parseManifest(
		opts.manifest,
		opts.status ? opts.status.split(",") : [],
	);
	if (opts.limit) pairs = pairs.slice(0, opts.limit);

	let ok = 0;
	const failed: Failure[] = [];
	const plan: { fileA: string; fileB: string; output: string }[] = [];
	const planDocs: string[] = [];
	for (const pair of pairs) {
		const doc = `${pair.base}_${pair.next}`;
		const outPath = join(opts.out, outputName(pair, opts.tool));
		if (!opts.force && existsSync(outPath)) {
			ok += 1;
			continue;
		}
		const basePath = join(opts.sourceDir, `${pair.base}.docx`);
		const nextPath = join(opts.sourceDir, `${pair.next}.docx`);
		if (!existsSync(basePath) || !existsSync(nextPath)) {
			failed.push({
				doc,
				stage: "missing_source",
				error: "source docx not found",
			});
			continue;
		}
		plan.push({
			fileA: resolve(basePath),
			fileB: resolve(nextPath),
			output: resolve(outPath),
		});
		planDocs.push(doc);
	}

	if (plan.length) {
		const planPath = join(opts.runDir, "superdoc-native-plan.json");
		writeFileSync(planPath, JSON.stringify(plan));
		// The batch `it()` in redline.test.js catches per-pair errors internally and
		// always exits 0 — a rejection here means vitest itself failed to run at all
		// (bad env, missing deps, ...), so fail fast rather than reporting bogus
		// per-pair failures below.
		await runSuperDocVitest({
			REDLINE_PLAN: planPath,
			REDLINE_AUTHOR: "superdoc-native",
		});
		for (let i = 0; i < plan.length; i++) {
			if (existsSync(plan[i].output)) {
				ok += 1;
			} else {
				failed.push({
					doc: planDocs[i],
					stage: "generate",
					error:
						"superdoc-native batch did not produce this output (see vitest console log above)",
				});
			}
		}
	}
	return { ok, failed, timings: {} };
}

export async function runBatch(
	opts: GenOptions,
): Promise<{ ok: number; failed: Failure[]; timings: Record<string, number> }> {
	if (opts.method === "superdoc-native") return runSuperDocNativeBatch(opts);
	mkdirSync(opts.out, { recursive: true });
	const engine = await loadEngine(opts.method, opts.dist);
	let pairs = parseManifest(
		opts.manifest,
		opts.status ? opts.status.split(",") : [],
	);
	if (opts.limit) pairs = pairs.slice(0, opts.limit);

	let ok = 0;
	const failed: Failure[] = [];
	const timings: Record<string, number> = {};
	try {
		for (const pair of pairs) {
			const doc = `${pair.base}_${pair.next}`;
			const outNames = outputNames(pair, opts.tool);
			const outPaths = outNames.map((n) => join(opts.out, n));
			if (!opts.force && outPaths.every((p) => existsSync(p))) {
				ok += outNames.length;
				continue;
			}
			const basePath = join(opts.sourceDir, `${pair.base}.docx`);
			const nextPath = join(opts.sourceDir, `${pair.next}.docx`);
			if (!existsSync(basePath) || !existsSync(nextPath)) {
				failed.push({
					doc,
					stage: "missing_source",
					error: "source docx not found",
				});
				continue;
			}
			try {
				const t0 = process.hrtime.bigint();
				const bytes = await engine(
					new Uint8Array(readFileSync(basePath)),
					new Uint8Array(readFileSync(nextPath)),
				);
				const elapsedNs = Number(process.hrtime.bigint() - t0);
				for (let i = 0; i < outPaths.length; i++) {
					writeFileSync(outPaths[i], bytes);
					timings[outNames[i].replace(/\.docx$/, "")] = elapsedNs;
				}
				ok += outNames.length;
			} catch (err) {
				failed.push({ doc, stage: "generate", error: (err as Error).message });
			}
		}
	} finally {
		// Engines holding a child process (superdoc-ts) must be torn down or the
		// process never exits — the bench would block on `generate:` forever.
		await engine.dispose?.();
	}
	return { ok, failed, timings };
}

function parseArgs(argv: string[]): GenOptions {
	const get = (flag: string, dflt: string): string => {
		const i = argv.indexOf(flag);
		if (i !== -1 && i + 1 < argv.length) return argv[i + 1];
		const eq = argv.find((a) => a.startsWith(`${flag}=`));
		return eq ? eq.slice(flag.length + 1) : dflt;
	};
	const method = get("--method", "jubarte");
	const limitRaw = get("--limit", "");
	return {
		method,
		dist: get("--dist", "dist/jubarte"),
		out: get(
			"--out",
			process.env.RUN_DIR ? join(process.env.RUN_DIR, "docx") : "out/docx",
		),
		runDir: get("--run-dir", process.env.RUN_DIR ?? "."),
		manifest: get("--manifest", "corpus/word_based/centralized_mapping.csv"),
		sourceDir: get("--source-dir", "corpus/word_based/docx_source"),
		status: get("--status", "ok"),
		limit: limitRaw ? Number(limitRaw) : undefined,
		tool: get("--tool", method),
		force: argv.includes("--force"),
	};
}

const isMain =
	import.meta.url === `file://${process.argv[1]}` ||
	process.argv[1]?.endsWith("generate-native-redlines.ts");
if (isMain) {
	const opts = parseArgs(process.argv.slice(2));
	const { ok, failed, timings } = await runBatch(opts);
	// Persist which docs didn't work to $RUN_DIR/generate_failures.json
	// so the Python bench folds it into the JSONL line.
	writeFileSync(
		join(opts.runDir, "generate_failures.json"),
		JSON.stringify(failed, null, 2),
	);
	writeFileSync(
		join(opts.runDir, "generate_timings.json"),
		JSON.stringify(timings),
	);
	console.log(`[${opts.method}] wrote ${ok} redline(s) → ${opts.out}`);
	if (failed.length) {
		console.error(`[${opts.method}] ${failed.length} pair(s) skipped:`);
		for (const f of failed.slice(0, 10))
			console.error(`  ${f.doc} [${f.stage}]: ${f.error}`);
	}
	// Partial success is fine (produced redlines still get scored); only a total wipeout fails.
	if (ok === 0) process.exitCode = 1;
}
