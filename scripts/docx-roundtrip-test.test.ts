import { describe, expect, it } from "vitest";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

// Regression guard: scripts/docx-roundtrip-test.mjs once declared local
// `const readBytes`/`toBytes`/`docxIn`/`async function isValidDocx` that
// shadowed the same-named imports from ./docx-utils.mjs — ESM rejects this
// at parse time (SyntaxError: Identifier already declared), making the
// script unloadable. `node --check` catches parse errors without executing.
describe("docx-roundtrip-test.mjs", () => {
	it("parses without SyntaxError (no shadowed-import redeclarations)", () => {
		const script = resolve(import.meta.dirname, "docx-roundtrip-test.mjs");
		// `node --check` exits 0 on a clean parse, non-zero on SyntaxError.
		execFileSync("node", ["--check", script], { stdio: "pipe" });
		expect(true).toBe(true); // reached only if --check succeeded
	});
});
