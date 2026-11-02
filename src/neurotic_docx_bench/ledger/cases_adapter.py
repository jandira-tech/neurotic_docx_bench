"""The one-time adapter: today's published case pages as contract objects.

The published gh-pages/benchmarks.law pages are the authoritative copy of the
case browsers' data (the survey found no canonical store for most of it). This
module imports that data — never the other way round: the emitter
(:mod:`neurotic_docx_bench.ledger.cases`) reads stores, not published HTML.

Two published forms are read:

* the inline gh-pages page — ``const ENGINES = [...]`` / ``const DATA = [...]``
  with absolute R2 asset URLs, rewritten to ``~/`` paths against the discovered
  ``assets_base`` (the ``https://`` origin of the first asset URL);
* the benchmarks.law ``data.json`` — ``{"base": ..., "cases": [...]}`` with
  ``~/`` paths already relative to ``base``.

The kind comes from the source page's path (a ``redlines/`` path component
imports as ``redline``), never from group spelling. Engine lists are the union
of every lane key the data uses (``engines_from_cases``), so lanes that only
appear as dropped/unavailable/superseded pins are covered too; labels come from
the page's own ``ENGINES`` display map, with ``ledger.cases.LABEL_OVERRIDES``
keeping them unique across kinds.

:func:`write_legacy` produces the emitter's ``legacy_cases`` input once — the
published families the stores cannot derive — and is the only piece of the
release that reads the pages.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from bench_ops.models import (
    Case,
    CaseShard,
    CasesIndex,
    ShardRef,
    dumps_compact,
    engines_from_cases,
    shard_path,
    validate_bundle,
)
from neurotic_docx_bench.ledger import cases as cases_mod
from neurotic_docx_bench.ledger.scores import RESULTS_REPO_URL


def _const(text: str, name: str) -> object:
    """The value of ``const <name> = <json>;`` in an inline page."""
    marker = f"const {name} = "
    at = text.index(marker) + len(marker)
    value, _ = json.JSONDecoder().raw_decode(text, at)
    return value


def _discover_base(cases: list[dict]) -> str:
    """The public asset base: the ``https://`` origin of the first asset URL."""
    for case in cases:
        for lanes in (case.get("pages") or {}).values():
            for url in lanes:
                if url:
                    parts = urlsplit(str(url))
                    if parts.scheme == "https":
                        return f"{parts.scheme}://{parts.netloc}/"
        for url in (case.get("pdfs") or {}).values():
            parts = urlsplit(str(url))
            if parts.scheme == "https":
                return f"{parts.scheme}://{parts.netloc}/"
    raise ValueError("the page carries no absolute asset URL to discover assets_base from")


def _relative(url: str, base: str, where: str) -> str:
    if url.startswith("~/"):
        return url
    if url.startswith(base):
        return "~/" + url[len(base) :]
    raise ValueError(f"{where}: asset URL {url!r} is neither ~/relative nor under {base}")


def from_published(path: Path, *, now: datetime | None = None) -> tuple[CasesIndex, list[CaseShard]]:
    """One published page (or its ``data.json``) as ``(CasesIndex, shards)``."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    kind = "redline" if "redlines" in path.parts else "conversion"
    if text.lstrip().startswith("{"):
        payload = json.loads(text)
        base = str(payload["base"])
        raw_cases = list(payload["cases"])
        page_labels: dict[str, str] = {}
    else:
        raw_cases = list(_const(text, "DATA"))  # type: ignore[arg-type]
        base = _discover_base(raw_cases)
        engines = _const(text, "ENGINES")
        page_labels = {str(pair[0]): str(pair[1]) for pair in engines}  # type: ignore[index,union-attr]
    cases: list[Case] = []
    for raw in raw_cases:
        row = dict(raw)
        row["kind"] = kind
        pages = row.get("pages")
        if isinstance(pages, dict):
            row["pages"] = {
                engine: [
                    None if slot is None else _relative(str(slot), base, str(path))
                    for slot in slots
                ]
                for engine, slots in pages.items()
            }
        pdfs = row.get("pdfs")
        if isinstance(pdfs, dict):
            row["pdfs"] = {
                engine: _relative(str(url), base, str(path)) for engine, url in pdfs.items()
            }
        cases.append(Case.model_validate(row))
    by_group: dict[tuple[str, str], list[Case]] = {}
    for case in cases:
        by_group.setdefault((case.kind, case.group), []).append(case)
    shards = [
        CaseShard(kind=k, group=g, cases=sorted(group_cases, key=lambda c: c.case))
        for (k, g), group_cases in sorted(by_group.items())
    ]
    index = CasesIndex(
        version=cases_mod.CONTRACT_VERSION,
        generated=now or datetime.now(UTC),
        repo=RESULTS_REPO_URL,
        assets_base=base,
        engines=engines_from_cases(cases, {**page_labels, **cases_mod.LABEL_OVERRIDES}),
        groups=[
            ShardRef(
                kind=shard.kind,
                group=shard.group,
                count=len(shard.cases),
                path=shard_path(shard.kind, shard.group),
            )
            for shard in shards
        ],
    )
    validate_bundle(index, shards)
    return index, shards


def write_legacy(pages, dest: Path, *, now: datetime | None = None) -> Path:
    """The ``legacy_cases`` input for :func:`cases.emit`, written once.

    One compact ``CaseShard`` per line, families sorted — the published data
    for every family the stores cannot derive, byte-for-byte as the adapter
    reads it. Commit it under ``results/`` when it is under 2 MB; otherwise it
    lives under ``results/release/`` (git-ignored) and is listed with the
    release.
    """
    shards: dict[tuple[str, str], CaseShard] = {}
    for page in pages:
        for shard in from_published(Path(page), now=now)[1]:
            key = (shard.kind, shard.group)
            if key in shards:
                raise ValueError(f"{page}: family {key} already comes from another page")
            shards[key] = shard
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        "".join(dumps_compact(shards[key]) + "\n" for key in sorted(shards)),
        encoding="utf-8",
    )
    return dest
