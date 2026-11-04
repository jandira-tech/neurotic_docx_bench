/**
 * Plan 7.5 (issue #132): the case browsers gain what only jubarte.pro has —
 * per-page scores, links to the case's files on Hugging Face, up to 12
 * pages — and the old gh-pages viewer's random case on open.
 *
 * The tests drive the render layer (data in, HTML out) and the wiring
 * through a small fake document, so no browser is needed.
 */

import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it, test } from "vitest";
import type { Case, CasesIndex, Engine } from "../src/cases.ts";
import {
  applyInlineCss,
  caseFilesUrl,
  formatPageScore,
  lanesForCase,
  mountCasesPage,
  PAGE_STEP,
  PRELOAD_STEP,
  parseCase,
  parseCaseShard,
  parseCasesIndex,
  pickRandomCase,
  randomIndex,
  renderCaseGrid,
  renderCaseHead,
  renderCaseList,
  renderCaseStrip,
  renderEngineToggles,
  renderOverlay,
  renderScoresTable,
  resolveFileUrl,
  safeFileUrl,
} from "../src/cases.ts";

const fixtureRoot = fileURLToPath(new URL("./fixtures/release/", import.meta.url));

async function readJson(path: string): Promise<unknown> {
  return JSON.parse(await readFile(path, "utf8"));
}

const index: CasesIndex = parseCasesIndex(await readJson(join(fixtureRoot, "cases", "index.json")));
const conversion = parseCaseShard(
  await readJson(join(fixtureRoot, "cases", "conversion", "v1--with_comments_clean.json")),
);
const engines: Engine[] = index.engines;

/** The Hugging Face base the case's files live under. */
const FILES_BASE = "https://huggingface.co/datasets/arthrod/neurotic_docx_bench/resolve/main/";

/** A case with per-page scores and per-lane files (plan 7's fields). */
function scoredCase(): Case {
  return {
    ...conversion.cases[0],
    page_scores: {
      reference: [100, 95.25],
      docxodus: [34.5, null],
    },
    files: {
      reference: "~/cases/04a44a5b5d/reference/word.pdf",
      docxodus: "~/cases/04a44a5b5d/docxodus/docxodus.pdf",
    },
  };
}

/** A seeded RNG (mulberry32): the same seed always draws the same number. */
function seeded(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ---- the fake document -----------------------------------------------------------------

interface FakeStyle {
  setProperty(name: string, value: string): void;
  [key: string]: unknown;
}

class FakeClassList {
  private readonly names = new Set<string>();

  toggle(name: string, force?: boolean): boolean {
    const on = force ?? !this.names.has(name);
    if (on) this.names.add(name);
    else this.names.delete(name);
    return on;
  }

  add(name: string): void {
    this.names.add(name);
  }

  remove(name: string): void {
    this.names.delete(name);
  }

  contains(name: string): boolean {
    return this.names.has(name);
  }
}

class FakeElement {
  innerHTML = "";
  textContent = "";
  value = "";
  checked = false;
  title = "";
  scrollTop = 0;
  offsetHeight = 0;
  clientHeight = 0;
  dataset: Record<string, string> = {};
  style: FakeStyle = { setProperty: () => undefined };
  classList = new FakeClassList();
  readonly attributes = new Map<string, string>();
  private readonly listeners = new Map<string, ((event: unknown) => void)[]>();

  addEventListener(type: string, fn: (event: unknown) => void): void {
    const list = this.listeners.get(type) ?? [];
    list.push(fn);
    this.listeners.set(type, list);
  }

  /** Fire the listeners of one event type (the wiring's own handlers). */
  dispatch(type: string, event: unknown = { target: null }): void {
    for (const fn of this.listeners.get(type) ?? []) fn(event);
  }

  setAttribute(name: string, value: string): void {
    this.attributes.set(name, value);
  }

  getAttribute(name: string): string | null {
    return this.attributes.get(name) ?? null;
  }

  querySelector(): null {
    return null;
  }

  querySelectorAll(): FakeElement[] {
    return [];
  }

  getBoundingClientRect(): { top: number } {
    return { top: 0 };
  }
}

class FakeDocument {
  readonly body = new FakeElement();
  readonly elements = new Map<string, FakeElement>();
  readonly defaultView = {
    location: { hash: "", search: "", href: "http://localhost/cases/index.html" },
    history: { replaceState: () => undefined },
    matchMedia: () => ({ matches: false }),
    addEventListener: () => undefined,
  };

  constructor(hash = "") {
    this.defaultView.location.hash = hash;
  }

  querySelector<T>(selector: string): T | null {
    let element = this.elements.get(selector);
    if (!element) {
      element = new FakeElement();
      this.elements.set(selector, element);
    }
    return element as unknown as T;
  }

  querySelectorAll(): FakeElement[] {
    return [];
  }

  addEventListener(): void {
    /* the wiring's keyboard handler needs no document */
  }

  element(selector: string): FakeElement {
    return this.querySelector<FakeElement>(selector) as FakeElement;
  }
}

/** The id of the case the list marks as selected. */
function selectedCaseId(html: string): string | undefined {
  return /class="case sel" data-case="([^"]*)"/.exec(html)?.[1];
}

