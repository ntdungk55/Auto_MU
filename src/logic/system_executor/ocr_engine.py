"""OCR Engine - Abstract interface and implementations for OCR processing."""

from abc import ABC, abstractmethod
import cv2
import numpy as np
import asyncio
import threading

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    import winsdk.windows.media.ocr as win_ocr
    import winsdk.windows.graphics.imaging as win_img
    import winsdk.windows.storage.streams as win_streams
except Exception:
    win_ocr = None
    win_img = None
    win_streams = None

try:
    import easyocr as _easyocr_lib
except Exception:
    _easyocr_lib = None

try:
    from paddleocr import PaddleOCR as _PaddleOCR
except Exception:
    _PaddleOCR = None

try:
    from vietocr.tool.predictor import Predictor as _VietOCRPredictor
    from vietocr.tool.config import Cfg as _VietOCRCfg
except Exception:
    _VietOCRPredictor = None
    _VietOCRCfg = None


class OCREngine(ABC):
    """Abstract base class for OCR engines."""
    
    @abstractmethod
    def recognize(self, img: np.ndarray) -> str:
        """Recognize text from image.
        
        Args:
            img: BGR image array
            
        Returns:
            Recognized text
        """
        pass

    def recognize_lines(self, img: np.ndarray) -> list[str]:
        """Recognize text and return line-based output when available."""
        text = self.recognize(img)
        return [line.strip() for line in str(text or "").splitlines() if line.strip()]


