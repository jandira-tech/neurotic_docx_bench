import { describe, expect, it } from "vitest";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import {
	buildFidelityTable,
	computeIttStats,
	type FidelityRow,
	isMainPath,
	mean,
	median,
	readFidelityRows,
} from "./update-readme-ranking.ts";

const completed = { n_docs: 4, overall_median: 80, n_failures: 2 };

function row(partial: Partial<FidelityRow>): FidelityRow {
	return {
		vendor: "acme",
		benchmark: "script_redlines",
		tool_version: "1.0.0",
		generate: "",
		n_docs: 10,
		overall_mean: 80,
		overall_median: 80,
		exact_100: 0,
		n_failures: 0,
		itt_median: 80,
		itt_mean: 80,
		itt_n: 10,
		itt_approx: false,
		render: "soffice",
		run_name: "acme",
		family: null,
		corpus_revision: null,
		timestamp: "2026-08-02T00:00:00Z",
		...partial,
	} as FidelityRow;
}

describe("readFidelityRows jubarte full-corpus floor", () => {
	it("drops jubarte-* rows with ITT docs under 760 so a 164-doc subset cannot rank", () => {
		const dir = mkdtempSync(join(tmpdir(), "fidelity-jubarte-n-"));
		const path = join(dir, "bench.jsonl");
		try {
			writeFileSync(
				path,
				[
					JSON.stringify({
						vendor: "jubarte-rust",
						benchmark: "script_redlines",
						tool_version: "jubarte-rust@subset164",
						n_docs: 164,
						itt_n_docs: 164,
						itt_mean: 92.21,
						itt_median: 99.92,
						overall_mean: 92.21,
						overall_median: 99.92,
					}),
					JSON.stringify({
						vendor: "jubarte",
						benchmark: "script_redlines",
						tool_version: "jubarte-final@subset163",
						n_docs: 163,
						itt_n_docs: 167,
						itt_mean: 87.89,
						itt_median: 91.84,
						overall_mean: 90.04,
						overall_median: 91.99,
					}),
					JSON.stringify({
						vendor: "jubarte-ast",
						benchmark: "script_redlines",
						tool_version: "jubarte-final@subset48",
						n_docs: 48,
						itt_n_docs: 48,
						overall_mean: 65.18,
						overall_median: 63.35,
					}),
					JSON.stringify({
						vendor: "jubarte-rust",
						benchmark: "script_redlines",
						tool_version: "jubarte-rust@full763",
						n_docs: 763,
						itt_n_docs: 763,
						itt_mean: 84.4,
						itt_median: 92.61,
						overall_mean: 84.4,
						overall_median: 92.61,
					}),
					JSON.stringify({
						vendor: "folio",
						benchmark: "script_redlines",
						tool_version: "0.3.1",
						n_docs: 205,
						overall_mean: 55.31,
						overall_median: 53.75,
					}),
				].join("\n") + "\n",
			);
			const rows = readFidelityRows(path);
			expect(rows.map((r) => r.tool_version).sort()).toEqual([
				"0.3.1",
				"jubarte-rust@full763",
			]);
		} finally {
			rmSync(dir, { recursive: true, force: true });
		}
	});
});

describe("readFidelityRows holdout", () => {
	it("drops holdout_mode=only so a 20-doc re-run cannot set current", () => {
		const dir = mkdtempSync(join(tmpdir(), "fidelity-holdout-"));
		const path = join(dir, "bench.jsonl");
		try {
			writeFileSync(
				path,
				[
					JSON.stringify({
						vendor: "folio",
						benchmark: "script_redlines",
						tool_version: "0.3.1",
						corpus_revision: "5ed816028d99",
						timestamp: "2026-08-13T02:00:00+00:00",
						n_docs: 763,
						overall_mean: 61,
						overall_median: 61,
					}),
					JSON.stringify({
						vendor: "folio",
						benchmark: "script_redlines",
						tool_version: "0.3.1",
						corpus_revision: "holdoutonlyxx",
						holdout_mode: "only",
						timestamp: "2026-08-13T03:00:00+00:00",
						n_docs: 40,
						overall_mean: 80,
						overall_median: 80,
					}),
				].join("\n") + "\n",
			);
			const rows = readFidelityRows(path);
			expect(rows).toHaveLength(1);
			expect(rows[0]?.corpus_revision).toBe("5ed816028d99");
		} finally {
			rmSync(dir, { recursive: true, force: true });
		}
	});
});

