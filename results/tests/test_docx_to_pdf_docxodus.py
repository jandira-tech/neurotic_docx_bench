"""#89: Docxodus as a DOCX→PDF converter (``@docxodus/export``, pinned Chromium print).

Every failure mode the converter can show is a generate failure scored 0, never a
stale or broken PDF that reaches the scorer; a missing install is an adapter gap,
not the vendor's score.
"""

from __future__ import annotations

import json
import stat
import subprocess
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pymupdf
import pytest

from neurotic_docx_bench import docx_to_pdf as d2p
from neurotic_docx_bench.ledger import converters as conv

ARGV = ["--review-profile", "markup", "--markup-presentation", "word", "--comments", "margin",
        "--comment-column-placement", "balloons"]
DEFAULT_FONT_SOURCES = d2p.DOCXODUS_FONT_SOURCES


@pytest.fixture(autouse=True)
def isolated_font_stage(tmp_path: Path, monkeypatch):
    source = tmp_path / "fonts"
    source.mkdir()
    (source / "Carlito-Regular.ttf").write_bytes(b"metric font")
    monkeypatch.setattr(d2p, "DOCXODUS_FONT_SOURCES", (source,))
    monkeypatch.setattr(d2p, "DOCXODUS_FONT_STAGE", tmp_path / "stage")
    monkeypatch.setattr(d2p, "_DOCXODUS_FONT_DIR", None, raising=False)


def _pdf_bytes(pages: int = 1) -> bytes:
    doc = pymupdf.open()
    for _ in range(pages):
        doc.new_page().insert_text((72, 72), "converted")
    data = doc.tobytes()
    doc.close()
    return data


def _fixture(tmp_path: Path, name: str = "a doc with spaces") -> d2p.Fixture:
    folder = tmp_path / "corpus dir" / "clean" / "docx"
    folder.mkdir(parents=True, exist_ok=True)
    docx = folder / f"{name}.docx"
    docx.write_bytes(b"PK fake docx")
    oracle = tmp_path / f"{name}.pdf"
    oracle.write_bytes(_pdf_bytes())
    return d2p.Fixture(stem=f"clean__{name}", kind="clean", original_stem=name, docx=docx, oracle=oracle)


