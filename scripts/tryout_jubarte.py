#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["typer>=0.12", "rich>=13"]
# ///
"""Build the 100-fixture tryout set and run jubarte on it.

Selection (deterministic): from ``corpus/no_comments_pdf_was_generated_by_word`` (the
corpus whose PDFs Microsoft Word exported itself; ``grok_run/word_based`` holds LibreOffice
renders and is NOT used) keep the pairs of ``centralized_mapping.csv`` whose base and
next docx (``docx_source``), Word source PDFs of both (``pdf_source``), Word redline docx
and PDF (``docx_redlines_word``, ``pdf_redlines_word``) and Word accepted docx and PDF
(``docx_accepted_word``, ``pdf_accepted_word``) all exist and whose stems are on neither
``grok_run/holdout_combined.txt`` nor ``grok_run/word_based/holdout.txt``; sort by pair stem;
``random.Random(20260927).sample(..., 100)``; sort again. When a pair has both
``<pair>_redline`` and ``<pair>_word_redline`` oracles the Word-captured variant wins,
as in ``pipeline._index_redlines``. The set is written once to
``corpus/tryout/tryout_100.csv`` with every file's sha256 and is not rewritten unless
``--force-set`` is given. If the set changes, the previous jubarte outputs are stale and
the run refuses to resume over them without ``--force``.

jubarte (the release binary, macOS) then runs on the set:

* redline, 100 runs: ``jubarte <base.docx> <next.docx> -o <out.docx> --force --quiet``
  into ``corpus/tryout/jubarte/redline/<pair_stem>_jubarte_redline.docx``, then 100 runs
  of ``jubarte convert <that.docx> -o <out.pdf> --force`` into
  ``corpus/tryout/jubarte/redline/<pair_stem>_jubarte_redline.pdf`` (jubarte's own
  render of its own redline; the Word oracle is the set's ``pdf_redline_word``)
* convert, 100 runs: ``jubarte convert <base.docx> -o <out.pdf> --force`` into
  ``corpus/tryout/jubarte/convert/<base>_jubarte.pdf`` (the base document of each pair;
  its Word oracle is ``pdf_source/<base>.pdf``)

No other renderer touches jubarte's output: the PDFs jubarte writes are what gets
scored against Word's PDFs.

Existing outputs are skipped (resume) unless ``--force``, which removes the previous
jubarte output before rerunning it. Nothing else is deleted.
``corpus/tryout/jubarte/MANIFEST.json``
records the binary path, its sha256 and ``--version`` output, every output's sha256,
timings and failures.

Run from the repository root::

    uv run scripts/tryout_jubarte.py --jubarte-bin /Users/arthrod/T/jubarte-redlines/target/release/jubarte
    uv run scripts/tryout_jubarte.py --task redline --dry-run     # selection only
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()
app = typer.Typer(add_completion=False)

SET_SIZE = 100
SET_SEED = 20260927
SET_NAME = "tryout_100.csv"
CORPUS = Path("corpus/no_comments_pdf_was_generated_by_word")
HOLDOUTS = (Path("grok_run/holdout_combined.txt"), Path("grok_run/word_based/holdout.txt"))
WORD_VARIANT = "_word_redline"
TRYOUT = Path("corpus/tryout")
DEFAULT_BIN = Path("/Users/arthrod/T/jubarte-redlines/target/release/jubarte")
TIMEOUT_S = 180.0

SET_COLUMNS = (
    "pair_stem",
    "base",
    "next",
    "docx_base",
    "docx_next",
    "pdf_base_word",
    "pdf_next_word",
    "docx_redline_word",
    "pdf_redline_word",
    "docx_accepted_word",
    "pdf_accepted_word",
    "sha256_docx_base",
    "sha256_docx_next",
    "sha256_pdf_base_word",
    "sha256_pdf_next_word",
    "sha256_docx_redline_word",
    "sha256_pdf_redline_word",
    "sha256_docx_accepted_word",
    "sha256_pdf_accepted_word",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class Pair:
    pair_stem: str
    base: str
    next: str
    docx_base: Path
    docx_next: Path
    pdf_base_word: Path
    pdf_next_word: Path
    docx_redline_word: Path
    pdf_redline_word: Path
    docx_accepted_word: Path
    pdf_accepted_word: Path

    def files(self) -> dict[str, Path]:
        return {
            "docx_base": self.docx_base,
            "docx_next": self.docx_next,
            "pdf_base_word": self.pdf_base_word,
            "pdf_next_word": self.pdf_next_word,
            "docx_redline_word": self.docx_redline_word,
            "pdf_redline_word": self.pdf_redline_word,
            "docx_accepted_word": self.docx_accepted_word,
            "pdf_accepted_word": self.pdf_accepted_word,
        }


def read_holdout(path: Path) -> set[str]:
    """One pair key per line; blank lines and ``#`` comments skipped; missing file is empty."""
    if not path.is_file():
        return set()
    keys = set()
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            keys.add(line)
    return keys


