"""Fetch a versioned release's input PDFs from the results hub (#180).

The versioned case shards are built from PDFs the repo does not track: each conversion
lane's candidates and each redline lane's Word exports. They live on the results dataset
under ``outputs/``, at the revision the release evidence pins. This puts exactly those
folders back where :mod:`release_cases` reads them, hash-verified by ``hub_get``, so a
fresh checkout (``bench publish``'s release worktree) builds the same release.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from neurotic_docx_bench import fixture_sets, hub, hub_get, hub_outputs
from neurotic_docx_bench.ledger.release_cases import (
    ReleaseInput,
    missing_scored_pdfs,
    release_inputs,
)

Get = Callable[..., object]


def fetch(root: Path, version: str, *, api: object | None = None, get: Get | None = None,
          revision: str | None = None) -> list[ReleaseInput]:
    """Download every input folder of ``version`` (PDFs only) at the pinned revision."""
    root = Path(root).resolve()
    revision = revision or hub_outputs.pinned_revision(root, version)
    if not revision:
        raise hub_outputs.PinnedRevisionMissing(
            f"no pinned revision for release {version} in {hub_outputs.evidence_path(root, version)}"
        )
    get = get or hub_get.get
    fixtures = fixture_sets.load()  # the corpus references: set v1's pinned commit
    pins = {
        "results": (hub.RESULTS_REPO, revision),
        "fixtures": (fixtures.repo_id, fixtures.revision),
    }
    inputs = release_inputs(root, version)
    api = api if api is not None else hub.default_api()
    for item in inputs:
        repo_id, rev = pins[item.repo]
        preset = hub_get.Preset(
            name=f"release-input:{item.hub_path}",
            repo_id=repo_id,
            path=item.hub_path,
            dest=item.local,
            about=f"release {version} input",
        )
        what = f"{len(item.files)} files" if item.files else "every PDF"
        print(f"{repo_id}:{item.hub_path} @ {rev[:12]} ({what}) -> {item.local.relative_to(root)}")
        if item.files:
            get(preset, api=api, revision=rev, dest=item.local, exact=item.files)
        else:
            get(preset, api=api, revision=rev, dest=item.local, include=("*.pdf", "manifest.jsonl"))
    missing = missing_scored_pdfs(root, version)
    if missing:
        more = f" and {len(missing) - 5} more" if len(missing) > 5 else ""
        raise RuntimeError(
            f"release {version}: {len(missing)} scored redline row(s) have no Word-rendered PDF "
            f"after the fetch ({'; '.join(missing[:5])}{more}); the release would link nothing "
            "for them"
        )
    return inputs
