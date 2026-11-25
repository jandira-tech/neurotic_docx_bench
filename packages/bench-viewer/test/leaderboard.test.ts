import { spawn } from "node:child_process";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, test } from "vitest";
import { buildLeaderboardPage, SAMPLES_HEADING, SAMPLES_HEADING_ID } from "../src/index.ts";
import type { Scores } from "../src/types.ts";
import { fixture } from "./fixture.ts";

// The arthur-law page (benchmarks.law) shows the scores. The jubarte page
// (jubarte.pro) shows the product: headlines, our own rows marked, the
// affiliation dagger. This file pins the difference, and pins that the
// jubarte page did not move while the arthur-law page did.

const packageRoot = fileURLToPath(new URL("../", import.meta.url));
const script = join(packageRoot, "scripts", "build-pages.ts");
const fixturePath = join(packageRoot, "test", "fixtures", "scores.json");
// The jubarte page as it was before the leaderboard page existed: the same
// build-pages output, with the jubarte skin on it. The theme flag picks the
// skin, so this snapshot is the jubarte theme's page byte for byte.
const jubarteGoldenPath = join(packageRoot, "test", "fixtures", "jubarte-page.html");

interface RunResult {
  code: number;
  stderr: string;
  stdout: string;
}

function runNode(args: string[]): Promise<RunResult> {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, args, { cwd: packageRoot });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString();
    });
    child.on("error", reject);
    child.on("close", (code) => {
      resolve({ code: code ?? 1, stderr, stdout });
    });
  });
}

const page = buildLeaderboardPage(fixture);

