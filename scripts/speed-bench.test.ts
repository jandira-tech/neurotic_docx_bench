import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

vi.mock("./generate-native-redlines.ts", () => ({ parseManifest: vi.fn(), loadEngine: vi.fn() }));
import { loadEngine, parseManifest } from "./generate-native-redlines.ts";

let root: string;
let rust: string;
let wasm: string;
let out: string;
const originalArgv = process.argv;

beforeEach(() => {
	vi.resetModules();
	vi.resetAllMocks();
	root = mkdtempSync(join(tmpdir(), "speed-bench-"));
	rust = join(root, "rust");
	wasm = join(root, "wasm");
	out = join(root, "results", "speed.jsonl");
	vi.stubEnv("JUBARTE_RUST_DIST", rust);
	vi.stubEnv("JUBARTE_WASM_DIST", wasm);
	process.argv = ["node", "speed-bench.ts", "--source-dir", root, "--out", out,
		"--warmup", "0", "--reps", "1", "--run-ts", "test-run"];
	writeFileSync(join(root, "a.docx"), new Uint8Array([1]));
	writeFileSync(join(root, "b.docx"), new Uint8Array([2]));
	vi.mocked(parseManifest).mockReturnValue([{ base: "a", next: "b", status: "ok" }] as never);
	vi.mocked(loadEngine).mockResolvedValue(vi.fn().mockResolvedValue(new Uint8Array([3])));
	vi.spyOn(console, "log").mockImplementation(() => {});
	vi.spyOn(console, "error").mockImplementation(() => {});
	vi.spyOn(process, "exit").mockImplementation((code) => { throw new Error(`exit ${code}`); });
});
afterEach(() => {
	process.argv = originalArgv;
	vi.restoreAllMocks();
	vi.unstubAllEnvs();
	vi.resetModules();
	rmSync(root, { recursive: true, force: true });
});

// speed-bench.ts runs main() at import: each test imports a fresh copy.
async function run(methods?: string) {
	if (methods) process.argv.push("--methods", methods);
	await import("./speed-bench.ts");
}
function rows() {
	return readFileSync(out, "utf8").trim().split("\n").map((line) => JSON.parse(line));
}

describe("Jubarte speed benchmark selection", () => {
	it.each(["jubarte-rust", "jubarte-wasm"])("fails before engine initialization when selected %s is absent", async (method) => {
		await expect(run(method)).rejects.toThrow("exit 1");
		expect(loadEngine).not.toHaveBeenCalled();
		expect(console.error).toHaveBeenCalledWith(expect.stringContaining(`missing jubarte build (${method}:`));
		expect(existsSync(out)).toBe(false);
	});

	it("reports both absent distributions for the default method set", async () => {
		await expect(run()).rejects.toThrow("exit 1");
		expect(console.error).toHaveBeenCalledWith(expect.stringContaining(`jubarte-rust: ${rust}; jubarte-wasm: ${wasm}`));
		expect(loadEngine).not.toHaveBeenCalled();
	});

	it("ignores absent Jubarte distributions when only another tool is requested", async () => {
		await run("docxodus");
		expect(loadEngine).toHaveBeenCalledExactlyOnceWith("docxodus", "");
		expect(rows()).toEqual([expect.objectContaining({ tool: "docxodus", n: 1 })]);
		expect(process.exit).not.toHaveBeenCalled();
	});

	it.each(["jubarte-rust", "jubarte-wasm"])("passes the overridden distribution and exact method to %s", async (method) => {
		const dist = method === "jubarte-rust" ? rust : wasm;
		mkdirSync(dist);
		await run(method);
		expect(loadEngine).toHaveBeenCalledExactlyOnceWith(method, dist);
		expect(rows()).toEqual([expect.objectContaining({
			tool: method, unit: "ms_per_redline", runtime: "node", run_ts: "test-run", n: 1, failures: 0,
		})]);
		const engine = await vi.mocked(loadEngine).mock.results[0].value;
		expect(engine).toHaveBeenCalledExactlyOnceWith(new Uint8Array([1]), new Uint8Array([2]));
	});
});
