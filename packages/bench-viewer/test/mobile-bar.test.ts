// #157: the four mobile buttons stay at the bottom of the viewport.
import { readFile } from "node:fs/promises";
import { describe, expect, test } from "vitest";

const css = await readFile(new URL("../themes/cases.css", import.meta.url), "utf8");

/** The declarations of every rule whose selector list is exactly `selector`. */
function rule(selector: string): string {
  const re = new RegExp(
    `(^|\\})\\s*${selector.replace(/[.#*+?^${}()|[\]\\]/g, "\\$&")}\\s*\\{([^}]*)\\}`,
    "g",
  );
  return [...css.matchAll(re)].map((m) => m[2]).join(";");
}

describe("the mobile bottom bar (#157)", () => {
  test("is fixed to the bottom of the viewport", () => {
    const d = rule("body.mobile #mfoot");
    expect(d).toMatch(/position:\s*fixed/);
    expect(d).toMatch(/bottom:\s*0/);
    expect(d).toMatch(/left:\s*0/);
    expect(d).toMatch(/right:\s*0/);
  });

  test("the case area reserves room for it, safe area included", () => {
    expect(rule("body.mobile #main")).toMatch(
      /padding-bottom:\s*calc\([^)]*var\(--mfoot-h\)[^;]*safe-area-inset-bottom/,
    );
  });

  test("the mobile page uses the dynamic viewport height", () => {
    expect(rule("body.mobile")).toMatch(/height:\s*100dvh/);
  });

  test("the case drawer and its scrim sit above the bar", () => {
    const bar = Number(/z-index:\s*(\d+)/.exec(rule("body.mobile #mfoot"))?.[1] ?? Number.NaN);
    const drawer = Number(/z-index:\s*(\d+)/.exec(rule("body.mobile #side"))?.[1] ?? Number.NaN);
    expect(bar).toBeGreaterThan(0);
    expect(drawer).toBeGreaterThan(bar);
  });
});
