/**
 * Ensure a DOCX package carries the optional package parts that Docxodus's
 * WmlToHtmlConverter assumes exist.
 *
 * Word opens packages without word/settings.xml (and often without theme /
 * fontTable) without complaint. Docxodus ≤6.4 crashes with
 * ArgumentNullException("part") in CalculateSpanWidthForTabs when
 * DocumentSettingsPart is null — that alone wiped ~150 of 199 visual_rendering
 * fixtures. This normalizer is a harness-side compatibility shim: it only
 * *adds* missing optional parts with Word-default content; existing parts are
 * left untouched so layout of healthy packages is unchanged.
 */
import { unzipSync, zipSync, strToU8, strFromU8 } from "fflate";

const CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types";
const REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships";
const W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";

const SETTINGS_PATH = "word/settings.xml";
const STYLES_PATH = "word/styles.xml";
const FONT_TABLE_PATH = "word/fontTable.xml";
const THEME_PATH = "word/theme/theme1.xml";
const DOCRELS_PATH = "word/_rels/document.xml.rels";
const CONTENT_TYPES_PATH = "[Content_Types].xml";

const REL_TYPE = {
	settings:
		"http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings",
	styles:
		"http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles",
	fontTable:
		"http://schemas.openxmlformats.org/officeDocument/2006/relationships/fontTable",
	theme:
		"http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme",
} as const;

const CONTENT_TYPE = {
	settings:
		"application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml",
	styles:
		"application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml",
	fontTable:
		"application/vnd.openxmlformats-officedocument.wordprocessingml.fontTable+xml",
	theme: "application/vnd.openxmlformats-officedocument.theme+xml",
} as const;

const MINIMAL_SETTINGS = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="${W_NS}">
  <w:defaultTabStop w:val="720"/>
  <w:characterSpacingControl w:val="doNotCompress"/>
</w:settings>
`;

const MINIMAL_STYLES = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="${W_NS}">
  <w:docDefaults>
    <w:rPrDefault>
      <w:rPr>
        <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
        <w:sz w:val="22"/>
      </w:rPr>
    </w:rPrDefault>
    <w:pPrDefault>
      <w:pPr>
        <w:spacing w:after="200" w:line="276" w:lineRule="auto"/>
      </w:pPr>
    </w:pPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
  </w:style>
</w:styles>
`;

const MINIMAL_FONT_TABLE = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:fonts xmlns:w="${W_NS}">
  <w:font w:name="Calibri">
    <w:panose1 w:val="020F0502020204030204"/>
    <w:charset w:val="00"/>
    <w:family w:val="swiss"/>
    <w:pitch w:val="variable"/>
  </w:font>
</w:fonts>
`;

// Minimal Office theme (clrScheme + fontScheme + fmtScheme stubs). Enough for
// ThemePart.GetXDocument() and theme-color resolution fallbacks.
const MINIMAL_THEME = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="HarnessMinimal">
  <a:themeElements>
    <a:clrScheme name="Harness">
      <a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>
      <a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>
      <a:dk2><a:srgbClr val="1F497D"/></a:dk2>
      <a:lt2><a:srgbClr val="EEECE1"/></a:lt2>
      <a:accent1><a:srgbClr val="4F81BD"/></a:accent1>
      <a:accent2><a:srgbClr val="C0504D"/></a:accent2>
      <a:accent3><a:srgbClr val="9BBB59"/></a:accent3>
      <a:accent4><a:srgbClr val="8064A2"/></a:accent4>
      <a:accent5><a:srgbClr val="4BACC6"/></a:accent5>
      <a:accent6><a:srgbClr val="F79646"/></a:accent6>
      <a:hlink><a:srgbClr val="0000FF"/></a:hlink>
      <a:folHlink><a:srgbClr val="800080"/></a:folHlink>
    </a:clrScheme>
    <a:fontScheme name="Harness">
      <a:majorFont>
        <a:latin typeface="Calibri"/>
        <a:ea typeface=""/>
        <a:cs typeface=""/>
      </a:majorFont>
      <a:minorFont>
        <a:latin typeface="Calibri"/>
        <a:ea typeface=""/>
        <a:cs typeface=""/>
      </a:minorFont>
    </a:fontScheme>
    <a:fmtScheme name="Harness">
      <a:fillStyleLst>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
      </a:fillStyleLst>
      <a:lnStyleLst>
        <a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
        <a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
        <a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
      </a:lnStyleLst>
      <a:effectStyleLst>
        <a:effectStyle><a:effectLst/></a:effectStyle>
        <a:effectStyle><a:effectLst/></a:effectStyle>
        <a:effectStyle><a:effectLst/></a:effectStyle>
      </a:effectStyleLst>
      <a:bgFillStyleLst>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
      </a:bgFillStyleLst>
    </a:fmtScheme>
  </a:themeElements>
</a:theme>
`;