class WinRTOCREngine(OCREngine):
    """Windows Runtime OCR engine (WinRT)."""
    
    def __init__(self, ui_log_func=None):
        self.engine = None
        self.ui_log = ui_log_func or (lambda x: None)
        self._init_engine()
    
    def _init_engine(self):
        """Initialize WinRT OCR engine."""
        if win_ocr is None:
            return
        
        try:
            self.engine = win_ocr.OcrEngine.try_create_from_user_profile_languages()
        except Exception as e:
            self.ui_log(f"<b style='color:red;'>[OCR]</b> Không khởi tạo được Windows OCR (WinRT): {e}")
            self.engine = None
    
    def recognize(self, img: np.ndarray) -> str:
        """Recognize text using WinRT OCR."""
        if self.engine is None or win_img is None or win_streams is None:
            return ""
        
        try:
            # Convert BGR to BGRA
            bgra = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
            height, width = bgra.shape[:2]
            raw = bgra.tobytes()
            
            # Wrap bytes into IBuffer
            writer = win_streams.DataWriter()
            writer.write_bytes(bytearray(raw))
            ibuf = writer.detach_buffer()
            
            # Get pixel format
            pixel_format = getattr(win_img.BitmapPixelFormat, "BGRA8", None)
            if pixel_format is None:
                raise AttributeError("Windows OCR: BitmapPixelFormat missing BGRA8")
            
            # Create SoftwareBitmap
            sb = win_img.SoftwareBitmap(pixel_format, width, height)
            sb.copy_from_buffer(ibuf)
            
            # Recognize
            result = self._run_async(self.engine.recognize_async(sb))
            text = getattr(result, "text", "") or ""
            return str(text).strip()
        except Exception as e:
            self.ui_log(f"<b style='color:red;'>[WinRT OCR]</b> Lỗi: {e}")
            return ""
    
    @staticmethod
    def _run_async(coro):
        """Run async coroutine."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        
        result_holder = {"value": None, "error": None}
        
        def _worker():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result_holder["value"] = loop.run_until_complete(coro)
                loop.close()
            except Exception as e:
                result_holder["error"] = e
        
        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        t.join()
        
        if result_holder["error"] is not None:
            raise result_holder["error"]
        return result_holder["value"]


class TesseractOCREngine(OCREngine):
    """Tesseract OCR engine."""
    
    def __init__(self, ui_log_func=None):
        self.ui_log = ui_log_func or (lambda x: None)
    
    def recognize(self, img: np.ndarray) -> str:
        """Recognize text using Tesseract."""
        if pytesseract is None:
            return ""
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            text = pytesseract.image_to_string(gray, lang="vie+eng")
            return (text or "").strip()
        except Exception as e:
            self.ui_log(f"<b style='color:red;'>[Tesseract OCR]</b> Lỗi: {e}")
            return ""


class EasyOCREngine(OCREngine):
    """EasyOCR engine - supports Vietnamese well."""

    _shared_reader = None  # Singleton - shared across all instances

    def __init__(self, ui_log_func=None):
        self.ui_log = ui_log_func or (lambda x: None)

    def _get_reader(self):
        """Lazy-load EasyOCR reader (singleton)."""
        if EasyOCREngine._shared_reader is None:
            if _easyocr_lib is None:
                return None
            try:
                EasyOCREngine._shared_reader = _easyocr_lib.Reader(['vi', 'en'], gpu=False)
            except Exception as e:
                self.ui_log(f"<b style='color:red;'>[EasyOCR]</b> Không khởi tạo được: {e}")
        return EasyOCREngine._shared_reader

    def recognize(self, img: np.ndarray) -> str:
        """Recognize text using EasyOCR."""
        lines = self.recognize_lines(img)
        return "\n".join(lines).strip()

    def recognize_lines(self, img: np.ndarray) -> list[str]:
        """Recognize text using EasyOCR and rebuild visual lines from boxes."""
        reader = self._get_reader()
        if reader is None:
            return []
        try:
            results = reader.readtext(img, detail=1, decoder='greedy')
            return self._group_results_into_lines(results)
        except Exception as e:
            self.ui_log(f"<b style='color:red;'>[EasyOCR]</b> Lỗi: {e}")
            return []

    @staticmethod
    def _group_results_into_lines(results) -> list[str]:
        """Group EasyOCR detail results into ordered text lines."""
        entries = []
        for item in results or []:
            if not item or len(item) < 2:
                continue
            box = item[0]
            text = str(item[1] or "").strip()
            if not box or not text:
                continue

            try:
                xs = [float(point[0]) for point in box]
                ys = [float(point[1]) for point in box]
            except Exception:
                continue

            if not xs or not ys:
                continue

            top = min(ys)
            bottom = max(ys)
            left = min(xs)
            height = max(1.0, bottom - top)
            center_y = (top + bottom) / 2.0
            entries.append(
                {
                    "text": text,
                    "left": left,
                    "top": top,
                    "center_y": center_y,
                    "height": height,
                }
            )

        if not entries:
            return []

        entries.sort(key=lambda item: (item["top"], item["left"]))
        line_groups: list[list[dict]] = []
        for entry in entries:
            placed = False
            for group in line_groups:
                avg_center_y = sum(item["center_y"] for item in group) / len(group)
                avg_height = sum(item["height"] for item in group) / len(group)
                tolerance = max(8.0, avg_height * 0.6)
                if abs(entry["center_y"] - avg_center_y) <= tolerance:
                    group.append(entry)
                    placed = True
                    break
            if not placed:
                line_groups.append([entry])

        output_lines = []
        for group in line_groups:
            group.sort(key=lambda item: item["left"])
            line_text = " ".join(item["text"] for item in group if item["text"]).strip()
            if line_text:
                output_lines.append(line_text)
        return output_lines


class PaddleOCREngine(OCREngine):
    """PaddleOCR engine - excellent Vietnamese support."""

    def __init__(self, ui_log_func=None):
        self.ui_log = ui_log_func or (lambda x: None)
        self._ocr = None

    def _get_ocr(self):
        """Lazy-load PaddleOCR instance."""
        if self._ocr is None:
            if _PaddleOCR is None:
                return None
            try:
                self._ocr = _PaddleOCR(use_angle_cls=True, lang='vi', show_log=False)
            except Exception as e:
                self.ui_log(f"<b style='color:red;'>[PaddleOCR]</b> Không khởi tạo được: {e}")
        return self._ocr

    def recognize(self, img: np.ndarray) -> str:
        """Recognize text using PaddleOCR."""
        ocr = self._get_ocr()
        if ocr is None:
            return ""
        try:
            result = ocr.ocr(img, cls=True)
            if not result or not result[0]:
                return ""
            lines = [line[1][0] for line in result[0] if line and line[1]]
            return "\n".join(str(item or "").strip() for item in lines if str(item or "").strip()).strip()
        except Exception as e:
            self.ui_log(f"<b style='color:red;'>[PaddleOCR]</b> Lỗi: {e}")
            return ""


class VietOCREngine(OCREngine):
    """VietOCR engine - specialized for Vietnamese text recognition."""

    def __init__(self, ui_log_func=None):
        self.ui_log = ui_log_func or (lambda x: None)
        self._predictor = None

    def _get_predictor(self):
        """Lazy-load VietOCR predictor."""
        if self._predictor is None:
            if _VietOCRPredictor is None or _VietOCRCfg is None:
                return None
            try:
                config = _VietOCRCfg.load_config_from_name('vgg_transformer')
                config['cnn']['pretrained'] = False
                config['device'] = 'cpu'
                self._predictor = _VietOCRPredictor(config)
            except Exception as e:
                self.ui_log(f"<b style='color:red;'>[VietOCR]</b> Không khởi tạo được: {e}")
        return self._predictor

    def recognize(self, img: np.ndarray) -> str:
        """Recognize text using VietOCR."""
        predictor = self._get_predictor()
        if predictor is None:
            print("[DEBUG VietOCR] predictor is None - library not available")
            return ""
        try:
            from PIL import Image as _PILImage
            pil_img = _PILImage.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            text = predictor.predict(pil_img)
            print(f"[DEBUG VietOCR] result: {repr(text)}")
            return (text or "").strip()
        except Exception as e:
            print(f"[DEBUG VietOCR] Exception: {e}")
            self.ui_log(f"<b style='color:red;'>[VietOCR]</b> Lỗi: {e}")
            return ""


class OCRFactory:
    """Factory for creating OCR engines."""
    
    @staticmethod
    def create(engine_type: str, ui_log_func=None) -> OCREngine:
        """Create OCR engine by type.
        
        Args:
            engine_type: "auto", "winrt", "tesseract", "easyocr", or "paddleocr"
            ui_log_func: Optional logging function
            
        Returns:
            OCREngine instance
        """
        engine_type = str(engine_type or "auto").lower()
        
        if engine_type == "winrt" and win_ocr is not None:
            return WinRTOCREngine(ui_log_func)
        elif engine_type == "tesseract" and pytesseract is not None:
            return TesseractOCREngine(ui_log_func)
        elif engine_type == "easyocr" and _easyocr_lib is not None:
            return EasyOCREngine(ui_log_func)
        elif engine_type == "paddleocr" and _PaddleOCR is not None:
            return PaddleOCREngine(ui_log_func)
        elif engine_type == "vietocr" and _VietOCRPredictor is not None:
            return VietOCREngine(ui_log_func)
        elif engine_type == "auto":
            # Priority: WinRT → EasyOCR → PaddleOCR → Tesseract
            if win_ocr is not None:
                return WinRTOCREngine(ui_log_func)
            elif _easyocr_lib is not None:
                return EasyOCREngine(ui_log_func)
            elif _PaddleOCR is not None:
                return PaddleOCREngine(ui_log_func)
            elif pytesseract is not None:
                return TesseractOCREngine(ui_log_func)
        
        # Fallback
        return TesseractOCREngine(ui_log_func)