def word_variant(directory: Path, pair_stem: str, suffix: str) -> Path | None:
    """``<pair>_word_redline<suffix>`` if present, else ``<pair>_redline<suffix>``, else None.

    Same preference as ``pipeline._index_redlines``: the Word-captured variant wins.
    """
    for name in (f"{pair_stem}{WORD_VARIANT}{suffix}", f"{pair_stem}_redline{suffix}"):
        if (directory / name).is_file():
            return directory / name
    return None


def eligible_pairs(corpus: Path, root: Path) -> list[Pair]:
    """Pairs with every input and every Word oracle present and no stem on a holdout.

    ``corpus`` is relative to ``root``; the returned paths are relative to ``root`` too.
    The mapping CSV supplies ``pair_stem``, ``base`` and ``next`` only; every file is
    located on disk (the CSV's accepted columns are stale in this corpus).
    """
    holdout: set[str] = set()
    for h in HOLDOUTS:
        holdout |= read_holdout(root / h)
    out: list[Pair] = []
    with (root / corpus / "centralized_mapping.csv").open(newline="") as fh:
        for row in csv.DictReader(fh):
            stem, base, next_ = row["pair_stem"], row["base"], row["next"]
            if {stem, base, next_} & holdout:
                continue
            found = {
                "docx_redline_word": word_variant(root / corpus / "docx_redlines_word", stem, ".docx"),
                "pdf_redline_word": word_variant(root / corpus / "pdf_redlines_word", stem, ".pdf"),
                "docx_accepted_word": word_variant(root / corpus / "docx_accepted_word", stem, ".docx"),
                "pdf_accepted_word": word_variant(root / corpus / "pdf_accepted_word", stem, ".pdf"),
            }
            if any(p is None for p in found.values()):
                continue
            pair = Pair(
                pair_stem=stem,
                base=base,
                next=next_,
                docx_base=corpus / "docx_source" / f"{base}.docx",
                docx_next=corpus / "docx_source" / f"{next_}.docx",
                pdf_base_word=corpus / "pdf_source" / f"{base}.pdf",
                pdf_next_word=corpus / "pdf_source" / f"{next_}.pdf",
                **{k: p.relative_to(root) for k, p in found.items() if p is not None},
            )
            if all((root / p).is_file() for p in pair.files().values()):
                out.append(pair)
    return sorted(out, key=lambda p: p.pair_stem)


def select_set(pairs: list[Pair], size: int = SET_SIZE, seed: int = SET_SEED) -> list[Pair]:
    ordered = sorted(pairs, key=lambda p: p.pair_stem)
    if len(ordered) < size:
        raise ValueError(f"only {len(ordered)} eligible pairs, need {size}")
    chosen = random.Random(seed).sample(ordered, size)
    return sorted(chosen, key=lambda p: p.pair_stem)


