import { describe, it, expect, vi } from "vitest";
import { existsSync, mkdirSync, readFileSync, readdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
// Root jszip, not the docx-redline-js vendored copy: that tree's `@ansonlai/docx-redline-js`
// is a `file:` dep pointing outside the repo, so on a fresh checkout it never installs and a
// top-level import from it makes this WHOLE file fail to collect. jszip is a root dependency
// and is always present after `bun install`. (The docx-redline-js *adapter* still loads its
// own vendored jszip — only this test helper moved.)
import JSZip from "../node_modules/jszip/lib/index.js";
import { parseManifest, loadEngine, outputName, runBatch } from "./generate-native-redlines.ts";
import { resolveDocxodusEntry } from "./docxodus-node-compat.mjs";

const MANIFEST = "corpus/word/pools/word_based_pairs.csv";
const SOURCE = "corpus/word";
const DIST = "dist/jubarte";
const haveCorpus = existsSync(MANIFEST) && existsSync(SOURCE);
const haveJubarte = existsSync(join(DIST, "node.cjs"));
const haveSuperDocNative = existsSync("superdoc/packages/super-editor/vite.config.js");
const haveFolio = existsSync("src/neurotic_docx_bench/utils/folio/node_modules/@stll/folio-core/package.json");

// The two node_modules trees docxodus can live in. `DOCXODUS_ROOT_PKG` is the one
// bench.yaml's `package:` pin installs into and reads `tool_version` back from
// (tool_updater.resolve_tool_version is called with cwd=repo root); `DOCXODUS_VENDOR_PKG`
// is the one loadEngine("docxodus") actually imports and therefore measures.
const DOCXODUS_ROOT_PKG = "node_modules/docxodus/package.json";
const DOCXODUS_VENDOR_PKG =
  "src/neurotic_docx_bench/utils/docxodus/node_modules/docxodus/package.json";
// Must mirror resolveDocxodusEntry() (docxodus-node-compat.mjs): pin-tree (repo root) first,
// vendored sub-install as fallback. Mocking the wrong one silently lets the REAL
// docxodus run and the assertion then reports "undefined" rather than a mismatch.
const DOCXODUS_ENTRY = (() => {
  const rel = "docxodus/dist/index.js";
  const rootEntry = resolve(import.meta.dirname, "../node_modules", rel);
  return existsSync(rootEntry)
    ? rootEntry
    : resolve(
        import.meta.dirname,
        "../src/neurotic_docx_bench/utils/docxodus/node_modules",
        rel,
      );
})();
const haveDocxodus = existsSync(DOCXODUS_VENDOR_PKG);

function installedVersion(pkgJson: string): string | null {
  if (!existsSync(pkgJson)) return null;
  return JSON.parse(readFileSync(pkgJson, "utf8")).version ?? null;
}

/** The version bench.yaml pins for the `docxodus` run, e.g. `docxodus@9.0.0` → `9.0.0`. */
function benchYamlDocxodusPin(): string {
  const m = readFileSync("bench.yaml", "utf8").match(/^\s*package:\s*"docxodus@([^"]+)"/m);
  if (!m) throw new Error("bench.yaml has no `package: \"docxodus@<version>\"` pin");
  return m[1]!;
}

async function documentXml(bytes: Uint8Array): Promise<string> {
  const zip = await JSZip.loadAsync(bytes);
  return zip.file("word/document.xml")!.async("string");
}

/** A run-stable structural signature of a redline. docxodus output is NOT byte-reproducible
 *  (fresh zip mtimes and revision dates per call), but the tracked-change SHAPE is: repeated
 *  calls on one engine give an identical signature, and the two comparison engines give
 *  different ones. That makes this a sound way to prove WHICH engine produced a document. */
async function redlineShape(bytes: Uint8Array) {
  const xml = await documentXml(bytes);
  return {
    ins: (xml.match(/<w:ins[\s>]/g) ?? []).length,
    del: (xml.match(/<w:del[\s>]/g) ?? []).length,
    xmlLen: xml.length,
  };
}

