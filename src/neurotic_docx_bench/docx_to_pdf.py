"""DOCX→PDF evaluation track: Word-exported oracles vs independent converters.

Scores candidate PDFs against committed Microsoft Word oracles in
``corpus/no_comments_pdf_was_generated_by_word`` using the shipped visual
pipeline (``score_folders_plain`` / ``match_by_plain_stem``). Convert crashes
and non-PDF output are generate failures scored as 0 (intent-to-treat). Does
not wrap soffice as a converter-under-test and does not touch ``score.py`` /
``diff.py`` / ``raster.py``.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import statistics
import subprocess
import zipfile
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from neurotic_docx_bench import pipeline

REPO_ROOT = Path(__file__).resolve().parents[2]
WORD_CORPUS = REPO_ROOT / "corpus" / "no_comments_pdf_was_generated_by_word"
WORD_PDF_TOOLS = (
    "rdocx",
    "office2pdf",
    "pdfitdown",
    "doxx",
    "libreoffice_convert_rust",
    "dxpdf",
    "docxide-pdf",
    "pymupdf-pro",
    "genoffice",
)

REQUIRED_FEATURES = frozenset(
    {"body_text", "table", "numbering", "image", "header_or_footer"},
)

DEFAULT_CONVERTER = REPO_ROOT.parent / "jubarte-redlines" / "target" / "release" / "jubarte"
# PyMuPDF Pro pins its own PyMuPDF, so it runs from an isolated venv (see its pyproject).
PYMUPDF_PRO_CONVERTER = Path(__file__).resolve().parent / "utils" / "pymupdf-pro" / "pymupdf-pro-convert"

_TOOL_BINARIES: dict[str, tuple[str, ...]] = {
    "rdocx": ("rdocx", "rdocx-cli"),
    "office2pdf": ("office2pdf",),
    "pdfitdown": ("pdfitdown",),
    "doxx": ("doxx",),
    "jubarte": ("jubarte",),
    "libreoffice_convert_rust": ("libreoffice_convert", "libreoffice_convert_rust"),
    "dxpdf": ("dxpdf",),
    "docxide-pdf": ("docxide-pdf",),
    "pymupdf-pro": ("pymupdf-pro-convert",),
    "genoffice": ("genoffice",),
}

RANKING_END = "<!-- RANKING-END -->"


@dataclass(frozen=True)
class Track:
    """One DOCX→PDF measurement set: oracle PDF folders + pin files."""

    name: str
    title: str
    pools: tuple[tuple[str, str, str], ...]
    fixture_list: Path
    sha_manifest: Path
    readme_start: str
    readme_end: str
    caption: str

    @property
    def oracle_pdf_dir_names(self) -> tuple[str, ...]:
        return tuple(pdf_dir for _, _, pdf_dir in self.pools)

    @property
    def kinds(self) -> frozenset[str]:
        return frozenset(kind for kind, _, _ in self.pools)


REDLINE_TRACK = Track(
    name="docx_to_pdf",
    title="docx_to_pdf — DOCX to PDF vs Word export",
    pools=(
        ("accepted", "docx_accepted_word", "pdf_accepted_word"),
        ("redline_randomized", "docx_redlines_randomized", "pdf_redlines_randomized"),
    ),
    fixture_list=WORD_CORPUS / "docx_to_pdf_fixtures.txt",
    sha_manifest=WORD_CORPUS / "docx_to_pdf_oracle_sha256.json",
    readme_start="<!-- DOCX-TO-PDF-START -->",
    readme_end="<!-- DOCX-TO-PDF-END -->",
    caption="pinned Word-export PDFs (`pdf_accepted_word`, `pdf_redlines_randomized`)",
)

NO_REDLINE_TRACK = Track(
    name="docx_to_pdf_no_redline_docs",
    title="docx_to_pdf_no_redline_docs — source DOCX to PDF vs Word export",
    pools=(
        ("source", "docx_source", "pdf_source"),
        ("source_randomized", "docx_source_randomized", "pdf_source_randomized"),
    ),
    fixture_list=WORD_CORPUS / "docx_to_pdf_no_redline_fixtures.txt",
    sha_manifest=WORD_CORPUS / "docx_to_pdf_no_redline_oracle_sha256.json",
    readme_start="<!-- DOCX-TO-PDF-NO-REDLINE-START -->",
    readme_end="<!-- DOCX-TO-PDF-NO-REDLINE-END -->",
    caption="pinned Word-export PDFs (`pdf_source`, `pdf_source_randomized`)",
)

TRACKS: dict[str, Track] = {
    REDLINE_TRACK.name: REDLINE_TRACK,
    NO_REDLINE_TRACK.name: NO_REDLINE_TRACK,
}

# Backward-compatible aliases for the redline/accepted track.
FIXTURE_LIST = REDLINE_TRACK.fixture_list
POOLS = REDLINE_TRACK.pools
ORACLE_PDF_DIRS = REDLINE_TRACK.oracle_pdf_dir_names
ORACLE_SHA_MANIFEST = REDLINE_TRACK.sha_manifest
README_START = REDLINE_TRACK.readme_start
README_END = REDLINE_TRACK.readme_end


def resolve_track(track: Track | str | None = None) -> Track:
    if track is None:
        return REDLINE_TRACK
    if isinstance(track, Track):
        return track
    if track not in TRACKS:
        raise ValueError(f"unknown DOCX→PDF track {track!r}; known: {sorted(TRACKS)}")
    return TRACKS[track]


@dataclass(frozen=True)
class Fixture:
    """One pinned DOCX plus its Word-exported oracle PDF, keyed uniquely."""

    stem: str
    kind: str
    original_stem: str
    docx: Path
    oracle: Path


def load_fixture_rows(path: Path | None = None, *, track: Track | str | None = None) -> list[tuple[str, str]]:
    """Read ``kind<TAB>original_stem`` rows (comments and blanks ignored)."""
    rows: list[tuple[str, str]] = []
    path = path or resolve_track(track).fixture_list
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        kind, original = line.split("\t", 1)
        rows.append((kind.strip(), original.strip()))
    return rows


def load_fixture_stems(path: Path | None = None, *, track: Track | str | None = None) -> list[str]:
    """Unique staging stems (``{kind}__{original_stem}``) from the pin list."""
    return [f"{kind}__{original}" for kind, original in load_fixture_rows(path, track=track)]


def _pool_dirs(kind: str, root: Path = WORD_CORPUS, *, track: Track | str | None = None) -> tuple[Path, Path]:
    spec = resolve_track(track)
    for name, docx_dir, pdf_dir in spec.pools:
        if name == kind:
            return root / docx_dir, root / pdf_dir
    raise ValueError(f"unknown Word-oracle pool {kind!r} for track {spec.name}")


def load_fixtures(path: Path | None = None, *, track: Track | str | None = None) -> list[Fixture]:
    """Resolve each pinned row to its source DOCX and Word oracle PDF."""
    spec = resolve_track(track)
    fixtures: list[Fixture] = []
    for kind, original in load_fixture_rows(path, track=spec):
        docx_dir, pdf_dir = _pool_dirs(kind, track=spec)
        fixtures.append(
            Fixture(
                stem=f"{kind}__{original}",
                kind=kind,
                original_stem=original,
                docx=docx_dir / f"{original}.docx",
                oracle=pdf_dir / f"{original}.pdf",
            ),
        )
    return fixtures


def oracle_pdf_dirs(root: Path = WORD_CORPUS, *, track: Track | str | None = None) -> list[Path]:
    """The Word-export PDF folders used as this track's ground truth."""
    return [root / name for name in resolve_track(track).oracle_pdf_dir_names]


