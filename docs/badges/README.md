# neurotic_docx_bench — Participant SVG Badges

The eight badge styles offered to tools benched in [`neurotic_docx_bench`](https://jandira-tech.github.io/neurotic_docx_bench/) ([repo `README.md`](../../README.md) · [`RESULTS.md`](../../RESULTS.md)). Which tool gets an issue, and with which opener line, is decided by [`OUTREACH_LIST.md`](OUTREACH_LIST.md); the text to paste is [`ISSUE_TEMPLATE.md`](ISSUE_TEMPLATE.md). Open [`preview.html`](preview.html) in a browser to compare every badge on light (`#ffffff`) and GitHub dark (`#0d1117`) surfaces.

Every badge locks monospace glyph widths via SVG `textLength` (`6.8px`/char at `11px`) with `≥10px` container padding so strikethroughs, underlines, and pill borders never clip or overflow across browsers.

## Offered badges

| Option | Badge file | Concept |
| --- | --- | --- |
| 1 | [`redline-14-wml-xml-move-two-line.svg`](redline-14-wml-xml-move-two-line.svg) | Compact two-line WordprocessingML move/redline: `<w:moveFrom>`, `<w:del>`, `<w:ins>`, `<w:moveTo>`. |
| 2 | [`redline-12-move-chill-neurotic-benched.svg`](redline-12-move-chill-neurotic-benched.svg) | Track move: green move-from/move-to (`docx_bench`), red delete (`chill`), blue double-underline insert (`neurotic` \| `BENCHED!`). |
| 3 | [`redline-11-chill-neurotic-benched.svg`](redline-11-chill-neurotic-benched.svg) | Classic inline redline: red strikethrough (`chill`), blue double-underline (`neurotic_docx_bench` \| `BENCHED!`). |
| 4 | [`redline-10-double-strike-legal.svg`](redline-10-double-strike-legal.svg) | Court blackline: double margin change bars, `§`, double red strikethrough (`neurotic`), double green underline (`benched!`). |
| 5 | [`redline-16-inline-swap-chill-green.svg`](redline-16-inline-swap-chill-green.svg) | Inline swap: red strikethrough (`chill`) → green double-underline (`neurotic_docx_bench` \| `BENCHED!`). |
| 6 | [`redline-17-inline-swap-chill-dark.svg`](redline-17-inline-swap-chill-dark.svg) | Dark mode (`#0f172a`): coral strike (`chill`), sky-blue double-underline (`neurotic` \| `BENCHED!`). |
| 7 | [`redline-19-inline-swap-forgiving-neurotic.svg`](redline-19-inline-swap-forgiving-neurotic.svg) | Inline swap: red strikethrough (`forgiving`) → blue double-underline (`neurotic` \| `BENCHED!`). |
| 8 *(docxodus only)* | [`docxodus-maize-blue.svg`](docxodus-maize-blue.svg) | Custom for docxodus: University of Michigan maize `#FFCB05` and blue `#00274C` — `docxodus` in blue with maize double-underline insertion, `BENCHED!` on a maize field. |

Embed pattern (badge image from this repo on `main`, link to the visual navigator):

```markdown
[![neurotic_docx_bench](https://raw.githubusercontent.com/jandira-tech/neurotic_docx_bench/main/docs/badges/<file>.svg)](https://jandira-tech.github.io/neurotic_docx_bench/)
```
