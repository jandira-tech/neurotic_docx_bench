# neurotic-docx-bench

How close can DOCX redline tools get to **Microsoft Word**?

This benchmark takes real `base → next` document pairs, asks each tool to produce a
tracked-change redline, renders the result to PDF, and scores every page **pixel-wise**
against a committed **Word oracle** for that pair. Higher scores mean the tool’s redline
looks more like Word’s.

| | |
| --- | --- |
| **Scores** | 0–100 per document (higher is better) |
| **Oracle** | Word’s tracked-change markup, rendered by LibreOffice 26.2.4.2 |
| **Trend log** | `results/bench.jsonl` (append-only) |
| **Full tables** | [`RESULTS.md`](RESULTS.md) · [`docs/RESULTS.md`](docs/RESULTS.md) |
| **Visual report** | `runs/<run>/report.html` — per-run candidate-vs-oracle gallery, worst first |
| **Speed** | [`docs/SPEED.md`](docs/SPEED.md) · large-N runs under `results/redline_speed_bench/` |

Rankings below cover **fidelity** (0–100 vs Word oracle) and **speed** (ms per redline) as
separate benchmarks. Jubarte families (**final**, **final-lossless**, **rust**) list only the
**best and worst** version pin per fidelity table so mid-range pins do not clutter the board;
other vendors keep each published pin. Pool results until a full re-run is complete, then
regenerate:

```bash
python3 scripts/export-results-md.py          # RESULTS.md + docs/RESULTS.md
bun run update-readme-ranking                 # tables between RANKING markers
uv run bench docx-to-pdf --update-readme      # 500-doc Word-oracle DOCX→PDF table
```

> **The oracle in one sentence.** Markup comes from real Microsoft Word; PDFs are rendered
> with **LibreOffice 26.2.4.2** for both oracle and candidates so scores measure
> *redline-markup fidelity vs Word*, not renderer drift. Feeding the oracle’s own source
> DOCX back through that pipeline scores **100** (sanity check).

> [!IMPORTANT]
> **The audit changed who wins.** We are jubarte's authors. An audit begun 2026-08-04
> found nine defects in this comparison, most of them favouring us. After fixing them,
> **`docxodus 9.0.0` led the redline table — 80.24 ITT mean / 91.11 median against
> jubarte's then-best 77.02 / 78.53, with 186 perfect scores to our 158.**
> **Current pin is `docxodus@9.8.0` (2026-08-12):** same 80.24 / 91.11, same 186
> perfects, same 4 failures as 9.0.0. **jubarte-rust HEAD still leads** on the
> 763-doc ITT (`@17ea47e9a0d7+git.bf3d07d`, 2026-08-13): **84.47 mean / 92.66
> median / 197 perfects / 0 failures**. **jubarte-first lossless** now ranks
> **above 9.8.0** (`@951a6e6b+git.98e641b1`, 2026-08-14): **81.99 / 91.31 /
> 186 perfects / 0 failures**. jubarte-ast has no current-corpus 763 (legacy
> 74.20 / 76.15). Jubarte subset rows (n < 760) are not ranked.
>
> It was hidden by our own configuration: bench.yaml pinned `docxodus@7.0.0`, two majors
> stale, and that build failed 38 documents where 9.0.0 fails 3. The engine we had been
> publishing numbers about is not the engine docxodus ships. Rows are still being
> re-measured; per-vendor disclosures are in [`docs/VENDOR_NOTES.md`](docs/VENDOR_NOTES.md)
> and the full write-up is Chapter 6 of the execution plan.
>
> **Retractions — these rows measured our bugs, not the vendor:**
> - **folio**, all `script_redlines` scores. Our adapter matched a revised-side block id
>   against base-side blocks, so **0 of 157** modification operations translated and
>   **24 of 60** sampled pairs emitted no tracked changes at all. Through folio's own
>   `generateRedlineDocx`, the same sample gives **59 of 60**.
> - **superdoc-ts**, which scored zero because it died at engine load — before the first
>   pair — on a module path our own updater never installs to.
> - **superdoc-native** and **superdoc-redlines**, which failed on clones we never
>   installed. `superdoc/` was not even gitignored, so installing it would have dirtied
>   the tree.
> - **docxodus**'s first row labelled `9.0.0` executed **7.0.0** (pin/install split-brain).
>   A genuine 9.0.0 run landed 2026-08-04; 9.8.0 was re-measured 2026-08-12 and matches it.
> - **docx-redline-js** is not the vendor's code at all: it builds
>   `@arthrod/docx-redline-js@0.3.0`, *our* TypeScript migration, while upstream
>   publishes 0.2.1. The row is named for them and runs us.
>
> **Fixed, and why the numbers move:**
> - **Corpus symmetry.** Coverage was per-run copy-paste: 4 of 12 runs covered all 803
>   pairs, 8 covered 207, and all of them shared one table. Now 12 of 12 cover 803.
>   (It never split along vendor lines — `docxodus` had full coverage; our own
>   `jubarte-wasm` did not.)
> - **Stale competitor versions**, up to two majors behind, with the pin enforced
>   *downward* — a run downgraded `package.json` from docxodus `^7.1.0` to `^7.0.0`.
>   All vendors now run their latest release.
> - **Our clock recorded as their crash.** A fixed 1800s generate budget, unchanged since
>   the corpus quadrupled, killed docxodus at 622/763 and logged it as a failure.
> - **A competitor-only wipeout.** `docxodus` was the only generating run declaring
>   `visual_*` benchmarks, so it alone carried two `n_docs=0` rows jubarte could not receive.
>
> **Still open:** jubarte is benchmarked at repo HEAD while competitors run published
> releases; jubarte's tables show its *best* pin while competitors show every pin
> (measured inflation **+3.6 to +8.8 points**); only jubarte has sealed-holdout
> overfitting checks; and `superdoc-redlines`' score is substantially our code, since its
> CLI has no compare call and our harness supplies the block alignment.
>
> A failure counts against a vendor only when *their* code produced it. Tools we failed to
> install, or killed with our own timeout, are our gap — never their zero.

