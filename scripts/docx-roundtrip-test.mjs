#!/usr/bin/env node
/**
 * DOCX → DOCX round-trip capability test for each tool in bench.yaml.
 *
 * For each tool (jubarte-final's two facets, docxodus, docx-redline-js,
 * superdoc-ts), we attempt a direct DOCX→DOCX conversion with one sample
 * document. If that fails, we fall back to DOCX→HTML→DOCX (using the tool's
 * own html export when available, plus soffice for the html→docx leg).
 *
 * The Python `superdoc` tool is tested separately by docx-roundtrip-superdoc.py.
 *
 * Usage:
 *   node scripts/docx-roundtrip-test.mjs [path/to/sample.docx]
 */
import {
	readFileSync,
	writeFileSync,
	mkdirSync,
	rmSync,
	existsSync,
} from "node:fs";
import { resolve, join } from "node:path";
import { tmpdir } from "node:os";
import {
	readBytes,
	toBytes,
	docxIn,
	isValidDocx,
	sofficeConvertTo,
} from "./docx-utils.mjs";

const SAMPLE =
	process.argv[2] ??
	"corpus/word_based/docx_source/1_5_line_spacing_id_paraid_overflow.docx";
const OUT_DIR = "out/roundtrip-test";
const JUBARTE_DIST = "dist/jubarte-final";

mkdirSync(OUT_DIR, { recursive: true });

// ── helpers ──────────────────────────────────────────────────────────────────
// readBytes / toBytes / docxIn / isValidDocx / sofficeConvertTo come from
// ./docx-utils.mjs (imported above). Do NOT redeclare them locally — ESM
// rejects import-name redeclaration at parse time (SyntaxError).

/** Convert an HTML file to DOCX via LibreOffice headless (argv-based, no shell). */
function sofficeHtmlToDocx(htmlPath, docxOutPath) {
	// sofficeConvertTo(srcPath, fmt, wantPath) runs soffice via execFileSync
	// (no shell=True), renames the default output to wantPath, and returns
	// true if wantPath exists afterwards.
	return sofficeConvertTo(resolve(htmlPath), "docx", resolve(docxOutPath));
}

// ── result collector ─────────────────────────────────────────────────────────
const results = [];

function record(tool, route, ok, detail, ms, outPath) {
	results.push({ tool, route, ok, detail, ms, outPath });
	const flag = ok ? "✅" : "❌";
	console.log(
		`${flag} ${tool.padEnd(28)} ${route.padEnd(16)} ${String(ms).padStart(6)}ms  ${detail}`,
	);
}

// ── per-tool attempts ────────────────────────────────────────────────────────

const sample = readBytes(SAMPLE);
console.log(`\nSample: ${SAMPLE}  (${sample.byteLength} bytes)\n`);

// ── 1. jubarte-final-native ──────────────────────────────────────────────────
{
	const tool = "jubarte-final-native";
	const mod = await import(resolve(JUBARTE_DIST, "node.cjs"));

	// Primary: roundtripDocx (pure docx→docx)
	try {
		const t0 = Date.now();
		const out = await toBytes(await mod.roundtripDocx(docxIn(sample)));
		const ms = Date.now() - t0;
		const v = await isValidDocx(out);
		const outPath = join(OUT_DIR, `${tool}.docx`);
		writeFileSync(outPath, out);
		record(
			tool,
			"docx→docx",
			v.ok,
			v.ok ? `valid ${v.size}B` : `invalid: ${v.reason}`,
			ms,
			outPath,
		);
	} catch (e) {
		record(tool, "docx→docx", false, e.message?.slice(0, 150), 0, null);

		// Fallback: docxToHtml → htmlToDocx (both in jubarte)
		try {
			const t0 = Date.now();
			const html = await mod.docxToHtml(docxIn(sample));
			const htmlStr = typeof html === "string" ? html : html.html;
			const out = await toBytes(await mod.htmlToDocx(htmlStr));
			const ms = Date.now() - t0;
			const v = await isValidDocx(out);
			const outPath = join(OUT_DIR, `${tool}_via_html.docx`);
			writeFileSync(outPath, out);
			record(
				tool,
				"docx→html→docx",
				v.ok,
				v.ok ? `valid ${v.size}B` : `invalid: ${v.reason}`,
				ms,
				outPath,
			);
		} catch (e2) {
			record(tool, "docx→html→docx", false, e2.message?.slice(0, 150), 0, null);
		}
	}
}

