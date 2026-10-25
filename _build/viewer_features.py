"""Viewer features on top of the engine-comparison template (engine_compare.HTML_TEMPLATE):

* a drop-down that switches between the DOCX to PDF comparison (``index.html``) and the
  redline comparison (``redlines/index.html``);
* case filters in the side panel: group, reference page count, one engine's score at most
  X on one metric, the engine's page count differing from Word's; a count of the cases
  shown, a random-case button (key ``r``) and a clear button;
* a random case when the page opens without a ``#group/case`` link, instead of the first;
* prev / random / next buttons with the position in the filtered list;
* a button (key ``s``) that hides the side panel, and the long note folded into an
  accordion (the keyboard hints move into it, the engine versions into tooltips) so the
  pages get the room.

``patch(html, mode)`` works on the template and on an already built page alike (the data
sits between the anchors, never inside them); it is idempotent. ``build_site.py`` applies
it through ``patched_template(note, mode)``; run this file to patch the published pages in
place without rebuilding them:

    python3 _build/viewer_features.py            # index.html, redlines/index.html, speed/index.html
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import viewer_theme  # noqa: E402  (beside this file, also when run as a script)

MARKER = "/* viewer-features v2 */"
MODES = {
    "convert": ("Convert DOCX → PDF", {"convert": "./", "redline": "redlines/"}),
    "redline": ("Compare (redline) two documents", {"convert": "../", "redline": "./"}),
}

CSS = MARKER + """
#bar select#mode { font-weight:600; }
#sidehead { position:sticky; top:0; z-index:2; background:var(--panel); border-bottom:1px solid var(--border); }
#sidehead #filter { position:static; }
#fx { display:grid; grid-template-columns:auto minmax(0, 1fr); gap:4px 6px; padding:6px 8px; font-size:12px; align-items:center; }
#fx label { color:var(--muted); }
#fx select, #fx input, #fx button { background:#333; color:var(--fg); border:1px solid #555; border-radius:3px; padding:1px 4px; font:inherit; width:auto; position:static; }
#fx .row { display:flex; gap:4px; align-items:center; flex-wrap:wrap; min-width:0; }
#fx select { max-width:100%; min-width:0; }
#fx input[type=number] { width:4.5em; }
#fx .foot { grid-column:1/3; display:flex; gap:6px; align-items:center; flex-wrap:wrap; padding-right:4px; }
#fx .foot #fxn { color:var(--muted); margin-right:auto; }
#fx button:hover { background:#444; }
#list .case { scroll-margin-top:var(--headh, 0px); }
body.noside { grid-template-columns:0 1fr; }
body.noside #side { display:none; }
body.noside #main { grid-column:1/3; }
#nav { gap:4px; }
#nav #navPos { color:var(--muted); font-size:11px; min-width:6.5em; text-align:center; font-variant-numeric:tabular-nums; }
#sideToggle { font-size:14px; line-height:1; padding:2px 7px; }
body.noside #sideToggle { background:#094771; border-color:var(--accent); }
#engines .ver { display:none; }
#legend { padding:0; }
#legend summary { list-style:none; cursor:pointer; user-select:none; }
#legend summary::-webkit-details-marker { display:none; }
#legend .chev { display:inline-block; transition:transform .18s ease; color:var(--accent); }
#legend details[open] > summary .chev { transform:rotate(90deg); }
#legend .about > summary { display:flex; flex-wrap:wrap; gap:6px 10px; align-items:center; padding:3px 10px; }
#legend .about > summary .ttl { color:var(--fg); font-weight:600; }
#legend .about > summary .hint { color:var(--muted); }
#legend .about > summary a, #legend .pill { display:inline-block; padding:0 9px; border:1px solid var(--border); border-radius:999px; background:#2d2d30; color:var(--accent); text-decoration:none; }
#legend .about > summary a:hover { background:#34343a; }
#legend .items { display:grid; grid-template-columns:repeat(auto-fill, minmax(320px, 1fr)); gap:6px; padding:2px 10px 8px; align-items:start; }
#legend .item { border:1px solid var(--border); border-radius:10px; background:#2a2a2d; overflow:hidden; }
#legend .item > summary { padding:4px 10px; color:var(--fg); display:flex; gap:7px; align-items:baseline; }
#legend .item > summary:hover { background:#313136; }
#legend .item > summary .dot { width:8px; height:8px; border-radius:50%; flex:none; align-self:center; }
#legend .item > summary .sub { color:var(--muted); font-weight:400; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
#legend .item > div { padding:2px 12px 8px 25px; color:#bbb; }
"""

FX_HTML = """<div id="sidehead"><input id="filter" placeholder="filter cases (name, group)…"><div id="fx">
  <label for="fxGroup">group</label><select id="fxGroup"><option value="">all groups</option></select>
  <label for="fxPages">pages</label><select id="fxPages"><option value="">any</option><option value="1-1">1</option><option value="2-3">2–3</option><option value="4-10">4–10</option><option value="11-">11+</option></select>
  <label for="fxEng">score</label><span class="row"><select id="fxEng"></select><select id="fxMetric"></select> ≤ <input type="number" id="fxMax" min="0" max="100" step="1" placeholder="any"></span>
  <label for="fxDiffer">pages</label><span class="row"><label><input type="checkbox" id="fxDiffer"> differ from Word</label></span>
  <span class="foot"><span id="fxn"></span><button id="fxRand" title="open a random case of this list (r)">random</button><button id="fxClear" title="clear every filter">clear</button></span>
