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
