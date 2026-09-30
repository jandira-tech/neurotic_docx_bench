# redlines_0929_full: script redlines vs Word, every compare we hold

Corpus: every Word compare in `corpus/word/comparisons.csv` whose PDF exists and whose base
and next originals both exist (`prepare.py`). 3502 Word compares of 2611 distinct pairs
(one compare skipped: `b1b752d8e6` has no PDF). A pair Word compared more than once is
redlined once per tool and scored against each of Word's compares.

| file | what |
|---|---|
| `pool_pairs.csv` | the 3502 Word compares (the scoring corpus) |
| `gen_pairs.csv` | the 2611 distinct pairs, keyed by the pair's first compare id |
| `oracle_pdf/<key>.pdf` | links to Word's compare PDFs |
| `<tool>/docx/<key>_<tool>.docx` | the tool's redline |
| `<tool>/pdf_by_word/<key>_<tool>.pdf` | that redline opened in Word and exported by `scripts/word_pdf.py` |

## Engines: both through their inproc workers

jubarte and docxodus run through `scripts/generate-native-redlines.ts` with the
**inproc** methods, one long-lived worker process per tool (the same
`COMPARE base next out` protocol the speed bench uses), not a process per pair:

- `--method jubarte-rust-inproc`: jubarte-redlines **0.10.0** (tag `v0.10.0`,
  86b6b5d36556), `jubarte-rust-inproc` built from the canonical worktree
  `~/T/jubarte-redlines/.worktrees/v0.10.0` and staged as
  `~/temp/T/speed_bins/jubarte-inproc-86b6b5d3/jubarte-worker`. The bench's own
  `utils/jubarte/jubarte-rust-inproc` is 0.9.3 from Aug 13 and was not used.
- `--method docxodus-csharp-inproc`: Docxodus **12.6.5** (tag `v12.6.5`, 19b40bd7, the
  latest GitHub and NuGet release), `utils/docxodus/docxodus-csharp-inproc/bin/Release/net10.0`,
  whose `Docxodus.dll` is byte-identical to `~/temp/T/ooxmlsdk/Docxodus/tools/redline`.
- SuperDoc last, as asked: `neurotic_docx_bench.superdoc_gen` with superdoc-sdk **2.16.0**
  (the latest on PyPI; pin bumped from 2.15.0), 8 shards (`superdoc/pool_shard*.csv`,
  `superdoc/shard*/`, merged into `superdoc/docx` and `superdoc/generate_failures.json`).
  192 of 2611 pairs gave a redline. The 2419 failures are SuperDoc's own refusals ("tracked
  header/footer slot or physical topology changes are not supported" 1164, "tracked shared
  definition replacement is not supported" 612, "numbering replay is unsafe" 304, ...) plus
  45 host failures (watchdog timeout, "Failed to open document in the v2 runtime") that failed
  again when retried one at a time (`superdoc/retry/`). 1100 SuperDoc redlines are not
  reachable with this engine: 2.15.0 made 94 of the 1164 0928 pairs. Checked on 2026-09-30:
  `diff.apply` with `force: true` fails the same way on one pair per blocker (shared
  definition, numbering, comment, settings, header/footer, unsupported-context); the
  `applyTarget` "versioned document review session" the error suggests is only named in the
  error text of the SDK's CLI and of `@superdoc/cli` 0.39.0, not implemented; npm `superdoc`
  2.19.0 (released that day) has the same `DiffApplyOptions` (`changeMode` only) and the same
  blocker codes. PyPI has no SDK newer than 2.16.0.

jubarte 0.9.3 on at least 1100 pairs is `../redlines_0928`: 0.9.3 @673aff74 on 1163 Word
compares, with docxodus 12.6.4 and SuperDoc 2.15.0 on the same pairs and the same accepted /
rejected selections. This run is 0.10.0, released 2026-09-29, over every compare.

