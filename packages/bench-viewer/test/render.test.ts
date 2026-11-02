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
    const heading = "By corpus state, the 600-document conversion sample";
    expect(renderStates(fixture.states, { heading })).toBe(goldenStates(fixture.states, heading));
  });

  test("renderBars matches the home-page bar groups", () => {
    expect(renderBars(fixture.home_groups)).toBe(goldenBars(fixture.home_groups));
  });

  test("renderMethod matches the METHOD section", () => {
    expect(renderMethod(fixture.method)).toBe(goldenMethod(fixture.method));
  });
});

describe("states options", () => {
  test("uses the caller's heading and does not hardcode a document count", () => {
    const html = renderStates(fixture.states, { heading: "States for the selected sample" });

    expect(html).toContain("<h2>States for the selected sample</h2>");
    expect(html).not.toContain("600-document");
  });

  test("uses a custom state label", () => {
    const html = renderStates(fixture.states, {
      heading: "States",
      label: (name) => `state: ${name}`,
    });

    expect(html).toContain("state: clean");
  });

  test("filters cells by their table id", () => {
    const states: StateCell[] = [
      { ...fixture.states[0], name: "first-cell", table: "table-a" },
      { ...fixture.states[1], name: "second-cell", table: "table-b" },
    ];

    const html = renderStates(states, { heading: "Selected states", table: "table-a" });

    expect(html).toContain("first-cell");
    expect(html).not.toContain("second-cell");
  });
});

describe("score widths", () => {
  test("clamps direct renderer values to the 0 through 100 range", () => {
    const row: Row = { ...fixture.tables[0].rows[0], median: -5 };
    const state: StateCell = {
      ...fixture.states[0],
      rows: [{ ...fixture.states[0].rows[0], median: 120 }],
    };
    const group: HomeGroup = {
      ...fixture.home_groups[0],
      rows: [{ ...fixture.home_groups[0].rows[0], v: -1 }],
    };

    expect(renderRow(row)).toContain("width:0%");
    expect(renderStates([state], { heading: "States" })).toContain("width:100%");
    expect(renderBars([group])).toContain("width:0%");
  });
});

describe("HTML escaping", () => {
  test("esc escapes all five HTML metacharacters", () => {
    expect(esc("& < > \" '")).toBe("&amp; &lt; &gt; &quot; &#39;");
  });

  test.each([undefined, null, true, {}, []])("esc rejects the non-text value %j", (value) => {
    expect(() => esc(value as unknown as string)).toThrowError(TypeError);
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