def _oracle_pdf_sha_map(root: Path = WORD_CORPUS, *, track: Track | str | None = None) -> dict[str, str]:
    """SHA-256 of every ``*.pdf`` in the track's pinned folders. Read-only."""
    from neurotic_docx_bench.oracle_manifest import _sha256

    out: dict[str, str] = {}
    for folder in oracle_pdf_dirs(root, track=track):
        for pdf in sorted(folder.glob("*.pdf")):
            rel = pdf.resolve().relative_to(root.resolve()).as_posix()
            out[rel] = _sha256(pdf)
    return out


def write_oracle_sha_manifest(
    path: Path | None = None, root: Path = WORD_CORPUS, *, track: Track | str | None = None,
) -> dict[str, str]:
    """SHA-256 every oracle PDF. Does not write inside the PDF folders."""
    from neurotic_docx_bench.oracle_manifest import write_manifest

    spec = resolve_track(track)
    manifest = _oracle_pdf_sha_map(root, track=spec)
    write_manifest(path or spec.sha_manifest, manifest)
    return manifest


def verify_oracle_sha_manifest(
    path: Path | None = None, root: Path = WORD_CORPUS, *, track: Track | str | None = None,
) -> None:
    """Abort if any pinned oracle PDF is missing, extra, or has a different hash."""
    from neurotic_docx_bench.oracle_manifest import ManifestDrift, load_manifest

    spec = resolve_track(track)
    path = path or spec.sha_manifest
    if not path.is_file():
        raise RuntimeError(f"DOCX→PDF oracle SHA manifest missing: {path}")
    expected = load_manifest(path) or {}
    actual = _oracle_pdf_sha_map(root, track=spec)
    changed = sorted(k for k in expected.keys() & actual.keys() if expected[k] != actual[k])
    missing = sorted(expected.keys() - actual.keys())
    extra = sorted(actual.keys() - expected.keys())
    drift = ManifestDrift(changed=changed, missing=missing, extra=extra)
    if not drift.clean:
        raise RuntimeError(
            f"DOCX→PDF oracle PDF drift (never regenerate those folders): {drift.summary()}",
        )


