import { esc } from "./esc.js";
// The markup below follows jubarte.pro's templates from jubarte-app (commit
// ad9b73e): site/pages/benchmark.ts lines 17-28 (row), 58-66 (headlines),
// 68-77 (table), 79-96 (states) and 107-109 (method), and site/pages/home.ts
// lines 177-191 (bar groups). The output is byte for byte identical for
// metacharacter-free values.
//
// Every text value goes through esc(). Jubarte already escapes most fields;
// its table ids, state counts and home-page prose are interpolated raw, so
// bench-viewer deliberately differs there when a value contains HTML
// metacharacters. The raw-facts fixture pins that documented difference.
/** Keep a score inside the range that CSS can render as a percentage. */
function scoreWidth(value) {
    return Math.max(0, Math.min(100, value));
}
/** The corpus folder names, said in words (jubarte's site/data/bench.ts). */
const STATE_LABELS = {
    tracking_without_comments: "tracking, no comments",
    with_comments_clean: "comments, clean",
    with_comments_tracking: "comments + tracking",
};
/** The page's name for a corpus state. */
export const stateLabel = (name) => STATE_LABELS[name] ?? name;
/** One row of a leaderboard table. */
export function renderRow(r) {
    const cls = r.ours ? " ours" : "";
    return `<div class="t-row bench-cols${cls}" role="row">
<span class="mono muted" role="cell">${esc(r.rank)}</span>
<div class="tool" role="rowheader"><div class="tool-name">${esc(r.tool)}</div><div class="tool-pin">${esc(r.pin)}</div></div>
<div class="bar-cell" role="cell"><div class="bar${r.ours ? " hi" : ""}" aria-hidden="true"><div style="width:${scoreWidth(r.median)}%"></div></div><span class="bar-note">${esc(r.note)}</span></div>
<span class="num strong" role="cell">${r.median.toFixed(2)}</span>
<span class="num" role="cell">${r.mean.toFixed(2)}</span>
<span class="num" role="cell">${r.docs.toLocaleString("en-US")}</span>
<span class="num${r.failed > 0 ? " failed" : " muted"}" role="cell">${r.failed.toLocaleString("en-US")}</span>
</div>`;
}
/** One leaderboard table, with its heading and its note. */
export function renderTable(t) {
    const id = esc(t.id);
    return `<section class="mt-72" id="${id}">
<div class="section-head"><h2 id="${id}-title">${esc(t.title)}</h2><span>${esc(t.meta)}</span></div>
<p class="note mt-12">${esc(t.desc)}</p>
<div class="scroll-x"><div class="bench-table" role="table" aria-labelledby="${id}-title">
<div class="t-row head bench-cols" role="row"><span role="columnheader">#</span><span role="columnheader">Tool · pin</span><span role="columnheader">Median · 95% CI</span><span class="r" role="columnheader">Median (fail = 0)</span><span class="r" role="columnheader">Mean (fail = 0)</span><span class="r" role="columnheader">Scored</span><span class="r" role="columnheader">Failed</span></div>
${t.rows.map((r) => renderRow(r)).join("\n")}
</div></div>
</section>`;
}
/** The headline cells above the tables. */
export function renderHeadlines(h) {
    return `<div class="cells cols-auto-200 mt-56">
${h
        .map((x) => `<div class="cell-pad headline">
<p class="kicker">${esc(x.label)}</p>
<p class="headline-v"><span>${esc(x.value)}</span><span class="mono muted">vs ${esc(x.vs)}</span></p>
<p class="small mt-12">${esc(x.sub)}</p>
</div>`)
        .join("\n")}
</div>`;
}
/** The conversion sample, split by corpus state. */
export function renderStates(s, opts = {}) {
    const label = opts.label ?? stateLabel;
    const heading = opts.heading ?? "By corpus state";
    const cells = opts.table === undefined ? s : s.filter((cell) => cell.table === opts.table);
    return `<section class="mt-72">
<div class="section-head"><h2>${esc(heading)}</h2><span>median · documents per state in brackets</span></div>
<div class="cells no-top cols-auto-220">
${cells
        .map((c) => `<div class="cell-pad">
<p class="state-name">${esc(label(c.name))} <span class="mono muted">(${esc(c.n)})</span></p>
<div class="state-rows">
${c.rows
        .map((r) => `<div class="state-row${r.ours ? " ours" : ""}"><div><span>${esc(r.tool)}</span><span class="mono">${r.median.toFixed(2)}</span></div><div class="bar thin${r.ours ? " hi" : ""}"><div style="width:${scoreWidth(r.median)}%"></div></div></div>`)
        .join("\n")}
</div>
</div>`)
        .join("\n")}
</div>
</section>`;
}
/** The bar groups of the home page: one group per sample, one bar per tool. */
export function renderBars(groups) {
    return `<div class="bench-groups">
${groups
        .map((g) => `<div>
<div class="group-head"><span>${esc(g.title)}</span><span class="kicker">${esc(g.meta)}</span></div>
<div class="bars">
${g.rows
        .map((r) => `<div class="bar-row${r.ours ? " ours" : ""}"><span>${esc(r.name)}</span><div class="bar${r.ours ? " hi" : ""}"><div style="width:${scoreWidth(r.v)}%"></div></div><span class="num">${r.v.toFixed(2)}</span></div>`)
        .join("\n")}
</div>${g.note ? `\n<p class="small mt-12">${esc(g.note)}</p>` : ""}
</div>`)
        .join("\n")}
</div>`;
}
/** The method: what the numbers mean, one card each. */
export function renderMethod(m) {
    return `<section class="cells cols-auto-240 mt-72">
${m.map((p) => `<div class="cell-pad"><p class="note-title">${esc(p.t)}</p><p class="small mt-12">${esc(p.d)}</p></div>`).join("\n")}
</section>`;
}
/** The badge: which bench version, generated when. */
export function renderBadge(s, tag) {
    return `<p class="bench-badge">bench ${esc(tag ?? s.version)} · generated ${esc(s.generated)}</p>`;
}
/** What the two marks in the tables mean. */
export function renderLegend() {
    return `<p class="bench-legend">† author-affiliated · failures count as 0</p>`;
}
