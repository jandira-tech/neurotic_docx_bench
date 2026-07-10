#!/usr/bin/env node
/**
 * DOCX → HTML → DOCX round-trip for the two tools whose direct docx→docx
 * round-trip produced a byte-identical word/document.xml (a no-op re-zip):
 *
 *   • jubarte-final-native  → uses jubarte's own docxToHtml + htmlToDocx
 *   • docx-redline-js       → has no HTML export; uses soffice for both legs
 *
 * Outputs land in out/roundtrip-test/*_via_html.docx and we verify that
 * word/document.xml is now genuinely re-serialised (different MD5).
 *
 * Usage:
 *   node scripts/docx-roundtrip-html.mjs [path/to/sample.docx]
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import {
	readBytes,
	toBytes,
	docxIn,
	docXmlMd5,
	isValidDocx,
	sofficeConvertTo,
} from "./docx-utils.mjs";

const SAMPLE =
	process.argv[2] ??
	"corpus/word_based/docx_source/1_5_line_spacing_id_paraid_overflow.docx";
const OUT_DIR = "out/roundtrip-test";
const JUBARTE_DIST = "dist/jubarte-final";

mkdirSync(OUT_DIR, { recursive: true });

// ── main ─────────────────────────────────────────────────────────────────────

const sample = readBytes(SAMPLE);
const origMd5 = await docXmlMd5(sample);
console.log(`\nSample: ${SAMPLE}  (${sample.byteLength} bytes)`);
console.log(`Original word/document.xml MD5: ${origMd5}\n`);

const results = [];

// ── 1. jubarte-final-native: docxToHtml → htmlToDocx (jubarte's own) ─────────
{
	const tool = "jubarte-final-native";
	const mod = await import(resolve(JUBARTE_DIST, "node.cjs"));
	try {
		const t0 = Date.now();
		// DOCX → HTML (jubarte's own converter)
		const htmlOut = await mod.docxToHtml(docxIn(sample));
		const htmlStr =
			typeof htmlOut === "string"
				? htmlOut
				: (htmlOut?.html ?? String(htmlOut));
		// Save HTML for inspection
		writeFileSync(join(OUT_DIR, `${tool}.html`), htmlStr);

		// HTML → DOCX (jubarte's own converter)
		const out = await toBytes(await mod.htmlToDocx(htmlStr));
		const ms = Date.now() - t0;
		const v = await isValidDocx(out);
		const outPath = join(OUT_DIR, `${tool}_via_html.docx`);
		writeFileSync(outPath, out);

		const newMd5 = await docXmlMd5(out);
		const changed = newMd5 !== origMd5;
		results.push({
			tool,
			route: "docx→html→docx (jubarte)",
			ok: v.ok && changed,
			outPath,
		});
		console.log(
			`${v.ok && changed ? "✅" : "❌"} ${tool.padEnd(28)} docx→html→docx (jubarte)  ` +
				`${v.ok ? `valid ${v.size}B` : `invalid: ${v.reason}`}  ` +
				`doc.xml changed: ${changed ? "YES ✅" : "NO ⚠️"}  ${ms}ms`,
		);
	} catch (e) {
		results.push({
			tool,
			route: "docx→html→docx (jubarte)",
			ok: false,
			outPath: null,
		});
		console.log(
			`❌ ${tool.padEnd(28)} docx→html→docx (jubarte)  ${e.message?.slice(0, 150)}`,
		);
	}
}

// ── 2. docx-redline-js: soffice docx→html, soffice html→docx ─────────────────
{
	const tool = "docx-redline-js";
	// docx-redline-js has no HTML export of its own, so we use soffice for
	// both legs — this still exercises a genuine re-serialisation.
	try {
		const t0 = Date.now();
		const srcDocx = join(OUT_DIR, `${tool}_src.docx`);
		writeFileSync(srcDocx, sample);

		// DOCX → HTML (soffice)
		const wantHtml = join(OUT_DIR, `${tool}.html`);
		if (!sofficeConvertTo(srcDocx, "html", wantHtml))
			throw new Error("soffice docx→html failed");

		// HTML → DOCX (soffice)
		// HTML import requires the explicit StarWriter infilter or soffice silently produces no output
		const wantDocx = join(OUT_DIR, `${tool}_via_html.docx`);
		if (!sofficeConvertTo(wantHtml, "docx", wantDocx, "HTML (StarWriter)"))
			throw new Error("soffice html→docx failed");

		const out = readBytes(wantDocx);
		const ms = Date.now() - t0;
		const v = await isValidDocx(out);
		const newMd5 = await docXmlMd5(out);
		const changed = newMd5 !== origMd5;
		results.push({
			tool,
			route: "docx→html→docx (soffice)",
			ok: v.ok && changed,
			outPath: wantDocx,
		});
		console.log(
			`${v.ok && changed ? "✅" : "❌"} ${tool.padEnd(28)} docx→html→docx (soffice)  ` +
				`${v.ok ? `valid ${v.size}B` : `invalid: ${v.reason}`}  ` +
				`doc.xml changed: ${changed ? "YES ✅" : "NO ⚠️"}  ${ms}ms`,
		);
	} catch (e) {
		results.push({
			tool,
			route: "docx→html→docx (soffice)",
			ok: false,
			outPath: null,
		});
		console.log(
			`❌ ${tool.padEnd(28)} docx→html→docx (soffice)  ${e.message?.slice(0, 150)}`,
		);
	}
}

// ── summary ──────────────────────────────────────────────────────────────────
console.log("\n" + "─".repeat(80));
console.log(
	"SUMMARY — docx→html→docx re-serialisation for the two no-op tools",
);
console.log("─".repeat(80));
for (const r of results) {
	console.log(
		`  ${r.ok ? "✅" : "❌"}  ${r.tool.padEnd(28)} ${r.route.padEnd(28)} ` +
			`${r.ok ? "→ " + r.outPath : ""}`,
	);
}
process.exit(0);
