"""EasyOCR adapter used by the AI game-controller reader."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError

import numpy as np

from src.logic.system_executor.ocr_engine import EasyOCREngine


class EasyOCRRecognizer:
    """Recognize one teaching ROI through the application's shared EasyOCR reader."""

    _timeout_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="easyocr-recognizer")

    def __init__(self) -> None:
        self._engine = EasyOCREngine()

    def recognize(self, image: np.ndarray, timeout_seconds: float | None = None) -> str:
        """Return normalized text; EasyOCR owns its shared reader lifecycle.

        EasyOCR does not expose a safe cancellation API for an in-flight recognition.
        For an explicit deadline, return an empty result at the deadline while its
        one shared worker finishes the inference in the background.
        """
        if timeout_seconds is None:
            return self._normalize(self._engine.recognize(image))
        future = self._timeout_executor.submit(self._engine.recognize, image)
        try:
            return self._normalize(future.result(timeout=max(0.1, timeout_seconds)))
        except TimeoutError:
            return ""

    @staticmethod
    def _normalize(value: object) -> str:
        return " ".join(str(value or "").split())
