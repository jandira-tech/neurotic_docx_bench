import { it, expect } from "vitest";
import { parseManifest } from "./generate-native-redlines.ts";
it("s2 main", () => { expect(typeof parseManifest).toBe("function"); });
