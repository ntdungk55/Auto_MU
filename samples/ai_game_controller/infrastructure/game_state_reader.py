"""Background game-state reader adapter."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

from ..domain.game_state import GameState
from ..domain.game_target import GameTarget


class WindowCapture(Protocol):
    """Capture a selected window as an image array."""

    def capture(self, hwnd: int) -> np.ndarray | None:
        """Capture the client area of one window."""


class TextRecognizer(Protocol):
    """Recognize text from one normalized ROI image."""

    def recognize(self, image: np.ndarray) -> str:
        """Return OCR text for one image."""


class GameStateReader:
    """Capture, normalize, and OCR one game window according to teaching JSON."""

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
        self._teaching = self._load_teaching()
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

    def _load_teaching(self) -> dict[str, object]:
        with self._teaching_path.open("r", encoding="utf-8-sig") as stream:
            payload = json.load(stream)
        main_info = payload.get("mainInfo")
        if not isinstance(main_info, dict):
            raise ValueError("teaching JSON must contain mainInfo")
        return main_info

    def _read_main_info(self, image: np.ndarray) -> dict[str, object]:
        result: dict[str, object] = {}
        for name, raw_definition in self._teaching.items():
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
        grayscale = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        _, thresholded = cv2.threshold(grayscale, self._threshold, 255, cv2.THRESH_BINARY)
        return thresholded
