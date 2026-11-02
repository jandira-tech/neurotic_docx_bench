/**
 * Golden renderers copied from jubarte-app at commit ad9b73e.
 *
 * Source files and line ranges:
 * - /Users/arthrod/temp/T/1_jubarte-redlines/jubarte-app/jubarte-site/site/pages/benchmark.ts
 *   lines 17-28 (row), 58-66 (headlines), 68-77 (table), 79-96 (states),
 *   and 107-109 (method)
 * - /Users/arthrod/temp/T/1_jubarte-redlines/jubarte-app/jubarte-site/site/pages/home.ts
 *   lines 177-191 (bar groups)
 * - /Users/arthrod/temp/T/1_jubarte-redlines/jubarte-app/jubarte-site/site/layout.ts
 *   lines 42-52 (esc)
 * - /Users/arthrod/temp/T/1_jubarte-redlines/jubarte-app/jubarte-site/site/data/bench.ts
 *   lines 50-55 (stateLabel)
 *
 * The inline template blocks are wrapped in functions so each golden output can
 * be compared independently. Jubarte's table/headline sorting is page logic and
 * is deliberately not copied: bench-viewer renders the given order.
 */

import type { Headline, HomeGroup, MethodPoint, Row, StateCell, Table } from "../src/types.ts";

const ENTITIES: Record<string, string> = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
};

export function esc(value: string | number): string {
  return String(value).replace(/[&<>"']/g, (c) => ENTITIES[c]);
}

/** Escape text that jubarte's source template interpolates without esc(). */
export function escapeGoldenText(value: string): string {
  return value.replace(/[&<>"']/g, (c) => ENTITIES[c]);
}

const STATE_LABELS: Record<string, string> = {
  tracking_without_comments: "tracking, no comments",
  with_comments_clean: "comments, clean",
  with_comments_tracking: "comments + tracking",
};
export const stateLabel = (name: string): string => STATE_LABELS[name] ?? name;

export function row(r: Row): string {
  const cls = r.ours ? " ours" : "";
  return `<div class="t-row bench-cols${cls}" role="row">
<span class="mono muted" role="cell">${esc(r.rank)}</span>
<div class="tool" role="rowheader"><div class="tool-name">${esc(r.tool)}</div><div class="tool-pin">${esc(r.pin)}</div></div>
<div class="bar-cell" role="cell"><div class="bar${r.ours ? " hi" : ""}" aria-hidden="true"><div style="width:${r.median}%"></div></div><span class="bar-note">${esc(r.note)}</span></div>
<span class="num strong" role="cell">${r.median.toFixed(2)}</span>
<span class="num" role="cell">${r.mean.toFixed(2)}</span>
<span class="num" role="cell">${r.docs.toLocaleString("en-US")}</span>
<span class="num${r.failed > 0 ? " failed" : " muted"}" role="cell">${r.failed.toLocaleString("en-US")}</span>
</div>`;
}

export function goldenHeadlines(HEADLINES: Headline[]): string {
  return `<div class="cells cols-auto-200 mt-56">
${HEADLINES.map(
  (h) => `<div class="cell-pad headline">
<p class="kicker">${esc(h.label)}</p>
<p class="headline-v"><span>${esc(h.value)}</span><span class="mono muted">vs ${esc(h.vs)}</span></p>
<p class="small mt-12">${esc(h.sub)}</p>
</div>`,
).join("\n")}
</div>`;
}

export function goldenTable(t: Table, escapeRawText = false): string {
  const id = escapeRawText ? escapeGoldenText(t.id) : t.id;
  return `<section class="mt-72" id="${id}">
<div class="section-head"><h2 id="${id}-title">${esc(t.title)}</h2><span>${esc(t.meta)}</span></div>
<p class="note mt-12">${esc(t.desc)}</p>
<div class="scroll-x"><div class="bench-table" role="table" aria-labelledby="${id}-title">
<div class="t-row head bench-cols" role="row"><span role="columnheader">#</span><span role="columnheader">Tool · pin</span><span role="columnheader">Median · 95% CI</span><span class="r" role="columnheader">Median (fail = 0)</span><span class="r" role="columnheader">Mean (fail = 0)</span><span class="r" role="columnheader">Scored</span><span class="r" role="columnheader">Failed</span></div>
${t.rows.map(row).join("\n")}
</div></div>
</section>`;
}

export function goldenStates(
  STATES: StateCell[],
  heading = "By corpus state, the 600-document conversion sample",
  escapeRawText = false,
): string {
  return `<section class="mt-72">
<div class="section-head"><h2>${heading}</h2><span>median · documents per state in brackets</span></div>
<div class="cells no-top cols-auto-220">
${STATES.map(
  (s) => `<div class="cell-pad">
<p class="state-name">${esc(stateLabel(s.name))} <span class="mono muted">(${escapeRawText ? escapeGoldenText(s.n) : s.n})</span></p>
<div class="state-rows">
${s.rows
  .map(
    (r) =>
      `<div class="state-row${r.ours ? " ours" : ""}"><div><span>${esc(r.tool)}</span><span class="mono">${r.median.toFixed(2)}</span></div><div class="bar thin${r.ours ? " hi" : ""}"><div style="width:${r.median}%"></div></div></div>`,
  )
  .join("\n")}
</div>
</div>`,
).join("\n")}
</div>
</section>`;
}

export function goldenMethod(METHOD: MethodPoint[]): string {
  return `<section class="cells cols-auto-240 mt-72">
${METHOD.map((m) => `<div class="cell-pad"><p class="note-title">${esc(m.t)}</p><p class="small mt-12">${esc(m.d)}</p></div>`).join("\n")}
</section>`;
}

export function goldenBars(GROUPS: HomeGroup[], escapeRawText = false): string {
  const text = escapeRawText ? escapeGoldenText : (value: string) => value;
  return `<div class="bench-groups">
${GROUPS.map(
  (g) => `<div>
<div class="group-head"><span>${text(g.title)}</span><span class="kicker">${text(g.meta)}</span></div>
<div class="bars">
${g.rows
  .map(
    (r) =>
      `<div class="bar-row${"ours" in r && r.ours ? " ours" : ""}"><span>${text(r.name)}</span><div class="bar${"ours" in r && r.ours ? " hi" : ""}"><div style="width:${r.v}%"></div></div><span class="num">${r.v.toFixed(2)}</span></div>`,
  )
  .join("\n")}
</div>${g.note ? `\n<p class="small mt-12">${text(g.note)}</p>` : ""}
</div>`,
).join("\n")}
</div>`;
}