// ── 2. jubarte-final-lossless ────────────────────────────────────────────────
{
	const tool = "jubarte-final-lossless";
	const mod = await import(resolve(JUBARTE_DIST, "node.cjs"));

	// Primary: compareDocx(base, base) — self-diff → docx
	try {
		const t0 = Date.now();
		const out = await toBytes(
			await mod.compareDocx(docxIn(sample), docxIn(sample)),
		);
		const ms = Date.now() - t0;
		const v = await isValidDocx(out);
		const outPath = join(OUT_DIR, `${tool}.docx`);
		writeFileSync(outPath, out);
		record(
			tool,
			"docx→docx",
			v.ok,
			v.ok ? `valid ${v.size}B` : `invalid: ${v.reason}`,
			ms,
			outPath,
		);
	} catch (e) {
		record(tool, "docx→docx", false, e.message?.slice(0, 150), 0, null);

		// Fallback: docxToHtml → htmlToDocx
		try {
			const t0 = Date.now();
			const html = await mod.docxToHtml(docxIn(sample));
			const htmlStr = typeof html === "string" ? html : html.html;
			const out = await toBytes(await mod.htmlToDocx(htmlStr));
			const ms = Date.now() - t0;
			const v = await isValidDocx(out);
			const outPath = join(OUT_DIR, `${tool}_via_html.docx`);
			writeFileSync(outPath, out);
			record(
				tool,
				"docx→html→docx",
				v.ok,
				v.ok ? `valid ${v.size}B` : `invalid: ${v.reason}`,
				ms,
				outPath,
			);
		} catch (e2) {
			record(tool, "docx→html→docx", false, e2.message?.slice(0, 150), 0, null);
		}
	}
}

// ── 3. docxodus (npm) ────────────────────────────────────────────────────────
{
	const tool = "docxodus";
	const dox = await import(
		// Point at dist/index.js: Node ESM rejects bare directory imports under
		// node_modules when the package uses an "exports" map (docxodus ≥7).
		"../src/neurotic_docx_bench/utils/docxodus/node_modules/docxodus/dist/index.js"
	);
	if (dox.initialize) await dox.initialize();

	// Primary: compareDocuments(base, base) — self-diff
	try {
		const t0 = Date.now();
		const out = await dox.compareDocuments(sample, sample);
		const bytes = out instanceof Uint8Array ? out : new Uint8Array(out);
		const ms = Date.now() - t0;
		const v = await isValidDocx(bytes);
		const outPath = join(OUT_DIR, `${tool}.docx`);
		writeFileSync(outPath, bytes);
		record(
			tool,
			"docx→docx",
			v.ok,
			v.ok ? `valid ${v.size}B` : `invalid: ${v.reason}`,
			ms,
			outPath,
		);
	} catch (e) {
		record(tool, "docx→docx", false, e.message?.slice(0, 150), 0, null);

		// Fallback: convertDocxToHtml → soffice html→docx
		try {
			const t0 = Date.now();
			const html = await dox.convertDocxToHtml(sample);
			const htmlStr =
				typeof html === "string" ? html : (html?.html ?? String(html));
			const htmlPath = join(OUT_DIR, `${tool}.html`);
			writeFileSync(htmlPath, htmlStr);
			const docxPath = join(OUT_DIR, `${tool}_via_html.docx`);
			sofficeHtmlToDocx(htmlPath, docxPath);
			const bytes = readBytes(docxPath);
			const ms = Date.now() - t0;
			const v = await isValidDocx(bytes);
			record(
				tool,
				"docx→html→docx",
				v.ok,
				v.ok ? `valid ${v.size}B` : `invalid: ${v.reason}`,
				ms,
				docxPath,
			);
		} catch (e2) {
			record(tool, "docx→html→docx", false, e2.message?.slice(0, 150), 0, null);
		}
	}
}

