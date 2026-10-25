"""`listing()` and the token refresh in scripts/publish/upload_r2.py (issues #63 and #65).

`listing()` used one `for attempt in range(4)` loop as both its retry budget and its pager,
so any prefix over 4,000 objects raised (#63): it now pages until `is_truncated` is false and
retries per page. #65 pins the failure handling: a page without `result_info` is the last
(that is how the live API marks it), a `result_info` without `is_truncated` raises; transport errors, 5xx and non-JSON bodies are retried at the same cursor; 429 waits
`Retry-After` without a token refresh; only 401/403 refresh the token, through one bounded
`wrangler whoami` helper that `upload_api()` shares.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "publish" / "upload_r2.py"
PREFIX = "wordcraft-20261014/compare/oracle/"


class HTTPError(Exception):
    pass


class TransportError(HTTPError):
    pass


class TimeoutException(TransportError):
    pass


class ReadTimeout(TimeoutException):
    pass


class NetworkError(TransportError):
    pass


class ConnectError(NetworkError):
    pass


@pytest.fixture
def upload_r2(monkeypatch: pytest.MonkeyPatch):
    """Load the upload script with a stub `httpx` (not installed in this env)."""
    httpx = types.ModuleType("httpx")
    for cls in (HTTPError, TransportError, TimeoutException, ReadTimeout, NetworkError, ConnectError):
        setattr(httpx, cls.__name__, cls)
    monkeypatch.setitem(sys.modules, "httpx", httpx)
    spec = importlib.util.spec_from_file_location("upload_r2_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeResponse:
    def __init__(self, payload=None, status_code=200, headers=None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeClient:
    """Scripted R2 client: yields the next page, recording every params dict.

    `default` is served for requests past the end of `pages` (used to model a
    prefix that never stops erroring).
    """

    def __init__(self, pages, default=None):
        self._pages = list(pages)
        self._default = default
        self.headers = {}
        self.calls: list[dict] = []

    async def get(self, url, params=None):
        self.calls.append(dict(params) if params is not None else {})
        idx = len(self.calls) - 1
        if idx < len(self._pages):
            page = self._pages[idx]
        elif self._default is not None:
            page = self._default
        else:
            raise AssertionError(f"FakeClient received unexpected request #{idx}: {params}")
        if isinstance(page, Exception):
            raise page
        return page if isinstance(page, FakeResponse) else FakeResponse(page)


@pytest.fixture
def patched(upload_r2, monkeypatch: pytest.MonkeyPatch):
    """Replace the shell-out, the token reader and asyncio.sleep, recording calls."""
    rec = {"subprocess": [], "tokens": [], "sleeps": [], "run_kwargs": [], "threads": []}

    def fake_run(*args, **kwargs):
        rec["subprocess"].append(args[0] if args else None)
        rec["run_kwargs"].append(kwargs)
        return subprocess.CompletedProcess(args[0], 0)

    counter = {"n": 0}

    def fake_token():
        counter["n"] += 1
        t = f"tok-{counter['n']}"
        rec["tokens"].append(t)
        return t

    async def fake_sleep(delay):  # ruff: ignore[unused-async] - stands in for asyncio.sleep, so it must be awaitable
        rec["sleeps"].append(delay)

    async def fake_to_thread(func, *args, **kwargs):  # ruff: ignore[unused-async] - same awaitable interface
        rec["threads"].append(func)
        return func(*args, **kwargs)

    monkeypatch.setattr(upload_r2.subprocess, "run", fake_run)
    monkeypatch.setattr(upload_r2, "token", fake_token)
    monkeypatch.setattr(upload_r2.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(upload_r2.asyncio, "to_thread", fake_to_thread)
    return rec


def batch(start: int, count: int = 1000) -> list[dict]:
    return [{"key": f"p/{i:05d}", "size": i} for i in range(start, start + count)]


def expected(*batches: list[dict]) -> dict:
    return {o["key"]: o["size"] for b in batches for o in b}


def good(items: list[dict], cursor, truncated: bool) -> dict:
    return {"success": True, "result": items, "result_info": {"cursor": cursor, "is_truncated": truncated}}


NULL_PAGE = FakeResponse(
    {"success": False, "result": None, "errors": [{"code": 10000, "message": "token expired"}]},
    status_code=401,
)


def test_listing_pages_past_four(upload_r2, patched):
    """5 full pages (5000 keys) must paginate through every cursor."""
    batches = [batch(j * 1000) for j in range(5)]
    pages = [
        good(batches[j], f"c{j + 1}" if j < 4 else None, j < 4)
        for j in range(5)
    ]
    client = FakeClient(pages)

    result = asyncio.run(upload_r2.listing(client, PREFIX))

    assert result == expected(*batches)
    assert len(client.calls) == 5
    # 2nd..5th requests carry the previous page's cursor.
    assert [c.get("cursor") for c in client.calls] == [None, "c1", "c2", "c3", "c4"]
    assert all(c["prefix"] == PREFIX and c["per_page"] == 1000 for c in client.calls)
    assert patched["subprocess"] == []
    assert patched["tokens"] == []


def test_listing_null_page_midway_refreshes_and_continues(upload_r2, patched):
    """A null page refreshes the token once and re-requests the same cursor."""
    batches = [batch(j * 1000) for j in range(5)]
    pages = [
        good(batches[0], "c1", True),
        good(batches[1], "c2", True),
        NULL_PAGE,
        good(batches[2], "c3", True),
        good(batches[3], "c4", True),
        good(batches[4], None, False),
    ]
    client = FakeClient(pages)

    result = asyncio.run(upload_r2.listing(client, PREFIX))

    assert result == expected(*batches)
    assert patched["subprocess"] == [["bunx", "wrangler", "whoami"]]
    assert patched["tokens"] == ["tok-1"]
    assert client.headers["Authorization"] == "Bearer tok-1"
    # request #3 (the null) and #4 carried the same cursor, so no page was skipped.
    assert client.calls[2]["cursor"] == "c2"
    assert client.calls[3]["cursor"] == "c2"


def test_listing_retry_budget_is_per_page(upload_r2, patched):
    """More than 4 total nulls, one before each page: still completes (reset per page)."""
    batches = [batch(j * 1000) for j in range(6)]
    pages = []
    for j in range(6):
        if j:
            pages.append(NULL_PAGE)
        pages.append(good(batches[j], f"c{j + 1}" if j < 5 else None, j < 5))
    client = FakeClient(pages)

    result = asyncio.run(upload_r2.listing(client, PREFIX))

    assert result == expected(*batches)
    assert len(patched["subprocess"]) == 5
    assert patched["tokens"] == [f"tok-{i}" for i in range(1, 6)]


def test_listing_gives_up_on_persistent_null(upload_r2, patched):
    """A page that never succeeds gives up with a bounded refresh count."""
    client = FakeClient([good(batch(0), "c1", True)], default=NULL_PAGE)

    with pytest.raises(RuntimeError) as excinfo:
        asyncio.run(upload_r2.listing(client, PREFIX))

    assert PREFIX in str(excinfo.value)
    assert len(patched["subprocess"]) <= 10


def test_listing_single_page(upload_r2, patched):
    """A single untruncated page returns its objects after one request."""
    items = [{"key": "p/00000", "size": 0}, {"key": "p/00001", "size": 1}]
    client = FakeClient([good(items, None, False)])

    result = asyncio.run(upload_r2.listing(client, PREFIX))

    assert result == expected(items)
    assert len(client.calls) == 1
    assert client.calls[0]["prefix"] == PREFIX
    assert client.calls[0]["per_page"] == 1000
    assert "cursor" not in client.calls[0]
    assert patched["subprocess"] == []


class CappedClient(FakeClient):
    """A FakeClient that fails the test instead of hanging when listing() loops."""

    async def get(self, url, params=None):
        if len(self.calls) >= 20:
            raise AssertionError("listing() looped: 20 requests for a malformed listing")
        return await super().get(url, params)


@pytest.mark.parametrize(
    "pages",
    [
        pytest.param([good(batch(0), None, True)], id="truncated-without-cursor"),
        pytest.param([good(batch(0), "", True)], id="truncated-with-empty-cursor"),
        pytest.param([good(batch(0), "c1", True), good(batch(1000), "c1", True)], id="repeated-cursor"),
        pytest.param(
            [good(batch(0), "c1", True), good(batch(1000), "c2", True), good(batch(2000), "c1", True)],
            id="cursor-cycle",
        ),
    ],
)
def test_listing_malformed_pagination_raises(upload_r2, patched, pages):
    """A truncated page must carry a new cursor; anything else fails instead of looping."""
    client = CappedClient(pages, default=pages[-1])

    with pytest.raises(RuntimeError) as excinfo:
        asyncio.run(upload_r2.listing(client, PREFIX))

    assert PREFIX in str(excinfo.value)
    assert len(client.calls) <= 4


def test_listing_recovers_after_three_consecutive_nulls(upload_r2, patched):
    """Three failures in a row on one page are within the 4-attempt budget."""
    first, second = batch(0), batch(1000)
    client = FakeClient([good(first, "c1", True), NULL_PAGE, NULL_PAGE, NULL_PAGE, good(second, None, False)])

    result = asyncio.run(upload_r2.listing(client, PREFIX))

    assert result == expected(first, second)
    assert len(patched["subprocess"]) == 3
    assert [c.get("cursor") for c in client.calls[1:]] == ["c1"] * 4
    assert patched["sleeps"] == [1, 2, 4]


def test_listing_fails_on_fourth_consecutive_null(upload_r2, patched):
    """The fourth failure in a row on one page gives up, without a pointless last sleep."""
    client = FakeClient([good(batch(0), "c1", True), NULL_PAGE, NULL_PAGE, NULL_PAGE, NULL_PAGE])

    with pytest.raises(RuntimeError) as excinfo:
        asyncio.run(upload_r2.listing(client, PREFIX))

    assert PREFIX in str(excinfo.value)
    assert len(client.calls) == 5
    assert len(patched["subprocess"]) == 4
    assert patched["sleeps"] == [1, 2, 4]


def outcome(coro):
    """Capture errors so RED reports the missing behaviour as an assertion."""
    try:
        return asyncio.run(coro), None
    except Exception as error:
        return None, error


@pytest.mark.parametrize("last", [
    {"success": True, "result": batch(1000, 1000), "result_info": None},
    {"success": True, "result": batch(1000, 1000)},
])
def test_listing_page_without_result_info_is_the_last(upload_r2, patched, last):
    """The live API leaves result_info out of the last page, even a full one (checked 2026-10-25:
    word-driver-ab/, 312 objects, per_page 104 gave two truncated pages and a third of 104 with
    no result_info), so its absence ends the listing."""
    client = FakeClient([good(batch(0), "c1", True), last])

    assert asyncio.run(upload_r2.listing(client, PREFIX)) == expected(batch(0), batch(1000, 1000))
    assert len(client.calls) == 2


def test_listing_missing_is_truncated_raises(upload_r2, patched):
    """A result_info without is_truncated says neither "more" nor "done"."""
    client = FakeClient([{"success": True, "result": batch(0, 1), "result_info": {"cursor": "c1"}}])

    with pytest.raises(RuntimeError, match=PREFIX):
        asyncio.run(upload_r2.listing(client, PREFIX))


def assert_retry_at_same_cursor(upload_r2, patched, failure):
    first, second = batch(0, 1), batch(1, 1)
    client = FakeClient([good(first, "c1", True), failure, good(second, None, False)])

    result, error = outcome(upload_r2.listing(client, PREFIX))

    assert error is None, f"listing should retry this page: {error!r}"
    assert result == expected(first, second)
    assert [c.get("cursor") for c in client.calls] == [None, "c1", "c1"]
    assert patched["sleeps"] == [1]
    assert patched["subprocess"] == []
    assert patched["tokens"] == []


def test_listing_read_timeout_retries_at_same_cursor(upload_r2, patched):
    assert_retry_at_same_cursor(upload_r2, patched, ReadTimeout("read timed out"))


def test_listing_connect_error_retries_at_same_cursor(upload_r2, patched):
    assert_retry_at_same_cursor(upload_r2, patched, ConnectError("connection failed"))


def test_listing_html_502_retries(upload_r2, patched):
    response = FakeResponse(json.JSONDecodeError("not JSON", "<html>502</html>", 0), status_code=502)
    assert_retry_at_same_cursor(upload_r2, patched, response)


def test_listing_non_json_200_retries(upload_r2, patched):
    assert_retry_at_same_cursor(upload_r2, patched, FakeResponse(ValueError("invalid JSON")))


def test_listing_503_empty_result_is_retried(upload_r2, patched):
    response = FakeResponse({"success": False, "result": []}, status_code=503)
    assert_retry_at_same_cursor(upload_r2, patched, response)


@pytest.mark.parametrize("status", [500, 503])
def test_listing_server_error_with_success_payload_is_retried(upload_r2, patched, status):
    assert_retry_at_same_cursor(upload_r2, patched, FakeResponse(good([], None, False), status_code=status))


def test_listing_429_retry_after_sleeps_without_refresh(upload_r2, patched):
    items = batch(0, 1)
    client = FakeClient([
        FakeResponse({"success": False, "result": None}, status_code=429, headers={"Retry-After": "7"}),
        good(items, None, False),
    ])

    result = asyncio.run(upload_r2.listing(client, PREFIX))

    assert result == expected(items)
    assert len(client.calls) == 2
    assert patched["sleeps"] == [7]
    assert patched["subprocess"] == []
    assert patched["tokens"] == []


@pytest.mark.parametrize("headers", [{}, {"Retry-After": "invalid"}])
def test_listing_429_without_parseable_retry_after_uses_backoff(upload_r2, patched, headers):
    client = FakeClient([FakeResponse(NULL_PAGE.json(), status_code=429, headers=headers)] * 3
                        + [good([], None, False)])

    assert asyncio.run(upload_r2.listing(client, PREFIX)) == {}
    assert patched["sleeps"] == [1, 2, 4]
    assert len(client.calls) == 4
    assert patched["subprocess"] == []
    assert patched["tokens"] == []


def test_listing_429_exhausts_budget_without_last_sleep(upload_r2, patched):
    client = FakeClient([], default=FakeResponse(NULL_PAGE.json(), status_code=429, headers={"Retry-After": "7"}))

    with pytest.raises(RuntimeError, match=PREFIX):
        asyncio.run(upload_r2.listing(client, PREFIX))

    assert len(client.calls) == 4
    assert patched["sleeps"] == [7, 7, 7]
    assert patched["subprocess"] == []


@pytest.mark.parametrize("status", [400, 404])
def test_listing_other_4xx_retries_without_refresh_then_reports_status(upload_r2, patched, status):
    client = FakeClient([], default=FakeResponse({"success": False, "result": None}, status_code=status))

    with pytest.raises(RuntimeError) as excinfo:
        asyncio.run(upload_r2.listing(client, PREFIX))

    assert PREFIX in str(excinfo.value)
    assert str(status) in str(excinfo.value)
    assert len(client.calls) == 4
    assert patched["sleeps"] == [1, 2, 4]
    assert patched["subprocess"] == []
    assert patched["tokens"] == []


@pytest.mark.parametrize("payload", [
    {"success": False, "result": [], "errors": ["listing denied"]},
    {"success": True, "result": None, "errors": ["listing denied"]},
])
def test_listing_200_failed_payload_retries_without_refresh(upload_r2, patched, payload):
    client = FakeClient([], default=payload)

    _, error = outcome(upload_r2.listing(client, PREFIX))

    assert isinstance(error, RuntimeError), f"failed payload must exhaust retries: {error!r}"
    assert PREFIX in str(error)
    assert "listing denied" in str(error)
    assert len(client.calls) == 4
    assert patched["sleeps"] == [1, 2, 4]
    assert patched["subprocess"] == []
    assert patched["tokens"] == []


def test_listing_persistent_transport_error_reports_last_error(upload_r2, patched):
    client = FakeClient([], default=ReadTimeout("read timed out"))

    _, error = outcome(upload_r2.listing(client, PREFIX))

    assert isinstance(error, RuntimeError), f"transport failures must exhaust retries: {error!r}"
    assert PREFIX in str(error)
    assert "read timed out" in str(error)
    assert len(client.calls) == 4
    assert patched["sleeps"] == [1, 2, 4]
    assert patched["subprocess"] == []


def test_listing_403_refreshes_token_in_thread_with_timeout(upload_r2, patched):
    client = FakeClient([FakeResponse(NULL_PAGE.json(), status_code=403), good([], None, False)])

    assert asyncio.run(upload_r2.listing(client, PREFIX)) == {}
    assert patched["subprocess"] == [["bunx", "wrangler", "whoami"]]
    assert patched["threads"] == [upload_r2.subprocess.run]
    assert patched["run_kwargs"] == [{"capture_output": True, "timeout": 60}]
    assert client.headers["Authorization"] == "Bearer tok-1"
    assert patched["sleeps"] == [1]


def test_wrangler_timeout_raises_login_guidance(upload_r2, patched, monkeypatch):
    def timed_out(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 60)

    monkeypatch.setattr(upload_r2.subprocess, "run", timed_out)
    client = FakeClient([NULL_PAGE, good([], None, False)])

    _, error = outcome(upload_r2.listing(client, PREFIX))

    assert isinstance(error, RuntimeError), f"wrangler timeout needs login guidance: {error!r}"
    assert "bunx wrangler login" in str(error)
    assert patched["tokens"] == []
    assert "Authorization" not in client.headers


def test_wrangler_nonzero_exit_raises_login_guidance(upload_r2, patched, monkeypatch):
    def failed_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 1)

    monkeypatch.setattr(upload_r2.subprocess, "run", failed_run)
    client = FakeClient([NULL_PAGE, good([], None, False)])

    _, error = outcome(upload_r2.listing(client, PREFIX))

    assert isinstance(error, RuntimeError), f"wrangler failure needs login guidance: {error!r}"
    assert "bunx wrangler login" in str(error)
    assert patched["tokens"] == []
    assert "Authorization" not in client.headers


class MemoryFile:
    suffix = ".txt"

    def read_bytes(self):
        return b"fixture"


class FakePutClient:
    def __init__(self):
        self.headers = {"Authorization": "Bearer expired"}
        self.sent = []

    async def put(self, url, content, headers):
        self.sent.append(self.headers["Authorization"])
        return FakeResponse(status_code=401 if len(self.sent) == 1 else 200)


def test_upload_api_and_listing_use_same_refresh_helper(upload_r2, patched, monkeypatch):
    refreshed = []

    async def fake_refresh(client):  # ruff: ignore[unused-async] - same awaitable interface
        refreshed.append(client)
        client.headers["Authorization"] = "Bearer refreshed"

    monkeypatch.setattr(upload_r2, "refresh_token", fake_refresh, raising=False)
    listing_client = FakeClient([NULL_PAGE, good([], None, False)])
    assert asyncio.run(upload_r2.listing(listing_client, PREFIX)) == {}
    client = FakePutClient()
    failed = []

    asyncio.run(upload_r2.upload_api(client, "p/fixture.txt", MemoryFile(), asyncio.Semaphore(1),
                                     failed, asyncio.Lock()))

    assert refreshed == [listing_client, client]
    assert client.sent == ["Bearer expired", "Bearer refreshed"]
    assert failed == []
    assert patched["subprocess"] == []


# --- review round on PR #68 (CodeRabbit) ---------------------------------------------

@pytest.mark.parametrize("info", [
    {"cursor": "c1", "is_truncated": None},
    {"cursor": "c1", "is_truncated": "false"},
])
def test_listing_non_boolean_is_truncated_raises(upload_r2, patched, info):
    """null or a string is neither "more" nor "done": an indeterminate page must not end the listing."""
    client = FakeClient([{"success": True, "result": batch(0, 1), "result_info": info}])

    with pytest.raises(RuntimeError, match=PREFIX):
        asyncio.run(upload_r2.listing(client, PREFIX))


@pytest.mark.parametrize("body", [
    {"success": True, "result": {}},  # result must be the documented array
    [{"key": "p/00000", "size": 0}],  # a JSON body that is not an object
])
def test_listing_malformed_200_body_is_retried(upload_r2, patched, body):
    assert_retry_at_same_cursor(upload_r2, patched, FakeResponse(body))


@pytest.mark.parametrize(("value", "fallback", "wait"), [
    ("7", 1, 7),
    ("0", 1, 0),
    ("99999", 1, 300),  # capped: the API's rate window is 300 s
    ("-5", 2, 2),  # nonsense: the normal backoff
    ("soon", 4, 4),
    ("Wed, 21 Oct 2026 07:28:10 GMT", 1, 10),  # HTTP-date, 10 s after `now`
    ("Wed, 21 Oct 2026 07:27:00 GMT", 1, 0),  # already past
    ("Wed, 21 Oct 2027 07:28:00 GMT", 1, 300),
])
def test_retry_after_seconds_or_http_date_capped(upload_r2, value, fallback, wait):
    from datetime import UTC, datetime

    now = datetime(2026, 10, 21, 7, 28, 0, tzinfo=UTC)
    assert upload_r2.retry_after(value, fallback, now=now) == wait


def test_listing_429_with_huge_retry_after_sleeps_the_cap(upload_r2, patched):
    client = FakeClient([
        FakeResponse({"success": False, "result": None}, status_code=429, headers={"Retry-After": "99999"}),
        good([], None, False),
    ])

    assert asyncio.run(upload_r2.listing(client, PREFIX)) == {}
    assert patched["sleeps"] == [300]
