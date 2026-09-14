"""Exercise companion tools with real teaching and simulated game I/O."""

from pathlib import Path

import cv2
import numpy as np
import pytest
import win32gui

from samples.ai_game_controller.infrastructure.window_capture import GameWindowCapture
from src.ai_control import companion_summoner as summoner
from src.ai_control import companion_switcher as switcher
from src.ai_control import companion_info
from src.ai_control.servers import keyboard
from src.logic.system_executor.mouse_controller import MouseController
from src.logic.system_executor.ocr_engine import EasyOCREngine, WinRTOCREngine


ROOT = Path(__file__).resolve().parents[1]
TARGET = {"hwnd": 777, "pid": 123, "title": "MU GamethuVN - Season 21 (Golden - NTD1007)"}


@pytest.fixture
def game(monkeypatch: pytest.MonkeyPatch) -> dict:
    unsummoned = np.zeros((600, 800, 3), dtype=np.uint8)
    icon = cv2.imread(str(ROOT / "assets/companion_management1_not_summoned.png"))
    assert icon is not None
    unsummoned[529:562, 640:672] = icon
    character_list = cv2.imread(str(ROOT / "assets/character_list_dialog.png"))
    management = cv2.imread(str(ROOT / "assets/companion_management_dialog.png"))
    assert character_list is not None and management is not None
    summoned = np.zeros((600, 800, 3), dtype=np.uint8)
    summoned[529:562, 640:672] = management[529:562, 640:672]
    state = {
        "unsummoned": unsummoned, "summoned": summoned,
        "character_list": character_list, "management": management,
        "frames": [], "clicks": [], "captures": [], "ocr_calls": 0, "close_works": True,
        "items": [([[10, 10], [70, 10], [70, 30], [10, 30]], "NTD3001", 0.99)],
    }

    def capture(self: object, hwnd: int) -> np.ndarray:
        state["captures"].append(hwnd)
        if len(state["frames"]) > 1:
            return state["frames"].pop(0)
        return state["frames"][0]

    def click(self: object, x: int, y: int) -> None:
        state["clicks"].append((x, y))
        if (x, y) in ((423, 37), (761, 114), (581, 144)) and state["close_works"]:
            state["frames"] = [state["summoned"]]

    class OCR:
        def readtext(self, image: np.ndarray, **kwargs: object) -> list:
            state["ocr_calls"] += 1
            return state["items"]

    monkeypatch.setattr(GameWindowCapture, "capture", capture)
    monkeypatch.setattr(MouseController, "click_at_client", click)
    monkeypatch.setattr(EasyOCREngine, "_get_reader", lambda self: OCR())
    values = iter(["NTD3001", "19", "Loren Market (233,30)", "0.mt (0.000%)", "137.rs", "Waiting for control"])
    monkeypatch.setattr(WinRTOCREngine, "recognize", lambda self, image: next(values))
    monkeypatch.setattr(win32gui, "IsWindow", lambda hwnd: hwnd == TARGET["hwnd"])
    monkeypatch.setattr(win32gui, "IsWindowVisible", lambda hwnd: hwnd == TARGET["hwnd"])
    monkeypatch.setattr(keyboard, "_selected_visible_windows", lambda: ([dict(TARGET)], None))
    monkeypatch.setattr(keyboard, "_wake_selected_window", lambda target: {
        "success": True, "method": "background_center_click", "hwnd": TARGET["hwnd"],
        "x": 400, "y": 300, "focus_requested": False, "key_sent": False, "delay_ms": 0,
    })
    return state


def test_summon_tool_selects_unique_ocr_name_and_confirms_icon(game: dict) -> None:
    game["frames"] = [game["unsummoned"], game["character_list"], game["summoned"]]
    result = keyboard.summon_companion_character("ntd3001")
    assert result["success"] is True
    assert result["selected_character"]["text"] == "NTD3001"
    assert result["before_companion_state"]["companion_summoned"] is False
    assert result["after_companion_state"]["companion_summoned"] is True
    assert game["clicks"][0] == (656, 545)
    assert len(game["clicks"]) == 2
    assert game["ocr_calls"] == 1
    assert set(game["captures"]) == {TARGET["hwnd"]}