Before 2814e016 the inproc methods never stopped their worker at the end of `runBatch`,
so a generate run wrote every redline and then hung; only the speed bench, which shuts its
workers down itself, had used them.

Before 6d1127a5 a compare that hit the inproc reply timeout left its worker busy, so
every later pair queued behind it and timed out as well. The first docxodus run stalled
that way after 1139 redlines and was stopped; the resumed run (`docxodus.generate.resume.log`)
kept those 1139, used the fixed engine and `WORKER_REPLY_TIMEOUT_MS=120000` (the speed
lanes' per-pair limit), and its `generate_timings.json` covers only the pairs it made.
jubarte ran under the 15 s default and no pair reached it.

`generate.sh` runs both generators; `<tool>.generate.log`, `<tool>/generate_failures.json`
and `<tool>/generate_timings.json` record each run.

## Word export (`<tool>/pdf_by_word`)

| tool | redlines | PDFs by Word | Word failed |
|---|---|---|---|
| jubarte-rust | 2611 | 2608 | 3 |
| docxodus | 2605 (6 generate failures) | 1895 | 100 of the 100 retried; 551 never retried |
| superdoc | 192 | 192 | 0 |

docxodus redlines stall Word far more often. On "Word found unreadable content", the watchdog
answers No and Word then raises "Word experienced an error trying to open the file" (OK), but
only once Word is frontmost; in the background that alert does not exist, and the batch `open`
hangs until the 240 s AppleEvent timeout, which ends the pass and poisons later opens.
`scripts/word_pdf_focus.py` (`word_pdf.py` with a watchdog and progress tracker swapped in)
brings Word forward when an item is not saved within 5 s, presses No then OK, hides Word and
hands focus back. 651 redlines were owed when it started. It ran two batches of 50
(`docxodus.word_pdf.f{1,2}.log`, 30 min each, 184 forwards, no timeout) and got 0 PDFs: 99
loaded empty twice and one crashed Word twice, so those are not Word valid. At that yield the
remaining 551 (about 6 h of Word) were not retried; the run was stopped during batch 3, before
it logged a result.
`rest_list.py` links the owed files, `stage_word_pdf.py` collects PDFs from a live export,
`docxodus.word_pdf.{rest,b,f,single}*.log` record the passes.

## Scores (`measure.py`, pixel scorer + ink Jaccard, torch-mps)

Oracles: Word's compare PDFs, the 516 compares made again for this run (`compare_regen/out`,
"fresh") in place of the old ones. Headline is `pipeline.overall_from_result`.

| | jubarte 0.10.0 | docxodus 12.6.5 |
|---|---|---|
| all scored | 3499/3502, mean 72.29, median 81.79 | 2612/3502 (1895 PDFs), mean 72.33, median 81.75 |
| same 2611 compares: mean / median | **73.32 / 83.01** | 72.34 / 81.75 |
| =100 / >=90 / <50 | **244 / 517 / 558** | 204 / 482 / 613 |
| ink Jaccard mean / median (2554) | **0.688 / 0.899** | 0.657 / 0.851 |
| better by > 0.5 | 1008 | 738 (865 within 0.5) |

Final docxodus score after the focus retry (`measure_docxodus_focus.log`, 2026-09-30).
jubarte scores 69.25 mean on the 888 compares docxodus has no PDF for, so docxodus's gap is
biased toward the hard pairs. jubarte 0.10.0 vs 0.9.3 (`../redlines_0928`), same 1090 oracles:
68.03 / 70.07 -> 68.63 / 72.44 (96 better, 34 worse, 960 within 0.5); the regressions cluster in
the `*_id_paraid_overflow` fixtures (8 went from 100 to about 85).

SuperDoc 2.16.0: 380/3502 compares scored (its 192 redlines), mean 61.40, median 61.11. On the
323 compares all three tools scored (the pairs SuperDoc can do, which are easy ones):

