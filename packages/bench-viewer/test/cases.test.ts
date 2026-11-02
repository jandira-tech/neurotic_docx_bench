import { spawn } from "node:child_process";
import { access, mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, test } from "vitest";
import type { Case, CasesIndex, Engine } from "../src/cases.ts";
import {
  caseHash,
  defaultComparisonLane,
  defaultOverlayLane,
  laneState,
  lanesForCase,
  lanesWithData,
  orderLanes,
  parseCaseHash,
  parseCaseShard,
  parseCasesIndex,
  renderCaseGrid,
  renderCaseList,
  renderCaseStrip,
  renderCasesLegend,
  renderEngineToggles,
  renderGroupOptions,
  renderOverlay,
  renderScoresTable,
  resolveAssetUrl,
  safeAssetUrl,
  shardUrl,
} from "../src/cases.ts";

const packageRoot = fileURLToPath(new URL("../", import.meta.url));
const fixtureRoot = fileURLToPath(new URL("./fixtures/release/", import.meta.url));
const script = join(packageRoot, "scripts", "build-pages.ts");

async function readJson(path: string): Promise<unknown> {
  return JSON.parse(await readFile(path, "utf8"));
}

const index: CasesIndex = parseCasesIndex(await readJson(join(fixtureRoot, "cases", "index.json")));

const conversion = parseCaseShard(
  await readJson(join(fixtureRoot, "cases", "conversion", "v1--with_comments_clean.json")),
);
const wordcraft = parseCaseShard(
  await readJson(join(fixtureRoot, "cases", "conversion", "wordcraft1014--convert.json")),
);
const redlines = parseCaseShard(
  await readJson(join(fixtureRoot, "cases", "redline", "wordcraft1014--compare.json")),
);

const engines: Engine[] = index.engines;

/** A case whose strings are all hostile: nothing may reach the page as markup. */
function hostileCase(): Case {
  return {
    kind: "conversion",
    group: '<script>alert("group")</script>',
    case: '<img src=x onerror="alert(1)">',
    pages: {
      reference: ["~/pages/reference/page_001.webp"],
      "evil-lane": ["~/pages/evil/page_001.webp"],
    },
    page_counts: { reference: 1, "evil-lane": 1 },
    scores: { "evil-lane": { pixel: 1 } },
    times: {},
    versions: {
      reference: '"><script>alert("version")</script>',
      "evil-lane": "1.0 & <b>bold</b>",
    },
    dropped: [],
    reference_app: "Microsoft Word",
    errors: { "evil-lane": "<script>alert('error')</script>" },
  };
}

describe("the cases index", () => {
  test("reads the release's own fields", () => {
    expect(index.version).toBe("1");
    expect(index.assets_base).toBe("https://pub-92c80eda1059428394970066c8500eda.r2.dev/");
    expect(index.engines.length).toBeGreaterThan(0);
    expect(index.groups.map((group) => group.group)).toEqual([
      "v1/with_comments_clean",
      "wordcraft1014/convert",
      "ar/accept_all",
      "wordcraft1014/compare",
    ]);
  });

  test("the group paths are the release's own shard paths", () => {
    for (const group of index.groups) {
      expect(group.path).toBe(`cases/${group.kind}/${group.group.replace("/", "--")}.json`);
    }
  });

  test("refuses an index without an https asset base", () => {
    expect(() => parseCasesIndex({ ...index, assets_base: "http://example.com/" })).toThrow(
      /assets_base/,
    );
  });
});

describe("the case shards", () => {
  test("read the group's cases", () => {
    expect(conversion.kind).toBe("conversion");
    expect(conversion.group).toBe("v1/with_comments_clean");
    expect(conversion.cases.length).toBe(2);
    expect(redlines.cases.length).toBe(2);
  });

  test("a case keeps its pages, scores, versions and lanes", () => {
    const c = conversion.cases[0];
    expect(c.case).toBeTruthy();
    expect(Object.keys(c.pages).length).toBeGreaterThan(0);
    expect(c.versions.reference).toBeTruthy();
  });
});