def _converter(tmp_path: Path, body: str) -> Path:
    """A fake ``docxodus`` CLI; ``$OUT`` is the --output argument."""
    script = tmp_path / "bin" / "docxodus"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(
        "#!/bin/sh\n"
        'OUT=""\n'
        'while [ $# -gt 0 ]; do\n  if [ "$1" = "--output" ]; then OUT="$2"; fi\n  shift\ndone\n'
        '[ -n "$OUT" ] || { echo "usage: docxodus convert IN --to pdf --output OUT" >&2; exit 2; }\n'
        f"{body}\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script




def test_docxodus_is_a_named_converter() -> None:
    assert "docxodus" in d2p.WORD_PDF_TOOLS


def test_the_argv_is_the_documented_cli_with_words_markup(tmp_path: Path) -> None:
    """``docxodus convert IN --to pdf --output OUT``, tracked changes painted as Word prints them."""
    src, dest = tmp_path / "in put.docx", tmp_path / "out put.pdf"
    cmd = d2p.convert_command("docxodus", src, dest, binary=Path("/opt/dx/docxodus"))
    assert cmd[:7] == ["/opt/dx/docxodus", "convert", str(src), "--to", "pdf", "--output", str(dest)]
    assert cmd[7:15] == ARGV
    assert cmd[15:17] == ["--timeout", str(int(d2p.CONVERT_TIMEOUT_S * 1000))]


@pytest.mark.parametrize("tool", ["docxodus", "jubarte"])
@pytest.mark.parametrize("timeout", [d2p.CONVERT_TIMEOUT_S, 1, None])
def test_subprocess_budget_allows_docxodus_to_stop_cleanly(tmp_path: Path, monkeypatch, tool, timeout) -> None:
    item = _fixture(tmp_path)
    dest = tmp_path / "cand" / "a.pdf"
    budgets = []

    def run(cmd, **kwargs):
        budgets.append(kwargs["timeout"])
        dest.write_bytes(_pdf_bytes())
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(d2p.subprocess, "run", run)
    assert d2p.try_convert_fixture(tool, Path("converter"), item, dest, timeout_s=timeout) is None
    expected = timeout + 15 if tool == "docxodus" and timeout == d2p.CONVERT_TIMEOUT_S else timeout
    assert budgets == [expected]


def test_the_pinned_install_is_resolved_before_path(monkeypatch) -> None:
    monkeypatch.setattr(d2p.shutil, "which", lambda _name: "/usr/bin/docxodus-somebody-else")
    monkeypatch.setattr(d2p, "DOCXODUS_CONVERTER", Path(__file__))  # any existing file
    assert d2p.resolve_tool_binary("docxodus") == Path(__file__)
    assert d2p.DOCXODUS_CONVERTER_DIR.name == "docxodus-export"


def test_a_real_pdf_with_a_space_in_every_path_converts(tmp_path: Path) -> None:
    fx = _fixture(tmp_path)
    good = tmp_path / "good.pdf"
    good.write_bytes(_pdf_bytes(2))
    binary = _converter(tmp_path, f'cp "{good}" "$OUT"')
    dest = tmp_path / "cand dir" / f"{fx.stem}.pdf"
    assert d2p.try_convert_fixture("docxodus", binary, fx, dest) is None
    assert pymupdf.open(dest).page_count == 2


def test_a_pdf_with_an_unloadable_second_page_is_a_conversion_failure(tmp_path: Path) -> None:
    with pymupdf.open(stream=_pdf_bytes(2), filetype="pdf") as doc:
        xref = doc.page_xref(1)
        data = doc.tobytes()
    marker = f"{xref} 0 obj\n".encode()
    start = data.index(marker) + len(marker)
    end = data.index(b"\nendobj", start)
    # Keep the xref offsets intact but replace page 2 with an empty page-tree node.
    broken_page = b"<</Type/Pages/Count 0/Kids[]>>"
    assert len(broken_page) <= end - start
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(data[:start] + broken_page.ljust(end - start) + data[end:])
    with pymupdf.open(broken) as doc:
        assert doc.page_count == 2
        assert doc.load_page(0).get_text().strip() == "converted"
        with pytest.raises(ValueError, match="page not in document"):
            doc.load_page(1)
    binary = _converter(tmp_path, f'cp "{broken}" "$OUT"')
    dest = tmp_path / "candidate" / "a.pdf"
    error = d2p.try_convert_fixture("docxodus", binary, _fixture(tmp_path), dest)
    assert error is not None, "an unloadable later page must fail conversion"
    assert "unreadable PDF" in error["error"]
    assert not dest.exists()


@pytest.mark.parametrize(
    ("body", "error"),
    [
        ('echo "browser crashed" >&2; exit 3', "browser crashed"),
        ("exit 0", "no PDF written"),
        (': > "$OUT"', "no PDF written"),
        ('printf "<html>" > "$OUT"', "not a PDF"),
        ('printf "%%PDF-1.7 truncated garbage" > "$OUT"', "unreadable PDF"),
    ],
    ids=["crash", "exit0-no-output", "empty", "not-pdf", "corrupt-behind-header"],
)
def test_every_bad_outcome_is_a_generate_failure_and_leaves_no_pdf(tmp_path: Path, body: str, error: str) -> None:
    fx = _fixture(tmp_path)
    dest = tmp_path / "cand" / f"{fx.stem}.pdf"
    fail = d2p.try_convert_fixture("docxodus", _converter(tmp_path, body), fx, dest)
    assert fail is not None and fail["stage"] == "generate" and error in str(fail["error"])
    assert not dest.exists()


def test_a_stale_pdf_never_survives_a_failed_convert(tmp_path: Path) -> None:
    """The previous run's PDF is removed first; a nonzero exit cannot pass it off as this run's."""
    fx = _fixture(tmp_path)
    dest = tmp_path / "cand" / f"{fx.stem}.pdf"
    dest.parent.mkdir(parents=True)
    dest.write_bytes(_pdf_bytes())
    fail = d2p.try_convert_fixture("docxodus", _converter(tmp_path, "exit 9"), fx, dest)
    assert fail is not None and not dest.exists()


def test_a_timeout_leaves_no_partial_pdf(tmp_path: Path) -> None:
    fx = _fixture(tmp_path)
    dest = tmp_path / "cand" / f"{fx.stem}.pdf"
    binary = _converter(tmp_path, 'printf "%%PDF-1.7 half" > "$OUT"; exec sleep 30')
    fail = d2p.try_convert_fixture("docxodus", binary, fx, dest, timeout_s=1)
    assert fail is not None and "timeout" in str(fail["error"])
    assert not dest.exists()


def test_a_partial_batch_keeps_going_and_times_every_document(tmp_path: Path) -> None:
    good = tmp_path / "good.pdf"
    good.write_bytes(_pdf_bytes())
    items = [_fixture(tmp_path, f"doc {i}") for i in range(3)]
    binary = _converter(tmp_path, f'sleep 0.2; case "$OUT" in *"doc 1"*) exit 4;; esac; cp "{good}" "$OUT"')
    seconds: dict[str, float] = {}
    failures = d2p.try_convert_fixtures("docxodus", binary, items, tmp_path / "cand", workers=2,
                                        resume=False, seconds=seconds)
    assert [f["doc"] for f in failures] == ["clean__doc 1"]
    assert set(seconds) == {i.stem for i in items} and all(s >= 0.2 for s in seconds.values())


def test_a_missing_install_is_an_adapter_gap_not_a_score(tmp_path: Path, monkeypatch) -> None:
    items = [_fixture(tmp_path, f"doc {i}") for i in range(2)]

    def missing(tool: str, override=None) -> Path:
        raise FileNotFoundError(f"{tool} binary not found")

    monkeypatch.setattr(d2p, "resolve_tool_binary", missing)
    monkeypatch.setattr(d2p, "score_folder_pair", lambda *a, **k: {})
    report = d2p.run_eval(tmp_path / "r.json", tools=("docxodus",), work_dir=tmp_path / "w", fixtures=items,
                          check_pins=False, track="corpus/word:all", resume=False)
    tool = report["tools"]["docxodus"]
    assert "not found" in tool["adapter_gap"]
    assert conv.lines_from_report(report, hardware=None, report_path="r.json") == []  # nothing to rank


def test_the_report_records_conversion_seconds_per_document(tmp_path: Path, monkeypatch) -> None:
    good = tmp_path / "good.pdf"
    good.write_bytes(_pdf_bytes())
    items = [_fixture(tmp_path, f"doc {i}") for i in range(2)]
    binary = _converter(tmp_path, f'sleep 0.2; cp "{good}" "$OUT"')
    monkeypatch.setattr(d2p, "score_folder_pair", lambda *a, **k: {})
    report = d2p.run_eval(tmp_path / "r.json", tools=("docxodus",), converter=binary, work_dir=tmp_path / "w",
                          fixtures=items, check_pins=False, track="corpus/word:all", resume=False)
    tool = report["tools"]["docxodus"]
    assert set(tool["convert_seconds"]) == {i.stem for i in items}
    assert all(s >= 0.2 for s in tool["convert_seconds"].values())
    assert json.loads((tmp_path / "r.json").read_text())["tools"]["docxodus"]["convert_seconds"]


@pytest.mark.parametrize("workers", [1, 8])
def test_resumed_valid_pdf_is_not_a_timing_sample(tmp_path: Path, workers: int) -> None:
    items = [_fixture(tmp_path, f"doc {i}") for i in range(2)]
    cand = tmp_path / "cand"
    cand.mkdir()
    for item in items:
        (cand / f"{item.stem}.pdf").write_bytes(_pdf_bytes())
    called = tmp_path / "called"
    binary = _converter(tmp_path, f'touch "{called}"; exit 4')
    seconds: dict[str, float] = {}
    assert d2p.try_convert_fixtures("docxodus", binary, items, cand, workers=workers, seconds=seconds) == []
    assert not called.exists()
    assert seconds == {}


def test_resumed_truncated_pdf_is_reconverted(tmp_path: Path) -> None:
    item = _fixture(tmp_path)
    dest = tmp_path / "cand" / f"{item.stem}.pdf"
    dest.parent.mkdir()
    dest.write_bytes(b"%PDF-1.7 truncated garbage")
    good = tmp_path / "good.pdf"
    good.write_bytes(_pdf_bytes())
    binary = _converter(tmp_path, f'cp "{good}" "$OUT"')
    assert d2p.try_convert_fixture("docxodus", binary, item, dest, resume=True) is None
    assert dest.read_bytes() == good.read_bytes()


def test_resumed_batch_times_only_reconverted_pdf(tmp_path: Path) -> None:
    items = [_fixture(tmp_path, f"doc {i}") for i in range(2)]
    cand = tmp_path / "cand"
    cand.mkdir()
    good = _pdf_bytes()
    (cand / f"{items[0].stem}.pdf").write_bytes(good)
    (cand / f"{items[1].stem}.pdf").write_bytes(b"%PDF-1.7 truncated garbage")
    source = tmp_path / "good.pdf"
    source.write_bytes(good)
    binary = _converter(tmp_path, f'sleep 0.2; cp "{source}" "$OUT"')
    seconds: dict[str, float] = {}
    assert d2p.try_convert_fixtures("docxodus", binary, items, cand, workers=8, seconds=seconds) == []
    assert set(seconds) == {items[1].stem}
    assert seconds[items[1].stem] >= 0.2
    assert (cand / f"{items[1].stem}.pdf").read_bytes() == good


def test_the_cli_can_score_without_touching_the_store(tmp_path: Path, monkeypatch) -> None:
    """A scratch evaluation (#89): ``--no-store`` writes the report and appends nothing."""
    from typer.testing import CliRunner

    from neurotic_docx_bench import cli

    calls: list[object] = []
    monkeypatch.setattr(cli, "_append_converter_lines", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(d2p, "run_eval", lambda json_out, **k: {"n": 0, "tools": {}})
    monkeypatch.setattr(cli, "_corpus_word_selection", lambda **k: type("S", (), {
        "fixtures": [object()], "candidates": {}, "warnings": []})())
    got = CliRunner().invoke(cli.app, ["docx-to-pdf", "--tool", "docxodus", "--no-store",
                                       "--json", str(tmp_path / "r.json")])
    assert got.exit_code == 0, got.output
    assert calls == []


def test_the_version_is_what_node_modules_actually_loads(tmp_path: Path) -> None:
    """Vendor notes: a root pin once disagreed with a stale nested module; read the installed manifests."""
    nm = tmp_path / "node_modules"
    for pkg, version in (("@docxodus/export", "14.2.0"), ("docxodus", "14.2.0")):
        (nm / pkg).mkdir(parents=True)
        (nm / pkg / "package.json").write_text(json.dumps({"name": pkg, "version": version}))
    (nm / ".bin").mkdir()
    binary = nm / ".bin" / "docxodus"
    binary.write_text("#!/bin/sh\necho usage >&2; exit 2\n")
    binary.chmod(0o755)
    assert d2p.tool_version(binary) == "@docxodus/export 14.2.0 (docxodus 14.2.0)"


def test_docxodus_gets_the_metric_fonts_libreoffice_renders_with(tmp_path: Path, monkeypatch) -> None:
    """Fairness (#89): without --font-directory docxodus falls back to browser fonts. It gets the
    Carlito/Caladea/Liberation faces LibreOffice ships (the substitutes docxodus documents), staged
    alone, because docxodus refuses a whole folder holding one variable font."""
    lo = tmp_path / "LibreOffice fonts"
    lo.mkdir()
    for name in ("Carlito-Regular.ttf", "Caladea-Bold.ttf", "LiberationSerif-Italic.ttf",
                 "NotoSans-VariableFont.ttf", "DejaVuSans.ttf", "fc_local.conf"):
        (lo / name).write_bytes(name.encode())
    monkeypatch.setattr(d2p, "DOCXODUS_FONT_SOURCES", (tmp_path / "absent", lo))
    monkeypatch.setattr(d2p, "DOCXODUS_FONT_STAGE", tmp_path / "stage")
    cmd = d2p.convert_command("docxodus", tmp_path / "a.docx", tmp_path / "a.pdf", binary=Path("/opt/dx/docxodus"))
    assert cmd[-2:] == ["--font-directory", str(tmp_path / "stage")] and cmd.count("--font-directory") == 1
    staged = sorted(p.name for p in (tmp_path / "stage").iterdir())
    assert staged == ["Caladea-Bold.ttf", "Carlito-Regular.ttf", "LiberationSerif-Italic.ttf"]
    assert (tmp_path / "stage" / "Carlito-Regular.ttf").read_bytes() == b"Carlito-Regular.ttf"


@pytest.mark.parametrize("override", [False, True])
def test_no_metric_fonts_refuses_converter_resolution(tmp_path: Path, monkeypatch, override: bool) -> None:
    sources = (tmp_path / "absent", tmp_path / "also absent")
    monkeypatch.setattr(d2p, "DOCXODUS_FONT_SOURCES", sources)
    monkeypatch.setattr(d2p, "DOCXODUS_CONVERTER", Path(__file__))
    with pytest.raises(FileNotFoundError, match="metric fonts") as exc:
        d2p.resolve_tool_binary("docxodus", Path(__file__) if override else None)
    assert all(str(source) in str(exc.value) for source in sources)


def test_missing_metric_fonts_leave_nothing_to_rank(tmp_path: Path, monkeypatch) -> None:
    item = _fixture(tmp_path)
    monkeypatch.setattr(d2p, "DOCXODUS_FONT_SOURCES", (tmp_path / "absent",))
    good = tmp_path / "good.pdf"
    good.write_bytes(_pdf_bytes())
    binary = _converter(tmp_path, f'cp "{good}" "$OUT"')
    scored = []
    monkeypatch.setattr(d2p, "score_folder_pair", lambda *a, **k: scored.append(a) or {})
    report = d2p.run_eval(tmp_path / "r.json", tools=("docxodus",), converter=binary,
                          work_dir=tmp_path / "w", fixtures=[item], check_pins=False,
                          track="corpus/word:all", resume=False)
    assert scored == []
    assert "metric fonts" in report["tools"]["docxodus"]["adapter_gap"]
    assert conv.lines_from_report(report, hardware=None, report_path="r.json") == []


def test_the_default_font_source_is_libreoffices_bundle() -> None:
    assert any(p.parts[-3:] == ("Resources", "fonts", "truetype") for p in DEFAULT_FONT_SOURCES)


def test_concurrent_font_staging_copies_each_face_once(tmp_path: Path, monkeypatch) -> None:
    source = d2p.DOCXODUS_FONT_SOURCES[0]
    (source / "Caladea-Bold.ttf").write_bytes(b"second face")
    copies: Counter[str] = Counter()
    copyfile = d2p.shutil.copyfile
    barrier = threading.Barrier(8)

    def copy(src, dest):
        copies[Path(src).name] += 1
        return copyfile(src, dest)

    def stage(_):
        barrier.wait()
        path = d2p.docxodus_font_dir()
        assert sorted(p.name for p in path.iterdir()) == ["Caladea-Bold.ttf", "Carlito-Regular.ttf"]
        return path

    monkeypatch.setattr(d2p.shutil, "copyfile", copy)
    with ThreadPoolExecutor(max_workers=8) as pool:
        paths = list(pool.map(stage, range(8)))
    assert paths == [d2p.DOCXODUS_FONT_STAGE] * 8
    assert copies == {"Caladea-Bold.ttf": 1, "Carlito-Regular.ttf": 1}
    (source / "Carlito-Regular.ttf").write_bytes(b"changed after staging")
    assert d2p.docxodus_font_dir().joinpath("Carlito-Regular.ttf").read_bytes() == b"metric font"


def test_font_staging_replaces_same_size_different_content() -> None:
    stage = d2p.DOCXODUS_FONT_STAGE
    stage.mkdir()
    (stage / "Carlito-Regular.ttf").write_bytes(b"stale! font")
    assert d2p.docxodus_font_dir().joinpath("Carlito-Regular.ttf").read_bytes() == b"metric font"


def test_font_staging_removes_stale_faces() -> None:
    stage = d2p.DOCXODUS_FONT_STAGE
    stage.mkdir()
    (stage / "NotoSans-VariableFont.ttf").write_bytes(b"stale")
    assert sorted(p.name for p in d2p.docxodus_font_dir().iterdir()) == ["Carlito-Regular.ttf"]


def test_font_staging_prunes_only_unselected_ttf_files() -> None:
    stage = d2p.DOCXODUS_FONT_STAGE
    stage.mkdir()
    kept = {".Carlito-Regular.ttf.123.456.tmp": b"copy in progress", "README.txt": b"notes",
            ".hidden.ttf": b"hidden face"}
    for name, data in kept.items():
        (stage / name).write_bytes(data)
    (stage / "NotoSans-VariableFont.ttf").write_bytes(b"stale")
    d2p.docxodus_font_dir()
    assert all((stage / name).is_file() for name in kept), "staging must preserve dotfiles and non-font files"
    assert {name: (stage / name).read_bytes() for name in kept} == kept
    assert not (stage / "NotoSans-VariableFont.ttf").exists()
    assert (stage / "Carlito-Regular.ttf").read_bytes() == b"metric font"


def test_score_only_resumes_from_the_tools_checkpoint(tmp_path: Path, monkeypatch) -> None:
    """#89: a share scored on another machine is merged into the checkpoint and not scored again."""
    items = [_fixture(tmp_path, f"doc {i}") for i in range(2)]
    seen: list[object] = []
    monkeypatch.setattr(d2p, "score_folder_pair", lambda *a, **k: seen.append(k.get("checkpoint")) or {})
    cand = {i.stem: i.oracle for i in items}
    d2p.run_eval(tmp_path / "r.json", tools=("soffice",), work_dir=tmp_path / "w", fixtures=items,
                 check_pins=False, track="corpus/word:all", resume=False, score_only=True, candidates=cand)
    assert seen == [tmp_path / "w" / "soffice" / "scores.checkpoint.jsonl"]
