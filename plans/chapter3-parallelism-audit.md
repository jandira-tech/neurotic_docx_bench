# Chapter 3 audit — where the time actually goes

Measured on this machine (Darwin 25.5.0, 12 logical cores = **8 performance +
4 efficiency**, LibreOffice 26.2.4.2, scikit-image 0.26.0), 2026-08-04, against
the 400-pair SuperDoc redline corpus.

The plan's Chapter 3 was written from a reading of the code, not from
measurements. Three of its six tasks turn out to be premised on conditions that
do not hold here. This document records what was measured, so the rejections are
checkable rather than asserted.

## Cost breakdown for one tool over the 400-pair subcorpus

| stage | measured | notes |
|---|---|---|
| render candidates (soffice, 12 jobs) | **0.48 s/doc** → ~192 s | 60 docs in 28.8 s |
| score (12 jobs) | **337.7 s** | 400 pairs, ~1290 page-pairs |
| score, serial | **1.19 s per page-pair** | 12 pairs / 38 pages, jobs=1: 45.2 s |
| ProcessPoolExecutor startup, 12 workers | **0.62 s** | warmed or cold, same |

Scoring dominates. Rendering is second. Pool construction is noise.

## Task-by-task verdict

### 3.2 Shared executor — **not worth it**

The premise was "~1–2 s × 12 workers of interpreter+import startup, several
times per run". Measured pool construction including a real import of the
scoring stack in every worker:

| context | startup |
|---|---|
| default (spawn) | 0.62 s |
| spawn + warm initializer | 0.62 s |
| forkserver | 0.44 s |
| forkserver + warm initializer | 0.42 s |

A run builds roughly five pools, so the whole prize is **~3 s** (~1 s more from
forkserver). That does not justify threading a shared executor through
`pipeline` / `accept_changes` / `functional_lens`, each of which is on the
scoring path this chapter is forbidden to perturb.

### 3.3 Vectorize pixel compare — **already done**

`score.py` is numpy/skimage throughout (`_load_image` → `np.asarray`, masks via
`filters.threshold_otsu` / `feature.canny` / `ndimage.distance_transform_edt`),
and `html_report.py:712` already uses `np.abs` + `np.any`. There is no
per-pixel Python arithmetic left to convert. No change made.

### 3.4 `--dist worksteal` — **measurably slower, rejected**

Full suite, `--ignore=tests/test_canary.py` (pre-existing import failure):

| addopts | run 1 | run 2 |
|---|---|---|
| `-n 12` (current) | 45.01 s | 44.10 s |
| `-n 12 --dist worksteal` | 45.82 s | 46.18 s |

~3 % slower. The plan's own acceptance criterion is "verify wall-clock drops";
it does not, so `addopts` is left alone. The default `--dist load` already
schedules per-test, so worksteal only adds coordination overhead — it pays off
under `--dist loadfile`, which this suite does not use.

### Thread pinning inside workers — **score-neutral but no gain**

12 worker processes each running their own BLAS/FFT thread pool on 8
performance cores looks like textbook oversubscription. Setting
`OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1` in the workers:

| mode | 24 pairs |
|---|---|
| default | 12.0 s |
| pinned to 1 thread | 12.6 s |

Slightly worse. Scores were compared field by field and are **identical** —
only the `raster_ns` / `score_ns` timing fields differ — so the change is safe,
it simply buys nothing. Not adopted.

## The one big speed-up on the table, and why it must not be taken

`soffice` is invoked once per document with an isolated user profile. Passing
many documents to a single invocation amortises LibreOffice startup:

| invocation | 12 documents |
|---|---|
| 12 separate `soffice` calls (serial) | 16.0 s |
| 1 `soffice` call, 12 files | **4.0 s** |

4× — and it is the same binary with the same flags, so it looks free. It is
not. Rasterising both sets at 144 dpi and comparing pixel by pixel:

| documents compared | result |
|---|---|
| per-file run A vs per-file run B | 0 / 12 differ (bit-identical) |
| per-file vs batched | **5 / 12 differ**, up to **2.7 % of pixels** |

LibreOffice carries state across documents inside one process. The per-document
isolated profile is not naive — it is what makes renders reproducible, and this
benchmark's entire premise is that oracle and candidate are rendered by the same
renderer in the same state.

**This also condemns the "persistent LibreOffice via unoserver" drop-in** in
Chapter 1 of the execution plan: unoserver is a long-lived LibreOffice process
serving many documents, which is precisely the condition measured above. If it
is ever revisited, it must first pass this equivalence test — render the whole
corpus both ways and show zero differing pixels — and on this evidence it will
not.

## What is actually left

The bottleneck is the scorer at ~1.19 s per page-pair, already vectorised,
already parallel, on 8 performance cores. Making it faster means changing what
it computes, and Chapter 3's own rule is that it must not move a single score.
So the honest position is: **there is no significant score-neutral speed-up
available here**, and the chapter's remaining value is this measurement,
not a refactor.

If a future speed-up is wanted, the candidates that do not touch numerics are:
- caching rasterised pages by content hash across runs (raster is only ~3 % of
  per-document cost — `raster_ns` 0.28 s vs `score_ns` 9.15 s — so the ceiling
  is small);
- scoring at lower dpi, which **does** move scores and therefore needs its own
  decision and a re-baseline, not a speed-up PR.