<!-- RANKING-START -->
### script_redlines — redline markup vs Word

Sorted by **ITT median** (intent-to-treat: every failed doc scores 0, so crashing on hard docs is penalized, not rewarded; 0–100, higher is closer to the oracle). Mean/Median cover completed docs only. `~` marks ITT stats approximated from summary numbers (older runs without per-doc scores). Jubarte families (**final**, **final-lossless**, **rust**) show only the **best** and **worst** version pin for this benchmark; other vendors list each pin. Jubarte-`*` rows with ITT docs < 760 are omitted.

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`)

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | jubarte-rust | jubarte-rust@17ea47e9a0d7+git.bf3d07ddd61180e55f327c8e891affd0f6c18d64 | 763 | 763 | 84.47 | 92.66 | 84.47 | 92.66 | 197 | 0 |
| 2 | jubarte (lossless) | jubarte-final@951a6e6b453c+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a (best) | 763 | 763 | 81.99 | 91.31 | 81.99 | 91.31 | 186 | 0 |
| 3 | docxodus | 9.8.0 | 760 | 763 | 80.24 | 91.11 | 80.55 | 91.19 | 186 | 4 |
| 4 | jubarte (lossless) | jubarte-final@e7bcd29bb5a9+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a (worst) | 763 | 763 | 81.57 | 89.11 | 81.57 | 89.11 | 182 | 0 |
| 5 | stemma | 0.5.0@2e7bdc832391+git.efaed0c1ecb41142b1465bbb124dd183c385a2b0 | 614 | 763 | 50.63 | 56.62 | 62.91 | 61.83 | 9 | 149 |
| 6 | safe-docx | 0.19.1@e3f092da3639+git.7bd35c876493f2725b095f0190c28d2644962c78 | 688 | 763 | 48.38 | 49.69 | 53.65 | 51.31 | 6 | 75 |
| 7 | redlines | 0.6.1 | 745 | 763 | 44.86 | 47.05 | 45.94 | 47.14 | 0 | 18 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs — not comparable with the rows above; kept for history until each tool re-runs):

> ⚠️ **Rows below cover different document counts (763, 232, 230, 207, 196, 195, 168, 9) — they are not the same measurement.** A tool scored on fewer documents ran a different, usually easier, subset; its rank is not comparable with a row covering more. Compare only rows whose `ITT Docs` match.

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 9.0.0 | 760 | 763 | 80.24 | 91.11 | 80.55 | 91.19 | 186 | 4 |
| 2 | jubarte-wasm | 0.1.0@4b36f4db1d2f+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 763 | 763 | 79.57 | 84.89 | 79.57 | 84.89 | 182 | 0 |
| 3 | jubarte (lossless) | jubarte-final@d43557e042c1 | 763 | 763 | 77.02 | 78.53 | 77.02 | 78.53 | 142 | 0 |
| 4 | jubarte-wasm | 0.1.0 | 763 | 763 | 76.21 | 77.95 | 76.21 | 77.95 | 158 | 0 |
| 5 | jubarte-ast | jubarte-final@a58157a9cd2d | 763 | 763 | 74.20 | 76.15 | 74.20 | 76.15 | 96 | 0 |
| 6 | jubarte-rust | jubarte-rust@9457b6549b5d+git.ebf1a79 | 763 | 763 | 76.40 | 76.04 | 76.40 | 76.04 | 144 | 0 |
| 7 | sanity-word | — | 230 | 230 | 68.17 | 70.48 | 68.17 | 70.48 | 0 | 0 |
| 8 | jubarte-ast | jubarte-final@d43557e042c1 | 755 | 763 | 69.83 | 68.30 | 70.57 | 68.67 | 84 | 9 |
| 9 | ooxmlsdk | — | 232 | 232 | 55.19 | 55.24 | 55.19 | 55.24 | 0 | 0 |
| 10 | docxodus | 6.4.0 | 205 | 207 | 58.17 | 55.00 | 58.74 | 55.03 | 3 | 2 |
| 11 | folio | 0.3.1 | 205 | 207 | 54.77 | 53.52 | 55.31 | 53.75 | 0 | 2 |
| 12 | superdoc | 1.19.2 | 171 | 195 | 49.39 | 52.95 | 56.32 | 54.81 | 2 | 33 |
| 13 | folio | 0.15.13 | 744 | 763 | 50.83 | 50.29 | 52.13 | 50.43 | 0 | 19 |
| 14 | superdoc | 1.21.3 | 665 | 763 | 46.30 | 50.16 | 53.13 | 51.56 | 3 | 115 |
| 15 | docx-redline-js | 0.3.0-ts-migration | 161 | 168 | 48.43 | 50.09 | 50.53 | 50.26 | 0 | 7 |
| 16 | docxodus | 7.0.0 | 196 | 196 | 50.49 | 49.64 | 50.49 | 49.64 | 0 | 0 |
| 17 | superdoc-redlines | 0.2.0 | 703 | 763 | 47.37 | 49.16 | 51.41 | 50.11 | 0 | 68 |
| 18 | docx-redline-js | 0.3.0 | 746 | 763 | 45.16 | 47.22 | 46.19 | 47.42 | 0 | 17 |
| 19 | superdoc | 2.0.0 | 331 | 763 | 19.61 | 0.00 | 45.19 | 46.72 | 1 | 432 |
| 20 | docx-redline-js | — | 2 | 9 | 12.25 | 0.00 | 55.12 | 55.12 | 0 | 7 |

### accepted_changes — accept all changes, match final doc

Sorted by **ITT median** (intent-to-treat: every failed doc scores 0, so crashing on hard docs is penalized, not rewarded; 0–100, higher is closer to the oracle). Mean/Median cover completed docs only. `~` marks ITT stats approximated from summary numbers (older runs without per-doc scores). Jubarte families (**final**, **final-lossless**, **rust**) show only the **best** and **worst** version pin for this benchmark; other vendors list each pin. Jubarte-`*` rows with ITT docs < 760 are omitted.

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`)

