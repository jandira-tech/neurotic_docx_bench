# @jandira-tech/bench-viewer

Framework-free HTML renderers for `neurotic_docx_bench` scores. Pure
functions that return HTML strings; no runtime dependencies.

The markup follows jubarte.pro's class names and structure. For values without
HTML metacharacters it is byte for byte identical to jubarte's templates. Where
jubarte's source interpolates prose without escaping it, bench-viewer escapes
the five HTML metacharacters; `test/fixtures/scores-raw.json` proves that
invariant against the raw `bench.*` facts.

Two skins ship with it: `themes/jubarte.css` (jubarte.pro's light and dark
rules) and `themes/arthur-law.css` (the arthur.law look).

Two pages come out of the same scores file. The **jubarte page** is the
product's own framing: headline cells ("jubarte vs X"), the author's rows
marked with a dagger and a highlighted background. The **leaderboard page**
(`buildLeaderboardPage`) is the arthur.law page benchmarks.law wears: the
scores and nothing else — no headlines, no "ours" rows, no dagger — every
tool ranked in every table, the leader of each table named above it, the
full-corpus tables first and the release's own samples after them.

## Install

The compiled `dist/` is committed, so a git dependency has a ready-to-import
fallback. With pnpm 12, install the pinned commit without running dependency
build scripts:

```bash
pnpm add --ignore-scripts "@jandira-tech/bench-viewer@github:jandira-tech/neurotic_docx_bench#<commit>&path:packages/bench-viewer"
```

`--ignore-scripts` installs the committed `dist/` directly, so the consumer
needs no `allowBuilds` entry. The package keeps `prepare: tsc` for source
checkouts and publishing; once the package is published to npm, a normal
`pnpm add @jandira-tech/bench-viewer` needs no special flag.

## Use

```ts
import { parseScores, renderBadge, renderTable } from "@jandira-tech/bench-viewer";

const scores = parseScores(JSON.parse(await readFile("scores.json", "utf8")));
const html = `${renderBadge(scores)}${scores.tables.map(renderTable).join("\n")}`;
```

`parseScores` validates the document field by field and throws a `TypeError`
naming the bad path (`scores: tables[0].rows[0].median must be a finite number`).
Scores must be finite values from 0 through 100, document counts must be
non-negative integers, and `repo` and `viewer` must be absolute HTTP(S) URLs.

| Function                                 | Markup                               |
| ---------------------------------------- | ------------------------------------ |
| `parseScores(json)`                      | the validated `Scores`               |
| `esc(value)`                             | one text value, escaped              |
| `buildLeaderboardPage(scores, options?)` | the whole leaderboard page           |
| `renderRow(row)`                         | one table row                        |
| `renderTable(table)`                     | one table section                    |
| `renderTableHead()`                      | the head row of a table              |
| `renderHeadlines(headlines)`             | the headline cells                   |
| `renderStates(states, options?)`         | the states section                   |
| `renderBars(groups)`                     | the home-page bar groups             |
| `renderMethod(points)`                   | the method cards                     |
| `renderProvenance(provenance)`           | the provenance section               |
| `renderBadge(scores, tag?)`              | `bench <version> · generated <date>` |
| `renderLegend()`                         | what the marks mean                  |

`renderStates` accepts `{ heading?, label?, table? }`. The caller supplies the
heading, `label` changes a corpus state's display name, and `table` keeps only
the state cells linked to that table id.

`buildLeaderboardPage` accepts `{ tag?, samplesHeading?, title?, description? }`.
It drops the affiliation dagger from the tool names, drops the "ours" marking
from the rows and the states, drops the method card that explains the dagger
(it would be false on a page that marks nothing), and leaves out the headline
cells entirely.

Every text value goes through `esc()`.

## Build the page

```bash
node packages/bench-viewer/scripts/build-pages.ts scores.json /tmp/bv-pages
node packages/bench-viewer/scripts/build-pages.ts scores.json /tmp/bv-jubarte --theme jubarte
```

writes `index.html` and copies `themes/tokens.css`, `themes/arthur-law.css`
and `themes/jubarte.css` beside it, so the directory opens as a page on its
own. No git operations, no network.

`--theme` picks the page:

| Theme        | Page                                                                      |
| ------------ | ------------------------------------------------------------------------- |
| `arthur-law` | the leaderboard page (the default): the scores, ranked                    |
| `jubarte`    | the jubarte page: the headlines, the "ours" rows, the dagger, jubarte.css |

`test/fixtures/jubarte-page.html` is the jubarte page as it was before the
leaderboard page existed; the build-pages test compares the `jubarte` theme
against it byte for byte.

## Build the package

```bash
pnpm --filter @jandira-tech/bench-viewer build       # tsc -> dist/ (.js + .d.ts)
pnpm --filter @jandira-tech/bench-viewer test
pnpm --filter @jandira-tech/bench-viewer check       # biome
pnpm --filter @jandira-tech/bench-viewer check:dist  # committed dist is current
```
