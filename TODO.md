# TODO — neurotic_docx_bench

Findings from the 2026-07-17 folio×jubarte demo session.

## 1. WV-1 word-validate cannot judge large documents (HIGH)

`bench word-validate` infers "repair dialog" from an AppleScript timeout —
but Word takes longer than the AppleEvent reply window just to OPEN a
~1000-page dissertation, so big documents fail with `AppleEvent timed out
(-1712)` regardless of validity (the ORIGINAL, known-Word-valid dissertation
"fails" identically; even a manual `with timeout of 600 seconds` open did not
complete in 10 minutes). Timeout ≠ dialog at this size, and a timed-out
`open` can leave Word holding the document with no cleanup.

- [ ] Distinguish dialog-vs-slow: detect an actual modal (sheet/dialog window
  via System Events) instead of inferring from silence.
- [ ] Add a size class above which the gate reports "unjudgeable by Word on
  this machine" as its own recorded outcome (that fact is itself a finding —
  the corpus is named `word_based` and Word cannot reopen its own output at
  scale).
- [ ] On timeout, attempt a targeted close of the opened document so retries
  do not stack windows.

## 2. ENGINE_COMMIT pin must record the full build recipe (MEDIUM)

The vendored browser wasm is now built with
`RUSTFLAGS="-C link-arg=-zstack-size=8388608"` on top of the wasm-pack `-O3`
profile — "same engine commit" no longer identifies the artifact. Extend the
A-4 pin mandate (tool_updater) to persist rustflags + wasm-pack
target/profile + wasm-opt flags alongside the commit. Consider moving the
stack-size flag into the adapter crate's wasm-pack metadata so it cannot be
forgotten.

## 3. Memory budget gate per corpus size class (MEDIUM)

Measured on the dissertation pair (276k runs, 9.8 MB): jubarte-rust native
**~11.9 GB peak footprint**, jubarte-first AST **13.9 GB / 35 s**,
jubarte-first lossless WmlComparer **23.4 GB / 78 min**. wasm32 (4 GiB) can
run none of them. Add a scheduled bench job recording peak footprint per
engine per corpus size class with an explicit wasm32-viability line, so
memory regressions surface as diffs the way speed regressions do.

## 4. Cross-engine judge triangulation for D-2 (MEDIUM)

The demo sessions proved the judging risk both ways: folio's resolver bug
(non-atomic PM join) made a CORRECT jubarte output fail folio's self-check;
jubarte-first's reject (no mark-join semantics) masks its own
paragraph-mark defect from reject-based self-tests. D-2's accept/reject gate
must judge through THREE lenses — folio views, the engine's own
accept/reject, and WV-1 Word samples — and treat lens disagreement as the
alarm. (Recorded in
`reconciliation_plan/ST-THOMAS-JUBARTE-FOLIO-INTEGRATION-REVIEW.md`.)
