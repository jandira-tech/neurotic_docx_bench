import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { hardwareInfo, npmVersion, toolVersionForDist, toolVersionForMethod } from "./provenance.ts";

describe("toolVersionForDist", () => {
	it("matches the Python pin shape: <label>@<12 hex>[+git.<sha>]", () => {
		const dist = mkdtempSync(join(tmpdir(), "dist-"));
		writeFileSync(join(dist, "package.json"), JSON.stringify({ version: "0.2.0" }));
		mkdirSync(join(dist, "pkg"));
		writeFileSync(join(dist, "pkg", "a.js"), "console.log(1)\n");
		writeFileSync(join(dist, "ENGINE_COMMIT.txt"), "ebf1a7996df49f99fb40f4f67713e61cfd19c731\n");
		const pin = toolVersionForDist(dist);
		expect(pin).toMatch(/^0\.2\.0@[0-9a-f]{12}\+git\.ebf1a7996df49f99fb40f4f67713e61cfd19c731$/);
	});

	it("ENGINE_*.txt files never change the hash", () => {
		const dist = mkdtempSync(join(tmpdir(), "dist-"));
		writeFileSync(join(dist, "a.js"), "x");
		const before = toolVersionForDist(dist);
		writeFileSync(join(dist, "ENGINE_NOTE.txt"), "hello");
		expect(toolVersionForDist(dist)).toBe(before);
	});

	it("changes when a payload byte changes", () => {
		const dist = mkdtempSync(join(tmpdir(), "dist-"));
		writeFileSync(join(dist, "a.js"), "x");
		const before = toolVersionForDist(dist);
		writeFileSync(join(dist, "a.js"), "y");
		expect(toolVersionForDist(dist)).not.toBe(before);
	});

	it("returns null for a missing or empty path", () => {
		expect(toolVersionForDist("/nonexistent/dist")).toBeNull();
		expect(toolVersionForDist("")).toBeNull();
	});
});

describe("toolVersionForMethod", () => {
	it("reads npm versions for npm engines and content hashes for dists", () => {
		const root = mkdtempSync(join(tmpdir(), "root-"));
		mkdirSync(join(root, "node_modules", "docxodus"), { recursive: true });
		writeFileSync(join(root, "node_modules", "docxodus", "package.json"), JSON.stringify({ version: "12.6.2" }));
		expect(toolVersionForMethod("docxodus", "", root)).toBe("12.6.2");
		expect(npmVersion("nope", root)).toBeNull();
		const dist = mkdtempSync(join(tmpdir(), "dist-"));
		writeFileSync(join(dist, "a.js"), "x");
		expect(toolVersionForMethod("jubarte-rust", dist, root)).toMatch(/^dist-[^@]+@[0-9a-f]{12}$/);
	});
});

describe("hardwareInfo", () => {
	it("carries the fields the tables print", () => {
		const h = hardwareInfo();
		expect(h.cores).toBeGreaterThan(0);
		expect(h.ram_gb).toBeGreaterThan(0);
		expect(typeof h.cpu).toBe("string");
		expect(h.system).toBe(process.platform);
	});
});
