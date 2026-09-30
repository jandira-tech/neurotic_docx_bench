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
- SuperDoc last, as asked.

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

`scores_<tool>.json`: `rows` per compare, `summary` by oracle and state, `missing`. Rasters
are deleted per chunk.
