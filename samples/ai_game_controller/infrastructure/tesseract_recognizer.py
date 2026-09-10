"""Minimal text OCR adapter used until an OpenVINO OCR model is configured."""

from __future__ import annotations

import numpy as np


class TesseractRecognizer:
    """Recognize one cropped text ROI through the locally installed Tesseract engine."""

    def recognize(self, image: np.ndarray, timeout_seconds: float | None = None) -> str:
        """Return normalized OCR text for one image ROI."""
        try:
            import pytesseract
        except ImportError as error:
            raise RuntimeError("OCR requires pytesseract") from error
        kwargs: dict[str, object] = {"config": "--psm 7"}
        if timeout_seconds is not None:
            kwargs["timeout"] = max(0.1, timeout_seconds)
        text = pytesseract.image_to_string(image, **kwargs)
        return " ".join(text.split())