describe("the asset paths", () => {
  test("a ~/ path resolves against the asset base", () => {
    expect(resolveAssetUrl(index.assets_base, "~/renew1030/x/page_001.webp")).toBe(
      "https://pub-92c80eda1059428394970066c8500eda.r2.dev/renew1030/x/page_001.webp",
    );
  });

  test("a path that is not a URL is refused", () => {
    expect(safeAssetUrl(index.assets_base, "javascript:alert(1)")).toBe("");
    expect(safeAssetUrl(index.assets_base, "~/ok/page_001.webp")).toBe(
      "https://pub-92c80eda1059428394970066c8500eda.r2.dev/ok/page_001.webp",
    );
  });

  test("a shard path resolves against the release the index came from", () => {
    expect(
      shardUrl("../release/cases/index.json", "cases/conversion/samples.json", "http://x/"),
    ).toBe("http://x/release/cases/conversion/samples.json");
    expect(
      shardUrl("release/cases/index.json", "cases/redline/ar--accept_all.json", "http://x/"),
    ).toBe("http://x/release/cases/redline/ar--accept_all.json");
  });
});

describe("the hash routing", () => {
  test("a hash names the group and the case", () => {
    expect(parseCaseHash("#v1/clean/abc123")).toEqual({ group: "v1/clean", case: "abc123" });
  });

  test("the known groups win over the last slash", () => {
    const parsed = parseCaseHash("#v1/clean/abc123", ["v1/clean", "cases"]);
    expect(parsed).toEqual({ group: "v1/clean", case: "abc123" });
  });

  test("an encoded hash decodes", () => {
    const hash = caseHash("wordcraft1014/convert", "clean__070591c299");
    expect(hash).toBe("#wordcraft1014%2Fconvert%2Fclean__070591c299");
    expect(parseCaseHash(hash, ["wordcraft1014/convert"])).toEqual({
      group: "wordcraft1014/convert",
      case: "clean__070591c299",
    });
  });

  test("a hash that names nothing is null", () => {
    expect(parseCaseHash("")).toBeNull();
    expect(parseCaseHash("#scores", ["cases"])).toBeNull();
  });
});

describe("the lanes", () => {
  test("a lane's state follows the case's own lists", () => {
    const c = redlines.cases[0];
    expect(laneState(c, "reference")).toBe("measured");
    expect(laneState(c, "stemma-0.5.0")).toBe("unavailable");
    expect(laneState(c, "superdoc-2.20.0")).toBe("failed");
    expect(laneState(c, "superdoc")).toBe("dropped");
  });

  test("a lane excluded for cause is not applicable", () => {
    const c = wordcraft.cases[0];
    expect(laneState(c, "pymupdf-pro-1.28.2")).toBe("not-applicable");
  });

  test("the lanes come with Word first", () => {
    const lanes = lanesForCase(redlines.cases[0], engines);
    expect(lanes[0].engine.key).toBe("reference");
  });
});

