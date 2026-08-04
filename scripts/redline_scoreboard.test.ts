/**
 * D-2 accept/reject scoreboard — contract tests.
 *
 * RED (TDD): this file is written before scripts/redline_scoreboard.ts exists,
 * so the first run fails on the missing module (stated per plan §4 D-2; the
 * assertions below are the real contract once the module lands).
 *
 * The contract under test:
 *  - every scoreboard row is HARD-PINNED: building a row without an engine pin,
 *    corpus vintage, or bench source commit throws (MissingEnginePinError) —
 *    reusing the A-4 pin mandate; no "unknown engine" rows can ever land in
 *    RESULTS.md;
 *  - rows carry the three-lens verdicts (engine self accept/reject, folio
 *    views, WV-1 word sample) and lens DISAGREEMENT is the alarm;
 *  - the RESULTS.md section updates idempotently between markers.
 */
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
	MissingEnginePinError,
	buildScoreboardRow,
	detectLensDisagreement,
	parseWordValidateOutput,
	renderScoreboardSection,
	resolveCorpusVintage,
	resolveEnginePin,
	updateResultsScoreboard,
	writeScoreboardRow,
} from "./redline_scoreboard.ts";
import type { LensVerdict, ScoreboardRow } from "./redline_scoreboard.ts";

const CORPUS_DIR = "corpus/word_based";
const haveCorpus = existsSync(join(CORPUS_DIR, "centralized_mapping_randomized.csv"));

const provenance = {
	engine: "jubarte-native",
	enginePin: "abc1234",
	corpusVintage: "daa7d92",
	benchCommit: "854abe3",
	folioCommit: "d2d2907",
};

const passing: LensVerdict = { ran: true, acceptOk: true, rejectOk: true };
const failing: LensVerdict = { ran: true, acceptOk: false, rejectOk: true };
const skipped: LensVerdict = { ran: false };

describe("hard pin (A-4 mandate)", () => {
	it("refuses a row without an engine pin", () => {
		expect(() =>
			buildScoreboardRow({
				...provenance,
				enginePin: "",
				pair: "file_1_file_2",
				engineLens: passing,
				folioLens: passing,
			}),
		).toThrow(MissingEnginePinError);
	});

	it("refuses a row without a corpus vintage or bench commit", () => {
		expect(() =>
			buildScoreboardRow({
				...provenance,
				corpusVintage: "",
				pair: "file_1_file_2",
				engineLens: passing,
				folioLens: passing,
			}),
		).toThrow(MissingEnginePinError);
		expect(() =>
			buildScoreboardRow({
				...provenance,
				benchCommit: "",
				pair: "file_1_file_2",
				engineLens: passing,
				folioLens: passing,
			}),
		).toThrow(MissingEnginePinError);
	});

	it("stamps provenance on every row", () => {
		const row = buildScoreboardRow({
			...provenance,
			pair: "file_1_file_2",
			engineLens: passing,
			folioLens: passing,
		});
		expect(row.enginePin).toBe("abc1234");
		expect(row.corpusVintage).toBe("daa7d92");
		expect(row.benchCommit).toBe("854abe3");
		expect(row.engine).toBe("jubarte-native");
		expect(row.disagreement).toBe(false);
	});
});

describe("lens triangulation", () => {
	it("flags disagreement when lenses that ran disagree", () => {
		expect(detectLensDisagreement(passing, failing)).toBe(true);
		expect(detectLensDisagreement(failing, passing)).toBe(true);
	});

	it("no disagreement when lenses agree (both directions)", () => {
		expect(detectLensDisagreement(passing, passing)).toBe(false);
		expect(detectLensDisagreement(failing, failing)).toBe(false);
	});

	it("a skipped lens cannot disagree", () => {
		expect(detectLensDisagreement(passing, skipped)).toBe(false);
		expect(detectLensDisagreement(skipped, failing)).toBe(false);
	});

	it("a disagreeing row is marked as the alarm", () => {
		const row = buildScoreboardRow({
			...provenance,
			pair: "file_1_file_2",
			engineLens: passing,
			folioLens: failing,
		});
		expect(row.disagreement).toBe(true);
	});
});

describe("row persistence (JSONL)", () => {
	it("appends one JSON row per call and round-trips", () => {
		const dir = mkdtempSync(join(tmpdir(), "d2-scoreboard-"));
		try {
			const path = join(dir, "scoreboard.jsonl");
			const row = buildScoreboardRow({
				...provenance,
				pair: "file_1_file_2",
				engineLens: passing,
				folioLens: passing,
			});
			writeScoreboardRow(path, row);
			writeScoreboardRow(path, row);
			const lines = readFileSync(path, "utf8").trim().split("\n");
			expect(lines).toHaveLength(2);
			const parsed = JSON.parse(lines[0]) as ScoreboardRow;
			expect(parsed.enginePin).toBe("abc1234");
			expect(parsed.pair).toBe("file_1_file_2");
		} finally {
			rmSync(dir, { recursive: true, force: true });
		}
	});
});

