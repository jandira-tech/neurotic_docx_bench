"""bench.yaml parsing."""

from __future__ import annotations

import pytest

from neurotic_docx_bench.config import BenchConfig, load_config

_YAML = """
source_of_truth: corpus/word_based/pdf_redlines_word
scoring:
  dpi: 200
runs:
  - name: jubarte
    render: soffice
    docx: runs/jubarte/docx
    package: docxodus@6.4.0
    jobs: 8
  - name: prebaked
    render: passthrough
    modified: /abs/path/to/pdfs
    unversioned: true
"""


def test_load_config_parses(tmp_path):
    cfg_path = tmp_path / "bench.yaml"
    cfg_path.write_text(_YAML)
    cfg = load_config(cfg_path)
    assert isinstance(cfg, BenchConfig)
    # relative source_of_truth resolves against the yaml's parent
    assert cfg.source_of_truth == tmp_path / "corpus/word_based/pdf_redlines_word"
    assert cfg.scoring.dpi == 200
    assert [r.name for r in cfg.runs] == ["jubarte", "prebaked"]
    jub = cfg.runs[0]
    assert jub.render == "soffice"
    assert jub.jobs == 8
    assert jub.docx == tmp_path / "runs/jubarte/docx"
    assert jub.package == "docxodus@6.4.0"
    assert jub.unversioned is False
    pre = cfg.runs[1]
    assert pre.render == "passthrough"
    assert pre.modified is not None
    assert pre.modified.is_absolute() and str(pre.modified) == "/abs/path/to/pdfs"
    assert pre.unversioned is True


def test_defaults(tmp_path):
    cfg_path = tmp_path / "bench.yaml"
    cfg_path.write_text(
        "source_of_truth: oracle\nruns:\n  - {name: t, render: passthrough, unversioned: true}\n",
    )
    cfg = load_config(cfg_path)
    assert cfg.scoring.dpi == 144
    assert cfg.runs[0].jobs == 12


@pytest.mark.parametrize(
    "bad",
    [
        "runs: []\n",  # no source_of_truth
        "source_of_truth: o\nruns:\n  - {render: soffice}\n",  # run w/o name
        "source_of_truth: o\nruns:\n  - {name: t}\n",  # run w/o render
        "source_of_truth: o\nruns:\n  - {name: t, render: bogus}\n",  # unknown backend
    ],
)
def test_invalid_config_raises(tmp_path, bad):
    cfg_path = tmp_path / "bench.yaml"
    cfg_path.write_text(bad)
    with pytest.raises(ValueError):
        load_config(cfg_path)


# --- Phase A: version-pin validation -----------------------------------------


def _y(run_body: str) -> str:
    return f"source_of_truth: o\nruns:\n  - {{name: t, render: soffice, {run_body}}}\n"


@pytest.mark.parametrize(
    "body",
    [
        "package: docxodus@6.4.0",               # exact npm pin
        "python_package: superdoc-sdk==1.19.2",  # exact pip pin
        "dist: dist/jubarte",                    # local build dir
        "unversioned: true",                     # sanity-run escape hatch
        "package: '@scope/pkg@1.2.3'",         # scoped npm with exact pin (quoted for YAML)
    ],
)
def test_valid_version_pins(tmp_path, body):
    cfg_path = tmp_path / "bench.yaml"
    cfg_path.write_text(_y(body))
    cfg = load_config(cfg_path)
    assert cfg.runs[0].name == "t"


@pytest.mark.parametrize(
    "body",
    [
        "package: docxodus",          # bare npm name, no version
        "package: docxodus@latest",   # @latest is not a pin
        "python_package: superdoc-sdk",          # bare pip name
        "python_package: superdoc-sdk>=1.0",     # not an exact pin (==)
        "docx: runs/t/docx",          # zero version sources
        "package: 'docxodus @ 6.4.0'",          # spaces around @ (copy-paste from URL)
        "python_package: 'superdoc-sdk==1.0.'",  # PEP 440 forbids trailing dot
        "package: 'docxodus@-1.0.0'",           # negative semver is not a pin
    ],
)
def test_invalid_version_pins(tmp_path, body):
    cfg_path = tmp_path / "bench.yaml"
    cfg_path.write_text(_y(body))
    with pytest.raises(ValueError):
        load_config(cfg_path)


