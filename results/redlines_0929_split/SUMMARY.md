# redlines_0929_split: tool redlines, Accept All / Reject All by Word, vs Word

800 comparisons of `corpus/word/pools/accept_reject_split.csv` (`pool_pairs.csv`): 400 for
`accept_all`, 400 for `reject_all`. Each tool redlines every pair (`run.sh`: jubarte-redlines
0.9.3 native CLI, npm docxodus 12.6.4, superdoc-sdk). Word then accepts or rejects every change
in the tool's redline, by the pair's action, and exports it to PDF (`scripts/word_pdf.py`).
`measure.py` scores that PDF against Word's own compare, accepted or rejected the same way
(`corpus/word/accept_all`, `corpus/word/reject_all`), with the bench's pixel scorer. A pair
with no scored PDF counts 0 in the intent-to-treat (ITT) columns. Per-document rows are in
`scores.jsonl`.

| Tool | Action | Scored /400 | ITT mean | ITT median | Scored-only mean | = 100 | >= 90 | < 50 | Ink Jaccard | Text boundary |
|---|---|---|---|---|---|---|---|---|---|---|
| word-identity | accept_all | 400 | 100.00 | 100.00 | 100.00 | 400 | 400 | 0 | 1.00 | 1.00 |
| word-identity | reject_all | 400 | 100.00 | 100.00 | 100.00 | 400 | 400 | 0 | 1.00 | 1.00 |
| jubarte-rust | accept_all | 400 | 87.56 | 99.70 | 87.56 | 181 | 261 | 33 | 0.80 | 0.94 |
| jubarte-rust | reject_all | 400 | 86.22 | 99.85 | 86.22 | 186 | 260 | 35 | 0.77 | 0.91 |
| docxodus | accept_all | 394 | 90.07 | 99.87 | 91.44 | 166 | 299 | 16 | 0.85 | 0.96 |
| docxodus | reject_all | 385 | 85.38 | 99.80 | 88.70 | 155 | 275 | 26 | 0.80 | 0.94 |
| superdoc | accept_all | 58 | 13.95 | 0.00 | 96.24 | 4 | 52 | 1 | 0.95 | 0.98 |
| superdoc | reject_all | 49 | 11.07 | 0.00 | 90.41 | 1 | 36 | 1 | 0.83 | 0.95 |

The `= 100`, `>= 90` and `< 50` counts and the two docxide metrics are over the scored
documents only.

## Why pairs are missing

- **docxodus, 21 pairs** (6 accept_all, 15 reject_all): Word could not open the redline.
  Two Word passes each timed out or never reached them. A plain Word export of three of them,
  with no Accept or Reject step, also timed out. Opened by hand, one shows Word's "unreadable
  content ... recover?" prompt and another "Word experienced an error trying to open the file".
  jubarte-rust's redlines of the same pairs export fine. The list and the evidence are in
  `docxodus/word_failures.txt`.
- **superdoc, 693 pairs**: the SDK refused to write a redline ("No mutation was performed").
  The most common reasons are tracked shared-definition replacement (175), header/footer
  slot or topology changes (159), deferred settings changes (78), numbering part creation (58)
  or removal (43), and comment topology (37). Every refusal is in
  `superdoc/generate_failures.json`.
- **jubarte-rust**: none. Word's first accept_all pass exported 344 of 400 because Word
  restarted several times mid-batch. The retry pass exported the other 56, which shows those
  failures were Word restarts, not invalid files.

The redline DOCX and the Word PDFs (477 MB) stay out of git; `run.sh` rebuilds them.
