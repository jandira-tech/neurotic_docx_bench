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
| Pinned | **9.0.0** (was `7.0.0` — two majors stale) |
| Actually measured so far | **7.0.0** — see the retraction below; a true 9.0.0 run is pending |
| Harness-assisted | No — single `compareDocuments` call, now with an explicitly named engine |
| Known-unfixed | Yes — status against 9.0.0 **unknown**, see retraction |

> **RETRACTED 2026-08-04 — the run labelled `docxodus 9.0.0` executed 7.0.0.**
>
> The `package:` pin installs into the repo-root `node_modules` and
> `tool_version` is read back from there (9.0.0), but the adapter imports
> `src/neurotic_docx_bench/utils/docxodus/node_modules`, which still held
> **7.0.0**. The published line recorded one version and ran another — the D5
> split-brain, in the very vendor whose upgrade introduced the D5 fix, caught by
> that upgrade's own test only after the number had been published. The vendored
> tree is now at 9.0.0 and **docxodus must be re-run** before any 9.0.0 number
> is quoted.
>
> Two claims made on the strength of that run are withdrawn:
>
> 1. That **9.0.0 is a rewritten IR-based engine**, inferred from failures moving
>    from `WmlComparer.AddFootnotesEndnotesStyles` to `Ir.IrReader` /
>    `IrMarkupRenderer.Render`. The crash sites did move — but the same change
>    also made the adapter **name the comparison engine explicitly**, selecting a
>    different engine inside the *same* 7.0.0 build. Engine identity and version
>    identity were confounded, and the version was the wrong explanation.
> 2. That **the bug behind the rejected upstream PR may already be fixed.** That
>    was inferred from the same moved crash site, inherits the same confound, and
>    is not established in either direction.
>
> The ITT mean of **51.70** (n=707 of 763) stands only as a measurement of
> *docxodus 7.0.0 driven with an explicitly named engine*. It is not a 9.0.0
> result and must not be labelled one.

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

3. **Observed crash on the current corpus (docxodus 7.0.0, 2026-08-04 sweep,
   default engine).**
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
   published material until it is checked against a genuine 9.0.0 run.

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
- **`superdoc-native` has never been runnable in this checkout, and that is
  entirely our gap.** Its first failure was `tool build dir not found:
  superdoc/packages/super-editor` — the gitignored monorepo clone was absent.
  Cloning SuperDoc (HEAD `5b1af90`, 2026-08-03) and running its `pnpm install`
  fixed that, and revealed a second, larger problem: the run drives SuperDoc's
  own vitest at
  `superdoc/packages/super-editor/src/editors/v1/tests/redline-bench/redline.test.js`
  — **a bench-authored harness file that exists nowhere.** Not in the upstream
  clone (it is ours, not theirs), not in this repo, and not anywhere in git
  history (searched across all refs, 2026-08-04).

  So `superdoc-native` is `UNINSTALLED`: it is excluded from superdoc's score
  and reported as a hole in *our* harness. It must never be zero-filled — doing
  so would penalise SuperDoc for a file we never wrote or never committed.
  Reconstructing that harness is required before superdoc's in-process engine
  can be measured at all, and until then superdoc is represented only by its
  Python and TypeScript SDKs.
- **Upgrading to latest LOWERS superdoc's coverage, and we are publishing the
  lower number.** Measured A/B on the same first 25 pairs of
  `corpus/word_based/centralized_mapping.csv`: `superdoc-sdk` **1.19.2
  generated 25/25**, **2.0.0 generates 20/25**. The 5 losses are not adapter
  bugs — they are deliberate engine-side refusals in 2.0.0, which declines
  rather than emit markup it cannot author faithfully:
  - `SOURCE_NOT_COMPLETE` ("synchronous compare capture requires a terminal
    source-complete posture"). Permanent, not a race — it still fails after 6
    retries. The async capture path has an `allowIncompleteSource` escape
    hatch, but `doc.diff.capture` declares only `{doc, sessionId}`, so the SDK
    cannot reach it.
  - `diff.apply` refusing families deferred this release (`tracked-changes`,
    `header-footer-parts`) — sources that already carry tracked changes.

  This is the sharp edge of "benchmark the latest version": the latest is
  sometimes *worse on coverage* because it got stricter. We publish 2.0.0
  because that is what a user installs today, and we publish this paragraph
  next to it so the drop is not mistaken for a capability regression we
  discovered. Scoring the refusals as misses is the honest reading — the
  current release genuinely cannot redline those pairs — but a vendor that
  refuses rather than emits garbage is behaving *better* than one that emits
  garbage, and a pixel score cannot see that difference.

- **Full-corpus result on 2.0.0 (2026-08-04): mean 45.19, median 46.72, but
  n=331 of 763.** The engine declined 432 pairs, so the ITT figure is roughly
  **19.6** — most of it zero-fill for output that was never produced. Read that
  number with the paragraph above: those are *deliberate refusals*, not crashes.
  The 1.19.2 engine attempted far more of the corpus.

  This is the hardest fairness call in the ledger and it is being made in the
  open: policy is to benchmark the **latest released version**, because that is
  what a user installs today, and 2.0.0 is what they get. The consequence is
  that superdoc's headline drops sharply for having become *more* conservative.
  A tool that refuses a document it cannot render faithfully is behaving better
  than one that emits broken markup, and a pixel-vs-oracle score is structurally
  incapable of rewarding that. Anyone quoting superdoc's ITT number without this
  paragraph is misrepresenting them.

  Consequence for the tables (not yet done): superdoc should carry **two
  labelled rows** — latest (2.0.0) as the headline, and the last
  wider-coverage release (1.19.2) beside it — the same treatment the docxodus
  fork gets. One number cannot express "worse score, better behaviour".

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

### docx-redline-js

| field | value |
|---|---|
| Upstream | `@ansonlai/docx-redline-js` — published **0.2.1** |
| What we actually benchmark | **`@arthrod/docx-redline-js@0.3.0`** — *our own* TypeScript migration, built from the sibling repo `../docx-redline-migration-kit` |
| Harness-assisted | Beyond assisted — it is our fork |

> **The row labelled `docx-redline-js` is not running the vendor's published
> code.** It runs our fork of it.

This is the sharpest labelling problem in the ledger. The vendor column names
AnsonLai's project, and a reader will attribute the score to that project, but
the bytes under test are a migration we wrote and version ourselves. The
`tool_version` string (`0.3.0-ts-migration`) hints at it; the vendor name does
not, and the vendor name is what people read.

It cuts in both directions and neither is acceptable unlabelled: if our
migration is better than upstream we flatter them, and if it is worse we
publish a low score under their name for defects we introduced. The same policy
as docxodus applies and is not yet implemented here:

- the **headline row must be the published upstream release** (0.2.1), because
  that is what a user installs;
- our fork is a **separate, explicitly-labelled row** — ideally under a vendor
  name that is visibly ours, not theirs.

Until that split exists, no `docx-redline-js` number should be published as a
statement about AnsonLai's tool.

One further trap for anyone auditing this by hand: the fork is installed at
`src/neurotic_docx_bench/utils/docx-redline-js/node_modules/`**`@ansonlai/`**`docx-redline-js`
— a directory named for upstream that contains `@arthrod/docx-redline-js@0.3.0`.
Reading the path is not enough; read the `package.json` inside it. (Verified
2026-08-04: that directory and the sibling build both hold `@arthrod` 0.3.0, so
the *measurement* is at least self-consistent — it is the labelling, at every
level, that points at the wrong project.)

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
