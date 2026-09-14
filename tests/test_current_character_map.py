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
    monkeypatch.setattr(WinRTOCREngine, "recognize", lambda self, image: "Varka")

    result = current_character_info.get_current_character_map(TARGET)

    assert result["success"] is True
    assert result["map"] == "Varka"
    assert result["is_varka"] is True
    assert result["ocr"]["roi"] == {"x1": 55, "y1": 0, "x2": 116, "y2": 20}


def test_current_map_reader_uses_easyocr_word_results_when_winrt_fails(monkeypatch) -> None:
    frame = np.zeros((600, 800, 3), dtype=np.uint8)

    class Reader:
        def readtext(self, _image, **options):
            assert options["paragraph"] is False
            return [([[0, 0]], "Varka", 0.99)]

    monkeypatch.setattr(win32gui, "IsWindow", lambda hwnd: hwnd == 777)
    monkeypatch.setattr(win32gui, "IsWindowVisible", lambda hwnd: hwnd == 777)
    monkeypatch.setattr(GameWindowCapture, "capture", lambda self, hwnd: frame)
    monkeypatch.setattr(WinRTOCREngine, "recognize", lambda self, image: (_ for _ in ()).throw(IndexError("bad OCR result")))
    monkeypatch.setattr(EasyOCREngine, "_get_reader", lambda self: Reader())

    result = current_character_info.get_current_character_map(TARGET)

    assert result["success"] is True
    assert result["map"] == "Varka"
    assert result["ocr"]["method"] == "easyocr"


def test_current_map_normalizer_discards_a_trailing_hud_number() -> None:
    assert current_character_info._normalize_map("Varka 1") == "Varka"
