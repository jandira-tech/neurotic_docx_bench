import { describe, expect, test } from "vitest";
import { parseScores } from "../src/index.ts";
import { fixture } from "./fixture.ts";

describe("parseScores", () => {
  test("accepts the jubarte scores fixture", () => {
    expect(parseScores(fixture)).toEqual(fixture);
  });

  test("rejects a missing tables field and names the path", () => {
    const missingTables = structuredClone(fixture) as unknown as Record<string, unknown>;
    delete missingTables.tables;

    expect(() => parseScores(missingTables)).toThrowError(TypeError);
    expect(() => parseScores(missingTables)).toThrowError(/tables/);
  });

  test("rejects a non-numeric row median and names the exact path", () => {
    const invalidMedian = structuredClone(fixture) as unknown as {
      tables: Array<{ rows: Array<{ median: unknown }> }>;
    };
    invalidMedian.tables[0].rows[0].median = "x";

    expect(() => parseScores(invalidMedian)).toThrowError(TypeError);
    expect(() => parseScores(invalidMedian)).toThrowError(/tables\[0\]\.rows\[0\]\.median/);
  });
});
