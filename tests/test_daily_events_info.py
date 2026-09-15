"""Exercise Daily Events teaching and flow using real images with simulated window/OCR I/O."""

import json
from pathlib import Path

import cv2
import numpy as np
import pytest
import win32gui

from src.ai_control import daily_events_info as daily
from src.ai_control.servers import keyboard
from src.logic.system_executor.ocr_engine import EasyOCREngine
from src.logic.system_executor.mouse_controller import MouseController


ROOT = Path(__file__).resolve().parents[1]
TARGET = {"hwnd": 777, "pid": 123, "title": "MU (Golden - NTD3006)"}


@pytest.fixture
def game(monkeypatch: pytest.MonkeyPatch) -> dict:
    frame = cv2.imread(str(ROOT / "assets/daily_events_ntd3006.png"))
    assert frame is not None
    state = {"frame": frame, "frames": [frame], "keys": [], "captures": [], "ocr_calls": 0,
             "clicks": [], "close_works": True,
             "texts": ["Remaining: 12 times", "Remaining; 3 time", "Remaining: 0 times",
                       "Remaining: 4 times", "Remaining: 1 times"], "confidence": 0.95}

    def capture(self: object, hwnd: int) -> np.ndarray:
        state["captures"].append(hwnd)
        return state["frames"].pop(0) if len(state["frames"]) > 1 else state["frames"][0]

    def send_key(hwnd: int, key: str) -> bool:
        state["keys"].append((hwnd, key))
        return True

    def click(self: object, x: int, y: int) -> None:
        state["clicks"].append((self.target_window_hwnd, x, y))
        if state["close_works"]:
            state["frames"] = [np.zeros_like(frame)]

    class OCR:
        def readtext(self, image: np.ndarray, **kwargs: object) -> list:
            text = state["texts"][state["ocr_calls"]]
            state["ocr_calls"] += 1
            return [([[0, 0], [10, 0], [10, 10], [0, 10]], text, state["confidence"])]

    monkeypatch.setattr(daily.GameWindowCapture, "capture", capture)
    monkeypatch.setattr(MouseController, "click_at_client", click)
    monkeypatch.setattr(EasyOCREngine, "_get_reader", lambda self: OCR())
    monkeypatch.setattr(win32gui, "IsWindow", lambda hwnd: hwnd == 777)
    monkeypatch.setattr(win32gui, "IsWindowVisible", lambda hwnd: hwnd == 777)
    monkeypatch.setattr(keyboard, "_selected_visible_windows", lambda: ([TARGET], None))
    monkeypatch.setattr(keyboard, "_wake_selected_window", lambda target: {
        "success": True, "method": "background_center_click", "hwnd": 777,
        "x": 400, "y": 300, "focus_requested": False, "key_sent": False, "delay_ms": 0,
    })
    monkeypatch.setattr(keyboard, "_post_single_key", send_key)
    return state


@pytest.mark.parametrize("already_open", [True, False])
def test_tool_reads_five_dynamic_counts_and_preserves_zero(game: dict, already_open: bool) -> None:
    if not already_open:
        game["frames"] = [np.zeros_like(game["frame"]), game["frame"]]
    result = keyboard.get_daily_events_dialog_info()
    assert result["success"] is True
    assert result["remaining"] == {"boss": 12, "jewel": 3, "bc": 0, "devil": 4, "ig": 1}
    assert result["fields"]["boss"]["roi"] == {"x1": 338, "y1": 227, "x2": 436, "y2": 241}
    assert result["fields"]["bc"]["roi"]["y1"] == 371
    assert game["keys"] == ([] if already_open else [(777, "s")])
    assert game["ocr_calls"] == 5 and set(game["captures"]) == {777}
    assert game["clicks"] == [(777, 751, 171)]
    assert result["dialog_close"]["closed"] is True


def test_counters_follow_moved_title(game: dict) -> None:
    game["frames"] = [cv2.warpAffine(game["frame"], np.float32([[1, 0, -100], [0, 1, -30]]), (800, 600))]
    result = keyboard.get_daily_events_dialog_info()
    assert result["success"] is True
    assert result["fields"]["boss"]["roi"] == {"x1": 238, "y1": 197, "x2": 336, "y2": 211}
    assert not game["keys"]
    assert game["clicks"] == [(777, 651, 141)]
    assert result["dialog_close"]["closed"] is True