describe("the lane order", () => {
  test("a group's lanes are Word first, then the scored-case count, ties by label", () => {
    // v1/with_comments_clean: libreoffice, docxodus and jubarte each scored both
    // cases (tie), so the label breaks it: LibreOffice < docxodus < jubarte.
    const order = orderLanes(conversion.cases, engines);
    expect(order.slice(0, 4).map((engine) => engine.key)).toEqual([
      "reference",
      "libreoffice",
      "docxodus",
      "jubarte",
    ]);
  });

  test("lanes the group's cases never mention are not the page's lanes", () => {
    // The redline-only lanes (jubarte-rust, superdoc, stemma, docxodus-12.6.5,
    // jubarte-093, …) are mentioned by no conversion case: dropped, pages,
    // scores, errors, nothing.
    const order = orderLanes(conversion.cases, engines);
    for (const key of [
      "jubarte-rust",
      "superdoc",
      "superdoc-2.20.0",
      "stemma-0.5.0",
      "docxodus-12.6.5",
      "jubarte-093",
    ]) {
      expect(order.find((engine) => engine.key === key)).toBeUndefined();
    }
  });

  test("a redline group keeps the redline lanes and drops the conversion-only ones", () => {
    const order = orderLanes(redlines.cases, engines);
    expect(order[0].key).toBe("reference");
    expect(order.map((engine) => engine.key)).toContain("jubarte-rust");
    expect(order.find((engine) => engine.key === "jubarte")).toBeUndefined();
    expect(order.find((engine) => engine.key === "libreoffice")).toBeUndefined();
  });

  test("the lanes with data are everything but the dropped-everywhere ones", () => {
    // wordcraft1014/compare: stemma-0.5.0 is `unavailable` in both cases (the
    // cohort lane with no published measurement — data, shown as "not
    // measured"), while superdoc is dropped in both (folded behind +N more).
    const data = lanesWithData(redlines.cases);
    expect(data.has("reference")).toBe(true);
    expect(data.has("stemma-0.5.0")).toBe(true);
    expect(data.has("superdoc")).toBe(false);
  });

  test("the default comparison lane is the first non-reference lane, the overlay's the second", () => {
    const order = orderLanes(conversion.cases, engines);
    expect(defaultComparisonLane(order)?.key).toBe("libreoffice");
    expect(defaultOverlayLane(order)?.key).toBe("docxodus");
    expect(defaultComparisonLane(order.slice(0, 1))?.key).toBeUndefined();
    expect(defaultOverlayLane(order.slice(0, 2))?.key).toBeUndefined();
  });
});

describe("the case strip", () => {
  test("draws the pages as images resolved against the asset base", () => {
    const c = conversion.cases[0];
    const lane = Object.keys(c.pages).find((key) => key !== "reference") as string;
    const html = renderCaseStrip({
      case: c,
      engine: { key: lane, label: lane },
      assetsBase: index.assets_base,
    });
    expect(html).toContain(`src="${index.assets_base}`);
    expect(html).toContain('loading="lazy"');
    expect(html).toContain("<img");
  });

  test("a lane with no page for one of the pages says so", () => {
    const c: Case = {
      ...conversion.cases[0],
      pages: { reference: ["~/a/page_001.webp", null], short: ["~/b/page_001.webp", null] },
    };
    const html = renderCaseStrip({
      case: c,
      engine: { key: "short", label: "short" },
      assetsBase: index.assets_base,
    });
    expect(html).toContain("no page 2");
  });

  test("labels the lanes left out", () => {
    const c = redlines.cases[0];
    const unavailable = renderCaseStrip({
      case: c,
      engine: { key: "stemma-0.5.0", label: "stemma-0.5.0" },
      assetsBase: index.assets_base,
    });
    expect(unavailable).toContain("not measured");
    const dropped = renderCaseStrip({
      case: c,
      engine: { key: "superdoc", label: "SuperDoc" },
      assetsBase: index.assets_base,
    });
    expect(dropped).toContain("dropped");
    const failed = renderCaseStrip({
      case: c,
      engine: { key: "superdoc-2.20.0", label: "superdoc-2.20.0" },
      assetsBase: index.assets_base,
    });
    expect(failed).toContain("failed");
  });

  test("a failed lane keeps its error", () => {
    const c = redlines.cases[0];
    const html = renderCaseStrip({
      case: c,
      engine: { key: "stemma-0.6.0", label: "stemma-0.6.0" },
      assetsBase: index.assets_base,
    });
    expect(html).toContain("lane-error");
    expect(html).toContain("missing candidate PDF");
  });

  test("every data string is escaped", () => {
    const c = hostileCase();
    const html = renderCaseStrip({
      case: c,
      engine: { key: "evil-lane", label: "<b>evil</b>" },
      assetsBase: index.assets_base,
    });
    expect(html).not.toContain("<script>");
    expect(html).not.toContain("onerror=");
    expect(html).toContain("&lt;script&gt;");
  });
});

