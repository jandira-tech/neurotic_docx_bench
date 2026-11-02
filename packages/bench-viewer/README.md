# @jandira-tech/bench-viewer

Framework-free HTML renderers for `neurotic_docx_bench` scores. Pure
functions that return HTML strings; no runtime dependencies.

The markup is jubarte.pro's, byte for byte: the same class names
(`bench-table`, `t-row`, `bench-cols`, `bar`, `headline`, `state-row`,
`bar-row`…), so a page built here and a page built there read the same. Two
skins ship with it: `themes/jubarte.css` (jubarte.pro's rules) and
`themes/arthur-law.css` (the arthur.law look).

## Use

```ts
import { parseScores, renderBadge, renderTable } from "@jandira-tech/bench-viewer";

const scores = parseScores(JSON.parse(await readFile("scores.json", "utf8")));
const html = `${renderBadge(scores)}${scores.tables.map(renderTable).join("\n")}`;
```

`parseScores` validates the document field by field and throws a `TypeError`
naming the bad path (`scores: tables[0].rows[0].median must be a number`).

| Function                       | Markup                               |
| ------------------------------ | ------------------------------------ |
| `parseScores(json)`            | the validated `Scores`               |
| `esc(value)`                   | one text value, escaped              |
| `renderRow(row)`               | one table row                        |
| `renderTable(table)`           | one table section                    |
| `renderHeadlines(headlines)`   | the headline cells                   |
| `renderStates(states, label?)` | the states section                   |
| `renderBars(groups)`           | the home-page bar groups             |
| `renderMethod(points)`         | the method cards                     |
| `renderBadge(scores, tag?)`    | `bench <version> · generated <date>` |
| `renderLegend()`               | what the marks mean                  |

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
pnpm --filter @jandira-tech/bench-viewer build   # tsc -> dist/ (.js + .d.ts)
pnpm --filter @jandira-tech/bench-viewer test
pnpm --filter @jandira-tech/bench-viewer check   # biome
```

`prepare` runs `tsc`, so a consumer that installs the package from git gets
the compiled JavaScript: Node does not strip types from files under
`node_modules`.
