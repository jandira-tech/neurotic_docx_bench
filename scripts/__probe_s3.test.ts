import { it, expect } from "vitest";
import { resolveDocxodusEntry } from "./docxodus-node-compat.mjs";
it("s3 compat", () => { expect(typeof resolveDocxodusEntry).toBe("function"); });
