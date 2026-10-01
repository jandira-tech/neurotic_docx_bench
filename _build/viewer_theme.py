"""The jubarte.pro look for the GitHub Pages viewer (index.html, redlines/index.html, speed/).

The engine-comparison template is a dark editor theme. This layer gives the same pages
jubarte.pro's design: paper and white surfaces, navy ink, Manrope text, JetBrains Mono
labels, square mono "chip" buttons, a navy current case, and the whale-and-wordmark
header linking back to jubarte.pro. Only presentation changes: every control, key and
data structure of the template and of viewer_features stays as it is.

``theme(html, page)`` is idempotent (MARKER) and runs on the template or a built page
alike. ``viewer_features.patch`` applies it after its own swaps; run
``python3 _build/viewer_features.py`` to restyle the published pages in place.

The fonts are the files jubarte.pro serves (Manrope and JetBrains Mono, both SIL OFL 1.1,
licences beside them in ``_static/fonts/``).
"""

from __future__ import annotations

MARKER = "/* jubarte-theme v1 */"

# The page's path back to the site root, where _static/ lives.
ROOT = {"convert": "", "redline": "../", "speed": "../"}

BRAND_MARK = '<svg viewBox="0 0 560 360" width="34" height="22" aria-hidden="true"><g transform="rotate(-5 280 200)"><path d="M 76 192 C 82 172 112 156 150 146 C 196 132 258 112 310 110 C 356 108 402 118 448 148 C 458 152 464 150 470 144 C 478 128 494 106 520 92 C 512 112 508 126 502 134 C 514 140 526 148 540 160 C 520 164 498 160 480 162 C 470 164 460 166 452 166 C 420 190 382 228 328 252 C 270 278 194 286 148 268 C 114 254 88 230 81 208 C 76 198 74 194 76 192 Z" fill="#1E5580"/><path d="M 208 228 C 246 240 286 268 322 298 C 334 308 338 320 330 326 C 296 326 254 306 226 280 C 206 260 200 240 208 228 Z" fill="#8FB8CE"/><circle cx="122" cy="196" r="6" fill="#FFFFFF"/></g></svg>'

TITLES = {
    "convert": "DOCX → PDF vs Microsoft Word",
    "redline": "Redlines vs Microsoft Word",
    "speed": "Speed on 10,000 inputs",
}


def fonts(root: str) -> str:
    return "".join(
        f'@font-face {{ font-family:"{family}"; font-style:normal; font-weight:{weights}; font-display:swap; '
        f'src:url("{root}_static/fonts/{file}") format("woff2-variations"); }}\n'
        for family, weights, file in (
            ("Manrope", "200 800", "manrope-latin-wght-normal.woff2"),
            ("JetBrains Mono", "100 800", "jetbrains-mono-latin-wght-normal.woff2"),
        )
    )


TOKENS = """
:root {
  --ink:#0b1e2d; --muted:#5a7183; --line:#dce6ec; --paper:#f4f8fb; --white:#fff; --blue:#1e5580;
  --blue-d:#123b5c; --navy:#061c30; --sky:#e9f3f7; --hover:#eef4f8; --steel:#b4c4cf; --off:#8fa6b6;
  --forest:#1c5f46; --brick:#8a3b2e;
  --sans:"Manrope", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono:"JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace;
  --bg:var(--paper); --panel:var(--white); --fg:var(--ink); --accent:var(--blue); --border:var(--line);
}
body { font-family:var(--sans); -webkit-font-smoothing:antialiased; }
a { color:var(--blue); }
a:hover { color:var(--blue-d); }
#brand { grid-column:1/3; display:flex; align-items:center; gap:14px; padding:10px 14px; background:var(--white); border-bottom:1px solid var(--line); flex-wrap:wrap; }
#brand .logo { display:inline-flex; align-items:center; gap:10px; color:var(--ink); text-decoration:none; font-family:var(--mono); font-size:13px; font-weight:600; letter-spacing:.14em; }
#brand .crumb { font-family:var(--mono); font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }
#brand .links { margin-left:auto; display:flex; gap:16px; font-family:var(--mono); font-size:11px; letter-spacing:.06em; text-transform:uppercase; }
#brand .links a { text-decoration:none; }
"""

