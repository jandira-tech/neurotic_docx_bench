/**
 * Node OOXML package adapter for jubarte's "lossless" `WmlComparer` port.
 *
 * jubarte's lossless engine (`lossless.node.cjs`) ports the OpenXmlPowerTools
 * `WmlComparer` faithfully, but leaves its packaging I/O (open a docx, read/write
 * parts, zip it back up) behind several injectable seams — the comparison
 * algorithm is package-agnostic; something has to supply the actual zip/XML I/O.
 * This module IS that supplier for Node, built entirely from primitives jubarte
 * itself ships (`PartFS`, `unzipSync`, `parseXDocument` — found by scanning
 * `lossless.node.cjs`'s own `require()` calls, so this stays correct even when
 * the internal chunk filenames change hash between builds).
 *
 * Plain .mjs (not .ts): generate-roundtrips.mjs runs under plain `node` (no
 * tsx/TS loader), so this module has to be importable from both that script
 * and generate-native-redlines.ts without a build step.
 *
 * Verified against the full corpus (`corpus/word_based/centralized_mapping.csv`,
 * 207 pairs) — 207/207 produce non-empty `w:ins`/`w:del` output.
 */

import { readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";

const REL_BASE =
	"http://schemas.openxmlformats.org/officeDocument/2006/relationships";
const STRICT_REL_PREFIX =
	"http://purl.oclc.org/ooxml/officeDocument/relationships";

function normalize(uri) {
	return uri.startsWith("/") ? uri.slice(1) : uri;
}

function normalizeRelType(type) {
	return type.startsWith(STRICT_REL_PREFIX)
		? REL_BASE + type.slice(STRICT_REL_PREFIX.length)
		: type;
}

function decodeXmlEntities(s) {
	if (!s.includes("&")) return s;
	return s
		.replace(/&#(\d+);/g, (_, dec) => String.fromCodePoint(Number(dec)))
		.replace(/&#x([0-9a-fA-F]+);/g, (_, hex) =>
			String.fromCodePoint(Number.parseInt(hex, 16)),
		)
		.replace(/&amp;/g, "&")
		.replace(/&lt;/g, "<")
		.replace(/&gt;/g, ">")
		.replace(/&apos;/g, "'")
		.replace(/&quot;/g, '"');
}

function relsUriFor(partUri) {
	const norm = normalize(partUri);
	const slash = norm.lastIndexOf("/");
	const dir = slash >= 0 ? norm.slice(0, slash) : "";
	const file = slash >= 0 ? norm.slice(slash + 1) : norm;
	return dir.length > 0 ? `${dir}/_rels/${file}.rels` : `_rels/${file}.rels`;
}

function readPartRels(fs, partUri) {
	const bytes = fs.read(relsUriFor(partUri));
	if (bytes.length === 0) return [];
	const xml = new TextDecoder("utf-8").decode(bytes);
	const out = [];
	const re = /<Relationship\b[^>]*>/g;
	let m;
	while ((m = re.exec(xml)) != null) {
		const tag = m[0];
		const id = /\bId\s*=\s*"([^"]*)"/.exec(tag);
		const type = /\bType\s*=\s*"([^"]*)"/.exec(tag);
		const target = /\bTarget\s*=\s*"([^"]*)"/.exec(tag);
		const mode = /\bTargetMode\s*=\s*"([^"]*)"/.exec(tag);
		if (id && type && target) {
			out.push({
				id: decodeXmlEntities(id[1]),
				type: normalizeRelType(decodeXmlEntities(type[1])),
				target: decodeXmlEntities(target[1]),
				external: mode != null && mode[1] === "External",
			});
		}
	}
	return out;
}

function resolveRelTarget(basePartUri, target) {
	if (target.startsWith("/")) return normalize(target);
	const norm = normalize(basePartUri);
	const slash = norm.lastIndexOf("/");
	const dir = slash >= 0 ? norm.slice(0, slash) : "";
	const baseSegs = dir.length > 0 ? dir.split("/") : [];
	for (const seg of target.split("/")) {
		if (seg === "" || seg === ".") continue;
		if (seg === "..") baseSegs.pop();
		else baseSegs.push(seg);
	}
	return baseSegs.join("/");
}