/** The text a reader sees: the markup stripped, the whitespace collapsed. */
function textOf(html: string): string {
  return html
    .replace(/<[^>]*>/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

describe("leaderboard page", () => {
  test("renders no headline from the scores", () => {
    for (const headline of fixture.headlines) {
      expect(page).not.toContain(headline.label);
      expect(page).not.toContain(headline.vs);
      expect(page).not.toContain(headline.sub);
    }
    expect(page).not.toContain('class="cell-pad headline"');
    expect(page).not.toContain('class="headline-v"');
  });

  test("marks no row as ours and no tool name carries the affiliation mark", () => {
    expect(page).not.toContain("†");
    expect(page).not.toMatch(/class="[^"]*\bours\b/);
    expect(page).not.toContain('class="bar hi"');
    expect(page).not.toContain('class="bar thin hi"');
  });

  test("shows every table the scores carry", () => {
    for (const table of fixture.tables) {
      expect(page).toContain(`id="${table.id}"`);
    }
  });

  test("puts the full-corpus tables before the sample tables", () => {
    const full = fixture.tables.filter((t) => !t.id.endsWith("-sample"));
    const samples = fixture.tables.filter((t) => t.id.endsWith("-sample"));

    expect(full.length).toBeGreaterThan(0);
    expect(samples.length).toBeGreaterThan(0);

    const headingAt = page.indexOf(`id="${SAMPLES_HEADING_ID}"`);
    expect(headingAt).toBeGreaterThan(-1);

    const fullAt = full.map((t) => page.indexOf(`id="${t.id}"`));
    for (const at of fullAt) {
      expect(at).toBeGreaterThan(-1);
      expect(at).toBeLessThan(headingAt);
    }
    // The full tables keep the order the scores give them.
    expect([...fullAt].sort((a, b) => a - b)).toEqual(fullAt);

    for (const table of samples) {
      const at = page.indexOf(`id="${table.id}"`);
      expect(at).toBeGreaterThan(headingAt);
    }
  });

  test("the samples heading claims no size, even when the samples differ in size", () => {
    // ndb-v0.0.11's samples differ (860 documents, 600 pairs); each sample
    // table's own title says its size, so the heading must not.
    const uneven = structuredClone(fixture) as Scores;
    const sample = uneven.tables.find((t) => t.id === "conversion-sample");
    expect(sample).toBeDefined();
    for (const row of sample?.rows ?? []) row.docs = 860;
    const html = buildLeaderboardPage(uneven);
    const at = html.indexOf(`id="${SAMPLES_HEADING_ID}"`);
    expect(at).toBeGreaterThan(-1);
    const heading = textOf(html.slice(html.lastIndexOf("<h2", at), html.indexOf("</h2>", at) + 5));
    expect(heading).toBe(SAMPLES_HEADING);
    expect(heading).toBe("Release samples");
  });

  test("calls out the leader of every table that ranks more than one tool", () => {
    const text = textOf(page);
    const ranked = fixture.tables.filter((table) => table.rows.length > 1);
    expect(ranked.length).toBeLessThan(fixture.tables.length); // the fixture holds a table of one
    expect(page.match(/Leader: /g)?.length ?? 0).toBe(ranked.length);
    // The leader is the row ranked 1, not the row that is ours.
    expect(text).toContain("Leader: docxodus — median 99.87");
    expect(text).toContain("Leader: office2pdf — median 84.34");
    expect(text).toContain("Leader: jubarte — median 81.09");
  });

  test("keeps the badge, the states, the method and the provenance", () => {
    const withProvenance = structuredClone(fixture) as Scores;
    withProvenance.provenance = { docsets: ["abc123"], renderers: ["oracle:microsoft_word"] };
    const html = buildLeaderboardPage(withProvenance);

    expect(html).toContain(`bench ${fixture.version}`);
    expect(html).toContain(`generated ${fixture.generated}`);
    expect(html).toContain("By corpus state");
    expect(html).toContain("tracking, no comments");
    expect(html).toContain("Oracle: real Word");
    expect(html).toContain("Provenance");
    expect(html).toContain("oracle:microsoft_word");
  });

  test("escapes a malicious tool name", () => {
    const hostile = structuredClone(fixture) as Scores;
    hostile.tables[0].rows[0].tool = '<script>alert("x")</script>';

    const html = buildLeaderboardPage(hostile);

    expect(html).not.toContain("<script>");
    expect(html).not.toContain("</script>");
    expect(html).toContain("&lt;script&gt;");
  });
});

describe("build-pages themes", () => {
  test("builds the leaderboard page for the arthur-law theme", async () => {
    const outDir = await mkdtemp(join(tmpdir(), "bench-viewer-arthur-law-"));

    try {
      const result = await runNode([script, fixturePath, outDir, "--theme", "arthur-law"]);

      expect(result.code).toBe(0);
      const html = await readFile(join(outDir, "index.html"), "utf8");
      expect(html).toContain('href="./arthur-law.css"');
      expect(html).not.toContain('class="cell-pad headline"');
      expect(html).not.toContain("†");
      for (const table of fixture.tables) {
        expect(html).toContain(`id="${table.id}"`);
      }
    } finally {
      await rm(outDir, { recursive: true, force: true });
    }
  });

  test("builds the jubarte page byte for byte as it was", async () => {
    const outDir = await mkdtemp(join(tmpdir(), "bench-viewer-jubarte-"));

    try {
      const result = await runNode([script, fixturePath, outDir, "--theme", "jubarte"]);

      expect(result.code).toBe(0);
      const html = await readFile(join(outDir, "index.html"), "utf8");
      const golden = await readFile(jubarteGoldenPath, "utf8");
      expect(html).toBe(golden);
    } finally {
      await rm(outDir, { recursive: true, force: true });
    }
  });

  test("refuses an unknown theme", async () => {
    const outDir = await mkdtemp(join(tmpdir(), "bench-viewer-theme-"));

    try {
      const result = await runNode([script, fixturePath, outDir, "--theme", "nope"]);

      expect(result.code).not.toBe(0);
      expect(result.stderr).toContain("theme");
    } finally {
      await rm(outDir, { recursive: true, force: true });
    }
  });
});

describe("a table of one on the leaderboard page", () => {
  const page = buildLeaderboardPage(fixture);
  const one = fixture.tables.find((table) => table.rows.length === 1);

  test("names no leader and prints no rank", () => {
    expect(one).toBeDefined();
    const section = page.slice(page.indexOf(`<section class="mt-72" id="${one?.id}">`));
    const own = section.slice(0, section.indexOf("</section>"));
    expect(own).not.toContain("Leader: ");
    expect(own).toContain('<span class="mono muted" role="cell"></span>');
  });

  test("backtick spans in a table's meta and note are code, not literal backticks", () => {
    const withCode = structuredClone(fixture) as Scores;
    withCode.tables[0].meta = "set `c947065c59b2`";
    const html = buildLeaderboardPage(withCode);
    expect(html).toContain("set <code>c947065c59b2</code>");
  });
});
