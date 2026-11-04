// Arthur, 2026-11-03: the case browsers' header. (1) no "pages 1–N of N";
// (2) an "all groups" choice; (3) the bar breaks before overlay on both
// browsers; (4) the scores-table toggle sits after "About these scores · N
// notes", before the DOCX → PDF link.
import { readFile } from "node:fs/promises";
import { describe, expect, test } from "vitest";
import type { Case, ShardRef } from "../src/cases.ts";
import {
  ALL_GROUPS,
  caseKey,
  renderCaseList,
  renderCasesLegend,
  renderCasesPage,
  renderGroupOptions,
  renderScoresTable,
} from "../src/cases.ts";

const casesCss = await readFile(new URL("../themes/cases.css", import.meta.url), "utf8");
const page = (kind: "conversion" | "redline") =>
  renderCasesPage({ kind, indexUrl: "i.json", moduleUrl: "m.js" });
const bar = (html: string) =>
  html.slice(html.indexOf('<div id="bar">'), html.indexOf('<div id="engines"'));

describe("the header", () => {
  test("(1) carries no page count", () => {
    for (const kind of ["conversion", "redline"] as const) {
      expect(page(kind)).not.toContain('id="pageinfo"');
    }
  });

  test("(3) breaks before overlay on both browsers", () => {
    for (const kind of ["conversion", "redline"] as const) {
      const b = bar(page(kind));
      const brk = b.indexOf('class="brk"');
      expect(brk, kind).toBeGreaterThan(b.indexOf('id="zoom"'));
      expect(brk, kind).toBeLessThan(b.indexOf('id="ovl"'));
    }
    expect(casesCss).toMatch(/#bar \.brk\s*\{[^}]*flex-basis:\s*100%/);
  });

  test("(4) the scores-table toggle sits after the notes count, before the DOCX → PDF link", () => {
    for (const kind of ["conversion", "redline"] as const) {
      expect(bar(page(kind))).not.toContain('id="viewToggle"');
      const legend = renderCasesLegend({ kind });
      const toggle = legend.indexOf('id="viewToggle"');
      expect(toggle, kind).toBeGreaterThan(legend.indexOf(" notes</span>"));
      expect(toggle, kind).toBeLessThan(legend.indexOf(">DOCX → PDF</a>"));
      expect(legend.match(/id="viewToggle"/g)?.length).toBe(1);
    }
  });
});

describe("(2) all groups", () => {
  const groups: ShardRef[] = [
    { kind: "conversion", group: "corpus/clean", count: 3, path: "a.json" },
    { kind: "conversion", group: "v1/clean", count: 4, path: "b.json" },
  ];

  test("the picker opens with an all-groups choice counting every case", () => {
    const html = renderGroupOptions(groups, ALL_GROUPS);
    expect(html.startsWith(`<option value="${ALL_GROUPS}" selected>all groups (7)</option>`)).toBe(
      true,
    );
    expect(renderGroupOptions(groups, "v1/clean")).toContain(
      `<option value="${ALL_GROUPS}">all groups (7)</option>`,
    );
  });

  test("a case id two groups share selects only the group's own row", () => {
    const a = { case: "04a44a5b5d", group: "corpus/clean" } as Case;
    const b = { case: "04a44a5b5d", group: "v1/clean" } as Case;
    const list = renderCaseList({ cases: [a, b], selected: caseKey(b) });
    expect(list.match(/class="case sel"/g)?.length).toBe(1);
    expect(list).toContain(`class="case sel" data-case="04a44a5b5d" data-key="${caseKey(b)}"`);
    const table = renderScoresTable({ cases: [a, b], engines: [], selected: caseKey(a) });
    expect(table.match(/class="sel"/g)?.length).toBe(1);
    expect(table).toContain(`data-key="${caseKey(a)}" class="sel"`);
  });
});

describe("the shown pages keep their shape", () => {
  // The <img> carries width="1020" height="1320" (space reserved before it
  // loads); CSS narrows the width to the zoom, so without height:auto the
  // attribute height stays and the page is stretched (Arthur, 2026-11-03:
  // "the documents are squeshed").
  test.each([".page img", "#overlay img"])("%s sets height: auto", (selector) => {
    const escaped = selector.replace(/[.#]/g, (m) => `\\${m}`);
    expect(casesCss).toMatch(new RegExp(`(^|\\n)${escaped}\\s*\\{[^}]*height:\\s*auto`));
  });
});
