# comment_balloons_0929: when Word for Mac draws no comment balloon

Synthetic A/B documents from the 2026-09-29 investigation of why Word draws no comment
balloons for 37 of the 151 corpus documents that hold comments, while jubarte's and
docxodus's redlines of the same pairs get balloons. Every PDF here is Word for Mac
(16.114) exporting the docx through `scripts/word_pdf.py`; the balloon count is the number
of `Commented [` labels in the PDF text (`scripts/ab.py count`).

## The rule

A comment gets a balloon in Word's PDF when

1. the body references it (`w:commentReference`), and
2. its `w:commentRangeEnd`, if it has one, is **live**: inside a paragraph with content
   before it in that paragraph (text, deleted text, a drawing, object, symbol, tab, or
   another comment's reference mark), and
3. for a reply (`w15:paraIdParent` in `commentsExtended.xml`), its parent gets one.

A range end at body level (between paragraphs or after `</w:tbl>`), or first in a paragraph
before any content, is **dead**: Word draws no balloon for that comment or its replies,
and with no balloon on the page it draws no markup pane either (the page stays 612 pt wide).

`scripts/survey5.py` applies the rule to the 151 corpus documents: the predicted balloon
count matches Word's exactly for 149, and it predicts zero for all 37 zero-balloon
documents. Two documents were unexplained by that reading, `1672057675_485599b4e9_rejected_tracking`
(Word 4, predicted 2) and `6ef6726c28_comments_complex_style_attr_word_redline_accepte`
(Word 1, predicted 0); round 6 and `survey6.py` (2026-10-03) close them: a range end with
its own start before it in the paragraph is live, 151/151.

## Rounds

| round | base | what varies | finding |
|---|---|---|---|
| R1 | Word's compare of `b175a00954_file_27` vs `f32428a03a_file_28` (0 balloons) | sections, orientation | not the cause |
| R2 | same | drops chunks of body blocks; `R2_99_drop_all_unmarked` keeps only the comment-bearing blocks | still 0 balloons on 2 pages |
| R3 | `R2_99` | per comment-id removal (4, 5, 11, 12, 296, 297); no extended comment parts | all 0: not one comment, not the extended parts |
| R4 | `R3_keep_4` (one comment) | table, tracked changes, page break, reference layout | balloon only when the range end moves into the paragraph (`R4_02`) or a simple paragraph holds the whole comment (`R4_07`, `R4_08`) |
| R5 | plain paragraphs, one comment | where the range end and the reference sit | end after content: 1 balloon; end at body level or first in its paragraph: 0; the reference's place does not matter |
| AB2-AB4 | jubarte's redline (4 balloons) with single parts from Word's compare, and the reverse | settings, content types, rels, comments parts, styles | not the cause (document.xml is) |
| R6 (2026-10-03) | plain paragraphs, one comment, an EMPTY range | start and end adjacent or with an empty `w:t` run between; styled or plain reference; a stray start of another comment first; the paragraph first, last, only, with pPr, with text after the reference (13 shapes) | all 13 get a balloon; the end-first-in-paragraph control (R5_04) stays dead. So a range end with its own start before it in the paragraph is live: `survey6.py` predicts 151/151 (`6ef6726c28` and `1672057675` explained). The R5-era reading of the empty-`w:t` shape as dead was wrong. |

`word_invalid/` holds five R3 variants as first generated: a comment deleted from
`comments.xml` while a `w:commentReference` to it stayed in the body. Word answers
"Word found unreadable content ... Do you want to recover the contents?" for them.

## What it means for the bench

Word's compare keeps the source's range-end layout (body level after a table, a reply's
end right after its parent's reference), so Word's reference PDF has no balloons for
those comments. jubarte 0.9.3 moves the range end into the paragraph after the deleted
text, a live position, so Word draws balloons that Word's own compare does not have; those
pages widen and score low for a layout choice, not for a wrong change. To match Word, a
tool has to keep a range end where the source put it.

This folder holds the generators (`round1.py` ... `round5.py`), the harness (`ab.py`,
`blocklib.py`) and the truth tables (`survey.py` ... `survey5.py`, `survey5.json`).

The A/B documents and PDFs (`ab_docx/`, `ab_pdf/`, `docx/`, `pdf/`, `word_invalid/`) are
archived outside the repo in `~/temp/T/grok_run_archive/comment_balloons_0929/`.