@pytest.mark.parametrize("bad_text", ["", "Remaining: ? times", "Remaining: 4 times 8 times", "Remaining: -1 times"])
def test_missing_or_ambiguous_count_returns_partial_failure(game: dict, bad_text: str) -> None:
    game["texts"][1] = bad_text
    result = keyboard.get_daily_events_dialog_info()
    assert result["success"] is False
    assert result["remaining"]["jewel"] is None
    assert result["remaining"]["boss"] == 12
    assert result["missing_fields"] == ["jewel"]
    assert game["clicks"] == [(777, 751, 171)]
    assert result["dialog_close"]["closed"] is True


def test_low_confidence_does_not_invent_counts(game: dict) -> None:
    game["confidence"] = 0.1
    result = keyboard.get_daily_events_dialog_info()
    assert result["success"] is False
    assert all(value is None for value in result["remaining"].values())


@pytest.mark.parametrize("ocr_text", ["Remaining: 34 times|", "Remaining: 35 tmes"])
def test_boss_counter_accepts_known_easyocr_suffix_noise(game: dict, ocr_text: str) -> None:
    game["texts"][0] = ocr_text
    game["confidence"] = 0.64

    result = keyboard.get_daily_events_dialog_info()

    assert result["success"] is True
    assert result["remaining"]["boss"] == int(ocr_text.split()[1])


def test_wrong_dialog_never_reads_counters(game: dict) -> None:
    game["frames"] = [cv2.imread(str(ROOT / "assets/character_list_dialog.png"))]
    result = daily.get_daily_events_dialog_info(TARGET, send_key=keyboard._post_single_key, dialog_timeout_seconds=0.05)
    assert result["success"] is False
    assert game["keys"] == [(777, "s")] and game["ocr_calls"] == 0
    assert not game["clicks"]


def test_key_failure_never_reads_counters(game: dict) -> None:
    game["frames"] = [np.zeros_like(game["frame"])]
    result = daily.get_daily_events_dialog_info(TARGET, send_key=lambda hwnd, key: False)
    assert result["success"] is False and game["ocr_calls"] == 0
    assert not game["clicks"]


def test_invalid_roi_is_reported_without_losing_other_values(game: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = json.loads(daily.TEACHING_PATH.read_text(encoding="utf-8-sig"))
    config["dialogs"]["dialog.advanced.opened"]["layout"]["textRegions"]["ig"]["roiRelativeToTitle"]["x2"] = 900
    path = tmp_path / "teaching.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(daily, "TEACHING_PATH", path)
    result = keyboard.get_daily_events_dialog_info()
    assert result["success"] is False
    assert result["missing_fields"] == ["ig"] and game["ocr_calls"] == 4


@pytest.mark.parametrize("windows,error", [([], "Select a game window"), ([TARGET, TARGET], None)])
def test_invalid_target_never_touches_game(game: dict, monkeypatch: pytest.MonkeyPatch, windows: list, error: str | None) -> None:
    monkeypatch.setattr(keyboard, "_selected_visible_windows", lambda: (windows, error))
    assert keyboard.get_daily_events_dialog_info()["success"] is False
    assert not game["keys"] and not game["captures"]


def test_close_failure_preserves_read_counters(game: dict) -> None:
    game["close_works"] = False
    result = daily.get_daily_events_dialog_info(TARGET, send_key=keyboard._post_single_key, close_timeout_seconds=0.05)
    assert result["success"] is False
    assert result["remaining"]["boss"] == 12
    assert result["dialog_close"]["closed"] is False
    assert game["clicks"] == [(777, 751, 171)]


def test_unavailable_ocr_still_closes(game: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(EasyOCREngine, "_get_reader", lambda self: None)
    result = keyboard.get_daily_events_dialog_info()
    assert result["success"] is False and "EasyOCR is unavailable" in result["error"]
    assert result["dialog_close"]["closed"] is True
    assert game["clicks"] == [(777, 751, 171)]


def test_missing_capture_does_not_confirm_closure(game: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    def click(self: object, x: int, y: int) -> None:
        game["frames"] = [None]

    monkeypatch.setattr(MouseController, "click_at_client", click)
    result = daily.get_daily_events_dialog_info(TARGET, send_key=keyboard._post_single_key, close_timeout_seconds=0.05)
    assert result["success"] is False
    assert result["dialog_close"]["closed"] is False
    assert result["remaining"]["boss"] == 12


def test_dialog_already_closed_does_not_send_extra_click(game: dict) -> None:
    game["frames"] = [game["frame"], np.zeros_like(game["frame"])]
    result = keyboard.get_daily_events_dialog_info()
    assert result["success"] is True and result["dialog_close"]["closed"] is True
    assert result["dialog_close"]["click_sent"] is False and not game["clicks"]
