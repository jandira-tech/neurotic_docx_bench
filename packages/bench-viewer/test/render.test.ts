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
import type { Headline, HomeGroup, MethodPoint, Row, StateCell, Table } from "../src/types.ts";
import { fixture } from "./fixture.ts";
import {
  goldenBars,
  goldenHeadlines,
  goldenMethod,
  row as goldenRow,
  goldenStates,
  goldenTable,
} from "./golden.ts";

describe("jubarte golden markup", () => {
  const rows = fixture.tables.flatMap((table) =>
    table.rows.map((row, rowIndex) => ({ row, rowIndex, tableId: table.id })),
  );

  test.each(rows)("renderRow matches row() for $tableId row $rowIndex", ({ row }) => {
    expect(renderRow(row)).toBe(goldenRow(row));
  });

  test.each(fixture.tables)("renderTable matches the table section for $id", (table) => {
    expect(renderTable(table)).toBe(goldenTable(table));
  });

  test("renderHeadlines matches the headlines block", () => {
    expect(renderHeadlines(fixture.headlines)).toBe(goldenHeadlines(fixture.headlines));
  });

  test("renderStates matches the states section", () => {
    expect(renderStates(fixture.states)).toBe(goldenStates(fixture.states));
  });

  test("renderBars matches the home-page bar groups", () => {
    expect(renderBars(fixture.home_groups)).toBe(goldenBars(fixture.home_groups));
  });

  test("renderMethod matches the METHOD section", () => {
    expect(renderMethod(fixture.method)).toBe(goldenMethod(fixture.method));
  });
});

describe("HTML escaping", () => {
  test("esc escapes all five HTML metacharacters", () => {
    expect(esc("& < > \" '")).toBe("&amp; &lt; &gt; &quot; &#39;");
  });

  test("every text field in every rendered value is escaped", () => {
    const script = "<script>x</script>";
    const maliciousRow: Row = {
      ...fixture.tables[0].rows[0],
      rank: script,
      tool: script,
      pin: script,
      note: script,
    };
    const maliciousTable: Table = {
      ...fixture.tables[0],
      id: script,
      title: script,
      meta: script,
      desc: script,
      rows: [maliciousRow],
    };
    const maliciousHeadline: Headline = {
      label: script,
      value: script,
      vs: script,
      sub: script,
    };
    const maliciousState: StateCell = {
      name: script,
      n: script,
      rows: [{ ...fixture.states[0].rows[0], tool: script }],
    };
    const maliciousGroup: HomeGroup = {
      title: script,
      meta: script,
      rows: [{ ...fixture.home_groups[0].rows[0], name: script }],
      note: script,
    };
    const maliciousMethod: MethodPoint = { t: script, d: script };

    const outputs = [
      renderRow(maliciousRow),
      renderTable(maliciousTable),
      renderHeadlines([maliciousHeadline]),
      renderStates([maliciousState]),
      renderBars([maliciousGroup]),
      renderMethod([maliciousMethod]),
    ];

    for (const output of outputs) {
      expect(output).not.toContain("<script>");
      expect(output).not.toContain("</script>");
    }
  });
});
