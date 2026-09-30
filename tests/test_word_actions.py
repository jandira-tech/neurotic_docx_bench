"""Word's Accept All / Reject All of pool comparisons, filed under the pair key.

``corpus/word/<action>/{docx,pdf}/<key>.*`` next to ``pools/<action>.csv``: the
key is the comparison's stem, so the accepted-changes matcher pairs a tool's
``<key>_<tool>`` with it directly.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from neurotic_docx_bench import hub, word_actions

K1 = "aaaaaaaaaa_x__vs__bbbbbbbbbb_y_redline_cccccccccc"
K2 = "dddddddddd_p__vs__eeeeeeeeee_q_redline_ffffffffff"
K3 = "1111111111_m__vs__2222222222_n_redline_3333333333"


def _tree(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    dest = root / "corpus/word"
    (dest / "pools").mkdir(parents=True)
    with (dest / "pools/accept_reject_split.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(("key", "pool", "state", "action", "seed"))
        w.writerow((K1, "word_based", "tracking_without_comments", "accept_all", 7))
        w.writerow((K2, "word_based", "with_comments_tracking", "reject_all", 7))
        w.writerow((K3, "word_based", "tracking_without_comments", "accept_all", 7))
    with (dest / "comparisons.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(("key", "docx"))
        w.writerow((K1, f"tracking_without_comments/docx/{K1}.docx"))
        w.writerow((K2, f"with_comments_tracking/docx/{K2}.docx"))
    acc, rej = root / "grok_run/acc", root / "grok_run/rej"
    acc.mkdir(parents=True)
    rej.mkdir(parents=True)
    (acc / f"{K1}_accepted_tracking.docx").write_bytes(b"PK acc 1")
    (acc / f"{K1}_accepted_tracking.pdf").write_bytes(b"%PDF acc 1")
    (acc / f"{K3}_accepted_tracking.docx").write_bytes(b"PK acc 3")  # Word saved it but never printed it
    (rej / f"{K2}_rejected_tracking.docx").write_bytes(b"PK rej 2")
    (rej / f"{K2}_rejected_tracking.pdf").write_bytes(b"%PDF rej 2")
    return root, dest


def _rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="") as fh:
        return {r["key"]: r for r in csv.DictReader(fh)}


def test_files_each_output_under_its_pair_key(tmp_path: Path) -> None:
    root, dest = _tree(tmp_path)
    counts = word_actions.build(
        root, dest, {"accept_all": root / "grok_run/acc", "reject_all": root / "grok_run/rej"},
    )
    assert counts == {"accept_all": {"ok": 1, "no_pdf": 1}, "reject_all": {"ok": 1}}
    assert (dest / f"accept_all/docx/{K1}.docx").read_bytes() == b"PK acc 1"
    assert (dest / f"accept_all/pdf/{K1}.pdf").read_bytes() == b"%PDF acc 1"
    assert (dest / f"reject_all/pdf/{K2}.pdf").read_bytes() == b"%PDF rej 2"
    assert not (dest / f"accept_all/pdf/{K3}.pdf").exists()
    acc = _rows(dest / "pools/accept_all.csv")
    assert acc[K1]["docx"] == f"accept_all/docx/{K1}.docx" and acc[K1]["pdf"] == f"accept_all/pdf/{K1}.pdf"
    assert acc[K1]["source_docx"] == f"tracking_without_comments/docx/{K1}.docx"
    assert acc[K1]["origin_docx"] == f"grok_run/acc/{K1}_accepted_tracking.docx"
    assert (acc[K3]["status"], acc[K3]["pdf"], acc[K3]["source_docx"]) == ("no_pdf", "", "")
    assert set(_rows(dest / "pools/reject_all.csv")) == {K2}
    assert hub.verify_manifest(dest).ok
    # idempotent
    word_actions.build(root, dest, {"accept_all": root / "grok_run/acc", "reject_all": root / "grok_run/rej"})
    assert (dest / f"accept_all/docx/{K1}.docx").read_bytes() == b"PK acc 1"


def test_a_missing_output_folder_is_an_error(tmp_path: Path) -> None:
    root, dest = _tree(tmp_path)
    with pytest.raises(word_actions.WordActionsError, match="no output folder"):
        word_actions.build(root, dest, {"accept_all": root / "nope", "reject_all": root / "grok_run/rej"})


def test_stage_clones_what_a_list_names(tmp_path: Path) -> None:
    # a pool table (docx/pdf relative to the corpus root) becomes a working folder
    from neurotic_docx_bench import word_corpus

    dest = tmp_path / "corpus/word"
    (dest / "clean/docx").mkdir(parents=True)
    (dest / "clean/pdf").mkdir(parents=True)
    (dest / "pools").mkdir()
    (dest / "clean/docx/a1_x.docx").write_bytes(b"PK x")
    (dest / "clean/pdf/a1_x.pdf").write_bytes(b"%PDF x")
    (dest / "clean/docx/b2_y.docx").write_bytes(b"PK y")
    (dest / "clean/docx/c3_z.docx").write_bytes(b"PK not listed")
    with (dest / "pools/l.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(("stem", "kind", "docx", "pdf", "state"))
        w.writerow(("a1_x", "document", "clean/docx/a1_x.docx", "clean/pdf/a1_x.pdf", "clean"))
        w.writerow(("b2_y", "document", "clean/docx/b2_y.docx", "", "clean"))
    out = tmp_path / "out"
    assert word_corpus.stage_list(dest / "pools/l.csv", out) == 2
    assert sorted(p.name for p in (out / "docx").iterdir()) == ["a1_x.docx", "b2_y.docx"]
    assert [p.name for p in (out / "pdf").iterdir()] == ["a1_x.pdf"]
    assert word_corpus.stage_list(dest / "pools/l.csv", out) == 2  # idempotent