function contentTypeFor(fs, partUri) {
	const norm = normalize(partUri);
	const ext = norm.slice(norm.lastIndexOf(".") + 1).toLowerCase();
	const ctXml = new TextDecoder("utf-8").decode(fs.read("[Content_Types].xml"));
	const overrideRe = /<(?:[A-Za-z_][\w.-]*:)?Override\b([^>]*)>/gi;
	for (const m of ctXml.matchAll(overrideRe)) {
		const pn = /\bPartName\s*=\s*"([^"]*)"/.exec(m[1]);
		const ct = /\bContentType\s*=\s*"([^"]*)"/.exec(m[1]);
		if (pn && pn[1] === `/${norm}`) return ct ? ct[1] : "application/xml";
	}
	const defaultRe = /<(?:[A-Za-z_][\w.-]*:)?Default\b([^>]*)>/gi;
	for (const m of ctXml.matchAll(defaultRe)) {
		const extAttr = /\bExtension\s*=\s*"([^"]*)"/.exec(m[1]);
		const ct = /\bContentType\s*=\s*"([^"]*)"/.exec(m[1]);
		if (extAttr && extAttr[1].toLowerCase() === ext)
			return ct ? ct[1] : "application/xml";
	}
	return "application/xml";
}

function addRelationship(fs, basePartUri, type, target) {
	const relsUri = relsUriFor(basePartUri);
	const bytes = fs.read(relsUri);
	const existing = bytes.length
		? new TextDecoder("utf-8").decode(bytes)
		: '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>';
	const ids = [...existing.matchAll(/\bId="rId(\d+)"/g)].map((m) =>
		Number(m[1]),
	);
	const nextId = `rId${ids.length ? Math.max(...ids) + 1 : 1}`;
	const rel = `<Relationship Id="${nextId}" Type="${type}" Target="${target}"/>`;
	const updated = existing.includes("</Relationships>")
		? existing.replace("</Relationships>", rel + "</Relationships>")
		: existing.replace("/>", `>${rel}</Relationships>`);
	fs.write(relsUri, new TextEncoder().encode(updated));
	return nextId;
}

function addRelationshipWithId(fs, basePartUri, id, type, target, external) {
	const relsUri = relsUriFor(basePartUri);
	const bytes = fs.read(relsUri);
	const existing = bytes.length
		? new TextDecoder("utf-8").decode(bytes)
		: '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>';
	const mode = external ? ' TargetMode="External"' : "";
	const rel = `<Relationship Id="${id}" Type="${type}" Target="${target}"${mode}/>`;
	const updated = existing.includes("</Relationships>")
		? existing.replace("</Relationships>", rel + "</Relationships>")
		: existing.replace("/>", `>${rel}</Relationships>`);
	fs.write(relsUri, new TextEncoder().encode(updated));
}

function addContentTypeOverride(fs, partUri, contentType) {
	const ctXml = new TextDecoder("utf-8").decode(fs.read("[Content_Types].xml"));
	const override = `<Override PartName="/${normalize(partUri)}" ContentType="${contentType}"/>`;
	const updated = ctXml.replace("</Types>", override + "</Types>");
	fs.write("[Content_Types].xml", new TextEncoder().encode(updated));
}

function partForRel(fs, basePartUri, rel) {
	const targetUri = resolveRelTarget(basePartUri, rel.target);
	if (fs.read(targetUri).length === 0) return null;
	return new NodeOpenXmlPart(fs, targetUri);
}

// --- IPartStream / OpenXmlPart stand-ins, backed by PartFS -------------------

