# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
from pathlib import Path

from livebench.config import Config
from livebench.service import Worker
from livebench.state import State


def test_two_hundred_initial_rows_and_one_hundred_refill_at_ninety_persist_across_boundary():
    class Index:
        height = 1000

        def row(self, index, named):
            assert named
            return {"id": str(index), "url": f"https://example.com/{index}.docx"}

    identifiers = iter(f"019a0000-0000-7000-8000-{i:012d}" for i in range(400))
    worker = object.__new__(Worker)
    worker.config = Config(Path("unused"), "https://word", "a", "https://ingest", "b")
    worker.state = State(":memory:", id_factory=lambda: next(identifiers))
    worker.index = Index()
    worker.replenish()
    assert worker.state.depth() == 200
    assert worker.state.get("sampler")["offset"] == 200
    for sequence in range(1, 101):
        queued_sequence, row = worker.state.queued_download()
        assert queued_sequence == sequence
        worker.state.downloaded(sequence, row)
        worker.state.finish(sequence, {"id": row["review_id"], "sequence": sequence}, row)
        if sequence == 90:
            worker.replenish()
            assert worker.state.depth() == 210
            assert worker.state.get("prefetched_group") == 1
            worker.replenish()
            assert worker.state.depth() == 210
    assert worker.state.depth() == 200
    assert worker.state.queued_download()[0] == 101
    assert worker.state.get("previous")["review_id"] == row["review_id"]
    assert worker.state.get("sampler")["offset"] == 300
    worker.state.close()