describe("the grid", () => {
  test("draws a header and a column per lane", () => {
    const c = conversion.cases[0];
    const lanes = lanesForCase(c, engines).filter((lane) => lane.state !== "dropped");
    const html = renderCaseGrid({
      case: c,
      lanes,
      assetsBase: index.assets_base,
      engines,
      limit: 2,
    });
    expect(html).toContain("colhead");
    expect(html).toContain('class="col"');
    expect(html).toContain("PDF");
  });

  test("the overlay draws the lane over the lane under", () => {
    const c = conversion.cases[0];
    const html = renderOverlay({
      case: c,
      under: { key: "reference", label: "Word" },
      over: { key: Object.keys(c.pages).find((key) => key !== "reference") as string, label: "x" },
      assetsBase: index.assets_base,
      blend: "difference",
      alpha: 40,
    });
    expect(html).toContain("mix-blend-mode:difference");
    expect(html).toContain("opacity:0.4");
  });
});

describe("the list and the score table", () => {
  test("the list names the case and the group", () => {
    const html = renderCaseList({ cases: conversion.cases, selected: conversion.cases[0].case });
    expect(html).toContain(`data-case="${conversion.cases[0].case}"`);
    expect(html).toContain("sel");
  });

  test("the score table has a row per case and a column per metric", () => {
    const html = renderScoresTable({ cases: conversion.cases, engines });
    expect(html).toContain("<table>");
    expect(html).toContain("mean");
    expect(html).toContain("Pixel");
    expect(html).toContain("best");
  });

  test("the group picker names the groups and their counts", () => {
    const html = renderGroupOptions(index.groups, "ar/accept_all");
    expect(html).toContain('value="ar/accept_all" selected');
    expect(html).toContain("(2)");
  });

  test("the engine toggles fold the lanes without data away", () => {
    const html = renderEngineToggles({
      engines,
      on: Object.fromEntries(engines.map((engine) => [engine.key, true])),
      active: new Set(["reference"]),
      versions: { reference: "Word 16.115 compare" },
    });
    expect(html).toContain("+");
    expect(html).toContain("more");
  });

  test("the engine bar shows the group's lanes in display order and never the other kind's", () => {
    const order = orderLanes(conversion.cases, engines);
    const html = renderEngineToggles({
      engines,
      lanes: order,
      on: Object.fromEntries(order.map((engine) => [engine.key, true])),
      active: lanesWithData(conversion.cases),
    });
    // One toggle per lane of the page's kind, in the display order.
    expect([...html.matchAll(/data-e="([^"]+)"/g)].map((m) => m[1])).toEqual(
      order.map((engine) => engine.key),
    );
    // The redline-only lanes are not even folded away: they are not this
    // page's lanes.
    expect(html).not.toContain('data-e="jubarte-rust"');
    expect(html).not.toContain('data-e="superdoc"');
    // 20 lanes of the kind, 4 with data in the group: 16 folded.
    expect(html).toContain('data-count="16"');
  });

  test("the legend explains the scores", () => {
    const html = renderCasesLegend({ kind: "redline" });
    expect(html).toContain("About these scores");
    expect(html).toContain("Jaccard");
  });
});

