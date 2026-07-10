# Frozen reference copy of the ORIGINAL scoring core from
# superdoc-visual-benchmarks (.old/compare/score.py), committed so tests/test_parity.py
# verifies the lifted src/neurotic_docx_bench/score.py stays byte-identical EVEN in CI /
# fresh clones (where the git-ignored .old/ is absent). Do not edit — regenerate only if
# the upstream scoring core is intentionally re-lifted. Provenance: README.
"""Visual similarity scoring for Word vs SuperDoc page renders."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from skimage import color, feature, filters, measure, metrics, morphology, registration, transform


@dataclass(frozen=True)
class ScoreWeights:
    ssim_full: float = 0.25
    ssim_small: float = 0.15
    ink_f1: float = 0.2
    edge_iou: float = 0.15
    color_sim: float = 0.15
    blob_sim: float = 0.1

    def normalized(self) -> ScoreWeights:
        total = sum(asdict(self).values())
        if total <= 0:
            return self
        scale = 1.0 / total
        return ScoreWeights(**{k: v * scale for k, v in asdict(self).items()})


@dataclass(frozen=True)
class ScoreConfig:
    max_shift_px: float = 5.0
    align_upsample: int = 10
    downscale_factor: float = 0.25
    edge_sigma: float = 1.2
    edge_dilate: int = 1
    ink_min_size: int = 24
    ink_tol_px: float = 2.0
    drift_sigma: float = 2.0
    min_drift_px: float = 1.0
    single_issue_cap: float = 30.0
    single_issue_min_gain: float = 15.0
    single_issue_min_ssim_small: float = 0.7
    single_issue_min_ink_f1: float = 0.65
    single_issue_min_edge_iou: float = 0.5
    single_issue_max_blob_penalty: float = 0.03
    color_deltaE_max: float = 20.0
    blob_min_size: int = 40
    weights: ScoreWeights = field(default_factory=ScoreWeights)


def _load_image(path: Path) -> np.ndarray:
    with Image.open(path) as img:
        return np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0


def _resize_image(img: np.ndarray, shape: tuple[int, ...], channel_axis: int | None) -> np.ndarray:
    kwargs = {"order": 1, "preserve_range": True, "anti_aliasing": True}
    if channel_axis is not None:
        kwargs["channel_axis"] = channel_axis
    try:
        resized = transform.resize(img, shape, **kwargs)
    except TypeError:
        kwargs.pop("channel_axis", None)
        resized = transform.resize(img, shape, **kwargs)
    return resized.astype(np.float32)


def _resize_to_match(ref: np.ndarray, img: np.ndarray) -> np.ndarray:
    if ref.shape == img.shape:
        return img
    if img.ndim == 3:
        channel_axis = -1
        target_shape = ref.shape[:2]
    else:
        channel_axis = None
        target_shape = ref.shape
    return _resize_image(img, target_shape, channel_axis)


def _align_images(ref_gray: np.ndarray, mov_gray: np.ndarray, mov_rgb: np.ndarray, config: ScoreConfig) -> np.ndarray:
    shift, _, _ = registration.phase_cross_correlation(ref_gray, mov_gray, upsample_factor=config.align_upsample)
    shift_y, shift_x = float(shift[0]), float(shift[1])
    if abs(shift_x) > config.max_shift_px or abs(shift_y) > config.max_shift_px:
        return mov_rgb
    tform = transform.SimilarityTransform(translation=(-shift_x, -shift_y))
    try:
        aligned = transform.warp(  # type: ignore[call-arg]
            mov_rgb, tform, preserve_range=True, order=1, mode="constant", cval=1.0, channel_axis=-1,  # type: ignore[arg-type]
        )
    except TypeError:
        aligned = transform.warp(mov_rgb, tform, preserve_range=True, order=1, mode="constant", cval=1.0)  # type: ignore[call-arg]
    return aligned.astype(np.float32)


def _ink_mask(gray: np.ndarray, min_size: int) -> np.ndarray:
    try:
        thr = filters.threshold_otsu(gray)
    except ValueError:
        thr = 0.95
    thr = min(thr, 0.95)
    ink = gray < thr
    ink = morphology.remove_small_objects(ink, max_size=min_size)
    return ink


def _edge_mask(gray: np.ndarray, sigma: float) -> np.ndarray:
    return feature.canny(gray, sigma=sigma)


def _f1_with_tolerance(a: np.ndarray, b: np.ndarray, tol_px: float) -> float:
    if a.sum() == 0 and b.sum() == 0:
        return 1.0
    if a.sum() == 0 or b.sum() == 0:
        return 0.0
    dt_b = ndimage.distance_transform_edt(~b)
    dt_a = ndimage.distance_transform_edt(~a)
    match_a = (dt_b <= tol_px) & a
    match_b = (dt_a <= tol_px) & b
    recall = match_a.sum() / a.sum()
    precision = match_b.sum() / b.sum()
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _edge_iou(a: np.ndarray, b: np.ndarray, dilate: int) -> float:
    if a.sum() == 0 and b.sum() == 0:
        return 1.0
    if dilate > 0:
        selem = morphology.disk(dilate)
        a = morphology.dilation(a, selem)
        b = morphology.dilation(b, selem)
    inter = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()
    return inter / union if union else 0.0


def _blob_penalty(mismatch: np.ndarray, ink_union: np.ndarray, min_size: int) -> float:
    mismatch = morphology.remove_small_objects(mismatch, max_size=min_size)
    if mismatch.sum() == 0 or ink_union.sum() == 0:
        return 0.0
    labels = measure.label(mismatch, connectivity=1)
    props = measure.regionprops(labels)
    largest = max((p.area for p in props), default=0)
    return min(1.0, largest / ink_union.sum())


def _delta_e_mean(a_rgb: np.ndarray, b_rgb: np.ndarray, mask: np.ndarray) -> float:
    if mask.sum() == 0:
        return 0.0
    a_lab = color.rgb2lab(a_rgb)
    b_lab = color.rgb2lab(b_rgb)
    delta = color.deltaE_ciede2000(a_lab, b_lab)
    return float(delta[mask].mean())


def _vertical_map_from_ink(
    word_ink: np.ndarray, sd_ink: np.ndarray, config: ScoreConfig,
) -> tuple[np.ndarray | None, float]:
    word_proj = word_ink.sum(axis=1).astype(np.float32)
    sd_proj = sd_ink.sum(axis=1).astype(np.float32)

    if config.drift_sigma > 0:
        word_proj = ndimage.gaussian_filter1d(word_proj, sigma=config.drift_sigma)
        sd_proj = ndimage.gaussian_filter1d(sd_proj, sigma=config.drift_sigma)

    word_total = float(word_proj.sum())
    sd_total = float(sd_proj.sum())
    if word_total == 0 or sd_total == 0:
        return None, 0.0

    word_cdf = np.cumsum(word_proj) / word_total
    sd_cdf = np.cumsum(sd_proj) / sd_total

    sd_cdf_unique, unique_idx = np.unique(sd_cdf, return_index=True)
    if sd_cdf_unique[0] > 0:
        sd_cdf_unique = np.insert(sd_cdf_unique, 0, 0.0)
        unique_idx = np.insert(unique_idx, 0, 0)
    if sd_cdf_unique[-1] < 1.0:
        sd_cdf_unique = np.append(sd_cdf_unique, 1.0)
        unique_idx = np.append(unique_idx, len(sd_cdf) - 1)

    map_y = np.interp(word_cdf, sd_cdf_unique, unique_idx)
    map_y = np.clip(map_y, 0, len(sd_cdf) - 1)
    drift_strength = float(np.mean(np.abs(map_y - np.arange(len(map_y)))))
    if drift_strength < config.min_drift_px:
        return None, drift_strength
    return map_y, drift_strength


def _apply_vertical_map(sd_rgb: np.ndarray, map_y: np.ndarray) -> np.ndarray:
    height, width, _ = sd_rgb.shape
    coords_y = np.repeat(map_y[:, None], width, axis=1)
    coords_x = np.broadcast_to(np.arange(width)[None, :], (height, width))
    coords = np.array([coords_y, coords_x])

    warped = np.empty_like(sd_rgb)
    for channel in range(sd_rgb.shape[2]):
        warped[..., channel] = ndimage.map_coordinates(
            sd_rgb[..., channel], coords, order=1, mode="constant", cval=1.0,
        )
    return warped


def _compute_metrics(word_rgb: np.ndarray, sd_rgb: np.ndarray, config: ScoreConfig) -> dict:
    word_gray = color.rgb2gray(word_rgb)
    sd_gray = color.rgb2gray(sd_rgb)

    ink_word = _ink_mask(word_gray, config.ink_min_size)
    ink_sd = _ink_mask(sd_gray, config.ink_min_size)
    ink_union = np.logical_or(ink_word, ink_sd)

    ssim_full = metrics.structural_similarity(word_gray, sd_gray, data_range=1.0)

    if config.downscale_factor < 1.0:
        small_shape = (
            max(1, int(word_gray.shape[0] * config.downscale_factor)),
            max(1, int(word_gray.shape[1] * config.downscale_factor)),
        )
        word_small = _resize_image(word_gray, small_shape, None)
        sd_small = _resize_image(sd_gray, small_shape, None)
        ssim_small = metrics.structural_similarity(word_small, sd_small, data_range=1.0)
    else:
        ssim_small = ssim_full

    ink_f1 = _f1_with_tolerance(ink_word, ink_sd, config.ink_tol_px)

    edge_word = _edge_mask(word_gray, config.edge_sigma)
    edge_sd = _edge_mask(sd_gray, config.edge_sigma)
    edge_iou = _edge_iou(edge_word, edge_sd, config.edge_dilate)

    mismatch = np.logical_xor(ink_word, ink_sd)
    blob_penalty = _blob_penalty(mismatch, ink_union, config.blob_min_size)
    blob_sim = 1.0 - blob_penalty

    delta_e = _delta_e_mean(word_rgb, sd_rgb, ink_union)
    color_sim = max(0.0, 1.0 - min(delta_e / config.color_deltaE_max, 1.0))

    weights = config.weights.normalized()
    ssim_full = min(max(ssim_full, 0.0), 1.0)
    ssim_small = min(max(ssim_small, 0.0), 1.0)
    ink_f1 = min(max(ink_f1, 0.0), 1.0)
    edge_iou = min(max(edge_iou, 0.0), 1.0)
    color_sim = min(max(color_sim, 0.0), 1.0)
    blob_sim = min(max(blob_sim, 0.0), 1.0)

    score = (
        weights.ssim_full * ssim_full
        + weights.ssim_small * ssim_small
        + weights.ink_f1 * ink_f1
        + weights.edge_iou * edge_iou
        + weights.color_sim * color_sim
        + weights.blob_sim * blob_sim
    )

    return {
        "score": float(score * 100.0),
        "ssim_full": float(ssim_full),
        "ssim_small": float(ssim_small),
        "ink_f1": float(ink_f1),
        "edge_iou": float(edge_iou),
        "color_sim": float(color_sim),
        "delta_e": float(delta_e),
        "blob_penalty": float(blob_penalty),
        "ink_area": int(ink_union.sum()),
    }


def _score_page(word_rgb: np.ndarray, sd_rgb: np.ndarray, config: ScoreConfig) -> dict:
    word_gray = color.rgb2gray(word_rgb)
    sd_gray = color.rgb2gray(sd_rgb)

    sd_aligned = _align_images(word_gray, sd_gray, sd_rgb, config)
    strict_metrics = _compute_metrics(word_rgb, sd_aligned, config)

    sd_aligned_gray = color.rgb2gray(sd_aligned)
    ink_word = _ink_mask(word_gray, config.ink_min_size)
    ink_sd = _ink_mask(sd_aligned_gray, config.ink_min_size)
    map_y, drift_strength = _vertical_map_from_ink(ink_word, ink_sd, config)

    if map_y is not None:
        sd_warped = _apply_vertical_map(sd_aligned, map_y)
        drift_metrics = _compute_metrics(word_rgb, sd_warped, config)
        drift_applied = True
    else:
        drift_metrics = strict_metrics
        drift_applied = False

    improvement = drift_metrics["score"] - strict_metrics["score"]
    single_issue = (
        drift_applied
        and improvement >= config.single_issue_min_gain
        and drift_strength >= config.min_drift_px
        and drift_metrics["ssim_small"] >= config.single_issue_min_ssim_small
        and drift_metrics["ink_f1"] >= config.single_issue_min_ink_f1
        and drift_metrics["edge_iou"] >= config.single_issue_min_edge_iou
        and drift_metrics["blob_penalty"] <= config.single_issue_max_blob_penalty
    )

    if single_issue:
        boost = min(config.single_issue_cap, improvement)
        combined_score = strict_metrics["score"] + boost
    else:
        combined_score = strict_metrics["score"]

    return {
        "score": float(combined_score),
        "score_strict": float(strict_metrics["score"]),
        "score_drift": float(drift_metrics["score"]),
        "single_issue_applied": bool(single_issue),
        "drift_applied": bool(drift_applied),
        "drift_strength_px": float(drift_strength),
        "ssim_full": strict_metrics["ssim_full"],
        "ssim_small": strict_metrics["ssim_small"],
        "ink_f1": strict_metrics["ink_f1"],
        "edge_iou": strict_metrics["edge_iou"],
        "color_sim": strict_metrics["color_sim"],
        "delta_e": strict_metrics["delta_e"],
        "blob_penalty": strict_metrics["blob_penalty"],
        "ink_area": strict_metrics["ink_area"],
        "drift_ssim_full": drift_metrics["ssim_full"],
        "drift_ssim_small": drift_metrics["ssim_small"],
        "drift_ink_f1": drift_metrics["ink_f1"],
        "drift_edge_iou": drift_metrics["edge_iou"],
        "drift_color_sim": drift_metrics["color_sim"],
        "drift_delta_e": drift_metrics["delta_e"],
        "drift_blob_penalty": drift_metrics["blob_penalty"],
    }


def score_document(word_pages: list[Path], jubarte_pages: list[Path], config: ScoreConfig | None = None) -> dict:
    if config is None:
        config = ScoreConfig()

    page_count = min(len(word_pages), len(jubarte_pages))
    if page_count == 0:
        raise RuntimeError("No pages available for scoring.")

    pages = []
    total_weight = 0
    weighted_sum = 0.0
    weighted_sum_strict = 0.0
    weighted_sum_drift = 0.0

    for idx in range(page_count):
        word_img = _load_image(word_pages[idx])
        sd_img = _load_image(jubarte_pages[idx])
        sd_img = _resize_to_match(word_img, sd_img)
        metrics_page = _score_page(word_img, sd_img, config)
        metrics_page["page"] = idx + 1
        pages.append(metrics_page)
        weight = max(metrics_page["ink_area"], 1)
        weighted_sum += metrics_page["score"] * weight
        weighted_sum_strict += metrics_page["score_strict"] * weight
        weighted_sum_drift += metrics_page["score_drift"] * weight
        total_weight += weight

    avg_score = weighted_sum / total_weight if total_weight else 0.0
    avg_score_strict = weighted_sum_strict / total_weight if total_weight else 0.0
    avg_score_drift = weighted_sum_drift / total_weight if total_weight else 0.0
    min_score = min(p["score"] for p in pages)
    min_score_strict = min(p["score_strict"] for p in pages)
    min_score_drift = min(p["score_drift"] for p in pages)
    overall = 0.7 * avg_score + 0.3 * min_score
    overall_strict = 0.7 * avg_score_strict + 0.3 * min_score_strict
    overall_drift = 0.7 * avg_score_drift + 0.3 * min_score_drift

    return {
        "overall_score": float(overall),
        "overall_score_strict": float(overall_strict),
        "overall_score_drift": float(overall_drift),
        "page_count": page_count,
        "average_score": float(avg_score),
        "average_score_strict": float(avg_score_strict),
        "average_score_drift": float(avg_score_drift),
        "min_score": float(min_score),
        "min_score_strict": float(min_score_strict),
        "min_score_drift": float(min_score_drift),
        "pages": pages,
        "config": {**asdict(config), "weights": asdict(config.weights.normalized())},
    }


def format_score_text(score_data: dict) -> str:
    lines = [
        f'overall_score: {score_data["overall_score"]:.2f}',
        f'average_score: {score_data["average_score"]:.2f}',
        f'min_score: {score_data["min_score"]:.2f}',
        f'page_count: {score_data["page_count"]}',
        "",
    ]
    for page in score_data["pages"]:
        lines.append(f'page_{page["page"]:04d}: {page["score"]:.2f}')
    return "\n".join(lines) + "\n"