def test_multiple_version_sources_rejected(tmp_path):
    """Two version sources (package + dist) must be rejected as ambiguous."""
    cfg_path = tmp_path / "bench.yaml"
    cfg_path.write_text(
        "source_of_truth: o\n"
        "runs:\n"
        "  - name: t\n"
        "    render: soffice\n"
        "    package: docxodus@6.4.0\n"
        "    dist: dist/jubarte\n",
    )
    with pytest.raises(ValueError):
        load_config(cfg_path)


def test_run_config_parses_vendor_and_benchmarks(tmp_path):
    """Vendor and benchmarks are parsed from bench.yaml (schema v4)."""
    cfg_path = tmp_path / "bench.yaml"
    cfg_path.write_text(
        "source_of_truth: oracle\n"
        "runs:\n"
        "  - name: docxodus\n"
        "    vendor: docxodus\n"
        "    package: docxodus@6.4.0\n"
        "    render: soffice\n"
        "    benchmarks: [script_redlines, accepted_changes, roundtrip]\n",
    )
    cfg = load_config(cfg_path)
    run = cfg.runs[0]
    assert run.vendor == "docxodus"
    assert run.benchmarks == ["script_redlines", "accepted_changes", "roundtrip"]


def test_vendor_defaults_to_name_when_absent(tmp_path):
    """If vendor is not specified, it defaults to the run name."""
    cfg_path = tmp_path / "bench.yaml"
    cfg_path.write_text(
        "source_of_truth: oracle\n"
        "runs:\n"
        "  - {name: my-tool, render: soffice, unversioned: true}\n",
    )
    cfg = load_config(cfg_path)
    assert cfg.runs[0].vendor == "my-tool"


def test_unknown_benchmark_rejected(tmp_path):
    """An unknown benchmark name is rejected with a clear error."""
    cfg_path = tmp_path / "bench.yaml"
    cfg_path.write_text(
        "source_of_truth: oracle\n"
        "runs:\n"
        "  - {name: x, render: soffice, unversioned: true, benchmarks: [bogus]}\n",
    )
    with pytest.raises(ValueError, match="unknown benchmark"):
        load_config(cfg_path)


def test_viewer_block_parsed(tmp_path):
    """The dependency-viewer block is parsed into RunConfig.viewer."""
    cfg_path = tmp_path / "bench.yaml"
    cfg_path.write_text(
        "source_of_truth: oracle\n"
        "runs:\n"
        "  - name: docxodus-playwright\n"
        "    render: playwright\n"
        "    unversioned: true\n"
        "    viewer:\n"
        "      root: harness/react-docxodus-viewer\n"
        "      port: 5174\n",
    )
    cfg = load_config(cfg_path)
    assert cfg.runs[0].viewer == {"root": "harness/react-docxodus-viewer", "port": 5174}


def test_committed_bench_yaml_has_expected_vendor_coverage():
    """The committed bench.yaml declares the expected benchmark coverage per vendor.

    Guards against accidentally dropping a benchmark from a vendor's list. The matrix
    (per the standardized-results plan):
      - docxodus, superdoc: all six benchmarks
      - jubarte: accepted_changes, script_redlines, roundtrip
    """
    from pathlib import Path
    repo_cfg = Path("bench.yaml")
    if not repo_cfg.is_file():
        return  # running outside the repo root — skip
    cfg = load_config(repo_cfg)
    by_vendor: dict[str, set[str]] = {}
    for run in cfg.runs:
        v = run.vendor or run.name
        by_vendor.setdefault(v, set()).update(run.benchmarks)
    six = {
        "accepted_changes", "script_redlines", "roundtrip",
        "visual_rendering", "visual_redlines", "visual_accepted_changes",
    }
    assert by_vendor.get("docxodus", set()) >= six
    assert by_vendor.get("superdoc", set()) >= six
    assert by_vendor.get("jubarte", set()) >= {"accepted_changes", "script_redlines", "roundtrip"}


