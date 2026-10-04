# jubarte 0.11.2 on the full 3502 Word compares (2026-10-04)

Lane `jubarte-0.11.2-full`: 2611 redlines by the 0.11.2 release binary (pdf29), 600 of
them byte-identical to the sample lane (`identity_0112_full.tsv`). Word exported 2610 to
PDF; one (`acce1b593c_…_redline_63ea4d3f8d`) failed twice (batch, then alone at 300 s)
and scores 0. It passes the OpenXml validator.

## Same scorer first

`scores_jubarte-0.10.1.json` was scored on 2026-10-01, before bench `0de6361bf`
(2026-10-03) changed `score.py`. The old file is kept as
`scores_jubarte-0.10.1.scorer-pre-0de6361.json`; the 0.10.1 PDFs were rescored with the
current scorer. Every number below compares the two lanes under the same scorer
(`paired_0101_0112.py`, bootstrap 95% intervals, seed 20261004).

## Overall score: flat, and its >=90 count is a colour lottery

| | n | 0.10.1 | 0.11.2 | delta [95%] | >=90 |
|---|---|---|---|---|---|
| all | 3496 | 75.16 | 75.17 | +0.01 [-0.26, +0.28] | 615 -> 427 |
| corpus | 2980 | 74.63 | 74.29 | -0.35 [-0.63, -0.05] | 575 -> 338 |
| fresh | 516 | 78.21 | 80.30 | +2.09 [+1.57, +2.61] | 40 -> 89 |

The 427 compares that fell below 90 kept their ink (median ink_jaccard delta -0.001),
their text boundary (median 0) and their page count (0 changes); 354 of them now sit in
the 80-85 band, the harness colour cap. Probe `0086695f46_file_124__vs__d8f8e09b6e_file_125`:
Word's compare and the 0.10.1 PDF draw the marks in the 0078D4 blue family, the 0.11.2 PDF in
D13438 red. Same marks, a different Word-session author colour. The overall score's >=90
count, and part of its mean, measure which colour Word's export session picked.

## Colour-free terms: 0.11.2 is better

| term | oracle | n | 0.10.1 | 0.11.2 | delta [95%] | up / down (>0.01) |
|---|---|---|---|---|---|---|
| ink_jaccard | all | 3431 | 0.7299 | 0.7460 | +0.0161 [+0.0125, +0.0196] | 447 / 247 |
| ink_jaccard | corpus | 2941 | 0.7117 | 0.7300 | +0.0183 [+0.0143, +0.0223] | 389 / 174 |
| ink_jaccard | fresh | 490 | 0.8393 | 0.8424 | +0.0031 [-0.0022, +0.0087] | 58 / 73 |
| text_boundary | all | 3406 | 0.8009 | 0.8168 | +0.0159 [+0.0125, +0.0199] | 194 / 52 |
| text_boundary | corpus | 2900 | 0.7869 | 0.8036 | +0.0167 [+0.0126, +0.0210] | 169 / 44 |
| text_boundary | fresh | 506 | 0.8813 | 0.8926 | +0.0113 [+0.0051, +0.0186] | 25 / 8 |

Page count equal to Word's: 3197 -> 3204 of 3496.

## Word's per-session font cache inflates the colour-free gain

The largest loss, `b6bcd5d86d_file_198__vs__7f73d1af22_file_199` (ink 1.000 -> 0.145), is
not jubarte's: both redlines carry `Liberation Serif` with altName `Hiragino Mincho ProN
W3`. Word's compare and the 0.10.1 PDF embed HiraMinProN-W3; the 0.11.2 full-lane export
embedded TimesNewRomanPSMT. Converted alone in a fresh Word session
(`jubarte-loop/release_0.11.2/colour_probe/fresh_session.sh`), the same 0.11.2 docx embeds
HiraMinProN-W3 + Cambria, as Word's compare does. Word caches the face it substitutes for
a missing font name for the rest of a session.

`font_session_split.py` lists every compare whose ink moved by more than 0.10 (177) and
whether the fonts moved with it: gains 53 font-moved / 65 same fonts / 35 other; losses
5 / 12 / 7. The session noise leaned toward 0.11.2. Without the 58 font-moved compares:

| term | n | delta [95%] |
|---|---|---|
| ink_jaccard | 3373 | +0.0081 [+0.0057, +0.0106] |
| text_boundary | 3348 | +0.0071 [+0.0046, +0.0095] |
| overall_score | 3438 | -0.42 [-0.68, -0.19] (colour lottery still in it) |

So 0.11.2 is better on marks and text, by about half the raw paired gain. Smaller font
moves (|ink delta| <= 0.10) are still inside these numbers.

## Open

- Export lanes so that no document inherits another's font substitution: one Word
  session per document is exact but slow; a cheaper check is to re-export, alone, every
  compare whose embedded fonts differ from Word's compare and keep the fresh PDF.

- The scorer should map the candidate's author colours onto the reference's in order of
  first appearance (Word's own rule, see the author-colour notes) before the colour term,
  so lanes exported in different Word sessions compare on marks, not on the lottery.
- Read the largest losses by hand (`paired_0101_0112.py` lists them), starting with
  `b6bcd5d86d_file_198__vs__7f73d1af22_file_199` (100 -> 54.90).
