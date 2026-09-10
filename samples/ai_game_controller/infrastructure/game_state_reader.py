"""Background game-state reader adapter."""

from __future__ import annotations

from difflib import SequenceMatcher
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

from ..domain.game_state import GameState
from ..domain.game_target import GameTarget


class WindowCapture(Protocol):
    """Capture a selected window as a BGR image array."""

    def capture(self, hwnd: int) -> np.ndarray | None:
        """Capture the client area of one window."""


class TextRecognizer(Protocol):
    """Recognize text from one normalized ROI image."""

    def recognize(self, image: np.ndarray, timeout_seconds: float | None = None) -> str:
        """Return OCR text for one image."""


class GameStateReader:
    """Capture, normalize, and OCR one game window according to teaching JSON."""

    _DYNAMIC_TEXT_FUZZY_THRESHOLD = 0.70

    def __init__(
        self,
        capture: WindowCapture,
        recognizer: TextRecognizer,
        teaching_path: Path,
        width: int = 800,
        height: int = 600,
        scale: float = 1.0,
        grayscale: bool = True,
        threshold: int = 80,
    ) -> None:
        self._capture = capture
        self._recognizer = recognizer
        self._teaching_path = teaching_path
        self._width = width
        self._height = height
        self._scale = max(1.0, scale)
        self._grayscale = grayscale
        self._threshold = threshold
        self._main_info_teaching, self._dynamic_texts = self._load_teaching()
        self.last_error: str | None = None

    def read(self, target: GameTarget) -> GameState | None:
        """Read a normalized OCR snapshot for the configured target."""
        self.last_error = None
        try:
            image = self._capture.capture(target.hwnd)
            if image is None:
                self.last_error = "window capture returned no image"
                return None
            normalized = cv2.resize(image, (self._width, self._height), interpolation=cv2.INTER_AREA)
            return GameState(
                target_id=target.target_id,
                hwnd=target.hwnd,
                captured_at=datetime.now(timezone.utc),
                main_info=self._read_main_info(normalized),
            )
        except Exception as error:
            self.last_error = str(error)
            return None

    def verify_dynamic_text(
        self,
        target: GameTarget,
        event_type: str,
        timeout_seconds: float | None = None,
    ) -> str | None:
        """OCR one configured dynamic-text ROI only when a caller requests it."""
        definition = self._dynamic_texts.get(event_type)
        if definition is None:
            raise ValueError(f"dynamic text is not configured for event: {event_type}")
        expected_text = str(definition.get("text", "") or "")
        roi = definition.get("roi")
        if not expected_text or not isinstance(roi, dict):
            raise ValueError(f"dynamic text configuration is invalid for event: {event_type}")

        try:
            image = self._capture.capture(target.hwnd)
            if image is None:
                self.last_error = "window capture returned no image"
                return None
            normalized = cv2.resize(image, (self._width, self._height), interpolation=cv2.INTER_AREA)
            recognized_text = self._recognizer.recognize(
                self._prepare_for_ocr(self._crop(normalized, roi)),
                timeout_seconds=timeout_seconds,
            )
            if self._dynamic_text_matches(expected_text, recognized_text):
                return recognized_text
            return None
        except Exception as error:
            self.last_error = str(error)
            return None

    def _load_teaching(self) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
        with self._teaching_path.open("r", encoding="utf-8-sig") as stream:
            payload = json.load(stream)
        main_info = payload.get("mainInfo")
        if not isinstance(main_info, dict):
            raise ValueError("teaching JSON must contain mainInfo")
        raw_dynamic_texts = payload.get("dynamicTexts", {})
        if not isinstance(raw_dynamic_texts, dict):
            raise ValueError("teaching JSON dynamicTexts must be an object")
        dynamic_texts = {
            str(event_type): definition
            for event_type, definition in raw_dynamic_texts.items()
            if isinstance(definition, dict)
        }
        return main_info, dynamic_texts

    def _read_main_info(self, image: np.ndarray) -> dict[str, object]:
        result: dict[str, object] = {}
        for name, raw_definition in self._main_info_teaching.items():
            if not isinstance(raw_definition, dict):
                continue
            roi = raw_definition.get("roi")
            if not isinstance(roi, dict):
                continue
            crop = self._crop(image, roi)
            recognition_type = str(raw_definition.get("recognitionType", ""))
            if recognition_type == "text":
                result[name] = {
                    "text": self._recognizer.recognize(self._prepare_for_ocr(crop)),
                    "value_pattern": str(raw_definition.get("valuePattern", "")),
                }
            else:
                result[name] = {
                    "recognition_type": recognition_type,
                    "roi": {key: int(value) for key, value in roi.items()},
                }
        return result

    def _crop(self, image: np.ndarray, roi: dict[str, object]) -> np.ndarray:
        x1 = max(0, int(roi["x1"]))
        y1 = max(0, int(roi["y1"]))
        x2 = min(self._width, int(roi["x2"]))
        y2 = min(self._height, int(roi["y2"]))
        if x2 <= x1 or y2 <= y1:
            raise ValueError("teaching ROI must have a positive area")
        return image[y1:y2, x1:x2]

    def _prepare_for_ocr(self, image: np.ndarray) -> np.ndarray:
        if self._scale > 1.0:
            image = cv2.resize(image, None, fx=self._scale, fy=self._scale, interpolation=cv2.INTER_CUBIC)
        if not self._grayscale:
            return image
        grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, thresholded = cv2.threshold(grayscale, self._threshold, 255, cv2.THRESH_BINARY)
        return thresholded

    @staticmethod
    def _normalize_text(value: str) -> str:
        return " ".join(value.split()).casefold()

    @classmethod
    def _dynamic_text_matches(cls, expected_text: str, recognized_text: str) -> bool:
        """Match an expected dialog label exactly or as a close OCR token phrase."""
        expected = cls._normalize_text(expected_text)
        observed = cls._normalize_text(recognized_text)
        if not expected or not observed:
            return False
        if expected in observed:
            return True

        expected_tokens = expected.split()
        observed_tokens = observed.split()
        expected_count = len(expected_tokens)
        for window_size in range(max(1, expected_count - 1), expected_count + 2):
            if window_size > len(observed_tokens):
                continue
            for start in range(0, len(observed_tokens) - window_size + 1):
                candidate = " ".join(observed_tokens[start:start + window_size])
                if SequenceMatcher(None, expected, candidate).ratio() >= cls._DYNAMIC_TEXT_FUZZY_THRESHOLD:
                    return True
        return False
