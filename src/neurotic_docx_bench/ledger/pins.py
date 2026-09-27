"""Parse the tool_version strings the stores carry into comparable parts.

Shapes seen in ``results/bench.jsonl`` and the converter reports:

- ``9.8.0`` (npm / PyPI version)
- ``jubarte-final@dd16ad8fbcf3`` (dist label + 12-hex content hash)
- ``0.2.0@1286be69c690+git.<sha>`` (label + hash + engine commit, sha 7 to 40 hex)
- ``jubarte 0.7.0`` / ``docxide-pdf v0.17.0`` (converter ``--version`` output)
- ``None`` / empty (unversioned sanity runs)
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

_PIN_RE = re.compile(
    r"^(?P<label>[^@\s]+)@(?P<hash>[0-9a-f]{6,64})(?:\+git\.(?P<sha>[0-9a-f]{7,40}))?$"
)


class ToolPin(BaseModel):
    model_config = ConfigDict(frozen=True)

    raw: str | None
    label: str | None
    content_hash: str | None
    git_sha: str | None

    @classmethod
    def parse(cls, raw: object) -> ToolPin:
        """Parse a stripped version string, treating None, empty text, and "None" as unpinned.

        Recognize ``label@hash[+git.sha]`` with a 6–64 digit lowercase hex hash
        and an optional 7–40 digit lowercase hex SHA. Other text is retained as
        both raw version and label; non-None inputs are converted to strings.
        """
        if raw is None:
            return cls(raw=None, label=None, content_hash=None, git_sha=None)
        text = str(raw).strip()
        if not text or text == "None":
            return cls(raw=None, label=None, content_hash=None, git_sha=None)
        m = _PIN_RE.match(text)
        if m:
            return cls(
                raw=text,
                label=m.group("label"),
                content_hash=m.group("hash"),
                git_sha=m.group("sha"),
            )
        return cls(raw=text, label=text, content_hash=None, git_sha=None)

    @property
    def pinned(self) -> bool:
        """Whether a raw version is present, even without a content hash or commit."""
        return self.raw is not None

    @property
    def identity(self) -> str | None:
        """What "the same pin" means: the content hash when there is one, else the raw text."""
        if self.content_hash:
            return self.content_hash
        return self.raw

    @property
    def display(self) -> str:
        """Return "unpinned", raw text, or a label with hash/SHA shortened to 12/7 characters."""
        if self.raw is None:
            return "unpinned"
        if self.content_hash is None:
            return self.raw
        out = f"{self.label}@{self.content_hash[:12]}"
        if self.git_sha:
            out += f"+git.{self.git_sha[:7]}"
        return out

    def same_commit(self, other: ToolPin) -> bool:
        """Compare SHA prefixes through the shorter length; return False if either is absent."""
        if not self.git_sha or not other.git_sha:
            return False
        n = min(len(self.git_sha), len(other.git_sha))
        return self.git_sha[:n] == other.git_sha[:n]