type PartSpec = {
	path: string;
	relType: string;
	relTarget: string;
	contentType: string;
	xml: string;
};

const OPTIONAL_PARTS: PartSpec[] = [
	{
		path: SETTINGS_PATH,
		relType: REL_TYPE.settings,
		relTarget: "settings.xml",
		contentType: CONTENT_TYPE.settings,
		xml: MINIMAL_SETTINGS,
	},
	{
		path: STYLES_PATH,
		relType: REL_TYPE.styles,
		relTarget: "styles.xml",
		contentType: CONTENT_TYPE.styles,
		xml: MINIMAL_STYLES,
	},
	{
		path: FONT_TABLE_PATH,
		relType: REL_TYPE.fontTable,
		relTarget: "fontTable.xml",
		contentType: CONTENT_TYPE.fontTable,
		xml: MINIMAL_FONT_TABLE,
	},
	{
		path: THEME_PATH,
		relType: REL_TYPE.theme,
		relTarget: "theme/theme1.xml",
		contentType: CONTENT_TYPE.theme,
		xml: MINIMAL_THEME,
	},
];

function ensureContentTypeOverride(
	ctXml: string,
	partName: string,
	contentType: string,
): string {
	if (ctXml.includes(`PartName="${partName}"`)) return ctXml;
	const override = `<Override PartName="${partName}" ContentType="${contentType}"/>`;
	if (ctXml.includes("</Types>")) {
		return ctXml.replace("</Types>", `${override}</Types>`);
	}
	// Degenerate Content_Types — rebuild a minimal wrapper.
	return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="${CT_NS}"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>${override}</Types>`;
}

function nextRelId(existing: string[]): string {
	let max = 0;
	for (const id of existing) {
		const m = /^rId(\d+)$/i.exec(id);
		if (m) max = Math.max(max, parseInt(m[1], 10));
	}
	return `rId${max + 1}`;
}

function ensureRelationship(
	relsXml: string,
	relType: string,
	target: string,
): string {
	// Already present (by Type or Target)?
	if (relsXml.includes(`Type="${relType}"`) || relsXml.includes(`Target="${target}"`)) {
		return relsXml;
	}
	const ids = [...relsXml.matchAll(/\bId="([^"]+)"/g)].map((m) => m[1]);
	const id = nextRelId(ids);
	const rel = `<Relationship Id="${id}" Type="${relType}" Target="${target}"/>`;
	if (relsXml.includes("</Relationships>")) {
		return relsXml.replace("</Relationships>", `${rel}</Relationships>`);
	}
	return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="${REL_NS}">${rel}</Relationships>`;
}

/**
 * Returns the input File unchanged when every optional part is already present.
 * Otherwise returns a new File with the missing parts injected.
 */
export async function normalizeDocxForViewer(file: File): Promise<File> {
	const input = new Uint8Array(await file.arrayBuffer());
	let files: Record<string, Uint8Array>;
	try {
		files = unzipSync(input);
	} catch (err) {
		// Not a zip / corrupt — let the viewer surface the original error.
		console.warn("[harness] normalizeDocx: unzip failed, passing through", err);
		return file;
	}

	const missing = OPTIONAL_PARTS.filter((p) => !(p.path in files));
	if (missing.length === 0) return file;

	let ctXml =
		CONTENT_TYPES_PATH in files
			? strFromU8(files[CONTENT_TYPES_PATH])
			: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="${CT_NS}"></Types>`;
	let relsXml =
		DOCRELS_PATH in files
			? strFromU8(files[DOCRELS_PATH])
			: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="${REL_NS}"></Relationships>`;

	for (const part of missing) {
		files[part.path] = strToU8(part.xml);
		ctXml = ensureContentTypeOverride(ctXml, `/${part.path}`, part.contentType);
		relsXml = ensureRelationship(relsXml, part.relType, part.relTarget);
	}

	files[CONTENT_TYPES_PATH] = strToU8(ctXml);
	files[DOCRELS_PATH] = strToU8(relsXml);

	const out = zipSync(files, { level: 6 });
	return new File([out], file.name, {
		type: file.type || "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
		lastModified: file.lastModified,
	});
}
