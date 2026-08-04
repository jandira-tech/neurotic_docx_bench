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
```

> **The oracle in one sentence.** Markup comes from real Microsoft Word; PDFs are rendered
> with **LibreOffice 26.2.4.2** for both oracle and candidates so scores measure
> *redline-markup fidelity vs Word*, not renderer drift. Feeding the oracle’s own source
> DOCX back through that pipeline scores **100** (sanity check).

> [!WARNING]
> **Do not read the cross-vendor rows below as a fair comparison yet.** We are jubarte's
> authors, and an audit on 2026-08-04 found three defects in the comparison — *all three
> favouring us*. They are being fixed in the open; until they are, jubarte-vs-competitor
> rows are provisional. Details and per-vendor disclosures:
> [`docs/VENDOR_NOTES.md`](docs/VENDOR_NOTES.md) · plan Chapter 6.
>
> 1. **Different document sets in the same table.** Corpus coverage is configured per run
>    and drifted: 4 of the 12 redline runs enumerate all three corpus pools (803 pairs)
>    while 8 silently run on one (207 pairs). Any row whose `Docs` differs from another
>    row's is *not the same measurement* — check the `Docs` / `ITT Docs` columns before
>    comparing anything. (This one does not split along vendor lines: `docxodus` has full
>    coverage, and our own `jubarte-wasm` is among the partial ones.)
> 2. **Best-of-N for us, single-shot for them.** The tables show jubarte's **best** version
>    pin while each competitor shows its own pins. The maximum of several noisy runs is
>    biased upward; measured inflation on real data was **+3.6 to +8.8 points**.
> 3. **Stale competitor versions.** Pins ran up to two majors behind (docxodus 7.0.0 vs
>    9.0.0 published, folio-core 0.3.1 vs 0.15.13, superdoc-sdk 1.19.2 vs 2.0.0). The pin
>    was even enforced *downward*: a run downgraded `package.json` from docxodus ^7.1.0 to
>    ^7.0.0.
>
> **Retracted: every folio `script_redlines` score published before 2026-08-04.** Our
> adapter composed two folio APIs and did it wrong — it matched a revised-side block id
> against base-side blocks, so **0 of 157** modification operations translated and **24 of
> 60** sampled pairs emitted no tracked changes at all. Those rows measured our
> translation, not folio. On current folio (`generateRedlineDocx`, a single call) the same
> sample gives **59 of 60** pairs with tracked changes. See
> [`docs/VENDOR_NOTES.md`](docs/VENDOR_NOTES.md).
>
> Also load-bearing: some competitor scores are partly **our** code — superdoc-redlines has
> no compare call at all, so our harness supplies the block alignment, which is arguably
> the hardest part of redlining. Those are marked harness-assisted in the ledger. And a
> failure only counts against a vendor when *their* code produced it: tools we failed to
> install, or killed with our own timeout, are our gap — never their zero.

<!-- RANKING-START -->
### script_redlines — redline markup vs Word

Sorted by **ITT median** (intent-to-treat: every failed doc scores 0, so crashing on hard docs is penalized, not rewarded; 0–100, higher is closer to the oracle). Mean/Median cover completed docs only. `~` marks ITT stats approximated from summary numbers (older runs without per-doc scores). Jubarte families (**final**, **final-lossless**, **rust**) show only the **best** and **worst** version pin for this benchmark; other vendors list each pin.

**Current corpus** (lines stamped with `corpus_revision` — the 403-pair corpus):

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | jubarte-rust | jubarte-rust@fcea02da49f4 | 383 | 383 | 85.02 | 93.37 | 85.02 | 93.37 | 126 | 0 |
| 2 | jubarte (lossless) | jubarte-final@d43557e042c1 | 383 | 383 | 82.27 | 86.05 | 82.27 | 86.05 | 109 | 0 |
| 3 | jubarte-ast | jubarte-final@d43557e042c1 | 375 | 383 | 73.43 | 75.45 | 75.00 | 77.14 | 40 | 9 |

**Legacy corpus** (older, smaller corpora — not comparable with the rows above; kept for history until each tool re-runs):

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | jubarte-rust | jubarte-rust@63e57d122c83 (best) | 164 | 164 | 92.21 | 99.92 | 92.21 | 99.92 | 80 | 0 |
| 2 | jubarte-wasm | 0.1.0 | 164 | 164 | 92.21 | 99.92 | 92.21 | 99.92 | 80 | 0 |
| 3 | jubarte (final) | jubarte-final@3995702f73ed (best) | 163 | 167 | 87.89 | 91.84 | 90.04 | 91.99 | 44 | 4 |
| 4 | jubarte (lossless) | jubarte-final@d5bd12d173d6+git.aaa85454f569b7174dd99d5244877d29819a99b9 (best) | 164 | 164 | 83.63 | 88.96 | 83.63 | 88.96 | 53 | 0 |
| 5 | sanity-word | — | 230 | 230 | 68.17 | 70.48 | 68.17 | 70.48 | 0 | 0 |
| 6 | jubarte (lossless) | jubarte-final@b4f90acaa85e (worst) | 196 | 196 | 64.69 | 63.48 | 64.69 | 63.48 | 0 | 0 |
| 7 | jubarte-rust | jubarte-rust@b834d6e49fdb (worst) | 172 | 207 | 51.34 | 55.92 | 61.78 | 59.28 | 2 | 35 |
| 8 | ooxmlsdk | — | 232 | 232 | 55.19 | 55.24 | 55.19 | 55.24 | 0 | 0 |
| 9 | docxodus | 7.0.0 | 205 | 207 | 58.18 | 55.00 | 58.75 | 55.03 | 3 | 2 |
| 10 | docxodus | 6.4.0 | 205 | 207 | 58.17 | 55.00 | 58.74 | 55.03 | 3 | 2 |
| 11 | folio | 0.3.1 | 205 | 207 | 54.77 | 53.52 | 55.31 | 53.75 | 0 | 2 |
| 12 | superdoc | 1.19.2 | 182 | 207 | 50.28 | 53.25 | 57.19 | 55.60 | 2 | 25 |
| 13 | superdoc-redlines | 0.2.0 | 192 | 207 | 53.45 | 53.11 | 57.63 | 55.90 | 0 | 15 |
| 14 | redlines | 0.6.1 | 200 | 207 | 49.55 | 51.32 | 51.28 | 51.77 | 0 | 7 |
| 15 | docx-redline-js | 0.3.0-ts-migration | 161 | 168 | 48.43 | 50.09 | 50.53 | 50.26 | 0 | 7 |
| 16 | jubarte (final) | jubarte-final@8b23cdc7eca8 (worst) | 207 | 207 | 48.31 | 49.46 | 48.31 | 49.46 | 0 | 0 |
| 17 | docx-redline-js | — | 2 | 9 | 12.25 | 0.00 | 55.12 | 55.12 | 0 | 7 |

### accepted_changes — accept all changes, match final doc

Sorted by **ITT median** (intent-to-treat: every failed doc scores 0, so crashing on hard docs is penalized, not rewarded; 0–100, higher is closer to the oracle). Mean/Median cover completed docs only. `~` marks ITT stats approximated from summary numbers (older runs without per-doc scores). Jubarte families (**final**, **final-lossless**, **rust**) show only the **best** and **worst** version pin for this benchmark; other vendors list each pin.

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | jubarte-rust | jubarte-rust@653876af82d6 (best) | 164 | 164 | 89.58 | 99.89 | 89.58 | 99.89 | 78 | 0 |
| 2 | jubarte (lossless) | jubarte-final@dd16ad8fbcf3 (best) | 164 | 164 | 86.53 | 94.42 | 86.53 | 94.42 | 63 | 0 |
| 3 | jubarte (lossless) | jubarte-final@717311c03d4f (worst) | 166 | 166 | 78.15 | 80.64 | 78.15 | 80.64 | 26 | 0 |
| 4 | docxodus | 6.4.0 | 164 | 164 | 69.00 | 77.19 | 69.00 | 77.19 | 14 | 0 |
| 5 | docxodus | 7.0.0 | 164 | 164 | 70.20 | 74.92 | 70.20 | 74.92 | 17 | 0 |
| 6 | superdoc | 1.19.2 | 150 | 166 | 57.67 | 55.82 | 63.82 | 61.12 | 2 | 16 |
| 7 | folio | 0.3.1 | 164 | 174 | 54.58 | 53.96 | 57.91 | 55.61 | 3 | 10 |
| 8 | jubarte (final) | jubarte-final@dd16ad8fbcf3 | 164 | 164 | 48.52 | 50.51 | 48.52 | 50.51 | 0 | 0 |
| 9 | jubarte-rust | jubarte-rust@b834d6e49fdb (worst) | 147 | 174 | 53.65 | 49.17 | 63.50 | 54.45 | 13 | 27 |

### roundtrip — self-diff must not invent noise

Sorted by **ITT median** (intent-to-treat: every failed doc scores 0, so crashing on hard docs is penalized, not rewarded; 0–100, higher is closer to the oracle). Mean/Median cover completed docs only. `~` marks ITT stats approximated from summary numbers (older runs without per-doc scores). Jubarte families (**final**, **final-lossless**, **rust**) show only the **best** and **worst** version pin for this benchmark; other vendors list each pin.

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | jubarte-rust | jubarte-rust@cbbcefb724a7 (best) | 166 | 166 | 99.17 | 100.00 | 99.17 | 100.00 | 157 | 0 |
| 2 | folio | 0.3.1 | 198 | 198 | 98.07 | 100.00 | 98.07 | 100.00 | 185 | 0 |
| 3 | jubarte (lossless) | jubarte-final@dd16ad8fbcf3 (best) | 166 | 166 | 97.63 | 100.00 | 97.63 | 100.00 | 152 | 0 |
| 4 | docxodus | 7.0.0 | 166 | 166 | 97.43 | 100.00 | 97.43 | 100.00 | 148 | 0 |
| 5 | jubarte (lossless) | jubarte-final@717311c03d4f (worst) | 199 | 199 | 94.49 | 100.00 | 94.49 | 100.00 | 149 | 0 |
| 6 | docxodus | 6.4.0 | 198 | 198 | 92.24 | 100.00 | 92.24 | 100.00 | 144 | 0 |
| 7 | superdoc | 1.19.2 | 194 | 197 | 91.59 | 100.00 | 93.00 | 100.00 | 144 | 3 |
| 8 | jubarte-rust | jubarte-rust@b834d6e49fdb (worst) | 171 | 192 | 82.93 | 100.00 | 93.12 | 100.00 | 120 | 23 |
| 9 | jubarte (final) | jubarte-final@dd16ad8fbcf3 | 166 | 166 | 52.63 | 53.23 | 52.63 | 53.23 | 0 | 0 |

### visual_rendering — editor render of plain DOCX

Sorted by **ITT median** (intent-to-treat: every failed doc scores 0, so crashing on hard docs is penalized, not rewarded; 0–100, higher is closer to the oracle). Mean/Median cover completed docs only. `~` marks ITT stats approximated from summary numbers (older runs without per-doc scores). Jubarte families (**final**, **final-lossless**, **rust**) show only the **best** and **worst** version pin for this benchmark; other vendors list each pin.

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | superdoc | 1.44.1 | 199 | 199 | 58.78 | 61.25 | 58.78 | 61.25 | 0 | 0 |
| 2 | folio | 0.5.0 | 198 | 198 | 59.65 | 55.10 | 59.65 | 55.10 | 0 | 0 |
| 3 | docxodus | 6.4.0-local.1 | 190 | 199 | 53.95 | 49.24 | 56.50 | 49.72 | 0 | 9 |
| 4 | docxodus | 7.0.0 | 190 | 199 | 53.95 | 49.24 | 56.50 | 49.72 | 0 | 9 |

### visual_redlines — editor render of redline DOCX

Sorted by **ITT median** (intent-to-treat: every failed doc scores 0, so crashing on hard docs is penalized, not rewarded; 0–100, higher is closer to the oracle). Mean/Median cover completed docs only. `~` marks ITT stats approximated from summary numbers (older runs without per-doc scores). Jubarte families (**final**, **final-lossless**, **rust**) show only the **best** and **worst** version pin for this benchmark; other vendors list each pin.

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 6.4.0 | 145 | 182 | 48.54 | 58.92 | 60.92 | 61.22 | 0 | 37 |
| 2 | superdoc | 1.44.1 | 164 | 165 | 55.00 | 56.34 | 55.33 | 56.42 | 0 | 1 |
| 3 | folio | 0.5.0 | 164 | 166 | 50.93 | 51.48 | 51.55 | 51.65 | 0 | 2 |
| 4 | docxodus | 7.0.0 | 164 | 166 | 47.65 | 48.03 | 48.23 | 48.08 | 0 | 2 |

### visual_accepted_changes — editor render of accepted DOCX

Sorted by **ITT median** (intent-to-treat: every failed doc scores 0, so crashing on hard docs is penalized, not rewarded; 0–100, higher is closer to the oracle). Mean/Median cover completed docs only. `~` marks ITT stats approximated from summary numbers (older runs without per-doc scores). Jubarte families (**final**, **final-lossless**, **rust**) show only the **best** and **worst** version pin for this benchmark; other vendors list each pin.

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
| 1 | jubarte-rust-inproc | rust | 1000 | 5000 | 8.10 | 33.74 | 142.24 | 29.6 | 5000 | 0 |
| 2 | docxodus-csharp-inproc | dotnet | 1000 | 5000 | 9.43 | 29.90 | 110.73 | 33.4 | 4880 | 120 |
| 3 | jubarte-rust | rust | 1000 | 5000 | 9.66 | 31.02 | 123.39 | 32.2 | 5000 | 0 |
| 4 | jubarte-wasm | rust-wasm | 1000 | 5000 | 9.72 | 41.44 | 180.49 | 24.1 | 5000 | 0 |
| 5 | jubarte-native | node | 1000 | 5000 | 14.43 | 57.15 | 175.71 | 17.5 | 5000 | 0 |
| 6 | jubarte-lossless | node | 1000 | 5000 | 54.64 | 168.18 | 592.49 | 5.9 | 4997 | 3 |
| 7 | docxodus | dotnet-wasm | 200 | 500 | 148.75 | 607.38 | 3212.30 | 1.6 | 496 | 4 |
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
| **docxodus** | npm `docxodus` WASM `compareDocuments` | **6.4.0** | Generator + viewer |
| **folio** | `@stll/folio-core` compare + applyOperations | **0.3.1** | Generator |
| **folio** (viewer) | `@stll/folio-react` Playwright harness | **0.5.0** | Editor |
| **superdoc** | Python `superdoc-sdk` Document Engine | **1.19.2** | Generator |
| **superdoc** (editor) | npm `superdoc` Playwright harness | **1.44.1** | Editor |
| **docx-redline-js** | `@ansonlai/docx-redline-js` OOXML reconciliation | **0.2.0** | Generator |
| **redlines** | [houfu/redlines](https://github.com/houfu/redlines) text differ (`redlines_gen.py` wraps it with DOCX extract/rebuild) | **0.6.1** | Generator (text-level baseline) |
| **superdoc-redlines** | [yuch85/superdoc-redlines](https://github.com/yuch85/superdoc-redlines) SuperDoc-headless CLI (`superdoc_redlines_gen.py` aligns blocks, the CLI applies word-diffed track changes) | **0.2.0** | Generator |

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
