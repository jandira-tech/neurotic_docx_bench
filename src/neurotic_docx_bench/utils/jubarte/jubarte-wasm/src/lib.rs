//! WebAssembly bindings for the canonical **jubarte-redlines** Word-mode compare.
//!
//! Built with **wasm-pack** + **wasm-opt -O3** (Binaryen) — the standard
//! Rust→browser/Node pipeline that currently produces the fastest practical
//! wasm-bindgen artefacts for pure compute crates.
//!
//! # JS API (Node target)
//!
//! ```js
//! import init, { compareDocuments } from "./pkg/jubarte_wasm.js";
//! await init();
//! const redline = compareDocuments(baseBytes, nextBytes, "jubarte-wasm");
//! // redline: Uint8Array
//! ```
//!
//! # Build
//!
//! ```sh
//! wasm-pack build --target nodejs --release
//! ```

use wasm_bindgen::prelude::*;

/// One-shot init: panic hook → `console.error`. Safe to call multiple times.
#[wasm_bindgen(js_name = initPanicHook)]
pub fn init_panic_hook() {
    #[cfg(feature = "console-panic")]
    console_error_panic_hook::set_once();
}

fn js_err(e: impl std::fmt::Display) -> JsValue {
    JsValue::from_str(&format!("jubarte-wasm: {e}"))
}

/// Compare two DOCX packages (bytes) → redline DOCX bytes (`w:ins`/`w:del`).
///
/// Mirrors `jubarte::document_comparer::compare_documents`.
#[wasm_bindgen(js_name = compareDocuments)]
pub fn compare_documents(
    original: &[u8],
    modified: &[u8],
    author: &str,
) -> Result<Vec<u8>, JsValue> {
    jubarte::document_comparer::compare_documents(original, modified, author).map_err(js_err)
}

/// Accept every tracked revision (package-wide) → clean DOCX bytes.
///
/// Mirrors `jubarte::document_comparer::accept_revisions`.
#[wasm_bindgen(js_name = acceptRevisions)]
pub fn accept_revisions(docx: &[u8]) -> Result<Vec<u8>, JsValue> {
    jubarte::document_comparer::accept_revisions(docx).map_err(js_err)
}

/// Reject every tracked revision (package-wide) → base DOCX bytes.
///
/// Mirrors `jubarte::document_comparer::reject_revisions`.
#[wasm_bindgen(js_name = rejectRevisions)]
pub fn reject_revisions(docx: &[u8]) -> Result<Vec<u8>, JsValue> {
    jubarte::document_comparer::reject_revisions(docx).map_err(js_err)
}

/// List the tracked revisions in a DOCX as a JSON array string — the same
/// object shape as the CLI `jubarte revisions --json` lines
/// (`type`/`author`/`date`/`part`/`moveGroupId`/`isMoveSource`/`formatChange`/`text`).
///
/// Mirrors `jubarte::document_comparer::get_revisions` with default settings,
/// serialized by the shared `revisions_to_json`.
#[wasm_bindgen(js_name = getRevisions)]
pub fn get_revisions(docx: &[u8]) -> Result<String, JsValue> {
    let settings = jubarte::comparer::WmlComparerSettings::default();
    let revs = jubarte::document_comparer::get_revisions(docx, &settings).map_err(js_err)?;
    Ok(jubarte::document_comparer::revisions_to_json(&revs))
}
