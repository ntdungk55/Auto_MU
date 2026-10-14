"""Tests for coordinate matching offset calculations."""

import pytest
import cv2
import numpy as np
from PyQt6.QtWidgets import QApplication

from src.logic.action_type import ActionMode, ActionType, AutoAction
from src.logic.teaching_matching import expand_coordinate_bounds
from src.ui.multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
from src.ui.teaching_algorithm_settings_dialog import TeachingAlgorithmSettingsDialog


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    """Provide one Qt application for settings visibility checks."""
    return QApplication.instance() or QApplication([])


def test_expand_coordinate_bounds_adds_offset_to_each_side() -> None:
    """Offset expands every edge independently."""
    assert expand_coordinate_bounds(100, 80, 200, 160, 10, 800, 600) == (
        90,
        70,
        210,
        170,
    )


def test_expand_coordinate_bounds_clamps_to_image_edges() -> None:
    """Expanded coordinates remain inside the captured image."""
    assert expand_coordinate_bounds(4, 6, 795, 598, 10, 800, 600) == (
        0,
        0,
        800,
        600,
    )


def test_expand_coordinate_bounds_rejects_empty_roi() -> None:
    """Invalid coordinate rectangles do not produce a matching region."""
    assert expand_coordinate_bounds(20, 20, 20, 40, 10, 800, 600) is None


def test_offset_spin_follows_coordinate_checkbox(qapp) -> None:
    """Offset is defaulted to 10px and shown only in coordinate mode."""
    dialog = TeachingAlgorithmSettingsDialog({"match_by_coordinates": False})

    assert dialog.coordinate_offset_spin.value() == 10
    assert dialog.coordinate_offset_widget.isHidden()

    dialog.match_by_coordinates_checkbox.setChecked(True)

    assert not dialog.coordinate_offset_widget.isHidden()
    assert dialog.values() == {
        "match_by_coordinates": True,
        "coordinate_offset": 10,
    }
    dialog.close()
    dialog.deleteLater()
    qapp.processEvents()


def test_coordinate_offset_finds_shifted_teaching_image(qapp, tmp_path) -> None:
    """Coordinate matching searches around the teaching ROI by the offset."""
    rng = np.random.default_rng(42)
    teaching = rng.integers(0, 256, (20, 20, 3), dtype=np.uint8)
    teaching_path = tmp_path / "teaching.png"
    cv2.imwrite(str(teaching_path), teaching)

    capture = np.zeros((100, 100, 3), dtype=np.uint8)
    capture[45:65, 45:65] = teaching
    capture_path = tmp_path / "capture.png"
    cv2.imwrite(str(capture_path), capture)

    action = AutoAction(
        name="Coordinate offset",
        purpose="Test",
        action_type=ActionType.IMAGE_DETECT,
        mode=ActionMode.PASSIVE,
        image_path=str(teaching_path),
    )
    action.multiscale_enabled = False
    action.teaching_match_by_coordinates = True
    action.teaching_match_coordinate_offset = 10
    action.teaching_corner_x1 = 40
    action.teaching_corner_y1 = 40
    action.teaching_corner_x2 = 60
    action.teaching_corner_y2 = 60
    action.teaching_window_width = 100
    action.teaching_window_height = 100

    dialog = MultiImageAlgorithmTestingDialog(action, tool_id="offset-test")
    score, bbox = dialog._test_single_image(str(capture_path), [])

    assert score >= 0.99
    assert bbox is not None
    assert bbox[:2] == (45, 45)
    dialog.close()
    dialog.deleteLater()
    qapp.processEvents()