/** First corpus pair whose base and next DOCX both exist on disk. */
function firstPair() {
  const p = parseManifest(MANIFEST, ["ok"]).find(
    (x) => existsSync(join(SOURCE, `${x.base}.docx`)) && existsSync(join(SOURCE, `${x.next}.docx`)),
  )!;
  return [
    new Uint8Array(readFileSync(join(SOURCE, `${p.base}.docx`))),
    new Uint8Array(readFileSync(join(SOURCE, `${p.next}.docx`))),
  ] as const;
}

describe("generate-native-redlines", () => {
  it("outputName normalizes back to <base>_<next>", () => {
    expect(outputName({ base: "a_x", next: "b_y", status: "ok" }, "jubarte")).toBe(
      "a_x_b_y_jubarte_redline.docx",
    );
  });

  it("outputName is the Word-corpus key plus the tool when the pool has a key", () => {
    const keyed = {
      base: "clean/docx/0123456789_a",
      next: "clean/docx/abcdef0123_b",
      status: "ok",
      key: "0123456789_a__vs__abcdef0123_b_redline_fedcba9876",
    };
    expect(outputName(keyed, "jubarte")).toBe("0123456789_a__vs__abcdef0123_b_redline_fedcba9876_jubarte.docx");
  });

  it("parseManifest reads the key of a Word-corpus pool", () => {
    const dir = mkdtempSync(join(tmpdir(), "ndb-pool-"));
    const pool = join(dir, "sources_pairs.csv");
    writeFileSync(
      pool,
      "key,base,next,base_name,next_name,docx,pdf,state\n" +
        "0123456789_a__vs__abcdef0123_b_redline_fedcba9876,clean/docx/0123456789_a,clean/docx/abcdef0123_b,a,b," +
        "clean/docx/0123456789_a__vs__abcdef0123_b_redline_fedcba9876.docx,clean/pdf/0123456789_a__vs__abcdef0123_b_redline_fedcba9876.pdf,clean\n",
    );
    const pairs = parseManifest(pool, ["ok"]);
    expect(pairs).toHaveLength(1);
    expect(pairs[0].base).toBe("clean/docx/0123456789_a");
    expect(pairs[0].next).toBe("clean/docx/abcdef0123_b");
    expect(pairs[0].key).toBe("0123456789_a__vs__abcdef0123_b_redline_fedcba9876");
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
      expect(xml.includes("<w:ins")).toBe(true);
      expect(xml.includes("<w:del")).toBe(true);
    },
    60_000,
  );

  // ── docxodus is benchmarked at a KNOWN version driving a NAMED engine ──────────
  //
  // Two ways a docxodus run can silently measure something other than what it reports,
  // both of which these tests make loud:
  //
  //  1. Version split-brain. bench.yaml's `package: "docxodus@X"` is installed into —
  //     and read back from — the REPO ROOT node_modules, because cli.py calls
  //     tool_updater.resolve_tool_version(cwd=Path.cwd()). The adapter, however,
  //     imports docxodus from the VENDORED utils/docxodus/node_modules tree. Nothing
  //     forces those two to hold the same version, so a run can record `tool_version:
  //     7.0.0` while the numbers come from a different build entirely.
  //
  //  2. Unnamed engine. `compareDocuments(base, next)` with no options resolves the
  //     engine from whatever the installed version happens to default to. docxodus
  //     7.0.0 defaulted to WmlComparer; 9.0.0 flipped the unnamed default to DocxDiff
  //     (`dist/index.js`: `const engine = options?.engine ?? ComparisonEngine.DocxDiff`).
  //     Identical call, different comparison engine, no error, different scores.
  describe("docxodus version + engine pinning", () => {
    it("the docxodus that runs is the version bench.yaml pins", () => {
      const pinned = benchYamlDocxodusPin();
      // Both trees must agree with the pin: the root one because that is what the run
      // RECORDS as tool_version, the vendored one because that is what it MEASURES.
      expect(
        { root: installedVersion(DOCXODUS_ROOT_PKG), vendor: installedVersion(DOCXODUS_VENDOR_PKG) },
        "bench.yaml pins docxodus@" +
          pinned +
          " — the installed trees must match it, or the run records one version and measures another",
      ).toEqual({ root: pinned, vendor: pinned });
      const entry = resolveDocxodusEntry();
      const pkg = JSON.parse(readFileSync(join(entry, "..", "..", "package.json"), "utf8"));
      expect(pkg.version, "resolveDocxodusEntry must refuse a tree that is not the pin").toBe(
        pinned,
      );
    });

    it("package-lock.json, if present, resolves the same pin as bench.yaml", () => {
      const lockPath = "package-lock.json";
      if (!existsSync(lockPath)) return;
      const lock = JSON.parse(readFileSync(lockPath, "utf8")) as {
        packages?: Record<string, { version?: string }>;
        dependencies?: Record<string, { version?: string }>;
      };
      const resolved =
        lock.packages?.["node_modules/docxodus"]?.version ??
        lock.dependencies?.docxodus?.version;
      expect(
        resolved,
        "package-lock.json still resolves a different docxodus than bench.yaml — npm ci would measure the wrong engine",
      ).toBe(benchYamlDocxodusPin());
    });

    it("resolveDocxodusEntry skips a stale root tree and uses the pinned vendor tree", () => {
      const root = mkdtempSync(join(tmpdir(), "docxodus-pin-"));
      try {
        writeFileSync(
          join(root, "package.json"),
          JSON.stringify({ dependencies: { docxodus: "9.8.0" } }),
        );
        const stale = join(root, "node_modules/docxodus");
        mkdirSync(join(stale, "dist"), { recursive: true });
        writeFileSync(join(stale, "package.json"), JSON.stringify({ version: "7.0.0" }));
        writeFileSync(join(stale, "dist/index.js"), "export {}\n");
        const vendor = join(
          root,
          "src/neurotic_docx_bench/utils/docxodus/node_modules/docxodus",
        );
        mkdirSync(join(vendor, "dist"), { recursive: true });
        writeFileSync(join(vendor, "package.json"), JSON.stringify({ version: "9.8.0" }));
        writeFileSync(join(vendor, "dist/index.js"), "export {}\n");
        mkdirSync(join(root, "scripts"), { recursive: true });
        const entry = resolveDocxodusEntry(join(root, "scripts"));
        expect(entry).toBe(join(vendor, "dist/index.js"));
      } finally {
        rmSync(root, { recursive: true, force: true });
      }
    });

    it.runIf(haveCorpus && haveDocxodus)(
      "the adapter names the comparison engine instead of inheriting the version default",
      async () => {
        // Stand in for docxodus and record exactly what the adapter passes through.
        const seen: { options?: unknown } = {};
        vi.doMock(DOCXODUS_ENTRY, () => ({
          ComparisonEngine: { WmlComparer: 0, DocxDiff: 1 },
          initialize: async () => {},
          compareDocuments: async (_a: Uint8Array, _b: Uint8Array, options?: unknown) => {
            seen.options = options;
            return new Uint8Array([1, 2, 3]);
          },
        }));
        try {
          vi.resetModules();
          const { loadEngine: freshLoadEngine } = await import("./generate-native-redlines.ts");
          const engine = await freshLoadEngine("docxodus", "");
          const [base, next] = firstPair();
          await engine(base, next);
          expect(
            (seen.options as { engine?: number } | undefined)?.engine,
            "loadEngine('docxodus') must pass an explicit CompareOptions.engine; passing none " +
              "makes the benchmarked engine a property of the installed version, not of the bench",
          ).toBe(1 /* ComparisonEngine.DocxDiff */);
        } finally {
          vi.doUnmock(DOCXODUS_ENTRY);
          vi.resetModules();
        }
      },
      30_000,
    );

    it.runIf(haveCorpus && haveDocxodus)(
      "docxodus ≥12 (no ComparisonEngine enum, one engine) compares without an engine option",
      async () => {
        const seen: { calls: number; options?: unknown } = { calls: 0 };
        vi.doMock(DOCXODUS_ENTRY, () => ({
          initialize: async () => {},
          compareDocuments: async (_a: Uint8Array, _b: Uint8Array, options?: unknown) => {
            seen.calls += 1;
            seen.options = options;
            return new Uint8Array([1, 2, 3]);
          },
        }));
        try {
          vi.resetModules();
          const { loadEngine: freshLoadEngine } = await import("./generate-native-redlines.ts");
          const engine = await freshLoadEngine("docxodus", "");
          const [base, next] = firstPair();
          expect(await engine(base, next)).toEqual(new Uint8Array([1, 2, 3]));
          expect(seen).toEqual({ calls: 1, options: undefined });
        } finally {
          vi.doUnmock(DOCXODUS_ENTRY);
          vi.resetModules();
        }
      },
      30_000,
    );

    it.runIf(haveCorpus && haveDocxodus)(
      "the engine the adapter names is still the one docxodus itself defaults to",
      async () => {
        const dox: any = await import(DOCXODUS_ENTRY);
        await dox.initialize();
        const [base, next] = firstPair();
        if (!("ComparisonEngine" in dox)) {
          // docxodus ≥12: one engine, no default to drift. The adapter must still drive it.
          const engine = await loadEngine("docxodus", "");
          expect(await redlineShape(await engine(base, next))).toEqual(
            await redlineShape(await dox.compareDocuments(base, next)),
          );
          return;
        }

        const shapeOf = async (options?: unknown) =>
          redlineShape(await dox.compareDocuments(base, next, options));
        const unnamed = await shapeOf(undefined);
        const wml = await shapeOf({ engine: dox.ComparisonEngine.WmlComparer });
        const docxDiff = await shapeOf({ engine: dox.ComparisonEngine.DocxDiff });

        // If the engines produced identical markup the rest of this proves nothing.
        expect(wml, "the two comparison engines must produce materially different redlines").not.toEqual(
          docxDiff,
        );

        // Drift alarm: we deliberately benchmark docxodus at ITS OWN current default rather
        // than freezing a legacy engine. If a future release moves that default again, this
        // fails and forces a re-review instead of quietly shifting every docxodus score.
        expect(
          unnamed,
          "docxodus changed its unnamed default engine — re-review which engine the bench should name",
        ).toEqual(docxDiff);

        // And the adapter really drives that engine end to end.
        const engine = await loadEngine("docxodus", "");
        expect(await redlineShape(await engine(base, next))).toEqual(docxDiff);
      },
      60_000,
    );
  });

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

  // Regression pin for the folio adapter's block-id contract.
  //
  // The pre-0.15 adapter composed compareDocxVersions + FolioDocxReviewer and
  // assumed a `modified` FolioBlockDiff's `blockId` was a BASE-side id it could
  // feed straight to replaceInBlock. It never was: folio emits the diff in
  // revised-side order and `blockId` is the REVISED-side id, so every
  // `baseIds.has(c.blockId)` guard failed, every replaceInBlock op was dropped,
  // and `ops.length === 0` fell through to the "no diff" path that returns the
  // BASE document unchanged. Pairs that differ only by modified text scored as
  // "folio produced no redline" — a harness bug credited to folio.
  //
  // This pair's three body paragraphs are all `modified` and nothing else, so
  // it is exactly the case the old translation dropped in full. The assertion is
  // behavioural, not structural: the output must carry tracked changes AND must
  // not be the base document handed back.
  const MOD_ONLY_BASE = "blue_bold_centered_demo_id_paraid_overflow";
  const MOD_ONLY_NEXT = "blue_centered_title_demo_style_default_missing";
  const haveModOnlyPair =
    existsSync(join(SOURCE, `${MOD_ONLY_BASE}.docx`)) &&
    existsSync(join(SOURCE, `${MOD_ONLY_NEXT}.docx`));

  it.runIf(haveFolio && haveModOnlyPair)(
    "folio engine tracks changes on a modification-only pair (never returns base unchanged)",
    async () => {
      const base = new Uint8Array(readFileSync(join(SOURCE, `${MOD_ONLY_BASE}.docx`)));
      const next = new Uint8Array(readFileSync(join(SOURCE, `${MOD_ONLY_NEXT}.docx`)));
      const engine = await loadEngine("folio", "");
      const out = await engine(base, next);

      // The identity fallback returns the very same Uint8Array it was handed.
      expect(out).not.toBe(base);
      const xml = await documentXml(out);
      expect(xml.includes("<w:ins")).toBe(true);
      expect(xml.includes("<w:del")).toBe(true);
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

  it.each(["jubarte-rust-inproc", "docxodus-csharp-inproc"])(
    "runBatch stops the %s worker when the batch ends (or the CLI never exits)",
    async (method) => {
      const tmp = mkdtempSync(join(tmpdir(), "gen-inproc-"));
      try {
        const dist = join(tmp, "dist");
        mkdirSync(dist);
        const pidFile = join(tmp, "worker.pid");
        const worker = [
          "#!/bin/sh",
          `echo $$ > '${pidFile}'`,
          "echo READY",
          "while read cmd a b c; do",
          '  case "$cmd" in',
          '    COMPARE) cp "$b" "$c"; echo "OK 1 1";;',
          "    QUIT) echo BYE; exit 0;;",
          "  esac",
          "done",
        ].join("\n");
        for (const name of ["jubarte-worker", "docxodus-inproc"]) {
          writeFileSync(join(dist, name), worker, { mode: 0o755 });
        }
        writeFileSync(join(tmp, "a.docx"), "base");
        writeFileSync(join(tmp, "b.docx"), "next");
        const manifest = join(tmp, "manifest.csv");
        writeFileSync(manifest, "key,base,next\nk1,a,b\n");
        const res = await runBatch({
          method,
          dist,
          out: join(tmp, "out"),
          runDir: join(tmp, "run"),
          manifest,
          sourceDir: tmp,
          status: "",
          tool: "t",
          force: true,
        });
        expect(res.failed).toEqual([]);
        expect(readFileSync(join(tmp, "out", "k1_t.docx"), "utf8")).toBe("next");
        const pid = Number(readFileSync(pidFile, "utf8"));
        const alive = () => {
          try {
            process.kill(pid, 0);
            return true;
          } catch {
            return false;
          }
        };
        const deadline = Date.now() + 3000;
        while (alive() && Date.now() < deadline) await new Promise((r) => setTimeout(r, 50));
        expect(alive()).toBe(false);
      } finally {
        rmSync(tmp, { recursive: true, force: true });
      }
    },
    30_000,
  );

  it.each(["jubarte-rust-inproc", "docxodus-csharp-inproc"])(
    "a %s pair that times out costs only that pair: the stuck worker is killed and the next pair gets a fresh one",
    async (method) => {
      const tmp = mkdtempSync(join(tmpdir(), "gen-inproc-timeout-"));
      const before = process.env.WORKER_REPLY_TIMEOUT_MS;
      process.env.WORKER_REPLY_TIMEOUT_MS = "1000";
      try {
        const dist = join(tmp, "dist");
        mkdirSync(dist);
        const pidFile = join(tmp, "worker.pids");
        const worker = [
          "#!/bin/sh",
          `echo $$ >> '${pidFile}'`,
          "echo READY",
          "while read cmd a b c; do",
          '  case "$cmd" in',
          '    COMPARE) if grep -q slow "$a"; then while :; do :; done; fi; cp "$b" "$c"; echo "OK 1 1";;',
          "    QUIT) echo BYE; exit 0;;",
          "  esac",
          "done",
        ].join("\n");
        for (const name of ["jubarte-worker", "docxodus-inproc"]) {
          writeFileSync(join(dist, name), worker, { mode: 0o755 });
        }
        writeFileSync(join(tmp, "slow.docx"), "slow");
        writeFileSync(join(tmp, "a.docx"), "base");
        writeFileSync(join(tmp, "b.docx"), "next");
        writeFileSync(join(tmp, "c.docx"), "next2");
        const manifest = join(tmp, "manifest.csv");
        writeFileSync(manifest, "key,base,next\nk1,slow,b\nk2,a,b\nk3,a,c\n");
        const t0 = Date.now();
        const res = await runBatch({
          method,
          dist,
          out: join(tmp, "out"),
          runDir: join(tmp, "run"),
          manifest,
          sourceDir: tmp,
          status: "",
          tool: "t",
          force: true,
        });
        expect(Date.now() - t0).toBeLessThan(10_000);
        expect(res.failed.map((f) => f.doc)).toEqual(["k1"]);
        expect(res.failed[0].error).toMatch(/timeout/);
        expect(readFileSync(join(tmp, "out", "k2_t.docx"), "utf8")).toBe("next");
        expect(readFileSync(join(tmp, "out", "k3_t.docx"), "utf8")).toBe("next2");
        const pids = readFileSync(pidFile, "utf8").trim().split("\n").map(Number);
        expect(pids).toHaveLength(2);
        const alive = (pid: number) => {
          try {
            process.kill(pid, 0);
            return true;
          } catch {
            return false;
          }
        };
        const deadline = Date.now() + 3000;
        while (pids.some(alive) && Date.now() < deadline) await new Promise((r) => setTimeout(r, 50));
        expect(pids.filter(alive)).toEqual([]);
      } finally {
        if (before === undefined) delete process.env.WORKER_REPLY_TIMEOUT_MS;
        else process.env.WORKER_REPLY_TIMEOUT_MS = before;
        rmSync(tmp, { recursive: true, force: true });
      }
    },
    90_000,
  );

  it("runBatch creates the run dir the CLI writes generate_failures.json into", async () => {
    const tmp = mkdtempSync(join(tmpdir(), "gen-rundir-"));
    try {
      const manifest = join(tmp, "manifest.csv");
      writeFileSync(manifest, "pair_stem,base,next\n");
      const runDir = join(tmp, "run", "nested");
      const res = await runBatch({
        method: "docxodus",
        dist: "",
        out: join(tmp, "out"),
        runDir,
        manifest,
        sourceDir: tmp,
        status: "ok",
        limit: 0,
        tool: "docxodus",
        force: true,
      });
      expect(res).toEqual({ ok: 0, failed: [], timings: {} });
      expect(existsSync(runDir)).toBe(true);
    } finally {
      rmSync(tmp, { recursive: true, force: true });
    }
  }, 60_000);

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

  // Newer jubarte builds return { criticmarkup, handle } from redlineDocx instead of
  // the bare handle; redlineToDocx wants the handle either way. Stub node.cjs builds
  // pin the unwrap so a jubarte upgrade can't silently break the native route.
  describe("jubarte-native result unwrapping", () => {
    function stubDist(nodeCjs: string): string {
      const dist = mkdtempSync(join(tmpdir(), "jubarte-stub-"));
      writeFileSync(join(dist, "node.cjs"), nodeCjs);
      return dist;
    }
    const OUT = "[1,2,3]"; // JSON so the stub can return plain bytes

    it("unwraps { criticmarkup, handle } and passes the handle to redlineToDocx", async () => {
      const dist = stubDist(`
        const SENTINEL = { tag: "handle" };
        module.exports = {
          redlineDocx: async () => ({ criticmarkup: "{++x++}", handle: SENTINEL }),
          redlineToDocx: async (h) => {
            if (h !== SENTINEL) throw new Error("redlineToDocx got the wrapper, not the handle");
            return new Uint8Array(${OUT});
          },
        };
      `);
      try {
        const engine = await loadEngine("jubarte-native", dist);
        const out = await engine(new Uint8Array([0]), new Uint8Array([1]));
        expect(Array.from(out)).toEqual([1, 2, 3]);
      } finally {
        rmSync(dist, { recursive: true, force: true });
      }
    });

    it("still accepts a bare handle from older builds", async () => {
      const dist = stubDist(`
        const SENTINEL = { tag: "bare" };
        module.exports = {
          redlineDocx: async () => SENTINEL,
          redlineToDocx: async (h) => {
            if (h !== SENTINEL) throw new Error("expected the bare handle");
            return new Uint8Array(${OUT});
          },
        };
      `);
      try {
        const engine = await loadEngine("jubarte-native", dist);
        const out = await engine(new Uint8Array([0]), new Uint8Array([1]));
        expect(Array.from(out)).toEqual([1, 2, 3]);
      } finally {
        rmSync(dist, { recursive: true, force: true });
      }
    });

    it("treats a wrapped null handle as no-differences identity", async () => {
      const dist = stubDist(`
        module.exports = {
          redlineDocx: async () => ({ criticmarkup: null, handle: null }),
          redlineToDocx: async () => { throw new Error("must not be called for no-diff"); },
        };
      `);
      try {
        const engine = await loadEngine("jubarte-native", dist);
        const base = new Uint8Array([7, 7]);
        const out = await engine(base, new Uint8Array([1]));
        expect(out).toBe(base);
      } finally {
        rmSync(dist, { recursive: true, force: true });
      }
    });
  });
});
