// @vitest-environment happy-dom
// The keyboard paths of the polish round, on the page's own markup and wiring
// in a real DOM (happy-dom): what opens, where the focus lands, what the
// overlay checkbox says, and which keys a field keeps for itself.
import { afterEach, beforeEach, describe, expect, test } from "vitest";
import { mountCasesPage, renderCasesPage } from "../src/cases.ts";

const names = ["one", "two", "three"];
const index = {
  version: "1",
  generated: "2026-11-02T22:56:57.713469Z",
  repo: "https://github.com/jandira-tech/neurotic_docx_bench",
  assets_base: "https://example.invalid/",
  engines: [
    { key: "jubarte", label: "jubarte" },
    { key: "reference", label: "Word" },
  ],
  groups: [
    { kind: "conversion", group: "v1/clean", count: 3, path: "cases/conversion/v1--clean.json" },
  ],
};
const shard = {
  kind: "conversion",
  group: "v1/clean",
  cases: names.map((name, i) => ({
    kind: "conversion",
    group: "v1/clean",
    case: `${"abcdef0123".slice(0, 10)}${i}_${name}`,
    pages: {
      reference: [`~/cases/${name}/reference/page_001.webp`],
      jubarte: [`~/cases/${name}/jubarte/page_001.webp`],
    },
    page_counts: { reference: 1, jubarte: 1 },
    scores: { reference: { pixel: 100 }, jubarte: { pixel: 90 - i } },
    times: { reference: 1, jubarte: 2 },
    versions: { reference: "Word 16.115", jubarte: "jubarte 0.14.0" },
    dropped: [],
    reference_app: "Microsoft Word",
  })),
};

const key = (target: Element, k: string) => {
  const event = new KeyboardEvent("keydown", { key: k, bubbles: true, cancelable: true });
  target.dispatchEvent(event);
  return event;
};
const $ = <T extends Element = HTMLElement>(selector: string) =>
  document.querySelector<T>(selector) as T;
const realFetch = globalThis.fetch;

beforeEach(async () => {
  localStorage.clear();
  const html = renderCasesPage({ kind: "conversion", indexUrl: "index.json", moduleUrl: "m.js" });
  document.body.innerHTML = html.slice(
    html.indexOf("<body") + html.slice(html.indexOf("<body")).indexOf(">") + 1,
    html.indexOf("</body>"),
  );
  document.body.className = "";
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    const body = String(input).includes("index.json") ? index : shard;
    return { ok: true, status: 200, statusText: "OK", json: async () => body } as Response;
  }) as typeof fetch;
  await mountCasesPage({
    kind: "conversion",
    indexUrl: "index.json",
    root: document,
    random: () => 0,
  });
});
afterEach(() => {
  globalThis.fetch = realFetch;
});

describe("the keyboard on the real page", () => {
  test("Enter on a focused option opens that case and the focus stays on its option", () => {
    const second = document.querySelectorAll<HTMLElement>("#list .case")[1];
    second.focus();
    key(second, "Enter");
    expect($("#navCase").textContent).toBe("two");
    const active = document.activeElement as HTMLElement;
    expect(active.classList.contains("sel")).toBe(true);
    expect(active.getAttribute("aria-selected")).toBe("true");
    expect(active.dataset.case).toBe(shard.cases[1].case);
    expect(document.querySelectorAll('#list [tabindex="0"]').length).toBe(1);
  });

  test("Enter on a scores row opens the case and moves the focus out of the hidden table", () => {
    key(document.body, "t");
    expect($("#scores").classList.contains("hidden")).toBe(false);
    const row = document.querySelectorAll<HTMLElement>("#scores tr[data-key]")[2];
    row.focus();
    key(row, "Enter");
    expect($("#scores").classList.contains("hidden")).toBe(true);
    const active = document.activeElement as HTMLElement;
    expect($("#scores").contains(active)).toBe(false);
    expect(active.dataset.key).toBe(row.dataset.key);
  });

  test("Enter on a column head sorts and keeps the focus on that head", () => {
    key(document.body, "t");
    const head = $('#scores th[data-c="0"]');
    head.focus();
    key(head, "Enter");
    const again = document.activeElement as HTMLElement;
    expect(again.dataset.c).toBe("0");
    expect(again.getAttribute("aria-sort")).not.toBeNull();
    expect(document.querySelectorAll("#scores [aria-sort]").length).toBe(1);
  });

  test("the o key turns the overlay on and the checkbox says so", () => {
    const box = $<HTMLInputElement>("#ovl");
    expect(box.checked).toBe(false);
    key(document.body, "o");
    expect(box.checked).toBe(true);
    key(document.body, "o");
    expect(box.checked).toBe(false);
  });

  test("? hides the legend without a re-render: the focus stays on the checkbox", () => {
    const box = $<HTMLInputElement>("#engines input[type=checkbox]");
    box.focus();
    key(box, "?");
    expect(document.body.classList.contains("nokeys")).toBe(true);
    expect(document.activeElement).toBe(box);
    key(box, "?");
    expect(document.body.classList.contains("nokeys")).toBe(false);
  });

  test("a field that takes text keeps ? and the shortcut letters", () => {
    for (const type of ["password", "email", "search"]) {
      const field = document.createElement("input");
      field.type = type;
      document.body.append(field);
      field.focus();
      for (const k of ["?", "o", "t"])
        expect(key(field, k).defaultPrevented, `${type} ${k}`).toBe(false);
      field.remove();
    }
    expect(document.body.classList.contains("nokeys")).toBe(false);
    expect($<HTMLInputElement>("#ovl").checked).toBe(false);
  });

  test("the label search finds a case by the name it shows", () => {
    const filter = $<HTMLInputElement>("#filter");
    filter.value = "three";
    filter.dispatchEvent(new Event("input", { bubbles: true }));
    expect(document.querySelectorAll("#list .case").length).toBe(1);
    // the open case is filtered out: the one shown still takes the Tab stop
    expect(document.querySelectorAll('#list [tabindex="0"]').length).toBe(1);
  });
});
