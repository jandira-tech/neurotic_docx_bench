-- SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
-- SPDX-License-Identifier: AGPL-3.0-only
CREATE TABLE IF NOT EXISTS bench_runs (
  id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bench_live (
  singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
  run_id TEXT NOT NULL REFERENCES bench_runs(id),
  sequence INTEGER NOT NULL,
  updated_at TEXT NOT NULL,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bench_results (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES bench_runs(id),
  sequence INTEGER NOT NULL,
  batch_id TEXT NOT NULL,
  completed_at TEXT NOT NULL,
  payload TEXT NOT NULL,
  UNIQUE (run_id, sequence)
);
CREATE INDEX IF NOT EXISTS bench_results_history ON bench_results(run_id, sequence DESC);
CREATE INDEX IF NOT EXISTS bench_results_batch ON bench_results(run_id, batch_id, sequence);
CREATE INDEX IF NOT EXISTS bench_results_global_history ON bench_results(completed_at DESC, id DESC);
CREATE TABLE IF NOT EXISTS bench_scores (
  result_id TEXT NOT NULL REFERENCES bench_results(id),
  run_id TEXT NOT NULL,
  tool TEXT NOT NULL,
  benchmark TEXT NOT NULL,
  reference_tool TEXT,
  reference_renderer TEXT,
  status TEXT NOT NULL,
  overall REAL,
  PRIMARY KEY (result_id, tool, benchmark)
);
CREATE INDEX IF NOT EXISTS bench_scores_cohort ON bench_scores(run_id, tool, benchmark, reference_tool, reference_renderer);
CREATE TABLE IF NOT EXISTS bench_batches (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES bench_runs(id),
  last_sequence INTEGER NOT NULL,
  completed_at TEXT NOT NULL,
  payload TEXT NOT NULL,
  UNIQUE (run_id, last_sequence)
);
