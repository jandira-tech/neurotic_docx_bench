"""Diff overlay generation for visual comparison."""

from pathlib import Path

from PIL import Image, ImageOps

# Diff overlay colors (RGB)
WORD_DIFF_COLOR = (12, 86, 52)  # Dark teal/green for Word-only content
SUPERDOC_DIFF_COLOR = (160, 0, 0)  # Dark red for SuperDoc-only content
DIFF_MAX_ALPHA = 200
DEFAULT_INK_THRESHOLD = 20


def _tint_overlay_layer(
    img: Image.Image,
    color: tuple[int, int, int],
    max_alpha: int,
    ink_threshold: int,
) -> Image.Image:
    """Create a tinted overlay layer from an image.

    Extracts "ink" (dark content) from the image and tints it with the specified color.

    Args:
        img: Source image.
        color: RGB color tuple for tinting.
        max_alpha: Maximum alpha value for the overlay.
        ink_threshold: Minimum ink intensity to include.

    Returns:
        RGBA image with tinted ink overlay.
    """
    gray = img.convert("L")
    ink = ImageOps.invert(gray)
    if ink_threshold > 0:
        ink = ink.point(lambda x: 0 if x < ink_threshold else x)
    if max_alpha < 255:
        ink = ink.point(lambda x: int(x * max_alpha / 255))
    colored = ImageOps.colorize(ink, black=(0, 0, 0), white=color).convert("RGBA")
    colored.putalpha(ink)
    return colored


def build_diff_overlay(
    word_img: Image.Image,
    superdoc_img: Image.Image,
    ink_threshold: int = DEFAULT_INK_THRESHOLD,
) -> Image.Image:
    """Build a diff overlay showing differences between Word and SuperDoc renders.

    Word-only content is tinted in green, SuperDoc-only content in red.
    Where they match, the colors blend.

    Args:
        word_img: Word rendering image.
        superdoc_img: SuperDoc rendering image.
        ink_threshold: Minimum ink intensity to include in diff.

    Returns:
        RGB image with diff overlay.
    """
    # Ensure same size (resize superdoc to match word if needed)
    if word_img.size != superdoc_img.size:
        superdoc_img = superdoc_img.resize(word_img.size, Image.Resampling.LANCZOS)

    word_layer = _tint_overlay_layer(word_img, WORD_DIFF_COLOR, DIFF_MAX_ALPHA, ink_threshold)
    sd_layer = _tint_overlay_layer(superdoc_img, SUPERDOC_DIFF_COLOR, DIFF_MAX_ALPHA, ink_threshold)

    # Composite on white background
    out = Image.new("RGBA", word_img.size, (255, 255, 255, 255))
    out = Image.alpha_composite(out, word_layer)
    out = Image.alpha_composite(out, sd_layer)

    return out.convert("RGB")


def create_diff_from_files(
    word_path: Path,
    superdoc_path: Path,
    output_path: Path | None = None,
    ink_threshold: int = DEFAULT_INK_THRESHOLD,
) -> Image.Image:
    """Create a diff overlay from image files.

    Args:
        word_path: Path to Word screenshot.
        superdoc_path: Path to SuperDoc screenshot.
        output_path: Optional path to save the diff image.
        ink_threshold: Minimum ink intensity to include in diff.

    Returns:
        RGB diff overlay image.
    """
    word_img = Image.open(word_path)
    superdoc_img = Image.open(superdoc_path)

    diff_img = build_diff_overlay(word_img, superdoc_img, ink_threshold)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        diff_img.save(output_path)

    return diff_img
