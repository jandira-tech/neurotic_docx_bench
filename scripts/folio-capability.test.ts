import { describe, expect, it } from "vitest";
import { assessFolioCapabilities } from "./folio-capability.ts";

describe("folio capability assessment", () => {
	it("reports script_redlines + accepted_changes as supported with real adapter evidence", async () => {
		const result = await assessFolioCapabilities();
		// accepted_changes: proven (FolioDocxReviewer.acceptAll + toBuffer).
		expect(result.accepted_changes.status).toBe("supported");
		expect(result.accepted_changes.api).toContain("FolioDocxReviewer.toBuffer");
		// script_redlines: proven by the loadEngine 'folio' adapter, which since
		// folio-core 0.13.0 is a single native call — the catalog must not claim
		// harness-composed APIs the adapter no longer uses.
		expect(result.script_redlines.status).toBe("supported");
		expect(result.script_redlines.api).toEqual([
			"@stll/folio-core/server.generateRedlineDocx",
		]);
	});

	it("marks roundtrip + visual_* as needs-adapter until a real harness proves them", async () => {
		const result = await assessFolioCapabilities();
		// No adapter in this repo drives these end-to-end yet.
		expect(result.roundtrip.status).toBe("needs-adapter");
		expect(result.visual_rendering.status).toBe("needs-adapter");
		expect(result.visual_redlines.status).toBe("needs-adapter");
		expect(result.visual_accepted_changes.status).toBe("needs-adapter");
	});

	it("covers all six benchmark names with a legal status + non-empty api/evidence", async () => {
		const result = await assessFolioCapabilities();
		for (const key of [
			"accepted_changes",
			"script_redlines",
			"roundtrip",
			"visual_rendering",
			"visual_redlines",
			"visual_accepted_changes",
		] as const) {
			expect(result[key]).toBeDefined();
			// status must be one of the three legal values (this is NOT a tautology —
			// it guards against a future typo like "supproted").
			expect(["supported", "unsupported", "needs-adapter"]).toContain(
				result[key].status,
			);
			expect(Array.isArray(result[key].api)).toBe(true);
			expect(result[key].api.length).toBeGreaterThan(0);
			expect(typeof result[key].evidence).toBe("string");
			expect(result[key].evidence.length).toBeGreaterThan(0);
		}
	});
});
