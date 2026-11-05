"""The 1.0.0 distributions: the wheel carries the fixture manifest and no fixture, the sdist the package only (#84)."""

from __future__ import annotations

import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def dist(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if shutil.which("uv") is None:
        pytest.skip("uv is not on PATH")
    out = tmp_path_factory.mktemp("dist")
    subprocess.run(["uv", "build", "-q", "-o", str(out)], cwd=ROOT, check=True)
    return out


def test_the_wheel_ships_the_manifest_and_no_document(dist: Path) -> None:
    [wheel] = dist.glob("*.whl")
    names = zipfile.ZipFile(wheel).namelist()
    assert "neurotic_docx_bench/data/fixture_sets/v1.csv.gz" in names
    assert "neurotic_docx_bench/data/fixture_sets/v1.json" in names
    assert "neurotic_docx_bench/py.typed" in names
    assert not [n for n in names if n.endswith((".docx", ".pdf", ".png"))]
    assert not [n for n in names if "/utils/" in n]
    assert wheel.stat().st_size < 5_000_000


def test_the_sdist_is_the_package_only(dist: Path) -> None:
    [sdist] = dist.glob("*.tar.gz")
    tops = {Path(m.name).parts[1] for m in tarfile.open(sdist).getmembers() if len(Path(m.name).parts) > 1}
    assert tops <= {"src", "licenses", "LICENSE", "README.md", "CHANGELOG.md", "CITATION.cff", "pyproject.toml",
                    "PKG-INFO", ".gitignore"}
