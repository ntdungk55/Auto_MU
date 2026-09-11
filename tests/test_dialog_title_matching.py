"""Regression checks for teaching-driven dialog title image verification."""

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from samples.ai_game_controller.domain.game_target import GameTarget
from samples.ai_game_controller.infrastructure.game_state_reader import GameStateReader


ROOT = Path(__file__).resolve().parents[1]
DIALOG = "dialog.character_list.opened"
TARGET = GameTarget("offline", 0, "offline", "offline")


class Capture:
    def __init__(self, frame: np.ndarray) -> None:
        self.frame = frame

    def capture(self, hwnd: int) -> np.ndarray:
        return self.frame


class Recognizer:
    def __init__(self) -> None:
        self.calls = 0

    def recognize(self, image: np.ndarray, timeout_seconds: float | None = None) -> str:
        self.calls += 1
        return "Character List"


@pytest.fixture
def setup_reader(tmp_path: Path) -> tuple[GameStateReader, Capture, Recognizer]:
    payload = json.loads((ROOT / "mcp/config/mu_game_window.json").read_text(encoding="utf-8"))
    config = tmp_path / "teaching.json"
    config.write_text(json.dumps(payload), encoding="utf-8")
    frame = cv2.imread(str(ROOT / "assets/character_list_dialog.png"))
    assert frame is not None
    capture = Capture(frame)
    recognizer = Recognizer()
    return GameStateReader(capture, recognizer, config), capture, recognizer


def test_title_template_matches_without_ocr(setup_reader: tuple) -> None:
    reader, _, recognizer = setup_reader
    assert reader.verify_dynamic_text(TARGET, DIALOG) == "Character List"
    evidence = reader.last_dialog_verification
    assert evidence["method"] == "template_matching"
    assert evidence["score"] >= evidence["threshold"]
    assert evidence["bbox"]["x1"] in range(230, 237)
    assert recognizer.calls == 0


def test_missing_title_is_rejected_without_ocr(setup_reader: tuple) -> None:
    reader, capture, recognizer = setup_reader
    capture.frame = np.zeros((600, 800, 3), dtype=np.uint8)
    assert reader.verify_dynamic_text(TARGET, DIALOG) is None
    assert reader.last_error is None
    assert recognizer.calls == 0


@pytest.mark.parametrize("problem", ["missing_file", "empty_path", "bad_threshold", "small_roi"])
def test_invalid_image_teaching_fails_without_ocr(setup_reader: tuple, problem: str) -> None:
    reader, _, recognizer = setup_reader
    definition = reader._dialogs[DIALOG]
    anchor = definition["layout"]["Anchor"]
    if problem == "missing_file":
        anchor["titleImagePath"] = "assets/does-not-exist.png"
    elif problem == "empty_path":
        anchor["titleImagePath"] = ""
    elif problem == "bad_threshold":
        anchor["templateThreshold"] = 1.5
    else:
        definition["roi"] = {"x1": 0, "y1": 0, "x2": 1, "y2": 1}
    assert reader.verify_dynamic_text(TARGET, DIALOG) is None
    assert reader.last_error
    assert recognizer.calls == 0


def test_title_outside_search_roi_is_rejected(setup_reader: tuple) -> None:
    reader, _, recognizer = setup_reader
    reader._dialogs[DIALOG]["roi"] = {"x1": 0, "y1": 0, "x2": 200, "y2": 100}
    assert reader.verify_dynamic_text(TARGET, DIALOG) is None
    assert reader.last_error is None
    assert recognizer.calls == 0


def test_text_only_teaching_retains_ocr(setup_reader: tuple) -> None:
    reader, _, recognizer = setup_reader
    del reader._dialogs[DIALOG]["layout"]["Anchor"]["titleImagePath"]
    assert reader.verify_dynamic_text(TARGET, DIALOG) == "Character List"
    assert reader.last_dialog_verification["method"] == "ocr"
    assert recognizer.calls == 1


def test_recovery_clears_previous_error(setup_reader: tuple) -> None:
    reader, _, _ = setup_reader
    anchor = reader._dialogs[DIALOG]["layout"]["Anchor"]
    original = anchor["titleImagePath"]
    anchor["titleImagePath"] = "assets/does-not-exist.png"
    assert reader.verify_dynamic_text(TARGET, DIALOG) is None
    anchor["titleImagePath"] = original
    assert reader.verify_dynamic_text(TARGET, DIALOG) == "Character List"
    assert reader.last_error is None


def test_mcp_verification_reports_image_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    from samples.ai_game_controller.infrastructure.easyocr_recognizer import EasyOCRRecognizer
    from samples.ai_game_controller.infrastructure.window_capture import GameWindowCapture
    from src.ai_control.servers.keyboard import _await_dynamic_text

    frame = cv2.imread(str(ROOT / "assets/character_list_dialog.png"))
    assert frame is not None
    monkeypatch.setattr(GameWindowCapture, "capture", lambda self, hwnd: frame)

    def unexpected_ocr(*args: object, **kwargs: object) -> str:
        pytest.fail("Image verification must not invoke OCR")

    monkeypatch.setattr(EasyOCRRecognizer, "recognize", unexpected_ocr)
    result = _await_dynamic_text(0, DIALOG, 1000)
    assert result["success"] is True
    assert result["method"] == "template_matching"
    assert result["score"] >= result["threshold"]
    assert result["matched_label"] == "Character List"
    assert "observed_text" not in result


@pytest.mark.parametrize(
    "asset, expected",
    [("daily_events_dialog.png", "Daily Events"),
     ("character_list_dialog.png", None),
     ("companion_management_dialog.png", None)],
)
def test_daily_events_uses_its_saved_title_only(asset: str, expected: str | None) -> None:
    frame = cv2.imread(str(ROOT / "assets" / asset))
    assert frame is not None
    recognizer = Recognizer()
    reader = GameStateReader(Capture(frame), recognizer, ROOT / "mcp/config/mu_game_window.json")
    assert reader.verify_dynamic_text(TARGET, "dialog.advanced.opened") == expected
    assert reader.last_error is None
    assert reader.last_dialog_verification["method"] == "template_matching"
    assert recognizer.calls == 0
