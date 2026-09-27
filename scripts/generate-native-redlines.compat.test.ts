import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

// Mock the package boundary, including resolution, so these unit tests need neither
// a vendor install nor real DOCX fixtures or the .NET WASM runtime.
vi.mock("./docxodus-node-compat.mjs", () => ({
  resolveDocxodusEntry: () => resolve("node_modules/docxodus/dist/index.js"),
  installDocxodusNodeCompat: vi.fn(),
}));
vi.mock("./prosemirror-headless-editor-server.ts", () => ({ runSuperDocVitest: vi.fn() }));

const entry = resolve("node_modules/docxodus/dist/index.js");
let root: string;

beforeEach(() => {
  vi.resetModules();
  root = mkdtempSync(join(tmpdir(), "redline-compat-"));
});
afterEach(() => {
  vi.doUnmock(entry);
  vi.resetModules();
  vi.clearAllMocks();
  rmSync(root, { recursive: true, force: true });
});

describe("Docxodus single-engine compatibility", () => {
  it.each(["bytes", "buffer"])("preserves comparison inputs and normalizes %s output", async (kind) => {
    const bytes = new Uint8Array([80, 75, 3, 4]);
    const initialize = vi.fn().mockResolvedValue(undefined);
    const compareDocuments = vi.fn(async () => {
      expect(initialize).toHaveBeenCalledOnce();
      return kind === "bytes" ? bytes : bytes.buffer;
    });
    vi.doMock(entry, () => ({ initialize, compareDocuments }));
    const { loadEngine } = await import("./generate-native-redlines.ts");
    const engine = await loadEngine("docxodus", "");
    const base = new Uint8Array([1]);
    const next = new Uint8Array([2]);
    const result = await engine(base, next);
    expect(compareDocuments).toHaveBeenCalledExactlyOnceWith(base, next);
    expect(result).toBeInstanceOf(Uint8Array);
    expect(result).toEqual(bytes);
    if (kind === "bytes") expect(result).toBe(bytes);
  });

  it("supports a single-engine package with an undefined optional initializer", async () => {
    const compareDocuments = vi.fn().mockResolvedValue(new Uint8Array([3]));
    vi.doMock(entry, () => ({ initialize: undefined, compareDocuments }));
    const { loadEngine } = await import("./generate-native-redlines.ts");
    const engine = await loadEngine("docxodus", "");
    expect(await engine(new Uint8Array(), new Uint8Array())).toEqual(new Uint8Array([3]));
  });

  it("propagates comparison errors so the batch records a failed document", async () => {
    const failure = new Error("unsupported revision topology");
    vi.doMock(entry, () => ({ initialize: undefined, compareDocuments: vi.fn().mockRejectedValue(failure) }));
    const { loadEngine } = await import("./generate-native-redlines.ts");
    const engine = await loadEngine("docxodus", "");
    await expect(engine(new Uint8Array([1]), new Uint8Array([2]))).rejects.toBe(failure);
  });

  it("propagates initialization failure before returning an engine", async () => {
    const failure = new Error("runtime unavailable");
    const compareDocuments = vi.fn();
    vi.doMock(entry, () => ({ initialize: vi.fn().mockRejectedValue(failure), compareDocuments }));
    const { loadEngine } = await import("./generate-native-redlines.ts");
    await expect(loadEngine("docxodus", "")).rejects.toBe(failure);
    expect(compareDocuments).not.toHaveBeenCalled();
  });

  it.each([
    { compareDocuments: undefined },
    { compareDocuments: "not callable" },
    { ComparisonEngine: {}, compareDocuments: vi.fn() },
    { ComparisonEngine: undefined, compareDocuments: vi.fn() },
  ])("rejects a malformed API instead of silently selecting an engine: %j", async (api) => {
    vi.doMock(entry, () => ({ initialize: undefined, ComparisonEngine: undefined, ...api }));
    const { loadEngine } = await import("./generate-native-redlines.ts");
    await expect(loadEngine("docxodus", "")).rejects.toThrow("ComparisonEngine.DocxDiff missing");
  });

  it.each([0, 7])("still selects the shipped legacy DocxDiff enum value %i", async (value) => {
    const compareDocuments = vi.fn().mockResolvedValue(new Uint8Array([3]));
    vi.doMock(entry, () => ({ initialize: undefined, ComparisonEngine: { DocxDiff: value }, compareDocuments }));
    const { loadEngine } = await import("./generate-native-redlines.ts");
    const base = new Uint8Array([1]);
    const next = new Uint8Array([2]);
    const engine = await loadEngine("docxodus", "");
    await engine(base, next);
    expect(compareDocuments).toHaveBeenCalledExactlyOnceWith(base, next, { engine: value });
  });
});

describe("batch run directory creation", () => {
  function options(method: string) {
    const manifest = join(root, "manifest.csv");
    writeFileSync(manifest, "base,next\n");
    return {
      method, dist: "", manifest, sourceDir: root, tool: method,
      out: join(root, "outputs"), runDir: join(root, "nested", "run"), force: false,
    };
  }

  it.each(["docxodus", "superdoc-native"])("creates a separate nested runDir for an empty %s batch", async (method) => {
    const compareDocuments = vi.fn();
    vi.doMock(entry, () => ({ initialize: undefined, compareDocuments }));
    const { runBatch } = await import("./generate-native-redlines.ts");
    const opts = options(method);
    expect(await runBatch(opts)).toEqual({ ok: 0, failed: [], timings: {} });
    expect(existsSync(opts.runDir)).toBe(true);
    expect(existsSync(opts.out)).toBe(true);
    expect(compareDocuments).not.toHaveBeenCalled();
  });

  it("preserves existing run artifacts when the directory already exists", async () => {
    vi.doMock(entry, () => ({ initialize: undefined, compareDocuments: vi.fn() }));
    const { runBatch } = await import("./generate-native-redlines.ts");
    const opts = options("docxodus");
    mkdirSync(opts.runDir, { recursive: true });
    const marker = join(opts.runDir, "previous.json");
    writeFileSync(marker, '{"previous":true}');
    await runBatch(opts);
    expect(readFileSync(marker, "utf8")).toBe('{"previous":true}');
  });

  it("creates runDir before writing and dispatching a SuperDoc plan", async () => {
    const { runSuperDocVitest } = await import("./prosemirror-headless-editor-server.ts");
    const { runBatch } = await import("./generate-native-redlines.ts");
    const opts = options("superdoc-native");
    writeFileSync(opts.manifest, "base,next\na,b\n");
    writeFileSync(join(root, "a.docx"), "base");
    writeFileSync(join(root, "b.docx"), "next");
    const output = join(opts.out, "a_b_superdoc-native_redline.docx");
    vi.mocked(runSuperDocVitest).mockImplementationOnce(async (env) => {
      expect(env.REDLINE_PLAN).toBe(join(opts.runDir, "superdoc-native-plan.json"));
      expect(JSON.parse(readFileSync(env.REDLINE_PLAN!, "utf8"))).toEqual([
        { fileA: join(root, "a.docx"), fileB: join(root, "b.docx"), output },
      ]);
      writeFileSync(output, "redline");
    });
    expect(await runBatch(opts)).toEqual({ ok: 1, failed: [], timings: {} });
    expect(runSuperDocVitest).toHaveBeenCalledOnce();
  });
});
