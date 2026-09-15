import cv2
import numpy as np

from src.ai_control import auto_play_control as control


def _write_template(path, marker: int) -> None:
    image = np.zeros((6, 6, 3), dtype=np.uint8)
    image[1:5, 1:5] = marker
    image[2:4, 2:4] = marker + 30
    assert cv2.imwrite(str(path), image)


def test_state_reader_returns_the_best_taught_icon(tmp_path) -> None:
    stopped, running = tmp_path / "stopped.png", tmp_path / "running.png"
    _write_template(stopped, 60)
    _write_template(running, 150)
    image = np.zeros((20, 20, 3), dtype=np.uint8)
    image[5:11, 7:13] = cv2.imread(str(running))

    result = control._state_from_templates(
        image,
        {"x1": 0, "y1": 0, "x2": 20, "y2": 20},
        {"stopped": {"path": str(stopped), "threshold": 0.7, "minimumScoreMargin": 0.0},
         "running": {"path": str(running), "threshold": 0.7, "minimumScoreMargin": 0.0}},
    )

    assert result["state"] == "running"
    assert result["scores"]["running"] > result["scores"]["stopped"]


def test_state_reader_rejects_an_icon_below_its_threshold(tmp_path) -> None:
    template = tmp_path / "state.png"
    _write_template(template, 100)
    image = np.zeros((20, 20, 3), dtype=np.uint8)

    result = control._state_from_templates(
        image,
        {"x1": 0, "y1": 0, "x2": 20, "y2": 20},
        {"running": {"path": str(template), "threshold": 0.9}},
    )

    assert result["state"] is None
