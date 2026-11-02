import { describe, expect, test } from "vitest";
import {
  esc,
  renderBars,
  renderHeadlines,
  renderMethod,
  renderRow,
  renderStates,
  renderTable,
} from "../src/index.ts";
import { rawFixture } from "./fixture.ts";
import {
  escapeGoldenText,
  goldenBars,
  goldenHeadlines,
  goldenMethod,
  row as goldenRow,
  goldenStates,
  goldenTable,
} from "./golden.ts";

const heading = "By corpus state";

describe("raw jubarte facts parity", () => {
  test("the raw fixture keeps jubarte's ASCII apostrophes", () => {
    expect(rawFixture.home_groups[0]?.title).toContain("Word's own export");
    expect(rawFixture.home_groups[1]?.note).toContain("release's samples");
  });

  test("the golden escaping map matches esc", () => {
    expect(escapeGoldenText("& < > \" '")).toBe(esc("& < > \" '"));
  });

  test.each(rawFixture.tables)("renderTable matches the escaped golden for $id", (table) => {
    expect(renderTable(table)).toBe(goldenTable(table, true));
  });

  test.each(rawFixture.tables.flatMap((table) => table.rows))(
    "renderRow matches the escaped golden for $tool",
    (row) => {
      expect(renderRow(row)).toBe(goldenRow(row));
    },
  );

  test("renderHeadlines matches the escaped golden", () => {
    expect(renderHeadlines(rawFixture.headlines)).toBe(goldenHeadlines(rawFixture.headlines));
  });

  test("renderStates matches the escaped golden", () => {
    expect(renderStates(rawFixture.states, { heading })).toBe(
      goldenStates(rawFixture.states, heading, true),
    );
  });

  test("renderBars matches the escaped golden", () => {
    expect(goldenBars(rawFixture.home_groups)).not.toBe(renderBars(rawFixture.home_groups));
    expect(renderBars(rawFixture.home_groups)).toBe(goldenBars(rawFixture.home_groups, true));
  });

  test("renderMethod matches the escaped golden", () => {
    expect(renderMethod(rawFixture.method)).toBe(goldenMethod(rawFixture.method));
  });
});
