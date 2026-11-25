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
  caseLabels,
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
    ).toBe("gdocs comments export vs super editor gdocs single comment");
    expect(caseLabel("04a44a5b5d")).toBe("04a44a5b5d");
  });

  test("a pair of hashed files reads as its two short hashes, never as 'redline'", () => {
    // ndb-v0.0.10's redline sample: 254 of 600 ids are hashes on both sides,
    // and all 254 read "redline" before this.
    const id =
      "0048ba31dd_000be19a055234f8e79ec0baadc41d2a49050b2ea0a60654__vs__5203829c7a_001cc92b88566d5f930fe57f25813c0bf52a7bdc72c217d0_redline_5fee58b86b";
    expect(caseLabel(id)).toBe("0048ba3 vs 5203829");
    expect(
      caseLabel(
        "01d1b3da75_table_bookmark_end__vs__906753e55b_super_editor__table_c70ca973_redline_ba99cf4c8d",
      ),
    ).toBe("table bookmark end vs super editor table");
  });

  test("labels that collide each get the pair's own short hash", () => {
    const a = "1111111111_file_6__vs__2222222222_file_7_redline_aaaaaaa111";
    const b = "3333333333_file_6__vs__4444444444_file_7_redline_bbbbbbb222";
    const c = "5555555555_file_8__vs__6666666666_file_9_redline_ccccccc333";
    const labels = caseLabels([a, b, c]);
    expect(labels.get(a)).toBe("file 6 vs file 7 · aaaaaaa");
    expect(labels.get(b)).toBe("file 6 vs file 7 · bbbbbbb");
    expect(labels.get(c)).toBe("file 8 vs file 9");
    expect(new Set(labels.values()).size).toBe(3);
  });

  test("the list and the table say the group's labels, not the filtered few's", () => {
    const a = {
      case: "1111111111_file_6__vs__2222222222_file_7_redline_aaaaaaa111",
      group: "g",
    } as Case;
    const b = {
      case: "3333333333_file_6__vs__4444444444_file_7_redline_bbbbbbb222",
      group: "g",
    } as Case;
    const labels = caseLabels([a.case, b.case]);
    // The filter shows only `a`; its label still tells it from `b`.
    expect(renderCaseList({ cases: [a], labels })).toContain("file 6 vs file 7 · aaaaaaa");
    expect(renderCaseList({ cases: [a] })).not.toContain("·");
    const table = renderScoresTable({ cases: [a], engines: [], labels });
    expect(table).toContain("file 6 vs file 7 · aaaaaaa");
  });

  test("a suffix never repeats a label: longer hashes, then the id", () => {
    // Same first 7 digits of the run hash (review on #209).
    const a = "1111111111_file__vs__2222222222_edit_redline_abcdef0123";
    const b = "3333333333_file__vs__4444444444_edit_redline_abcdef0456";
    // Even the whole run hash shared.
    const c = "5555555555_x__vs__6666666666_y_redline_0123456789";
    const d = "7777777777_x__vs__8888888888_y_redline_0123456789";
    // A plain label that looks like another's suffixed one.
    const e = "9999999999_file__vs__aaaaaaaaaa_edit_·_abcdef0";
    const labels = caseLabels([a, b, c, d, e]);
    expect(new Set(labels.values()).size).toBe(5);
    expect(labels.get(a)).toBe("file vs edit · abcdef0123");
    expect(labels.get(b)).toBe("file vs edit · abcdef0456");
    expect(labels.get(c)).toBe(`x vs y · ${c}`);
    expect(labels.get(d)).toBe(`x vs y · ${d}`);
    expect(labels.get(e)).toBe("file vs edit · abcdef0");
    // Order-independent.
    expect(caseLabels([e, d, c, b, a])).toEqual(labels);
  });

  test("conversion ids of a state and hashes read apart (ndb-v0.0.10: 267 → 860 of 860)", () => {
    const a = "clean__010cd893de_003c49178daa9062e84e769e1d6ab945d773ead75ca6da68";
    const b = "clean__014f5b166b_0085209e9b3ab0868bc2f0148f1d27f12a95fa9a49727438";
    const c = "clean__0a1b2c3d4e_file_160";
    const labels = caseLabels([a, b, c]);
    expect(labels.get(a)).toBe("clean · 003c491");
    expect(labels.get(b)).toBe("clean · 0085209");
    expect(labels.get(c)).toBe("clean file 160");
  });

  test("the id fallback never repeats another case's label (review on #209)", () => {
    const labels = caseLabels(["file", "_file", "file_·_file"]);
    expect(new Set(labels.values()).size).toBe(3);
  });

  test("a hostile case id is escaped in the list and the table (review on #209)", () => {
    const evil = {
      case: '<img src=x onerror=alert(1)>__vs__"><script>x</script>',
      group: "g",
    } as Case;
    for (const html of [
      renderCaseList({ cases: [evil] }),
      renderScoresTable({ cases: [evil], engines: [] }),
    ]) {
      expect(html).not.toMatch(/<img|<script/);
      expect(html).toContain("&lt;img");
    }
  });

  test("an empty side of a pair is dropped", () => {
    expect(caseLabel("left_doc__vs__")).toBe("left doc");
    expect(caseLabel("__vs__right_doc")).toBe("right doc");
  });

  test("the case column sorts by the label a reader sees; the id breaks ties only", () => {
    const short = { case: "9999999999_file", group: "g" } as Case;
    const long = { case: "1111111111_file2", group: "g" } as Case;
    const html = renderScoresTable({ cases: [long, short], engines: [], sort: { col: 0, dir: 1 } });
    expect(html.indexOf(">file<")).toBeLessThan(html.indexOf(">file2<"));
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
    // aria-sort sits on the sorted head only (WAI-ARIA 1.2), never "none" elsewhere.
    expect(table).toContain('data-c="1" tabindex="0" class="">group</th>');
    expect(table.match(/aria-sort=/g)?.length).toBe(1);
    // A sort column a filter removed falls back to the case column, and says so.
    const gone = renderScoresTable({ cases: [a], engines: [], sort: { col: 42, dir: -1 } });
    expect(gone).toContain('data-c="0" tabindex="0" aria-sort="descending"');
    expect(table).toContain('tr data-case="aaaaaaaaaa_one"');
    expect(table).toMatch(/<tr data-case="aaaaaaaaaa_one" data-key="[^"]+" tabindex="0">/);
    expect(table).toContain('<td class=" case-name" title="aaaaaaaaaa_one">one</td>');
    expect(table).toContain("bold green = best");
  });

  test("the case column sorts by the label it shows, the id breaking a tie", () => {
    const zulu = { case: "aaaaaaaaaa_Zulu_file", group: "g" } as Case;
    const alpha = { case: "bbbbbbbbbb_Alpha_file", group: "g" } as Case;
    const table = renderScoresTable({
      cases: [zulu, alpha],
      engines: [],
      sort: { col: 0, dir: 1 },
    });
    expect(table.indexOf(">Alpha file<")).toBeLessThan(table.indexOf(">Zulu file<"));
  });

  test("a filter that hides the open case leaves the list one Tab stop", () => {
    const a = { case: "aaaaaaaaaa_one", group: "g" } as Case;
    const b = { case: "bbbbbbbbbb_two", group: "g" } as Case;
    const list = renderCaseList({ cases: [a, b], selected: "zzzz_gone" });
    expect(list.match(/tabindex="0"/g)?.length).toBe(1);
    expect(list.indexOf('tabindex="0"')).toBeLessThan(list.indexOf("bbbbbbbbbb_two"));
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

describe("targets", () => {
  test("the brand bar's links are 24px tall at least (WCAG 2.2 2.5.8)", () => {
    expect(casesCss).toMatch(/#brand \.links a\s*\{[^}]*min-height:\s*24px/);
  });
});
