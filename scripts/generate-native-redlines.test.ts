import { describe, it, expect } from "vitest";
import { existsSync, readFileSync, readdirSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import JSZip from "../src/neurotic_docx_bench/utils/docx-redline-js/node_modules/jszip/lib/index.js";
import { parseManifest, loadEngine, outputName, runBatch } from "./generate-native-redlines.ts";

const MANIFEST = "corpus/word_based/centralized_mapping.csv";
const SOURCE = "corpus/word_based/docx_source";
const DIST = "dist/jubarte";
const haveCorpus = existsSync(MANIFEST) && existsSync(SOURCE);
const haveJubarte = existsSync(join(DIST, "node.cjs"));
const haveSuperDocNative = existsSync("superdoc/packages/super-editor/vite.config.js");
const haveFolio = existsSync("src/neurotic_docx_bench/utils/folio/node_modules/@stll/folio-core/package.json");

async function documentXml(bytes: Uint8Array): Promise<string> {
  const zip = await JSZip.loadAsync(bytes);
  return zip.file("word/document.xml")!.async("string");
}

describe("generate-native-redlines", () => {
  it("outputName normalizes back to <base>_<next>", () => {
    expect(outputName({ base: "a_x", next: "b_y", status: "ok" }, "jubarte")).toBe(
      "a_x_b_y_jubarte_redline.docx",
    );
  });

  it.runIf(haveCorpus)("parseManifest returns ok pairs with base+next", () => {
    const pairs = parseManifest(MANIFEST, ["ok"]);
    expect(pairs.length).toBeGreaterThan(0);
    expect(pairs[0].base).toBeTruthy();
    expect(pairs[0].next).toBeTruthy();
    // The current manifest dropped batch_status, so every pair just needs base+next.
    expect(pairs.every((p) => p.base && p.next)).toBe(true);
  });

  it.runIf(haveCorpus && haveJubarte).each(["jubarte-native", "jubarte-lossless"])(
    "jubarte %s route produces a redline docx with tracked changes",
    async (method) => {
      const pairs = parseManifest(MANIFEST, ["ok"]);
      const p = pairs.find(
        (x) =>
          existsSync(join(SOURCE, `${x.base}.docx`)) && existsSync(join(SOURCE, `${x.next}.docx`)),
      )!;
      const engine = await loadEngine(method, DIST);
      const out = await engine(
        new Uint8Array(readFileSync(join(SOURCE, `${p.base}.docx`))),
        new Uint8Array(readFileSync(join(SOURCE, `${p.next}.docx`))),
      );
      expect(out).toBeInstanceOf(Uint8Array);
      expect(out.length).toBeGreaterThan(1000);
      const xml = await documentXml(out);
      expect(xml.includes("<w:ins")).toBe(true);
      expect(xml.includes("<w:del")).toBe(true);
    },
    30_000,
  );

  it.runIf(haveCorpus)(
    "docxodus engine produces a redline docx with tracked changes",
    async () => {
      const pairs = parseManifest(MANIFEST, ["ok"]);
      const p = pairs.find(
        (x) =>
          existsSync(join(SOURCE, `${x.base}.docx`)) && existsSync(join(SOURCE, `${x.next}.docx`)),
      )!;
      const engine = await loadEngine("docxodus", "");
      const out = await engine(
        new Uint8Array(readFileSync(join(SOURCE, `${p.base}.docx`))),
        new Uint8Array(readFileSync(join(SOURCE, `${p.next}.docx`))),
      );
      expect(out).toBeInstanceOf(Uint8Array);
      const xml = await documentXml(out);
      expect(xml.includes("<w:ins") || xml.includes("<w:del")).toBe(true);
    },
    60_000,
  );

  it.runIf(haveCorpus)(
    "docx-redline-js adapter produces a redline docx with tracked changes",
    async () => {
      const pairs = parseManifest(MANIFEST, ["ok"]);
      const p = pairs.find(
        (x) =>
          existsSync(join(SOURCE, `${x.base}.docx`)) && existsSync(join(SOURCE, `${x.next}.docx`)),
      )!;
      const engine = await loadEngine("docx-redline-js", "");
      const out = await engine(
        new Uint8Array(readFileSync(join(SOURCE, `${p.base}.docx`))),
        new Uint8Array(readFileSync(join(SOURCE, `${p.next}.docx`))),
      );
      expect(out).toBeInstanceOf(Uint8Array);
      const xml = await documentXml(out);
      expect(xml.includes("<w:ins") || xml.includes("<w:del")).toBe(true);
    },
    60_000,
  );

  it.runIf(haveCorpus && haveFolio)(
    "folio engine produces a redline docx with tracked changes",
    async () => {
      const pairs = parseManifest(MANIFEST, ["ok"]);
      const p = pairs.find(
        (x) =>
          existsSync(join(SOURCE, `${x.base}.docx`)) && existsSync(join(SOURCE, `${x.next}.docx`)),
      )!;
      const engine = await loadEngine("folio", "");
      const out = await engine(
        new Uint8Array(readFileSync(join(SOURCE, `${p.base}.docx`))),
        new Uint8Array(readFileSync(join(SOURCE, `${p.next}.docx`))),
      );
      expect(out).toBeInstanceOf(Uint8Array);
      expect(out.length).toBeGreaterThan(1000);
      const xml = await documentXml(out);
      expect(xml.includes("<w:ins") || xml.includes("<w:del")).toBe(true);
    },
    60_000,
  );

  it.runIf(haveCorpus)(
    "superdoc-ts (TypeScript SDK) produces a redline docx with tracked changes",
    async () => {
      const pairs = parseManifest(MANIFEST, ["ok"]);
      const p = pairs.find(
        (x) =>
          existsSync(join(SOURCE, `${x.base}.docx`)) && existsSync(join(SOURCE, `${x.next}.docx`)),
      )!;
      const engine = await loadEngine("superdoc-ts", "");
      const out = await engine(
        new Uint8Array(readFileSync(join(SOURCE, `${p.base}.docx`))),
        new Uint8Array(readFileSync(join(SOURCE, `${p.next}.docx`))),
      );
      expect(out).toBeInstanceOf(Uint8Array);
      const xml = await documentXml(out);
      expect(xml.includes("<w:ins") || xml.includes("<w:del")).toBe(true);
    },
    60_000,
  );

  it.runIf(haveCorpus && haveSuperDocNative)(
    "superdoc-native (Editor.commands.compareDocuments) produces redlines with tracked changes",
    async () => {
      const out = mkdtempSync(join(tmpdir(), "gen-superdoc-native-"));
      try {
        const res = await runBatch({
          method: "superdoc-native",
          dist: "",
          out,
          runDir: out,
          manifest: MANIFEST,
          sourceDir: SOURCE,
          status: "ok",
          limit: 3,
          tool: "superdoc-native",
          force: true,
        });
        expect(res.ok).toBeGreaterThanOrEqual(1);
        const files = readdirSync(out).filter((f) => f.endsWith("_superdoc-native_redline.docx"));
        expect(files.length).toBe(res.ok);
        const xml = await documentXml(new Uint8Array(readFileSync(join(out, files[0]!))));
        expect(xml.includes("<w:ins") || xml.includes("<w:del")).toBe(true);
      } finally {
        rmSync(out, { recursive: true, force: true });
      }
    },
    120_000,
  );

  it.runIf(haveCorpus && haveJubarte)(
    "runBatch writes a redline whose name normalizes to the pair key",
    async () => {
      const out = mkdtempSync(join(tmpdir(), "gen-"));
      try {
        const res = await runBatch({
          method: "jubarte",
          dist: DIST,
          out,
          runDir: out,
          manifest: MANIFEST,
          sourceDir: SOURCE,
          status: "ok",
          limit: 1,
          tool: "jubarte",
          force: true,
        });
        expect(res.ok).toBeGreaterThanOrEqual(1);
        const files = readdirSync(out).filter((f) => f.endsWith("_jubarte_redline.docx"));
        expect(files.length).toBe(1);
      } finally {
        rmSync(out, { recursive: true, force: true });
      }
    },
    30_000,
  );
});