class NodePartStream {
	constructor(fs, uri) {
		this.fs = fs;
		this.uri = uri;
	}
	get Length() {
		return this.fs.read(this.uri).length;
	}
	ReadAllBytes() {
		return this.fs.read(this.uri);
	}
	WriteAllBytes(bytes) {
		this.fs.write(this.uri, bytes);
	}
	ReadToEnd() {
		return new TextDecoder("utf-8").decode(this.fs.read(this.uri));
	}
}

class NodeOpenXmlPart {
	constructor(fs, uri, contentType) {
		this.fs = fs;
		this._uri = normalize(uri);
		this.Uri = { toString: () => `/${this._uri}` };
		this.ContentType = contentType ?? contentTypeFor(fs, uri);
		this._annotations = new Map();
		this.OpenXmlPackage = null;
	}
	GetStream() {
		return new NodePartStream(this.fs, this._uri);
	}
	GetStreamCreate() {
		return new NodePartStream(this.fs, this._uri);
	}
	FeedData(bytes) {
		this.fs.write(this._uri, bytes);
	}
	Annotation(ctor) {
		return this._annotations.get(ctor) ?? null;
	}
	AddAnnotation(annotation) {
		this._annotations.set(annotation?.constructor, annotation);
	}
	RemoveAnnotations(ctor) {
		this._annotations.delete(ctor);
	}
	get Parts() {
		return [];
	}
	get HeaderParts() {
		return [];
	}
	get FooterParts() {
		return [];
	}
	get FootnotesPart() {
		return null;
	}
	get EndnotesPart() {
		return null;
	}
	get WordprocessingCommentsPart() {
		return null;
	}
}

class NodeMainDocumentPart extends NodeOpenXmlPart {
	constructor(fs) {
		super(
			fs,
			"word/document.xml",
			"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml",
		);
		const rels = readPartRels(fs, "word/document.xml").filter(
			(r) => !r.external,
		);
		const byType = (t) =>
			rels
				.filter((r) => r.type === `${REL_BASE}/${t}`)
				.map((r) => partForRel(fs, "word/document.xml", r))
				.filter((p) => p != null);
		this._headerParts = byType("header");
		this._footerParts = byType("footer");
		this._footnotesPart = byType("footnotes")[0] ?? null;
		this._endnotesPart = byType("endnotes")[0] ?? null;
		this._commentsPart = byType("comments")[0] ?? null;
	}
	get HeaderParts() {
		return this._headerParts;
	}
	get FooterParts() {
		return this._footerParts;
	}
	get FootnotesPart() {
		return this._footnotesPart;
	}
	set FootnotesPart(part) {
		this._footnotesPart = part;
	}
	get EndnotesPart() {
		return this._endnotesPart;
	}
	set EndnotesPart(part) {
		this._endnotesPart = part;
	}
	get WordprocessingCommentsPart() {
		return this._commentsPart;
	}
	set WordprocessingCommentsPart(part) {
		this._commentsPart = part;
	}
}

class NodeWordprocessingDocument {
	constructor(fs) {
		this.fs = fs;
		this.MainDocumentPart = new NodeMainDocumentPart(fs);
		const md = this.MainDocumentPart;
		const parts = [
			md,
			...md.HeaderParts,
			...md.FooterParts,
			...(md.FootnotesPart ? [md.FootnotesPart] : []),
			...(md.EndnotesPart ? [md.EndnotesPart] : []),
		];
		for (const part of parts) part.OpenXmlPackage = this;
	}
}

// --- IPkg / IPkgPart stand-ins (the richer Package surface WmlComparer's
// move/relocation code touches) -----------------------------------------------

class NodePkgPart {
	constructor(pkg, fs, uri, contentType) {
		this.Package = pkg;
		this.fs = fs;
		this._uri = normalize(uri);
		this.Uri = { toString: () => `/${this._uri}` };
		this.ContentType = contentType ?? contentTypeFor(fs, uri);
	}
	GetStream() {
		return new NodePartStream(this.fs, this._uri);
	}
	GetRelationship(id) {
		const rel = readPartRels(this.fs, this._uri).find((r) => r.id === id);
		if (!rel) return null;
		return {
			Id: rel.id,
			TargetUri: { toString: () => rel.target },
			RelationshipType: rel.type,
		};
	}
	CreateRelationship(targetUri, targetMode, relationshipType, id) {
		addRelationshipWithId(
			this.fs,
			this._uri,
			id,
			relationshipType,
			targetUri,
			targetMode === "External",
		);
	}
}

