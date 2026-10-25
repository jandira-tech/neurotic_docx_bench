"""RED tests for `listing()` pagination in scripts/publish/upload_r2.py (issue #63).

`listing()` used `for attempt in range(4)` as both its retry budget *and* its
pager, so any prefix with more than 4 pages of objects raised
`RuntimeError("R2 listing kept failing for prefix ...")`. These tests pin the
intended behaviour: paginate until `is_truncated` is false, refresh the token on
an error page, and retry per page.
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "publish" / "upload_r2.py"
PREFIX = "wordcraft-20261014/compare/oracle/"


@pytest.fixture
def upload_r2(monkeypatch: pytest.MonkeyPatch):
    """Load the upload script with a stub `httpx` (not installed in this env)."""
    monkeypatch.setitem(sys.modules, "httpx", types.ModuleType("httpx"))
    spec = importlib.util.spec_from_file_location("upload_r2_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
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
        return FakeResponse(page)


@pytest.fixture
def patched(upload_r2, monkeypatch: pytest.MonkeyPatch):
    """Replace the shell-out, the token reader and asyncio.sleep, recording calls."""
    rec = {"subprocess": [], "tokens": [], "sleeps": []}

    def fake_run(*args, **kwargs):
        rec["subprocess"].append(args[0] if args else None)
        return None

    counter = {"n": 0}

    def fake_token():
        counter["n"] += 1
        t = f"tok-{counter['n']}"
        rec["tokens"].append(t)
        return t

    async def fake_sleep(delay):  # ruff: ignore[unused-async] - stands in for asyncio.sleep, so it must be awaitable
        rec["sleeps"].append(delay)

    monkeypatch.setattr(upload_r2.subprocess, "run", fake_run)
    monkeypatch.setattr(upload_r2, "token", fake_token)
    monkeypatch.setattr(upload_r2.asyncio, "sleep", fake_sleep)
    return rec


def batch(start: int, count: int = 1000) -> list[dict]:
    return [{"key": f"p/{i:05d}", "size": i} for i in range(start, start + count)]


def expected(*batches: list[dict]) -> dict:
    return {o["key"]: o["size"] for b in batches for o in b}


def good(items: list[dict], cursor, truncated: bool) -> dict:
    return {"result": items, "result_info": {"cursor": cursor, "is_truncated": truncated}}


NULL_PAGE = {"result": None, "errors": [{"code": 10000, "message": "token expired"}]}


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