> ⚠️ **Rows below cover different document counts (198, 178, 144) — they are not the same measurement.** A tool scored on fewer documents ran a different, usually easier, subset; its rank is not comparable with a row covering more. Compare only rows whose `ITT Docs` match.

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 9.8.0 | 195 | 198 | 88.82 | 100.00 | 90.19 | 100.00 | 119 | 4 |
| 2 | stemma | 0.5.0@2e7bdc832391+git.efaed0c1ecb41142b1465bbb124dd183c385a2b0 | 141 | 144 | 77.46 | 80.63 | 79.10 | 80.77 | 19 | 3 |
| 3 | safe-docx | 0.19.1@e3f092da3639+git.7bd35c876493f2725b095f0190c28d2644962c78 | 177 | 178 | 63.73 | 59.71 | 64.09 | 60.22 | 9 | 1 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs — not comparable with the rows above; kept for history until each tool re-runs):

> ⚠️ **Rows below cover different document counts (174, 166, 164) — they are not the same measurement.** A tool scored on fewer documents ran a different, usually easier, subset; its rank is not comparable with a row covering more. Compare only rows whose `ITT Docs` match.

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 6.4.0 | 164 | 164 | 69.00 | 77.19 | 69.00 | 77.19 | 14 | 0 |
| 2 | docxodus | 7.0.0 | 164 | 164 | 70.20 | 74.92 | 70.20 | 74.92 | 17 | 0 |
| 3 | superdoc | 1.19.2 | 150 | 166 | 57.67 | 55.82 | 63.82 | 61.12 | 2 | 16 |
| 4 | folio | 0.3.1 | 164 | 174 | 54.58 | 53.96 | 57.91 | 55.61 | 3 | 10 |

### roundtrip — self-diff must not invent noise

