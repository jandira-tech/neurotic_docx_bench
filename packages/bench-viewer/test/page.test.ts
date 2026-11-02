import { spawn } from "node:child_process";
import { access, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, test } from "vitest";
import { fixture } from "./fixture.ts";

const packageRoot = fileURLToPath(new URL("../", import.meta.url));
const script = join(packageRoot, "scripts", "build-pages.ts");
const fixturePath = join(packageRoot, "test", "fixtures", "scores.json");

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

describe("build-pages", () => {
  test("builds a page with every table, the badge, and both local stylesheets", async () => {
    const outDir = await mkdtemp(join(tmpdir(), "bench-viewer-page-"));

    try {
      const result = await runNode([script, fixturePath, outDir]);

      expect(result.code).toBe(0);
      const page = await readFile(join(outDir, "index.html"), "utf8");
      for (const table of fixture.tables) {
        expect(page).toContain(`id="${table.id}"`);
      }
      expect(page).toContain(`bench ${fixture.version}`);
      expect(page).toContain('href="./tokens.css"');
      expect(page).toContain('href="./arthur-law.css"');
      await expect(access(join(outDir, "tokens.css"))).resolves.toBeUndefined();
      await expect(access(join(outDir, "arthur-law.css"))).resolves.toBeUndefined();
    } finally {
      await rm(outDir, { recursive: true, force: true });
    }
  });

  test("exits nonzero for a non-http(s) repo URL", async () => {
    const outDir = await mkdtemp(join(tmpdir(), "bench-viewer-page-"));
    const scoresPath = join(outDir, "scores.json");
    const hostile = structuredClone(fixture);
    hostile.repo = "javascript:alert(1)";
    await writeFile(scoresPath, JSON.stringify(hostile), "utf8");

    try {
      const result = await runNode([script, scoresPath, join(outDir, "page")]);

      expect(result.code).not.toBe(0);
      expect(result.stderr).toMatch(/repo/);
    } finally {
      await rm(outDir, { recursive: true, force: true });
    }
  });

  test("reports invalid scores as one line, without a stack trace", async () => {
    const outDir = await mkdtemp(join(tmpdir(), "bench-viewer-page-"));
    const scoresPath = join(outDir, "scores.json");
    const bad = structuredClone(fixture) as unknown as {
      tables: { rows: { median: unknown }[] }[];
    };
    bad.tables[0].rows[0].median = "x";
    await writeFile(scoresPath, JSON.stringify(bad), "utf8");

    try {
      const result = await runNode([script, scoresPath, join(outDir, "page")]);

      expect(result.code).toBe(1);
      expect(result.stderr).toContain("scores: tables[0].rows[0].median must be a finite number");
      expect(result.stderr).not.toMatch(/^\s+at /m);
    } finally {
      await rm(outDir, { recursive: true, force: true });
    }
  });
});