VIEWER = """
body { font-size:13px; grid-template-rows:auto auto auto 1fr; }
#bar { background:var(--paper); border-bottom:1px solid var(--line); gap:10px 14px; padding:8px 14px; }
#bar .grp { border-right:1px solid var(--line); }
#bar button, #bar select, #bar input[type=text], #fx select, #fx input, #fx button, #more {
  background:var(--white); color:var(--ink); border:1px solid var(--line); border-radius:0; font-family:var(--mono);
  font-size:11px; letter-spacing:.06em; padding:5px 10px; }
#bar button, #fx button, #more { text-transform:uppercase; letter-spacing:.08em; cursor:pointer; }
#bar button:hover, #fx button:hover, #more:hover { background:var(--hover); }
#bar select#mode { background:var(--navy); color:var(--white); border-color:var(--navy); font-family:var(--sans); font-size:13px; font-weight:600; letter-spacing:0; padding:6px 10px; }
#navRand { background:var(--navy) !important; color:var(--white) !important; border-color:var(--navy) !important; }
body.noside #sideToggle { background:var(--sky); color:var(--blue-d); border-color:var(--line); }
#nav #navPos, #pageinfo { font-family:var(--mono); font-size:11px; color:var(--muted); }
#bar label { font-family:var(--mono); font-size:11px; letter-spacing:.04em; }
input[type=range], input[type=checkbox] { accent-color:var(--blue); }
kbd { background:var(--white); border:1px solid var(--line); border-radius:0; color:var(--muted); font-family:var(--mono); }
#side { background:var(--white); border-right:1px solid var(--line); }
#side input#filter { background:var(--white); color:var(--ink); border-bottom:1px solid var(--line); font-family:var(--sans); padding:9px 10px; }
#sidehead { background:var(--white); border-bottom:1px solid var(--line); }
#fx select, #fx input, #fx button { padding:4px 6px; }
#fx input[type=number] { width:5.5em; }
#fx label { font-family:var(--mono); font-size:10px; letter-spacing:.08em; text-transform:uppercase; }
#fx .foot #fxn { font-family:var(--mono); font-size:11px; }
#side .case { border-bottom:1px solid var(--line); padding:6px 10px; }
#side .case:hover { background:var(--hover); }
#side .case.sel { background:var(--navy); color:var(--white); }
#side .case.sel .grp { color:var(--steel); }
#side .name { font-family:var(--mono); font-size:12px; }
#side .grp { font-family:var(--mono); font-size:10px; }
#main { background:var(--paper); padding:14px; }
.colhead { background:var(--paper); font-family:var(--mono); font-size:11px; letter-spacing:.06em; color:var(--muted); padding:4px 0 6px; }
.colhead b { color:var(--ink); text-transform:uppercase; letter-spacing:.08em; }
.page img { box-shadow:0 0 0 1px var(--line); }
.missing { background:var(--white); border:1px dashed var(--steel); color:var(--muted); font-family:var(--mono); font-size:11px; }
#scores table { font-family:var(--sans); background:var(--white); border:1px solid var(--line); }
#scores th, #scores td { border-bottom:1px solid var(--line); }
#scores th { background:var(--paper); font-family:var(--mono); font-size:10px; letter-spacing:.08em; text-transform:uppercase; }
#scores th.eng, #scores td.first { border-left:1px solid var(--line); }
#scores td.best { color:var(--forest); font-weight:600; }
#scores tr.mean td { background:var(--sky); color:var(--ink); }
#scores tbody tr:hover { background:var(--hover); }
#scores tbody tr.sel { background:var(--sky); box-shadow:inset 3px 0 0 var(--navy); }
#legend { background:var(--white); border-bottom:1px solid var(--line); }
#legend .chev { color:var(--blue); }
#legend .about > summary { padding:6px 14px; }
#legend .about > summary .ttl { font-family:var(--mono); font-size:11px; letter-spacing:.08em; text-transform:uppercase; }
#legend .about > summary a, #legend .pill { border-radius:0; background:var(--white); border-color:var(--line); color:var(--blue); font-family:var(--mono); font-size:11px; padding:2px 10px; }
#legend .about > summary a:hover { background:var(--hover); }
#legend .item { border-radius:0; background:var(--white); border-color:var(--line); }
#legend .item > summary:hover { background:var(--hover); }
#legend .item > div { color:var(--muted); }
"""

SPEED = """
body { background:var(--white); color:var(--ink); font-size:15px; padding:0 0 48px; max-width:none; }
body > :not(#brand) { max-width:1180px; margin-left:auto; margin-right:auto; padding-left:24px; padding-right:24px; }
#brand { margin-bottom:24px; }
h1 { font-size:34px; letter-spacing:-.02em; line-height:1.1; }
h2 { font-family:var(--mono); font-size:12px; font-weight:600; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); border-bottom:1px solid var(--line); padding-bottom:8px; }
table { background:var(--white); }
th, td { border:1px solid var(--line); padding:5px 10px; }
th { background:var(--paper); font-family:var(--mono); font-size:11px; letter-spacing:.06em; }
code { background:var(--sky); border-radius:0; font-family:var(--mono); font-size:.9em; }
nav { font-family:var(--mono); font-size:11px; letter-spacing:.06em; text-transform:uppercase; }
"""

# The legend accordion's dots: the template's editor palette, then jubarte's.
DOTS = ("['#4ea1ff', '#c586c0', '#4ec9b0', '#dcdcaa', '#ce9178', '#9cdcfe', '#b5cea8', '#f48771']",
        "['#1e5580', '#3d7eae', '#1c5f46', '#8a3b2e', '#67c6ee', '#123b5c', '#8fa6b6', '#061c30']")


def brand(page: str) -> str:
    root = ROOT[page]
    links = [("jubarte.pro", "https://jubarte.pro/"), ("Cases", "https://jubarte.pro/cases"),
             ("Bench repo", "https://github.com/jandira-tech/neurotic_docx_bench")]
    if page != "speed":
        links.insert(1, ("Speed", f"{root}speed/"))
    return (f'<header id="brand"><a class="logo" href="https://jubarte.pro/">{BRAND_MARK}JUBARTE.DOCX</a>'
            f'<span class="crumb">/ {TITLES[page]}</span><span class="links">'
            + "".join(f'<a href="{href}">{label}{" ↗" if href.startswith("http") else ""}</a>' for label, href in links)
            + "</span></header>\n")


def swaps(page: str) -> list[tuple[str, str]]:
    css = MARKER + "\n" + fonts(ROOT[page]) + TOKENS + (SPEED if page == "speed" else VIEWER)
    out = [("</style>", css + "</style>")]
    if page == "speed":
        out.append(("</style>\n<nav>", "</style>\n" + brand(page) + "<nav>"))
    else:
        out.append(('<div id="bar">\n', brand(page) + '<div id="bar">\n'))
        out.append(DOTS)
    return out


def theme(html: str, page: str) -> str:
    if MARKER in html:
        return html
    for old, new in swaps(page):
        if html.count(old) != 1:
            raise SystemExit(f"theme anchor not found once ({html.count(old)}x): {old[:70]!r}")
        html = html.replace(old, new)
    return html