/** The number of pages one lane's column drew. */
function pagesPerColumn(html: string): number {
  const first = html.split('<div class="col"')[1] ?? "";
  return [...first.matchAll(/<img /g)].length;
}

/** Serve an index and a shard to the wiring, and mount the page. */
async function mountPage(options: {
  hash?: string;
  random?: () => number;
  index?: unknown;
  shard?: unknown;
}): Promise<FakeDocument> {
  const doc = new FakeDocument(options.hash ?? "");
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    const url = String(input);
    const body = url.includes("index.json") ? options.index : options.shard;
    return {
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => body,
    } as Response;
  }) as typeof fetch;
  try {
    await mountCasesPage({
      kind: "conversion",
      indexUrl: "../release/cases/index.json",
      root: doc as unknown as Document,
      ...(options.random ? { random: options.random } : {}),
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
  return doc;
}

/** An index and a shard with `count` cases of `pages` pages each. */
function caseBundle(pages: number, count = 3): { index: unknown; shard: unknown } {
  const names = ["one", "two", "three", "four", "five"];
  const cases: Case[] = names.slice(0, count).map((name, caseIndex) => {
    const pagePaths = Array.from(
      { length: pages },
      (_, i) => `~/cases/${name}/reference/page_${String(i + 1).padStart(3, "0")}.webp`,
    );
    return {
      kind: "conversion",
      group: "v1/clean",
      case: name,
      pages: { reference: pagePaths, jubarte: pagePaths },
      page_counts: { reference: pages, jubarte: pages },
      scores: { reference: { pixel: 100 }, jubarte: { pixel: 90 - caseIndex } },
      times: { reference: 1, jubarte: 2 },
      versions: { reference: "Word 16.115", jubarte: "jubarte 0.14.0" },
      dropped: [],
      reference_app: "Microsoft Word",
    };
  });
  return {
    index: {
      version: "1",
      generated: "2026-11-02T22:56:57.713469Z",
      repo: "https://github.com/jandira-tech/neurotic_docx_bench",
      assets_base: "https://example.invalid/",
      engines: [
        { key: "jubarte", label: "jubarte" },
        { key: "reference", label: "Word" },
      ],
      groups: [
        {
          kind: "conversion",
          group: "v1/clean",
          count: cases.length,
          path: "cases/conversion/v1--clean.json",
        },
      ],
    },
    shard: { kind: "conversion", group: "v1/clean", cases },
  };
}

// ---- the contract ----------------------------------------------------------------------

describe("the new contract fields", () => {
  test("the index reads the files base", () => {
    const parsed = parseCasesIndex({
      ...index,
      files_base: FILES_BASE,
    });
    expect(parsed.files_base).toBe(FILES_BASE);
  });

  test("an index without a files base has none", () => {
    expect(index.files_base).toBeUndefined();
  });

  test("the index refuses a files base that is not an https URL ending in /", () => {
    expect(() => parseCasesIndex({ ...index, files_base: "http://example.com/x" })).toThrow(
      /files_base/,
    );
    expect(() => parseCasesIndex({ ...index, files_base: "https://example.com/x" })).toThrow(
      /files_base/,
    );
    expect(() => parseCasesIndex({ ...index, files_base: "https://example.com/" })).not.toThrow();
  });

  test("a case reads its page scores and its files", () => {
    const parsed = parseCase(
      {
        kind: "conversion",
        group: "v1/clean",
        case: "one",
        pages: {},
        page_counts: {},
        scores: {},
        times: {},
        versions: {},
        dropped: [],
        reference_app: "Microsoft Word",
        page_scores: { jubarte: [12.5, null] },
        files: { jubarte: "~/cases/one/jubarte/output.pdf" },
      },
      "case",
    );
    expect(parsed.page_scores?.jubarte).toEqual([12.5, null]);
    expect(parsed.files?.jubarte).toBe("~/cases/one/jubarte/output.pdf");
  });

  test("a case without the new fields has neither", () => {
    const parsed = parseCase(
      {
        kind: "conversion",
        group: "v1/clean",
        case: "one",
        pages: {},
        page_counts: {},
        scores: {},
        times: {},
        versions: {},
        dropped: [],
        reference_app: "Microsoft Word",
      },
      "case",
    );
    expect(parsed.page_scores).toBeUndefined();
    expect(parsed.files).toBeUndefined();
  });

  test("a page score that is not a number is refused", () => {
    expect(() =>
      parseCase(
        {
          kind: "conversion",
          group: "v1/clean",
          case: "one",
          pages: {},
          page_counts: {},
          scores: {},
          times: {},
          versions: {},
          dropped: [],
          reference_app: "Microsoft Word",
          page_scores: { jubarte: ["12.5"] },
        },
        "case",
      ),
    ).toThrow(/page_scores/);
  });
});

// ---- feature 1: the per-page scores -----------------------------------------------------

describe("the per-page scores", () => {
  test("each shown page carries its own score", () => {
    const html = renderCaseStrip({
      case: scoredCase(),
      engine: { key: "docxodus", label: "docxodus" },
      assetsBase: index.assets_base,
    });
    expect(html).toContain('<div class="page-score" title="Page 1 score (0–100)">34.5</div>');
    expect(pagesPerColumn(html)).toBe(2);
  });

  test("an unscored page says so with a dash", () => {
    const html = renderCaseStrip({
      case: scoredCase(),
      engine: { key: "docxodus", label: "docxodus" },
      assetsBase: index.assets_base,
    });
    expect(html).toContain('<div class="page-score" title="Page 2 was not scored">—</div>');
  });

  test("a score is one decimal", () => {
    expect(formatPageScore(95.25)).toBe("95.3");
    expect(formatPageScore(100)).toBe("100.0");
    expect(formatPageScore(0)).toBe("0.0");
    expect(formatPageScore(null)).toBe("—");
    expect(formatPageScore(undefined)).toBe("—");
  });

  test("a case without page scores draws no score at all", () => {
    const html = renderCaseStrip({
      case: conversion.cases[0],
      engine: { key: "docxodus", label: "docxodus" },
      assetsBase: index.assets_base,
    });
    expect(html).not.toContain("page-score");
  });

  test("a lane without page scores draws none while its neighbour has them", () => {
    const html = renderCaseStrip({
      case: scoredCase(),
      engine: { key: "jubarte", label: "jubarte" },
      assetsBase: index.assets_base,
    });
    expect(html).not.toContain("page-score");
  });

  test("a page with no image has no score", () => {
    const c: Case = {
      ...scoredCase(),
      pages: { docxodus: ["~/a/page_001.webp", null] },
      page_scores: { docxodus: [34.5, null] },
    };
    const html = renderCaseStrip({
      case: c,
      engine: { key: "docxodus", label: "docxodus" },
      assetsBase: index.assets_base,
    });
    expect(html).toContain("no page 2");
    // Only the page that is there carries a score.
    expect([...html.matchAll(/class="page-score"/g)].length).toBe(1);
  });

  test("the overlay shows the score of the lane over Word", () => {
    const html = renderOverlay({
      case: scoredCase(),
      under: { key: "reference", label: "Word" },
      over: { key: "docxodus", label: "docxodus" },
      assetsBase: index.assets_base,
    });
    expect(html).toContain('<div class="page-score" title="Page 1 score (0–100)">34.5</div>');
    expect(html).toContain('<div class="page-score" title="Page 2 was not scored">—</div>');
  });
});

// ---- feature 2: the file links ---------------------------------------------------------

describe("the file links", () => {
  test("a file path resolves against the files base", () => {
    expect(resolveFileUrl(FILES_BASE, "~/cases/one/jubarte/output.pdf")).toBe(
      `${FILES_BASE}cases/one/jubarte/output.pdf`,
    );
    expect(safeFileUrl(FILES_BASE, "~/cases/one/jubarte/output.pdf")).toBe(
      `${FILES_BASE}cases/one/jubarte/output.pdf`,
    );
  });

  test("a path that is not relative to the base is refused", () => {
    expect(safeFileUrl(FILES_BASE, "https://evil.example/x")).toBe("");
    expect(safeFileUrl(FILES_BASE, "javascript:alert(1)")).toBe("");
    expect(safeFileUrl(FILES_BASE, "../escape")).toBe("");
  });

  test("a lane with a file gets a files link", () => {
    const html = renderCaseHead({
      case: scoredCase(),
      engine: { key: "docxodus", label: "docxodus" },
      assetsBase: index.assets_base,
      engines,
      filesBase: FILES_BASE,
    });
    expect(html).toContain(
      `<a class="files" href="${FILES_BASE}cases/04a44a5b5d/docxodus/docxodus.pdf" target="_blank" rel="noopener" title="The case's files on Hugging Face">files ↗</a>`,
    );
  });

  test("a lane without a file gets no link", () => {
    const html = renderCaseHead({
      case: scoredCase(),
      engine: { key: "jubarte", label: "jubarte" },
      assetsBase: index.assets_base,
      engines,
      filesBase: FILES_BASE,
    });
    expect(html).not.toContain("files ↗");
  });

  test("no files base, no link", () => {
    const html = renderCaseHead({
      case: scoredCase(),
      engine: { key: "docxodus", label: "docxodus" },
      assetsBase: index.assets_base,
      engines,
    });
    expect(html).not.toContain("files ↗");
  });

  test("the case gets one link to its files on Hugging Face", () => {
    const lanes = [
      { engine: { key: "reference", label: "Word" }, state: "measured" as const },
      { engine: { key: "docxodus", label: "docxodus" }, state: "measured" as const },
    ];
    const html = renderCaseGrid({
      case: scoredCase(),
      lanes,
      assetsBase: index.assets_base,
      engines,
      filesBase: FILES_BASE,
    });
    expect(html).toContain("files on Hugging Face ↗");
    expect(html).toContain(`href="${FILES_BASE}cases/04a44a5b5d/"`);
    expect(html).toContain('rel="noopener"');
    expect(html).toContain('target="_blank"');
  });

  test("a case without files gets no case-level link", () => {
    const lanes = [{ engine: { key: "reference", label: "Word" }, state: "measured" as const }];
    const html = renderCaseGrid({
      case: conversion.cases[0],
      lanes,
      assetsBase: index.assets_base,
      engines,
      filesBase: FILES_BASE,
    });
    expect(html).not.toContain("files on Hugging Face");
  });

  test("the case folder is the folder the lanes' files share", () => {
    expect(caseFilesUrl(FILES_BASE, scoredCase())).toBe(`${FILES_BASE}cases/04a44a5b5d/`);
    expect(caseFilesUrl(FILES_BASE, conversion.cases[0])).toBe("");
    expect(caseFilesUrl(undefined, scoredCase())).toBe("");
  });

  test("a hostile file path cannot break out of the href", () => {
    const hostile: Case = {
      ...scoredCase(),
      files: { docxodus: '~/x" onmouseover="alert(1)' },
    };
    const html = renderCaseHead({
      case: hostile,
      engine: { key: "docxodus", label: "docxodus" },
      assetsBase: index.assets_base,
      engines,
      filesBase: FILES_BASE,
    });
    expect(html).not.toContain('onmouseover="alert(1)"');
    expect(html).toContain("x%22%20onmouseover%3D%22alert(1)");
  });

  test("a hostile lane name is escaped in the link", () => {
    const hostile: Case = {
      ...scoredCase(),
      files: { '<script>alert("lane")</script>': "~/cases/one/x.pdf" },
    };
    const html = renderCaseHead({
      case: hostile,
      engine: { key: '<script>alert("lane")</script>', label: "evil" },
      assetsBase: index.assets_base,
      engines,
      filesBase: FILES_BASE,
    });
    expect(html).not.toContain("<script>");
  });
});

// ---- feature 3: up to 12 pages ---------------------------------------------------------

describe("up to 12 pages", () => {
  test("the page step is 12", () => {
    expect(PAGE_STEP).toBe(12);
  });

  test("the strip draws every shown page, not three", () => {
    const many: Case = {
      ...conversion.cases[0],
      pages: {
        reference: Array.from(
          { length: 12 },
          (_, i) => `~/cases/one/reference/page_${String(i + 1).padStart(3, "0")}.webp`,
        ),
      },
    };
    const html = renderCaseStrip({
      case: many,
      engine: { key: "reference", label: "Word" },
      assetsBase: index.assets_base,
    });
    expect(pagesPerColumn(html)).toBe(12);
  });

  test("the page opens on twelve pages and the more button grows it", async () => {
    const bundle = caseBundle(20);
    const doc = await mountPage({ index: bundle.index, shard: bundle.shard });
    expect(pagesPerColumn(doc.element("#grid").innerHTML)).toBe(12);
    const more = doc.element("#more");
    expect(more.textContent).toBe("more pages (8 left)");
    more.dispatch("click");
    expect(pagesPerColumn(doc.element("#grid").innerHTML)).toBe(20);
  });
});

// ---- feature 4: the random case on open ------------------------------------------------

describe("the random case on open", () => {
  test("a seeded draw picks the same case every time", () => {
    const cases = [{ id: "a" }, { id: "b" }, { id: "c" }];
    expect(pickRandomCase(cases, seeded(11))?.id).toBe("b");
    expect(pickRandomCase(cases, seeded(11))?.id).toBe(pickRandomCase(cases, seeded(11))?.id);
  });

  test("a draw lands inside the list", () => {
    expect(randomIndex(4, seeded(11))).toBe(2);
    expect(randomIndex(0, seeded(11))).toBe(-1);
    expect(pickRandomCase([], seeded(11))).toBeUndefined();
  });

  test("the page opens on a random case when the URL names none", async () => {
    const bundle = caseBundle(3);
    const doc = await mountPage({
      index: bundle.index,
      shard: bundle.shard,
      random: seeded(11),
    });
    expect(selectedCaseId(doc.element("#list").innerHTML)).toBe("two");
  });

  test("the random draw is the one the seed makes", async () => {
    const bundle = caseBundle(3);
    const rng = seeded(11);
    let drawn = 0;
    const doc = await mountPage({
      index: bundle.index,
      shard: bundle.shard,
      random: () => {
        drawn += 1;
        return rng();
      },
    });
    expect(drawn).toBeGreaterThan(0);
    expect(selectedCaseId(doc.element("#list").innerHTML)).toBe("two");
  });

  test("a URL that names a case opens that case and draws nothing random", async () => {
    const bundle = caseBundle(3);
    let drawn = 0;
    const doc = await mountPage({
      hash: "#v1%2Fclean/one",
      index: bundle.index,
      shard: bundle.shard,
      random: () => {
        drawn += 1;
        return 0;
      },
    });
    expect(selectedCaseId(doc.element("#list").innerHTML)).toBe("one");
    expect(drawn).toBe(0);
  });
});

// ---- the old data renders as before ----------------------------------------------------

describe("the old data", () => {
  test("renders exactly as it did before the new fields", async () => {
    const legacy = (await readJson(
      fileURLToPath(new URL("./fixtures/cases-legacy.json", import.meta.url)),
    )) as Record<string, string>;
    const c = conversion.cases[0];
    const lane = Object.keys(c.pages).find((key) => key !== "reference") as string;
    const lanes = lanesForCase(c, engines).filter((l) => l.state !== "dropped");
    expect(
      renderCaseStrip({
        case: c,
        engine: { key: lane, label: lane },
        assetsBase: index.assets_base,
      }),
    ).toBe(legacy.strip);
    expect(
      renderCaseStrip({
        case: c,
        engine: { key: "reference", label: "Word" },
        assetsBase: index.assets_base,
      }),
    ).toBe(legacy.stripReference);
    expect(
      renderCaseHead({
        case: c,
        engine: { key: lane, label: lane },
        assetsBase: index.assets_base,
        engines,
      }),
    ).toBe(legacy.head);
    expect(
      renderCaseHead({
        case: c,
        engine: { key: lane, label: lane },
        assetsBase: index.assets_base,
        engines,
        compact: true,
      }),
    ).toBe(legacy.headCompact);
    expect(
      renderCaseGrid({
        case: c,
        lanes,
        assetsBase: index.assets_base,
        engines,
        limit: 2,
      }),
    ).toBe(legacy.grid);
    expect(
      renderOverlay({
        case: c,
        under: { key: "reference", label: "Word" },
        over: { key: lane, label: "x" },
        assetsBase: index.assets_base,
        blend: "difference",
        alpha: 40,
      }),
    ).toBe(legacy.overlay);
  });
});

describe("file URLs are encoded per segment and stay under the base", () => {
  const base = "https://huggingface.co/datasets/o/r/resolve/abc/";
  it("encodes characters that would end the path", () => {
    expect(resolveFileUrl(base, "~/out/a b#1?.pdf")).toBe(`${base}out/a%20b%231%3F.pdf`);
  });
  it("refuses dot segments and empty segments", () => {
    expect(resolveFileUrl(base, "~/../escape.pdf")).toBe("");
    expect(resolveFileUrl(base, "~/a/./b.pdf")).toBe("");
    expect(resolveFileUrl(base, "~/a//b.pdf")).toBe("");
  });
});

// ---- the group picker under load (CodeRabbit, #154) ------------------------------------

describe("switching groups while a load is in flight", () => {
  /** Two groups, A and B; B's shard is served only when the test says so. */
  function twoGroups() {
    const a = caseBundle(1, 2);
    const b = caseBundle(1, 3);
    const shardA = { ...(a.shard as object), group: "A" } as { cases: Case[] };
    shardA.cases = shardA.cases.map((c) => ({ ...c, group: "A" }));
    const shardB = { ...(b.shard as object), group: "B" } as { cases: Case[] };
    shardB.cases = shardB.cases.map((c) => ({ ...c, group: "B" }));
    const index = {
      ...(a.index as object),
      groups: [
        { kind: "conversion", group: "A", count: 2, path: "cases/conversion/A.json" },
        { kind: "conversion", group: "B", count: 3, path: "cases/conversion/B.json" },
      ],
    };
    let releaseB: (ok: boolean) => void = () => undefined;
    const gateB = new Promise<boolean>((resolve) => {
      releaseB = resolve;
    });
    const fetchFake = (async (input: RequestInfo | URL) => {
      const url = String(input);
      const respond = (ok: boolean, body: unknown) =>
        ({
          ok,
          status: ok ? 200 : 503,
          statusText: ok ? "OK" : "Service Unavailable",
          json: async () => body,
        }) as Response;
      if (url.includes("index.json")) return respond(true, index);
      if (url.includes("A.json")) return respond(true, shardA);
      return respond(await gateB, shardB);
    }) as typeof fetch;
    return { fetchFake, releaseB: (ok: boolean) => releaseB(ok) };
  }

  async function mountOnA(fetchFake: typeof fetch): Promise<FakeDocument> {
    // Linked to group A: with no link the page opens all groups (#159).
    const doc = new FakeDocument("#A/one");
    globalThis.fetch = fetchFake;
    await mountCasesPage({
      kind: "conversion",
      indexUrl: "../release/cases/index.json",
      root: doc as unknown as Document,
      random: seeded(11),
    });
    return doc;
  }

  const pick = (doc: FakeDocument, value: string) => {
    const select = doc.element("#fxGroup");
    select.value = value;
    select.dispatch("change", { target: select });
  };
  const settle = () => new Promise((resolve) => setTimeout(resolve, 0));
  const groupsInList = (doc: FakeDocument) =>
    [...doc.element("#list").innerHTML.matchAll(/data-key="([^/"]*)\//g)].map((m) => m[1]);

  test("a slow load that a newer choice superseded does not take the view back", async () => {
    const original = globalThis.fetch;
    const { fetchFake, releaseB } = twoGroups();
    try {
      const doc = await mountOnA(fetchFake);
      pick(doc, "*"); // all groups: waits on B
      await settle();
      pick(doc, "A"); // the visitor changes their mind; A is cached
      await settle();
      doc.element("#navNext").dispatch("click");
      const chosen = selectedCaseId(doc.element("#list").innerHTML);
      expect(chosen).toBeDefined();
      releaseB(true); // the superseded load finishes last
      await settle();
      await settle();
      expect(doc.element("#fxGroup").value).toBe("A");
      expect(selectedCaseId(doc.element("#list").innerHTML)).toBe(chosen);
      expect(new Set(groupsInList(doc))).toEqual(new Set(["A"]));
    } finally {
      globalThis.fetch = original;
    }
  });

  test("all groups lists every group's cases, each under its own group", async () => {
    const original = globalThis.fetch;
    const { fetchFake, releaseB } = twoGroups();
    try {
      const doc = await mountOnA(fetchFake);
      pick(doc, "*");
      releaseB(true);
      await settle();
      await settle();
      expect(doc.element("#fxGroup").value).toBe("*");
      expect(groupsInList(doc).sort()).toEqual(["A", "A", "B", "B", "B"]);
      expect(doc.element("#fxn").textContent).toBe("5 of 5 cases");
    } finally {
      globalThis.fetch = original;
    }
  });

  test("the Scores table click cancels its default action (it sits in the About summary)", async () => {
    const bundle = caseBundle(2);
    const doc = await mountPage({ index: bundle.index, shard: bundle.shard });
    let prevented = false;
    doc.element("#viewToggle").dispatch("click", {
      target: null,
      preventDefault: () => {
        prevented = true;
      },
    });
    expect(prevented).toBe(true);
  });

  test("a load that fails puts the picker back on the group on screen and says why", async () => {
    const original = globalThis.fetch;
    const { fetchFake, releaseB } = twoGroups();
    try {
      const doc = await mountOnA(fetchFake);
      pick(doc, "B");
      await settle();
      releaseB(false);
      await settle();
      await settle();
      expect(doc.element("#fxGroup").value).toBe("A");
      expect(new Set(groupsInList(doc))).toEqual(new Set(["A"]));
      expect(doc.element("#fxn").textContent).toMatch(/B did not load: 503/);
    } finally {
      globalThis.fetch = original;
    }
  });
});

// ---- #158: no inline style attributes (benchmarks.law's CSP is style-src 'self') ----

describe("the renderers emit no style attribute (#158)", () => {
  const bundle = caseBundle(2, 2);
  const shard = parseCaseShard(bundle.shard);
  const parsedIndex = parseCasesIndex(bundle.index);
  const c = shard.cases[0] as Case;
  const engines = parsedIndex.engines;
  const lanes = lanesForCase(c, engines);
  const word = engines.find((e) => e.key === "reference") as Engine;
  const jub = engines.find((e) => e.key === "jubarte") as Engine;
  const html = [
    renderOverlay({
      case: c,
      under: word,
      over: jub,
      assetsBase: parsedIndex.assets_base,
      alpha: 30,
      blend: "difference",
    }),
    renderCaseGrid({
      case: c,
      lanes,
      assetsBase: parsedIndex.assets_base,
      engines,
      filesBase: "https://example.invalid/f/",
    }),
    renderCaseGrid({ case: c, lanes, assetsBase: parsedIndex.assets_base, engines, compact: true }),
    renderEngineToggles({
      engines,
      lanes: engines,
      on: { jubarte: true, reference: true },
      active: new Set(["jubarte", "reference"]),
      versions: {},
    }),
    renderScoresTable({
      cases: shard.cases,
      engines,
      lanes: engines,
      selected: "",
      sort: { key: "", dir: 1 },
    } as never),
    renderCaseList({ cases: shard.cases }),
  ];

  test.each(html.map((h, i) => [i, h]))("renderer %i has no style= attribute", (_i, h) => {
    expect(h).not.toMatch(/\sstyle="/);
  });

  test("the overlay's top page carries its opacity and blend in data-css", () => {
    expect(html[0]).toMatch(/class="top"[^>]*data-css="opacity:0\.3;mix-blend-mode:difference"/);
  });

  test("applyInlineCss sets each declaration as its own CSSOM property (never cssText)", () => {
    const set: [string, string][] = [];
    const el = {
      dataset: { css: "opacity:0.3;mix-blend-mode:difference; border-top: 2px solid #FFD400" },
      style: {
        setProperty: (name: string, value: string) => set.push([name, value]),
        set cssText(_v: string) {
          throw new Error("cssText is a CSS string; a strict style-src may block it");
        },
      },
    };
    const root = { querySelectorAll: () => [el] };
    applyInlineCss(root as unknown as ParentNode);
    expect(set).toEqual([
      ["opacity", "0.3"],
      ["mix-blend-mode", "difference"],
      ["border-top", "2px solid #FFD400"],
    ]);
  });

  test("the package entry exports applyInlineCss beside the renderers", async () => {
    const entry = await import("../src/index.ts");
    expect(typeof (entry as Record<string, unknown>).applyInlineCss).toBe("function");
  });
});

// ---- #159: all groups by default, and the next case pre-loaded ----

function twoGroupBundle(): { index: unknown; shards: Record<string, unknown> } {
  const a = caseBundle(1, 2);
  const b = caseBundle(1, 3);
  const shardA = a.shard as { cases: Case[] };
  const shardB = b.shard as { cases: Case[] };
  shardA.cases = shardA.cases.map((c) => ({ ...c, group: "A" }));
  shardB.cases = shardB.cases.map((c) => ({ ...c, group: "B" }));
  return {
    index: {
      ...(a.index as object),
      groups: [
        { kind: "conversion", group: "A", count: 2, path: "cases/conversion/A.json" },
        { kind: "conversion", group: "B", count: 3, path: "cases/conversion/B.json" },
      ],
    },
    shards: { "A.json": { ...shardA, group: "A" }, "B.json": { ...shardB, group: "B" } },
  };
}

async function mountTwo(
  hash: string,
  preload?: (url: string) => void,
  search = "",
  failing = "",
): Promise<{ doc: FakeDocument; fetched: string[] }> {
  const { index, shards } = twoGroupBundle();
  const fetched: string[] = [];
  const doc = new FakeDocument(hash);
  doc.defaultView.location.search = search;
  const original = globalThis.fetch;
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    const url = String(input);
    fetched.push(url);
    const name = Object.keys(shards).find((k) => url.endsWith(k));
    const body = url.includes("index.json") ? index : name ? shards[name] : undefined;
    if (failing && url.endsWith(failing)) {
      return {
        ok: false,
        status: 503,
        statusText: "Service Unavailable",
        json: async () => ({}),
      } as Response;
    }
    return { ok: true, status: 200, statusText: "OK", json: async () => body } as Response;
  }) as typeof fetch;
  try {
    await mountCasesPage({
      kind: "conversion",
      indexUrl: "../release/cases/index.json",
      root: doc as unknown as Document,
      random: seeded(3),
      ...(preload ? { preload } : {}),
    });
  } finally {
    globalThis.fetch = original;
  }
  return { doc, fetched };
}

describe("all groups by default (#159)", () => {
  test("a page opened without a link loads every group and shows all of them", async () => {
    const { doc, fetched } = await mountTwo("");
    expect(fetched.some((u) => u.endsWith("A.json"))).toBe(true);
    expect(fetched.some((u) => u.endsWith("B.json"))).toBe(true);
    expect(doc.element("#fxGroup").value).toBe("*");
    const groupsShown = new Set(
      [...doc.element("#list").innerHTML.matchAll(/data-key="([^/"]*)\//g)].map((m) => m[1]),
    );
    expect([...groupsShown].sort()).toEqual(["A", "B"]);
  });

  test("one group that fails to load leaves the others on screen and says so", async () => {
    const { doc } = await mountTwo("", undefined, "", "B.json");
    expect(doc.element("#fxGroup").value).toBe("A");
    expect(selectedCaseId(doc.element("#list").innerHTML)).toBeDefined();
    expect(doc.element("#fxn").textContent).toMatch(/all groups did not load: 503/);
  });

  test("a #scores link opens the table over all groups", async () => {
    const { doc, fetched } = await mountTwo("#scores");
    expect(fetched.some((u) => u.endsWith("A.json"))).toBe(true);
    expect(fetched.some((u) => u.endsWith("B.json"))).toBe(true);
    expect(doc.element("#fxGroup").value).toBe("*");
  });

  test("a link to one group's case still opens that group", async () => {
    const { doc } = await mountTwo("#B/two");
    expect(doc.element("#fxGroup").value).toBe("B");
    expect(selectedCaseId(doc.element("#list").innerHTML)).toBe("two");
  });
});

describe("the next case is pre-loaded (#159)", () => {
  test("after a case renders, the next visible case's pages are pre-loaded, and only those", async () => {
    const urls: string[] = [];
    const { doc } = await mountTwo("#A/one", (u) => urls.push(u));
    // The list order in group A is one, two: the next case is "two".
    expect(selectedCaseId(doc.element("#list").innerHTML)).toBe("one");
    expect(urls.length).toBeGreaterThan(0);
    expect(urls.every((u) => u.includes("/cases/two/"))).toBe(true);
  });
});

describe("the mobile overlay keeps its header current (#158)", () => {
  test("with the overlay on, Next moves the case name and the Overlay button stays pressed", async () => {
    const { doc } = await mountTwo("#A/one", () => undefined, "?mobile=1");
    doc.element("#mOvl").dispatch("click");
    expect(doc.element("#mOvl").getAttribute("aria-pressed")).toBe("true");
    expect(doc.element("#mCase").textContent).toBe("one");
    doc.element("#mNext").dispatch("click");
    expect(doc.element("#mCase").textContent).toBe("two");
    expect(doc.element("#mOvl").getAttribute("aria-pressed")).toBe("true");
  });
});

describe("the pre-load is bounded per step (#159)", () => {
  test("at most PRELOAD_STEP pages are requested for the next case, first pages first", async () => {
    const { index, shards } = twoGroupBundle();
    // Group A's second case gets 20 pages in two lanes: 40 candidate URLs.
    const shard = shards["A.json"] as { cases: Case[] };
    const many = (lane: string) =>
      Array.from(
        { length: 20 },
        (_, i) => `~/cases/two/${lane}/page_${String(i + 1).padStart(3, "0")}.webp`,
      );
    shard.cases[1] = {
      ...(shard.cases[1] as Case),
      pages: { reference: many("reference"), jubarte: many("jubarte") },
      page_counts: { reference: 20, jubarte: 20 },
    };
    const urls: string[] = [];
    const doc = new FakeDocument("#A/one");
    const original = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL) => {
      const url = String(input);
      const name = Object.keys(shards).find((k) => url.endsWith(k));
      const body = url.includes("index.json") ? index : name ? shards[name] : undefined;
      return { ok: true, status: 200, statusText: "OK", json: async () => body } as Response;
    }) as typeof fetch;
    try {
      await mountCasesPage({
        kind: "conversion",
        indexUrl: "../release/cases/index.json",
        root: doc as unknown as Document,
        preload: (u) => urls.push(u),
      });
    } finally {
      globalThis.fetch = original;
    }
    expect(urls.length).toBe(PRELOAD_STEP);
    expect(urls.slice(0, 2).every((u) => /page_001/.test(u))).toBe(true);
  });
});

