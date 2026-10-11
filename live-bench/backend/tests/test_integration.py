# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""Integration checks: real local files, parsers and scorer, no external requests."""

import hashlib
import json
from dataclasses import replace

import httpx
import pymupdf
import pytest
from PIL import Image

from livebench.config import Config
from livebench.corpus import download
from livebench.models import MAX_FILE_BYTES, ToolFailure
from livebench.pdf_probe import inspect_pdf
from livebench.publisher import Publisher
from livebench.scorer import score_pair
from livebench.seed import build_seed
from livebench.service import Worker
from livebench.state import State
from livebench.tools import RealTools

pytestmark = pytest.mark.integration


def pdf(path, pages=1, width=595):
    with pymupdf.open() as document:
        for _ in range(pages):
            page = document.new_page(width=width, height=842)
            page.insert_text((50, 50), "Actual benchmark evidence.")
        document.save(path)


def test_fixed_complex_seed_is_reproducible_and_link_download_has_actual_docx_bytes(tmp_path):
    first, second = tmp_path / "first.docx", tmp_path / "second.docx"
    build_seed(first)
    build_seed(second)
    assert first.read_bytes() == second.read_bytes()
    content = first.read_bytes()
    # A public literal IP avoids any real DNS dependency in this integration transport.
    row = {"id": "corpus-row", "url": "https://8.8.8.8/actual.docx", "review_id": "review", "topic": "law"}
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=content))
    ) as client:
        document = download(row, tmp_path / "downloaded.docx", client, MAX_FILE_BYTES)
    assert document.path.read_bytes() == content
    assert document.sha256 == hashlib.sha256(content).hexdigest()
    assert document.security["status"] == "safe"
    assert document.metadata["download_bytes"] == len(content)
    assert document.metadata["corpus"]["topic"] == "law"


def test_word_rejects_oversize_response_and_local_input_before_publication(tmp_path):
    source = tmp_path / "source.docx"
    build_seed(source)
    output = tmp_path / "word.pdf"
    config = Config(tmp_path, "https://word.example", "word-token", "https://ingest.example", "ingest-token")
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, headers={"content-length": str(MAX_FILE_BYTES + 1)}, content=b"%PDF-small")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        tools = RealTools(config, client)
        with pytest.raises(ToolFailure, match="20 MB") as failed:
            tools.perform("word", "convert", [source], output)
        assert failed.value.status == "broken" and not output.exists()
        with source.open("wb") as fh:
            fh.truncate(MAX_FILE_BYTES + 1)
        with pytest.raises(ToolFailure, match="input exceeds"):
            tools.perform("word", "convert", [source], output)
    assert len(requests) == 1 and not output.with_suffix(".pdf.part").exists()


def test_real_pdf_probe_and_scorer_preserve_full_metrics_and_inspection_png(tmp_path):
    reference, candidate = tmp_path / "reference.pdf", tmp_path / "candidate.pdf"
    pdf(reference)
    pdf(candidate, pages=2)
    assert inspect_pdf(str(reference), 72)["pages"] == 1
    metrics = score_pair(str(reference), str(candidate), 72, str(tmp_path / "score"))
    raw = json.loads((tmp_path / "score.json").read_text())
    assert metrics["page_count_mismatch"] is True
    assert metrics["overall"] < 100
    assert raw["pages"] and raw["raster_ns"] > 0 and raw["page_count_candidate"] == 2
    with Image.open(tmp_path / "score.png") as image:
        assert image.size == (1200, 740)
    pdf(reference, pages=2)
    identity = score_pair(str(reference), str(candidate), 72, str(tmp_path / "identity"))
    assert identity["overall"] == pytest.approx(100)
    pdf(tmp_path / "oversized.pdf", width=100_000)
    with pytest.raises(ValueError, match="raster safety"):
        inspect_pdf(str(tmp_path / "oversized.pdf"))


def test_pdf_encryption_page_count_and_total_raster_cost_are_bounded(tmp_path):
    encrypted = tmp_path / "encrypted.pdf"
    with pymupdf.open() as document:
        document.new_page()
        document.save(encrypted, encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="user")
    with pytest.raises(ValueError, match="encrypted"):
        inspect_pdf(str(encrypted))
    pdf(tmp_path / "pages.pdf", pages=501)
    with pytest.raises(ValueError, match="500 pages"):
        inspect_pdf(str(tmp_path / "pages.pdf"))
    pdf(tmp_path / "raster.pdf", pages=210)
    with pytest.raises(ValueError, match="document exceeds raster"):
        inspect_pdf(str(tmp_path / "raster.pdf"))


def test_word_malformed_pdf_is_rejected_instead_of_becoming_a_reference(tmp_path):
    config = Config(
        tmp_path, "https://word.example", "secret-word", "https://ingest.example", "secret-ingest"
    )
    source = tmp_path / "source.docx"
    build_seed(source)
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b"invalid PDF"))
    ) as client:
        with pytest.raises(ToolFailure, match="not a PDF"):
            RealTools(config, client).perform("word", "convert", [source], tmp_path / "bad.pdf")
    assert not (tmp_path / "bad.pdf").exists()


