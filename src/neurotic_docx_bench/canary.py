"""Renderer fingerprint canary (PR5).

LibreOffice rendering depends on the LO build and the installed fonts; a silent font
substitution shifts every raster a few pixels and reads as a mass score change with
no visible cause. Before any scoring, ``bench run`` renders one small committed
corpus DOCX and compares the page-1 PNG hash against the committed expectation for
the CURRENT LibreOffice version:

- match → proceed;
- mismatch → abort (exit 2): the environment drifted, scores would be incomparable;
- no expectation for this LO version / dpi → warn and proceed (CI runs a different
  LO on purpose and regenerates the oracle in-image).

``bench canary --write`` baselines the current environment. Expectations live in
``corpus/canary_expected.json`` keyed by LO version so multiple environments can
coexist.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from neurotic_docx_bench import raster
from neurotic_docx_bench.render.soffice import SofficeRenderer, convert_one

DEFAULT_CANARY_DOCX = Path("corpus/word_based/docx_source/24_id_paraid_overflow.docx")
DEFAULT_SPEC_PATH = Path("corpus/canary_expected.json")

_VERSION_RE = re.compile(r"LibreOffice\s+(\d+(?:\.\d+)+)")


@dataclass(frozen=True)
class CanaryOutcome:
    status: str  # "ok" | "mismatch" | "no-baseline"
    detail: str = ""


def parse_soffice_version(output: str) -> str | None:
    m = _VERSION_RE.search(output)
    return m.group(1) if m else None


def current_soffice_version() -> str | None:
    """Resolve soffice the same way rendering does ($SOFFICE / PATH / app), then
    parse ``--version`` from stdout+stderr (some LO builds put the banner on stderr)."""
    from neurotic_docx_bench.render.soffice import find_soffice

    try:
        soffice = find_soffice()
    except RuntimeError:
        return None
    try:
        proc = subprocess.run(
            [str(soffice), "--version"], capture_output=True, text=True, timeout=60,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    return parse_soffice_version((proc.stdout or "") + "\n" + (proc.stderr or ""))


def render_canary_hash(docx: Path, work_dir: Path, *, dpi: int = 144) -> str:
    """Render the single canary DOCX via the soffice backend and hash the page-1 PNG."""
    renderer = SofficeRenderer()
    soffice = renderer._resolve_soffice()  # noqa: SLF001 — same-package reuse
    result = convert_one(soffice, docx, work_dir / "pdf", force=True)
    if not result.ok or result.pdf is None:
        raise RuntimeError(f"canary render failed: {result.error or '?'}")
    pages_dir = work_dir / "pages"
    raster.rasterize_pdf(result.pdf, pages_dir, dpi=dpi)
    pages = sorted(pages_dir.glob("page_*.png"))
    if not pages:
        raise RuntimeError("canary raster produced no pages")
    return hashlib.sha256(pages[0].read_bytes()).hexdigest()


class CanarySpecError(ValueError):
    """Raised when a canary expectation file exists but is unreadable/malformed."""


def load_canary_spec(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise CanarySpecError(f"malformed canary spec at {path}: {exc}") from exc
    except OSError as exc:
        raise CanarySpecError(f"unreadable canary spec at {path}: {exc}") from exc
    if not isinstance(data, dict) or "docx" not in data:
        raise CanarySpecError(f"canary spec at {path} missing required 'docx' field")
    return data


def write_canary_spec(path: Path, docx: Path, expected: dict[str, dict]) -> None:
    try:
        existing = load_canary_spec(path)
    except CanarySpecError:
        existing = None  # overwrite a corrupt file with a clean baseline
    merged = dict((existing or {}).get("expected", {}))
    merged.update(expected)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"docx": docx.as_posix(), "expected": merged}, indent="\t", sort_keys=True)
        + "\n",
    )


def expected_hash(spec: dict, version: str, dpi: int) -> str | None:
    entry = (spec.get("expected") or {}).get(version)
    if not isinstance(entry, dict) or int(entry.get("dpi", -1)) != dpi:
        return None
    value = entry.get("page1_sha256")
    return str(value) if value else None


def check(spec_path: Path, work_dir: Path, *, dpi: int = 144) -> CanaryOutcome:
    try:
        spec = load_canary_spec(spec_path)
    except CanarySpecError as exc:
        return CanaryOutcome("invalid-spec", str(exc))
    if spec is None:
        return CanaryOutcome("no-baseline", f"no canary spec at {spec_path}")
    version = current_soffice_version()
    if version is None:
        return CanaryOutcome("no-baseline", "soffice not found ($SOFFICE / PATH / app bundle)")
    expected = expected_hash(spec, version, dpi)
    if expected is None:
        return CanaryOutcome(
            "no-baseline",
            f"no canary expectation for LibreOffice {version} @ {dpi}dpi "
            f"(baseline it: bench canary --write)",
        )
    docx = Path(str(spec["docx"]))
    actual = render_canary_hash(docx, work_dir, dpi=dpi)
    if actual == expected:
        return CanaryOutcome("ok", f"LibreOffice {version} fingerprint OK")
    return CanaryOutcome(
        "mismatch",
        f"renderer fingerprint changed for LibreOffice {version} @ {dpi}dpi: "
        f"expected {expected}, got {actual} — fonts or LO build drifted",
    )
