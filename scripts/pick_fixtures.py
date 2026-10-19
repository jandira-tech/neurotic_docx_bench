"""Browse and download fixtures from the neurotic-docx-bench Hugging Face dataset.

The public dataset `arthrod/neurotic_docx_bench-fixtures` holds the bench corpus:
every source DOCX, Microsoft Word's PDF of it, and every Word-compare redline pair
(3,503 comparisons over 2,925 documents). This tool lets you decide *which* of those
samples you want before pulling any bytes — explore the corpus (`list`), filter it
(`search`), then download exactly the files you picked (`download`), sha256-verified
against the dataset's own tables.

    uv run --with typer --with rich --with "huggingface_hub<2" \\
        python scripts/pick_fixtures.py --help

Both tables share one schema (id, key, state, docx, pdf, sets, names, sha256,
producer); comparisons add base_id/next_id, resolved against documents.csv when you
ask for the pair's input files. The dataset is public — a local
`huggingface-cli login` (or HF_TOKEN) only adds rate-limit headroom. Tables are
fetched once and cached by huggingface_hub.
"""

from __future__ import annotations

import csv
import hashlib
import random
import time
from pathlib import Path

import typer
from huggingface_hub import hf_hub_download
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import (BarColumn, DownloadColumn, Progress, SpinnerColumn,
                           TaskProgressColumn, TextColumn, TransferSpeedColumn)
from rich.table import Table

REPO = "arthrod/neurotic_docx_bench-fixtures"
TABLES = {"documents": "word/documents.csv", "comparisons": "word/comparisons.csv"}
RUN = 'uv run --with typer --with rich --with "huggingface_hub<2" python scripts/pick_fixtures.py'
STATE_STYLE = {  # a stable colour per corpus state (dim fallback for anything else)
    "clean": "green",
    "tracking_without_comments": "yellow",
    "with_comments_tracking": "magenta",
    "with_comments_clean": "cyan",
    "accept_all": "blue",
    "reject_all": "red",
}
console = Console()
app = typer.Typer(
    add_completion=False, rich_markup_mode="rich", no_args_is_help=True,
    help="Browse the bench corpus on [bold]arthrod/neurotic_docx_bench-fixtures[/bold] "
         "and download only the samples you pick.",
    epilog=f"[dim]examples[/dim]\n"
           f"  {RUN} list\n"
           f"  {RUN} search comparisons --state tracking_without_comments --set redlines_en_500\n"
           f"  {RUN} download documents --set sources_500 --sample 10 --seed 7 --what both\n"
           f"  {RUN} download comparisons --contains contract --sample 5 --with-inputs\n"
           f"[dim]kinds[/dim] documents (source DOCX + Word's PDF) · "
           f"comparisons (base→next pairs + Word's redline DOCX/PDF)")


def short(sha: str, n: int = 12) -> str:
    return sha[:n] + "…" if sha else "[dim]–[/dim]"


def load(kind: str) -> list[dict]:
    last = None
    for attempt in range(4):  # the hub flakes now and then (connection resets)
        try:
            path = hf_hub_download(REPO, TABLES[kind], repo_type="dataset")
            with open(path, newline="", encoding="utf-8") as fh:
                return list(csv.DictReader(fh))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2**attempt)
    raise SystemExit(f"could not fetch {TABLES[kind]} from {REPO}: {last}")


def matches(rows: list[dict], state, sset, sha256, contains, producer) -> list[dict]:
    out = []
    for r in rows:
        if state and r.get("state") != state:
            continue
        if sset and sset not in (r.get("sets") or "").split(";"):
            continue
        if sha256 and sha256 != (r.get("sha256") or ""):
            continue
        if contains and contains.lower() not in f"{r.get('key') or ''} {r.get('names') or ''}".lower():
            continue
        if producer and producer.lower() not in (r.get("producer") or "").lower():
            continue
        out.append(r)
    return sorted(out, key=lambda r: r.get("id") or "")


def pick(rows: list[dict], limit: int, sample: int | None, seed: int) -> list[dict]:
    if sample is not None:
        rows = random.Random(seed).sample(rows, min(sample, len(rows)))
    return rows[:limit]


