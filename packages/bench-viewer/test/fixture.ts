import { readFileSync } from "node:fs";
import type { Scores } from "../src/types.ts";

// The original fixture stays sanitized with typographic apostrophes so it can
// be compared directly with jubarte's byte-for-byte golden output. The raw
// fixture is extracted from jubarte's bench.* facts and keeps its ASCII
// apostrophes; its parity test covers the documented escaping difference.
export const fixture = JSON.parse(
  readFileSync(new URL("./fixtures/scores.json", import.meta.url), "utf8"),
) as Scores;

export const rawFixture = JSON.parse(
  readFileSync(new URL("./fixtures/scores-raw.json", import.meta.url), "utf8"),
) as Scores;
