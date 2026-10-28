"""Versioned fixture sets: what the bench's results were measured on, pinned to one hub commit.

A fixture set is a frozen manifest of files on the fixtures dataset
(``hub.FIXTURES_REPO``) and the commit they are read at. The wheel ships the
manifest (``data/fixture_sets/<name>.csv.gz`` and its ``<name>.json``), never the
documents: ``get`` downloads exactly the manifest's files at the pinned commit
through ``hub_get`` (no clobbering, the hub's own hashes) and then checks every
file against the manifest's sha256.

**v1** is every file whose oracle Microsoft Word made, for every test the bench
runs (``TESTS``): a document and Word's PDF of it (``docx_to_pdf``); the two sides
of a compare, Word's compare and Word's PDF of that compare (``redline``); a Word
compare with Word's Accept All or Reject All of it and Word's PDF of the result
(``accept_all``, ``reject_all``). LibreOffice renders, superseded Word renders
(``pdf_prior``) and the one compare Word left without a PDF are not in it.
``accept_reject_split.csv`` gives each compare one action, so the tests are a
union: no case is in all four.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

from neurotic_docx_bench import hub, hub_get

TESTS = ("docx_to_pdf", "redline", "accept_all", "reject_all")
# The corpus tables (documents.csv, comparisons.csv, pools/, notices/, the manifest) that
# name the files; ``get`` always fetches them, whatever ``tests`` asks for.
SUPPORT = "support"
COLUMNS = ("test", "case", "state", "role", "path", "sha256", "size", "blob_id")
DEFAULT = "v1"


class FixtureSetError(Exception):
    """A set that cannot be read, or a hub commit that does not hold the set's bytes."""


@dataclass(frozen=True)
class Row:
    """One file of one case of one test. ``path`` is relative to the set's ``path`` on the hub."""

    test: str
    case: str
    state: str
    role: str
    path: str
    sha256: str
    size: int
    blob_id: str


@dataclass(frozen=True)
class FixtureSet:
    name: str
    repo_id: str
    revision: str
    path: str
    tests: tuple[str, ...] = TESTS
    cases: dict[str, int] = field(default_factory=dict)
    files: int = 0
    bytes: int = 0
    about: str = ""

    @property
    def dest(self) -> Path:
        """Where ``get`` puts the files by default: the corpus folder the bench reads."""
        return hub.DEFAULT_CORPUS / self.path


def _data() -> Traversable:
    return resources.files("neurotic_docx_bench") / "data" / "fixture_sets"


def manifest_resource(name: str = DEFAULT) -> Traversable:
    return _data() / f"{name}.csv.gz"


def names() -> list[str]:
    return sorted(p.name.removesuffix(".json") for p in _data().iterdir() if p.name.endswith(".json"))


def load(name: str = DEFAULT) -> FixtureSet:
    meta = _data() / f"{name}.json"
    if not meta.is_file():
        raise FixtureSetError(f"no fixture set {name!r}; known: {', '.join(names()) or 'none'}")
    raw = json.loads(meta.read_text(encoding="utf-8"))
    return FixtureSet(**raw | {"tests": tuple(raw.get("tests", TESTS))})


def _parse(text: str) -> list[Row]:
    reader = csv.DictReader(io.StringIO(text))
    if tuple(reader.fieldnames or ()) != COLUMNS:
        raise FixtureSetError(f"a fixture manifest has the columns {COLUMNS}, not {reader.fieldnames}")
    return [Row(**r | {"size": int(r["size"])}) for r in reader]


def rows(name: str = DEFAULT, tests: Sequence[str] = ()) -> list[Row]:
    """The manifest's rows, of ``tests`` only when given."""
    unknown = sorted(set(tests) - set(TESTS))
    if unknown:
        raise FixtureSetError(f"unknown test(s) {unknown}; the tests are {', '.join(TESTS)}")
    with manifest_resource(name).open("rb") as fh:
        got = _parse(gzip.decompress(fh.read()).decode("utf-8"))
    return [r for r in got if not tests or r.test in tests or r.test == SUPPORT]


def files(name: str = DEFAULT, tests: Sequence[str] = ()) -> dict[str, Row]:
    """One row per file (a document is the base of many compares): path → its first row."""
    out: dict[str, Row] = {}
    for r in rows(name, tests):
        out.setdefault(r.path, r)
    return out


