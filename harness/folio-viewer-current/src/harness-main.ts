import { renderAsync } from "@stll/folio-react";
import "@stll/folio-react/standalone.css";

// Readiness contract consumed by the Playwright renderer (see bench.yaml readiness_js):
//   window.__folioReady === true  → document parsed + paginated, ready for page.pdf()
//   window.__folioError          → last error message (empty string when OK)
declare global {
	interface Window {
		__folioReady: boolean;
		__folioError: string;
	}
}

window.__folioReady = false;
window.__folioError = "";

const host = document.getElementById("host")!;
const fileInput = document.getElementById(
	"fileInput",
) as HTMLInputElement | null;
if (!fileInput) {
	throw new Error("harness: #fileInput not found");
}

async function loadDocx(file: File): Promise<void> {
	window.__folioReady = false;
	window.__folioError = "";
	// Clear any previously rendered editor so re-renders don't accumulate.
	host.innerHTML = "";
	try {
		const buf = await file.arrayBuffer();
		// renderAsync mounts the full editor (paginated) into #host and resolves on
		// first onChange = doc parsed + paginated. readOnly + mode:"viewing" + toolbar
		// off = a clean capture surface that still renders tracked-change markup.
		await renderAsync(buf, host, {
			readOnly: true,
			mode: "viewing",
			showToolbar: false,
			showZoomControl: false,
			showReviewControls: false,
			showRuler: false,
			showMarginGuides: false,
			showPrintButton: false,
			showHeaderFooterEditing: false,
			enableWheelZoom: false,
			author: "bench",
		});
		window.__folioReady = true;
	} catch (e: any) {
		window.__folioError = e?.message ?? String(e);
		console.error("[folio harness] renderAsync failed:", e);
	}
}

fileInput.addEventListener("change", async () => {
	const f = fileInput.files?.[0];
	if (f) await loadDocx(f);
});

// Signal that the harness script itself loaded (distinct from doc-ready).
(window as any).__folioHarnessInit = true;
