import { spawnSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { describe, expect, test } from "vitest";

interface PackageManifest {
  exports: Record<string, unknown>;
  scripts: Record<string, string>;
}

const packageRoot = fileURLToPath(new URL("../", import.meta.url));
const repositoryRoot = fileURLToPath(new URL("../../../", import.meta.url));
const manifest = JSON.parse(
  await readFile(new URL("../package.json", import.meta.url), "utf8"),
) as PackageManifest;

describe("package contract", () => {
  test("exports its package manifest", () => {
    expect(manifest.exports["./package.json"]).toBe("./package.json");

    const require = createRequire(import.meta.url);
    expect(require.resolve("@jandira-tech/bench-viewer/package.json")).toContain(
      "packages/bench-viewer/package.json",
    );
  });

  test("keeps prepare and checks the committed dist build", () => {
    expect(manifest.scripts.prepare).toBe("tsc");
    expect(manifest.scripts["check:dist"]).toBe("tsc && git diff --exit-code -- dist");
  });

  test("does not ignore the package dist directory", () => {
    const result = spawnSync(
      "git",
      ["check-ignore", "--no-index", "-q", "packages/bench-viewer/dist/index.js"],
      { cwd: repositoryRoot },
    );

    expect(result.status).toBe(1);
  });

  test("has the compiled package entry point", async () => {
    const entry = await readFile(new URL("../dist/index.js", import.meta.url), "utf8");

    expect(entry).toContain("parseScores");
    expect(packageRoot).toContain("packages/bench-viewer");
  });
});
