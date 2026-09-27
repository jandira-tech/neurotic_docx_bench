"""Every version-string shape in results/bench.jsonl and the converter reports parses."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

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


@pytest.mark.parametrize("raw", [None, "", " \t\n", " None "])
def test_unpinned_versions_have_no_identity(raw) -> None:
    pin = ToolPin.parse(raw)
    assert (pin.identity, pin.label, pin.content_hash, pin.git_sha) == (None,) * 4


@pytest.mark.parametrize("raw, expected", [(42, "42"), (9.8, "9.8"), ("  v1.2\n", "v1.2")])
def test_plain_versions_are_normalized_without_losing_identity(raw, expected) -> None:
    pin = ToolPin.parse(raw)
    assert pin.raw == pin.label == pin.identity == pin.display == expected
    assert pin.pinned is True


@pytest.mark.parametrize("hash_length", [6, 64])
@pytest.mark.parametrize("sha_length", [7, 40])
def test_structured_pin_accepts_hash_and_sha_length_boundaries(hash_length, sha_length) -> None:
    content_hash = "a" * hash_length
    sha = "b" * sha_length
    pin = ToolPin.parse(f"  engine@{content_hash}+git.{sha}\n")
    assert pin.content_hash == pin.identity == content_hash
    assert pin.git_sha == sha
    assert pin.raw == f"engine@{content_hash}+git.{sha}"
    assert pin.display == f"engine@{content_hash[:12]}+git.{sha[:7]}"


def test_display_truncates_content_hash_without_a_git_commit() -> None:
    pin = ToolPin.parse("engine@0123456789abcdef")
    assert pin.display == "engine@0123456789ab"
    assert pin.identity == "0123456789abcdef"


@pytest.mark.parametrize(
    "raw",
    [
        "engine@abcde",
        "engine@" + "a" * 65,
        "engine@abcdef+git.123456",
        "engine@abcdef+git." + "a" * 41,
        "engine@abcdeg",
        "engine@abcdef+git.123456z",
        "@abcdef",
        "engine name@abcdef",
        "engine@abcdef+git.1234567.extra",
    ],
)
def test_malformed_structured_pin_is_preserved_as_an_opaque_version(raw) -> None:
    pin = ToolPin.parse(raw)
    assert pin.raw == pin.label == pin.identity == pin.display == raw
    assert pin.content_hash is None and pin.git_sha is None
    assert pin.pinned is True


@pytest.mark.parametrize(
    "left, right, expected",
    [
        ("a@aaaaaa+git.abcdef1", "b@bbbbbb+git.abcdef123456", True),
        ("a@aaaaaa+git.abcdef1", "b@aaaaaa+git.abcdef2", False),
        ("a@aaaaaa+git.abcdef123", "b@aaaaaa+git.abcdef124", False),
        ("a@aaaaaa", "b@aaaaaa", False),
        (None, None, False),
        (None, "b@bbbbbb+git.abcdef1", False),
    ],
)
def test_same_commit_is_symmetric_and_requires_matching_commit_prefixes(
    left, right, expected
) -> None:
    a, b = ToolPin.parse(left), ToolPin.parse(right)
    assert a.same_commit(b) is expected
    assert b.same_commit(a) is expected


def test_pin_cannot_be_reassigned() -> None:
    pin = ToolPin.parse("1.0")
    with pytest.raises(ValidationError, match="frozen_instance"):
        pin.raw = "2.0"
