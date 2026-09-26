<!--
SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
SPDX-License-Identifier: AGPL-3.0-only
-->

# Messed redline fixtures (negative controls), 2026-09-25

Every file under `redlines/` and `pdfs/` is deliberately wrong for the name it
carries, except R. R is a real Word PDF from the English run that turned out
to be wrong. The identity checkers must reject every file here.

- **Sources.** `a/` and `b/` hold the source documents the names refer to.
- **Build.** `build_messed_fixtures.sh OUT` rebuilds the fixtures from
  `grok_run`.
- **Real pairs used.** `pairs.txt` lists them.
  - X = `23ba7149…__vs__0ba09db4…`
  - Y = `782587f6…__vs__7672b472…`
  - Z = `fd826863…__vs__3a5aa393…`
  - R = `0217951c…__vs__08c53c4f…`

Commands:

    uv run --script scripts/check_redline_identity.py --a scripts/messed_fixtures/a \
        --b scripts/messed_fixtures/b --redlines scripts/messed_fixtures/redlines
    uv run --script scripts/detect_review_balloons.py --src scripts/messed_fixtures/pdfs \
        --a scripts/messed_fixtures/a --b scripts/messed_fixtures/b

## docx: `check_redline_identity.py` catches all 4

| id | file name (base vs revision) | what it really is | before/base | after/revision | verdict |
|---|---|---|---|---|---|
| D1 swapped | Y's name (`782587f6… vs 7672b472…`) | X's redline | 0.00 | 0.00 | BAD ✔ |
| D2 half | Z's A with Y's B (`fd826863… vs 7672b472…`) | Z's redline | 1.00 | 0.00 | BAD ✔ |
| D3 leftover B | X's name | the plain B source, saved as the redline | 0.40 | 1.00 | BAD ✔ |
| D4 leftover A | Z's name | the plain A source, saved as the redline | 1.00 | 0.00 | BAD ✔ |

Result: `checked=4 bad=4`, exit 1.

**Margin note (D3).** The failing side scores 0.40 against a 0.9 threshold,
so it is caught. A B document that happens to share 90% of A's 40-character
windows would slip through.

## pdf: `detect_review_balloons.py --a --b` missed 1 of 5 (fixed, now 5 of 5)

| id | file name | what it really is | score_base | score_revision | verdict |
|---|---|---|---|---|---|
| P1 swapped | Y's name | X's Word redline PDF | 0.004 | 0.007 | no ✔ |
| P2 half | Z's A with Y's B | Z's Word redline PDF | 1.000 | 0.168 | no ✔ |
| **P3 leftover B** | X's name | **Word PDF of the plain B source only** | **0.760** | 1.000 | **yes ✘ (missed) → now no ✔ (base's own words 0/6)** |
| P4 leftover A | Z's name | Word PDF of the plain A source only | 1.000 | 0.111 | no ✔ |
| R real | `0217951c… vs 08c53c4f…` | Word's PDF of a verified redline docx; B's inserted 21-column table is absent from the PDF (even without clipping) | 0.999 | 0.309 | no ✔ |

The redline docx behind R passes both identity checks: `check_redline_identity`,
and an independent 5-gram check with an argmax over all 500 A and 500 B. So the
defect is in Word's PDF of that document, not in the pairing.

## Script findings

**Fixed 2026-09-25 (Arthur asked):** `detect_review_balloons.py` now also requires each side's
*distinctive* words (words the other file lacks, letters split from digits) at >= 0.40 whenever a side has
>= 5 of them, and exits 1 on any "no" or unreadable PDF. Result on these fixtures: yes 0, no 5, exit 1.
On the 385 real English redline PDFs only R fails (revision 0.130); real pairs stay >= 0.53.
Tests: `tests/test_detect_review_balloons.py` (lone revision PDF, near-identical redline, glued figures,
command exit code on this folder).

Original findings:

1. **`detect_review_balloons.py` passes P3.**
   - `_NAME_MIN = 0.60` fuzzy word recall is too loose. Common English words
     give an unrelated document 0.76 recall.
   - P3 is exactly the failure the checker exists for: a leftover document
     saved under a pair's name.
   - Possible fixes: raise the threshold; use windows or n-grams as
     `redline_identity.coverage` does rather than single words; or require
     the base side to beat the revision's own PDF by a margin.
2. **`detect_review_balloons.py` exits 0 even when rows say "no".**
   - A pipeline cannot gate on it.
   - `check_redline_identity.py` exits 1 on any bad file, which is the
     behaviour to copy.