def discover_word_oracle_pairs(root: Path = WORD_CORPUS, *, track: Track | str | None = None) -> list[Fixture]:
    """Every valid pair whose oracle PDF lives in this track's pinned folders."""
    found: list[Fixture] = []
    for kind, docx_dir, pdf_dir in resolve_track(track).pools:
        ddir = root / docx_dir
        pdir = root / pdf_dir
        if not ddir.is_dir() or not pdir.is_dir():
            continue
        for docx in sorted(ddir.glob("*.docx")):
            if docx.name.startswith("~$"):
                continue
            oracle = pdir / f"{docx.stem}.pdf"
            if not oracle.is_file():
                continue
            found.append(
                Fixture(
                    stem=f"{kind}__{docx.stem}",
                    kind=kind,
                    original_stem=docx.stem,
                    docx=docx,
                    oracle=oracle,
                ),
            )
    return found


def select_word_oracle_fixtures(
    n: int | None = None, root: Path = WORD_CORPUS, *, track: Track | str | None = None,
) -> list[Fixture]:
    """All Word-oracle pairs for the track, or the first ``n`` in pool order."""
    spec = resolve_track(track)
    by_kind: dict[str, list[Fixture]] = {kind: [] for kind, _, _ in spec.pools}
    for item in discover_word_oracle_pairs(root, track=spec):
        by_kind[item.kind].append(item)
    selected: list[Fixture] = []
    for kind, _, _ in spec.pools:
        selected.extend(by_kind[kind])
    if n is not None:
        if len(selected) < n:
            raise RuntimeError(f"only {len(selected)} Word-oracle pairs available, need {n}")
        selected = selected[:n]
    return selected


def write_fixture_list(
    path: Path | None = None, n: int | None = None, *, track: Track | str | None = None,
) -> list[Fixture]:
    """Write the checked-in pin list from :func:`select_word_oracle_fixtures`."""
    spec = resolve_track(track)
    items = select_word_oracle_fixtures(n=n, track=spec)
    lines = [
        f"# Word-oracle DOCX→PDF pin ({spec.name}).",
        f"# Pools: {', '.join(spec.oracle_pdf_dir_names)} (SHA-256 pinned).",
        "# Staging key is {kind}__{original_stem}. Columns: kind<TAB>original_stem",
    ]
    for item in items:
        lines.append(f"{item.kind}\t{item.original_stem}")
    dest = path or spec.fixture_list
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return items


