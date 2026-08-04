# Corpus-400 recovery archive (August 2026)

Working files kept from `~/temp/T/bench-recovery/`, the scratch directory used to
reconstruct PRs #10–#15 and drive the first full-corpus runs after the 403-pair
migration. The scratch directory itself has been deleted; this is what was worth
keeping.

## What is here

| file | why it is kept |
|---|---|
| `final-run.log`, `final-run2.log` | the exact invocations and output of the first full-corpus (403-pair) runs — the provenance for the numbers that shipped in that generation of RESULTS.md |
| `run-rust.log`, `run-lossless.log`, `run-native2.log` | the three per-engine runs behind that generation's jubarte comparison |
| `holdout_keys.txt` | the sealed holdout keys as originally drawn |
| `holdout_gen.py` | how those keys were drawn — without it the sealed set is an unexplained list |

## What was discarded, and why that is safe

`gatefix.patch`, `pr10-cli.patch`, `pr12-tracked.patch`, `pr15fix.patch`,
`workers.patch`, `probe-check/`, `pr12-test_holdout.py`, `extract_prompts.py` and the
`prompt-impl-*.md` scaffolding.

The patches were the *mechanism* for reconstructing work that is now ordinary git
history, so keeping them stores the same change twice — in a form that no longer
applies. Before deleting, each was checked against the tree rather than assumed:
`gatefix.patch` reverse-applies cleanly (definitively already present), and for the
rest, distinctive added lines were grepped out of `src/`, `tests/` and `scripts/` —
40/40, 28/40, 25/32 and 24/25 present. The shortfalls are reworded strings and
docstrings, plus one `pyproject`/`uv.lock` dependency line that lives outside those
three directories. Nothing was found that had been lost.

## Caveat on the numbers in these logs

These runs predate the 803-pair corpus (`corpus_revision b7f467074a51`) and the
SuperDoc subcorpus. Their means are **not** comparable with current results — the
current corpus is materially harder. Read them as provenance, not as a baseline.
