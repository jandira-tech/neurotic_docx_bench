import { describe, it, expect } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

// The folio viewer harness (harness/folio-viewer/) renders DOCX via
// @stll/folio-react's renderAsync for the Playwright renderer. The full
// Chromium render is exercised by `bench run --only folio-playwright`; these
// tests pin the static contract the renderer depends on, without needing
// a browser.

const HARNESS_DIR = "harness/folio-viewer";
const haveHarness = existsSync(HARNESS_DIR);

describe.runIf(haveHarness)("folio viewer harness static contract", () => {
	it("harness.html exposes a hidden #fileInput and a #host container", () => {
		const html = readFileSync(join(HARNESS_DIR, "harness.html"), "utf-8");
		expect(html).toContain('id="fileInput"');
		expect(html).toContain('id="host"');
		expect(html).toContain('type="file"');
	});

	it("harness-main.ts imports renderAsync and sets the readiness globals", () => {
		const src = readFileSync(join(HARNESS_DIR, "src/harness-main.ts"), "utf-8");
		expect(src).toContain('import { renderAsync } from "@stll/folio-react"');
		// The Playwright renderer polls these globals (see bench.yaml readiness_js).
		expect(src).toContain("__folioReady");
		expect(src).toContain("__folioError");
		// The renderer uploads via #fileInput; the script must wire a change listener.
		expect(src).toContain('addEventListener("change"');
		// readOnly viewing mode for clean capture.
		expect(src).toContain("readOnly: true");
	});

	it("package.json pins the expected folio-react version and dedupes folio-core", () => {
		const pkg = JSON.parse(
			readFileSync(join(HARNESS_DIR, "package.json"), "utf-8"),
		);
		expect(pkg.dependencies["@stll/folio-react"]).toBe("0.13.4");
		expect(pkg.overrides["@stll/folio-core"]).toBe("0.17.1");
	});
});