describe("the build-pages release mode", () => {
  test("builds the whole site and copies the release files", async () => {
    const outDir = await mkdtemp(join(tmpdir(), "bench-viewer-release-"));
    try {
      const result = await new Promise<{ code: number | null; stderr: string; stdout: string }>(
        (resolvePromise, reject) => {
          const child = spawn(
            process.execPath,
            [
              script,
              "--release",
              fixtureRoot,
              outDir,
              "--scores",
              join(packageRoot, "test", "fixtures", "scores.json"),
            ],
            { cwd: packageRoot },
          );
          let stdout = "";
          let stderr = "";
          child.stdout.on("data", (chunk: Buffer) => {
            stdout += chunk.toString();
          });
          child.stderr.on("data", (chunk: Buffer) => {
            stderr += chunk.toString();
          });
          child.on("error", reject);
          child.on("close", (code) => resolvePromise({ code, stderr, stdout }));
        },
      );
      expect(result.stderr).toBe("");
      expect(result.code).toBe(0);

      for (const path of [
        "index.html",
        "tokens.css",
        "arthur-law.css",
        "cases.css",
        "cases/index.html",
        "redlines/index.html",
        "speed/index.html",
        "js/cases.js",
        "js/esc.js",
        "js/speed.js",
        "release/cases/index.json",
        "release/cases/conversion/v1--with_comments_clean.json",
        "release/cases/redline/ar--accept_all.json",
        "release/speed.json",
      ]) {
        await expect(access(join(outDir, path))).resolves.toBeUndefined();
      }

      const cases = await readFile(join(outDir, "cases", "index.html"), "utf8");
      expect(cases).toContain('href="../cases.css"');
      expect(cases).toContain('"../release/cases/index.json"');
      expect(cases).toContain('"../js/cases.js"');
      expect(cases).not.toContain('"pages":');

      const speed = await readFile(join(outDir, "speed", "index.html"), "utf8");
      expect(speed).toContain('"../release/speed.json"');
      expect(speed).toContain('"../js/speed.js"');

      // Without --fonts nothing is copied and the package ships no binaries.
      await expect(access(join(outDir, "_static"))).rejects.toThrow();
      const css = await readFile(join(outDir, "cases.css"), "utf8");
      expect(css).toContain("@font-face");
      expect(css).toContain("manrope-latin-wght-normal.woff2");
    } finally {
      await rm(outDir, { recursive: true, force: true });
    }
  });

  test("--fonts copies the fonts next to the pages", async () => {
    const outDir = await mkdtemp(join(tmpdir(), "bench-viewer-fonts-"));
    try {
      const result = await new Promise<{ code: number | null; stderr: string; stdout: string }>(
        (resolvePromise, reject) => {
          const child = spawn(
            process.execPath,
            [
              script,
              "--release",
              fixtureRoot,
              outDir,
              "--scores",
              join(packageRoot, "test", "fixtures", "scores.json"),
              "--fonts",
              join(packageRoot, "test", "fixtures", "fonts"),
            ],
            { cwd: packageRoot },
          );
          let stdout = "";
          let stderr = "";
          child.stdout.on("data", (chunk: Buffer) => {
            stdout += chunk.toString();
          });
          child.stderr.on("data", (chunk: Buffer) => {
            stderr += chunk.toString();
          });
          child.on("error", reject);
          child.on("close", (code) => resolvePromise({ code, stderr, stdout }));
        },
      );
      expect(result.stderr).toBe("");
      expect(result.code).toBe(0);

      for (const path of [
        "_static/fonts/manrope-latin-wght-normal.woff2",
        "_static/fonts/jetbrains-mono-latin-wght-normal.woff2",
        "_static/fonts/LICENSE-manrope.txt",
        "_static/fonts/LICENSE-jetbrains-mono.txt",
      ]) {
        await expect(access(join(outDir, path))).resolves.toBeUndefined();
      }
    } finally {
      await rm(outDir, { recursive: true, force: true });
    }
  });

  test("--fonts refuses a directory that does not exist", async () => {
    const outDir = await mkdtemp(join(tmpdir(), "bench-viewer-nofonts-"));
    try {
      const result = await new Promise<{ code: number | null; stderr: string }>(
        (resolvePromise, reject) => {
          const child = spawn(
            process.execPath,
            [
              script,
              "--release",
              fixtureRoot,
              outDir,
              "--scores",
              join(packageRoot, "test", "fixtures", "scores.json"),
              "--fonts",
              join(outDir, "not-there"),
            ],
            { cwd: packageRoot },
          );
          let stderr = "";
          child.stderr.on("data", (chunk: Buffer) => {
            stderr += chunk.toString();
          });
          child.on("error", reject);
          child.on("close", (code) => resolvePromise({ code, stderr }));
        },
      );
      expect(result.code).not.toBe(0);
      expect(result.stderr).toContain("not-there");
    } finally {
      await rm(outDir, { recursive: true, force: true });
    }
  });
});