</div></div>"""

FX_JS = r"""
// Case filters (viewer-features): group, reference page count, one engine's score, page count.
function refPages(c) { return (c.page_counts || {}).reference ?? (c.pages.reference || []).length; }
function passesFx(c) {
  const fx = state.fx;
  if (fx.group && c.group !== fx.group) return false;
  if (fx.pages) {
    const [lo, hi] = fx.pages.split('-').map(x => x === '' ? Infinity : +x);
    const n = refPages(c); if (n < lo || n > hi) return false;
  }
  if (fx.max !== '' && fx.max != null) {
    const v = c.scores[fx.eng]?.[fx.metric];
    if (v == null || v > +fx.max) return false;
  }
  if (fx.differ) {
    const n = (c.page_counts || {})[fx.eng];
    if (n == null || n === refPages(c)) return false;
  }
  return true;
}
// Scroll the selected case to the middle of the list area below the sticky filters.
function showSel() {
  const side = $('#side'), sel = document.querySelector('#side .sel'), head = $('#sidehead').offsetHeight;
  $('#list').style.setProperty('--headh', head + 'px');
  if (!sel) return;
  const room = side.clientHeight - head;
  side.scrollTop += sel.getBoundingClientRect().top - side.getBoundingClientRect().top - head - Math.max(0, (room - sel.offsetHeight) / 2);
}
function pickRandom() {
  const vis = visibleCases();
  if (vis.length) state.sel = vis[Math.floor(Math.random() * vis.length)][1];
  state.view = 'viewer'; state.shown = PAGE_STEP;
}
function fxChanged() {
  const vis = visibleCases().map(([, i]) => i);
  if (vis.length && !vis.includes(state.sel)) { state.sel = vis[0]; state.shown = PAGE_STEP; }
  render(); showSel();
}
function setupFx() {
  const fx = state.fx, groups = [...new Set(DATA.map(c => c.group))].sort();
  for (const g of groups) { const o = document.createElement('option'); o.value = g; o.textContent = g; $('#fxGroup').appendChild(o); }
  for (const [k, label] of ENGINES) if (k !== 'reference') { const o = document.createElement('option'); o.value = k; o.textContent = label; $('#fxEng').appendChild(o); }
  for (const m of METRICS) { const o = document.createElement('option'); o.value = m; o.textContent = METRIC_LABEL[m]; o.title = METRIC_INFO[m]; $('#fxMetric').appendChild(o); }
  if (!groups.includes(fx.group)) fx.group = '';
  if (!ENGINES.some(([k]) => k === fx.eng && k !== 'reference')) fx.eng = ENGINES.find(([k]) => k !== 'reference')?.[0] ?? '';
  if (!METRICS.includes(fx.metric)) fx.metric = METRICS[0];
  // Filters saved by an earlier visit that hide every case would open on an empty page.
  if (!visibleCases().length) { Object.assign(fx, { group: '', pages: '', max: '', differ: false }); state.filter = ''; $('#filter').value = ''; }
  if (!DATA[state.sel]) state.sel = 0;
  $('#fxGroup').value = fx.group; $('#fxPages').value = fx.pages; $('#fxEng').value = fx.eng;
  $('#fxMetric').value = fx.metric; $('#fxMax').value = fx.max; $('#fxDiffer').checked = fx.differ;
  $('#fxGroup').onchange = e => { fx.group = e.target.value; fxChanged(); };
  $('#fxPages').onchange = e => { fx.pages = e.target.value; fxChanged(); };
  $('#fxEng').onchange = e => { fx.eng = e.target.value; fxChanged(); };
  $('#fxMetric').onchange = e => { fx.metric = e.target.value; fxChanged(); };
  $('#fxMax').oninput = e => { fx.max = e.target.value; fxChanged(); };
  $('#fxDiffer').onchange = e => { fx.differ = e.target.checked; fxChanged(); };
  $('#fxRand').onclick = () => { pickRandom(); render(); showSel(); };
  $('#fxClear').onclick = () => {
    Object.assign(fx, { group: '', pages: '', max: '', differ: false }); state.filter = '';
    $('#filter').value = ''; $('#fxGroup').value = ''; $('#fxPages').value = ''; $('#fxMax').value = ''; $('#fxDiffer').checked = false;
    fxChanged();
  };
  $('#mode').onchange = e => { location.href = e.target.value; };
  $('#navPrev').onclick = () => step(-1);
  $('#navNext').onclick = () => step(1);
  $('#navRand').onclick = $('#fxRand').onclick;
  $('#sideToggle').onclick = toggleSide;
  // The versions stay readable in each page column's header; in the bar they are tooltips.
  document.querySelectorAll('#engines label').forEach(l => { const v = l.querySelector('.ver'); if (v) l.title = v.textContent; });
}
// Prev / next through the filtered list, wrapping at both ends.
function step(d) {
  const vis = visibleCases().map(([, i]) => i); if (!vis.length) return;
  const at = vis.indexOf(state.sel);
  state.sel = at < 0 ? vis[0] : vis[(at + d + vis.length) % vis.length];
  state.view = 'viewer'; state.shown = PAGE_STEP; render(); showSel();
}
function toggleSide() { state.noside = !state.noside; render(); showSel(); }
// The legend's spans become an accordion: link-only spans stay visible as pills, every
// other span (and the keyboard hints) is one fold, all of it closed by default.
function accordionLegend() {
  const lg = $('#legend'), colors = ['#4ea1ff', '#c586c0', '#4ec9b0', '#dcdcaa', '#ce9178', '#9cdcfe', '#b5cea8', '#f48771'];
  const esc = t => t.replace(/&/g, '&amp;').replace(/</g, '&lt;');
  const links = [], items = [];
  for (const sp of [...lg.children]) {
    const a = sp.querySelector('a');
    if (a && sp.textContent.trim() === a.textContent.trim()) { links.push(a.outerHTML); continue; }
    const b = sp.firstElementChild?.tagName === 'B' && sp.innerHTML.startsWith('<b>') ? sp.firstElementChild : null;
    let title = 'How the scores work', body = sp.innerHTML, sub = '';
    if (b) { title = b.textContent; b.remove(); body = sp.innerHTML.replace(/^\s*:\s*/, ''); }
    if (b && title.length <= 5) sub = sp.textContent.trim().split(/[:.,;]/)[0];  // metric: J, SSIM, TB, s
    items.push([title, sub, body]);
  }
  const keys = $('#keys'); if (keys) { items.push(['Keyboard', '', keys.innerHTML]); keys.remove(); }
  lg.innerHTML = `<details class="about"${state.about ? ' open' : ''}><summary><span class="chev">&#9656;</span>`
    + `<span class="ttl">About these scores</span><span class="hint">${items.length} notes</span>${links.join('')}</summary>`
    + `<div class="items">${items.map(([t, sub, body], i) => `<details class="item"><summary><span class="chev">&#9656;</span>`
      + `<span class="dot" style="background:${colors[i % colors.length]}"></span><b>${t}</b>${sub ? `<span class="sub">${esc(sub)}</span>` : ''}</summary>`
      + `<div>${body}</div></details>`).join('')}</div></details>`;
  const about = lg.querySelector('.about');
  about.ontoggle = () => { state.about = about.open; save('state', state); showSel(); };
}
"""


NAV = ('<span class="grp" id="nav"><button id="sideToggle" title="hide / show the case list (s)">&#9776;</button>'
       '<button id="navPrev" title="previous case (&uarr;)">&lsaquo; prev</button>'
       '<button id="navRand" title="random case (r)">random</button>'
       '<button id="navNext" title="next case (&darr;)">next &rsaquo;</button><span id="navPos"></span></span>')


def mode_select(mode: str) -> str:
    """The drop-down: this page selected, the other one a link (relative to this page)."""
    here = MODES[mode][1][mode]
    options = "".join(
        f'<option value="{MODES[mode][1][m]}"{" selected" if MODES[mode][1][m] == here else ""}>{label}</option>'
        for m, (label, _) in MODES.items()
    )
    return f'<span class="grp"><select id="mode" autocomplete="off" title="what to compare">{options}</select></span>'


def swaps(mode: str) -> list[tuple[str, str]]:
    """(anchor, replacement) pairs; every anchor must occur exactly once."""
    # Both pages share one origin: the redline page saves under its own key, so a filter or
    # case index of one page never lands on the other. The convert page keeps "ec.".
    key = "'ec.'" if mode == "convert" else "'ec.redline.'"
    return [
        ("localStorage.getItem('ec.'+k)", f"localStorage.getItem({key}+k)"),
        ("localStorage.setItem('ec.'+k", f"localStorage.setItem({key}+k"),
        ("</style>", CSS + "</style>"),
        ('<div id="bar">\n', '<div id="bar">\n  ' + mode_select(mode) + "\n  " + NAV + "\n"),
        ('<input id="filter" placeholder="filter cases (name, group)…">', FX_HTML),  # FX_HTML wraps the same input
        ("for (const [k] of ENGINES) if (state.on[k] == null) state.on[k] = true;",
         "for (const [k] of ENGINES) if (state.on[k] == null) state.on[k] = true;\n"
         "state.fx = Object.assign({ group: '', pages: '', eng: '', metric: '', max: '', differ: false }, state.fx || {});"),
        ("applyHash();\nwindow.onhashchange", "const linked = applyHash();\nwindow.onhashchange"),
        ("  return DATA.map((c,i) => [c,i]).filter(([c]) => !f || (c.case + ' ' + c.group).toLowerCase().includes(f));\n}\n",
         "  return DATA.map((c,i) => [c,i]).filter(([c]) => (!f || (c.case + ' ' + c.group).toLowerCase().includes(f)) && passesFx(c));\n}\n"
         + FX_JS),
        ("  const list = $('#list'); list.innerHTML = '';",
         "  const list = $('#list'); list.innerHTML = '';\n"
         "  const shownCases = visibleCases(), at = shownCases.findIndex(([, i]) => i === state.sel);\n"
         "  $('#fxn').textContent = `${shownCases.length} of ${DATA.length} cases`;\n"
         "  $('#navPos').textContent = `${at < 0 ? '–' : at + 1} / ${shownCases.length}`;\n"
         "  document.body.classList.toggle('noside', !!state.noside);"),
        ("$('#filter').oninput = e => { state.filter = e.target.value; renderList(); };",
         "$('#filter').oninput = e => { state.filter = e.target.value; renderList(); };\n"
         "setupFx();\nif (!linked) pickRandom();"),
        ("if (e.target.tagName === 'INPUT' && e.target.type === 'text') return;",
         "if (e.target.tagName === 'SELECT' || (e.target.tagName === 'INPUT' && ['text', 'number'].includes(e.target.type))) return;"),
        ("  else if (e.key === 'o') state.ovl = !state.ovl;",
         "  else if (e.key === 'r') pickRandom();\n  else if (e.key === 's') state.noside = !state.noside;\n"
         "  else if (e.key === 'o') state.ovl = !state.ovl;"),
        ("<kbd>o</kbd> overlay", "<kbd>r</kbd> random &nbsp;<kbd>s</kbd> side panel &nbsp;<kbd>o</kbd> overlay"),
        ('<span style="color:var(--muted)"><kbd>1</kbd>', '<span id="keys" style="color:var(--muted)"><kbd>1</kbd>'),
        ("TABLE_COLS.map(m => `<span><b>${METRIC_LABEL[m]}</b> ${METRIC_INFO[m]}</span>`).join('');\n",
         "TABLE_COLS.map(m => `<span><b>${METRIC_LABEL[m]}</b> ${METRIC_INFO[m]}</span>`).join('');\naccordionLegend();\n"),
        # The opening (random) case is somewhere down the list: bring it into view.
        ("\nrender();\n</script>",
         "\nrender();\nshowSel();\n</script>"),
    ]


def patch(html: str, mode: str) -> str:
    """The viewer features, then the jubarte.pro theme (viewer_theme); each step runs once."""
    if MARKER not in html:
        for old, new in swaps(mode):
            if html.count(old) != 1:
                raise SystemExit(f"viewer anchor not found once ({html.count(old)}x): {old[:70]!r}")
            html = html.replace(old, new)
    return viewer_theme.theme(html, mode)


def main(argv: list[str]) -> int:
    site = Path(__file__).resolve().parent.parent
    for rel, mode in (("index.html", "convert"), ("redlines/index.html", "redline"), ("speed/index.html", "speed")):
        path = site / rel
        before = path.read_text()
        after = viewer_theme.theme(before, mode) if mode == "speed" else patch(before, mode)
        if after != before:
            path.write_text(after)
        print(f"{rel}: {'patched' if after != before else 'already patched'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