describe("review round 2 on #160", () => {
  test("with the desktop overlay on, only the under and over lanes are pre-loaded", async () => {
    const { index, shards } = twoGroupBundle();
    const shard = shards["A.json"] as { cases: Case[] };
    shard.cases = shard.cases.map((c) => ({
      ...c,
      pages: {
        reference: c.pages.reference,
        jubarte: c.pages.reference.map((p) => p.replace("/reference/", "/jubarte/")),
        docxodus: c.pages.reference.map((p) => p.replace("/reference/", "/docxodus/")),
      },
      page_counts: { ...c.page_counts, docxodus: 1 },
      scores: { ...c.scores, docxodus: { pixel: 50 } },
    }));
    const idx = {
      ...(index as { engines: unknown[] }),
      engines: [
        ...(index as { engines: Engine[] }).engines,
        { key: "docxodus", label: "docxodus" },
      ],
    };
    const urls: string[] = [];
    const doc = new FakeDocument("#A/one");
    const original = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL) => {
      const url = String(input);
      const name = Object.keys(shards).find((k) => url.endsWith(k));
      const body = url.includes("index.json") ? idx : name ? shards[name] : undefined;
      return { ok: true, status: 200, statusText: "OK", json: async () => body } as Response;
    }) as typeof fetch;
    try {
      await mountCasesPage({
        kind: "conversion",
        indexUrl: "../release/cases/index.json",
        root: doc as unknown as Document,
        preload: (u) => urls.push(u),
      });
    } finally {
      globalThis.fetch = original;
    }
    urls.length = 0;
    const box = doc.element("#ovl");
    box.checked = true;
    box.dispatch("change", { target: box });
    // Move on: the next case is now "one", not yet pre-loaded with any lane.
    doc.element("#navNext").dispatch("click");
    const lanes = new Set(urls.map((u) => /\/cases\/one\/([^/]+)\//.exec(u)?.[1]));
    expect(urls.length).toBeGreaterThan(0);
    expect(lanes.size).toBe(2);
    expect(lanes.has("reference")).toBe(true);
  });

  test("a stale startup load does not leave the page blank after the visitor's own pick failed", async () => {
    const { index, shards } = twoGroupBundle();
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    let bCalls = 0;
    const doc = new FakeDocument("");
    const original = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL) => {
      const url = String(input);
      const respond = (ok: boolean, body: unknown) =>
        ({
          ok,
          status: ok ? 200 : 503,
          statusText: ok ? "OK" : "Service Unavailable",
          json: async () => body,
        }) as Response;
      if (url.includes("index.json")) return respond(true, index);
      if (url.endsWith("B.json") && ++bCalls === 2) return respond(false, {});
      await gate;
      const name = Object.keys(shards).find((k) => url.endsWith(k)) as string;
      return respond(true, shards[name]);
    }) as typeof fetch;
    try {
      const mounted = mountCasesPage({
        kind: "conversion",
        indexUrl: "../release/cases/index.json",
        root: doc as unknown as Document,
        random: seeded(5),
      });
      await new Promise((resolve) => setTimeout(resolve, 0));
      const select = doc.element("#fxGroup");
      select.value = "B";
      select.dispatch("change", { target: select });
      await new Promise((resolve) => setTimeout(resolve, 0));
      release();
      await mounted;
    } finally {
      globalThis.fetch = original;
    }
    expect(selectedCaseId(doc.element("#list").innerHTML)).toBeDefined();
  });
});
