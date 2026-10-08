# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
import json
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import httpx
import pytest

from livebench.config import Config
from livebench.corpus import draw_indices, public_url
from livebench.corpus import fetch_document as fetch
from livebench.models import MAX_FILE_BYTES, ToolFailure
from livebench.publisher import Publisher, archive_files
from livebench.safety import UnsafeDocument, inspect_docx
from livebench.tools import verify_output


def fetch_document(*args, **kwargs):
    kwargs.setdefault("clock", lambda: 0)
    return fetch(*args, **kwargs)


def package(xml=b'<w:document xmlns:w="urn:word"><w:body/></w:document>', extra=None):
    data = BytesIO()
    with ZipFile(data, "w", ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", '<Types xmlns="urn:content"/>')
        docx.writestr("word/document.xml", xml)
        for name, content in extra or []:
            docx.writestr(name, content)
    return data.getvalue()


def test_safe_xml_metadata():
    result = inspect_docx(package())
    assert result["status"] == "safe" and result["xml_parts"] == 2


def test_nonstandard_xml_part_cannot_bypass_preflight():
    bomb = b'<!DOCTYPE a [<!ENTITY x "bomb">]><a>&x;</a>'
    with pytest.raises(UnsafeDocument, match="DTD"):
        inspect_docx(package(extra=[("word/styles.bin", bomb)]))
    data = BytesIO()
    with ZipFile(data, "w", ZIP_DEFLATED) as docx:
        docx.writestr(
            "[Content_Types].xml",
            '<Types xmlns="urn:content">'
            '<Override PartName="/word/styles.bin" ContentType="application/styles+xml"/>'
            "</Types>",
        )
        docx.writestr("word/document.xml", b"<document/>")
        docx.writestr("word/styles.bin", bomb)
    with pytest.raises(UnsafeDocument, match="DTD"):
        inspect_docx(data.getvalue())


def test_total_download_deadline_is_bounded_without_wall_clock():
    times = iter([0, 121])
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b"x"))) as client:
        with pytest.raises(ValueError, match="total download"):
            fetch_document(
                client,
                "https://example.com/a",
                100,
                lambda _: None,
                clock=lambda: next(times),
                total_timeout=120,
            )


@pytest.mark.parametrize(
    "xml",
    [
        b'<!DOCTYPE a [<!ENTITY a "bomb">]><a>&a;</a>',
        '<!DOCTYPE a [<!ENTITY a "bomb">]><a>&a;</a>'.encode("utf-16"),
        b"<a>" * 100 + b"</a>" * 100,
        b"<a " + b" ".join(f'x{i}="1"'.encode() for i in range(257)) + b"/>",
        b"<invalid>",
        b'<!DOCTYPE a SYSTEM "https://example.com/evil.dtd"><a/>',
    ],
)
def test_xml_entity_depth_attribute_and_parse_bombs_rejected(xml):
    with pytest.raises(UnsafeDocument):
        inspect_docx(package(xml))


@pytest.mark.parametrize(
    "blob",
    [
        b"not a zip",
        package(extra=[("../outside.xml", b"<a/>")]),
        package(extra=[("word/huge.bin", b"x" * 2_000_000)]),
    ],
)
def test_bad_archive_and_zip_bomb_rejected(blob):
    with pytest.raises(UnsafeDocument):
        inspect_docx(blob)


def test_duplicate_zip_part_is_rejected():
    with pytest.warns(UserWarning, match="Duplicate name"):
        blob = package(extra=[("word/document.xml", b"<a/>")])
    with pytest.raises(UnsafeDocument, match="duplicate"):
        inspect_docx(blob)


def test_sampler_resumes_without_replacement_and_crosses_cycle():
    a, cursor = draw_indices(20, 12, 42, 0, 0)
    b, cursor = draw_indices(20, 8, 42, **cursor)
    assert len(set(a + b)) == 20 and cursor == {"cycle": 1, "offset": 0}
    c, cursor = draw_indices(20, 21, 42, **cursor)
    assert len(set(c[:20])) == 20 and cursor == {"cycle": 2, "offset": 1}
    with pytest.raises(ValueError):
        draw_indices(0, 1, 42, 0, 0)


@pytest.mark.parametrize(
    "url", ["file:///etc/passwd", "http://user:pass@example.com/a", "https://example.com:8000/a"]
)
def test_unsafe_fixture_url_rejected_without_network(url):
    with pytest.raises(ValueError):
        public_url(url, resolver=lambda *a, **k: [])


def test_public_and_private_dns_addresses():
    public_url("https://example.com/a", resolver=lambda *a, **k: [(0, 0, 0, "", ("8.8.8.8", 443))])
    for address in ("127.0.0.1", "169.254.169.254", "10.0.0.1", "::1"):
        with pytest.raises(ValueError, match="private"):
            public_url("https://example.com/a", resolver=lambda *a, **k: [(0, 0, 0, "", (address, 443))])


