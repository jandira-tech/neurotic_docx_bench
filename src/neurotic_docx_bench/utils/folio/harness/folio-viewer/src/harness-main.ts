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

/**
 * Resolve when the paginated output has stopped changing.
 *
 * We cannot use renderAsync's own promise as the readiness signal. It resolves
 * on the editor's first `onChange` (see its doc comment), and as of
 * @stll/folio-react 0.13.2 loading a document no longer fires `onChange` — the
 * document renders correctly but the promise never settles. Verified on 0.13.2
 * with Playwright: `.layout-page` is present and populated while
 * `renderAsync` is still pending, with no error and no rejection.
 *
 * So readiness is measured from the DOM instead, which is what the PDF capture
 * actually depends on: at least one `.layout-page`, and a page count + rendered
 * text length that hold steady across consecutive polls. The stability window
 * matters because folio paginates incrementally — the first `.layout-page`
 * appears well before the last one does, and bench.yaml's `readiness_js`
 * fallback (`.layout-page` count > 0) would otherwise let Playwright capture a
 * partially paginated document.
 */
function waitForStablePagination(
	timeoutMs: number,
	quietMs = 400,
	pollMs = 100,
): Promise<void> {
	return new Promise((resolve, reject) => {
		const started = Date.now();
		let lastSignature = "";
		let stableSince = 0;
		const tick = () => {
			const pages = host.querySelectorAll(".layout-page");
			// Text length is a cheap proxy for "content settled"; page count alone
			// goes stable between incremental pagination passes.
			const signature = `${pages.length}:${host.textContent?.length ?? 0}`;
			if (pages.length > 0 && signature === lastSignature) {
				if (stableSince === 0) stableSince = Date.now();
				if (Date.now() - stableSince >= quietMs) {
					resolve();
					return;
				}
			} else {
				lastSignature = signature;
				stableSince = 0;
			}
			if (Date.now() - started > timeoutMs) {
				reject(
					new Error(
						`pagination did not stabilise in ${timeoutMs}ms (last signature ${signature})`,
					),
				);
				return;
			}
			setTimeout(tick, pollMs);
		};
		tick();
	});
}

async function loadDocx(file: File): Promise<void> {
	window.__folioReady = false;
	window.__folioError = "";
	// Clear any previously rendered editor so re-renders don't accumulate.
	host.innerHTML = "";
	try {
		const buf = await file.arrayBuffer();
		// renderAsync mounts the full editor (paginated) into #host. readOnly +
		// mode:"viewing" + toolbar off = a clean capture surface that still renders
		// tracked-change markup. We deliberately do NOT await it (see
		// waitForStablePagination) — but we do keep its rejection, which is the only
		// channel folio reports a parse/mount failure through.
		let renderFailed: Error | null = null;
		void renderAsync(buf, host, {
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
		}).catch((e: unknown) => {
			renderFailed = e instanceof Error ? e : new Error(String(e));
		});

		await waitForStablePagination(60_000);
		if (renderFailed) throw renderFailed;
		window.__folioReady = true;
	} catch (e: any) {
		window.__folioError = e?.message ?? String(e);
		console.error("[folio harness] render failed:", e);
	}
}

fileInput.addEventListener("change", async () => {
	const f = fileInput.files?.[0];
	if (f) await loadDocx(f);
});

// Signal that the harness script itself loaded (distinct from doc-ready).
(window as any).__folioHarnessInit = true;