def state_cell(state: str) -> str:
    return f"[{STATE_STYLE.get(state, 'dim')}]{state}[/]"


# ── commands ───────────────────────────────────────────────────────────────────

@app.command("list")
def overview(
    state: str = typer.Option(None, help="Count only this state."),
    set: str = typer.Option(None, help="Count only rows in this set."),
) -> None:
    """Overview of the corpus: documents and comparisons by state and set."""
    docs = [r for r in load("documents") if (not state or r["state"] == state) and (not set or set in r["sets"].split(";"))]
    comps = [r for r in load("comparisons") if (not state or r["state"] == state) and (not set or set in r["sets"].split(";"))]

    counts: dict[str, list[int]] = {}
    for r in docs:
        counts.setdefault(r["state"], [0, 0])[0] += 1
    for r in comps:
        counts.setdefault(r["state"], [0, 0])[1] += 1

    t = Table(box=box.ROUNDED, title=f"[bold]{REPO}[/]", title_style="bright_cyan",
              header_style="bold white on grey19")
    t.add_column("state", style="bold")
    t.add_column("documents", justify="right")
    t.add_column("comparisons", justify="right")
    t.add_column("")
    top = max(sum(c) for c in counts.values()) or 1
    for s in sorted(counts, key=lambda s: -sum(counts[s])):
        n_docs, n_comps = counts[s]
        bar = "█" * round((n_docs + n_comps) / top * 22)
        t.add_row(state_cell(s), f"{n_docs:,}", f"{n_comps:,}",
                  f"[{STATE_STYLE.get(s, 'bright_black')}]{bar}[/]")
    console.print(t)

    sets: dict[str, int] = {}
    for r in docs + comps:
        for s in (r.get("sets") or "").split(";"):
            if s:
                sets[s] = sets.get(s, 0) + 1
    st = Table(box=box.SIMPLE, title="sets", title_style="italic bright_black", header_style="dim")
    st.add_column("set", style="white")
    st.add_column("rows", justify="right", style="bright_blue")
    for s, n in sorted(sets.items(), key=lambda kv: -kv[1])[:12]:
        st.add_row(s, f"{n:,}")
    console.print(st)
    console.print("[dim]filter any of these with[/dim] [bold cyan]search[/bold cyan] "
                  "[dim]· fetch your picks with[/dim] [bold green]download[/bold green]")


FilterState = typer.Option(None, help="Only this corpus state.")
FilterSet = typer.Option(None, help="Only rows whose sets contain this.")
FilterSha = typer.Option(None, help="Exact sha256 of the row's DOCX.")
FilterContains = typer.Option(None, help="Substring of the key or original file name(s).")
FilterProducer = typer.Option(None, help="Substring of the PDF producer.")
FilterLimit = typer.Option(20, min=1, help="Show at most N rows.")
FilterSample = typer.Option(None, min=1, help="Random sample of N matching rows (with --seed, reproducible).")
FilterSeed = typer.Option(0, min=0, help="Seed for --sample.")


@app.command()
def search(
    kind: str = typer.Argument(..., help="documents | comparisons."),
    state: str = FilterState, set: str = FilterSet, sha256: str = FilterSha,
    contains: str = FilterContains, producer: str = FilterProducer,
    limit: int = FilterLimit, sample: int = FilterSample, seed: int = FilterSeed,
) -> None:
    """Filter the corpus tables without downloading any document bytes."""
    if kind not in TABLES:
        typer.secho(f"kind must be one of {sorted(TABLES)}", fg=typer.colors.RED)
        raise typer.Exit(2)
    rows = pick(matches(load(kind), state, set, sha256, contains, producer), limit, sample, seed)
    if not rows:
        console.print(Panel("[yellow]no matches[/yellow] — loosen a filter, or run "
                            "[bold]list[/bold] to see the vocabulary"))
        return

    t = Table(box=box.ROUNDED, header_style="bold white on grey19",
              title=f"[bold]{len(rows)}[/bold] of the matches shown")
    t.add_column("id", style="bold")
    t.add_column("state")
    if kind == "documents":
        t.add_column("original name", style="white", overflow="fold")
        t.add_column("sets", style="dim")
        t.add_column("sha256", style="bright_black")
        for r in rows:
            t.add_row(r["id"], state_cell(r["state"]), (r.get("names") or "?")[:48],
                      (r.get("sets") or "").replace(";", " "), short(r.get("sha256")))
    else:
        t.add_column("base → next", style="white")
        t.add_column("sets", style="dim")
        t.add_column("redline sha256", style="bright_black")
        for r in rows:
            t.add_row(r["id"], state_cell(r["state"]),
                      f"{r.get('base_id', '?')} [bright_green]→[/] {r.get('next_id', '?')}",
                      (r.get("sets") or "").replace(";", " "), short(r.get("sha256")))
    console.print(t)
    console.print(f"[dim]→ fetch with[/dim] [bold green]download {kind}[/bold green] "
                  f"[dim]and the same filters[/dim]")