def test_upstream_mock_transport_checks_every_redirect_and_metadata():
    validated = []

    def handler(request):
        if request.url.path == "/old":
            return httpx.Response(302, headers={"location": "/new"})
        return httpx.Response(
            200, content=b"fixture", headers={"x-source": "corpus", "set-cookie": "private"}
        )

    metadata = {}
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert (
            fetch_document(client, "https://example.com/old", 100, validated.append, metadata) == b"fixture"
        )
    assert validated == ["https://example.com/old", "https://example.com/new"]
    assert metadata["final_url"].endswith("/new") and "set-cookie" not in metadata["response_headers"]


@pytest.mark.parametrize(
    "status,headers,content,limit",
    [
        (200, {"content-length": "100"}, b"x", 10),
        (200, {}, b"x" * 20, 10),
        (404, {}, b"gone", 100),
    ],
)
def test_download_limits_and_http_errors(status, headers, content, limit):
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(status, headers=headers, content=content))
    ) as client:
        with pytest.raises((ValueError, httpx.HTTPStatusError)):
            fetch_document(client, "https://example.com/a", limit, lambda _: None)


def test_redirect_loop_bounded():
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(302, headers={"location": "/again"}))
    ) as client:
        with pytest.raises(ValueError, match="redirect"):
            fetch_document(client, "https://example.com/a", 100, lambda _: None)


def test_config_validation():
    valid = Config(
        Path("data"), "https://word.example", "wordsecret", "https://ingest.example", "ingestsecret"
    )
    valid.validate()
    from dataclasses import replace

    for change in (
        {"word_token": ""},
        {"batch_size": 101},
        {"prefetch_at": 101},
        {"word_url": "ftp://example.com"},
        {"dpi": 10},
        {"timeout": 0},
        {"max_bytes": MAX_FILE_BYTES + 1},
        {"max_bytes": 0},
    ):
        with pytest.raises(ValueError):
            replace(valid, **change).validate()


def test_authenticated_idempotent_publication_uses_sdk_transport_and_checks_artifact():
    requests = []

    def handler(request):
        requests.append(request)
        assert request.headers["authorization"] == "Bearer secret"
        return httpx.Response(200, json={"ok": True})

    class MemoryFile:
        def stat(self):
            from types import SimpleNamespace

            return SimpleNamespace(st_size=3)

        def read_bytes(self):
            return b"PDF"

    class MemoryWork:
        def __truediv__(self, name):
            assert name == "out.pdf"
            return MemoryFile()

    import hashlib

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        publisher = Publisher("https://example.com", "secret", client)
        artifact = {
            "key": "run/1/out.pdf",
            "content_type": "application/pdf",
            "sha256": hashlib.sha256(b"PDF").hexdigest(),
        }
        publisher.result({"artifacts": [artifact], "id": "review"}, MemoryWork())
        assert [r.method for r in requests] == ["PUT", "POST"]
        assert requests[0].headers["x-content-sha256"] == artifact["sha256"]
        assert json.loads(requests[1].content)["id"] == "review"
        artifact["sha256"] = "0" * 64
        with pytest.raises(ValueError, match="differs"):
            publisher.result({"artifacts": [artifact]}, MemoryWork())


def test_twenty_mb_is_a_hard_limit_for_downloads_packages_outputs_and_uploads():
    assert (
        Config(Path("data"), "https://word.example", "word", "https://ingest.example", "ingest").max_bytes
        == 20_000_000
    )

    class Oversized(bytes):
        def __len__(self):
            return MAX_FILE_BYTES + 1

    class LargeFile:
        def is_file(self):
            return True

        def stat(self):
            from types import SimpleNamespace

            return SimpleNamespace(st_size=MAX_FILE_BYTES + 1)

    with pytest.raises(UnsafeDocument, match="20 MB"):
        inspect_docx(Oversized(b"x"))
    with pytest.raises(ToolFailure, match="20 MB"):
        verify_output(LargeFile())
    requested = []

    def handler(request):
        requested.append(request.method)
        return httpx.Response(200, headers={"content-length": str(MAX_FILE_BYTES + 1)}, content=b"x")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError, match="size limit"):
            fetch_document(client, "https://example.com/large.docx", MAX_FILE_BYTES * 3, lambda _: None)
        with pytest.raises(ValueError, match="20 MB"):
            Publisher("https://example.com", "secret", client).upload(
                "run/1/large.pdf", "application/pdf", Oversized(b"x")
            )
    assert requested == ["GET"]


def test_large_archive_splits_complete_evidence_into_bounded_verified_parts():
    import hashlib

    rows = [{"id": str(i), "metadata": "x" * 500} for i in range(100)]
    key = "run/100/manifest.json"
    files = archive_files({"id": "run"}, rows, key, limit=8000)
    index = json.loads(files[key])
    assert len(index["result_parts"]) == 10
    reconstructed = []
    for part in index["result_parts"]:
        data = files[part["key"]]
        assert len(data) == part["size"] <= 8000
        assert hashlib.sha256(data).hexdigest() == part["sha256"]
        reconstructed.extend(json.loads(data)["results"])
    assert reconstructed == rows and len(files[key]) <= 8000
    assert json.loads(archive_files({"id": "run"}, rows[:1], key)[key])["results"] == rows[:1]
    with pytest.raises(ValueError, match="archive part"):
        archive_files({}, rows, key, limit=50)
    with pytest.raises(ValueError, match="archive index"):
        archive_files({}, [{"id": i} for i in range(100)], key, limit=200)
