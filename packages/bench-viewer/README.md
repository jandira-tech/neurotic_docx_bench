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

| Function                         | Markup                               |
| -------------------------------- | ------------------------------------ |
| `parseScores(json)`              | the validated `Scores`               |
| `esc(value)`                     | one text value, escaped              |
| `renderRow(row)`                 | one table row                        |
| `renderTable(table)`             | one table section                    |
| `renderHeadlines(headlines)`     | the headline cells                   |
| `renderStates(states, options?)` | the states section                   |
| `renderBars(groups)`             | the home-page bar groups             |
| `renderMethod(points)`           | the method cards                     |
| `renderBadge(scores, tag?)`      | `bench <version> · generated <date>` |
| `renderLegend()`                 | what the marks mean                  |

`renderStates` accepts `{ heading?, label?, table? }`. The caller supplies the
heading, `label` changes a corpus state's display name, and `table` keeps only
the state cells linked to that table id.

Every text value goes through `esc()`.

## Build the page

```bash
node packages/bench-viewer/scripts/build-pages.ts scores.json /tmp/bv-pages
```

writes `index.html` (badge, legend, headlines, every table, the states and the
method) and copies `themes/tokens.css` and `themes/arthur-law.css` beside it.
No git operations, no network.

## Build the package

```bash
pnpm --filter @jandira-tech/bench-viewer build       # tsc -> dist/ (.js + .d.ts)
pnpm --filter @jandira-tech/bench-viewer test
pnpm --filter @jandira-tech/bench-viewer check       # biome
pnpm --filter @jandira-tech/bench-viewer check:dist  # committed dist is current
```
