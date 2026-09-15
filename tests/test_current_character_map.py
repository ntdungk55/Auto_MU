"""Tests for the read-only active-character map MCP implementation."""

import numpy as np
import win32gui

from samples.ai_game_controller.infrastructure.window_capture import GameWindowCapture
from src.ai_control import current_character_info
from src.logic.system_executor.ocr_engine import EasyOCREngine, WinRTOCREngine


TARGET = {"hwnd": 777, "title": "MU"}


def test_current_map_reader_marks_varka_without_opening_a_dialog(monkeypatch) -> None:
    frame = np.zeros((600, 800, 3), dtype=np.uint8)
    monkeypatch.setattr(win32gui, "IsWindow", lambda hwnd: hwnd == 777)
    monkeypatch.setattr(win32gui, "IsWindowVisible", lambda hwnd: hwnd == 777)
    monkeypatch.setattr(GameWindowCapture, "capture", lambda self, hwnd: frame)
    monkeypatch.setattr(
        WinRTOCREngine, "recognize",
        lambda self, image: "Varka" if image.shape[1] == 231 else "199,156",
    )

    result = current_character_info.get_current_character_map(TARGET)

    assert result["success"] is True
    assert result["map"] == "Varka"
    assert result["position"] == {"x": 199, "y": 156}
    assert "coordinates" not in result
    assert "is_varka" not in result
    assert result["ocr"]["roi"] == {"x1": 55, "y1": 0, "x2": 116, "y2": 20}
    assert result["position_ocr"]["roi"] == {"x1": 115, "y1": 0, "x2": 162, "y2": 20}


def test_current_map_reader_uses_easyocr_word_results_when_winrt_fails(monkeypatch) -> None:
    frame = np.zeros((600, 800, 3), dtype=np.uint8)

    class Reader:
        def readtext(self, _image, **options):
            assert options["paragraph"] is False
            return [([[0, 0]], "Varka" if _image.shape[1] == 231 else "199,156", 0.99)]

    monkeypatch.setattr(win32gui, "IsWindow", lambda hwnd: hwnd == 777)
    monkeypatch.setattr(win32gui, "IsWindowVisible", lambda hwnd: hwnd == 777)
    monkeypatch.setattr(GameWindowCapture, "capture", lambda self, hwnd: frame)
    monkeypatch.setattr(WinRTOCREngine, "recognize", lambda self, image: (_ for _ in ()).throw(IndexError("bad OCR result")))
    monkeypatch.setattr(EasyOCREngine, "_get_reader", lambda self: Reader())

    result = current_character_info.get_current_character_map(TARGET)

    assert result["success"] is True
    assert result["map"] == "Varka"
    assert result["position"] == {"x": 199, "y": 156}
    assert result["ocr"]["method"] == "easyocr"
    assert result["position_ocr"]["method"] == "easyocr"


def test_current_map_normalizer_discards_a_trailing_hud_number() -> None:
    assert current_character_info._normalize_map("Varka 1") == "Varka"


def test_current_position_normalizer_requires_two_integer_coordinates() -> None:
    assert current_character_info._normalize_position("(199, 156)") == {"x": 199, "y": 156}
    assert current_character_info._normalize_position("Kanturu") is None
