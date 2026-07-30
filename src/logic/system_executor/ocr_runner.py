"""OCR Runner - OCR pipeline extracted from SystemExecutor."""

import cv2
import numpy as np
from typing import Callable, Optional, Tuple

from .ocr_engine import OCRFactory
from .ocr_preprocessor import OCRPreprocessor


class OCRRunner:
    """OCR pipeline: preprocessing -> engine selection -> recognition."""

    def __init__(self, ui_log_func: Callable[[str], None], apply_preprocessing_fn: Optional[Callable] = None):
        """Initialize OCRRunner."""
        self._ui_log = ui_log_func
        self._apply_preprocessing = apply_preprocessing_fn

    def preprocess_for_ocr(
        self,
        img_bgr: np.ndarray,
        enable_upscale: bool = True,
        enable_contrast: bool = True,
        enable_sharpen: bool = True,
        enable_denoise: bool = False,
        upscale_factor: float = 2.0,
    ) -> Optional[np.ndarray]:
        """Apply legacy OCR preprocessing pipeline."""
        if img_bgr is None:
            return None

        preprocessor = OCRPreprocessor(img_bgr, self._ui_log)
        if enable_upscale:
            preprocessor.upscale(upscale_factor)
        if enable_contrast:
            preprocessor.enhance_contrast()
        if enable_sharpen:
            preprocessor.sharpen()
        if enable_denoise:
            preprocessor.denoise()
        return preprocessor.build()

    def run(self, bgr_img: np.ndarray, action) -> Tuple[str, str]:
        """Run OCR with preprocessing on a BGR image."""
        text = ""
        engine_used = ""

        ocr_algorithms = getattr(action, "ocr_algorithms", None)

        if ocr_algorithms and len(ocr_algorithms) > 0 and self._apply_preprocessing:
            bgr_preprocessed = self._apply_preprocessing(bgr_img, ocr_algorithms)
            self._ui_log(
                f"<span style='color:blue;'>[OCR Preprocessing]</span> Đã áp dụng {len(ocr_algorithms)} thuật toán custom"
            )
        else:
            enable_upscale = bool(getattr(action, "ocr_upscale_enabled", True))
            enable_contrast = bool(getattr(action, "ocr_enhance_contrast", True))
            enable_sharpen = bool(getattr(action, "ocr_sharpen", True))
            enable_denoise = bool(getattr(action, "ocr_denoise", False))
            upscale_factor = float(getattr(action, "ocr_upscale_factor", 2.0) or 2.0)
            bgr_preprocessed = self.preprocess_for_ocr(
                bgr_img,
                enable_upscale=enable_upscale,
                enable_contrast=enable_contrast,
                enable_sharpen=enable_sharpen,
                enable_denoise=enable_denoise,
                upscale_factor=upscale_factor,
            )

        try:
            gray = cv2.cvtColor(bgr_preprocessed, cv2.COLOR_BGR2GRAY)
        except Exception:
            gray = None

        ocr_bgr = bgr_preprocessed
        if gray is not None and bool(getattr(action, "ocr_bright_on_dark", False)):
            try:
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
                top = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                top = clahe.apply(top)
                top = cv2.GaussianBlur(top, (3, 3), 0)
                cv2.threshold(top, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                ocr_bgr = cv2.cvtColor(top, cv2.COLOR_GRAY2BGR)
            except Exception:
                pass

        engine_sel = str(getattr(action, "ocr_engine", "auto") or "auto").lower()
        if engine_sel == "paddle":
            engine_sel = "auto"
        if engine_sel not in ("auto", "winrt", "tesseract", "easyocr", "vietocr"):
            engine_sel = "auto"

        passive_mode = str(getattr(action, "passive_mode", "") or "")
        if passive_mode == "event_tracking":
            event_engine = str(getattr(action, "event_ocr_engine", "auto") or "auto").lower()
            if event_engine and event_engine != "auto":
                engine_sel = event_engine

        try:
            engine = OCRFactory.create(engine_sel, self._ui_log)
            self._ui_log(f"<span style='color:blue;'>[OCR]</span> Dùng engine: <b>{engine_sel}</b>")
            text = engine.recognize(ocr_bgr)
            engine_used = engine_sel
        except Exception as exc:
            self._ui_log(f"<b style='color:red;'>[OCR]</b> Lỗi: {exc}")
            text = ""

        return text, engine_used
