# Upstream note: Docxodus HTML conversion crash on packages without `settings.xml`

**Audience:** someone filing a PR / issue against
[JSv4/Docxodus](https://github.com/JSv4/Docxodus) (and possibly
[JSv4/react-docxodus-viewer](https://github.com/JSv4/react-docxodus-viewer)).

**Context:** this repo ([neurotic-docx-bench](.)) scores DOCX viewers by rendering
them to PDF and pixel-comparing against a Microsoft Word / LibreOffice oracle.
One of the tools under test is **Docxodus** via `react-docxodus-viewer`
(Playwright harness → WASM `convertDocxToHtml`). While running the full
`visual_rendering` corpus (`corpus/word_based/docx_source/`, ~199 docs), the
converter aborted on the majority of fixtures with:

```text
ArgumentNull_Generic Arg_ParamName_Name, part
```

(surfaced from the worker as `Error: ArgumentNull_Generic Arg_ParamName_Name, part`).

That is a **real fidelity / robustness bug**, not a bench harness quirk: Word
opens the same packages without repair prompts, and LibreOffice renders them for
the oracle PDFs. A viewer that claims DOCX support should not hard-crash on
optional package parts Word treats as optional.

---

## Why this is wrong (spec / product)

ECMA-376 / OOXML does **not** require a main-document relationship to
`word/settings.xml` (`DocumentSettingsPart`). A package that only has
`document.xml` + `styles.xml` (plus the usual package scaffolding) is a legal
minimal DOCX. Word opens it. Many generators and test fixtures emit exactly that
shape — including large parts of this bench’s corpus (style demos,
`*_id_paraid_overflow`, `*_style_default_missing`, etc.).

Docxodus’s HTML conversion path, however, **assumes** `DocumentSettingsPart` is
always present and dereferences it unconditionally. The failure is not “bad
input”; it is “optional part missing → null → throw.”

---

## Root cause (exact call site)

During `WmlToHtmlConverter.ConvertToHtml`, every document runs:

```csharp
CalculateSpanWidthForTabs(wordDoc);
```

In `Docxodus/WmlToHtmlConverter.cs`, that helper historically did:

```csharp
// w:defaultTabStop in settings
var sxd = wordDoc.MainDocumentPart.DocumentSettingsPart.GetXDocument();
var defaultTabStopValue = (string)sxd.Descendants(W.defaultTabStop)
    .Attributes(W.val).FirstOrDefault();
var defaultTabStop = defaultTabStopValue != null
    ? WordprocessingMLUtil.StringToTwips(defaultTabStopValue)
    : 720;
```

`OpenXmlPart` extension `GetXDocument` (in `PtOpenXmlUtil.cs`) starts with:

```csharp
if (part == null) throw new ArgumentNullException("part");
```

So when `MainDocumentPart.DocumentSettingsPart` is **null** (no
`word/settings.xml` / no settings relationship), conversion dies with
`ArgumentNullException("part")` before any HTML is produced.

The code already knows the default tab stop is **720 twips** when the setting is
absent — it just never applied that default when the *part* itself is absent.

Nearby code paths already null-check optional parts correctly, e.g. theme
resolution uses `MainDocumentPart?.ThemePart` / `DocumentSettingsPart` with
guards. `CalculateSpanWidthForTabs` was simply missed.

---

## Evidence from this bench

### Correlation (full `docx_source` corpus, published viewer stack)

On a full `docxodus-playwright-rendering` / `visual_rendering` run before the
fix:

| Outcome | Count (approx.) | Package shape |
|---|---|---|
| Scored OK | ~21 | almost all had `word/settings.xml` |
| `ArgumentNull…, part` | ~149 | almost all **lacked** `word/settings.xml` (and usually theme / fontTable too) |

Settings absence was the strong discriminator for this specific exception name
(`part`). A few other exceptions (`NullReference`, `InvalidCast`, blank pages)
remain on hard fixtures and are out of scope for this note.

### Minimal repro package

Any Word-valid package **without** `word/settings.xml` is enough. Example from
this repo (tiny, intentional style fixture):

```text
corpus/word_based/docx_source/1_5_line_spacing_id_paraid_overflow.docx
```

Zip contents (no settings part):

```text
[Content_Types].xml
_rels/.rels
docProps/app.xml
docProps/core.xml
word/_rels/document.xml.rels
word/document.xml
word/styles.xml
```

Open in Microsoft Word → opens cleanly.  
Run through Docxodus `convertDocxToHtml` (main thread or worker) on **≤6.4.0**
published WASM → `ArgumentNullException("part")`.

### Impact numbers (this bench)

| Metric | Published stack (crash) | After null-safe settings fix |
|---|---|---|
| `visual_rendering` docs scored | **21** | **190** |
| Render failures | **178** | **9** |
| Failure mode for the bulk | `ArgumentNull…, part` | gone for no-settings packages |

So this single null-check is not a one-off edge case; it was the dominant failure
mode for an entire real-world-ish fixture set.

---

## Suggested fix (upstream)

In `WmlToHtmlConverter.CalculateSpanWidthForTabs`, treat settings as optional:

```csharp
private static void CalculateSpanWidthForTabs(WordprocessingDocument wordDoc)
{
    // Settings is optional in OOXML. Word opens packages without
    // word/settings.xml. Missing DocumentSettingsPart must not abort conversion.
    var settingsPart = wordDoc.MainDocumentPart?.DocumentSettingsPart;
    var defaultTabStop = 720;
    if (settingsPart != null)
    {
        var sxd = settingsPart.GetXDocument();
        var defaultTabStopValue = (string)sxd.Descendants(W.defaultTabStop)
            .Attributes(W.val).FirstOrDefault();
        if (defaultTabStopValue != null)
            defaultTabStop = WordprocessingMLUtil.StringToTwips(defaultTabStopValue);
    }

    var pxd = wordDoc.MainDocumentPart.GetXDocument();
    // ... remainder unchanged ...
}
```

**Behaviour:**

- With `settings.xml` + `w:defaultTabStop` → unchanged.
- With `settings.xml` but no `defaultTabStop` → still 720 (already the case).
- **Without** `settings.xml` → 720 instead of throw (new).

**Tests to add (suggested):**

1. Minimal package: `document.xml` + `styles.xml` only, one paragraph of text →
   `ConvertToHtml` returns non-empty HTML, no exception.
2. Same package **with** `settings.xml` and `w:defaultTabStop w:val="1440"` →
   conversion still succeeds (regression guard; tab-width math can be asserted if
   you have an existing tab fixture).
3. Optional: pin the exact exception message so a future reintroduction of
   `DocumentSettingsPart.GetXDocument()` without a null check fails CI.

Rebuild the **npm WASM package** after the C# change (`scripts/build-wasm.sh` +
TS/worker bundles) so consumers on the published `docxodus` package get the fix,
not only source-tree users.

---

## What we did locally in this repo (not a substitute for upstream)

For the bench only, under `src/neurotic_docx_bench/utils/docxodus/`:

1. **Engine patch** — same null-safe change as above in the vendored Docxodus tree.
2. **Matched JS + WASM** — rebuilt `Docxodus/npm` and pointed
   `react-docxodus-viewer` at `file:../Docxodus/npm` (`6.4.0-local.1`). Mixing
   published `docxodus@6.2.x` JS with a newer local WASM (or the reverse) fails
   to boot (`.NET` 10 uses `dotnet.boot.js`; older trees used `blazor.boot.json`).
   That is a **packaging / version-coupling** concern for the viewer docs, not
   the settings crash itself.
3. **Harness belt-and-suspenders** — `demo/normalize-docx.ts` can inject minimal
   `settings.xml` / styles / theme / fontTable before convert. Useful for the
   bench; **should not be required** once upstream is fixed. Prefer the engine
   fix so every Docxodus consumer benefits.

Rebuild instructions for the local matched package:
[`src/neurotic_docx_bench/utils/docxodus/react-docxodus-viewer/README.bench.md`](src/neurotic_docx_bench/utils/docxodus/react-docxodus-viewer/README.bench.md).

---

## Secondary findings (optional follow-ups, separate issues)

These showed up after the settings fix unblocked the bulk of the corpus. They
are **not** required for the primary contribution, but they are good candidates
for later issues:

| Symptom | Example fixture(s) | Notes |
|---|---|---|
| `Arg_NullReferenceException` | `strict01`, `ole_object`, `strict01_sdt_controls`, `word_clean_strict01` | Heavier / strict OOXML; separate null path |
| `ArgumentNull…, key` / `, attribute` | `i_am_sharing_…`, `word_tolerated_duplicate_ppr` | Other unconditional map/attribute reads |
| `Arg_InvalidCastException` | `complex_style_attr` | Cast on style attributes |
| Blank page chrome (no ink) | `mcdoc`, `text_box` | Converts enough to paginate but no text/media; harness rejects as blank |

Also worth documenting for consumers: **JS bindings and WASM must ship as a
matched pair**. Publishing WASM from a newer SDK while leaving npm JS on an
older boot layout breaks worker init with opaque “Loading document engine…”
symptoms.

---

## Suggested upstream issue / PR title

> **fix(html): do not crash ConvertToHtml when DocumentSettingsPart is missing**

Body can link this file or paste the “Root cause” + “Suggested fix” + “Minimal
repro package” sections. Point reviewers at `CalculateSpanWidthForTabs` and the
existing 720-twip default already used when `w:defaultTabStop` is absent.

---

## Checklist for a clean contribution

- [ ] C# null-safe `DocumentSettingsPart` in `CalculateSpanWidthForTabs`
- [ ] Unit / conversion test with a package that has **no** `word/settings.xml`
- [ ] Rebuild and publish WASM so npm `docxodus` consumers get the fix
- [ ] (Optional) Scan for other unconditional `DocumentSettingsPart.GetXDocument()`
      on the convert path (`TextReplacer`, `ReferenceAdder`, etc. may be
      compare/edit-only — call that out if you touch them)
- [ ] (Optional, separate PR) Document “JS and WASM versions must match” for the
      viewer / npm README

---

*Written from work in neurotic-docx-bench while scoring Docxodus
`visual_rendering` against the Word/LibreOffice oracle (2026-07).*