def write_set(pairs: list[Pair], csv_path: Path, root: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SET_COLUMNS)
        w.writeheader()
        for p in pairs:
            row = {"pair_stem": p.pair_stem, "base": p.base, "next": p.next}
            for key, path in p.files().items():
                row[key] = path.as_posix()
                row[f"sha256_{key}"] = sha256_file(root / path)
            w.writerow(row)


def read_set(csv_path: Path) -> list[Pair]:
    with csv_path.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    return [
        Pair(
            pair_stem=r["pair_stem"],
            base=r["base"],
            next=r["next"],
            docx_base=Path(r["docx_base"]),
            docx_next=Path(r["docx_next"]),
            pdf_base_word=Path(r["pdf_base_word"]),
            pdf_next_word=Path(r["pdf_next_word"]),
            docx_redline_word=Path(r["docx_redline_word"]),
            pdf_redline_word=Path(r["pdf_redline_word"]),
            docx_accepted_word=Path(r["docx_accepted_word"]),
            pdf_accepted_word=Path(r["pdf_accepted_word"]),
        )
        for r in rows
    ]


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
    corpus = CORPUS
    set_csv = root / TRYOUT / SET_NAME
    if set_csv.is_file() and not force_set:
        try:
            pairs = read_set(set_csv)
        except KeyError as exc:
            console.print(f"[red]{set_csv.relative_to(root)} lacks column {exc}: an older set; pass --force-set[/red]")
            raise typer.Exit(code=2) from None
        if not pairs or not pairs[0].docx_base.as_posix().startswith(corpus.as_posix() + "/"):
            console.print(f"[red]{set_csv.relative_to(root)} is not drawn from {corpus}; pass --force-set[/red]")
            raise typer.Exit(code=2)
        console.print(f"using existing set {set_csv.relative_to(root)} ({len(pairs)} pairs)")
    else:
        if not (root / corpus / "centralized_mapping.csv").is_file():
            raise typer.BadParameter(f"no {corpus / 'centralized_mapping.csv'} under {root}; pass --root")
        eligible = eligible_pairs(corpus, root)
        console.print(f"{len(eligible)} eligible pairs in {corpus} (all Word oracles present, off the holdouts)")
        pairs = select_set(eligible)
        write_set(pairs, set_csv, root)
        console.print(f"wrote {set_csv.relative_to(root)} ({len(pairs)} pairs, seed {SET_SEED})")
    if len(pairs) != SET_SIZE:
        console.print(f"[red]set has {len(pairs)} pairs, expected {SET_SIZE}[/red]")
        raise typer.Exit(code=2)
    if dry_run:
        for p in pairs[:5]:
            console.print(f"  {p.pair_stem}")
        console.print(f"  ... {len(pairs)} pairs; dry run, jubarte not invoked")
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
    with typer.progressbar(pairs, label="jubarte", length=len(pairs)) as bar:
        for p in bar:
            if task in ("redline", "both"):
                out = out_dir / "redline" / f"{p.pair_stem}_jubarte_redline.docx"
                cmd = redline_cmd(jubarte_bin, root / p.docx_base, root / p.docx_next, out)
                rec = run_one("redline", p.pair_stem, cmd, out, force=force)
                records.append(rec)
                if rec.status != "failed":
                    pdf = out.with_suffix(".pdf")
                    cmd = convert_cmd(jubarte_bin, out, pdf)
                    records.append(run_one("redline_pdf", p.pair_stem, cmd, pdf, force=force))
            if task in ("convert", "both"):
                out = out_dir / "convert" / f"{p.base}_jubarte.pdf"
                cmd = convert_cmd(jubarte_bin, root / p.docx_base, out)
                records.append(run_one("convert", p.base, cmd, out, force=force))

    manifest = {
        "generated_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
        "set": (TRYOUT / SET_NAME).as_posix(),
        "set_sha256": set_sha,
        "set_size": len(pairs),
        "set_seed": SET_SEED,
        "corpus": corpus.as_posix(),
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