describe("median/mean", () => {
	it("handles empty, odd, even", () => {
		expect(median([])).toBe(0);
		expect(median([3, 1, 2])).toBe(2);
		expect(median([1, 2, 3, 4])).toBe(2.5);
		expect(mean([])).toBe(0);
		expect(mean([1, 2, 3])).toBe(2);
	});
});

describe("isMainPath", () => {
	const moduleUrl = import.meta.url;

	it("is true only for the exact resolved script path", () => {
		const self = fileURLToPath(moduleUrl);
		// This test file is not update-readme-ranking.ts — exact path to ranking script:
		const rankingUrl = new URL("./update-readme-ranking.ts", import.meta.url).href;
		const rankingPath = fileURLToPath(rankingUrl);
		expect(isMainPath(rankingPath, rankingUrl)).toBe(true);
		// Same basename, different directory → must NOT fire.
		expect(isMainPath("/tmp/other/update-readme-ranking.ts", rankingUrl)).toBe(false);
		expect(isMainPath(self, rankingUrl)).toBe(false);
		expect(isMainPath(undefined, rankingUrl)).toBe(false);
	});
});

describe("computeIttStats", () => {
	it("uses server-emitted itt_* fields verbatim when present", () => {
		const stats = computeIttStats(
			{ itt_median: 12.5, itt_mean: 20, itt_n_docs: 8, scores: { a: 100 } },
			completed,
		);
		expect(stats).toEqual({
			itt_median: 12.5,
			itt_mean: 20,
			itt_n: 8,
			itt_approx: false,
		});
	});

	it("derives ITT from scores + failures, deduped, scored doc keeps score", () => {
		const stats = computeIttStats(
			{
				scores: { a: 100, b: 50 },
				failures: [{ doc: "c" }, { doc: "c" }, { doc: "a" }],
			},
			completed,
		);
		// values = [100, 50, 0] — c zeroed once, a keeps its score.
		expect(stats.itt_n).toBe(3);
		expect(stats.itt_median).toBe(50);
		expect(stats.itt_mean).toBeCloseTo(50);
		expect(stats.itt_approx).toBe(false);
	});

	it("equals completed stats when there are no failures", () => {
		const stats = computeIttStats(
			{ scores: { a: 90, b: 70 } },
			{ n_docs: 2, overall_median: 80, n_failures: 0 },
		);
		expect(stats.itt_median).toBe(80);
		expect(stats.itt_n).toBe(2);
	});

	it("approximates legacy lines without per-doc scores and flags them", () => {
		const stats = computeIttStats({}, completed);
		// [80, 80, 80, 80, 0, 0] → median 80, mean 53.33, flagged approximate.
		expect(stats.itt_approx).toBe(true);
		expect(stats.itt_n).toBe(6);
		expect(stats.itt_median).toBe(80);
		expect(stats.itt_mean).toBeCloseTo(53.333, 2);
	});
});

