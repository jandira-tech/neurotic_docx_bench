"""Vendor registry: the single source of truth for tool identity.

Every store the report reads names tools differently: ``bench.jsonl`` has a
``vendor`` string plus a run name inside ``environment_config``, speed rows have a
``tool`` string that may carry an ``-inproc`` suffix, converter reports have their
own ``tool`` key. The registry maps each of those spellings to exactly one
``tool_id`` and carries the facts the tables need (display name, role, engine,
author affiliation, benchmarks the tool cannot perform).
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

Role = Literal["generator", "editor", "converter", "calibration"]
Status = Literal["active", "retired"]

DEFAULT_REGISTRY_PATH = Path("bench.registry.yaml")
_INPROC_SUFFIX = "-inproc"


class ToolEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    vendor: str
    display: str
    role: Role
    engine: str
    affiliated: bool = False
    status: Status = "active"
    configuration: str | None = None
    run_names: tuple[str, ...] = ()
    bench_vendors: tuple[str, ...] = ()
    speed_tools: tuple[str, ...] = ()
    converter_tools: tuple[str, ...] = ()
    not_applicable: tuple[str, ...] = ()
    url: str | None = None
    note: str | None = None

    def applies_to(self, benchmark: str) -> bool:
        return benchmark not in self.not_applicable


class Registry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int
    tools: tuple[ToolEntry, ...]

    @model_validator(mode="after")
    def _unique_claims(self) -> Registry:
        ids: set[str] = set()
        claims: dict[str, dict[str, str]] = {
            "run name": {},
            "speed tool": {},
            "converter tool": {},
        }
        for t in self.tools:
            if t.id in ids:
                raise ValueError(f"duplicate tool id {t.id!r}")
            ids.add(t.id)
            for label, names in (
                ("run name", t.run_names),
                ("speed tool", t.speed_tools),
                ("converter tool", t.converter_tools),
            ):
                for name in names:
                    owner = claims[label].get(name)
                    if owner is not None:
                        raise ValueError(
                            f"{label} {name!r} claimed by {owner!r} and {t.id!r}"
                        )
                    claims[label][name] = t.id
        return self

    def by_id(self, tool_id: str) -> ToolEntry:
        for t in self.tools:
            if t.id == tool_id:
                return t
        raise KeyError(tool_id)

    def resolve_bench(
        self, *, vendor: str, run_name: str, render: str
    ) -> ToolEntry | None:
        """Run name first (most specific), then bench vendor. A playwright render
        prefers an editor entry for that vendor, any other render a non-editor one."""
        for t in self.tools:
            if run_name in t.run_names:
                return t
        want_editor = render == "playwright"
        candidates = [t for t in self.tools if vendor in t.bench_vendors]
        preferred = [t for t in candidates if (t.role == "editor") == want_editor]
        if preferred:
            return preferred[0]
        return candidates[0] if candidates else None

    def resolve_speed(self, tool: str) -> tuple[ToolEntry | None, bool]:
        inproc = tool.endswith(_INPROC_SUFFIX)
        base = tool[: -len(_INPROC_SUFFIX)] if inproc else tool
        for t in self.tools:
            if base in t.speed_tools or tool in t.speed_tools:
                return t, inproc
        return None, False

    def resolve_converter(self, tool: str) -> ToolEntry | None:
        for t in self.tools:
            if tool in t.converter_tools:
                return t
        return None


def load_registry(path: Path = DEFAULT_REGISTRY_PATH) -> Registry:
    raw = yaml.safe_load(Path(path).read_text())
    if not isinstance(raw, dict):
        raise TypeError(f"{path}: registry must be a mapping")
    return Registry.model_validate(raw)
