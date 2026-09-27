"""Every version-string shape in results/bench.jsonl and the converter reports parses."""

from __future__ import annotations

import pytest

from neurotic_docx_bench.ledger.pins import ToolPin


@pytest.mark.parametrize(
    ("raw", "label", "content_hash", "git_sha"),
    [
        ("9.8.0", "9.8.0", None, None),
        ("0.3.0-ts-migration", "0.3.0-ts-migration", None, None),
        ("jubarte-final@dd16ad8fbcf3", "jubarte-final", "dd16ad8fbcf3", None),
        (
            "0.2.0@1286be69c690+git.65014685f960a5c1b9a19250e23fccaa4df5e5ef",
            "0.2.0",
            "1286be69c690",
            "65014685f960a5c1b9a19250e23fccaa4df5e5ef",
        ),
        (
            "jubarte-rust@9457b6549b5d+git.ebf1a79",
            "jubarte-rust",
            "9457b6549b5d",
            "ebf1a79",
        ),
        ("jubarte 0.7.0", "jubarte 0.7.0", None, None),
        (
            "LibreOffice Convert Rust v0.1.0",
            "LibreOffice Convert Rust v0.1.0",
            None,
            None,
        ),
    ],
)
def test_parse_shapes(
    raw: str, label: str, content_hash: str | None, git_sha: str | None
) -> None:
    pin = ToolPin.parse(raw)
    assert pin.raw == raw
    assert pin.label == label
    assert pin.content_hash == content_hash
    assert pin.git_sha == git_sha


@pytest.mark.parametrize("raw", [None, "", "   ", "None"])
def test_missing_versions_are_unpinned(raw: str | None) -> None:
    pin = ToolPin.parse(raw)
    assert pin.raw is None
    assert pin.pinned is False
    assert pin.display == "unpinned"


def test_identity_is_content_hash_when_present() -> None:
    a = ToolPin.parse("jubarte-final@dd16ad8fbcf3")
    b = ToolPin.parse("0.9.9@dd16ad8fbcf3+git.abcdef1")
    assert a.identity == b.identity == "dd16ad8fbcf3"
    assert ToolPin.parse("9.8.0").identity == "9.8.0"


def test_display_is_short_and_stable() -> None:
    pin = ToolPin.parse(
        "0.2.0@1286be69c690+git.65014685f960a5c1b9a19250e23fccaa4df5e5ef"
    )
    assert pin.display == "0.2.0@1286be69c690+git.6501468"
    assert ToolPin.parse("9.8.0").display == "9.8.0"


def test_same_git_commit_detected_across_short_and_long_sha() -> None:
    a = ToolPin.parse("x@000000000000+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731")
    b = ToolPin.parse("y@111111111111+git.ebf1a79")
    assert a.same_commit(b) is True
    assert a.same_commit(ToolPin.parse("z@222222222222")) is False
