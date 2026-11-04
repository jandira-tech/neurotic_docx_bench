// The arthur.law skin for the case browsers and the speed page (#153): a layer
// loaded after cases.css that remaps its palette and type onto arthur.law's
// tokens. cases.css itself (the gh-pages look) does not change.
import { readFile } from "node:fs/promises";
import { describe, expect, test } from "vitest";

const casesCss = await readFile(new URL("../themes/cases.css", import.meta.url), "utf8");
const layer = await readFile(new URL("../themes/arthur-law-cases.css", import.meta.url), "utf8");

/** The custom properties a :root block declares, name -> value. */
function rootVars(css: string): Map<string, string> {
  const block = css.match(/:root\s*\{([^}]*)\}/)?.[1] ?? "";
  const out = new Map<string, string>();
  for (const m of block.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) out.set(m[1], m[2].trim());
  return out;
}

const published = rootVars(casesCss);
const skin = rootVars(layer);
const HEX = /^#[0-9a-f]{3,8}$/i;

describe("arthur-law-cases.css", () => {
  test("redefines every colour of the published palette", () => {
    const colours = [...published].filter(([, v]) => HEX.test(v)).map(([k]) => k);
    expect(colours.length).toBeGreaterThan(10);
    for (const name of colours) expect(skin.has(name), name).toBe(true);
  });

  test("keeps none of the published blues", () => {
    for (const blue of ["--blue", "--blue-d", "--navy", "--sky", "--paper", "--ink", "--line"]) {
      expect(skin.get(blue)?.toLowerCase(), blue).not.toBe(published.get(blue)?.toLowerCase());
    }
    expect(layer.toLowerCase()).not.toContain("#1e5580");
  });

  test("wears arthur.law's palette and type", () => {
    expect(skin.get("--paper")?.toLowerCase()).toBe("#fafaf8");
    expect(skin.get("--ink")?.toLowerCase()).toBe("#0a0a0a");
    expect(skin.get("--mark")?.toLowerCase()).toBe("#ffd400");
    expect(skin.get("--accent")).toBe("var(--ink)");
    expect(skin.get("--sans")).toMatch(/^"Libre Franklin"/);
    expect(skin.get("--mono")).toMatch(/^"Roboto Mono"/);
  });

  test("is only a :root layer, so the rules stay cases.css's", () => {
    const rules = layer.replace(/\/\*[\s\S]*?\*\//g, "").match(/[^{}]+\{/g) ?? [];
    expect(rules.map((r) => r.trim().replace(/\s*\{$/, ""))).toEqual([":root"]);
  });
});