@pytest.mark.parametrize("duplicate", [False, True])
def test_unmatched_or_ambiguous_name_closes_dialog(game: dict, duplicate: bool) -> None:
    game["frames"] = [game["unsummoned"], game["character_list"]]
    game["items"] = game["items"] * 2 if duplicate else []
    result = keyboard.summon_companion_character("NTD3001")
    assert result["success"] is False
    assert result["dialog_close_requested"] is True
    assert "selected_character" not in result
    assert len(game["clicks"]) == 2
    assert game["clicks"][-1] == (result["close_button"]["click_x"], result["close_button"]["click_y"])


def test_unmatched_name_does_not_close_from_stale_title(game: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    game["frames"] = [game["unsummoned"], game["character_list"]]
    game["items"] = []

    class OCR:
        def readtext(self: object, image: np.ndarray, **kwargs: object) -> list:
            game["ocr_calls"] += 1
            game["frames"] = [game["summoned"]]
            return []

    monkeypatch.setattr(EasyOCREngine, "_get_reader", lambda self: OCR())
    result = keyboard.summon_companion_character("NTD3001")
    assert result["success"] is False
    assert result["dialog_close_requested"] is False
    assert result["close_button"]["click_sent"] is False
    assert game["clicks"] == [(656, 545)]


def test_already_summoned_prevents_clicks(game: dict) -> None:
    game["frames"] = [game["summoned"]]
    result = keyboard.summon_companion_character("NTD3001")
    assert result["success"] is False
    assert "already summoned" in result["error"]
    assert not game["clicks"]
    assert game["ocr_calls"] == 0


def test_shifted_empty_slot_is_detected_before_click(game: dict) -> None:
    frame = np.zeros((602, 800, 3), dtype=np.uint8)
    icon = cv2.imread(str(ROOT / "assets/companion_management1_not_summoned.png"))
    frame[533:566, 640:672] = icon
    game["frames"] = [frame]
    state = switcher.get_companion_summoned_state(TARGET["hwnd"])
    assert state["companion_summoned"] is False
    assert state["companion_state"] == "not_summoned"
    assert state["not_summoned_icon_score"] >= state["not_summoned_threshold"]
    result = switcher.open_companion_management_dialog(TARGET)
    assert result["success"] is False
    assert not game["clicks"]


def test_ambiguous_slot_state_refuses_to_click(game: dict) -> None:
    template = cv2.imread(str(ROOT / "assets/companion_management1_not_summoned.png"), cv2.IMREAD_GRAYSCALE)
    noise = np.random.default_rng(7).integers(0, 256, template.shape, dtype=np.uint8)
    blend = np.clip(0.64 * template.astype(np.float32) + 0.36 * noise, 0, 255).astype(np.uint8)
    frame = np.zeros((600, 800, 3), dtype=np.uint8)
    frame[529:562, 640:672] = cv2.cvtColor(blend, cv2.COLOR_GRAY2BGR)
    game["frames"] = [frame]
    state = switcher.get_companion_summoned_state(TARGET["hwnd"])
    assert state["companion_summoned"] is None
    assert state["companion_state"] == "unknown"
    result = switcher.open_companion_management_dialog(TARGET)
    assert result["success"] is False
    assert "uncertain" in result["error"]
    assert not game["clicks"]


def test_occluded_slot_refuses_to_click(game: dict) -> None:
    frame = np.zeros((602, 800, 3), dtype=np.uint8)
    frame[523:568, 634:678] = (25, 80, 140)
    game["frames"] = [frame]
    state = switcher.get_companion_summoned_state(TARGET["hwnd"])
    assert state["companion_summoned"] is None
    assert state["companion_state"] == "unknown"
    result = switcher.open_companion_management_dialog(TARGET)
    assert result["success"] is False
    assert "uncertain" in result["error"]
    assert not game["clicks"]


def test_indicator_without_bright_character_icon_refuses_to_click(game: dict) -> None:
    frame = np.zeros((600, 800, 3), dtype=np.uint8)
    indicator = cv2.imread(str(ROOT / "assets/companion_summoned_play_indicator.png"))
    assert indicator is not None
    frame[529:542, 640:652] = indicator
    game["frames"] = [frame]
    state = switcher.get_companion_summoned_state(TARGET["hwnd"])
    assert state["companion_summoned"] is None
    assert state["companion_state"] == "unknown"
    assert any(sample["matched"] for sample in state["summoned_indicator_samples"])
    assert not any(sample["brightness_matched"] for sample in state["summoned_indicator_samples"])
    result = switcher.open_companion_management_dialog(TARGET)
    assert result["success"] is False
    assert not game["clicks"]


def test_dimmed_low_power_character_icon_is_still_verified(game: dict) -> None:
    dimmed = cv2.convertScaleAbs(game["summoned"], alpha=0.5, beta=0)
    game["frames"] = [dimmed]
    state = switcher.get_companion_summoned_state(TARGET["hwnd"])
    assert state["companion_summoned"] is True
    assert state["companion_state"] == "summoned"
    assert all(sample["low_power_matched"] for sample in state["summoned_indicator_samples"])


def test_icon_must_change_before_reporting_success(game: dict) -> None:
    game["frames"] = [game["unsummoned"], game["character_list"], game["unsummoned"]]
    result = summoner.summon_companion_character(TARGET, "NTD3001", verify_timeout_seconds=0.1)
    assert result["success"] is False
    assert result["after_companion_state"] is None
    assert len(game["clicks"]) == 2


def test_absent_title_prevents_character_selection(game: dict) -> None:
    game["frames"] = [game["unsummoned"]]
    result = summoner.summon_companion_character(TARGET, "NTD3001", dialog_timeout_seconds=0.1)
    assert result["success"] is False
    assert game["clicks"] == [(656, 545)]
    assert game["ocr_calls"] == 0


def test_open_management_tool_verifies_then_closes_dialog(game: dict) -> None:
    game["frames"] = [game["summoned"], game["management"]]
    result = keyboard.open_companion_management_dialog()
    assert result["success"] is True
    assert result["verification"]["method"] == "template_matching"
    assert game["clicks"] == [(656, 545), (423, 37)]
    assert result["dialog_close"]["closed"] is True
    assert game["ocr_calls"] == 0


def test_open_management_close_failure_returns_failure(game: dict) -> None:
    game["frames"] = [game["summoned"], game["management"]]
    game["close_works"] = False
    result = switcher.verify_and_close_companion_management_dialog(TARGET, close_timeout_seconds=0.1)
    assert result["success"] is False
    assert result["verification"]["success"] is True
    assert result["dialog_close"]["closed"] is False
    assert game["clicks"] == [(656, 545), (423, 37)]


def test_switch_still_enters_and_verifies_title(game: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    game["frames"] = [game["summoned"], game["management"]]
    titles = iter(["MU (Golden - NTD1007)", "MU (Golden - NTD3005)"])
    monkeypatch.setattr(win32gui, "GetWindowText", lambda hwnd: next(titles))
    result = keyboard.switch_to_companion_character()
    assert result["success"] is True
    assert game["clicks"] == [(656, 545), (276, 254)]


def test_read_state_tool_never_clicks(game: dict) -> None:
    game["frames"] = [game["unsummoned"]]
    result = keyboard.get_companion_summoned_state()
    assert result["success"] is True
    assert result["companion_summoned"] is False
    assert result["character"] is None
    assert not game["clicks"]


@pytest.mark.parametrize("already_open", [False, True])
def test_info_tool_reads_six_fields_from_verified_dialog(game: dict, already_open: bool) -> None:
    frame = cv2.imread(str(ROOT / "assets/companion_management_ntd3006.png"))
    game["frames"] = [frame] if already_open else [game["summoned"], game["summoned"], frame]
    result = keyboard.get_companion_summoned_state()
    assert result["success"] is True
    assert result["character"] == {
        "name": "NTD3001", "server": "19", "map": "Loren Market (233,30)",
        "level": "0.mt", "reset": "137.rs", "status": "Waiting for control",
    }
    assert game["clicks"] == ([(761, 114)] if already_open else [(656, 545), (761, 114)])
    assert result["dialog_close"]["closed"] is True
    assert result["fields"]["name"]["roi"] == {"x1": 652, "y1": 157, "x2": 779, "y2": 171}
    assert set(game["captures"]) == {777}


def test_info_missing_dialog_never_reads_ocr(game: dict) -> None:
    game["frames"] = [game["summoned"]]
    result = companion_info.get_companion_information(TARGET, dialog_timeout_seconds=0.1)
    assert result["success"] is False
    assert game["ocr_calls"] == 0
    assert game["clicks"] == [(656, 545)]


def test_info_missing_ocr_returns_partial_failure(game: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    game["frames"] = [cv2.imread(str(ROOT / "assets/companion_management_ntd3006.png"))]
    monkeypatch.setattr(WinRTOCREngine, "recognize", lambda self, image: "")
    game["items"] = []
    result = keyboard.get_companion_summoned_state()
    assert result["success"] is False
    assert result["selection_required"] is False
    assert set(result["missing_fields"]) == {"name", "server", "map", "level", "reset", "status"}
    assert all(value is None for value in result["character"].values())
    assert game["clicks"] == [(761, 114)]
    assert result["dialog_close"]["closed"] is True


def test_info_regions_follow_moved_title(game: dict) -> None:
    frame = cv2.imread(str(ROOT / "assets/companion_management_ntd3006.png"))
    moved = cv2.warpAffine(frame, np.float32([[1, 0, -180], [0, 1, 30]]), (800, 596))
    game["frames"] = [moved]
    result = keyboard.get_companion_summoned_state()
    assert result["success"] is True
    assert result["fields"]["name"]["roi"] == {"x1": 472, "y1": 187, "x2": 599, "y2": 201}
    assert game["clicks"] == [(581, 144)]
    assert result["dialog_close"]["closed"] is True


def test_info_ocr_fallback_and_numeric_level_correction(game: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    game["frames"] = [cv2.imread(str(ROOT / "assets/companion_management_ntd3006.png"))]
    values = iter(["NTD3001", "19", "Loren Market (233,30)", "o.mt (0.000%)", "", "Waiting for control"])
    monkeypatch.setattr(WinRTOCREngine, "recognize", lambda self, image: next(values))
    game["items"] = [([[0, 0], [10, 0], [10, 10], [0, 10]], "137.rs", 0.9)]
    result = keyboard.get_companion_summoned_state()
    assert result["success"] is True
    assert result["character"]["reset"] == "137.rs"
    assert result["fields"]["reset"]["method"] == "easyocr"
    assert result["character"]["level"] == "0.mt"
    assert result["fields"]["level"]["raw_text"] == "o.mt (0.000%)"
    assert game["ocr_calls"] == 1


def test_info_uses_taught_scale_and_digit_allowlist_for_small_fields(
    game: dict, monkeypatch: pytest.MonkeyPatch,
) -> None:
    game["frames"] = [cv2.imread(str(ROOT / "assets/companion_management_ntd3006.png"))]
    values = iter(["NTD3001", "", "Loren Market (233,30)", "", "137.rs", "Waiting for control"])
    monkeypatch.setattr(WinRTOCREngine, "recognize", lambda self, image: next(values))
    requests: list[dict] = []

    class OCR:
        def readtext(self, image: np.ndarray, **kwargs: object) -> list:
            requests.append({"shape": image.shape[:2], "options": kwargs})
            text = "6" if kwargs.get("allowlist") else "O.mt (0.000%)"
            return [([[0, 0], [10, 0], [10, 10], [0, 10]], text, 0.99)]

    monkeypatch.setattr(EasyOCREngine, "_get_reader", lambda self: OCR())
    result = keyboard.get_companion_summoned_state()
    assert result["success"] is True
    assert result["character"]["server"] == "6"
    assert result["character"]["level"] == "0.mt"
    assert requests[0]["options"]["allowlist"] == "0123456789"
    assert requests[0]["shape"] == (112, 572)
    assert "allowlist" not in requests[1]["options"]
    assert requests[1]["shape"] == (116, 572)


@pytest.mark.parametrize(
    ("field", "raw", "expected"),
    [
        ("server", "Imp", None),
        ("server", "19", "19"),
        ("map", "Kanturu (144146j¯", None),
        ("map", "Kanturu (144.146)", "Kanturu (144,146)"),
        ("level", "0.mt (0.000%Y1 OT Dinorari", "0.mt"),
        ("level", "0.mt (0.000%)Y1 OT Dinorari", "0.mt"),
        ("level", "347.1v (56.42%)", "347.lv"),
        ("level", "347.Iv (56.42%)", "347.lv"),
        ("reset", "Reset 60.rs extra", "60.rs"),
        ("status", "vent 71", None),
        ("status", "Automatically attacking", "Automatically attacking"),
    ],
)
def test_companion_field_normalization_rejects_or_trims_ocr_noise(
    field: str, raw: str, expected: str | None,
) -> None:
    assert companion_info._normalize_field_value(field, raw) == expected


def test_info_close_failure_preserves_character_fields(game: dict) -> None:
    game["frames"] = [cv2.imread(str(ROOT / "assets/companion_management_ntd3006.png"))]
    game["close_works"] = False
    result = companion_info.get_companion_information(TARGET, close_timeout_seconds=0.1)
    assert result["success"] is False
    assert result["character"]["name"] == "NTD3001"
    assert result["dialog_close"]["closed"] is False
    assert game["clicks"] == [(761, 114)]


def test_info_ocr_exception_still_closes_dialog(game: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    game["frames"] = [cv2.imread(str(ROOT / "assets/companion_management_ntd3006.png"))]

    def broken_ocr(self: object, image: np.ndarray) -> str:
        raise RuntimeError("OCR failed")

    monkeypatch.setattr(WinRTOCREngine, "recognize", broken_ocr)
    result = keyboard.get_companion_summoned_state()
    assert result["success"] is False
    assert result["error"] == "OCR failed"
    assert result["dialog_close"]["closed"] is True
    assert game["clicks"] == [(761, 114)]


def test_info_lost_capture_cannot_confirm_closed(game: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    game["frames"] = [cv2.imread(str(ROOT / "assets/companion_management_ntd3006.png"))]

    def close_without_capture(self: object, x: int, y: int) -> None:
        game["clicks"].append((x, y))
        game["frames"] = [None]

    monkeypatch.setattr(MouseController, "click_at_client", close_without_capture)
    result = companion_info.get_companion_information(TARGET, close_timeout_seconds=0.1)
    assert result["success"] is False
    assert result["dialog_close"]["closed"] is False
    assert result["character"]["name"] == "NTD3001"


@pytest.mark.parametrize("windows,error", [([], "Select a game window"), ([TARGET, TARGET], None)])
def test_tools_reject_missing_or_ambiguous_target(game: dict, monkeypatch: pytest.MonkeyPatch, windows: list, error: str | None) -> None:
    monkeypatch.setattr(keyboard, "_selected_visible_windows", lambda: (windows, error))
    for action in (keyboard.open_companion_management_dialog, keyboard.switch_to_companion_character,
                   keyboard.get_companion_summoned_state, lambda: keyboard.summon_companion_character("NTD3001")):
        assert action()["success"] is False
    assert not game["clicks"] and not game["captures"]


def test_empty_character_name_never_touches_game(game: dict) -> None:
    assert keyboard.summon_companion_character(" ")["success"] is False
    assert not game["clicks"] and not game["captures"]