# --- environment_config_for_run -------------------------------------------------


def test_environment_config_for_run_filters_to_single_run(tmp_path):
    """Only the named run is kept; shared env (source_of_truth, scoring, etc.) is preserved."""
    from neurotic_docx_bench.config import environment_config_for_run

    cfg_path = tmp_path / "bench.yaml"
    cfg_path.write_text(_YAML)
    cfg = load_config(cfg_path)
    assert len(cfg.runs) == 2  # sanity: two runs in the fixture

    filtered = environment_config_for_run(cfg, "jubarte")
    assert filtered.source_of_truth == cfg.source_of_truth
    assert filtered.scoring == cfg.scoring
    assert filtered.accepted_ground_truth == cfg.accepted_ground_truth
    assert filtered.generate_scripts == cfg.generate_scripts
    assert len(filtered.runs) == 1
    assert filtered.runs[0].name == "jubarte"
    assert filtered.runs[0].render == "soffice"


def test_environment_config_for_run_unknown_raises(tmp_path):
    """A run name that doesn't exist raises ValueError."""
    from neurotic_docx_bench.config import environment_config_for_run

    cfg_path = tmp_path / "bench.yaml"
    cfg_path.write_text(_YAML)
    cfg = load_config(cfg_path)

    with pytest.raises(ValueError, match="No run named"):
        environment_config_for_run(cfg, "nonexistent")


def test_extra_oracle_dirs_parsed(tmp_path):
    (tmp_path / "oracle").mkdir()
    (tmp_path / "rand_oracle").mkdir()
    cfg_path = tmp_path / "bench.yaml"
    cfg_path.write_text(
        "source_of_truth: oracle\n"
        "extra_oracle_dirs:\n"
        "  - rand_oracle\n"
        "runs:\n"
        "  - name: t\n"
        "    render: passthrough\n"
        "    modified: /x\n"
        "    unversioned: true\n",
    )
    cfg = load_config(cfg_path)
    assert cfg.extra_oracle_dirs == (tmp_path / "rand_oracle",)
    # and it survives the per-run environment_config narrowing
    from neurotic_docx_bench.config import environment_config_for_run

    assert environment_config_for_run(cfg, "t").extra_oracle_dirs == cfg.extra_oracle_dirs


def test_extra_oracle_dirs_default_empty(tmp_path):
    (tmp_path / "oracle").mkdir()
    cfg_path = tmp_path / "bench.yaml"
    cfg_path.write_text(
        "source_of_truth: oracle\n"
        "runs:\n"
        "  - name: t\n"
        "    render: passthrough\n"
        "    modified: /x\n"
        "    unversioned: true\n",
    )
    assert load_config(cfg_path).extra_oracle_dirs == ()


def test_extra_oracle_dirs_missing_dir_raises(tmp_path):
    (tmp_path / "oracle").mkdir()
    cfg_path = tmp_path / "bench.yaml"
    cfg_path.write_text(
        "source_of_truth: oracle\n"
        "extra_oracle_dirs:\n"
        "  - not_there\n"
        "runs:\n"
        "  - name: t\n"
        "    render: passthrough\n"
        "    modified: /x\n"
        "    unversioned: true\n",
    )
    with pytest.raises(ValueError, match="extra_oracle_dirs"):
        load_config(cfg_path)


def test_extra_oracle_dirs_non_list_raises(tmp_path):
    (tmp_path / "oracle").mkdir()
    cfg_path = tmp_path / "bench.yaml"
    cfg_path.write_text(
        "source_of_truth: oracle\n"
        "extra_oracle_dirs: not_a_list\n"
        "runs:\n"
        "  - name: t\n"
        "    render: passthrough\n"
        "    modified: /x\n"
        "    unversioned: true\n",
    )
    with pytest.raises(ValueError, match="must be a list"):
        load_config(cfg_path)