def docx_features(docx: Path) -> set[str]:
    """Feature tags from package XML (not from the redline coverage map)."""
    tags: set[str] = set()
    with zipfile.ZipFile(docx) as zf:
        names = set(zf.namelist())
        blobs: list[str] = []
        if "word/document.xml" in names:
            blobs.append(zf.read("word/document.xml").decode("utf-8", "replace"))
        for name in names:
            if name.startswith("word/header") and name.endswith(".xml"):
                tags.add("header")
                blobs.append(zf.read(name).decode("utf-8", "replace"))
            elif name.startswith("word/footer") and name.endswith(".xml"):
                tags.add("footer")
                blobs.append(zf.read(name).decode("utf-8", "replace"))
        xml = "\n".join(blobs)
    if "<w:t" in xml or "</w:t>" in xml:
        tags.add("body_text")
    if "<w:tbl" in xml:
        tags.add("table")
    if "<w:numPr" in xml or "<w:ilvl" in xml:
        tags.add("numbering")
    if "<w:drawing" in xml or "<a:blip" in xml or "<w:pict" in xml or "<v:imagedata" in xml:
        tags.add("image")
    if "header" in tags or "footer" in tags:
        tags.add("header_or_footer")
    return tags


def feature_coverage(fixtures: Iterable[Fixture]) -> set[str]:
    """Union of :func:`docx_features` across ``fixtures``."""
    found: set[str] = set()
    for item in fixtures:
        found |= docx_features(item.docx)
    return found


def aggregate(scores: dict[str, float]) -> dict[str, float | int]:
    """Mean / median / min / max / n over finite per-document scores."""
    vals = [v for v in scores.values() if isinstance(v, (int, float)) and math.isfinite(v)]
    if not vals:
        return {"n": 0}
    return {
        "mean": round(statistics.mean(vals), 4),
        "median": round(statistics.median(vals), 4),
        "min": round(min(vals), 4),
        "max": round(max(vals), 4),
        "n": len(vals),
    }


def _overall_map(full: dict[str, pipeline.ScoreResult]) -> dict[str, float]:
    return {key: pipeline.overall_from_result(result) for key, result in full.items()}


def score_folder_pair(
    oracle_dir: Path,
    candidate_dir: Path,
    work_dir: Path,
    *,
    dpi: int = 144,
    jobs: int = 8,
) -> dict[str, pipeline.ScoreResult]:
    """Score two PDF folders with the shipped plain-stem visual path."""
    return pipeline.score_folders_plain(
        oracle_dir, candidate_dir, work_dir, dpi=dpi, jobs=jobs,
    )


def convert_command(tool: str, src: Path, dest: Path, *, binary: Path) -> list[str]:
    """Argv for one vendor's own headless convert entry. No substitute pipelines."""
    if tool == "rdocx":
        return [str(binary), "convert", str(src), "--to", "pdf", "-o", str(dest)]
    if tool == "office2pdf":
        return [str(binary), str(src), "-o", str(dest)]
    if tool == "pdfitdown":
        return [str(binary), "-i", str(src), "-o", str(dest)]
    if tool == "doxx":
        # Upstream export formats are markdown/text/csv/json/ansi. Requesting PDF
        # is the honest convert attempt; a non-PDF result is a generate failure.
        return [str(binary), str(src), "--export", "pdf"]
    if tool == "jubarte":
        # Paint tracked changes the way Microsoft Word's Save as PDF does.
        return [str(binary), "convert", str(src), "-o", str(dest), "--force", "--revisions", "word"]
    if tool == "libreoffice_convert_rust":
        return [str(binary), str(src), str(dest), "pdf"]
    if tool == "dxpdf":
        return [str(binary), str(src), "-o", str(dest)]
    if tool in ("docxide-pdf", "pymupdf-pro"):
        return [str(binary), str(src), str(dest)]
    if tool == "genoffice":
        return [str(binary), "convert", str(src), "--to", "pdf", "--out", str(dest), "--force"]
    raise ValueError(f"unknown DOCX→PDF tool {tool!r}")


