# Redline speed run, notes

## Run of 2026-09-29 (00:45 to 09:23 EDT)

- jubarte-rust-inproc, jubarte-rust (CLI) and jubarte-wasm ran all 10,000 planned pairs with no
  failures (jubarte-redlines 0.9.3 @673aff74, same commit for all three lanes).
- docxodus (npm 12.6.4, .NET WASM) started at 01:35 and had finished 1,335 pairs (p00000 to
  p01334, all `word_compare`) when the run was stopped at 09:23. The harness then had no per-pair
  timeout and wrote per-pair rows only at the end of a lane, so nothing had been written.
- It was not hung. Single pairs took up to 7,162 s (p01320), 3,212 s (p01235) and 2,242 s
  (p01122). 21 of the 1,335 pairs took more than 120 s, and together they account for about
  18,600 of the 21,700 s the lane had used. Pair p01335 (base 491 KB, next 232 KB) had been
  running for more than an hour when the run was stopped.
- The 1,335 timings were read from the live process through the Node inspector (SIGUSR1, then
  `Runtime.queryObjects` over live arrays to find the lane's `samples`, `sampleKeys` and
  `outSizes`). The keys are contiguous from p00000 to p01334, so no pair in that range failed.
- `per_pair/docxodus.jsonl` holds them with `"source": "salvaged"`. The 120 s per-pair timeout
  now used by every lane is applied to them after the fact: the 21 slower pairs are rows with
  `ok: false`, `timeout: true`, `ms: 120000` and their real time in `measured_ms`.
- SuperDoc and the rest of docxodus (from p01335, with the per-pair timeout) are run separately.

## Load

The machine was shared: two `1-ce-5` Python processes at 100% CPU for the whole run and bursts
of another session's Rust builds (see ENV.txt). The lanes ran one after another, so each saw
the same background.
