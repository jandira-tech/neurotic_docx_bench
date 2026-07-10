/**
 * Shared DOCX byte-munging helpers used by the Node redline/roundtrip generators
 * and diagnostic scripts (generate-native-redlines.ts, generate-roundtrips.mjs,
 * docx-roundtrip-test.mjs, docx-roundtrip-html.mjs).
 *
 * Plain ESM (not TypeScript) so it can be imported both by `.ts` files running
 * under `node --import tsx` and by the `.mjs` scripts that are invoked directly
 * via plain `node` (no tsx loader).
 */
import { existsSync, readFileSync, rmSync, renameSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { basename, join, resolve } from "node:path";
import { createHash } from "node:crypto";

/** Read a file as Uint8Array. */
export const readBytes = (p) => new Uint8Array(readFileSync(p));

/** Normalise various engine return shapes into a Uint8Array. */
export const toBytes = async (out) => {
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
export const docxIn = (bytes) => ({ buffer: bytes });

/** MD5 of the word/document.xml entry inside a DOCX (Uint8Array or path). */
export async function docXmlMd5(bytesOrPath) {
	const bytes =
		typeof bytesOrPath === "string" ? readBytes(bytesOrPath) : bytesOrPath;
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
export async function isValidDocx(bytes) {
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

/** soffice headless convert; returns the produced output path or null. */
export function sofficeConvert(srcPath, fmt, outDir, infilter) {
	outDir = resolve(outDir);
	const expected = join(
		outDir,
		basename(srcPath).replace(/\.[^.]+$/, `.${fmt}`),
	);
	rmSync(expected, { force: true });
	const args = ["--headless"];
	if (infilter) {
		args.push(`--infilter=${infilter}`);
	}
	args.push("--convert-to", fmt, "--outdir", outDir, resolve(srcPath));
	execFileSync("soffice", args, { stdio: "pipe", timeout: 60_000 });
	return existsSync(expected) ? expected : null;
}

/**
 * Like sofficeConvert, but moves the result to `wantPath` if soffice's
 * default output name (derived from srcPath's stem) differs from it.
 * Returns true if `wantPath` exists afterwards.
 */
export function sofficeConvertTo(srcPath, fmt, wantPath, infilter) {
	const outPath = sofficeConvert(
		srcPath,
		fmt,
		resolve(wantPath, ".."),
		infilter,
	);
	if (outPath && resolve(outPath) !== resolve(wantPath)) {
		rmSync(wantPath, { force: true });
		renameSync(resolve(outPath), resolve(wantPath));
	}
	return existsSync(wantPath);
}
