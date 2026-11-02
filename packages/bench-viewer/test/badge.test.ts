import { describe, expect, test } from "vitest";
import { renderBadge, renderLegend } from "../src/index.ts";
import { fixture } from "./fixture.ts";

describe("renderBadge", () => {
  test("shows the scores version and generation date", () => {
    const html = renderBadge(fixture);

    expect(html).toContain(`bench ${fixture.version}`);
    expect(html).toContain(`generated ${fixture.generated}`);
  });

  test("uses an explicit tag instead of the scores version", () => {
    const html = renderBadge(fixture, "ndb-v1.2.3");

    expect(html).toContain("bench ndb-v1.2.3");
    expect(html).not.toContain(`bench ${fixture.version}`);
  });
});

describe("renderLegend", () => {
  test("explains the affiliation marker and failed-document score", () => {
    const html = renderLegend();

    expect(html).toContain("†");
    expect(html).toContain("0");
  });
});