@app.command()
def download(
    kind: str = typer.Argument(..., help="documents | comparisons."),
    state: str = FilterState, set: str = FilterSet, sha256: str = FilterSha,
    contains: str = FilterContains, producer: str = FilterProducer,
    limit: int = typer.Option(20, min=1, help="At most N rows."),
    sample: int = FilterSample, seed: int = FilterSeed,
    what: str = typer.Option("docx", help="docx | pdf | both (comparisons: the Word redline DOCX/PDF)."),
    with_inputs: bool = typer.Option(False, "--with-inputs",
                                     help="comparisons: also fetch the pair's base and next DOCX."),
    out: Path = typer.Option(None, help="Destination directory (default: fixtures/<kind>)."),
) -> None:
    """Download the picked samples (sha256-verified against the tables)."""
    if kind not in TABLES:
        typer.secho(f"kind must be one of {sorted(TABLES)}", fg=typer.colors.RED)
        raise typer.Exit(2)
    if what not in ("docx", "pdf", "both"):
        typer.secho("--what must be docx, pdf or both", fg=typer.colors.RED)
        raise typer.Exit(2)
    rows = pick(matches(load(kind), state, set, sha256, contains, producer), limit, sample, seed)
    if not rows:
        console.print(Panel("[yellow]nothing matched — nothing downloaded[/yellow]"))
        return
    out = out or Path("fixtures") / kind

    jobs: list[tuple[str, str, str | None]] = []  # (repo_path, dest_name, expected sha256)
    for r in rows:
        if what in ("docx", "both"):
            jobs.append((f"word/{r['docx']}", Path(r["docx"]).name, r.get("sha256")))
        if what in ("pdf", "both"):
            jobs.append((f"word/{r['pdf']}", Path(r["pdf"]).name, None))
    if with_inputs and kind == "comparisons":
        docs = {d["id"]: d for d in load("documents")}
        for r in rows:
            for side in ("base_id", "next_id"):
                if r.get(side) in docs:
                    d = docs[r[side]]
                    jobs.append((f"word/{d['docx']}", Path(d["docx"]).name, d.get("sha256")))

    out.mkdir(parents=True, exist_ok=True)
    bad = []
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  BarColumn(bar_width=24), TaskProgressColumn(), TransferSpeedColumn(),
                  DownloadColumn(), console=console) as progress:
        task = progress.add_task("downloading", total=len(jobs))
        for repo_path, name, expect in jobs:
            progress.update(task, description=f"[cyan]{name[:46]}[/cyan]")
            local = Path(hf_hub_download(REPO, repo_path, repo_type="dataset"))
            data = local.read_bytes()
            got = hashlib.sha256(data).hexdigest()
            if expect and got != expect:
                bad.append((name, expect, got))
            (out / name).write_bytes(data)
            progress.advance(task)

    if bad:
        for name, expect, got in bad:
            console.print(f"[bold red]sha256 mismatch[/bold red] {name}: "
                          f"table {short(expect)} got {short(got)}")
        raise typer.Exit(1)
    console.print(Panel(
        f"[bold green]{len(jobs)}[/bold green] file(s) · "
        f"{sum((out / n).stat().st_size for _, n, _ in jobs) / 1e6:.1f} MB\n"
        f"[dim]sha256 verified against the tables · saved to[/dim] [white]{out}[/white]",
        border_style="green", title="[bold green]done[/bold green]"))


if __name__ == "__main__":
    app()
