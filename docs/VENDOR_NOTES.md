# Vendor notes — the disclosure ledger

Every place where our harness touched a vendor's code, forked it, knows of an
unfixed bug, or supplies behaviour the vendor does not, is written down here and
published **beside** the numbers. Plan reference: `plans/agent-execution-plan.md`
Chapter 6.4.

The rule this file exists to enforce: *a benchmark run by one of the competitors
is only worth reading if the competitor discloses its own thumbs on the scale.*
We are jubarte's authors. Everything below is a thumb, ours included.

## How to read the columns

- **Version benchmarked** — the exact release, resolved on the run date. A pin
  older than the current release is a defect (Chapter 6 D2), not a policy.
- **Harness-assisted** — part of the score is *our* code, because the tool does
  not expose the operation the benchmark needs. The score is then a joint
  product of their engine and our glue, and must not be read as pure vendor
  capability.
- **Known-unfixed** — a defect we are aware of that is still in the published
  release a user would install.

## Ledger

### jubarte (jubarte-rust, jubarte-final-lossless, jubarte-final-native/ast)

**Ours.** Benchmarked at repo HEAD, not at a released version — every other
vendor is benchmarked at a published release. It also carries the deepest
adapter work in this repo.

On corpus coverage, honesty requires a correction to an earlier draft of this
file: it claimed jubarte was the only family covering all three corpus pools
while competitors ran on one. That was false. `docxodus` already had full
coverage, and our own `jubarte-wasm` was among the runs covering only 207
pairs. Coverage was copy-pasted per run and drifted in both directions — it is
a harness footgun, not a thumb on the scale (Chapter 6 D1).

Stated plainly: the home team has the home-field advantage in integration
effort. Chapter 6.2(5) ("adapter parity") is the remedy, and where parity is not
reached the deficit belongs in this file, not in the competitor's score.

### docxodus

