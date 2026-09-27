"""Machine and renderer identity stamped on every emitted result line.

Speed numbers without a machine are not comparable; fidelity numbers without a
renderer version are not reproducible. Both are cheap to record and were absent.
"""

from __future__ import annotations

import os
import platform
import subprocess
from collections.abc import Callable

from neurotic_docx_bench.config import RunConfig


def soffice_version() -> str | None:
    """LibreOffice version string, via the canary's parser; None when not installed."""
    from neurotic_docx_bench import canary

    try:
        return canary.current_soffice_version()
    except OSError, RuntimeError:
        return None


def _cpu_brand(
    *,
    system: str | None = None,
    cpuinfo: str = "/proc/cpuinfo",
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> str:
    """CPU brand string; the OS boundaries are parameters so each branch is testable."""
    system = platform.system() if system is None else system
    try:
        if system == "Darwin":
            out = run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        elif system == "Linux":
            with open(cpuinfo, encoding="utf-8") as fh:
                for line in fh:
                    if line.lower().startswith("model name"):
                        return line.split(":", 1)[1].strip()
    except OSError, subprocess.SubprocessError:
        pass
    return platform.processor() or platform.machine()


def _ram_gb() -> float:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return round(pages * page_size / 2**30, 1)
    except ValueError, OSError, AttributeError:
        return 0.0


def hardware_info() -> dict[str, object]:
    return {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "cpu": _cpu_brand(),
        "cores": os.cpu_count() or 1,
        "ram_gb": _ram_gb() or 0.1,
        "python": platform.python_version(),
    }


def word_version() -> str | None:
    """Microsoft Word's version string; None when Word is not reachable."""
    from neurotic_docx_bench.render import word

    return word.word_version()


def renderer_id(rc: RunConfig) -> str:
    if rc.render == "soffice":
        return f"soffice-{soffice_version() or 'unknown'}"
    if rc.render == "word":
        return f"word-{word_version() or 'unknown'}"
    if rc.render == "playwright":
        return f"playwright:{rc.package or rc.name}"
    return rc.render