| | jubarte 0.10.0 | docxodus 12.6.5 | SuperDoc 2.16.0 |
|---|---|---|---|
| mean / median | **90.96 / 86.72** | 89.78 / 85.00 | 61.42 / 61.67 |
| =100 / >=90 / <50 | 106 / **146** / 0 | **120** / 137 / 0 | 0 / 3 / 18 |
| ink Jaccard mean | **0.944** | 0.909 | 0.206 |

`scores_<tool>.json`: `rows` per compare, `summary` by oracle and state, `missing`. Rasters
are deleted per chunk.

## jubarte 0.9.3, the release (`jubarte-093`)

The goal named jubarte 0.9.3, so the tagged release ran the same 2611 pairs as a fourth tool:
the `v0.9.3` GitHub release asset (`jubarte-0.9.3-macos-aarch64`, sha256 checked against the
release's `SHA256SUMS.txt` by `jubarte_release.github_download`, binary sha256 15efac59...), through
`generate-native-redlines.ts --method jubarte-rust --tool jubarte-093` (the native CLI, one
process per pair). `../redlines_0928` ran `673aff74`, five commits before the tag. 2611 redlines,
0 failures (`jubarte-093.generate.log`).

Word export: `scripts/word_pdf.py` made 1790 PDFs and ended its three stalled passes with 817 never
reached (Word hung on files it cannot read, `jubarte-093.word_pdf.log`); `scripts/word_pdf_focus.py`
on the same folder took the rest (`jubarte-093.word_pdf.focus.log`), and a retry of the 4 with a
transient error got one (`jubarte-093.word_pdf.retry.log`): **2497 of 2611**. Of the 114 without a
PDF, 111 never opened ("every document doesn't understand close"), 3 failed twice
(`jubarte-093/word_missing.txt` lists the 115 before the retry).

| | jubarte 0.9.3 | jubarte 0.10.0 |
|---|---|---|
| all scored | 3338/3502, mean 71.99, median 81.34 | 3499/3502, mean 72.29, median 81.79 |
| same 3338 compares: mean / median | 71.99 / 81.34 | 71.99 / 81.36 |
| =100 / >=90 / <50 | **309 / 634** / 780 | 297 / 618 / **773** |
| better by > 0.5 | 83 | **114** (3141 within 0.5) |

On the 2584 compares jubarte 0.9.3, 0.10.0 and docxodus all scored: 73.23 / 82.81, 73.21 / 82.86
and 72.27 / 81.71; 0.9.3 is better than docxodus on 993, worse on 719. Between 0.9.3 and 0.10.0 the
redline scores are a wash; 0.10.0's gain in the 0928 comparison was against `673aff74`.

## Accepted and rejected tracks (`measure_tracks.py`)

The 100 compares of `accept_selection.csv` and the 100 of `reject_selection.csv` (copies of the
0928 selections: stratified, 40/60 and 25/75 with/without comments). Each tool's redline of
the compare's pair is staged as `<tool>/{accepted,rejected}/src/<compare id>.docx`, Word
accepts / rejects every change and saves docx + PDF
(`scripts/word_pdf_focus.py --one-osascript --accept-all --accept-suffix
_accepted_tracking_<tool>`, `--reject-all --reject-suffix _rejected_tracking_<tool>`) into
`<tool>/{accepted,rejected}/by_word`, scored against Word's own compare accepted / rejected
the same way (corpus sets `accepted_tracking_0928`, `rejected_tracking_0928`) by the 0928
scorer (`../redlines_0928/measure.py`, `HERE` pointed here). No compare failed for all
three tools, so none was replaced.

| track | jubarte 0.10.0 | jubarte 0.9.3 | docxodus 12.6.5 | SuperDoc 2.16.0 |
|---|---|---|---|---|
| accepted: scored | 99/100 | 99/100 | 91/100 | 5/5 |
| accepted: mean / median | 79.38 / 90.85 | 78.61 / 88.78 | 83.84 / 98.70 | 96.29 / 97.61 |
| accepted: =100 / >=90 / <50 | 20 / 51 / 21 | 19 / 49 / 22 | 22 / 55 / 15 | 0 / 4 / 0 |
| rejected: scored | 100/100 | 100/100 | 96/100 | 8/8 |
| rejected: mean / median | 64.17 / 58.29 | 64.18 / 58.29 | 72.52 / 77.18 | 97.77 / 98.57 |
| rejected: =100 / >=90 / <50 | 19 / 36 / 41 | 19 / 36 / 41 | 17 / 40 / 31 | 0 / 8 / 0 |

jubarte 0.9.3's tracks were staged by `stage_tracks.py jubarte-093` and run through the same
`word_pdf_focus.py` accept / reject commands; its accept failure is the same `1855b51281`.

Against 0928 (jubarte 0.9.3, docxodus 12.6.4, SuperDoc 2.15.0, same compares and Word oracles):
accepted jubarte 78.01 / 88.18 -> 79.38 / 90.85, docxodus 84.13 / 99.65 -> 83.84 / 98.70,
SuperDoc unchanged (96.29 / 97.61); rejected jubarte 64.55 -> 64.17, docxodus 73.22 -> 72.52,
SuperDoc 97.63 -> 97.77. SuperDoc's scores cover only the few compares it can redline.

Word failures: jubarte accepted `1855b51281` (the open outlasts the 240 s AppleEvent timeout,
in the batch and alone; Word opened it after the driver gave up and was left holding it,
closed unsaved); docxodus accepted 9 and rejected 4, all "document loaded empty" (Word
cannot read the redline). Transient failures were retried alone and succeeded: docxodus
rejected 4, SuperDoc accepted 2 (`*/reject_retry.log`, `*/accept_retry.log`).

## Where the files are (`hub_upload.py`)

The tool outputs are on the Hugging Face dataset `arthrod/neurotic_docx_bench` under
`outputs/redlines_0929_full/`: `<tool>/docx`, `<tool>/pdf_by_word`,
`<tool>/{accepted,rejected}/{src,by_word}` and `<tool>/meta` for jubarte-rust, docxodus and
superdoc, `fresh_compares` (the 516 Word compares made again, docx + PDF) and `run` (this
folder's CSVs, JSONs, scripts, `MANIFEST.sha256.json`). 12387 files, 2.61 GB, every one checked
against the hub (`hub_upload.log`, `hub_prune.log`) and then deleted here, together with
`docxodus/{docx_rest,docx_sample500}` (symlinks) and `docxodus/pdf_staged` (a byte-identical
subset of `pdf_by_word`). Word's own files (`corpus/word`, `compare_regen`) stay local.
jubarte-093 went up the same way later: 5706 files of its own (docx 2611, pdf_by_word 2497,
accepted 100 + 198, rejected 100 + 200), 6785 staged with `fresh_compares`, meta and `run`
refreshed, all verified, then deleted here (`hub_upload_093.log`).
Page-by-page site: https://jandira-tech.github.io/neurotic_docx_bench/redlines/ (gh-pages a58adc22,
with the jubarte 0.9.3 column; the builder fetches pruned tool PDFs from the hub).

## Corpus checks (2026-09-30)

- Every docx in `corpus/word` has its Word PDF except `b1b752d8e6` (tracking_without_comments,
  `82348eef4b_multi_section__vs__0b2a46481b_nested_table_rowspan_redline_b1b752d8e6`): Word
  opens it and refuses `save as` (-1708) in every pass (`pdf_fill_0928` lists it absent;
  `word_pdf.py` and `word_pdf_focus.py` failed on it again today).
- 3502 Word compares with docx and PDF, 1504 distinct base and 1411 distinct next documents
  from 12 sets; 322 of them with comments (with_comments_tracking), plus 112 documents with
  comments that are not redlines (with_comments_clean).
- `accepted_tracking_0928`: 100 Word compares (40 with comments) accepted by Word, named
  `<compare id>_accepted_tracking`, with their Word PDFs.
