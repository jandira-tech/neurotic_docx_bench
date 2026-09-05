//! Batch scorer for the `docxide_metrics` benchmark track.
//!
//! Reads a JSON job list on stdin (or from a file), and for each job rasterizes the
//! oracle and candidate PDFs at docxide-pdf's own 150 DPI, scores them with the
//! upstream metric code in `metrics.rs` / `text_boundary.rs`, then **deletes the
//! rasters before moving on**. Peak disk cost is therefore one document's pages per
//! worker, not the whole corpus — AGENTS.md requires rasters be dropped as scoring
//! proceeds so a sweep cannot fill the disk.
//!
//! Per-page Jaccard and SSIM are averaged over the pages both PDFs have, exactly as
//! upstream's `tools/src/bin/page_metrics.rs` does it. Documents that render to a
//! different page count are still scored over `min(pages)`; `ref_pages`/`pages` are
//! reported so the caller can see the mismatch.
//!
//! Usage:
//!   docxide-metrics --jobs <jobs.json> --scratch <dir> [--workers N] --out <out.json>
//!
//! jobs.json: [{"stem": "...", "oracle": "/abs/a.pdf", "candidate": "/abs/b.pdf"}, ...]
//! A job whose candidate is missing is reported with `"converted": false` and no
//! scores; the caller decides how to treat it (this track scores it 0, intent-to-treat).
mod metrics;
#[allow(dead_code)]
mod text_boundary;

use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};

#[derive(Deserialize)]
struct Job {
    stem: String,
    oracle: PathBuf,
    candidate: PathBuf,
}

#[derive(Serialize)]
struct Score {
    stem: String,
    converted: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    jaccard: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    ssim: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    text_boundary: Option<f64>,
    ref_pages: usize,
    pages: usize,
    scored_pages: usize,
    max_break_drift: i64,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<String>,
}

fn missing(stem: &str, why: &str) -> Score {
    Score {
        stem: stem.to_string(),
        converted: false,
        jaccard: None,
        ssim: None,
        text_boundary: None,
        ref_pages: 0,
        pages: 0,
        scored_pages: 0,
        max_break_drift: 0,
        error: Some(why.to_string()),
    }
}

fn score_one(job: &Job, scratch: &Path) -> Score {
    if !job.candidate.is_file() {
        return missing(&job.stem, "candidate PDF missing (convert failure)");
    }
    if !job.oracle.is_file() {
        return missing(&job.stem, "oracle PDF missing");
    }
    let work = scratch.join(&job.stem);
    let ref_dir = work.join("oracle");
    let cand_dir = work.join("candidate");
    let _ = std::fs::remove_dir_all(&work);

    let raster = |pdf: &Path, dir: &Path| metrics::screenshot_pdf(pdf, dir);
    let outcome = raster(&job.oracle, &ref_dir).and_then(|()| raster(&job.candidate, &cand_dir));
    if let Err(e) = outcome {
        let _ = std::fs::remove_dir_all(&work);
        // A candidate that mutool cannot rasterize is a real PDF that does not render;
        // that is a scoring failure, not a convert failure, so `converted` stays true.
        return Score {
            converted: true,
            ..missing(&job.stem, &format!("rasterize failed: {e}"))
        };
    }

    let ref_pngs = metrics::collect_page_pngs(&ref_dir).unwrap_or_default();
    let cand_pngs = metrics::collect_page_pngs(&cand_dir).unwrap_or_default();
    let n = ref_pngs.len().min(cand_pngs.len());
    let pages: Vec<(f64, f64)> = (0..n)
        .into_par_iter()
        .filter_map(|i| {
            let a = image::open(&ref_pngs[i]).ok()?;
            let b = image::open(&cand_pngs[i]).ok()?;
            let jaccard = metrics::compare_and_diff(&a, &b).ok()?.jaccard;
            let ssim = metrics::ssim_score(&a, &b).ok()?;
            Some((jaccard, ssim))
        })
        .collect();
    let mean = |pick: fn(&(f64, f64)) -> f64| {
        (!pages.is_empty()).then(|| pages.iter().map(pick).sum::<f64>() / pages.len() as f64)
    };
    let tb = text_boundary::analyze(&job.oracle, &job.candidate);

    let score = Score {
        stem: job.stem.clone(),
        converted: true,
        jaccard: mean(|p| p.0),
        ssim: mean(|p| p.1),
        text_boundary: (tb.total_lines > 0).then(|| tb.line_match_pct()),
        ref_pages: ref_pngs.len(),
        pages: cand_pngs.len(),
        scored_pages: pages.len(),
        max_break_drift: tb.max_break_drift,
        error: None,
    };
    // Drop this document's rasters before the next one starts.
    let _ = std::fs::remove_dir_all(&work);
    score
}

fn arg(args: &[String], flag: &str) -> Option<String> {
    args.iter().position(|a| a == flag).and_then(|i| args.get(i + 1)).cloned()
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let (Some(jobs_path), Some(scratch), Some(out)) = (
        arg(&args, "--jobs"),
        arg(&args, "--scratch"),
        arg(&args, "--out"),
    ) else {
        eprintln!("usage: docxide-metrics --jobs <jobs.json> --scratch <dir> --out <out.json> [--workers N]");
        std::process::exit(2);
    };
    let workers: usize = arg(&args, "--workers").and_then(|v| v.parse().ok()).unwrap_or(4);
    rayon::ThreadPoolBuilder::new()
        .num_threads(workers.max(1))
        .build_global()
        .expect("failed to build rayon pool");

    let text = std::fs::read_to_string(&jobs_path).expect("cannot read job list");
    let jobs: Vec<Job> = serde_json::from_str(&text).expect("job list is not valid JSON");
    let scratch = PathBuf::from(scratch);
    std::fs::create_dir_all(&scratch).expect("cannot create scratch dir");

    let total = jobs.len();
    let done = AtomicUsize::new(0);
    let mut scores: Vec<Score> = jobs
        .par_iter()
        .map(|job| {
            let s = score_one(job, &scratch);
            let n = done.fetch_add(1, Ordering::Relaxed) + 1;
            if n == total || n % 10 == 0 {
                eprintln!("docxide-metrics scored {n}/{total}");
            }
            s
        })
        .collect();
    scores.sort_by(|a, b| a.stem.cmp(&b.stem));

    let json = serde_json::to_string_pretty(&scores).expect("serialize");
    std::fs::write(&out, json + "\n").expect("cannot write output");
    let _ = std::fs::remove_dir_all(&scratch);
    eprintln!("wrote {out}");
}
