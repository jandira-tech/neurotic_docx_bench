"""Run jubarte on the 100-fixture tryout set.

The set is ``corpus/tryout/tryout_100.csv``, drawn from the Word corpus by
:func:`neurotic_docx_bench.tryout.build_set` (the same draw as ``bench try build-set``): the
word_based, word_based_randomized and word_redlines_superdoc compares Word accepted cleanly,
off the sealed holdout, with all eight files present, ``random.Random(20260927).sample(..., 100)``.
An existing set is reused unless ``--force-set`` is given. If the set changes, the previous
jubarte outputs are stale and the run refuses to resume over them without ``--force``.

jubarte (the release binary, macOS) then runs on the set:

* redline, 100 runs: ``jubarte <base.docx> <next.docx> -o <out.docx> --force --quiet``
  into ``corpus/tryout/jubarte/redline/<pair_stem>_jubarte_redline.docx``, then 100 runs
  of ``jubarte convert <that.docx> -o <out.pdf> --force`` into
  ``corpus/tryout/jubarte/redline/<pair_stem>_jubarte_redline.pdf`` (jubarte's own
  render of its own redline; the Word oracle is the set's ``pdf_redline_word``)
* convert, 100 runs: ``jubarte convert <base.docx> -o <out.pdf> --force`` into
  ``corpus/tryout/jubarte/convert/<base>_jubarte.pdf`` (the base document of each pair;
  its Word oracle is the set's ``pdf_base_word``)

No other renderer touches jubarte's output: the PDFs jubarte writes are what gets
scored against Word's PDFs.

Existing outputs are skipped (resume) unless ``--force``, which removes the previous
jubarte output before rerunning it. Nothing else is deleted.
``corpus/tryout/jubarte/MANIFEST.json``
records the binary path, its sha256 and ``--version`` output, every output's sha256,
timings and failures.

Run from the repository root::

    uv run python scripts/tryout_jubarte.py --jubarte-bin /Users/arthrod/T/jubarte-redlines/target/release/jubarte
    uv run python scripts/tryout_jubarte.py --task redline --dry-run     # selection only
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from neurotic_docx_bench import tryout
from neurotic_docx_bench.hub import sha256_file

console = Console()
app = typer.Typer(add_completion=False)

TRYOUT = tryout.TRYOUT_DIR
DEFAULT_BIN = Path("/Users/arthrod/T/jubarte-redlines/target/release/jubarte")
TIMEOUT_S = 180.0


def redline_cmd(binary: Path, base: Path, next_: Path, out: Path) -> list[str]:
    return [str(binary), str(base), str(next_), "-o", str(out), "--force", "--quiet"]


def convert_cmd(binary: Path, src: Path, out: Path) -> list[str]:
    return [str(binary), "convert", str(src), "-o", str(out), "--force"]


@dataclass
class RunRecord:
    task: str
    stem: str
    output: str
    cmd: list[str]
    status: str  # ok | skipped | failed
    seconds: float
    sha256: str | None = None
    error: str | None = None


def _looks_right(path: Path, task: str) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    head = path.read_bytes()[:5]
    return head[:2] == b"PK" if task == "redline" else head == b"%PDF-"


def run_one(task: str, stem: str, cmd: list[str], out: Path, *, force: bool) -> RunRecord:
    out.parent.mkdir(parents=True, exist_ok=True)
    if not force and _looks_right(out, task):
        return RunRecord(task, stem, out.as_posix(), cmd, "skipped", 0.0, sha256_file(out))
    if force and out.exists():
        # --force asked for a rerun: the previous jubarte output must not survive a failed rerun
        # and be mistaken for a good one on the next resume. Only this script's own outputs.
        out.unlink()
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=TIMEOUT_S)
    except FileNotFoundError as exc:
        return RunRecord(
            task, stem, out.as_posix(), cmd, "failed", time.perf_counter() - t0, error=f"binary not found: {exc}"
        )
    except subprocess.TimeoutExpired:
        return RunRecord(
            task, stem, out.as_posix(), cmd, "failed", time.perf_counter() - t0, error=f"timeout after {TIMEOUT_S:g}s"
        )
    seconds = time.perf_counter() - t0
    if proc.returncode != 0 or not _looks_right(out, task):
        detail = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
        if proc.returncode == 0:
            detail = f"no usable output at {out}; {detail}"
        return RunRecord(task, stem, out.as_posix(), cmd, "failed", seconds, error=detail)
    return RunRecord(task, stem, out.as_posix(), cmd, "ok", seconds, sha256_file(out))


def binary_version(binary: Path) -> str:
    try:
        proc = subprocess.run([str(binary), "--version"], check=False, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"unavailable: {exc}"
    return (proc.stdout or proc.stderr).strip()


def vendored_commits(root: Path) -> dict[str, str]:
    vendored = root / "src/neurotic_docx_bench/utils/jubarte/jubarte-rust"
    out = {}
    for name in ("ENGINE_COMMIT.txt", "SOURCE_COMMIT"):
        p = vendored / name
        if p.is_file():
            out[name] = p.read_text().strip()
    return out


def summary(records: list[RunRecord]) -> Table:
    table = Table(title="jubarte on the tryout set")
    for col in ("task", "ok", "skipped", "failed", "seconds"):
        table.add_column(col, justify="right" if col != "task" else "left")
    for task in ("redline", "redline_pdf", "convert"):
        rows = [r for r in records if r.task == task]
        if not rows:
            continue
        table.add_row(
            task,
            str(sum(r.status == "ok" for r in rows)),
            str(sum(r.status == "skipped" for r in rows)),
            str(sum(r.status == "failed" for r in rows)),
            f"{sum(r.seconds for r in rows):.1f}",
        )
    return table


@app.command()
def main(
    jubarte_bin: Path = typer.Option(DEFAULT_BIN, "--jubarte-bin", help="the jubarte release binary"),
    task: str = typer.Option("both", "--task", help="redline | convert | both"),
    root: Path = typer.Option(Path("."), "--root", help="repository root"),
    force: bool = typer.Option(False, "--force", help="rerun jubarte on outputs that already exist"),
    force_set: bool = typer.Option(False, "--force-set", help="rewrite tryout_100.csv even if it exists"),
    dry_run: bool = typer.Option(False, "--dry-run", help="select and write the set, run nothing"),
) -> None:
    """Select the 100 tryout pairs and run jubarte redline and convert on them."""
    if task not in ("redline", "convert", "both"):
        raise typer.BadParameter("--task must be redline, convert or both")
    root = root.resolve()
    set_csv = root / TRYOUT / tryout.SET_NAME
    try:
        if set_csv.is_file() and not force_set:
            fixtures = list(tryout.load_set(root).fixtures)
            console.print(f"using existing set {set_csv.relative_to(root)} ({len(fixtures)} pairs)")
        else:
            fixtures = tryout.build_set(root)
            tryout.write_set(root, fixtures)
            console.print(f"wrote {set_csv.relative_to(root)} ({len(fixtures)} pairs, seed {tryout.SET_SEED})")
    except tryout.TryoutError as exc:
        console.print(f"[red]{exc}; pass --force-set to redraw it[/red]")
        raise typer.Exit(code=2) from None
    if len(fixtures) != tryout.SET_SIZE:
        console.print(f"[red]set has {len(fixtures)} pairs, expected {tryout.SET_SIZE}[/red]")
        raise typer.Exit(code=2)
    if dry_run:
        for f in fixtures[:5]:
            console.print(f"  {f.pair_stem}")
        console.print(f"  ... {len(fixtures)} pairs; dry run, jubarte not invoked")
        return
    if not jubarte_bin.is_file():
        raise typer.BadParameter(f"jubarte binary not found at {jubarte_bin}")
    # absolute, so a relative path such as ./jubarte is not looked up on PATH by subprocess
    jubarte_bin = jubarte_bin.resolve()

    out_dir = root / TRYOUT / "jubarte"
    set_sha = sha256_file(set_csv)
    previous = out_dir / "MANIFEST.json"
    if previous.is_file() and not force:
        try:
            recorded = json.loads(previous.read_text()).get("set_sha256")
        except ValueError:
            recorded = None
        if recorded != set_sha:
            console.print(
                f"[red]{previous.relative_to(root)} was made from a different set (recorded {recorded}, "
                f"current {set_sha[:12]}); the outputs under {out_dir.relative_to(root)} are stale. "
                "Pass --force to regenerate them.[/red]"
            )
            raise typer.Exit(code=2)
    records: list[RunRecord] = []
    started = datetime.now(UTC).isoformat()
    with typer.progressbar(fixtures, label="jubarte", length=len(fixtures)) as bar:
        for f in bar:
            if task in ("redline", "both"):
                out = out_dir / "redline" / f"{f.pair_stem}_jubarte_redline.docx"
                cmd = redline_cmd(jubarte_bin, f.path("docx_base", root), f.path("docx_next", root), out)
                rec = run_one("redline", f.pair_stem, cmd, out, force=force)
                records.append(rec)
                if rec.status != "failed":
                    pdf = out.with_suffix(".pdf")
                    cmd = convert_cmd(jubarte_bin, out, pdf)
                    records.append(run_one("redline_pdf", f.pair_stem, cmd, pdf, force=force))
            if task in ("convert", "both"):
                out = out_dir / "convert" / f"{f.base}_jubarte.pdf"
                cmd = convert_cmd(jubarte_bin, f.path("docx_base", root), out)
                records.append(run_one("convert", f.base, cmd, out, force=force))

    manifest = {
        "generated_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
        "set": (TRYOUT / tryout.SET_NAME).as_posix(),
        "set_sha256": set_sha,
        "set_size": len(fixtures),
        "set_seed": tryout.SET_SEED,
        "corpus": tryout.CORPUS.as_posix(),
        "binary": str(jubarte_bin),
        "binary_sha256": sha256_file(jubarte_bin),
        "binary_version": binary_version(jubarte_bin),
        "vendored": vendored_commits(root),
        "commands": {
            "redline": "jubarte <base.docx> <next.docx> -o <out.docx> --force --quiet",
            "redline_pdf": "jubarte convert <pair_jubarte_redline.docx> -o <out.pdf> --force",
            "convert": "jubarte convert <base.docx> -o <out.pdf> --force",
        },
        "outputs": {
            r.output.replace(root.as_posix() + "/", ""): {
                "task": r.task,
                "stem": r.stem,
                "sha256": r.sha256,
                "seconds": r.seconds,
            }
            for r in records
            if r.status in ("ok", "skipped")
        },
        "failures": [asdict(r) for r in records if r.status == "failed"],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    console.print(summary(records))
    for r in [r for r in records if r.status == "failed"][:10]:
        console.print(f"[red]{r.task} {r.stem}: {r.error}[/red]")
    console.print(f"wrote {(out_dir / 'MANIFEST.json').relative_to(root)}")
    if any(r.status == "failed" for r in records):
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
