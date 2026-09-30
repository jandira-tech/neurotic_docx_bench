"""superdoc_speed: --pairs-csv plans, per-pair timings, and no output left behind."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from neurotic_docx_bench import superdoc_speed


class FakeClient:
    made: list[FakeClient] = []

    def __init__(self, **_):
        self.connected = self.disposed = False
        FakeClient.made.append(self)

    async def connect(self):
        self.connected = True

    async def dispose(self):
        self.disposed = True

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *exc):
        await self.dispose()
        return False


def test_pairs_from_csv_reads_key_paths_and_category(tmp_path: Path):
    plan = tmp_path / 'pairs.csv'
    plan.write_text('key,base,next,category,base_bytes\nk1,a.docx,b.docx,real,10\nk2,b.docx,a.docx,reverse,12\n')
    assert superdoc_speed.pairs_from_csv(plan) == [
        ('k1', Path('a.docx'), Path('b.docx'), 'real'),
        ('k2', Path('b.docx'), Path('a.docx'), 'reverse'),
    ]


def test_run_times_each_pair_deletes_its_output_and_logs_failures(tmp_path: Path, monkeypatch):
    written: list[Path] = []

    async def fake_generate(client, base, nxt, out, idx):
        await asyncio.sleep(0)
        if base.name == 'bad.docx':
            raise RuntimeError('diff.apply: refused')
        out.write_bytes(b'docx')
        written.append(out)

    monkeypatch.setattr(superdoc_speed, 'generate_one', fake_generate)
    monkeypatch.setattr(superdoc_speed, 'AsyncSuperDocClient', FakeClient)
    pairs = [('k1', Path('a.docx'), Path('b.docx'), 'real'), ('k2', Path('bad.docx'), Path('b.docx'), 'grid')]
    per_pair = tmp_path / 'per_pair.jsonl'
    row = asyncio.run(superdoc_speed.run(pairs, reps=1, warmup=1, per_pair_out=per_pair))

    assert row['n'] == 1 and row['failures'] == 1
    assert written and not any(p.exists() for p in written)
    lines = [json.loads(line) for line in per_pair.read_text().splitlines()]
    assert [(r['key'], r['category'], r['ok']) for r in lines] == [('k1', 'real', True), ('k2', 'grid', False)]
    assert lines[1]['ms'] is not None and 'refused' in lines[1]['error']


def test_run_counts_a_hung_pair_as_a_timeout_failure(tmp_path: Path, monkeypatch):
    async def hang(client, base, nxt, out, idx):
        await asyncio.sleep(10)

    monkeypatch.setattr(superdoc_speed, 'generate_one', hang)
    monkeypatch.setattr(superdoc_speed, 'AsyncSuperDocClient', FakeClient)
    row = asyncio.run(
        superdoc_speed.run([('k', Path('a.docx'), Path('b.docx'), '')], reps=1, warmup=0, timeout_s=0.05)
    )
    assert row['failures'] == 1 and row['timeouts'] == 1


def test_a_timeout_disposes_the_busy_host_and_the_next_pair_gets_a_fresh_client(tmp_path: Path, monkeypatch):
    FakeClient.made = []
    used: list[FakeClient] = []

    async def gen(client, base, nxt, out, idx):
        used.append(client)
        if base.name == 'hang.docx':
            await asyncio.sleep(10)

    monkeypatch.setattr(superdoc_speed, 'generate_one', gen)
    monkeypatch.setattr(superdoc_speed, 'AsyncSuperDocClient', FakeClient)
    pairs = [('k1', Path('hang.docx'), Path('b.docx'), ''), ('k2', Path('a.docx'), Path('b.docx'), '')]
    row = asyncio.run(superdoc_speed.run(pairs, reps=1, warmup=0, timeout_s=0.05))

    assert row['timeouts'] == 1 and row['n'] == 1 and row['host_restarts'] == 1
    assert used[0] is FakeClient.made[0] and FakeClient.made[0].disposed
    assert used[1] is FakeClient.made[1] and FakeClient.made[1].connected
    assert all(c.disposed for c in FakeClient.made)


def test_each_row_is_on_disk_when_its_pair_ends(tmp_path: Path, monkeypatch):
    per_pair = tmp_path / 'per_pair.jsonl'
    seen: list[int] = []

    async def gen(client, base, nxt, out, idx):
        await asyncio.sleep(0)
        seen.append(len(per_pair.read_text().splitlines()) if per_pair.exists() else 0)

    monkeypatch.setattr(superdoc_speed, 'generate_one', gen)
    monkeypatch.setattr(superdoc_speed, 'AsyncSuperDocClient', FakeClient)
    pairs = [(f'k{i}', Path('a.docx'), Path('b.docx'), '') for i in range(3)]
    asyncio.run(superdoc_speed.run(pairs, reps=1, warmup=0, per_pair_out=per_pair))
    assert seen == [0, 1, 2]


@pytest.mark.parametrize('bad', ['key,base\nk,a\n', 'key,base,next\nk,a,b\nk,b,a\n'])
def test_pairs_from_csv_rejects_bad_plans(tmp_path: Path, bad: str):
    plan = tmp_path / 'pairs.csv'
    plan.write_text(bad)
    with pytest.raises(ValueError):
        superdoc_speed.pairs_from_csv(plan)