describe("fidelity table ITT ranking", () => {
	it("ranks a crashy tool below a clean tool despite a higher completed median", () => {
		const clean = row({
			vendor: "clean",
			overall_median: 80,
			overall_mean: 80,
			itt_median: 80,
			itt_mean: 80,
		});
		const crashy = row({
			vendor: "crashy",
			overall_median: 90,
			overall_mean: 90,
			n_failures: 5,
			itt_median: 40,
			itt_mean: 45,
			itt_n: 10,
		});
		const best = new Map<string, FidelityRow>([
			["clean__script_redlines__1", clean],
			["crashy__script_redlines__1", crashy],
		]);
		const table = buildFidelityTable(best, "script_redlines");
		const cleanRank = table.split("\n").findIndex((l) => l.includes("| clean |"));
		const crashyRank = table.split("\n").findIndex((l) => l.includes("| crashy |"));
		expect(cleanRank).toBeGreaterThan(0);
		expect(cleanRank).toBeLessThan(crashyRank);
		expect(table).toContain("ITT Median");
	});

	it("splits current-corpus and legacy-corpus rows into separate tables", () => {
		const current = row({
			vendor: "fresh",
			corpus_revision: "abc123def456",
			overall_mean: 70,
			itt_mean: 70,
			itt_median: 70,
			overall_median: 70,
		});
		const legacy = row({
			vendor: "stale",
			overall_mean: 95,
			itt_mean: 95,
			itt_median: 95,
			overall_median: 95,
		});
		const best = new Map<string, FidelityRow>([
			["fresh__script_redlines__1", current],
			["stale__script_redlines__1", legacy],
		]);
		const table = buildFidelityTable(best, "script_redlines");
		expect(table).toContain("**Current corpus**");
		expect(table).toContain("**Legacy corpus**");
		// The stale 95-mean line must NOT outrank the fresh line — it lives in
		// the legacy table below, and both tables restart ranks at 1.
		const currentIdx = table.indexOf("| fresh |");
		const legacyIdx = table.indexOf("| stale |");
		expect(currentIdx).toBeGreaterThan(0);
		expect(currentIdx).toBeLessThan(legacyIdx);
	});

	it("does not rank an older corpus_revision stamp with current", () => {
		const oldStamp = row({
			vendor: "docxodus-old",
			tool_version: "9.0.0",
			corpus_revision: "b7f467074a51",
			timestamp: "2026-08-04T13:11:19+00:00",
			overall_mean: 60,
			itt_mean: 60,
			itt_median: 60,
			overall_median: 60,
		});
		const newStamp = row({
			vendor: "docxodus-new",
			tool_version: "9.8.0",
			corpus_revision: "5ed816028d99",
			timestamp: "2026-08-13T02:15:21+00:00",
			overall_mean: 61,
			itt_mean: 61,
			itt_median: 61,
			overall_median: 61,
		});
		const table = buildFidelityTable(
			new Map([
				["old__script_redlines__9.0.0", oldStamp],
				["new__script_redlines__9.8.0", newStamp],
			]),
			"script_redlines",
		);
		const legacyAt = table.indexOf("**Legacy corpus**");
		expect(legacyAt).toBeGreaterThan(0);
		expect(table.indexOf("9.8.0")).toBeLessThan(legacyAt);
		expect(table.indexOf("9.0.0")).toBeGreaterThan(legacyAt);
		const currentHeading = table.slice(table.indexOf("**Current corpus**"), legacyAt);
		expect(currentHeading).not.toContain("lines stamped with");
		expect(currentHeading.toLowerCase()).toContain("newest");
		expect(currentHeading).toContain("5ed816028d99");
		expect(table.slice(legacyAt, legacyAt + 200)).not.toContain("smaller corpora");
	});

	it("newest stamp wins even when the older hash has a higher ITT", () => {
		const oldHigh = row({
			vendor: "docxodus-old",
			tool_version: "9.0.0",
			corpus_revision: "b7f467074a51",
			timestamp: "2026-08-04T13:11:19+00:00",
			overall_mean: 90,
			itt_mean: 90,
			itt_median: 90,
			overall_median: 90,
		});
		const newLow = row({
			vendor: "docxodus-new",
			tool_version: "9.8.0",
			corpus_revision: "5ed816028d99",
			timestamp: "2026-08-13T02:15:21+00:00",
			overall_mean: 60,
			itt_mean: 60,
			itt_median: 60,
			overall_median: 60,
		});
		const table = buildFidelityTable(
			new Map([
				["old__script_redlines__9.0.0", oldHigh],
				["new__script_redlines__9.8.0", newLow],
			]),
			"script_redlines",
		);
		const legacyAt = table.indexOf("**Legacy corpus**");
		expect(legacyAt).toBeGreaterThan(0);
		expect(table.indexOf("9.8.0")).toBeLessThan(legacyAt);
		expect(table.indexOf("9.0.0")).toBeGreaterThan(legacyAt);
	});

	it("does not let another bench's newer hash collapse this bench's split", () => {
		const scriptStamped = row({
			vendor: "fresh",
			benchmark: "script_redlines",
			corpus_revision: "aaaa1111aaaa",
			timestamp: "2026-08-01T00:00:00+00:00",
			overall_mean: 70,
			itt_mean: 70,
			itt_median: 70,
			overall_median: 70,
		});
		const scriptUnstamped = row({
			vendor: "stale",
			benchmark: "script_redlines",
			corpus_revision: null,
			timestamp: "2026-08-01T00:00:00+00:00",
			overall_mean: 95,
			itt_mean: 95,
			itt_median: 95,
			overall_median: 95,
		});
		const visualNewer = row({
			vendor: "other",
			benchmark: "visual_redlines",
			tool_version: "9.8.0",
			corpus_revision: "bbbb2222bbbb",
			timestamp: "2026-08-13T00:00:00+00:00",
		});
		const table = buildFidelityTable(
			new Map([
				["fresh__script_redlines__1", scriptStamped],
				["stale__script_redlines__1", scriptUnstamped],
				["other__visual_redlines__9.8.0", visualNewer],
			]),
			"script_redlines",
		);
		// Per-benchmark current is aaaa1111aaaa. A global picker would take
		// bbbb2222bbbb, empty this bench's current, and dump fresh+stale
		// into one unlabeled table.
		expect(table).toContain("**Current corpus**");
		expect(table).toContain("**Legacy corpus**");
		expect(table.indexOf("| fresh |")).toBeLessThan(table.indexOf("| stale |"));
		expect(table).not.toContain("9.8.0");
	});

	it("renders a single table when only one regime exists", () => {
		const only = row({ vendor: "solo" });
		const best = new Map<string, FidelityRow>([["solo__script_redlines__1", only]]);
		const table = buildFidelityTable(best, "script_redlines");
		expect(table).not.toContain("**Legacy corpus**");
		expect(table).toContain("| solo |");
	});

	it("marks approximate ITT stats with ~", () => {
		const legacy = row({ vendor: "old", itt_approx: true });
		const best = new Map<string, FidelityRow>([["old__script_redlines__1", legacy]]);
		const table = buildFidelityTable(best, "script_redlines");
		expect(table).toMatch(/80\.00~/);
	});
});