| field | value |
|---|---|
| Package | npm `docxodus` (WASM build of the C# engine) |
| Pinned in bench.yaml | `7.0.0` — **two majors stale**; published latest is `9.0.0` |
| Harness-assisted | No — single `compareDocuments` call |
| Known-unfixed | Yes, see below |

Two disclosures:

1. **We benchmarked a version we had already superseded.** The repo's
   `package.json` carried `docxodus ^7.1.0`; the benchmark's tool updater
   *downgraded* it to `^7.0.0` to honour the bench.yaml pin. That is worse than
   passive staleness — the pin was enforced downward against a newer release
   already present.

2. **A bug we found, fixed locally, and could not land upstream.** The fix was
   offered as a pull request and was **not accepted**. The consequence is the
   one that matters for a published benchmark: *the defect is still in the
   release a user installs.* Reporting only a patched-fork score would flatter
   them; reporting only the upstream score while sitting on a fix and saying
   nothing would bury the fact that the defect is known and fixable. So:
   - the **headline row is published upstream**, because that is what a user gets;
   - the patched fork, when available in the checkout, is a **separate,
     clearly-labelled row** — never merged into the headline.

   Status in this checkout (verified 2026-08-04): the patched C# source is
   **not present**. `docs/SPEED.md` points the C# lanes at a sibling repo
   `../ooxmlsdk/Docxodus/tools/redline` and bench.yaml's
   `docxodus-playwright-*` runs point at
   `src/neurotic_docx_bench/utils/docxodus/Docxodus/npm`; **neither path
   exists**, so no fork row can be produced here yet and those runs cannot
   resolve a version at all.

3. **Observed crash on the current corpus (docxodus 7.0.0, 2026-08-04 sweep).**
   A recurring managed exception, thrown from the vendor's own stack:

   ```
   at Docxodus.WmlComparer.AddFootnotesEndnotesStyles(WordprocessingDocument wDocWithRevisions)
   at Docxodus.WmlComparer.ProduceDocumentWithTrackedRevisions(...)
   at Docxodus.WmlComparer.CompareInternal(...)
   at DocxodusWasm.DocumentComparer.CompareDocuments(Byte[] originalBytes, Byte[] modifiedBytes, ...)
   ```

   This is the vendor's code failing on our input, so under ITT it scores as a
   failure and is **not** excluded. Whether it is the same defect as the
   rejected PR is **not yet established** — do not assert the connection in
   published material until it is checked against 9.0.0.

### folio

| field | value |
|---|---|
| Packages | `@stll/folio-core` (generator), `@stll/folio-react` (viewer) |
| Benchmarked | core **0.15.13**, react **0.13.2** (was pinned core `0.3.1` / react `0.5.0`) |
| Harness-assisted | **No longer** — see below |

> **Retraction: every folio `script_redlines` number we published before
> 2026-08-04 measured our translation layer, not folio.**

folio 0.3.1 exposed no single base+next→redline call, so our adapter composed
`compareDocxVersions` with `FolioDocxReviewer.applyOperations`. That
composition was **silently wrong**. It passed a `modified` diff entry's
`blockId` into `replaceInBlock`, but folio emits its diff in *revised-side*
order and that id is the revised-side id — so **no base block ever matched**.
Every modification operation was dropped, and any pair whose changes were all
modifications fell through to an identity fallback that returned the base
document unchanged.

Measured over the first 60 manifest pairs on 0.3.1:

| | 0.3.1 via our composition | 0.15.13 via `generateRedlineDocx` |
|---|---|---|
| `modified` entries translated | **0 of 157** | n/a — single call |
| pairs emitting **no** tracked changes | **24 of 60** | 1 of 60 (folio itself reports zero changes) |
| pairs carrying tracked changes | 36 of 60 | **59 of 60** |
| generate failures | — | 0 |

So folio's published fidelity scores (54.77 ITT mean / 55.31 mean) are not a
measurement of folio. A tool handed our broken translation was scored on it.
This is the exact hazard the "harness-assisted" mark exists to flag, and it
turned out to be worse than assistance — it was corruption. The scores are
withdrawn rather than corrected in place; folio must be re-measured on
0.15.13 before any folio number is published again.

**The good news, and it is real:** as of core **0.13.0** folio ships
`generateRedlineDocx(base, revised, {author})`. `script_redlines` is now a
one-call passthrough — the scored bytes are folio's own output, with no
composition of ours in between. folio is therefore **no longer
harness-assisted** for this benchmark, and its next number will be the purest
one we have ever had for it. `@stll/folio-agents` was dropped entirely (it is
now a thin re-export of folio-core).

Also: 0.15.13 relaxes the empty-comment-author rule, so the two
`vfdsdfcacawesd_suggesting_mixed_edits` pairs documented in `docs/FOLIO.md` as
adapter limitations now generate with no adapter change at all — another
"vendor limitation" that was ours.

### superdoc

Three *distinct* packages, routinely conflated — they are not the same product
and must never share a row:

| run | package | pinned | latest |
|---|---|---|---|
| `superdoc` | Python `superdoc-sdk` | 1.19.2 | **2.0.0** (1 major stale) |
| `superdoc-ts` | npm `@superdoc-dev/sdk` | 1.19.2 | 1.21.3 |
| `superdoc-playwright-*` | npm `superdoc` (the *editor*) | 1.44.1 | **2.3.0** (1 major stale) |
| `superdoc-native` | git clone of the SuperDoc monorepo, in-process engine | — | — |

Disclosures:

- **`superdoc-ts` failure in the 2026-08-04 sweep was ours, not theirs.**
  `ERR_MODULE_NOT_FOUND` for `@superdoc-dev/sdk`: the updater installs it at the
  repo root while the adapter resolved it from `utils/superdoc/node_modules/`.
  A tool we failed to install is `UNINSTALLED` — our gap — and is excluded from
  the vendor's score rather than zero-filled.
- **`superdoc-native` failure was also ours**: `tool build dir not found:
  superdoc/packages/super-editor`, i.e. the gitignored monorepo clone was absent.
- **Honest vendor-side data does exist** for the Python SDK: in the same sweep
  `superdoc` reported 22 pairs its engine explicitly declined (e.g. *"Header/
  footer replay skipped … section projection was not found"*, *"Invalid content
  for node run"*) plus 3 render failures — 33 docs recorded as failed in the
  JSONL. Those are the vendor's engine on our input and they count.

### superdoc-redlines

| field | value |
|---|---|
| Source | `https://github.com/yuch85/superdoc-redlines` (Apache-2.0), git clone + build |
| Harness-assisted | **Yes** |

The CLI applies block-ID edits with track changes but has **no base+next compare
at all**. `src/neurotic_docx_bench/superdoc_redlines_gen.py` supplies a
deterministic block alignment and drives the CLI's own extract→apply pipeline.
The alignment — arguably the hardest part of redlining — is therefore **ours**.
This tool's score should be read as "their edit application, our diff", and it
is not comparable to a tool that computes its own alignment.

Its 2026-08-04 failure (`tool build dir not found`) was our missing clone, not
their code.

### redlines

| field | value |
|---|---|
| Package | PyPI `redlines` (houfu/redlines, MIT) |
| Pinned | `0.6.1` — **current**, the only vendor not stale |
| Harness-assisted | Partly — see below |

A pure-text differ by design. Our harness extracts paragraph text from the
base/next DOCX, runs Redlines, and writes a new DOCX with `w:ins`/`w:del`. The
DOCX construction is ours; the diff is theirs. It is a **text-level baseline
only** and structurally cannot score well on OOXML fidelity — publishing it in
the same column as structure-aware engines without this note would be
misleading about what it is for.

Also noted (deferred, plan 6.6): `nupunkt` improves its sentence tokenisation
and is **not currently installed**, so this is not `redlines` at its best.

## Standing rules

1. A failure is attributed to a vendor **only** when their code ran and produced
   it. Install/build/adapter failures are ours (`UNINSTALLED` / `ADAPTER_GAP`),
   are excluded from the vendor's score, and are reported as our gaps.
   Zero-filling our own breakage as their score is both wrong and self-serving.
2. No cross-vendor number ships without its `n` and `corpus_revision` beside it.
   Two different `n` values in one table is a defect, not a footnote.
3. A harness fix that raises a competitor's score ships with the same urgency as
   one that raises jubarte's.
4. When we cannot drive a vendor's API after honest effort, we publish
   `ADAPTER_GAP` naming the specific call that broke — never a silent zero.