def resolve_tool_binary(tool: str, override: Path | None = None) -> Path:
    """Resolve a converter binary: ``override``, ``JUBARTE_BIN``, PATH, then ``~/.cargo/bin``."""
    if override is not None:
        return override
    env_bin = os.environ.get("JUBARTE_BIN") if tool == "jubarte" else None
    if env_bin:
        env_path = Path(env_bin).expanduser()
        if not env_path.is_file():
            raise FileNotFoundError(f"JUBARTE_BIN points to a missing file: {env_path}")
        return env_path
    if tool == "jubarte" and DEFAULT_CONVERTER.is_file():
        return DEFAULT_CONVERTER
    if tool == "pymupdf-pro" and PYMUPDF_PRO_CONVERTER.is_file():
        return PYMUPDF_PRO_CONVERTER
    names = _TOOL_BINARIES.get(tool, (tool,))
    for name in names:
        found = shutil.which(name)
        if found:
            return Path(found)
    cargo_bin = Path.home() / ".cargo" / "bin"
    for name in names:
        candidate = cargo_bin / name
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"{tool} binary not found (looked for {', '.join(names)} on PATH and {cargo_bin})",
    )


def _is_pdf(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0 and path.read_bytes()[:5] == b"%PDF-"


def try_convert_fixture(
    tool: str,
    binary: Path,
    fixture: Fixture,
    dest_pdf: Path,
    *,
    resume: bool = False,
    timeout_s: float | None = 180.0,
) -> dict[str, object] | None:
    """Run one convert. Return a generate-failure record, or None on a real PDF.

    Never raises for converter crashes, empty output, or non-PDF bytes.
    """
    dest_pdf.parent.mkdir(parents=True, exist_ok=True)
    if resume and _is_pdf(dest_pdf):
        return None
    if dest_pdf.exists() or dest_pdf.is_symlink():
        dest_pdf.unlink()
    cmd = convert_command(tool, fixture.docx, dest_pdf, binary=binary)
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except FileNotFoundError as exc:
        return {
            "doc": fixture.stem,
            "stage": "generate",
            "error": f"converter not found: {exc}",
            "cmd": cmd,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "doc": fixture.stem,
            "stage": "generate",
            "error": f"timeout after {exc.timeout}s",
            "cmd": cmd,
        }
    stderr = (proc.stderr or proc.stdout or "").strip()
    if proc.returncode != 0 or not _is_pdf(dest_pdf):
        header = b""
        if dest_pdf.is_file():
            header = dest_pdf.read_bytes()[:5]
            dest_pdf.unlink(missing_ok=True)
        detail = stderr or f"exit {proc.returncode}"
        if header and header != b"%PDF-":
            detail = f"output is not a PDF ({header!r}); {detail}"
        elif not dest_pdf.is_file():
            detail = f"no PDF written; {detail}"
        return {
            "doc": fixture.stem,
            "stage": "generate",
            "error": detail,
            "cmd": cmd,
        }
    return None


def convert_fixture(converter: Path, fixture: Fixture, dest_pdf: Path) -> None:
    """Legacy jubarte-shaped convert; raises on failure."""
    fail = try_convert_fixture("jubarte", converter, fixture, dest_pdf, resume=False)
    if fail is not None:
        raise RuntimeError(f"converter failed for {fixture.stem}: {fail['error']}")


def try_convert_fixtures(
    tool: str,
    binary: Path,
    fixtures: list[Fixture],
    dest_dir: Path,
    *,
    resume: bool = True,
    workers: int = 1,
    timeout_s: float | None = 180.0,
) -> list[dict[str, object]]:
    """Convert every fixture; never abort on a single failure."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    total = len(fixtures)

    def one(item: Fixture) -> dict[str, object] | None:
        return try_convert_fixture(
            tool,
            binary,
            item,
            dest_dir / f"{item.stem}.pdf",
            resume=resume,
            timeout_s=timeout_s,
        )

    failures: list[dict[str, object]] = []
    if workers <= 1 or total <= 1:
        for idx, item in enumerate(fixtures, 1):
            fail = one(item)
            if fail is not None:
                failures.append(fail)
            if idx == total or idx % 10 == 0:
                print(f"{tool} converted {idx}/{total} ({len(failures)} failures)", flush=True)
        return failures

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(one, item) for item in fixtures]
        for fut in as_completed(futures):
            fail = fut.result()
            if fail is not None:
                failures.append(fail)
            done += 1
            if done == total or done % 10 == 0:
                print(f"{tool} converted {done}/{total} ({len(failures)} failures)", flush=True)
    return failures


def link_or_copy(src: Path, target: Path) -> None:
    """Hardlink ``src`` onto ``target``, or copy the bytes when the link fails."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        target.unlink()
    try:
        if _same_fs(src, target.parent):
            target.hardlink_to(src)
            return
    except OSError:
        pass
    _copy(src, target)


def stage_oracles(fixtures: list[Fixture], dest_dir: Path) -> Path:
    """Copy Word oracles into ``dest_dir`` under their unique staging stems."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    for item in fixtures:
        link_or_copy(item.oracle, dest_dir / f"{item.stem}.pdf")
    return dest_dir


def stage_candidates(fixtures: list[Fixture], sources: dict[str, Path], dest_dir: Path) -> list[dict[str, object]]:
    """Stage score-only PDFs under each fixture stem. Missing sources are failures."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    failures: list[dict[str, object]] = []
    for item in fixtures:
        src = sources.get(item.stem)
        if src is None or not src.is_file():
            failures.append(
                {
                    "doc": item.stem,
                    "stage": "generate",
                    "error": "no PDF to score",
                    "cmd": [],
                },
            )
            continue
        link_or_copy(src, dest_dir / f"{item.stem}.pdf")
    return failures


def _same_fs(src: Path, dest_dir: Path) -> bool:
    try:
        return src.stat().st_dev == dest_dir.stat().st_dev
    except OSError:
        return False


def _copy(src: Path, dest: Path) -> None:
    dest.write_bytes(src.read_bytes())


def _version_from_cargo_install_list(binary_name: str) -> str | None:
    """Parse ``cargo install --list`` for the package owning ``binary_name``."""
    try:
        proc = subprocess.run(
            ["cargo", "install", "--list"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    current: str | None = None
    for line in (proc.stdout or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not line.startswith(" ") and line.startswith(" ") is False:
            # Package header line: "<name> v<version>:"
            if stripped.endswith(":"):
                header = stripped[:-1]
                if " v" in header:
                    current = header
        if stripped == binary_name:
            return current
    return None


def tool_version(binary: Path | None) -> str | None:
    """Best-effort ``--version`` line for a converter binary."""
    if binary is None or not Path(binary).is_file():
        return None
    binary_name = Path(binary).name
    try:
        proc = subprocess.run(
            [str(binary), "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode == 0:
        text = (proc.stdout or "").strip()
        if text:
            return text.splitlines()[0]
    return _version_from_cargo_install_list(binary_name)


def _tool_report(
    tool: str,
    converter: Path | None,
    stems: list[str],
    scores: dict[str, float],
    failures: list[dict[str, object]],
    *,
    version: str | None = None,
) -> dict:
    failed = {str(item["doc"]) for item in failures}
    per_doc: dict[str, float] = {}
    for stem in stems:
        if stem in scores:
            per_doc[stem] = scores[stem]
        else:
            per_doc[stem] = 0.0
    vals = list(per_doc.values())
    return {
        "tool": tool,
        "converter": None if converter is None else str(converter),
        "version": version,
        "n_scored": len(scores),
        "itt_n": len(stems),
        "mean": round(statistics.mean(vals), 4) if vals else 0.0,
        "median": round(statistics.median(vals), 4) if vals else 0.0,
        "perfects": sum(1 for value in vals if value >= 100.0 - 1e-9),
        "failures": len(failed),
        "per_doc": per_doc,
        "generate_failures": failures,
        "aggregate": aggregate(scores),
    }


def run_eval(
    json_out: Path,
    *,
    converter: Path | None = None,
    tools: Sequence[str] | None = None,
    jobs: int = 8,
    dpi: int = 144,
    work_dir: Path | None = None,
    limit: int | None = None,
    fixtures: list[Fixture] | None = None,
    resume: bool = True,
    convert_workers: int = 8,
    track: Track | str | None = None,
    check_pins: bool = True,
    score_only: bool = False,
    candidates: dict[str, Path] | None = None,
    warnings: Sequence[str] | None = None,
) -> dict:
    """Convert the pin list with each tool and score against Word oracles.

    Convert failures do not abort the rest of the set. Missing candidates are
    ITT-scored as 0. Returns the report dict and writes it to ``json_out``.

    ``check_pins`` is for the SHA-pinned Word sets. Corpus selections pass
    ``fixtures`` and ``check_pins=False``. ``score_only`` skips every converter
    and scores ``candidates`` (fixture stem to PDF) instead.
    """
    if fixtures is None:
        spec = resolve_track(track)
        items = load_fixtures(track=spec)
    else:
        spec = resolve_track(track) if check_pins else None
        items = list(fixtures)
    if tools is None:
        tools = ("jubarte",) if converter is not None else WORD_PDF_TOOLS
    if limit is not None:
        items = items[:limit]
    if not items:
        raise RuntimeError("no docx-to-pdf fixtures to evaluate")
    if check_pins:
        if spec is None:
            spec = resolve_track(track)
        verify_oracle_sha_manifest(track=spec)
        for item in items:
            oracle = item.oracle.resolve()
            allowed = {d.resolve() for d in oracle_pdf_dirs(track=spec)}
            if oracle.parent not in allowed:
                raise RuntimeError(f"oracle {oracle} is not in the pinned Word-export folders")

    root = work_dir if work_dir is not None else json_out.parent / "docx_to_pdf_work"
    oracle_dir = stage_oracles(items, root / "oracle")
    stems = [item.stem for item in items]
    track_name = spec.name if spec is not None else (track if isinstance(track, str) else "word")
    report: dict = {
        "track": track_name,
        "oracle": "microsoft_word",
        "generated_at": datetime.now(UTC).isoformat(),
        "n": len(items),
        "stems": stems,
        "warnings": list(warnings or []),
        "tools": {},
    }

    for tool in tools:
        if score_only:
            print(f"scoring {tool} vs Word oracle ({len(items)} docs)", flush=True)
            cand_dir = root / tool / "candidate"
            failures = stage_candidates(items, candidates or {}, cand_dir)
            score_dir = root / tool / "score"
            cand_full = score_folder_pair(
                oracle_dir, cand_dir, score_dir, dpi=dpi, jobs=jobs,
            )
            cand_scores = _overall_map(cand_full)
            shutil.rmtree(score_dir, ignore_errors=True)
            report["tools"][tool] = _tool_report(
                tool, None, stems, cand_scores, failures, version=None,
            )
            continue
        print(f"converting with {tool} ({len(items)} docs)", flush=True)
        try:
            binary: Path | None = resolve_tool_binary(tool, converter if len(list(tools)) == 1 else None)
        except FileNotFoundError as exc:
            binary = None
            failures: list[dict[str, object]] = [
                {
                    "doc": item.stem,
                    "stage": "generate",
                    "error": str(exc),
                    "cmd": [tool],
                }
                for item in items
            ]
            cand_dir = root / tool / "candidate"
            cand_dir.mkdir(parents=True, exist_ok=True)
            cand_scores: dict[str, float] = {}
        else:
            if len(list(tools)) == 1 and converter is not None:
                binary = converter
            cand_dir = root / tool / "candidate"
            failures = try_convert_fixtures(
                tool, binary, items, cand_dir, resume=resume, workers=convert_workers,
            )
            print(f"scoring {tool} vs Word oracle ({len(items)} docs)", flush=True)
            score_dir = root / tool / "score"
            cand_full = score_folder_pair(
                oracle_dir, cand_dir, score_dir, dpi=dpi, jobs=jobs,
            )
            cand_scores = _overall_map(cand_full)
            shutil.rmtree(score_dir, ignore_errors=True)

        report["tools"][tool] = _tool_report(
            tool,
            binary,
            stems,
            cand_scores,
            failures,
            version=tool_version(binary),
        )

    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report