describe("coverage mismatch is stated, not left for the reader to spot", () => {
	// Plan Chapter 6, D1 + ledger rule 2: two rows with different ITT Docs are
	// not the same measurement. Real case: jubarte-wasm ranked #1 at n=195 above
	// jubarte-rust at n=763 — on an easier subset, which the table showed only as
	// a number in a column nobody reads.
	const mixed = new Map<string, FidelityRow>([
		["a", row({ vendor: "wide", itt_n: 763, n_docs: 763, corpus_revision: "abc123" })],
		["b", row({ vendor: "narrow", itt_n: 195, n_docs: 195, corpus_revision: "abc123" })],
	]);

	it("warns when rows in one table cover different document counts", () => {
		const table = buildFidelityTable(mixed, "script_redlines");
		expect(table.toLowerCase()).toContain("not the same measurement");
		expect(table).toContain("763");
		expect(table).toContain("195");
	});

	it("stays quiet when every row covers the same documents", () => {
		const even = new Map<string, FidelityRow>([
			["a", row({ vendor: "one", itt_n: 763, n_docs: 763, corpus_revision: "abc123" })],
			["b", row({ vendor: "two", itt_n: 763, n_docs: 763, corpus_revision: "abc123" })],
		]);
		expect(buildFidelityTable(even, "script_redlines").toLowerCase()).not.toContain(
			"not the same measurement",
		);
	});
});
