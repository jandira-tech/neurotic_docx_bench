# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
import argparse
import fcntl
import hashlib
import json
import logging
import shutil
import threading
import time
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import httpx

from livebench.benchmark import Benchmark
from livebench.config import Config
from livebench.corpus import download, draw_indices, load_index
from livebench.models import MAX_FILE_BYTES, Document, batch_id, queue_target
from livebench.publisher import Publisher, archive_files
from livebench.seed import build_seed
from livebench.state import State
from livebench.tools import RealTools

LOG = logging.getLogger("livebench")


def now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def serialize_doc(doc: Document) -> dict:
    return {**asdict(doc), "path": str(doc.path) if doc.path else None}


def restore_doc(data: dict) -> Document:
    return Document(**{**data, "path": Path(data["path"]) if data["path"] else None})


class Worker:
    def __init__(self, config: Config):
        self.config = config
        config.data_dir.mkdir(parents=True, exist_ok=True)
        self.lock_file = (config.data_dir / "worker.lock").open("w")
        try:
            fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock_file.close()
            raise RuntimeError("another worker already owns this data volume") from None
        self.state = State(str(config.data_dir / "state.sqlite3"))
        self.client = httpx.Client(timeout=config.timeout, follow_redirects=False)
        self.downloader_client = httpx.Client(
            timeout=config.download_timeout, headers={"User-Agent": "Jubarte-Live-Bench/0.1"}
        )
        self.publisher = Publisher(config.ingest_url, config.ingest_token, self.client)
        self.tools = RealTools(config, self.client)
        self.stop = threading.Event()
        self.live = {"phase": "starting", "updated_at": now()}
        self.live_lock = threading.Lock()
        self.ready = False
        self.last_error = None
        self.threads: list[threading.Thread] = []

    def start(self):
        for target, name in ((self.loop, "benchmark"), (self.heartbeat, "heartbeat")):
            thread = threading.Thread(target=target, name=name, daemon=True)
            self.threads.append(thread)
            thread.start()

    def set_live(self, **values):
        with self.live_lock:
            self.live.update(
                values,
                updated_at=now(),
                queue_depth=self.state.depth(),
                completed=self.state.get("completed", 0),
            )

    def snapshot(self):
        with self.live_lock:
            return {**self.live, "updated_at": now()}

    def heartbeat(self):
        while not self.stop.is_set():
            health = {
                "timestamp": time.time(),
                "healthy": self.live.get("phase") != "worker-error",
                "ready": self.ready,
                "phase": self.live.get("phase"),
            }
            part = self.config.data_dir / "health.json.part"
            part.write_text(json.dumps(health))
            part.replace(self.config.data_dir / "health.json")
            if self.ready:
                try:
                    self.publisher.post("live", self.snapshot())
                except Exception as exc:
                    LOG.warning("live publication failed: %s", type(exc).__name__)
            self.stop.wait(self.config.heartbeat_seconds)

    def replenish(self):
        # Sampler and queue cursor are persisted under the same DB transaction.
        missing = queue_target(self.config.batch_size) - self.state.depth()
        completed = self.state.get("completed", 0)
        group = None
        if completed:
            group = completed // self.config.batch_size + 1
            if self.state.get("prefetched_group", 0) >= group and self.state.depth():
                return
            missing = self.config.batch_size
        if missing <= 0:
            return
        cursor = self.state.get("sampler", {"cycle": 0, "offset": 0})
        indices, cursor = draw_indices(self.index.height, missing, self.config.seed, **cursor)
        rows = [self.index.row(i, named=True) for i in indices]
        self.state.enqueue(rows, cursor, group)

    def downloads(self):
        while not self.stop.is_set():
            item = self.state.queued_download()
            if item is None:
                self.stop.wait(0.5)
                continue
            sequence, row = item
            doc = download(
                row,
                self.config.data_dir / "fixtures" / f"{sequence}.docx",
                self.downloader_client,
                self.config.max_bytes,
            )
            self.state.downloaded(sequence, serialize_doc(doc))
            LOG.info(
                "download sequence=%s status=%s url=%s bytes=%s",
                sequence,
                "rejected" if doc.security.get("status") == "rejected" else ("ok" if doc.path else "broken"),
                doc.url,
                doc.metadata.get("download_bytes", 0),
            )

    def flush(self) -> bool:
        for entry in self.state.pending():
            try:
                if entry["kind"] == "result":
                    self.publisher.result(
                        entry["payload"], self.config.data_dir / "work" / str(entry["payload"]["sequence"])
                    )
                else:
                    payload = entry["payload"]
                    manifest = self.config.data_dir / "manifests" / f"{payload['id']}.json"
                    contents = json.loads(manifest.read_bytes())
                    for artifact in contents.get("result_parts", []):
                        part = manifest.parent / artifact["key"].rsplit("/", 1)[1]
                        self.publisher.upload(artifact["key"], "application/json", part.read_bytes())
                    self.publisher.upload(payload["manifest_key"], "application/json", manifest.read_bytes())
                    self.publisher.post("batch", payload)
                self.state.acknowledge(entry["id"])
            except Exception as exc:
                self.last_error = f"publication: {type(exc).__name__}"
                LOG.warning("outbox publication failed id=%s: %s", entry["id"], type(exc).__name__)
                return False
        self.last_error = None
        return True

    def finalize(self, completed: int) -> bool:
        size = self.config.batch_size
        if completed == 0 or completed % size:
            return True
        identifier = batch_id(self.run_id, completed, size)
        if self.state.get("finalized", 0) >= completed:
            self.cleanup_finalized()
            return True
        first = completed - size + 1
        results = self.state.batch_results(first, completed)
        if len(results) != size:
            raise RuntimeError("completed group does not have every result in its durable outbox")
        folder = self.config.data_dir / "manifests"
        folder.mkdir(exist_ok=True)
        manifest_key = f"{self.run_id}/{completed}/{identifier}.json"
        for key, data in archive_files(self.run, results, manifest_key).items():
            target = folder / key.rsplit("/", 1)[1]
            part = target.with_suffix(".json.part")
            part.write_bytes(data)
            part.replace(target)
        self.state.put_outbox(
            identifier,
            "batch",
            {
                "id": identifier,
                "run_id": self.run_id,
                "first_sequence": first,
                "last_sequence": completed,
                "count": size,
                "completed_at": results[-1]["completed_at"],
                "manifest_key": manifest_key,
            },
        )
        if not self.flush():
            return False
        self.state.set("finalized", completed)
        self.cleanup_finalized()
        for path in folder.glob(f"{identifier}*.json"):
            path.unlink(missing_ok=True)
        LOG.info("group finalized id=%s count=%s", identifier, size)
        return True

    def cleanup_finalized(self):
        finalized = self.state.get("finalized", 0)
        completed = self.state.get("completed", 0)
        # Repeatable after a crash anywhere between acknowledgement and local pruning.
        self.state.prune_batch(1, finalized)
        for path in (self.config.data_dir / "work").glob("*"):
            if path.name.isdigit() and int(path.name) <= finalized:
                shutil.rmtree(path, ignore_errors=True)
        for path in (self.config.data_dir / "fixtures").glob("*.docx"):
            if path.stem.isdigit() and int(path.stem) < completed and int(path.stem) <= finalized:
                path.unlink(missing_ok=True)

    def loop(self):
        try:
            seed = self.config.data_dir / "starting_point.docx"
            if not seed.exists():
                build_seed(seed)
            self.cleanup_finalized()
            old_revision = self.state.get("corpus_revision")
            self.index, revision = load_index(self.config.index_path, old_revision)
            if old_revision is not None and revision != old_revision:
                raise RuntimeError("corpus revision changed; use the pinned index or a fresh data volume")
            self.state.set("corpus_revision", revision)
            versions = self.tools.versions()
            self.run = self.state.get("run")
            if self.run is not None and (
                self.run["versions"] != versions
                or self.run["config"].get("batch_size") != self.config.batch_size
            ):
                raise RuntimeError("tool versions or group size changed; use a fresh volume for a new run")
            if self.run is None:
                self.run = {
                    "id": str(uuid.uuid7()),
                    "started_at": now(),
                    "versions": versions,
                    "config": {
                        "batch_size": self.config.batch_size,
                        "prefetch_at": self.config.prefetch_at,
                        "seed": self.config.seed,
                        "dpi": self.config.dpi,
                        "dataset": "superdoc-dev/docx-corpus",
                        "corpus_revision": revision,
                        "chain": "previous-sampled-fixture",
                        "sequential": True,
                        "max_fixture_bytes": self.config.max_bytes,
                        "max_file_bytes": MAX_FILE_BYTES,
                    },
                }
                self.state.set("run", self.run)
            self.run_id = self.run["id"]
            while not self.stop.is_set():
                try:
                    self.publisher.post("run", self.run)
                    break
                except Exception as exc:
                    self.last_error = f"register run: {type(exc).__name__}"
                    self.stop.wait(5)
            if self.stop.is_set():
                return
            self.ready = True
            self.set_live(
                run_id=self.run_id,
                sequence=self.state.get("completed", 0) + 1,
                batch_id=batch_id(self.run_id, 1, self.config.batch_size),
                fixture_id="starting_point",
                phase="prefetch",
            )
            self.replenish()
            thread = threading.Thread(target=self.downloads, name="downloader", daemon=True)
            self.threads.append(thread)
            thread.start()
            # The initial two groups are downloaded before the benchmark starts.
            while self.state.queued_download() is not None and not self.stop.is_set():
                self.stop.wait(0.5)
            benchmark = Benchmark(self.tools, time.monotonic, now)
            while not self.stop.is_set():
                completed = self.state.get("completed", 0)
                if not self.finalize(completed):
                    self.set_live(phase="publication-retry")
                    self.stop.wait(5)
                    continue
                if self.config.max_batches and completed >= self.config.max_batches * self.config.batch_size:
                    self.set_live(phase="completed")
                    break
                if completed % self.config.batch_size >= self.config.prefetch_at or self.state.depth() == 0:
                    self.replenish()
                item = self.state.next()
                if item is None:
                    self.set_live(phase="waiting-for-download")
                    self.stop.wait(0.5)
                    continue
                sequence, data = item
                current = restore_doc(data)
                previous_data = self.state.get("previous")
                previous = (
                    restore_doc(previous_data)
                    if previous_data
                    else Document(
                        "starting_point",
                        "generated://starting_point.docx",
                        seed,
                        hashlib.sha256(seed.read_bytes()).hexdigest(),
                    )
                )
                work = self.config.data_dir / "work" / str(sequence)
                # Interrupted fixtures rerun from their original predecessor and clean outputs.
                shutil.rmtree(work, ignore_errors=True)
                work.mkdir(parents=True)
                if current.path:
                    shutil.copyfile(current.path, work / "source.docx")
                if previous.path:
                    shutil.copyfile(previous.path, work / "previous.docx")
                self.set_live(
                    sequence=sequence,
                    batch_id=batch_id(self.run_id, sequence, self.config.batch_size),
                    fixture_id=current.id,
                )
                result = benchmark.run(
                    self.run_id,
                    sequence,
                    self.config.batch_size,
                    previous,
                    current,
                    work,
                    lambda phase: self.set_live(phase=phase),
                )
                self.state.finish(sequence, result, serialize_doc(current))
                self.set_live(phase="publishing")
                self.flush()
                LOG.info(
                    "fixture completed sequence=%s broken=%s",
                    sequence,
                    sum(s["status"] == "broken" for s in result["stages"]),
                )
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"[:1200]
            self.ready = False
            self.set_live(phase="worker-error")
            LOG.exception("worker stopped")


def health_status(data: dict, timestamp: float) -> bool:
    return data.get("healthy") is True and 0 <= timestamp - data.get("timestamp", 0) <= 60


def main():
    parser = argparse.ArgumentParser(description="Jubarte outbound-only continuous DOCX benchmark worker")
    parser.add_argument("--health", action="store_true", help="check local worker health; no inbound port")
    parser.add_argument("--data-dir", default=None)
    args = parser.parse_args()
    if args.health:
        import os

        folder = Path(args.data_dir or os.environ.get("DATA_DIR", "/data"))
        try:
            healthy = health_status(json.loads((folder / "health.json").read_text()), time.time())
        except OSError, ValueError:
            healthy = False
        raise SystemExit(0 if healthy else 1)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    worker = Worker(Config.from_env())
    import signal

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: worker.stop.set())
    worker.start()
    worker.threads[0].join()
    worker.stop.set()
    if worker.last_error and worker.live.get("phase") == "worker-error":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
