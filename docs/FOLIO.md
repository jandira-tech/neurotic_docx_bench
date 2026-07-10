# Folio integration notes

Operational findings for the `folio` vendor (`@stll/folio-core`). Companion to the
`folio` run in `bench.yaml` and the `loadEngine("folio")` adapter in
`scripts/generate-native-redlines.ts`.

## Known corpus failures (not our bugs)

### `vfdsdfcacawesd_suggesting_mixed_edits.docx` — empty comment authors

Two corpus pairs fail at the `generate` stage whenever this file is the base or next:

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
