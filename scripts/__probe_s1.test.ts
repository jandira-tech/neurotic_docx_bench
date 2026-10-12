import { it, expect } from "vitest";
import JSZip from "../node_modules/jszip/lib/index.js";
it("s1 jszip", () => { expect(typeof JSZip.loadAsync).toBe("function"); });
