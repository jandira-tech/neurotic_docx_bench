// SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
// SPDX-License-Identifier: AGPL-3.0-only
//! Warm docx->pdf worker: `d2p-warm <tool>` stays alive and converts one
//! `src\tdst` line from stdin at a time, answering `ok <ms>` or
//! `err <ms> <message>` on stdout. Each sample times reading the docx,
//! converting and writing the PDF, with the same library calls and options
//! the tool's CLI makes; process start and one-time initialisation (fonts,
//! caches) are paid once, as by a long-lived service.
//!
//! Built once per tool: `cargo build --release --features <tool>`, the
//! binary copied to `d2p-warm-<tool>`.
//!
//! A panic answers `err`; the driver kills and respawns a worker that runs
//! past its timeout.

use std::io::{BufRead, Write};
use std::path::Path;
use std::time::Instant;

type Convert = fn(&Path, &Path) -> Result<(), String>;

#[cfg(feature = "jubarte")]
fn jubarte(src: &Path, dst: &Path) -> Result<(), String> {
    let bytes = std::fs::read(src).map_err(|e| e.to_string())?;
    // `jubarte convert --revisions word` without `--compress`.
    let options = jubarte::convert::PdfOptions {
        compress: false,
        revisions: jubarte::convert::RevisionStyle::Word,
    };
    let pdf = jubarte::convert::docx_to_pdf_with(&bytes, options).map_err(|e| e.to_string())?;
    std::fs::write(dst, pdf).map_err(|e| e.to_string())
}

#[cfg(feature = "docxide")]
fn docxide(src: &Path, dst: &Path) -> Result<(), String> {
    // `docxide-pdf SRC DST`.
    docxide_pdf::convert_docx_to_pdf(src, dst).map_err(|e| e.to_string())
}

#[cfg(feature = "rdocx")]
fn rdocx(src: &Path, dst: &Path) -> Result<(), String> {
    // `rdocx convert --to pdf -o DST SRC`.
    let doc = rdocx::Document::open(src).map_err(|e| e.to_string())?;
    let pdf = doc.to_pdf().map_err(|e| e.to_string())?;
    std::fs::write(dst, pdf).map_err(|e| e.to_string())
}

#[cfg(feature = "office2pdf")]
fn office2pdf(src: &Path, dst: &Path) -> Result<(), String> {
    // `office2pdf -o DST SRC`.
    let bytes = std::fs::read(src).map_err(|e| e.to_string())?;
    let result = office2pdf::convert_bytes(
        &bytes,
        office2pdf::config::Format::Docx,
        &office2pdf::config::ConvertOptions::default(),
    )
    .map_err(|e| e.to_string())?;
    std::fs::write(dst, result.pdf).map_err(|e| e.to_string())
}

fn main() {
    let tool = std::env::args().nth(1).unwrap_or_default();
    let convert: Convert = match tool.as_str() {
        #[cfg(feature = "jubarte")]
        "jubarte" => jubarte,
        #[cfg(feature = "docxide")]
        "docxide" => docxide,
        #[cfg(feature = "rdocx")]
        "rdocx" => rdocx,
        #[cfg(feature = "office2pdf")]
        "office2pdf" => office2pdf,
        _ => {
            eprintln!("usage: d2p-warm <tool built in>");
            std::process::exit(2);
        }
    };
    // Library panics are answered as `err`, not printed over the protocol.
    std::panic::set_hook(Box::new(|_| {}));
    let stdout = std::io::stdout();
    for line in std::io::stdin().lock().lines() {
        let Ok(line) = line else { break };
        let Some((src, dst)) = line.split_once('\t') else {
            continue;
        };
        let (src, dst) = (Path::new(src), Path::new(dst));
        let t0 = Instant::now();
        let outcome = std::panic::catch_unwind(|| convert(src, dst))
            .unwrap_or_else(|_| Err("panic".to_string()));
        let ms = t0.elapsed().as_secs_f64() * 1000.0;
        let mut out = stdout.lock();
        let _ = match outcome {
            Ok(()) => writeln!(out, "ok {ms:.3}"),
            Err(e) => writeln!(out, "err {ms:.3} {}", e.replace(['\n', '\r'], " ")),
        };
        let _ = out.flush();
    }
}
