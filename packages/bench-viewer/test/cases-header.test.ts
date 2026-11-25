// Arthur, 2026-11-03: the case browsers' header. (1) no "pages 1–N of N";
// (2) an "all groups" choice; (3) the bar breaks before overlay on both
// browsers; (4) the scores-table toggle and the bench links sit beside the
// "About these scores · N notes" summary, not inside it (a summary holds no
// other controls), the toggle before the DOCX → PDF link.
import { readFile } from "node:fs/promises";
import { describe, expect, test } from "vitest";
import type { Case, ShardRef } from "../src/cases.ts";
import {
  ALL_GROUPS,
  caseKey,
  caseLabel,
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
  html.slice(html.indexOf('<div id="bar"'), html.indexOf('<div id="engines"'));

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

  test("(4) the scores-table toggle and the links sit beside the About summary", () => {
    for (const kind of ["conversion", "redline"] as const) {
      expect(bar(page(kind))).not.toContain('id="viewToggle"');
      const legend = renderCasesLegend({ kind });
      const summary = legend.slice(legend.indexOf("<summary>"), legend.indexOf("</summary>"));
      expect(summary, kind).toContain(" notes</span>");
      expect(summary, kind).not.toMatch(/<(button|a)\b/);
      const toggle = legend.indexOf('id="viewToggle"');
      expect(toggle, kind).toBeGreaterThan(-1);
      expect(toggle, kind).toBeLessThan(legend.indexOf(">DOCX → PDF</a>"));
      expect(legend.match(/id="viewToggle"/g)?.length).toBe(1);
    }
  });

  test("(6) a link left undefined keeps its default", () => {
    const legend = renderCasesLegend({ kind: "redline", links: { speed: undefined } });
    expect(legend).toContain('<a href="../speed/index.html">Speed</a>');
  });

  test("(7) the inline script carries URLs as JS strings, not HTML-escaped", () => {
    const html = renderCasesPage({
      kind: "redline",
      indexUrl: "i.json?case=3&group=win",
      moduleUrl: "m.js?v=1&x=2",
    });
    const script = html.slice(html.indexOf('<script type="module">'), html.indexOf("</script>"));
    expect(script).toContain('indexUrl: "i.json?case=3&group=win"');
    expect(script).toContain('from "m.js?v=1&x=2"');
    expect(script).not.toContain("&amp;");
    const hostile = renderCasesPage({
      kind: "redline",
      indexUrl: "</script><b>",
      moduleUrl: "m.js",
    });
    expect(hostile.match(/<\/script>/g)?.length).toBe(1);
  });

  test("(8) the About disclosure comes before its actions in the DOM", () => {
    const legend = renderCasesLegend({ kind: "conversion" });
    expect(legend.indexOf('<details class="about"')).toBeLessThan(
      legend.indexOf('class="about-acts"'),
    );
  });

  test("(5) the About links go where the page says", () => {
    const legend = renderCasesLegend({
      kind: "redline",
      links: { conversion: "/use-cases/convert", redlines: "/use-cases" },
    });
    expect(legend).toContain('<a href="/use-cases/convert">DOCX → PDF</a>');
    expect(legend).toContain('<a href="/use-cases">Redlines</a>');
    expect(legend).toContain('<a href="../speed/index.html">Speed</a>');
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
    expect(list).toContain(
      `class="case sel" role="option" aria-selected="true" tabindex="0" data-case="04a44a5b5d" data-key="${caseKey(b)}"`,
    );
    const table = renderScoresTable({ cases: [a, b], engines: [], selected: caseKey(a) });
    expect(table.match(/class="sel"/g)?.length).toBe(1);
    expect(table).toContain(`data-key="${caseKey(a)}" tabindex="0" class="sel"`);
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

describe("polish round: cases a reader can name and a keyboard can reach", () => {
  test("a case id reads without its hashes, a redline pair as 'vs'", () => {
    expect(caseLabel("d435c8d66c_file_104__vs__9e1f2a3b4c_file_104_edited")).toBe(
      "file 104 vs file 104 edited",
    );
    expect(
      caseLabel(
        "a0738533be_gdocs_comments_export__vs__d5a56cdeb3_super_editor__gdocs_single_comment_ac5db87f_redline_745218f254",
      ),
    ).toBe("gdocs comments export vs super editor gdocs single comment redline");
    expect(caseLabel("04a44a5b5d")).toBe("04a44a5b5d");
  });

  test("the case list is a listbox whose selected option takes the focus", () => {
    const a = { case: "aaaaaaaaaa_one", group: "g" } as Case;
    const b = { case: "bbbbbbbbbb_two", group: "g" } as Case;
    const list = renderCaseList({ cases: [a, b], selected: caseKey(b) });
    expect(list.match(/role="option"/g)?.length).toBe(2);
    expect(list).toContain('aria-selected="false" tabindex="-1"');
    expect(list).toContain('aria-selected="true" tabindex="0"');
    expect(list).toContain('title="bbbbbbbbbb_two">two</span>');
    expect(page("redline")).toContain('<div id="list" role="listbox" aria-label="Cases">');
  });

  test("the scores table's heads and rows are reachable, and sorting is announced", () => {
    const a = { case: "aaaaaaaaaa_one", group: "g" } as Case;
    const table = renderScoresTable({ cases: [a], engines: [], sort: { col: 0, dir: 1 } });
    expect(table).toContain('data-c="0" tabindex="0" aria-sort="ascending"');
    expect(table).toContain('data-c="1" tabindex="0" aria-sort="none"');
    expect(table).toContain('tr data-case="aaaaaaaaaa_one"');
    expect(table).toMatch(/<tr data-case="aaaaaaaaaa_one" data-key="[^"]+" tabindex="0">/);
    expect(table).toContain('<td class=" case-name" title="aaaaaaaaaa_one">one</td>');
    expect(table).toContain("bold green = best");
  });

  test("the shortcut legend is on the page, and ? hides it", () => {
    const html = page("redline");
    expect(html).toContain('<span id="keys">');
    expect(html).toContain("<kbd>?</kbd> hide these");
    expect(casesCss).toContain("body.nokeys #keys");
  });

  test("the overlay's pickers hide while the overlay is off", () => {
    expect(page("redline")).toContain('<span class="ovl-under"> under </span>');
    expect(casesCss).toContain("#bar .grp:has(#ovl:not(:checked))");
  });
});
