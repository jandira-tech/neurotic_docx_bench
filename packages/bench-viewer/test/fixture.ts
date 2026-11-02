import { readFileSync } from "node:fs";
import type { Scores } from "../src/types.ts";

// The current facts use ASCII apostrophes in a few prose fields. The fixture
// normalizes them to the typographic apostrophe already used by jubarte so the
// raw home-page golden and the escaped bench-viewer output remain identical.
export const fixture = JSON.parse(
  readFileSync(new URL("./fixtures/scores.json", import.meta.url), "utf8"),
) as Scores;
