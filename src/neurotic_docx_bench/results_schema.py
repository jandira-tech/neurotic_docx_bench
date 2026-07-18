"""Typed benchmark results schema (Task 1 — Standardized Benchmark Results).

Defines :class:`Results`, the canonical JSONL line shape for every vendor×benchmark
pair. Each ``Results`` line is self-contained: aggregate scores + speed stats +
scoring config + environment config, with no embedded alternate-stage maps.

Schema v4 replaces the v3 ``tool``/``stage`` dict lines with ``vendor``/``benchmark``.
"""

from __future__ import annotations

import dataclasses
import statistics
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from neurotic_docx_bench.aggregate import compute_aggregate
from neurotic_docx_bench.benchmarks import BenchmarkName
from neurotic_docx_bench.config import BenchConfig
from neurotic_docx_bench.score import ScoreConfig, ScoreWeights


@dataclass(frozen=True)
class ScoreWeightsMetadata:
    ssim_full: float
    ssim_small: float
    ink_f1: float
    edge_iou: float
    color_sim: float
    blob_sim: float


@dataclass(frozen=True)
class ScoreConfigMetadata:
    max_shift_px: float
    align_upsample: int
    downscale_factor: float
    edge_sigma: float
    edge_dilate: int
    ink_min_size: int
    ink_tol_px: float
    drift_sigma: float
    min_drift_px: float
    single_issue_cap: float
    single_issue_min_gain: float
    single_issue_min_ssim_small: float
    single_issue_min_ink_f1: float
    single_issue_min_edge_iou: float
    single_issue_max_blob_penalty: float
    color_deltaE_max: float
    blob_min_size: int
    weights: ScoreWeightsMetadata


@dataclass(frozen=True)
class SpeedAggregate:
    overall_mean_speed: float
    overall_median_speed: float
    min_speed: float
    max_speed: float
    std_speed: float
    q1_speed: float
    q3_speed: float


@dataclass(frozen=True)
class Results:
    id_run: uuid.UUID
    vendor: str
    benchmark: BenchmarkName
    n_docs: int
    overall_mean: float
    overall_median: float
    exact_100: int
    at_least_90: int
    below_50: int
    min: float
    max: float
    std: float
    q1: float
    q3: float
    page_mean: float | None
    page_median: float | None
    overall_mean_speed: float
    overall_median_speed: float
    min_speed: float
    max_speed: float
    std_speed: float
    q1_speed: float
    q3_speed: float
    score_config: ScoreConfigMetadata
    environment_config: BenchConfig
    scores: dict[str, float] = field(default_factory=dict)
    per_doc: dict[str, dict[str, object]] | None = None
    failures: list[dict[str, str]] = field(default_factory=list)
    timings: dict[str, dict[str, float]] = field(default_factory=dict)
    tool_version: str | None = None
    build_recipe: dict[str, list[str]] | None = None
    config_hash: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.id_run.version != 7:
            raise ValueError(f"id_run must be UUIDv7, got UUIDv{self.id_run.version}")

    def to_json_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


def score_config_metadata(config: ScoreConfig | None = None) -> ScoreConfigMetadata:
    cfg = config or ScoreConfig()
    weights = cfg.weights if isinstance(cfg.weights, ScoreWeights) else ScoreWeights()
    return ScoreConfigMetadata(
        max_shift_px=cfg.max_shift_px,
        align_upsample=cfg.align_upsample,
        downscale_factor=cfg.downscale_factor,
        edge_sigma=cfg.edge_sigma,
        edge_dilate=cfg.edge_dilate,
        ink_min_size=cfg.ink_min_size,
        ink_tol_px=cfg.ink_tol_px,
        drift_sigma=cfg.drift_sigma,
        min_drift_px=cfg.min_drift_px,
        single_issue_cap=cfg.single_issue_cap,
        single_issue_min_gain=cfg.single_issue_min_gain,
        single_issue_min_ssim_small=cfg.single_issue_min_ssim_small,
        single_issue_min_ink_f1=cfg.single_issue_min_ink_f1,
        single_issue_min_edge_iou=cfg.single_issue_min_edge_iou,
        single_issue_max_blob_penalty=cfg.single_issue_max_blob_penalty,
        color_deltaE_max=cfg.color_deltaE_max,
        blob_min_size=cfg.blob_min_size,
        weights=ScoreWeightsMetadata(**asdict(weights)),
    )


def aggregate_speed(samples_ms: list[float]) -> SpeedAggregate:
    values = [float(v) for v in samples_ms]
    if not values:
        return SpeedAggregate(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    q = statistics.quantiles(values, n=4, method="inclusive") if len(values) >= 2 else [values[0]] * 3
    return SpeedAggregate(
        overall_mean_speed=round(statistics.mean(values), 4),
        overall_median_speed=round(statistics.median(values), 4),
        min_speed=round(min(values), 4),
        max_speed=round(max(values), 4),
        std_speed=round(statistics.pstdev(values), 4),
        q1_speed=round(q[0], 4),
        q3_speed=round(q[2], 4),
    )


def build_results(
    *,
    id_run: uuid.UUID,
    vendor: str,
    benchmark: BenchmarkName,
    scores: dict[str, float],
    per_doc: dict[str, dict[str, object]] | None,
    speed_samples_ms: list[float],
    environment_config: BenchConfig,
    timestamp: datetime,
    score_config: ScoreConfig | None = None,
    tool_version: str | None = None,
    build_recipe: dict[str, list[str]] | None = None,
    config_hash: str | None = None,
    failures: list[dict[str, str]] | None = None,
    timings: dict[str, dict[str, float]] | None = None,
) -> Results:
    rounded_scores = {k: round(float(v), 4) for k, v in scores.items()}
    aggregate = compute_aggregate(rounded_scores, per_doc=per_doc)
    speed = aggregate_speed(speed_samples_ms)
    return Results(
        id_run=id_run,
        vendor=vendor,
        benchmark=benchmark,
        n_docs=aggregate.n_docs,
        overall_mean=aggregate.overall_mean,
        overall_median=aggregate.overall_median,
        exact_100=aggregate.exact_100,
        at_least_90=aggregate.at_least_90,
        below_50=aggregate.below_50,
        min=aggregate.min,
        max=aggregate.max,
        std=aggregate.std,
        q1=aggregate.q1,
        q3=aggregate.q3,
        page_mean=aggregate.page_mean,
        page_median=aggregate.page_median,
        **asdict(speed),
        score_config=score_config_metadata(score_config),
        environment_config=environment_config,
        scores=rounded_scores,
        per_doc=per_doc,
        failures=failures or [],
        timings=timings or {},
        tool_version=tool_version,
        build_recipe=build_recipe,
        config_hash=config_hash,
        timestamp=timestamp,
    )


def _jsonable(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if dataclasses.is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value
