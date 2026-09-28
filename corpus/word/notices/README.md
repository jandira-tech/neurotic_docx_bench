# Names in the Word corpus

Every file carries the id of the docx it represents: the first 10 hex digits of the
sha256 of that docx's bytes (sha256[:10] of the docx bytes).

* A file that is not a comparison: `<id>_<name>`, the id at the beginning. Its Word PDF has
  the same stem.
* A file that is a comparison (a Word compare of two documents): `<idA>_<a>__vs__<idB>_<b>_redline_<idC>`,
  the two compared documents with their ids, then `_redline_` and the id of the compare itself
  (a third id, different from the other two). Its Word PDF has the same stem.
* A tool's output for a Word file is the Word stem plus `_<tool>`: `<id>_<name>_<tool>` and
  `<idA>_<a>__vs__<idB>_<b>_redline_<idC>_<tool>`. The scorer keys a candidate by stripping
  that suffix.

Names are lower-cased, anything but `[a-z0-9_-]` becomes `_`, and a name is cut at 48
characters (paths were failing the 256-character limit). The original names are kept in
`RENAMED.csv` (one row per origin file: original, new, id, sha256, set) and in the `names`
column of `documents.csv` and `comparisons.csv`.

Files live by the state of the docx, read from its XML: `clean`, `tracking_without_comments`,
`with_comments_clean`, `with_comments_tracking`. A comparison lives in the state of the compared docx. Under
each state: `docx/`, `pdf/` (the current Word render) and `pdf_prior/` (a render an earlier
Word build made of the same docx, under the same name).

Byte-identical docx from several origins are one file; every origin name and set is recorded
on the one entry. Two different docx sharing an id fail the build.

The other files in this folder are the origins' own notices, copied as found: the license
of the superdoc docx-corpus sample, its NOTICE and manifests, the pair lists, the Word
blacklist and the logs of the compare runs.