Sorted by **ITT median** (intent-to-treat: every failed doc scores 0, so crashing on hard docs is penalized, not rewarded; 0–100, higher is closer to the oracle). Mean/Median cover completed docs only. `~` marks ITT stats approximated from summary numbers (older runs without per-doc scores). Jubarte families (**final**, **final-lossless**, **rust**) show only the **best** and **worst** version pin for this benchmark; other vendors list each pin. Jubarte-`*` rows with ITT docs < 760 are omitted.

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`)

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | safe-docx | 0.19.1@e3f092da3639+git.7bd35c876493f2725b095f0190c28d2644962c78 | 166 | 166 | 100.00 | 100.00 | 100.00 | 100.00 | 166 | 0 |
| 2 | docxodus | 9.8.0 | 166 | 166 | 99.99 | 100.00 | 99.99 | 100.00 | 163 | 0 |
| 3 | stemma | 0.5.0@2e7bdc832391+git.efaed0c1ecb41142b1465bbb124dd183c385a2b0 | 166 | 166 | 99.95 | 100.00 | 99.95 | 100.00 | 161 | 0 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs — not comparable with the rows above; kept for history until each tool re-runs):

> ⚠️ **Rows below cover different document counts (198, 197, 166) — they are not the same measurement.** A tool scored on fewer documents ran a different, usually easier, subset; its rank is not comparable with a row covering more. Compare only rows whose `ITT Docs` match.

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | folio | 0.3.1 | 198 | 198 | 98.07 | 100.00 | 98.07 | 100.00 | 185 | 0 |
| 2 | docxodus | 7.0.0 | 166 | 166 | 97.43 | 100.00 | 97.43 | 100.00 | 148 | 0 |
| 3 | docxodus | 6.4.0 | 198 | 198 | 92.24 | 100.00 | 92.24 | 100.00 | 144 | 0 |
| 4 | superdoc | 1.19.2 | 194 | 197 | 91.59 | 100.00 | 93.00 | 100.00 | 144 | 3 |

### visual_rendering — editor render of plain DOCX

Sorted by **ITT median** (intent-to-treat: every failed doc scores 0, so crashing on hard docs is penalized, not rewarded; 0–100, higher is closer to the oracle). Mean/Median cover completed docs only. `~` marks ITT stats approximated from summary numbers (older runs without per-doc scores). Jubarte families (**final**, **final-lossless**, **rust**) show only the **best** and **worst** version pin for this benchmark; other vendors list each pin. Jubarte-`*` rows with ITT docs < 760 are omitted.

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`)

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 9.8.0 | 199 | 199 | 65.27 | 67.88 | 65.27 | 67.88 | 1 | 0 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs — not comparable with the rows above; kept for history until each tool re-runs):

> ⚠️ **Rows below cover different document counts (199, 198) — they are not the same measurement.** A tool scored on fewer documents ran a different, usually easier, subset; its rank is not comparable with a row covering more. Compare only rows whose `ITT Docs` match.

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | superdoc | 1.44.1 | 199 | 199 | 58.78 | 61.25 | 58.78 | 61.25 | 0 | 0 |
| 2 | folio | 0.5.0 | 198 | 198 | 59.65 | 55.10 | 59.65 | 55.10 | 0 | 0 |
| 3 | docxodus | 6.4.0-local.1 | 190 | 199 | 53.95 | 49.24 | 56.50 | 49.72 | 0 | 9 |
| 4 | docxodus | 7.0.0 | 190 | 199 | 53.95 | 49.24 | 56.50 | 49.72 | 0 | 9 |

### visual_redlines — editor render of redline DOCX

Sorted by **ITT median** (intent-to-treat: every failed doc scores 0, so crashing on hard docs is penalized, not rewarded; 0–100, higher is closer to the oracle). Mean/Median cover completed docs only. `~` marks ITT stats approximated from summary numbers (older runs without per-doc scores). Jubarte families (**final**, **final-lossless**, **rust**) show only the **best** and **worst** version pin for this benchmark; other vendors list each pin. Jubarte-`*` rows with ITT docs < 760 are omitted.

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`)

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 9.8.0 | 155 | 155 | 61.10 | 62.44 | 61.10 | 62.44 | 0 | 0 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs — not comparable with the rows above; kept for history until each tool re-runs):

> ⚠️ **Rows below cover different document counts (197, 182, 166, 165) — they are not the same measurement.** A tool scored on fewer documents ran a different, usually easier, subset; its rank is not comparable with a row covering more. Compare only rows whose `ITT Docs` match.

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 6.4.0 | 145 | 182 | 48.54 | 58.92 | 60.92 | 61.22 | 0 | 37 |
| 2 | superdoc | 1.44.1 | 164 | 165 | 55.00 | 56.34 | 55.33 | 56.42 | 0 | 1 |
| 3 | docxodus | 9.0.0 | 178 | 197 | 54.35 | 55.39 | 60.15 | 57.56 | 1 | 19 |
| 4 | folio | 0.5.0 | 164 | 166 | 50.93 | 51.48 | 51.55 | 51.65 | 0 | 2 |
| 5 | docxodus | 7.0.0 | 164 | 166 | 47.65 | 48.03 | 48.23 | 48.08 | 0 | 2 |

### visual_accepted_changes — editor render of accepted DOCX

Sorted by **ITT median** (intent-to-treat: every failed doc scores 0, so crashing on hard docs is penalized, not rewarded; 0–100, higher is closer to the oracle). Mean/Median cover completed docs only. `~` marks ITT stats approximated from summary numbers (older runs without per-doc scores). Jubarte families (**final**, **final-lossless**, **rust**) show only the **best** and **worst** version pin for this benchmark; other vendors list each pin. Jubarte-`*` rows with ITT docs < 760 are omitted.

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`)

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 9.8.0 | 155 | 155 | 64.63 | 65.79 | 64.63 | 65.79 | 0 | 0 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs — not comparable with the rows above; kept for history until each tool re-runs):

