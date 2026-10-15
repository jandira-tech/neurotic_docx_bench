import { it, expect } from "vitest";
it("probe main module import", async () => { await import("./generate-native-redlines.ts"); expect(1).toBe(1); });
