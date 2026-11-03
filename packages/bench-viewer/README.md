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

## The case browsers and the speed page

`src/cases.ts` and `src/speed.ts` are the other half of the package: the pages
that show the _cases_ (the per-document pages of every engine, beside Word's
own) and the _speed_ benchmark. They read the release, not a copy of it:

- `cases/index.json` (the `CasesIndex`) holds the shard directory, the engine
  list and the public asset base. One shard per group (`cases/<kind>/<group>.json`)
  is fetched when the group is opened, so a page opens on one group.
- `speed.json` (the `Speed`) holds the tasks, their coverage, their tables and
  their notes.

Both modules are two layers: a **render layer** that is pure (data in, HTML
string out) and a **wiring** that fetches, keeps the state and puts the strings
where they belong (`mountCasesPage`, `mountSpeedPage`). The render layer is
what the tests drive.

| Function                                                 | Markup                                                                    |
| -------------------------------------------------------- | ------------------------------------------------------------------------- |
| `parseCasesIndex(json)`                                  | the validated `CasesIndex`                                                |
| `parseCaseShard(json)`                                   | the validated `CaseShard`                                                 |
| `parseCase(json, path, kind?, group?)`                   | one validated `Case`                                                      |
| `parseSpeed(json)`                                       | the validated `Speed`                                                     |
| `renderCaseStrip(options)`                               | one lane's column of pages                                                |
| `renderCaseHead(options)`                                | one lane's header                                                         |
| `renderCaseGrid(options)`                                | the whole grid                                                            |
| `renderCaseList(options)`                                | the case list in the side panel                                           |
| `renderScoresTable(options)`                             | the score table                                                           |
| `renderEngineToggles(options)`                           | the engine toggles                                                        |
| `renderOverlay(options)`                                 | the overlay (one lane over another)                                       |
| `renderCasesPage(options)`                               | the whole browser page                                                    |
| `renderCasesLegend(options)`                             | the legend                                                                |
| `renderSpeed(speed)`                                     | the whole speed page body                                                 |
| `renderSpeedTable(table)`                                | one timing table                                                          |
| `renderSpeedNote(note)`                                  | one note                                                                  |
| `renderSpeedPage(options)`                               | the whole speed page                                                      |
| `inlineCode(text)`                                       | escaped text, `backtick` spans as `<code>`                                |
| `resolveAssetUrl(base, path)`                            | a `~/` path against the asset base                                        |
| `safeAssetUrl(base, path)`                               | the same, or `""` when it is not http(s)                                  |
| `resolveFileUrl(base, path)`                             | a `~/` path against the files base                                        |
| `safeFileUrl(base, path)`                                | the same, or `""` when it is not https                                    |
| `caseFilesUrl(base, case)`                               | the case's own folder on the files base                                   |
| `formatPageScore(value)`                                 | one page score: one decimal, or `—`                                       |
| `randomIndex(length, random?)`                           | the index a random draw lands on                                          |
| `pickRandomCase(cases, random?)`                         | a random case of the list                                                 |
| `shardUrl(indexUrl, path, base?)`                        | a shard's URL in the release                                              |
| `caseHash(group, case)` / `parseCaseHash(hash, groups?)` | the `#<group>/<case>` link                                                |
| `laneState(case, engine)`                                | what a lane holds: measured, failed, dropped, unavailable, not applicable |

Every data string — the case id, the group name, the version label, the error
message, the asset path — goes through `esc()`. The asset URL is refused when
it is not an http(s) URL, so it cannot become a `javascript:` source.

A lane's state comes from the case's own lists: `not_applicable` and
`unavailable` are said so in the column and in the engine bar, `dropped` lanes
are folded away behind the "+N more" button, and a failed lane keeps its error
under its pages.

### What plan 7 added (issue #132)

The case browsers gained what only jubarte.pro had. The contract grew three
optional fields, and the viewer reads them when the release carries them:

| Field                              | What the page does with it                                                      |
| ---------------------------------- | ------------------------------------------------------------------------------- |
| `Case.page_scores` (lane → scores) | the score of each shown page, under the page (`—` when the page was not scored) |
| `Case.files` (lane → path)         | a `files ↗` link per lane, and one `files on Hugging Face ↗` link for the case  |
| `CasesIndex.files_base`            | the public base the two above resolve against (the record on Hugging Face)      |

A release without them renders exactly as it did before — the page scores and
the file links are simply absent (`test/fixtures/cases-legacy.json` pins the
old output).

The page shows **up to 12 pages** of a case (`PAGE_STEP`), the cap the shown-page
renderer stores; the "more pages" button still grows the strip. And a URL that
names no case opens on a **random** one, the old gh-pages viewer's
`if (!linked) pickRandom()`. The random source is a parameter
(`mountCasesPage({ random })`), so a seeded generator makes the page
deterministic under test.

## Build the page

```bash
node packages/bench-viewer/scripts/build-pages.ts scores.json /tmp/bv-pages
node packages/bench-viewer/scripts/build-pages.ts scores.json /tmp/bv-jubarte --theme jubarte
node packages/bench-viewer/scripts/build-pages.ts --release results/release /tmp/bv-site --scores results/scores.json
node packages/bench-viewer/scripts/build-pages.ts --release results/release /tmp/bv-site --scores results/scores.json --fonts site/_static/fonts
```

writes `index.html` and copies `themes/tokens.css`, `themes/arthur-law.css`,
`themes/jubarte.css` and `themes/cases.css` beside it, so the directory opens
as a page on its own. No git operations, no network.

`--theme` picks the page:

| Theme        | Page                                                                      |
| ------------ | ------------------------------------------------------------------------- |
| `arthur-law` | the leaderboard page (the default): the scores, ranked                    |
| `jubarte`    | the jubarte page: the headlines, the "ours" rows, the dagger, jubarte.css |

`--release` builds the **whole site** from a release bundle:

```
<outdir>/index.html            the leaderboard, from scores.json
<outdir>/cases/index.html      the conversion browser
<outdir>/redlines/index.html   the redline browser
<outdir>/speed/index.html      the speed page
<outdir>/release/cases/…       the index and one shard per group
<outdir>/release/speed.json    the speed release
<outdir>/js/…                  the compiled modules the pages import
<outdir>/_static/fonts/…       the fonts, when --fonts is given
```

The pages fetch the release's own files; no data is inlined in them. The
`build:pages` script does this for the gh-pages worktree:

```bash
pnpm --filter @jandira-tech/bench-viewer build:pages
```

`--fonts <dir>` (release mode only) copies a font directory — the gh-pages
site's `_static/fonts` (Manrope and JetBrains Mono as woff2, plus their
licences) — into `<outdir>/_static/fonts/`, where `cases.css`'s `@font-face`
rules expect them. Without the flag nothing is copied and the pages fall
back to the system font stacks; the package itself ships no binaries.

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
