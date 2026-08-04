#!/usr/bin/env bun
/**
 * Folio capability catalog (Task 8).
 *
 * This is a STATIC catalog, not a live probe: it documents which folio
 * capabilities are proven (and where the proof lives), so downstream code and
 * reviewers can see at a glance what is backed by a real adapter vs what is
 * aspirational. It does NOT import or call @stll/folio-* itself; the evidence
 * for each "supported" entry points at the adapter that exercises the API.
 *
 * script_redlines: proven by scripts/generate-native-redlines.ts:loadEngine
 *   'folio' (generateRedlineDocx → w:ins/w:del). Since folio-core 0.13.0 this is a
 *   single native call, so nothing in the scored bytes is harness composition;
 *   see docs/FOLIO.md "Harness-assisted disclosure".
 * accepted_changes: proven by FolioDocxReviewer.acceptAll + toBuffer.
 * roundtrip / visual_*: the API exists but NO adapter in this repo drives them
 *   end-to-end yet, so they are marked "needs-adapter" until a spike proves them.
 *
 * Usage: bun run scripts/folio-capability.ts
 * Output: JSON report to stdout.
 */

export type CapabilityStatus = "supported" | "unsupported" | "needs-adapter";
export type Capability = {
	status: CapabilityStatus;
	api: string[];
	evidence: string;
};

export type FolioCapabilityReport = {
	accepted_changes: Capability;
	script_redlines: Capability;
	roundtrip: Capability;
	visual_rendering: Capability;
	visual_redlines: Capability;
	visual_accepted_changes: Capability;
};

/** Static catalog of folio capabilities (see module docstring). */
export async function assessFolioCapabilities(): Promise<FolioCapabilityReport> {
	return {
		accepted_changes: {
			status: "supported",
			api: [
				"@stll/folio-core/server.FolioDocxReviewer.acceptAll",
				"FolioDocxReviewer.toBuffer",
			],
			evidence:
				"headless reviewer exposes acceptAll() and serialises via toBuffer()",
		},
		script_redlines: {
			status: "supported",
			api: ["@stll/folio-core/server.generateRedlineDocx"],
			evidence:
				"generateRedlineDocx(base, next, {author}) returns the base package with tracked " +
				"changes across every matched story — a single native call, no harness-side diff " +
				"translation. Verified emitting w:ins/w:del on 59 of the first 60 corpus pairs with " +
				"0 generate failures (the 60th is folio reporting zero changes for itself); " +
				"scripts/generate-native-redlines.ts:loadEngine 'folio'. The pre-0.15 composition " +
				"(compareDocxVersions + FolioDocxReviewer.applyOperations) dropped every modified " +
				"block — see docs/FOLIO.md.",
		},
		roundtrip: {
			status: "needs-adapter",
			api: ["FolioDocxReviewer.fromBuffer", "FolioDocxReviewer.toBuffer"],
			evidence:
				"headless parse/save path exists, but no roundtrip adapter in this repo drives it end-to-end yet",
		},
		visual_rendering: {
			status: "needs-adapter",
			api: ["@stll/folio-react.renderAsync"],
			evidence:
				"official imperative React renderer exists, but no playwright harness wires it for the bench yet",
		},
		visual_redlines: {
			status: "needs-adapter",
			api: ["@stll/folio-react.renderAsync"],
			evidence:
				"renderer can load Word redline DOCX, but no playwright harness wires it yet",
		},
		visual_accepted_changes: {
			status: "needs-adapter",
			api: ["@stll/folio-react.renderAsync"],
			evidence:
				"renderer can load accepted DOCX, but no playwright harness wires it yet",
		},
	};
}

// Self-executing when run directly
const isMain = import.meta.main;
if (isMain) {
	const report = await assessFolioCapabilities();
	console.log(JSON.stringify(report, null, 2));
}
