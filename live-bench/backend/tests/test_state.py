# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
import uuid

from livebench.state import State


def test_queue_predecessor_and_outbox_commit_together_and_resume_idempotently():
    identifiers = iter(
        [
            "019a0000-0000-7000-8000-000000000001",
            "019a0000-0000-7000-8000-000000000002",
            "019a0000-0000-7000-8000-000000000003",
        ]
    )
    state = State(":memory:", id_factory=lambda: next(identifiers))
    assert state.next() is None
    state.enqueue([{"id": "same", "url": "https://example.com/a"}] * 2, {"cycle": 0, "offset": 2})
    first_sequence, first = state.queued_download()
    assert first_sequence == 1
    second_id = state.db.execute("SELECT row_json FROM queue WHERE sequence=2").fetchone()[0]
    assert first["review_id"] not in second_id
    assert uuid.UUID(first["review_id"]).version == 7
    assert state.next() is None
    state.downloaded(1, {"id": "same", "review_id": first["review_id"]})
    assert state.next()[0] == 1
    result = {"id": first["review_id"], "sequence": 1, "source": {"id": "same"}}
    state.finish(1, result, {"id": "previous"})
    assert state.get("completed") == 1 and state.get("previous")["id"] == "previous"
    assert state.pending()[0]["payload"] == result
    state.put_outbox(result["id"], "result", result)
    assert len(state.pending()) == 1
    state.acknowledge(result["id"])
    assert state.pending() == []
    assert state.batch_results(1, 1) == [result]
    state.prune_batch(1, 1)
    assert state.batch_results(1, 1) == []
    state.downloaded(2, {"id": "same"})
    assert state.queued_download() is None
    assert state.depth() == 1
    state.finish(2, {"id": "second", "sequence": 2}, {"id": "same"})
    state.enqueue([{"id": "third"}], {"cycle": 0, "offset": 3})
    assert state.queued_download()[0] == 3
    state.set("custom", {"alive": True})
    assert state.get("custom")["alive"]
    state.close()


def test_refill_marker_commits_with_sampler_and_rows():
    state = State(":memory:", id_factory=lambda: "review")
    state.enqueue([{"id": "fixture"}], {"cycle": 1, "offset": 3}, prefetched_group=4)
    assert state.get("prefetched_group") == 4
    assert state.get("sampler") == {"cycle": 1, "offset": 3}
    assert state.depth() == 1

    # A failed draw rolls back the entire transaction, including the refill marker.
    def failure():
        raise ValueError("id generator failed")

    state.id_factory = failure
    import pytest

    with pytest.raises(ValueError):
        state.enqueue([{"id": "new"}], {"cycle": 2, "offset": 0}, prefetched_group=5)
    assert state.get("prefetched_group") == 4 and state.depth() == 1
    assert state.get("sampler") == {"cycle": 1, "offset": 3}
    state.close()
