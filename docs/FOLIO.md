# Folio integration notes

Operational findings for the `folio` vendor (`@stll/folio-core`). Companion to the
`folio` run in `bench.yaml` and the `loadEngine("folio")` adapter in
`scripts/generate-native-redlines.ts`.

## Harness-assisted disclosure: none as of `@stll/folio-core` 0.15.13

The `folio` `script_redlines` run is **not** harness-assisted. The adapter is a
one-call passthrough to folio's own API:

```ts
const result = await generateRedlineDocx(toAB(base), toAB(next), { author: "folio" });
return new Uint8Array(result.buffer);
```

Everything the bench scores — block alignment, word-level segmentation, tracked-change
markup, story coverage — is folio's. The only harness code in the path is the
`Uint8Array`→`ArrayBuffer` copy required by folio's own signature, and the manifest
walk / file naming shared by every vendor.

### What this used to look like (and why the old folio numbers were wrong)

Before 0.13.0 folio had no single base+next→redline entry point, so the adapter
composed two APIs by hand: `@stll/folio-agents.compareDocxVersions` for the diff, then
`FolioDocxReviewer.applyOperations(ops, {mode:"tracked-changes"})` to write it. That
translation was **silently wrong**.

`compareDocxVersions` emits changes in *revised-side* document order, and a
`modified` entry's `blockId` is the *revised-side* id. `applyOperations`'
`replaceInBlock` anchors against a *base-side* id from the reviewer's own snapshot.
The adapter fed one into the other, so `baseIds.has(c.blockId)` was false for every
`modified` entry, every `replaceInBlock` op was dropped, and when a pair's changes were
all modifications `ops.length === 0` hit an identity fallback that returned the **base
document unchanged**. Folio scored as "produced a redline with no changes" on pairs it
had actually diffed correctly.

Measured on the first 60 manifest pairs, at the versions each adapter shipped with:

| | pairs with tracked changes | `modified` diff entries translated |
|---|---|---|
| 0.3.1 + composed adapter | 36 / 60 | 0 / 157 |
| 0.15.13 + `generateRedlineDocx` | 59 / 60 | n/a — folio does it |

The one remaining pair without tracked changes
(`bold_text_formatting_demo_id_paraid_overflow_2` → `bold_text_formatting_demo_id_paraid_overflow`)
is folio reporting zero changes for itself, not a harness fallback — there is no
identity path in the adapter any more.

**Any folio `script_redlines` number published before this change measured our
translation, not folio.**

## Known corpus failures (not our bugs)

### `vfdsdfcacawesd_suggesting_mixed_edits.docx` — empty comment authors

> **RESOLVED upstream in `@stll/folio-core` 0.15.13** (verified 2026-08-04): folio
> relaxed the empty-author rule. `FolioDocxReviewer.fromBuffer` and
> `generateRedlineDocx` both accept this file now (29 operations applied against
> `yellow_highlight_demo_id_paraid_overflow`), so both pairs below generate. The
> analysis is kept because it documents why they failed under the 0.3.1 pin and what
> the correct response to that class of failure is.

Two corpus pairs failed at the `generate` stage whenever this file was the base or next:

- `verdana_italic_centered_demo_id_paraid_overflow_vfdsdfcacawesd_suggesting_mixed_edits`
- `vfdsdfcacawesd_suggesting_mixed_edits_yellow_highlight_demo_id_paraid_overflow`

**Symptom:**
```
[generate]: Failed to parse DOCX: Parsed DOCX produced an invalid document model:
DOCX model error at package.document.comments[3].author: Comment author is empty.
DOCX model error at package.document.comments[4].author: Comment author is empty.
... (through comments[14])
```

**Root cause (verified 2026-07-07):**
The source DOCX `corpus/word_based/docx_source/vfdsdfcacawesd_suggesting_mixed_edits.docx`
carries 15 comments in `word/comments.xml`; **12 of them have `w:author=""`** (empty
string). The first three are `Online User` (a Google Docs export signature); the rest
are blank.

```
authors = ['Online User', 'Online User', 'Online User', '', '', '', '', '', '', '', '', '', '', '', '']
```

**This is folio-native, not our adapter.** The throw site is folio's own parser:
`@stll/folio-core/dist/docx/parser.js:183`, where
`validateFolioDocumentModel(document)` runs folio's valibot schema and rejects empty
comment authors. Confirmed by calling **only** `FolioDocxReviewer.fromBuffer(buf)` on the
file — no diff, no `applyOperations`, none of our adapter code in the path — and
reproducing the identical error.

**Word and LibreOffice tolerate this file normally** — Word renders and compares it
without complaint, and LibreOffice renders it to the oracle PDF that the bench scores
against. The bench's own `bench accept` path (via `balalofernandez/docx-revisions`) also
accepts it. Only folio's stricter document model rejects it.

**Do not "fix" this by:**
- sanitizing the source DOCX's `w:author` attributes — that mutates corpus inputs and
  would silently hide a real fidelity gap;
- adding a pre-parse workaround in the adapter — it would mask a genuine folio strictness
  decision and break the fairness invariant (each tool gets the same corpus bytes).

The error is the contract working as designed: caught, wrapped as
`{doc, stage: "generate", error}`, recorded in the JSONL, run continues. ~200 other
pairs generate fine.

**If folio upstream relaxes the empty-author rule** (or the corpus fixture is regenerated
with non-empty authors), these pairs will start generating without any change here.
That is exactly what happened at 0.15.13 — see the RESOLVED note at the top of this
section. No adapter change was needed.