// ── 4. docx-redline-js (npm) ─────────────────────────────────────────────────
{
	const tool = "docx-redline-js";
	const [JSZipMod, xmldom, rl] = await Promise.all([
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
	const toText = (xml) => {
		const t = rl.ingestWordOoxmlToPlainText(xml);
		return typeof t === "string" ? t : (t?.text ?? "");
	};

	// Primary: applyRedlineToOxml(baseXml, baseText, baseText) — self-diff → patched zip
	try {
		const t0 = Date.now();
		const zip = await JSZip.loadAsync(sample);
		const docXml = await zip.file("word/document.xml").async("string");
		const text = toText(docXml);
		const res = await rl.applyRedlineToOxml(docXml, text, text, {
			generateRedlines: true,
			author: "bench",
		});
		zip.file("word/document.xml", res.oxml ?? res.ooxml);
		const bytes = await zip.generateAsync({ type: "uint8array" });
		const ms = Date.now() - t0;
		const v = await isValidDocx(bytes);
		const outPath = join(OUT_DIR, `${tool}.docx`);
		writeFileSync(outPath, bytes);
		record(
			tool,
			"docx→docx",
			v.ok,
			v.ok ? `valid ${v.size}B` : `invalid: ${v.reason}`,
			ms,
			outPath,
		);
	} catch (e) {
		record(tool, "docx→docx", false, e.message?.slice(0, 150), 0, null);

		// Fallback: docx-redline-js has no html export; use soffice for docx→html→docx
		try {
			const t0 = Date.now();
			const docxPath = join(OUT_DIR, `${tool}_src.docx`);
			writeFileSync(docxPath, sample);
			// soffice docx→html (argv-based via sofficeConvertTo, no shell=True)
			const htmlPath = join(OUT_DIR, `${tool}_src.html`);
			rmSync(htmlPath, { force: true });
			sofficeConvertTo(resolve(docxPath), "html", htmlPath);
			const docxOut = join(OUT_DIR, `${tool}_via_html.docx`);
			sofficeHtmlToDocx(htmlPath, docxOut);
			const bytes = readBytes(docxOut);
			const ms = Date.now() - t0;
			const v = await isValidDocx(bytes);
			record(
				tool,
				"docx→html→docx",
				v.ok,
				v.ok ? `valid ${v.size}B (via soffice)` : `invalid: ${v.reason}`,
				ms,
				docxOut,
			);
		} catch (e2) {
			record(tool, "docx→html→docx", false, e2.message?.slice(0, 150), 0, null);
		}
	}
}

// ── 5. superdoc-ts (npm) ─────────────────────────────────────────────────────
{
	const tool = "superdoc-ts";
	const [{ SuperDocClient }, os, fs, path] = await Promise.all([
		import(
			"../src/neurotic_docx_bench/utils/superdoc/node_modules/@superdoc-dev/sdk"
		),
		import("node:os"),
		import("node:fs"),
		import("node:path"),
	]);
	const client = new SuperDocClient({
		user: { name: "bench", email: "b@b.b" },
	});
	const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "sd-rt-"));
	const bp = path.join(tmp, "b.docx");
	const op = path.join(tmp, "o.docx");
	fs.writeFileSync(bp, sample);

	// Primary: open → save (pure round-trip)
	try {
		const t0 = Date.now();
		const s = await client.open({ sessionId: "rt", doc: bp });
		await s.save({ out: op, force: true });
		await s.close({});
		const bytes = new Uint8Array(fs.readFileSync(op));
		const ms = Date.now() - t0;
		const v = await isValidDocx(bytes);
		const outPath = join(OUT_DIR, `${tool}.docx`);
		writeFileSync(outPath, bytes);
		record(
			tool,
			"docx→docx",
			v.ok,
			v.ok ? `valid ${v.size}B` : `invalid: ${v.reason}`,
			ms,
			outPath,
		);
	} catch (e) {
		record(tool, "docx→docx", false, e.message?.slice(0, 150), 0, null);

		// Fallback: soffice docx→html→docx (superdoc-ts has no html export in this API)
		try {
			const t0 = Date.now();
			const docxPath = join(OUT_DIR, `${tool}_src.docx`);
			writeFileSync(docxPath, sample);
			// soffice docx→html (argv-based via sofficeConvertTo, no shell=True)
			const htmlPath = join(OUT_DIR, `${tool}_src.html`);
			rmSync(htmlPath, { force: true });
			sofficeConvertTo(resolve(docxPath), "html", htmlPath);
			const docxOut = join(OUT_DIR, `${tool}_via_html.docx`);
			sofficeHtmlToDocx(htmlPath, docxOut);
			const bytes = readBytes(docxOut);
			const ms = Date.now() - t0;
			const v = await isValidDocx(bytes);
			record(
				tool,
				"docx→html→docx",
				v.ok,
				v.ok ? `valid ${v.size}B (via soffice)` : `invalid: ${v.reason}`,
				ms,
				docxOut,
			);
		} catch (e2) {
			record(tool, "docx→html→docx", false, e2.message?.slice(0, 150), 0, null);
		}
	} finally {
		fs.rmSync(tmp, { recursive: true, force: true });
	}
}

// ── summary ──────────────────────────────────────────────────────────────────
console.log("\n" + "─".repeat(80));
console.log("SUMMARY");
console.log("─".repeat(80));
for (const r of results) {
	console.log(
		`  ${r.ok ? "✅" : "❌"}  ${r.tool.padEnd(28)} ${r.route.padEnd(16)} ${r.detail}`,
	);
}
const okCount = results.filter((r) => r.ok).length;
console.log(`\n  ${okCount}/${results.length} conversions succeeded.`);
process.exit(0);
