"""Shared coordinate helpers for teaching-image matching."""

from __future__ import annotations

from typing import Optional


DEFAULT_COORDINATE_MATCH_OFFSET = 10
MAX_COORDINATE_MATCH_OFFSET = 200


def normalize_coordinate_match_offset(value: object) -> int:
    """Return a coordinate offset constrained to the supported pixel range."""
    try:
        offset = int(value)
    except (TypeError, ValueError):
        offset = DEFAULT_COORDINATE_MATCH_OFFSET
    return max(0, min(offset, MAX_COORDINATE_MATCH_OFFSET))


def expand_coordinate_bounds(
    x1: object,
    y1: object,
    x2: object,
    y2: object,
    offset: object,
    image_width: int,
    image_height: int,
) -> Optional[tuple[int, int, int, int]]:
    """Expand an ROI by offset pixels on every side and clamp it to an image."""
    try:
        left = int(x1)
        top = int(y1)
        right = int(x2)
        bottom = int(y2)
    except (TypeError, ValueError):
        return None

    if right <= left or bottom <= top or image_width <= 0 or image_height <= 0:
        return None

    margin = normalize_coordinate_match_offset(offset)
    left = max(0, min(left - margin, image_width))
    top = max(0, min(top - margin, image_height))
    right = max(left, min(right + margin, image_width))
    bottom = max(top, min(bottom + margin, image_height))
    if right <= left or bottom <= top:
        return None
    return left, top, right, bottom
