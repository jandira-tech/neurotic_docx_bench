/// <reference types="vite/client" />
import { useState, useRef, useEffect, useCallback } from "react";
import { createRoot } from "react-dom/client";
import { DocumentViewer } from "../src";
import type { DocumentViewerProps } from "../src";
import "../src/styles/DocumentViewer.css";
import { normalizeDocxForViewer } from "./normalize-docx";

const WASM_BASE_PATH = import.meta.env.BASE_URL + "wasm/";

declare global {
	interface Window {
		__rdvReady: boolean;
		__rdvDocumentReady: boolean;
		__rdvError: string;
		__rdvPageCount: number;
		/** True when laid-out pages contain text or media (not white chrome only). */
		__rdvHasContent: boolean;
		__rdvHarnessInit: boolean;
		__rdvCheckReady: () => boolean;
	}
}

function pagesHaveContent(pages: NodeListOf<HTMLElement>): boolean {
	for (const el of pages) {
		if ((el.innerText || "").trim().length > 0) return true;
		if (el.querySelector("img, svg, canvas, table, video")) return true;
	}
	return false;
}

function pagesLaidOut(): { ready: boolean; count: number; hasContent: boolean } {
	const pages = document.querySelectorAll<HTMLElement>("[data-page-number]");
	if (pages.length === 0) return { ready: false, count: 0, hasContent: false };
	// Require a real layout box so Playwright's "visible" wait can succeed
	// and page.pdf() is not printing empty cards mid-pagination.
	for (const el of pages) {
		const r = el.getBoundingClientRect();
		if (r.width < 50 || r.height < 50) {
			return { ready: false, count: pages.length, hasContent: false };
		}
	}
	return {
		ready: true,
		count: pages.length,
		hasContent: pagesHaveContent(pages),
	};
}

/**
 * Harness entry: DocumentViewer configured for headless PDF capture.
 *
 * Signals readiness via window globals:
 *   window.__rdvReady         — viewer shell mounted
 *   window.__rdvDocumentReady — DOCX converted + pages laid out (non-zero boxes)
 *   window.__rdvError         — last error message (empty if OK)
 *   window.__rdvPageCount     — number of [data-page-number] nodes when ready
 */
function HarnessApp() {
	const [file, setFile] = useState<File | null>(null);
	const readyPollRef = useRef<number | null>(null);

	useEffect(() => {
		window.__rdvReady = true;
		window.__rdvDocumentReady = false;
		window.__rdvError = "";
		window.__rdvPageCount = 0;
		window.__rdvHasContent = false;
	}, []);

	// DocumentViewer surfaces WASM/worker init failures only in the DOM
	// (`.rdv-message--error`), not via onError. Mirror them onto __rdvError so
	// Playwright fail-fasts instead of burning the full readiness timeout.
	useEffect(() => {
		const tick = () => {
			if (window.__rdvError) return;
			const el = document.querySelector(".rdv-message--error");
			const text = el?.textContent?.trim();
			if (text) {
				window.__rdvError = text;
				console.error("[harness] viewer init error:", text);
			}
		};
		const id = window.setInterval(tick, 200);
		return () => window.clearInterval(id);
	}, []);

	const stopReadyPoll = useCallback(() => {
		if (readyPollRef.current !== null) {
			window.clearInterval(readyPollRef.current);
			readyPollRef.current = null;
		}
	}, []);

	const startReadyPoll = useCallback(() => {
		stopReadyPoll();
		window.__rdvDocumentReady = false;
		window.__rdvHasContent = false;
		const started = Date.now();
		readyPollRef.current = window.setInterval(() => {
			// Conversion already failed — stop polling; Playwright should read __rdvError.
			if (window.__rdvError) {
				stopReadyPoll();
				return;
			}
			const { ready, count, hasContent } = pagesLaidOut();
			if (ready) {
				window.__rdvPageCount = count;
				window.__rdvHasContent = hasContent;
				// One rAF so fonts/paints settle after layout.
				requestAnimationFrame(() => {
					window.__rdvDocumentReady = true;
				});
				stopReadyPoll();
				return;
			}
			// Surface layout-timeout as an explicit error so Playwright fail-fasts
			// with a useful message instead of a generic selector TimeoutError.
			if (Date.now() - started > 55_000) {
				if (!window.__rdvError) {
					window.__rdvError =
						`layout timeout: ${count} page node(s) never reached non-zero boxes`;
				}
				stopReadyPoll();
			}
		}, 100);
	}, [stopReadyPoll]);

	useEffect(() => () => stopReadyPoll(), [stopReadyPoll]);

	const handleFileChange = useCallback((e: Event) => {
		const input = e.target as HTMLInputElement;
		const selectedFile = input.files?.[0];
		if (!selectedFile) return;

		// Reset readiness immediately so Playwright doesn't race a previous doc.
		window.__rdvDocumentReady = false;
		window.__rdvError = "";
		window.__rdvPageCount = 0;
		window.__rdvHasContent = false;

		// Inject missing optional package parts (settings/styles/theme/fontTable)
		// before the WASM converter sees the file. See normalize-docx.ts.
		void normalizeDocxForViewer(selectedFile)
			.then((normalized) => {
				setFile(normalized);
			})
			.catch((err) => {
				const message =
					err instanceof Error ? err.message : String(err);
				window.__rdvError = `normalize failed: ${message}`;
				console.error("[harness] normalize failed:", err);
				// Fall back to the raw upload so the viewer can still try.
				setFile(selectedFile);
			});
	}, []);

	useEffect(() => {
		const input = document.getElementById("fileInput");
		if (!input) return;
		input.addEventListener("change", handleFileChange);
		return () => input.removeEventListener("change", handleFileChange);
	}, [handleFileChange]);

	const onError = useCallback((err: Error) => {
		window.__rdvError = err.message;
		window.__rdvDocumentReady = false;
		console.error("[harness] viewer error:", err);
	}, []);

	const onConversionComplete = useCallback(
		(_html: string) => {
			// Conversion finished; PaginatedDocument still has to flow pages.
			// Poll for real laid-out page boxes instead of a fixed 500ms delay
			// (which raced pagination on multi-page / WASM-heavy docs).
			startReadyPoll();
		},
		[startReadyPoll],
	);

	const viewerSettings: Partial<DocumentViewerProps["settings"]> = {
		renderTrackedChanges: true,
		showDeletedContent: true,
		renderMoveOperations: true,
		showPageNumbers: false,
		// 1.0 = native page pt size (612×792 for Letter) → matches LO letter PDFs.
		paginationScale: 1.0,
		// Keep footnotes/endnotes in-page where the converter puts them; the
		// default endnote chrome panel is not part of the Word/LO oracle.
		renderFootnotesAndEndnotes: true,
		renderHeadersAndFooters: true,
		commentMode: "disabled",
	};

	return (
		<DocumentViewer
			file={file}
			wasmBasePath={WASM_BASE_PATH}
			toolbar="none"
			showSettingsButton={false}
			showRevisionsTab={false}
			onError={onError}
			onConversionComplete={onConversionComplete}
			settings={viewerSettings}
			useWorker={true}
			warmup={false}
			fitMode="manual"
			placeholder="Harness ready — upload a DOCX via #fileInput"
		/>
	);
}

window.__rdvCheckReady = (): boolean => pagesLaidOut().ready;

createRoot(document.getElementById("root")!).render(<HarnessApp />);

window.__rdvHarnessInit = true;
