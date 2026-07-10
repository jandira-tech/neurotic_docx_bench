"""Phase D — editor/harness server: ``bench serve`` command + auto-start/stop for
playwright runs declaring ``harness.server``.
"""

from __future__ import annotations

import http.server
import socketserver
import threading

import pytest
from typer.testing import CliRunner

from neurotic_docx_bench.cli import _wait_for_url, app

runner = CliRunner()


@pytest.fixture
def dummy_server(tmp_path):
    """Start a tiny HTTP server on an ephemeral port; yield (url, stop_fn)."""
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:
        port = httpd.server_address[1]
        url = f"http://127.0.0.1:{port}/"
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        yield url, httpd.shutdown


def test_wait_for_url_succeeds_on_reachable(dummy_server):
    url, _ = dummy_server
    assert _wait_for_url(url, timeout_s=5, interval_s=0.1) is True


def test_wait_for_url_times_out_on_unreachable(tmp_path):
    """An unreachable port returns False after the timeout."""
    # use a port that's almost certainly not listening
    assert _wait_for_url("http://127.0.0.1:1/", timeout_s=0.5, interval_s=0.1) is False


def test_serve_command_unknown_run(tmp_path):
    """Bench serve rejects a run name not in bench.yaml."""
    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        "source_of_truth: o\n"
        "runs:\n"
        "  - {name: real, render: soffice, unversioned: true}\n",
    )
    r = runner.invoke(app, ["serve", "nope", "-c", str(cfg)])
    assert r.exit_code != 0
    assert "unknown run name" in r.output


def test_serve_command_requires_harness_server(tmp_path):
    """Bench serve fails for a run without harness.server."""
    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        "source_of_truth: o\n"
        "runs:\n"
        "  - {name: noserver, render: playwright, unversioned: true, "
        "harness: {url: 'http://127.0.0.1:5173', file_input: '#f'}}\n",
    )
    r = runner.invoke(app, ["serve", "noserver", "-c", str(cfg)])
    assert r.exit_code != 0
    assert "harness.server" in r.output


def test_serve_command_starts_foreground_server(tmp_path, dummy_server):
    """Bench serve launches the harness.server command (here a sleep that we kill)."""
    url, _ = dummy_server
    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        f"source_of_truth: o\n"
        "runs:\n"
        "  - name: pw\n"
        "    render: playwright\n"
        "    unversioned: true\n"
        "    harness:\n"
        f"      url: '{url}'\n"
        "      file_input: '#f'\n"
        f'      server: "echo started > {tmp_path / "started.txt"}"\n',
    )
    r = runner.invoke(app, ["serve", "pw", "-c", str(cfg)])
    assert r.exit_code == 0
    assert "serving pw" in r.output
    assert (tmp_path / "started.txt").exists()
