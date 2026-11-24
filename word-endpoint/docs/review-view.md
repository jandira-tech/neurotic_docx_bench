# Review view: Word for Mac's, on this Windows endpoint

The bench's Word oracle (`corpus/word`, every fixed set's `pdf` column) was made by Word for Mac
16.115: Mac Word compared each pair, saved the redline, reopened it and exported it to PDF with
markup. PDFs exported here are scored against those, so this endpoint exports with the same
review settings and the same view. Both are set in code (`word_endpoint/worker.py`), not left to
Word's profile, so a service restart, a machine restart, a reset profile or a new machine
exports the same way.

## Word for Mac's settings

Read from Word 16.115 itself on 2026-11-24 with `scripts/mac-review-view.applescript` (Word >
Preferences > Track Changes holds the same settings in the GUI). The right-hand columns are what
`start_word()` sets on every Word start (`_MAC_REVISION_OPTIONS`; Windows enum values). Windows
Word on this machine already had every one of these values before the change.

| Word for Mac (`settings`) | Mac value | Windows `Options.` | value |
|---|---|---|---|
| inserted text mark | underline | `InsertedTextMark` | 3 `wdInsertedTextMarkUnderline` |
| inserted text color | by author | `InsertedTextColor` | -1 `wdByAuthor` |
| deleted text mark | strike through | `DeletedTextMark` | 1 `wdDeletedTextMarkStrikeThrough` |
| deleted text color | by author | `DeletedTextColor` | -1 `wdByAuthor` |
| revised properties mark | none | `RevisedPropertiesMark` | 0 `wdRevisedPropertiesMarkNone` |
| revised properties color | by author | `RevisedPropertiesColor` | -1 `wdByAuthor` |
| revised lines mark | outside border | `RevisedLinesMark` | 3 `wdRevisedLinesMarkOutsideBorder` |
| revised lines color | red | `RevisedLinesColor` | 6 `wdRed` |
| comments color | by author | `CommentsColor` | -1 `wdByAuthor` |
| move from text mark | double strike through | `MoveFromTextMark` | 1 `wdMoveFromTextMarkDoubleStrikeThrough` |
| move from text color | green | `MoveFromTextColor` | 11 `wdGreen` |
| move to text mark | double underline | `MoveToTextMark` | 4 `wdMoveToTextMarkDoubleUnderline` |
| move to text color | green | `MoveToTextColor` | 11 `wdGreen` |
| inserted cell color | light blue | `InsertedCellColor` | 2 `wdCellColorLightBlue` |
| deleted cell color | pink | `DeletedCellColor` | 1 `wdCellColorPink` |
| merged cell color | light yellow | `MergedCellColor` | 3 `wdCellColorLightYellow` |
| split cell color | light orange | `SplitCellColor` | 5 `wdCellColorLightOrange` |

Mac Word's registry database (`~/Library/Group Containers/UBF8T346G9.Office/MicrosoftRegistrationDB.reg`,
key `Software\Microsoft\Office\16.0\Word\Options`) agrees: `RevModeBalloons=1`,
`RevModeShowSimpleMarkup=0` (all markup), `RevModeShowInk=1`, `RevModeShowAcetateArea=0`,
`TrackFormatting=1`. The other options live in the binary blob `Word\Data\Settings`.

## The view

How Word for Mac opens a saved redline (read for a redline with no comments and one with 15),
and what `export_pdf()` sets before every export, for conversions and for a live comparison alike:

| Word for Mac (`view of active window`) | Mac | Windows `ActiveWindow.View.` | set |
|---|---|---|---|
| revisions mode | in line revisions | `RevisionsMode` | 1 `wdInLineRevisions` |
| revisions view | final | `RevisionsFilter.View` | 0 `wdRevisionsViewFinal` |
| (all markup, `RevModeShowSimpleMarkup=0`) | all markup | `RevisionsFilter.Markup` | 2 `wdRevisionsMarkupAll` |
| show revisions and comments | true | `ShowRevisionsAndComments` | True |
| show insertions and deletions | true | `ShowInsertionsAndDeletions` | True |
| show format changes | true | `ShowFormatChanges` | True |
| show comments | false | `ShowComments` | **True** (below) |

