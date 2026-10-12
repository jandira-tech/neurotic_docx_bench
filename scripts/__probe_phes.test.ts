import { it, expect } from "vitest";
it("probe phes", async () => { await import("./prosemirror-headless-editor-server.ts"); expect(1).toBe(1); });
