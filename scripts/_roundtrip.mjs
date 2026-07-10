import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const [, , method, dist, inPath, outPath] = process.argv;
const base = new Uint8Array(readFileSync(inPath));

const toBytes = async (out) => {
	if (out instanceof Uint8Array) return out;
	if (out?.docx instanceof Uint8Array) return out.docx;
	if (out?.bytes instanceof Uint8Array) return out.bytes;
	if (typeof out?.arrayBuffer === "function")
		return new Uint8Array(await out.arrayBuffer());
	return new Uint8Array(out);
};

const docxIn = (bytes) => ({ buffer: bytes });

async function loadEngine(method, dist) {
	if (method === "jubarte-native") {
		const mod = await import(resolve(dist, "node.cjs"));
		return async (b, n) => {
			const cm = await mod.redlineDocx(docxIn(b), docxIn(n), {
				author: "bench",
			});
			if (cm == null) return b;
			return toBytes(await mod.redlineToDocx(cm));
		};
	}
	if (method === "jubarte-lossless") {
		const mod = await import(resolve(dist, "node.cjs"));
		return async (b, n) => toBytes(await mod.compareDocx(docxIn(b), docxIn(n)));
	}
	if (method === "docxodus") {
		const dox = await import(
			// Point at dist/index.js: Node ESM rejects bare directory imports under
			// node_modules when the package uses an "exports" map (docxodus ≥7).
			"../src/neurotic_docx_bench/utils/docxodus/node_modules/docxodus/dist/index.js"
		);
		if (dox.initialize) await dox.initialize();
		return async (b, n) => {
			const out = await dox.compareDocuments(b, n);
			return out instanceof Uint8Array ? out : new Uint8Array(out);
		};
	}
	if (method === "docx-redline-js") {
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
		return async (b, n) => {
			const baseZip = await JSZip.loadAsync(b);
			const baseXml = await baseZip.file("word/document.xml").async("string");
			const nextZip = await JSZip.loadAsync(n);
			const nextXml = await nextZip.file("word/document.xml").async("string");
			const res = await rl.applyRedlineToOxml(
				baseXml,
				toText(baseXml),
				toText(nextXml),
				{
					generateRedlines: true,
					author: "bench",
				},
			);
			baseZip.file("word/document.xml", res.oxml ?? res.ooxml);
			return baseZip.generateAsync({ type: "uint8array" });
		};
	}
	if (method === "superdoc-ts") {
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
		const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "sd-"));
		return async (b, n) => {
			const bp = path.join(tmp, "b.docx"),
				np = path.join(tmp, "n.docx"),
				op = path.join(tmp, "o.docx");
			fs.writeFileSync(bp, b);
			fs.writeFileSync(np, n);
			try {
				const bs = await client.open({ sessionId: "b", doc: bp });
				const ns = await client.open({ sessionId: "n", doc: np });
				const snap = await ns.diff.capture({});
				await ns.close({});
				const d = await bs.diff.compare({ targetSnapshot: snap });
				await bs.diff.apply({ diff: d, changeMode: "tracked" });
				await bs.save({ out: op, force: true });
				await bs.close({});
				return new Uint8Array(fs.readFileSync(op));
			} finally {
				for (const f of [bp, np, op]) fs.rmSync(f, { force: true });
			}
		};
	}
	throw new Error("unknown method: " + method);
}

try {
	const engine = await loadEngine(method, dist);
	const t0 = Date.now();
	const out = await engine(base, base);
	const ms = Date.now() - t0;
	writeFileSync(outPath, out);
	console.log(`OK bytes=${out.byteLength} ms=${ms}`);
} catch (e) {
	console.log(`ERR ${e.message?.slice(0, 200)}`);
	process.exit(2);
}
