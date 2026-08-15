import { describe, it, expect } from "vitest";
import { existsSync, readFileSync, mkdtempSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { execSync } from "node:child_process";

const ROUNDTRIP_SOURCE = "corpus/word_based/word_working_roundtrip";
const haveCorpus = existsSync(ROUNDTRIP_SOURCE);
const haveFolio = existsSync("node_modules/@stll/folio-core/package.json");

// generate-roundtrips.mjs is a CLI script with no exported entry point, so we
// invoke it as a subprocess — the same boundary `bench run` uses.
function runCli(args: string[]): {
	status: number;
	stdout: string;
	stderr: string;
} {
	try {
		const stdout = execSync(
			`node scripts/generate-roundtrips.mjs ${args.join(" ")}`,
			{
				encoding: "utf-8",
				timeout: 120_000,
				env: { ...process.env },
			},
		);
		return { status: 0, stdout, stderr: "" };
	} catch (e: any) {
		return {
			status: e.status ?? 1,
			stdout: e.stdout ?? "",
			stderr: e.stderr ?? "",
		};
	}
}

const haveStemma = existsSync("src/neurotic_docx_bench/utils/stemma/stemma");
const haveSafeDocx = existsSync(
	"src/neurotic_docx_bench/utils/safe-docx-compare/node_modules/@usejunior/docx-compare/dist/index.js",
);

describe.runIf(haveCorpus && haveStemma)(
	"generate-roundtrips stemma self-compare",
	() => {
		it("produces a valid DOCX via stemma compare(file, file)", () => {
			const out = mkdtempSync(join(tmpdir(), "rt-stemma-"));
			const r = runCli([
				"--tool=stemma",
				`--source-dir=${ROUNDTRIP_SOURCE}`,
				`--out=${out}`,
				"--limit=1",
				"--force",
			]);
			expect(r.status).toBe(0);
			const dir = join(out, "stemma");
			const files = readdirSync(dir).filter((f) => f.endsWith(".docx"));
			expect(files.length).toBeGreaterThanOrEqual(1);
			expect(readFileSync(join(dir, files[0]!)).length).toBeGreaterThan(1000);
		}, 120_000);
	},
);

describe.runIf(haveCorpus && haveSafeDocx)(
	"generate-roundtrips safe-docx self-compare",
	() => {
		it("produces a valid DOCX via compareDocuments(file, file)", () => {
			const out = mkdtempSync(join(tmpdir(), "rt-safe-"));
			const r = runCli([
				"--tool=safe-docx-compare",
				`--source-dir=${ROUNDTRIP_SOURCE}`,
				`--out=${out}`,
				"--limit=1",
				"--force",
			]);
			expect(r.status).toBe(0);
			const dir = join(out, "safe-docx-compare");
			const files = readdirSync(dir).filter((f) => f.endsWith(".docx"));
			expect(files.length).toBeGreaterThanOrEqual(1);
			expect(readFileSync(join(dir, files[0]!)).length).toBeGreaterThan(1000);
		}, 120_000);
	},
);

describe.runIf(haveCorpus && haveFolio)(
	"generate-roundtrips folio route",
	() => {
		it("produces a valid re-serialized DOCX for each input", () => {
			const out = mkdtempSync(join(tmpdir(), "rt-folio-"));
			const r = runCli([
				"--tool=folio",
				`--source-dir=${ROUNDTRIP_SOURCE}`,
				`--out=${out}`,
				"--limit=2",
				"--force",
			]);
			expect(r.status).toBe(0);

			const folioDir = join(out, "folio");
			expect(existsSync(folioDir)).toBe(true);
			const files = readdirSync(folioDir).filter((f) => f.endsWith(".docx"));
			expect(files.length).toBeGreaterThanOrEqual(1);

			const outBytes = new Uint8Array(readFileSync(join(folioDir, files[0]!)));
			expect(outBytes.length).toBeGreaterThan(1000);
		}, 120_000);

		it("records no failures on a successful run", () => {
			const out = mkdtempSync(join(tmpdir(), "rt-folio-fail-"));
			const r = runCli([
				"--tool=folio",
				`--source-dir=${ROUNDTRIP_SOURCE}`,
				`--out=${out}`,
				"--limit=1",
				"--force",
			]);
			expect(r.status).toBe(0);
			const failuresPath = join(out, "folio", "generate_failures.json");
			expect(existsSync(failuresPath)).toBe(true);
			expect(readFileSync(failuresPath, "utf-8").trim()).toBe("[]");
		}, 120_000);
	},
);