class NodePkg {
	constructor(fs) {
		this.fs = fs;
	}
	GetPart(uri) {
		return new NodePkgPart(this, this.fs, uri);
	}
	GetParts() {
		return [...this.fs.entries.keys()].map(
			(name) => new NodePkgPart(this, this.fs, name),
		);
	}
	CreatePart(uri, contentType) {
		const norm = normalize(uri);
		this.fs.write(norm, new Uint8Array(0));
		addContentTypeOverride(this.fs, norm, contentType);
		return new NodePkgPart(this, this.fs, norm, contentType);
	}
}

/**
 * Find jubarte's internal `PartFS` / `unzipSync` / `parseXDocument` exports by
 * scanning `lossless.node.cjs`'s own `require()` calls, rather than hard-coding
 * the internal chunk's content-hashed filename (which changes every build).
 */
function findInternalPrimitives(losslessCjsPath, req) {
	const src = readFileSync(losslessCjsPath, "utf8");
	const chunkPaths = [
		...src.matchAll(/require\((['"])(\.\/[^'"]+\.cjs)\1\)/g),
	].map((m) => m[2]);

	// Pass 1 ─ classic named exports (older jubarte builds).
	for (const rel of chunkPaths) {
		const mod = req(rel);
		if (
			mod &&
			typeof mod.PartFS === "function" &&
			typeof mod.unzipSync === "function" &&
			typeof mod.parseXDocument === "function"
		) {
			return mod;
		}
	}

	// Pass 2 ─ shape-based detection (newer jubarte builds whose CJS exports
	// are minified to single-letter names).  PartFS is the most distinctive:
	// a constructor whose prototype carries read / write / toZip.  Once we
	// find it, we probe the *same* chunk for parseXDocument (test-call with
	// "<r/>") and unzipSync (test-call with a minimal empty ZIP).
	const EMPTY_ZIP = new Uint8Array(22);
	new DataView(EMPTY_ZIP.buffer).setUint32(0, 0x06054b50, true);

	for (const rel of chunkPaths) {
		const mod = req(rel);
		if (!mod) continue;

		// Find PartFS by prototype shape.
		let PartFS = null;
		for (const k of Object.keys(mod)) {
			const v = mod[k];
			if (
				typeof v === "function" &&
				v.prototype &&
				typeof v.prototype.read === "function" &&
				typeof v.prototype.write === "function" &&
				typeof v.prototype.toZip === "function"
			) {
				PartFS = v;
				break;
			}
		}
		if (!PartFS) continue;

		// Now find parseXDocument + unzipSync in this same chunk.
		let parseXDocument = null;
		let unzipSync = null;
		for (const k of Object.keys(mod)) {
			const v = mod[k];
			if (typeof v !== "function" || v === PartFS) continue;

			if (!parseXDocument) {
				try {
					const doc = v("<r/>");
					if (doc && doc.Root !== undefined) {
						parseXDocument = v;
						continue;
					}
				} catch {
					/* not an XML parser */
				}
			}

			if (!unzipSync) {
				try {
					const result = v(EMPTY_ZIP);
					if (result && typeof result === "object") {
						unzipSync = v;
					}
				} catch {
					/* not a ZIP unpacker */
				}
			}
		}

		if (PartFS && unzipSync && parseXDocument) {
			return { PartFS, unzipSync, parseXDocument };
		}
	}

	throw new Error(
		`jubarte-lossless-adapter: could not find PartFS/unzipSync/parseXDocument among ` +
			`${losslessCjsPath}'s required chunks (checked: ${chunkPaths.join(", ")})`,
	);
}

let wired = null;

/**
 * Wire jubarte's lossless `WmlComparer` (and its supporting subsystems) to a
 * working Node OOXML adapter, idempotently. Call this once with the loaded
 * `lossless.node.cjs` module before using `WmlComparer.Compare` /
 * `DocumentComparer.CompareDocuments`.
 */
export function wireJubarteLosslessAdapter(lossless, losslessCjsPath) {
	if (wired === lossless) return; // already wired for this exact module instance
	const req = createRequire(losslessCjsPath);
	const { PartFS, unzipSync, parseXDocument } = findInternalPrimitives(
		losslessCjsPath,
		req,
	);

	const {
		setWmlComparerPackageBoundary,
		setXmlParser,
		setFormattingAssemblerMemoryStreamDocumentFactory,
		setRevisionProcessorMemoryStreamDocumentFactory,
		setWmlToXmlMemoryStreamDocumentFactory,
		setOpenXmlPackageProvider,
		WmlDocument,
	} = lossless;
	for (const [name, fn] of Object.entries({
		setWmlComparerPackageBoundary,
		setXmlParser,
		setFormattingAssemblerMemoryStreamDocumentFactory,
		setRevisionProcessorMemoryStreamDocumentFactory,
		setWmlToXmlMemoryStreamDocumentFactory,
		setOpenXmlPackageProvider,
	})) {
		if (typeof fn !== "function") {
			throw new Error(
				`jubarte-lossless-adapter: ${losslessCjsPath} does not export ${name} — ` +
					"this jubarte build is missing a wiring point this adapter depends on.",
			);
		}
	}

	setXmlParser(parseXDocument);

	// ── The rich packaging boundary WmlComparer's internals delegate to. ──────
	setWmlComparerPackageBoundary({
		openWordprocessingDocument(bytes) {
			return new NodeWordprocessingDocument(new PartFS(unzipSync(bytes)));
		},
		getModifiedBytes(wDoc) {
			return wDoc.fs.toZip();
		},
		contentParts(wDoc) {
			const md = wDoc.MainDocumentPart;
			return [
				md,
				...md.HeaderParts,
				...md.FooterParts,
				...(md.FootnotesPart ? [md.FootnotesPart] : []),
				...(md.EndnotesPart ? [md.EndnotesPart] : []),
			];
		},
		allXmlParts(wDoc) {
			const out = [];
			for (const [name] of wDoc.fs.entries) {
				if (name.endsWith(".xml") && !name.endsWith(".rels")) {
					const part = new NodeOpenXmlPart(wDoc.fs, name);
					part.OpenXmlPackage = wDoc;
					out.push(part);
				}
			}
			return out;
		},
		rootElement(part) {
			const xml = new TextDecoder("utf-8").decode(part.fs.read(part._uri));
			return parseXDocument(xml).Root;
		},
		chartParts() {
			return [];
		},
		styleDefinitionsPart(mainPart) {
			const rels = readPartRels(mainPart.fs, "word/document.xml").filter(
				(r) => r.type === `${REL_BASE}/styles`,
			);
			const existing = rels.length
				? partForRel(mainPart.fs, "word/document.xml", rels[0])
				: null;
			if (existing != null) return existing;
			// `StyleDefinitionsPart` is non-nullable in the boundary interface: when
			// neither source carries a styles part, materialize an empty one so
			// downstream code (AddFootnotesEndnotesStyles) can still seed a root.
			const uri = "word/styles.xml";
			const ct =
				"application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml";
			mainPart.fs.write(uri, new Uint8Array(0));
			addContentTypeOverride(mainPart.fs, uri, ct);
			addRelationship(
				mainPart.fs,
				"word/document.xml",
				`${REL_BASE}/styles`,
				"styles.xml",
			);
			const part = new NodeOpenXmlPart(mainPart.fs, uri, ct);
			part.OpenXmlPackage = mainPart.OpenXmlPackage;
			return part;
		},
		documentSettingsPart(mainPart) {
			const rels = readPartRels(mainPart.fs, "word/document.xml").filter(
				(r) => r.type === `${REL_BASE}/settings`,
			);
			return rels.length
				? partForRel(mainPart.fs, "word/document.xml", rels[0])
				: null;
		},
		numberingDefinitionsPart(mainPart) {
			const rels = readPartRels(mainPart.fs, "word/document.xml").filter(
				(r) => r.type === `${REL_BASE}/numbering`,
			);
			return rels.length
				? partForRel(mainPart.fs, "word/document.xml", rels[0])
				: null;
		},
		addNewNumberingDefinitionsPart(mainPart) {
			const uri = "word/numbering.xml";
			const ct =
				"application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml";
			mainPart.fs.write(
				uri,
				new TextEncoder().encode(
					'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>',
				),
			);
			addContentTypeOverride(mainPart.fs, uri, ct);
			addRelationship(
				mainPart.fs,
				"word/document.xml",
				`${REL_BASE}/numbering`,
				"numbering.xml",
			);
			return new NodeOpenXmlPart(mainPart.fs, uri, ct);
		},
		addNewFootnotesPart(mainPart) {
			const uri = "word/footnotes.xml";
			const ct =
				"application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml";
			mainPart.fs.write(
				uri,
				new TextEncoder().encode(
					'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>',
				),
			);
			addContentTypeOverride(mainPart.fs, uri, ct);
			addRelationship(
				mainPart.fs,
				"word/document.xml",
				`${REL_BASE}/footnotes`,
				"footnotes.xml",
			);
			const part = new NodeOpenXmlPart(mainPart.fs, uri, ct);
			part.OpenXmlPackage = mainPart.OpenXmlPackage;
			mainPart.FootnotesPart = part;
		},
		addWordprocessingCommentsPart(mainPart) {
			const uri = "word/comments.xml";
			const ct =
				"application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml";
			mainPart.fs.write(
				uri,
				new TextEncoder().encode(
					'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>',
				),
			);
			addContentTypeOverride(mainPart.fs, uri, ct);
			addRelationship(
				mainPart.fs,
				"word/document.xml",
				`${REL_BASE}/comments`,
				"comments.xml",
			);
			const part = new NodeOpenXmlPart(mainPart.fs, uri, ct);
			part.OpenXmlPackage = mainPart.OpenXmlPackage;
			mainPart.WordprocessingCommentsPart = part;
			return part;
		},
		addNewEndnotesPart(mainPart) {
			const uri = "word/endnotes.xml";
			const ct =
				"application/vnd.openxmlformats-officedocument.wordprocessingml.endnotes+xml";
			mainPart.fs.write(
				uri,
				new TextEncoder().encode(
					'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:endnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>',
				),
			);
			addContentTypeOverride(mainPart.fs, uri, ct);
			addRelationship(
				mainPart.fs,
				"word/document.xml",
				`${REL_BASE}/endnotes`,
				"endnotes.xml",
			);
			const part = new NodeOpenXmlPart(mainPart.fs, uri, ct);
			part.OpenXmlPackage = mainPart.OpenXmlPackage;
			mainPart.EndnotesPart = part;
		},
		getPartById(part, rId) {
			const rels = readPartRels(part.fs, part._uri).filter(
				(r) => r.id === rId && !r.external,
			);
			const found = rels.length
				? partForRel(part.fs, part._uri, rels[0])
				: null;
			if (found == null) {
				// C#'s GetPartById throws ArgumentOutOfRangeException for a non-internal
				// (hyperlink/external) rId; WmlComparer's catch discriminates on exactly
				// this .name, then falls back to hyperlinkRelationships/externalRelationships.
				const err = new Error(
					`GetPartById: '${rId}' not found or not internal`,
				);
				err.name = "ArgumentOutOfRangeException";
				throw err;
			}
			return found;
		},
		hyperlinkRelationships(part) {
			return readPartRels(part.fs, part._uri)
				.filter((r) => r.type === `${REL_BASE}/hyperlink`)
				.map((r) => ({ Id: r.id, Uri: { toString: () => r.target } }));
		},
		externalRelationships(part) {
			return readPartRels(part.fs, part._uri)
				.filter((r) => r.external)
				.map((r) => ({ Id: r.id, Uri: { toString: () => r.target } }));
		},
		openXmlPackageGetPackage(part) {
			return new NodePkg(part.fs);
		},
		resolvePartUri(baseUri, target) {
			return `/${resolveRelTarget(baseUri, target)}`;
		},
		copyStream(src, dst) {
			dst.WriteAllBytes(src.ReadAllBytes());
		},
		saveAs(doc, fullName) {
			writeFileSync(fullName, doc.fs.toZip());
		},
	});

	// ── `OpenXmlMemoryStreamDocument` factories (three separately-scoped
	// registries in FormattingAssembler / RevisionProcessor / WmlToXml). ──────
	const memoryStreamDocumentFactory = (document) => {
		const fs = new PartFS(unzipSync(document.DocumentByteArray));
		let wDoc = null;
		return {
			GetWordprocessingDocument() {
				if (wDoc == null) wDoc = new NodeWordprocessingDocument(fs);
				return wDoc;
			},
			GetModifiedWmlDocument() {
				const out = new WmlDocument(fs.toZip());
				out.FileName = document.FileName;
				return out;
			},
			Dispose() {},
		};
	};
	setFormattingAssemblerMemoryStreamDocumentFactory(
		memoryStreamDocumentFactory,
	);
	setRevisionProcessorMemoryStreamDocumentFactory(memoryStreamDocumentFactory);
	setWmlToXmlMemoryStreamDocumentFactory(memoryStreamDocumentFactory);

	// ── The simpler `OpenXmlPackageProvider` registry — used by WmlDocument's
	// copy-with-replacement-parts constructor (`new WmlDocument(other, ...parts)`). ──
	class SimplePartXDocument {
		constructor(Root) {
			this.Root = Root;
		}
	}
	class SimpleOpenXmlPart {
		constructor(fs, uri) {
			this.fs = fs;
			this.Uri = normalize(uri);
		}
		GetXDocument() {
			const xml = new TextDecoder("utf-8").decode(this.fs.read(this.Uri));
			const root = parseXDocument(xml).Root;
			if (root == null)
				throw new Error(`GetXDocument: ${this.Uri} has no root`);
			return new SimplePartXDocument(root);
		}
	}
	class SimpleMainDocumentPart extends SimpleOpenXmlPart {
		constructor(fs, commentsUri) {
			super(fs, "word/document.xml");
			this.WordprocessingCommentsPart =
				commentsUri != null && fs.read(commentsUri).length > 0
					? new SimpleOpenXmlPart(fs, commentsUri)
					: null;
		}
	}
	class SimpleWordprocessingDocument {
		constructor(fs) {
			const rels = readPartRels(fs, "word/document.xml").filter(
				(r) => r.type === `${REL_BASE}/comments`,
			);
			const commentsUri = rels.length
				? resolveRelTarget("word/document.xml", rels[0].target)
				: null;
			this.MainDocumentPart = new SimpleMainDocumentPart(fs, commentsUri);
		}
	}
	class SimplePackagePart {
		constructor(fs, uri) {
			this.fs = fs;
			this.Uri = normalize(uri);
		}
		WriteXml(serializedXml) {
			this.fs.write(this.Uri, new TextEncoder().encode(serializedXml));
		}
	}
	setOpenXmlPackageProvider({
		OpenWordprocessingDocument(bytes) {
			return new SimpleWordprocessingDocument(new PartFS(unzipSync(bytes)));
		},
		OpenMemoryStreamDocument(document) {
			const fs = new PartFS(unzipSync(document.DocumentByteArray));
			return {
				GetPackage() {
					return {
						GetParts() {
							return [...fs.entries.keys()].map(
								(name) => new SimplePackagePart(fs, name),
							);
						},
					};
				},
				GetModifiedDocumentByteArray() {
					return fs.toZip();
				},
			};
		},
	});

	wired = lossless;
}
