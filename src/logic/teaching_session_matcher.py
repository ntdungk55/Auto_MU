"""Shared coordinate-aware matching for saved Teaching Algorithm sessions."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from .teaching_matching import expand_coordinate_bounds, normalize_coordinate_match_offset


DEFAULT_MATCH_THRESHOLD = 0.70


def load_teaching_session(project_root: Path, session_id: str) -> dict[str, Any]:
    """Load and validate one saved Teaching Algorithm session."""
    normalized_id = str(session_id or "").strip()
    if not normalized_id:
        raise ValueError("Missing trainingTeachingSessionId")
    if Path(normalized_id).name != normalized_id or normalized_id in {".", ".."}:
        raise ValueError("Invalid trainingTeachingSessionId")

    sessions_root = (
        Path(project_root) / "assets" / "teaching" / "algorithm_tests"
    ).resolve()
    session_dir = (sessions_root / normalized_id).resolve()
    try:
        session_dir.relative_to(sessions_root)
    except ValueError as exc:
        raise ValueError("Teaching session lies outside the configured data folder") from exc

    metadata_path = session_dir / "session.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise FileNotFoundError(f"Could not read Teaching session: {metadata_path}") from exc
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid Teaching session JSON: {metadata_path}") from exc
    if not isinstance(metadata, dict):
        raise ValueError("Teaching session JSON must contain an object")

    matching_method = str(metadata.get("matching_method") or "template").strip()
    if matching_method != "template":
        raise ValueError(
            f"Unsupported Teaching matching method for runtime: {matching_method}"
        )

    teaching_name = str(metadata.get("teaching_image") or "").strip()
    if not teaching_name:
        raise ValueError("Teaching session does not define teaching_image")
    teaching_path = (session_dir / teaching_name).resolve()
    try:
        teaching_path.relative_to(session_dir)
    except ValueError as exc:
        raise ValueError("Teaching image lies outside its session folder") from exc
    if not teaching_path.is_file():
        raise FileNotFoundError(f"Teaching image does not exist: {teaching_path}")

    teaching_metadata = metadata.get("teaching_metadata")
    if not isinstance(teaching_metadata, dict):
        raise ValueError("Teaching session does not contain valid teaching_metadata")
    algorithms = metadata.get("algorithms", [])
    if not isinstance(algorithms, list):
        raise ValueError("Teaching session algorithms must be a list")

    try:
        threshold = float(metadata.get("match_threshold", DEFAULT_MATCH_THRESHOLD))
    except (TypeError, ValueError) as exc:
        raise ValueError("Teaching match_threshold must be numeric") from exc
    if not math.isfinite(threshold) or not 0.01 <= threshold <= 1.0:
        raise ValueError("Teaching match_threshold must be between 0.01 and 1.00")

    return {
        "session_id": normalized_id,
        "session_dir": session_dir,
        "template_path": teaching_path,
        "matching_method": matching_method,
        "match_by_coordinates": bool(metadata.get("match_by_coordinates", False)),
        "coordinate_offset": normalize_coordinate_match_offset(
            metadata.get("coordinate_offset")
        ),
        "match_threshold": threshold,
        "algorithms": algorithms,
        "teaching_metadata": teaching_metadata,
    }


def match_teaching_config_against_image(
    image_bgr: np.ndarray,
    *,
    template_path: str | Path,
    algorithms: list[dict[str, Any]] | None,
    teaching_metadata: dict[str, Any] | None,
    match_by_coordinates: bool,
    coordinate_offset: object,
    match_threshold: object,
    matching_method: str = "template",
    multiscale_enabled: bool = True,
    multiscale_min: float = 0.70,
    multiscale_max: float = 1.30,
    multiscale_step: float = 0.05,
    mask_regions: list | None = None,
    suppress_ui_log: bool = False,
) -> dict[str, Any]:
    """Match using the same preprocessing and coordinate rules in UI and runtime."""
    if image_bgr is None or not isinstance(image_bgr, np.ndarray) or image_bgr.size == 0:
        raise ValueError("Window image is empty")
    if str(matching_method or "template") != "template":
        raise ValueError(
            f"Unsupported Teaching matching method for runtime: {matching_method}"
        )

    template = Path(template_path)
    if not template.is_file():
        raise FileNotFoundError(f"Teaching image does not exist: {template}")
    metadata = teaching_metadata if isinstance(teaching_metadata, dict) else {}
    try:
        threshold = float(match_threshold)
    except (TypeError, ValueError) as exc:
        raise ValueError("Teaching match_threshold must be numeric") from exc
    if not math.isfinite(threshold) or not 0.01 <= threshold <= 1.0:
        raise ValueError("Teaching match_threshold must be between 0.01 and 1.00")

    image_height, image_width = image_bgr.shape[:2]
    search_bounds = (0, 0, image_width, image_height)
    if match_by_coordinates:
        search_bounds = expand_coordinate_bounds(
            metadata.get("corner_x1"),
            metadata.get("corner_y1"),
            metadata.get("corner_x2"),
            metadata.get("corner_y2"),
            coordinate_offset,
            image_width,
            image_height,
        )
        if not search_bounds:
            raise ValueError("Teaching coordinates are missing or invalid")

    left, top, right, bottom = search_bounds
    search_image = image_bgr[top:bottom, left:right]
    if search_image.size == 0:
        raise ValueError("Teaching search ROI is empty")

    from .system_executor.system_executor import SystemExecutor

    coordinate_mode = bool(match_by_coordinates)
    target_width = (
        search_image.shape[1]
        if coordinate_mode
        else int(metadata.get("window_width") or image_width)
    )
    target_height = (
        search_image.shape[0]
        if coordinate_mode
        else int(metadata.get("window_height") or image_height)
    )
    executor = SystemExecutor(
        target_window_hwnd=None,
        # The headless Window State MCP server must not print Vietnamese UI
        # messages to its legacy console encoding.
        ui_log_func=(lambda _message: None) if suppress_ui_log else None,
    )
    image_result, raw_score = executor.match_template_against_image_with_score_adaptive(
        screenshot_bgr=search_image,
        template_path=str(template),
        threshold=0.0,
        ignore_text=False,
        multiscale_enabled=bool(multiscale_enabled),
        multiscale_min=float(multiscale_min),
        multiscale_max=float(multiscale_max),
        multiscale_step=float(multiscale_step),
        mask_regions=mask_regions,
        preprocessing_algorithms=list(algorithms or []),
        teaching_window_width=target_width,
        teaching_window_height=target_height,
    )

    score = float(raw_score or 0.0)
    if not math.isfinite(score):
        score = 0.0
    score = max(0.0, min(1.0, score))
    bbox = None
    if image_result and len(image_result) >= 4:
        x, y, width, height = image_result[:4]
        bbox = (
            int(x) + left,
            int(y) + top,
            int(width),
            int(height),
        )

    return {
        "matched": score >= threshold,
        "score": score,
        "threshold": threshold,
        "bbox": bbox,
        "roi": {
            "x1": int(left),
            "y1": int(top),
            "x2": int(right),
            "y2": int(bottom),
        },
        "coordinate_offset": (
            normalize_coordinate_match_offset(coordinate_offset)
            if coordinate_mode
            else 0
        ),
    }


def match_teaching_session_against_image(
    image_bgr: np.ndarray,
    *,
    project_root: Path,
    session_id: str,
) -> dict[str, Any]:
    """Load a saved session and match it against one captured game-window image."""
    session = load_teaching_session(project_root, session_id)
    result = match_teaching_config_against_image(
        image_bgr,
        template_path=session["template_path"],
        algorithms=session["algorithms"],
        teaching_metadata=session["teaching_metadata"],
        match_by_coordinates=session["match_by_coordinates"],
        coordinate_offset=session["coordinate_offset"],
        match_threshold=session["match_threshold"],
        matching_method=session["matching_method"],
        suppress_ui_log=True,
    )
    result["session_id"] = session["session_id"]
    return result
