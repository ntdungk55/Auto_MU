"""Minimal text OCR adapter used until an OpenVINO OCR model is configured."""

from __future__ import annotations

import numpy as np


class TesseractRecognizer:
    """Recognize one cropped text ROI through the locally installed Tesseract engine."""

    def recognize(self, image: np.ndarray) -> str:
        """Return normalized OCR text for one image ROI."""
        try:
            import pytesseract
        except ImportError as error:
            raise RuntimeError("OCR requires pytesseract") from error
        text = pytesseract.image_to_string(image, config="--psm 7")
        return " ".join(text.split())