> ⚠️ **Rows below cover different document counts (165, 164, 152) — they are not the same measurement.** A tool scored on fewer documents ran a different, usually easier, subset; its rank is not comparable with a row covering more. Compare only rows whose `ITT Docs` match.

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 6.4.0 | 152 | 152 | 62.32 | 62.76 | 62.32 | 62.76 | 0 | 0 |
| 2 | superdoc | 1.44.1 | 165 | 165 | 59.34 | 60.97 | 59.34 | 60.97 | 0 | 0 |
| 3 | folio | 0.5.0 | 164 | 164 | 59.67 | 54.95 | 59.67 | 54.95 | 0 | 0 |

### speed_redlines — generation time (ms per redline)

Sorted by median **ms per redline** (lower is faster). Large-N warm rows (`*-inproc`) measure algorithm cost in a long-lived process; CLI rows include process spawn. Prefer warm rows for engine comparisons. Methodology: [Speed methodology](#speed-methodology). Raw log: `results/speed.jsonl`.

**Large-N** (`kind: speed_redlines` — often 1000 fixtures → 5000 pairs):

| Rank | Tool | Runtime | Fixtures | Pairs | Median ms | Mean ms | p95 | /s | n | Failures |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | jubarte-rust-inproc | rust | 1000 | 5000 | 6.20 | 25.34 | 110.76 | 39.5 | 5000 | 0 |
| 2 | docxodus-csharp-inproc | dotnet | 1000 | 5000 | 7.89 | 25.83 | 101.85 | 38.7 | 4880 | 120 |
| 3 | jubarte-rust | rust | 1000 | 5000 | 9.66 | 31.02 | 123.39 | 32.2 | 5000 | 0 |
| 4 | jubarte-wasm | rust-wasm | 1000 | 5000 | 9.67 | 41.49 | 174.03 | 24.1 | 5000 | 0 |
| 5 | jubarte-native | node | 1000 | 5000 | 14.43 | 57.15 | 175.71 | 17.5 | 5000 | 0 |
| 6 | jubarte-lossless | node | 1000 | 5000 | 54.64 | 168.18 | 592.49 | 5.9 | 4997 | 3 |
| 7 | docxodus | dotnet-wasm | 1000 | 5000 | 74.59 | 428.23 | 922.48 | 2.3 | 5000 | 0 |
| 8 | docxodus-csharp | dotnet | 50 | 50 | 208.39 | 441.65 | 911.87 | 2.3 | 50 | 0 |

**Microbench** (`kind: speed` — typically ~30–40 pairs × 3 reps):

| Rank | Tool | Runtime | Median ms | Mean ms | p95 | /s | n | Failures |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | docx-redline-js | node | 1.45 | 2.79 | 6.91 | 358.4 | 90 | 0 |
| 2 | jubarte-third-docxodus | node | 2.36 | 6.03 | 33.76 | 165.8 | 90 | 0 |
| 3 | jubarte-second-docxodus | node | 2.39 | 5.89 | 31.35 | 169.8 | 90 | 0 |
| 4 | jubarte-lossless | node | 2.46 | 6.60 | 37.58 | 151.6 | 90 | 0 |
| 5 | jubarte-second-native | node | 4.46 | 7.49 | 31.96 | 133.6 | 90 | 0 |
| 6 | jubarte-third-native | node | 4.47 | 7.55 | 33.21 | 132.4 | 90 | 0 |
| 7 | jubarte-native | node | 4.50 | 7.67 | 33.27 | 130.4 | 90 | 0 |
| 8 | jubarte-final-native | node | 6.76 | 18.89 | 115.97 | 52.9 | 90 | 0 |
| 9 | jubarte-final-lossless | node | 18.13 | 52.76 | 311.11 | 19.0 | 90 | 0 |
| 10 | superdoc | python | 40.89 | 94.19 | 619.93 | 10.6 | 90 | 0 |
| 11 | docxodus | node | 75.27 | 236.57 | 1499.68 | 4.2 | 90 | 0 |
<!-- RANKING-END -->

<!-- DOCX-TO-PDF-START -->
### DOCX→PDF — 500 Word-oracle documents

Pixel score vs Microsoft Word–exported PDFs in `corpus/no_comments_pdf_was_generated_by_word` (source + Word redlines + accepted; no randomized clones, not the LibreOffice `pdf_source`). Intent-to-treat: convert crash, empty output, or non-`%PDF-` is a generate failure scored as 0. Mean and median are ITT. PdfItDown's Office path is office2pdf; near-identical scores are expected, not a measurement error.

Measurement set: **500** unique stems.

| Rank | Tool | Version | n scored | ITT n | ITT Mean | ITT Median | Perfect (100) | Failures |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | jubarte | jubarte 0.7.0 | 500 | 500 | 64.29 | 66.22 | 0 | 0 |
| 2 | office2pdf | office2pdf 0.6.7 | 489 | 500 | 64.83 | 62.79 | 1 | 11 |
| 3 | pdfitdown | pdfitdown 4.0.0 | 489 | 500 | 64.83 | 62.79 | 1 | 11 |
| 4 | rdocx | rdocx 0.7.0 | 500 | 500 | 53.17 | 51.18 | 0 | 0 |
| 5 | doxx | doxx 0.1.4 | 0 | 500 | 0.00 | 0.00 | 0 | 500 |
<!-- DOCX-TO-PDF-END -->

---

## What each benchmark measures

There are **six** benchmarks. The first three score **generator** quality through
LibreOffice. The last three score **web-editor** rendering through Playwright. **Do not
compare LibreOffice scores to Playwright scores** — only compare vendors within the same
benchmark.

### Generator fidelity (LibreOffice render)

| Benchmark | In plain English | What we feed the tool | What we score against |
| --- | --- | --- | --- |
| **`script_redlines`** | “Does your redline look like Word’s redline?” | `base.docx` + `next.docx` → tool produces a redline DOCX | Word’s redline PDF for that pair |
| **`accepted_changes`** | “If someone accepts all your tracked changes, is the final document right?” | Accept every `w:ins`/`w:del` on the tool’s redline | Word’s redline with all changes accepted |
| **`roundtrip`** | “Does a no-op self-diff invent junk?” | Tool diffs a document against itself (or re-serializes via its roundtrip path) | The original source PDF — perfect identity is **100** |

**`script_redlines`** is the headline metric: pixel match of the tool’s redline markup
against Word’s redline for the same pair.

**`accepted_changes`** catches tools that paint a pretty redline but put the wrong text in
the “final” document once changes are accepted (common when inserts/deletes are misplaced).

**`roundtrip`** is an identity / cleanliness test. Diffing a document with itself (or
running the tool’s roundtrip pipeline) should not invent spurious markup. High medians near
100 are expected; large drops mean the engine is noisy.

### Editor fidelity (Playwright viewer)

These open DOCX in each vendor’s **web editor** (not LibreOffice), screenshot pages to PDF,
and score against the matching Word-oracle PDF corpus.

| Benchmark | Document shown in the editor | Oracle PDF corpus |
| --- | --- | --- |
| **`visual_rendering`** | Plain source DOCX (`docx_source`) | `pdf_source` |
| **`visual_redlines`** | Word’s redline DOCX (`docx_redlines_word`) | `pdf_redlines_word` |
| **`visual_accepted_changes`** | Accepted Word redlines (`docx_accepted_word`) | `pdf_accepted_word` |

Notes that matter when reading scores:

- **SuperDoc generator ≠ SuperDoc editor.** Generator runs use the Python SDK
  (`superdoc-sdk` **1.19.2**). Visual runs use the browser editor (`superdoc` **1.44.1**).
  Different packages, different version numbers — both are intentional.
- **Folio generator ≠ Folio viewer.** Generator uses `@stll/folio-core` **0.3.1**; visual
  runs use `@stll/folio-react` **0.5.0**.
- Visual runs isolate **viewer** fidelity (they load Word’s DOCX, not the tool’s own
  redlines), so a strong visual score does not prove a strong generator.

---

## Tools

| Vendor | What runs | Version pin | Role |
| --- | --- | --- | --- |
| **jubarte** | In-repo `dist/jubarte-final` (`compareDocx` / CriticMarkup paths) | content-hash under `dist/` | Generator |
| **jubarte-rust** | Native CLI built from canonical `../jubarte-redlines` | content-hash | Generator |
| **jubarte-wasm** | wasm-bindgen adapter over canonical `../jubarte-redlines` | generated artifact + source commit | Generator |
| **docxodus** | npm `docxodus` WASM `compareDocuments` | **9.8.0** | Generator + viewer |
| **folio** | `@stll/folio-core` compare + applyOperations | **0.3.1** | Generator |
| **folio** (viewer) | `@stll/folio-react` Playwright harness | **0.5.0** | Editor |
| **superdoc** | Python `superdoc-sdk` Document Engine | **1.19.2** | Generator |
| **superdoc** (editor) | npm `superdoc` Playwright harness | **1.44.1** | Editor |
| **docx-redline-js** | `@ansonlai/docx-redline-js` OOXML reconciliation | **0.2.0** | Generator |
| **redlines** | [houfu/redlines](https://github.com/houfu/redlines) text differ (`redlines_gen.py` + required `nupunkt==0.6.0`) | **0.6.1** + nupunkt 0.6.0 | Generator (text-level baseline) |
| **superdoc-redlines** | [yuch85/superdoc-redlines](https://github.com/yuch85/superdoc-redlines) SuperDoc-headless CLI (`superdoc_redlines_gen.py` aligns blocks, the CLI applies word-diffed track changes) | **0.2.0** | Generator |
| **stemma** | [stemma-sh/stemma](https://github.com/stemma-sh/stemma) `stemma compare` (stemma-cli 0.5.0) | **0.5.0** (content-hash + git v0.5.0) | Generator |
| **safe-docx** | [UseJunior/safe-docx](https://github.com/UseJunior/safe-docx) `@usejunior/docx-compare` `compareDocuments` at PR 854 merge `7bd35c8` — **not** published `@usejunior/docx-compare@0.19.1` | **7bd35c8** (content-hash) | Generator |

Pins live in [`bench.yaml`](bench.yaml). Do not bump to `@latest` without re-review — the
pin is what keeps CI and published rankings reproducible.

For the canonical source folder, native/WASM build flow, fidelity gate, and 5k
speed command, read the local `../reconciliation_plan/GET_JUBARTE_RUST.md` handoff
and [`docs/SPEED.md`](docs/SPEED.md).

---

## Quick start

**Requirements:** Python 3.14 (`uv`), Bun (or Node), **LibreOffice 26.2.4.2** on `PATH`.

```bash
uv sync
bun install --frozen-lockfile

# Per-tool node deps (generators + viewers)
cd src/neurotic_docx_bench/utils/docxodus && bun install --frozen-lockfile && cd -
cd src/neurotic_docx_bench/utils/docx-redline-js && bun install --frozen-lockfile && cd -
cd src/neurotic_docx_bench/utils/folio && bun install --frozen-lockfile && cd -
cd src/neurotic_docx_bench/utils/superdoc && bun install --frozen-lockfile && cd -
cd harness/folio-viewer && bun install --frozen-lockfile && cd -

# Smoke one tool on a few docs
uv run bench run --only jubarte-final-lossless --limit 5

# Full suite (all runs in bench.yaml)
uv run bench run
```

Each run: resolve `tool_version` → generate redlines → render → score vs oracle → append
one JSONL line to `results/bench.jsonl` → gate against the accepted snapshot.

Work folders land in `runs/{run}_{datetime}`. Use `--clean-runs` in CI to delete them after
a successful emit (kept on failure for debugging).

### Useful commands

```bash
uv run bench run --only docxodus --limit 5 --no-emit   # quick smoke, no JSONL write
uv run bench run --only-on-change                      # append JSONL only when scores change
uv run bench run-all --really-all                      # every run + generate_scripts
uv run bench accept-scores jubarte                     # promote latest line to gate baseline

uv run bench render <docx-dir> <work-dir> -b soffice   # DOCX → PDF
uv run bench compare <candidate-pdfs> <oracle-pdfs> --tool name
uv run bench accept <redline-docx-dir> --out <folder>  # accept all tracked changes
uv run bench reject <redline-docx-dir> --out <folder>
```

Common flags: `--config`, `--limit`, `--dpi`, `--no-update`, `--emit/--no-emit`,
`--gate/--no-gate`, `--generate/--no-generate`, `--results-dir`, `--runs-dir`.

---

## How scoring works

1. **Match** candidate PDF ↔ oracle PDF by `<base>_<next>` key (redlines) or plain stem
   (roundtrip / some visual runs).
2. **Raster** every page at the configured DPI (default 144).
3. **Score** each page with a weighted blend of SSIM, ink-F1, edge-IoU, colour ΔE, and blob
   metrics → 0–100, then aggregate per document and per run.

The scoring core (`score.py`, `diff.py`, `raster.py`, …) is lifted **verbatim** from
[superdoc-visual-benchmarks](https://github.com/superdoc-dev/superdoc-visual-benchmarks);
`tests/test_parity.py` guards byte-identical behaviour against a committed reference.

**Page-count mismatches** are recorded (`page_count_mismatch`) but not penalised — only
`min(pages)` is compared.

### Gate (CI)

- Score **100** always passes.
- A **per-document** drop vs the accepted snapshot → warning.
- An **aggregate** drop (mean or median) → **fail** (non-zero exit).

Promote a good run: `uv run bench accept-scores <tool>`.

---

## Speed methodology

Generation and render speed are a **benchmark** (see the **speed_redlines** table in the
ranking block above), not a separate marketing section. Data: `results/speed.jsonl` and
`results/redline_speed_bench/`. Detail: [`docs/SPEED.md`](docs/SPEED.md).

Do not mix measurement modes when comparing tools:

| mode | what you measure | example tools | use when |
|---|---|---|---|
| **Warm in-process** | compare work inside one long-lived process | `jubarte-rust-inproc`, `docxodus-csharp-inproc` | algorithm comparison |
| **CLI per redline** | process spawn + runtime init + compare | `jubarte-rust`, `docxodus-csharp` | end-to-end CLI cost |
| **WASM** | in-process after one-time load | `jubarte-wasm` (Rust/wasm-bindgen), npm `docxodus` (.NET/Mono) | browser/WASM cost |
| **Microbench** | small N × reps (often in-memory Node) | `scripts/speed-bench.ts` | quick relative Node engines |

**Large-N protocol** (`scripts/redline_speed_bench.ts`):

1. **Fixtures:** up to 1000 unique `.docx` by content hash from corpus dirs → `fixtures_bytes/`.
2. **Pairs:** 5000 deterministic base→next pairs (Mulberry32 seed 42 by default); plan in `pairs.json`.
3. **Warmup** untimed; then each pair timed with `performance.now()`; failures excluded from stats.
4. **Warm workers** share a stdin `COMPARE` protocol so native engines are measured the same way.
5. Optional **samply** (1000 Hz) profiles over the timed loop for native workers.
6. Append to `results/speed.jsonl` (`kind: speed_redlines`); fold into README/RESULTS via
   `bun run update-readme-ranking` / `python3 scripts/export-results-md.py`.

```bash
node --import tsx scripts/speed-bench.ts --pairs 30 --reps 3 --out results/speed.jsonl
uv run python -m neurotic_docx_bench.superdoc_speed --pairs 30 --reps 3 --out results/speed.jsonl
bun run redline-speed-bench:warm    # large-N warm engines
bun run redline-speed-bench:thesis  # warm + CLI + WASM pack
```

---

## Project map

```
bench.yaml                 # runs, pins, oracles, generate_scripts
corpus/word_based/         # source / redline / accepted DOCX + PDF oracles
results/bench.jsonl        # append-only trend log (schema v4)
results/score-snapshots/   # gate baselines
src/neurotic_docx_bench/   # CLI, pipeline, scoring, generators
scripts/                   # Node generators, ranking export, speed bench
runs/                      # per-run work dirs (local; often gitignored artifacts)
```

Agent-oriented invariants: [`AGENTS.md`](AGENTS.md). Contributor notes: [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## Provenance & thanks

- **[balalofernandez/docx-revisions](https://github.com/balalofernandez/docx-revisions)** —
  accept/reject tracked changes (`bench accept` / `reject`).
- **[superdoc-dev/superdoc-visual-benchmarks](https://github.com/superdoc-dev/superdoc-visual-benchmarks)** —
  visual scoring core.
- **[JSv4/docxodus](https://github.com/JSv4/docxodus)** &
  **[react-docxodus-viewer](https://github.com/JSv4/react-docxodus-viewer)** (MIT).
- **[AnsonLai/docx-redline-js](https://github.com/AnsonLai/docx-redline-js)** (MIT).
- **[houfu/redlines](https://github.com/houfu/redlines)** (MIT) — Ang Hou Fu's text-level
  redliner; the `redlines` runs wrap it as a pure-text baseline generator.
- **[yuch85/superdoc-redlines](https://github.com/yuch85/superdoc-redlines)** (Apache-2.0) —
  SuperDoc-headless CLI for block-ID tracked-change edits; the `superdoc-redlines` run
  drives its extract→apply pipeline with a deterministic block alignment.
- **[stella/folio](https://github.com/stella/folio)** (Apache-2.0).
- **[SuperDoc](https://github.com/Harbour-Enterprises/SuperDoc)** (AGPL-3.0) and related
  SuperDoc tooling.

## License

Scoring core derived from
[`superdoc-visual-benchmarks`](https://github.com/superdoc-dev/superdoc-visual-benchmarks).
This repository is licensed under **AGPL-3.0-only**. See [`LICENSE`](LICENSE).

Published scores are independent engineering measurements — not endorsements of any
third-party product. Microsoft Word is a trademark of Microsoft; the Word oracle is used
for measurement only.