Inline mode still prints comments: their balloons go in a margin pane, as on the Mac. It does not
print "Formatted: …" balloons, which mixed mode (`RevisionsMode = 2`) adds and Word for Mac never
shows. The endpoint used mixed mode for every document with comments until 2026-11-24.

`ShowComments` is the one deliberate difference. On a saved redline it changes nothing (the 24
documents below export the same pages with it on and off), but on a **live** comparison result,
with it off, Word prints no comments at all: `tests/live_check.py` lost both comment texts of
`artifacts/markup-demo/with-comments.docx`. So it is on.

Not readable on the Mac: balloon width, side and print orientation (Word for Mac's dictionary
has no such properties). Windows has `RevisionsBalloonPrintOrientation = 0` (automatic),
balloons on the right, 266.4 pt wide; the Mac and Windows PDFs of the 24 documents below have the
same page sizes (Letter, A4 or landscape, as each document sets them) and the same page
count on 23 of 24.

## What cannot match

* **Colours by author.** Windows Word picks a revision's colour from the author's name: the same
  name gets the same colour in every document ("Comparison" is always green `#498205`, the most
  frequent person author in this sample always purple `#5c2e91`). Word for Mac does not: one
  author name gets different colours in different documents ("Comparison" came out `#d13438`,
  `#7160e8` and `#394146`), so its colour depends on something other than the name. Changing
  Windows Word's user name changes nothing (as Administrator and as Bob, all 24 PDFs have the same
  colours on the same amount of text). No Windows setting reproduces the Mac's colours, and a
  fixed colour on Windows would match them no better. The top revision colour agreed on 0 of 24
  documents.
* **Comments Word for Mac does not print.** On some documents Word for Mac prints no comment
  balloons at all (2 of the 12 with comments below); Windows prints them. This is Word for Mac's
  behaviour per document, not a setting.
* **The comparison itself.** Windows Word 2024 and Word for Mac 16.115 do not produce the same
  redline for every pair; that is the compare, not the view.

## Measured (2026-11-24)

24 of Word for Mac's own redlines from the bench's fixed set `redline_600` (seed 20261124: 12 with
1 to 6 comments, 12 without), exported here through the convert path under each view and scored
against Word for Mac's PDF of the same file with the bench's scorer (144 DPI, every page):

| view | 12 with comments | 12 without | all 24 |
|---|---|---|---|
| mixed with comments (the endpoint before) | 53.59 | 83.04 | 68.31 |
| inline (the endpoint now) | 57.57 | 83.04 | 70.30 |
| Word's view on open, untouched | 57.57 | 83.04 | 70.30 |
| mixed, format changes hidden | 53.59 | 83.04 | 68.31 |

Inline gained on 10 of the 12 documents with comments and lost on none. Documents without comments
are unchanged: they were inline before. Their 83 is the ceiling of Windows-vs-Mac Word on the same
file: author colours and rendering, nothing a view setting reaches.

## Reproducing and checking

```powershell
# What Word here has, and how it opens given documents (run from ssh: it runs in the interactive session)
powershell -ExecutionPolicy Bypass -File scripts\run-in-session.ps1 -ProbeArgs "dump C:\path\redline.docx"
# Export documents under the shipped view and the alternatives
powershell -ExecutionPolicy Bypass -File scripts\run-in-session.ps1 -ProbeArgs "export C:\out endpoint untouched mixed -- C:\path\a.docx C:\path\b.docx"
```

```sh
# What Word for Mac has (opens each document and closes it unsaved)
osascript scripts/mac-review-view.applescript /path/to/redline.docx
```

Every Word start logs `Word revision options match Word for Mac (already set)` or names the options
it had to set. Options set through COM are not written back to Word's profile (a new Word reads
the old value), so this code path is what keeps them; the unit tests in `tests/test_worker.py` pin
both the options and the view, and `scripts\restart.ps1`'s live check pins that comment texts
still print.
