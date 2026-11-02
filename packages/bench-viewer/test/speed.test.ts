import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { describe, expect, test } from "vitest";
import {
  formatMs,
  inlineCode,
  parseSpeed,
  renderCoverage,
  renderSampleNote,
  renderSpeed,
  renderSpeedNote,
  renderSpeedPage,
  renderSpeedTable,
  renderSpeedTask,
} from "../src/speed.ts";

const fixturePath = fileURLToPath(new URL("./fixtures/release/speed.json", import.meta.url));
const speed = parseSpeed(JSON.parse(await readFile(fixturePath, "utf8")));

const redlines = speed.tasks.find((task) => task.id === "redlines");
const pdf = speed.tasks.find((task) => task.id === "pdf");

describe("the speed release", () => {
  test("reads the tasks the release holds", () => {
    expect(speed.version).toBe("1");
    expect(speed.title).toContain("10,000");
    expect(speed.tasks.map((task) => task.id)).toEqual(["pdf", "redlines"]);
  });

  test("refuses a task with a table that is not there", () => {
    expect(() =>
      parseSpeed({
        ...speed,
        tasks: [{ ...redlines, tables: [] }],
      }),
    ).not.toThrow();
    expect(() => parseSpeed({ ...speed, tasks: "nope" })).toThrow(/tasks/);
  });
});

describe("the inline code", () => {
  test("a backtick span becomes a code element", () => {
    expect(inlineCode("the rows are in `results/speed_10k/`.")).toBe(
      "the rows are in <code>results/speed_10k/</code>.",
    );
  });

  test("the text is escaped before the backticks are read", () => {
    expect(inlineCode("`<script>` & `a`")).toBe("<code>&lt;script&gt;</code> &amp; <code>a</code>");
  });
});

describe("the speed page", () => {
  test("has a title, an introduction and one section per task", () => {
    const html = renderSpeed(speed);
    expect(html).toContain("<h1>");
    expect(html).toContain("Speed on");
    expect(html).toContain('<section id="redlines">');
    expect(html).toContain('<section id="pdf">');
  });

  test("the measured task has its coverage", () => {
    const html = renderSpeed(speed);
    expect(html).toContain("Coverage");
    expect(html).toContain("docxodus: 10000 of 10000 planned pairs");
  });

  test("the tables carry every column", () => {
    const html = renderSpeed(speed);
    expect(html).toContain("<table>");
    expect(html).toContain("median ms");
    expect(html).toContain("ok total s");
    expect(html).toContain("p99 ms");
  });

  test("the notes are prose with their bullets", () => {
    const html = renderSpeed(speed);
    expect(html).toContain("Redline generation run, notes");
    expect(html).toContain("Run of 2026-09-29");
    expect(html).toContain("<li>");
  });

  test("the unmeasured task says so", () => {
    expect(pdf?.available).toBe(false);
    expect(pdf ? renderSpeedTask(pdf) : "").toContain("Not measured yet.");
  });

  test("the sample note counts each tool's own sample", () => {
    const common = redlines?.tables.find((table) => table.id === "common");
    expect(common).toBeDefined();
    const note = common ? renderSampleNote(common) : "";
    expect(note).toContain("Times are per successful call.");
    expect(note).toContain("docxodus");
    expect(note).toContain("<code>ok</code>");
  });

  test("a row's numbers are formatted as the page shows them", () => {
    expect(formatMs(79.108)).toBe("79.1");
    expect(formatMs(null)).toBe("–");
  });

  test("the coverage line names the tool and both counts", () => {
    const html = renderCoverage({ tool: "jubarte-rust", completed: 10000, planned: 10000 });
    expect(html).toBe("<li>jubarte-rust: 10000 of 10000 planned pairs</li>");
  });

  test("a table row is escaped", () => {
    const html = renderSpeedTable({
      id: "common",
      title: "t",
      bucket_header: "pairs",
      rows: [
        {
          tool: "<script>alert(1)</script>",
          bucket: "all",
          n: 1,
          ok: 1,
          failed: 0,
          median_ms: 1,
          mean_ms: 1,
          p95_ms: 1,
          p99_ms: 1,
          max_ms: 1,
          ok_total_s: 1,
        },
      ],
    });
    expect(html).not.toContain("<script>");
    expect(html).toContain("&lt;script&gt;");
  });

  test("a note's heading and bullets are escaped", () => {
    const html = renderSpeedNote({
      heading: "<b>h</b>",
      paragraphs: ["a <i>p</i>"],
      bullets: ["b <u>u</u>"],
    });
    expect(html).toContain("&lt;b&gt;h&lt;/b&gt;");
    expect(html).toContain("&lt;i&gt;p&lt;/i&gt;");
    expect(html).toContain("&lt;u&gt;u&lt;/u&gt;");
  });
});

describe("the speed page shell", () => {
  test("fetches the release file instead of carrying the data", () => {
    const html = renderSpeedPage({
      speedUrl: "../release/speed.json",
      moduleUrl: "../js/speed.js",
      stylesheet: "../cases.css",
    });
    expect(html).toContain('href="../cases.css"');
    expect(html).toContain('"../release/speed.json"');
    expect(html).toContain('"../js/speed.js"');
    expect(html).not.toContain("docxodus");
  });
});