def test_word_compare_contract_sends_original_and_revised_and_redacts_error_credentials(tmp_path):
    config = Config(
        tmp_path, "https://word.example", "secret-word", "https://ingest.example", "secret-ingest"
    )
    original, revised = tmp_path / "original.docx", tmp_path / "revised.docx"
    build_seed(original)
    build_seed(revised)
    document = original.read_bytes()
    failed = False

    def handler(request):
        assert request.url.path == "/v1/compare"
        assert request.headers["authorization"] == "Bearer secret-word"
        assert request.headers["content-type"].startswith("multipart/form-data; boundary=")
        body = request.read()
        assert b'name="original"; filename="original.docx"' in body
        assert b'name="revised"; filename="revised.docx"' in body
        assert b'name="document"' not in body
        assert body.count(document) == 2
        if failed:
            return httpx.Response(400, json={"code": "unsafe_package", "error": "secret-word secret-ingest"})
        return httpx.Response(200, content=document)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        tools = RealTools(config, client)
        output = tools.perform("word", "compare", [original, revised], tmp_path / "redline.docx")
        assert output.read_bytes() == document
        failed = True
        with pytest.raises(ToolFailure) as caught:
            tools.perform("word", "compare", [original, revised], output)
        assert caught.value.status == "broken" and "unsafe_package" in str(caught.value)
        assert "secret-word" not in str(caught.value) and "secret-ingest" not in str(caught.value)
        assert not output.exists()


def test_finalization_cleanup_is_repeatable_and_keeps_predecessor(tmp_path):
    worker = object.__new__(Worker)
    worker.config = replace(Config(tmp_path, "https://word", "a", "https://ingest", "b"), batch_size=2)
    worker.state = State(":memory:", id_factory=lambda: "id")
    worker.state.set("completed", 2)
    worker.state.set("finalized", 2)
    for sequence in (1, 2, 3):
        work = tmp_path / "work" / str(sequence)
        work.mkdir(parents=True)
        (work / "output.pdf").write_bytes(b"preserved remotely")
        fixture = tmp_path / "fixtures" / f"{sequence}.docx"
        fixture.parent.mkdir(exist_ok=True)
        fixture.write_bytes(b"fixture")
    worker.cleanup_finalized()
    worker.cleanup_finalized()
    assert not (tmp_path / "fixtures/1.docx").exists()
    assert (tmp_path / "fixtures/2.docx").exists()
    assert (tmp_path / "fixtures/3.docx").exists()
    assert not (tmp_path / "work/2").exists()
    assert (tmp_path / "work/3/output.pdf").exists()
    worker.state.close()


@pytest.mark.parametrize("split_archive", [False, True])
def test_complete_hundred_manifest_retries_without_losing_a_review(tmp_path, split_archive):
    worker = object.__new__(Worker)
    worker.config = Config(tmp_path, "https://word", "a", "https://ingest", "b")
    identifiers = iter(f"review-{i}" for i in range(100))
    worker.state = State(":memory:", id_factory=lambda: next(identifiers))
    worker.run_id, worker.run = "run", {"id": "run", "config": {"batch_size": 100}}
    worker.state.enqueue([{"id": str(i)} for i in range(100)], {"cycle": 0, "offset": 100})
    for sequence in range(1, 101):
        _, row = worker.state.queued_download()
        worker.state.downloaded(sequence, row)
        worker.state.finish(
            sequence,
            {
                "id": row["review_id"],
                "sequence": sequence,
                "completed_at": "2026-10-08T00:00:00Z",
                "artifacts": [],
                "metadata": {"notes": "x" * 205_000} if split_archive else {},
            },
            row,
        )
    manifests, result_ids, batches = [], [], []

    def handler(request):
        if request.method == "PUT":
            assert len(request.content) <= MAX_FILE_BYTES
            manifests.append((request.url.path, request.content))
        elif request.url.path.endswith("/result"):
            result_ids.append(json.loads(request.content)["id"])
        elif request.url.path.endswith("/batch"):
            batches.append(json.loads(request.content))
            if len(batches) == 1:
                return httpx.Response(503)
        return httpx.Response(200)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        worker.publisher = Publisher("https://ingest", "token", client)
        assert worker.finalize(100) is False
        assert worker.state.get("finalized", 0) == 0
        assert len(worker.state.batch_results(1, 100)) == 100
        assert worker.finalize(100) is True
        assert worker.state.get("finalized") == 100
        assert worker.state.pending() == []
        assert len(set(result_ids)) == 100 and len(result_ids) == 100
        uploads = 11 if split_archive else 1
        assert manifests[:uploads] == manifests[uploads:]
        manifest = json.loads(manifests[uploads - 1][1])
        if split_archive:
            recovered = []
            for part in manifest["result_parts"]:
                data = next(data for path, data in manifests[:uploads] if path.endswith(part["key"]))
                assert hashlib.sha256(data).hexdigest() == part["sha256"]
                recovered.extend(json.loads(data)["results"])
        else:
            recovered = manifest["results"]
        assert len(recovered) == 100 and len({row["id"] for row in recovered}) == 100
        assert batches[-1]["first_sequence"] == 1 and batches[-1]["last_sequence"] == 100
        assert worker.finalize(100) is True
        assert len(manifests) == 2 * uploads
        assert list((tmp_path / "manifests").glob("*.json")) == []
    worker.state.close()
