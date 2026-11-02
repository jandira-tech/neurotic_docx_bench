import { readFile } from "node:fs/promises";
import { describe, expect, test } from "vitest";

const jubarteCss = await readFile(new URL("../themes/jubarte.css", import.meta.url), "utf8");
const arthurLawCss = await readFile(new URL("../themes/arthur-law.css", import.meta.url), "utf8");

describe("themes", () => {
  test("jubarte keeps the site's light and dark palette values", () => {
    expect(jubarteCss).toContain("color-scheme: light dark;");
    expect(jubarteCss).toContain("--bg: light-dark(oklch(97% 0.003 106.4), oklch(20% 0.023 249));");
    expect(jubarteCss).toContain("--ink: light-dark(oklch(18.2% 0 0), oklch(96.2% 0.008 241.7));");
    expect(jubarteCss).toContain(
      "--primary: light-dark(oklch(21.8% 0 0), oklch(79.1% 0.094 237.6));",
    );
    expect(jubarteCss).toContain(
      "--line: light-dark(oklch(87.5% 0.005 106.5), oklch(33.4% 0.039 250.5));",
    );
    expect(jubarteCss).toContain(
      "--line-strong: light-dark(oklch(73.3% 0.007 106.6), oklch(43.6% 0.043 246.4));",
    );
    expect(jubarteCss).toContain(
      "--surface: light-dark(oklch(94.2% 0.004 106.5), oklch(23.9% 0.026 249));",
    );
    expect(jubarteCss).toContain(
      "--hover: light-dark(oklch(92.4% 0.005 106.5), oklch(27.1% 0.029 246.9));",
    );
    expect(jubarteCss).toContain(
      "--hl: light-dark(oklch(91.6% 0.128 94.1), oklch(40.5% 0.075 243));",
    );
    expect(jubarteCss).toContain(
      "--hl-soft: light-dark(oklch(96.2% 0.062 95.4), oklch(28.4% 0.046 245.3));",
    );
  });

  test("arthur.law defines the display weight it uses", () => {
    expect(arthurLawCss).toContain("--display-weight: 700;");
  });
});
