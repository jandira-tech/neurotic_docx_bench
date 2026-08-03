import { describe, expect, it } from "vitest";
import {
	buildFidelityTable,
	computeIttStats,
	type FidelityRow,
	mean,
	median,
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

describe("median/mean", () => {
	it("handles empty, odd, even", () => {
		expect(median([])).toBe(0);
		expect(median([3, 1, 2])).toBe(2);
		expect(median([1, 2, 3, 4])).toBe(2.5);
		expect(mean([])).toBe(0);
		expect(mean([1, 2, 3])).toBe(2);
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