# --- building a set from the corpus tables -------------------------------------


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def build(word: Path, listing: Mapping[str, tuple[int, str, str | None]]) -> list[Row]:
    """The v1 rows from ``corpus/word``'s tables, hashes from its ``MANIFEST.sha256.json``.

    ``listing`` gives each hub path (relative to ``word/``) its size, git blob id and
    LFS sha256 (None for an inline file) at the pinned commit. A file the tables name
    that the manifest or the listing lacks is refused: the set must be complete or
    not exist. Every other file of the listing that is not a docx or PDF is a table
    the set ships as ``support``; the local copy must be the hub's.
    """
    sha = json.loads((word / "MANIFEST.sha256.json").read_text(encoding="utf-8"))["files"]
    out: list[Row] = []

    def add(test: str, case: str, state: str, role: str, path: str) -> None:
        if path not in sha or path not in listing:
            raise FixtureSetError(f"{test} {case}: {path} is not in the corpus manifest and the hub listing")
        size, blob, _ = listing[path]
        out.append(Row(test, case, state, role, path, sha[path], int(size), blob))

    documents = _read(word / "documents.csv")
    docx_of = {d["id"]: d["docx"] for d in documents}
    for d in sorted(documents, key=lambda d: d["id"]):
        add("docx_to_pdf", d["id"], d["state"], "input_docx", d["docx"])
        add("docx_to_pdf", d["id"], d["state"], "word_pdf", d["pdf"])
    for c in sorted(_read(word / "comparisons.csv"), key=lambda c: c["id"]):
        if not c["pdf"]:  # Word made the compare but no PDF of it: not measurable
            continue
        add("redline", c["id"], c["state"], "base_docx", docx_of[c["base_id"]])
        add("redline", c["id"], c["state"], "next_docx", docx_of[c["next_id"]])
        add("redline", c["id"], c["state"], "word_docx", c["docx"])
        add("redline", c["id"], c["state"], "word_pdf", c["pdf"])
    for action in ("accept_all", "reject_all"):
        for a in sorted(_read(word / "pools" / f"{action}.csv"), key=lambda a: a["key"]):
            if a["status"] != "ok":
                continue
            add(action, a["key"], a["state"], "input_docx", a["source_docx"])
            add(action, a["key"], a["state"], "word_docx", a["docx"])
            add(action, a["key"], a["state"], "word_pdf", a["pdf"])
    for path, (size, blob, lfs) in sorted(listing.items()):
        if path.endswith((".docx", ".pdf")):
            continue
        data = (word / path).read_bytes() if (word / path).is_file() else None
        digest = hashlib.sha256(data).hexdigest() if data is not None else None
        if data is None or len(data) != size or (lfs or _git_blob(data)) != (lfs and digest or blob):
            raise FixtureSetError(f"{word / path} is not the hub's {path} at the pinned commit")
        out.append(Row(SUPPORT, "tables", "", "table", path, digest, int(size), blob))
    return out


def write(name: str, folder: Path, built: Sequence[Row], meta: FixtureSet) -> tuple[Path, Path]:
    """Write ``<name>.csv.gz`` (byte-stable: no gzip timestamp) and ``<name>.json`` into ``folder``."""
    folder.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(COLUMNS)
    w.writerows([getattr(r, c) for c in COLUMNS] for r in built)
    csv_path = folder / f"{name}.csv.gz"
    csv_path.write_bytes(gzip.compress(buf.getvalue().encode("utf-8"), mtime=0))
    unique = {r.path: r.size for r in built}
    cases = Counter(t for t, _ in {(r.test, r.case) for r in built if r.test != SUPPORT})
    full = FixtureSet(**asdict(meta) | {"name": name, "cases": {t: cases[t] for t in TESTS if cases[t]},
                                        "files": len(unique), "bytes": sum(unique.values())})
    meta_path = folder / f"{name}.json"
    meta_path.write_text(json.dumps(asdict(full) | {"tests": list(full.tests)}, indent=1) + "\n", encoding="utf-8")
    return csv_path, meta_path


# --- getting a set --------------------------------------------------------------


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _check_remote(meta: FixtureSet, wanted: Mapping[str, Row], remote: Iterable[hub_get.RemoteFile]) -> None:
    """Every set file is at the pinned commit with the manifest's size and hash, before a byte moves."""
    got = {f.rel: f for f in remote}
    where = f"{meta.repo_id}@{meta.revision[:12]}"
    missing = sorted(set(wanted) - set(got))
    if missing:
        raise FixtureSetError(f"{where} lacks {len(missing)} file(s) of set {meta.name}: {', '.join(missing[:5])}")
    wrong = sorted(
        rel for rel, r in wanted.items()
        if got[rel].size != r.size
        or (got[rel].sha256 is not None and got[rel].sha256 != r.sha256)
        or (got[rel].sha256 is None and got[rel].blob_id != r.blob_id)
    )
    if wrong:
        raise FixtureSetError(
            f"{where} holds other bytes than set {meta.name} for {len(wrong)} file(s): {', '.join(wrong[:5])}"
        )


def get(
    name: str = DEFAULT,
    *,
    api: Any = None,
    dest: Path | None = None,
    tests: Sequence[str] = (),
    on_conflict: str = "refuse",
    dry_run: bool = False,
    workers: int = 8,
) -> hub_get.GetReport:
    """Download set ``name`` (of ``tests`` only, when given) at its pinned commit into ``dest``.

    The hub's listing at that commit is checked against the manifest first, and
    ``hub_get`` checks every staged file against that listing before it moves one, so
    no byte that is not the manifest's is placed. The hash after the download is a
    second look. Files ``keep-local`` kept are not the set's and the report says so.
    """
    meta = load(name)
    wanted = files(name, tests)
    dest = Path(dest if dest is not None else meta.dest)
    if not wanted:
        return hub_get.GetReport(meta.repo_id, meta.revision, dest, 0, 0, 0, 0, 0, 0, (), dry_run)
    api = api if api is not None else hub.default_api()
    remote = hub_get.remote_files(api, meta.repo_id, meta.revision, meta.path, exact=sorted(wanted))
    _check_remote(meta, wanted, remote)
    preset = hub_get.Preset(f"fixtures-{name}", meta.repo_id, meta.path, dest, f"fixture set {name}")
    report = hub_get.get(preset, api=api, revision=meta.revision, dest=dest, exact=sorted(wanted),
                         on_conflict=on_conflict, dry_run=dry_run, workers=workers)
    if not dry_run:
        kept = set(report.kept_local)
        bad = sorted(rel for rel, r in wanted.items() if rel not in kept and _sha256(dest / rel) != r.sha256)
        if bad:
            raise FixtureSetError(f"{len(bad)} file(s) in {dest} do not match set {name}: {', '.join(bad[:5])}")
    return report
