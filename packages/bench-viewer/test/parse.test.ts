import { describe, expect, test } from "vitest";
import { parseScores } from "../src/index.ts";
import type { Scores } from "../src/types.ts";
import { fixture } from "./fixture.ts";

const cloneFixture = (): Scores => structuredClone(fixture);

function setField(target: object, key: string, value: unknown): void {
  (target as Record<string, unknown>)[key] = value;
}

function expectRejected(scores: unknown, path: RegExp): void {
  expect(() => parseScores(scores)).toThrowError(TypeError);
  expect(() => parseScores(scores)).toThrowError(path);
}

describe("parseScores", () => {
  test("accepts the jubarte scores fixture", () => {
    expect(parseScores(fixture)).toEqual(fixture);
  });

  test("rejects a missing tables field and names the path", () => {
    const missingTables = cloneFixture() as unknown as Record<string, unknown>;
    delete missingTables.tables;

    expectRejected(missingTables, /tables/);
  });

  test("rejects a non-numeric row median and names the exact path", () => {
    const invalidMedian = cloneFixture();
    setField(invalidMedian.tables[0].rows[0], "median", "x");

    expectRejected(invalidMedian, /tables\[0\]\.rows\[0\]\.median/);
  });

  test.each(["repo", "viewer"] as const)("rejects a non-http(s) %s URL", (field) => {
    for (const url of [
      "javascript:alert(1)",
      "data:text/html,bad",
      "https:example.com",
      "/relative",
      "ftp://example.com",
    ]) {
      const invalid = cloneFixture();
      setField(invalid, field, url);

      expectRejected(invalid, new RegExp(`scores:.*${field}`));
    }
  });

  test("accepts absolute http and https URLs", () => {
    const valid = cloneFixture();
    valid.repo = "http://example.com/bench";
    valid.viewer = "https://example.com/viewer";

    expect(() => parseScores(valid)).not.toThrow();
  });

  test("rejects score values outside 0 through 100", () => {
    for (const field of ["median", "mean"] as const) {
      for (const value of [-0.01, 100.01, Number.NaN, Number.POSITIVE_INFINITY]) {
        const invalid = cloneFixture();
        setField(invalid.tables[0].rows[0], field, value);

        expectRejected(invalid, new RegExp(`tables\\[0\\]\\.rows\\[0\\]\\.${field}`));
      }
    }

    const invalidState = cloneFixture();
    setField(invalidState.states[0].rows[0], "median", 101);
    expectRejected(invalidState, /states\[0\]\.rows\[0\]\.median/);

    const invalidHomeBar = cloneFixture();
    setField(invalidHomeBar.home_groups[0].rows[0], "v", -1);
    expectRejected(invalidHomeBar, /home_groups\[0\]\.rows\[0\]\.v/);
  });

  test("accepts score and count boundaries", () => {
    const valid = cloneFixture();
    const row = valid.tables[0].rows[0];
    row.median = 0;
    row.mean = 100;
    row.docs = 0;
    row.failed = 0;
    valid.states[0].rows[0].median = 100;
    valid.home_groups[0].rows[0].v = 0;

    expect(() => parseScores(valid)).not.toThrow();
  });

  test("rejects negative and fractional document counts", () => {
    for (const field of ["docs", "failed"] as const) {
      for (const value of [-1, 1.5, Number.NaN, Number.POSITIVE_INFINITY]) {
        const invalid = cloneFixture();
        setField(invalid.tables[0].rows[0], field, value);

        expectRejected(invalid, new RegExp(`tables\\[0\\]\\.rows\\[0\\]\\.${field}`));
      }
    }
  });

  test.each([
    [
      "rank",
      (scores: Scores) => setField(scores.tables[0].rows[0], "rank", 1),
      /tables\[0\]\.rows\[0\]\.rank/,
    ],
    [
      "median",
      (scores: Scores) => setField(scores.tables[0].rows[0], "median", "1"),
      /tables\[0\]\.rows\[0\]\.median/,
    ],
    [
      "ours",
      (scores: Scores) => setField(scores.tables[0].rows[0], "ours", null),
      /tables\[0\]\.rows\[0\]\.ours/,
    ],
    [
      "note",
      (scores: Scores) => setField(scores.tables[0].rows[0], "note", null),
      /tables\[0\]\.rows\[0\]\.note/,
    ],
    ["rows", (scores: Scores) => setField(scores.tables[0], "rows", {}), /tables\[0\]\.rows/],
    [
      "provenance value",
      (scores: Scores) => setField(scores.provenance, "source", "not-an-array"),
      /provenance\.source/,
    ],
  ])("rejects a wrong %s type and names the path", (_field, mutate, path) => {
    const invalid = cloneFixture();
    mutate(invalid);

    expectRejected(invalid, path);
  });

  test("rejects fields outside the bench-ops contract", () => {
    const invalid = cloneFixture();
    setField(invalid, "unexpected", true);

    expectRejected(invalid, /unexpected/);
  });

  test("parses the optional state table id", () => {
    const valid = cloneFixture();
    setField(valid.states[0], "table", "conversion-sample");

    const parsed = parseScores(valid);
    const state = parsed.states[0] as unknown as { table?: string | null };

    expect(state.table).toBe("conversion-sample");
  });
});
