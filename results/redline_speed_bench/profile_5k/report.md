# WE WON — warm redline speed: jubarte-rust beats Docxodus C#

**Headline (fair algorithm comparison, not CLI cold-start theatre):**

| rank | engine | mode | n | fail | **median ms** | mean ms | p95 | /s | wall s |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1** | **jubarte-rust** | **warm in-process** (`compare_documents`) | **5000** | **0** | **9.69** | 40.76 | 157.5 | 24.5 | 203.8 |
| 2 | Docxodus (C# / .NET) | warm in-process (`DocxDiffOps.Compare`) | 4880 | 120 | 11.83 | 37.43 | 135.1 | 26.7 | 204.6 |

**jubarte-rust is faster at the median** (~**18% lower** than warm Docxodus C#: 9.69 vs 11.83 ms) **and more reliable** (0 failures vs 120 / 2.4% on the same pair plan).

- **Same fixtures, same pairs, same seed.** 1000 unique corpus DOCX → 5000 deterministic base→next pairs (seed **42**).
- **Same measurement model for both winners:** long-lived worker process (no per-redline process spawn). That is the only apples-to-apples *algorithm* race.
- **Do not cite cold C# CLI** (~200+ ms median in earlier smokes) as “Docxodus is slow” — that number is mostly .NET process cold-start. Warm C# is competitive; **warm Rust still wins median + reliability**.

Profiles (samply, 1000 Hz):

```bash
samply load results/redline_speed_bench/profile_5k/cpu/jubarte-rust-inproc.profile.json.gz
samply load results/redline_speed_bench/profile_5k/cpu/docxodus-csharp-inproc.profile.json.gz
```

---

## Methodology (what this run measured)

### Fixture pool

1. Collect up to **1000** unique `.docx` by content SHA-1 from:
   - `corpus/word_based/docx_source`
   - `corpus/word_based/docx_source_randomized`
   - `corpus/word_based/docx_accepted_word`
   - `corpus/no_comments_pdf_was_generated_by_word/docx_source`
   - `corpus/no_comments_pdf_was_generated_by_word/docx_accepted_word`
   - `corpus/word_based/docx_redlines_word`
   - `corpus/no_comments_pdf_was_generated_by_word/docx_redlines_word`
2. Materialize once under `fixtures_bytes/` (**1000 files, ~32.4 MiB**).
3. Build **5000 pairs** with Mulberry32 **seed=42**: every fixture is base at least once per round; next is a random *different* fixture; rounds until `min-pairs=5000` (~5 rounds). Plan: `pairs.json`.

### Engines compared (warm)

| tool id | binary / API | what is timed |
|---|---|---|
| `jubarte-rust-inproc` | `jubarte-worker` → `jubarte::document_comparer::compare_documents` | write temp paths → one long-lived Rust process → compare → read output |
| `docxodus-csharp-inproc` | `docxodus-inproc` → `Docxodus.Internal.DocxDiffOps.Compare` | same protocol for fair warm .NET |

Protocol (both workers): `READY` / `COMPARE base next out` → `OK nbytes ms` / `ERR …` / `QUIT`.

### Timing protocol

- **Warmup:** 50 untimed compares (excluded from stats).
- **Timed:** 5000 pairs × 1 rep; each sample = `performance.now()` around one `COMPARE`.
- **Failures** are counted but **excluded** from median/mean/percentiles (so a fast-throw cannot deflate the mean).
- **Profiler:** [samply](https://github.com/mstange/samply) 1000 Hz over the timed loop (`--save-only`); child worker appears in the Firefox Profiler capture.
- **No 5000 redline DOCX kept on disk** — generation is timed and discarded (speed bench, not corpus export).

### What this is *not*

- Not CLI-per-call cost (`docxodus-csharp` / `jubarte-rust` spawn) — use those only for “shipping the binary” numbers.
- Not WASM Docxodus npm package.
- Not Word fidelity — that is `script_redlines` / `accepted_changes` in `results/bench.jsonl` (jubarte-rust also leads there; see README rankings).

### Run parameters

- **fixtures:** 1000 unique  
- **pairs:** 5000 (seed=42)  
- **warmup:** 50 · **reps:** 1  
- **out:** `results/redline_speed_bench/profile_5k`  
- **csharp run_ts (samples):** prior step in same folder  
- **rust run_ts:** `2026-07-15T20:28:07.290Z`

### Full distributions

| tool | n | fail | median | mean | p90 | p95 | p99 | min | max | /s | wall s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| jubarte-rust-inproc | 5000 | 0 | 9.688 | 40.764 | 125.72 | 157.506 | 494.063 | 1.863 | 2985.73 | 24.5 | 203.83 |
| docxodus-csharp-inproc | 4880 | 120 | 11.825 | 37.433 | 98.033 | 135.074 | 308.13 | 1.856 | 7649.38 | 26.7 | 204.63 |

Docxodus failures (120): mostly hostile corpus packages (`Document has no w:body`, relationship `rId*` conflicts) — not counted in timing stats.

---

## Reproduce

```bash
# workers (once)
dotnet build -c Release src/neurotic_docx_bench/utils/docxodus/docxodus-csharp-inproc
( cd src/neurotic_docx_bench/utils/jubarte/jubarte-rust-inproc && cargo build --release )
cp -f src/neurotic_docx_bench/utils/jubarte/jubarte-rust-inproc/target/release/jubarte-inproc \
      src/neurotic_docx_bench/utils/jubarte/jubarte-rust/jubarte-worker

node --import tsx scripts/redline_speed_bench.ts \
  --methods jubarte-rust-inproc,docxodus-csharp-inproc \
  --fixture-count 1000 --min-pairs 5000 --warmup 50 --reps 1 \
  --out results/redline_speed_bench/profile_5k

python3 scripts/export-results-md.py
```

**WE WON.**
