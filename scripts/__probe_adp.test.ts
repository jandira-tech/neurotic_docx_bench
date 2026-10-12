import { it, expect } from "vitest";
it("probe adapter", async () => { await import("./jubarte-lossless-adapter.mjs"); expect(1).toBe(1); });