describe("RESULTS.md scoreboard section", () => {
	const rows: ScoreboardRow[] = [
		buildScoreboardRow({
			...provenance,
			pair: "file_1_file_2",
			engineLens: passing,
			folioLens: passing,
		}),
		buildScoreboardRow({
			...provenance,
			engine: "jubarte-first-lossless",
			enginePin: "def5678",
			pair: "file_1_file_2",
			engineLens: failing,
			folioLens: passing,
		}),
	];

	it("renders one summary line per engine with pin, vintage, commit and pass rates", () => {
		const section = renderScoreboardSection(rows, { runId: "run-1", date: "2026-07-17" });
		expect(section).toContain("jubarte-native");
		expect(section).toContain("abc1234");
		expect(section).toContain("jubarte-first-lossless");
		expect(section).toContain("def5678");
		expect(section).toContain("daa7d92");
		expect(section).toContain("854abe3");
		// the disagreeing engine surfaces its alarm count
		expect(section).toMatch(/disagree/i);
	});

	it("updates RESULTS.md idempotently between markers", () => {
		const dir = mkdtempSync(join(tmpdir(), "d2-results-"));
		try {
			const results = join(dir, "RESULTS.md");
			writeFileSync(
				results,
				"# Benchmark results\n\n## All fidelity runs (flat)\n\nstuff\n\n## Redline generation speed\n\nmore\n",
			);
			updateResultsScoreboard(results, rows, { runId: "run-1", date: "2026-07-17" });
			const once = readFileSync(results, "utf8");
			expect(once).toContain("<!-- D2_SCOREBOARD:BEGIN -->");
			expect(once).toContain("<!-- D2_SCOREBOARD:END -->");
			// the section lands before the speed section, keeping house order
			expect(once.indexOf("D2_SCOREBOARD:BEGIN")).toBeLessThan(
				once.indexOf("## Redline generation speed"),
			);
			updateResultsScoreboard(results, rows, { runId: "run-2", date: "2026-07-18" });
			const twice = readFileSync(results, "utf8");
			expect(twice.match(/D2_SCOREBOARD:BEGIN/g)).toHaveLength(1);
			expect(twice).toContain("run-2");
			expect(twice).not.toContain("run-1");
		} finally {
			rmSync(dir, { recursive: true, force: true });
		}
	});
});

describe("provenance resolution", () => {
	it.runIf(haveCorpus)("corpus vintage is the last commit touching the corpus dir", () => {
		const vintage = resolveCorpusVintage(CORPUS_DIR);
		expect(vintage).toMatch(/^[0-9a-f]{7,40}$/);
	});

	it("engine pin resolution refuses a path with no pin source", () => {
		const dir = mkdtempSync(join(tmpdir(), "d2-nopin-"));
		try {
			expect(() => resolveEnginePin(join(dir, "not-a-real-engine"))).toThrow(
				MissingEnginePinError,
			);
		} finally {
			rmSync(dir, { recursive: true, force: true });
		}
	});
});

describe("WV-1 output parse (PR9: UNJUDGEABLE outcome)", () => {
	it("counts valid/invalid/unjudgeable from per-doc lines", () => {
		const stdout = [
			"  VALID a.docx",
			"  INVALID b.docx: repair dialog (modal detected)",
			"  UNJUDGEABLE c.docx: slow open — no dialog observed within 240s budget",
			"  VALID d.docx",
			"word-validate: 2 valid, 1 invalid, 1 unjudgeable",
		].join("\n");
		const verdict = parseWordValidateOutput(stdout, 4);
		expect(verdict.valid).toBe(2);
		expect(verdict.invalid).toBe(1);
		expect(verdict.unjudgeable).toBe(1);
		expect(verdict.unavailable).toBe(false);
	});

	it("UNJUDGEABLE lines never leak into the valid count", () => {
		const stdout = [
			"  UNJUDGEABLE big.docx: slow open",
			"word-validate: 0 valid, 0 invalid, 1 unjudgeable",
		].join("\n");
		const verdict = parseWordValidateOutput(stdout, 1);
		expect(verdict.valid).toBe(0);
		expect(verdict.invalid).toBe(0);
		expect(verdict.unjudgeable).toBe(1);
	});
});