_ROOTED = """
renderer: {renderer}
oracle_roots:
  word: corpus/word
  soffice: corpus/libreoffice
source_of_truth: tracking_without_comments/pdf
extra_oracle_dirs:
  - with_comments_tracking/pdf
runs:
  - name: j
    render: {render}
    package: docxodus@6.4.0
"""


def _rooted(tmp_path, renderer="auto", render="auto"):
    for root in ("corpus/word", "corpus/libreoffice"):
        for state in ("tracking_without_comments", "with_comments_tracking"):
            (tmp_path / root / state / "pdf").mkdir(parents=True, exist_ok=True)
    p = tmp_path / "bench.yaml"
    p.write_text(_ROOTED.format(renderer=renderer, render=render))
    return p


@pytest.mark.parametrize(("has_word", "backend"), [(True, "word"), (False, "soffice")])
def test_auto_renders_with_word_where_the_machine_has_it(tmp_path, monkeypatch, has_word, backend):
    from neurotic_docx_bench.render import word

    monkeypatch.delenv("BENCH_RENDERER")
    monkeypatch.setattr(word, "word_available", lambda: has_word)
    cfg = load_config(_rooted(tmp_path))
    assert cfg.renderer == backend
    assert cfg.runs[0].render == backend


@pytest.mark.parametrize(("has_word", "root"), [(True, "corpus/word"), (False, "corpus/libreoffice")])
def test_oracle_dirs_follow_the_renderer(tmp_path, monkeypatch, has_word, root):
    # a Word render is scored against Word PDFs, a LibreOffice render against LibreOffice PDFs
    from neurotic_docx_bench.render import word

    monkeypatch.delenv("BENCH_RENDERER")
    monkeypatch.setattr(word, "word_available", lambda: has_word)
    cfg = load_config(_rooted(tmp_path))
    assert cfg.source_of_truth == tmp_path / root / "tracking_without_comments/pdf"
    assert cfg.extra_oracle_dirs == (tmp_path / root / "with_comments_tracking/pdf",)
    # a viewer is measured against what Word prints, whichever renderer the docx runs use
    assert cfg.visual_oracles["visual_redlines"] == tmp_path / "corpus/word/tracking_without_comments/pdf"


def test_an_explicit_renderer_overrides_the_machine(tmp_path, monkeypatch):
    from neurotic_docx_bench.render import word

    monkeypatch.delenv("BENCH_RENDERER")
    monkeypatch.setattr(word, "word_available", lambda: True)
    cfg = load_config(_rooted(tmp_path, renderer="soffice", render="soffice"))
    assert cfg.renderer == "soffice"
    assert cfg.source_of_truth == tmp_path / "corpus/libreoffice/tracking_without_comments/pdf"


def test_a_docx_run_on_another_renderer_than_its_oracle_is_refused(tmp_path, monkeypatch):
    from neurotic_docx_bench.render import word

    monkeypatch.delenv("BENCH_RENDERER")
    monkeypatch.setattr(word, "word_available", lambda: True)
    with pytest.raises(ValueError, match="renders with soffice but the oracle is word"):
        load_config(_rooted(tmp_path, renderer="auto", render="soffice"))


def test_oracle_roots_must_cover_the_renderer(tmp_path, monkeypatch):
    from neurotic_docx_bench.render import word

    monkeypatch.delenv("BENCH_RENDERER")
    monkeypatch.setattr(word, "word_available", lambda: False)
    p = _rooted(tmp_path)
    p.write_text(p.read_text().replace("  soffice: corpus/libreoffice\n", ""))
    with pytest.raises(ValueError, match="oracle_roots has no 'soffice'"):
        load_config(p)


def test_config_hash_tells_a_word_run_from_a_soffice_run(tmp_path):
    # render: auto makes one yaml mean two renderers; skip-already-ran must not confuse them
    from neurotic_docx_bench import provenance

    p = tmp_path / "bench.yaml"
    p.write_text("source_of_truth: x\n")
    legacy = provenance.config_hash(p)
    assert provenance.config_hash(p, renderer="soffice") == legacy  # soffice rows keep their hash
    assert provenance.config_hash(p, renderer="word") != legacy
    assert len(provenance.config_hash(p, renderer="word")) == 12
