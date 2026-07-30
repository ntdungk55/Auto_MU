# Phân Tích Refactoring system_executor.py

## Tình Trạng Hiện Tại
- **Tổng dòng code:** 2214 dòng
- **Một file duy nhất:** Khó bảo trì, khó đọc
- **Nhiều trách nhiệm:** Screenshot, OCR, Gemini, Passive Read, Template Matching, etc.

---

## Phân Tích Các Chức Năng Chính

### 1. **Screenshot Capture** (~100 dòng)
- `capture_window_screenshot()` - Chụp ảnh window
- Trách nhiệm: Lấy ảnh từ window game

**Nên tách thành:** `screenshot_capturer.py`

```python
class ScreenshotCapturer:
    def capture(self) -> np.ndarray
    def capture_with_fallback(self) -> np.ndarray
```

---

### 2. **OCR Processing** (~200 dòng)
- `_ocr_from_bgr()` - Gọi OCR engine
- `_winrt_ocr_text_from_bgr()` - Windows OCR
- `_get_winrt_ocr_engine()` - Khởi tạo WinRT OCR
- Trách nhiệm: Xử lý OCR (WinRT, Tesseract)

**Nên tách thành:** `ocr_engine.py`

```python
class OCREngine(ABC):
    @abstractmethod
    def recognize(self, img: np.ndarray) -> str

class WinRTOCREngine(OCREngine):
    def recognize(self, img: np.ndarray) -> str

class TesseractOCREngine(OCREngine):
    def recognize(self, img: np.ndarray) -> str

class OCRFactory:
    @staticmethod
    def create(engine_type: str) -> OCREngine
```

---

### 3. **OCR Preprocessing** (~150 dòng)
- `OCRPreprocessor` class - Builder pattern
- `preprocess_for_ocr()` - Gọi preprocessing
- Trách nhiệm: Cải thiện chất lượng ảnh trước OCR

**Nên tách thành:** `ocr_preprocessor.py`

```python
class OCRPreprocessor:
    def upscale(self, scale_factor: float) -> 'OCRPreprocessor'
    def enhance_contrast(self) -> 'OCRPreprocessor'
    def sharpen(self, strength: float) -> 'OCRPreprocessor'
    def denoise(self) -> 'OCRPreprocessor'
    def build(self) -> np.ndarray
```

---

### 4. **Gemini Integration** (~200 dòng)
- `_gemini_extract_from_ocr()` - Gọi Gemini API
- `_get_gemini_model()` - Khởi tạo Gemini model
- Trách nhiệm: Xử lý Gemini post-processing

**Nên tách thành:** `gemini_processor.py`

```python
class GeminiProcessor:
    def process(self, ocr_text: str, action: AutoAction) -> str
    def _configure_api(self, api_key: str)
    def _get_model(self, model_name: str)
```

---

### 5. **Template Matching** (~300 dòng)
- `find_image_in_window_with_score()` - Tìm ảnh
- `_iter_scales_adaptive()` - Adaptive scales
- `_iter_rois_adaptive()` - Adaptive ROI
- `_verify_cached_match_in_roi()` - Verify match
- Trách nhiệm: Nhận diện template matching

**Nên tách thành:** `template_matcher.py`

```python
class TemplateMatcher:
    def find_image(self, template_path: str, threshold: float) -> tuple
    def find_with_adaptive_scales(self, template_path: str) -> tuple
    def verify_cached_match(self, template_path: str, cached_result: tuple) -> tuple
```

---

### 6. **Passive Read** (~400 dòng)
- `_run_passive_read()` - Passive read loop
- `_compute_frame_hash()` - Hash frame
- Trách nhiệm: Đọc thụ động liên tục

**Nên tách thành:** `passive_reader.py`

```python
class PassiveReader:
    def run(self, action: AutoAction, timeout: float) -> bool
    def _compute_frame_hash(self, img: np.ndarray) -> str
    def _check_keywords(self, text: str, keywords: list) -> bool
```

---

### 7. **Image Detection** (~300 dòng)
- `execute_with_timeout()` - Chờ ảnh
- `find_image_in_window()` - Tìm ảnh
- Trách nhiệm: Detect ảnh trong window

**Nên tách thành:** `image_detector.py`

```python
class ImageDetector:
    def detect(self, template_path: str, threshold: float) -> tuple
    def wait_for_image(self, template_path: str, timeout: float) -> tuple
```

---

### 8. **Telegram Notification** (~50 dòng)
- `_send_telegram_notification()` - Gửi Telegram
- Trách nhiệm: Gửi thông báo

**Nên tách thành:** `telegram_notifier.py`

```python
class TelegramNotifier:
    def send(self, action: AutoAction, content: str, is_gemini: bool)
```

---

### 9. **Mouse/Keyboard Control** (~100 dòng)
- `click_at()` - Click chuột
- `click_at_client()` - Click PostMessage
- `_click_with_optional_alt()` - Click với ALT
- `_move_mouse_out_of_window()` - Di chuyển chuột
- Trách nhiệm: Điều khiển input

**Nên tách thành:** `input_controller.py`

```python
class InputController:
    def click_at(self, x: int, y: int)
    def click_at_client(self, client_x: int, client_y: int)
    def click_with_alt(self, x: int, y: int)
    def move_mouse_away(self)
```

---

### 10. **Window Detection** (~50 dòng)
- `set_target_window()` - Set window target
- Trách nhiệm: Quản lý window target

**Nên tách thành:** `window_manager.py`

```python
class WindowManager:
    def set_target(self, hwnd)
    def get_target(self) -> hwnd
    def capture_screenshot(self) -> np.ndarray
```

---

## Kiến Trúc Đề Xuất

```
system_executor/
├── __init__.py
├── system_executor.py (Main orchestrator - ~300 dòng)
├── screenshot_capturer.py (~100 dòng)
├── ocr_engine.py (~150 dòng)
├── ocr_preprocessor.py (~150 dòng)
├── gemini_processor.py (~150 dòng)
├── template_matcher.py (~250 dòng)
├── passive_reader.py (~300 dòng)
├── image_detector.py (~200 dòng)
├── telegram_notifier.py (~50 dòng)
├── input_controller.py (~100 dòng)
└── window_manager.py (~50 dòng)
```

---

## Lợi Ích Của Refactoring

✅ **Dễ đọc:** Mỗi file ~100-300 dòng
✅ **Dễ bảo trì:** Mỗi class có một trách nhiệm
✅ **Dễ test:** Có thể test từng component riêng
✅ **Dễ mở rộng:** Thêm feature mới không ảnh hưởng file khác
✅ **Reusable:** Có thể dùng lại các component
✅ **Clean code:** Tuân theo SOLID principles

---

## Ví Dụ Refactoring

### Trước (system_executor.py - 2214 dòng)
```python
class SystemExecutor:
    def __init__(self, target_window_hwnd=None):
        # 50 dòng initialization
        pass
    
    def capture_window_screenshot(self):
        # 100 dòng screenshot logic
        pass
    
    def _ocr_from_bgr(self, bgr_img, action):
        # 150 dòng OCR logic
        pass
    
    def _gemini_extract_from_ocr(self, ocr_text, action):
        # 200 dòng Gemini logic
        pass
    
    def _run_passive_read(self, action, timeout):
        # 400 dòng passive read logic
        pass
    
    # ... 1300+ dòng khác
```

### Sau (Modular)
```python
# system_executor.py - Main orchestrator (~300 dòng)
class SystemExecutor:
    def __init__(self, target_window_hwnd=None):
        self.window_manager = WindowManager(target_window_hwnd)
        self.screenshot_capturer = ScreenshotCapturer(self.window_manager)
        self.ocr_engine = OCRFactory.create("auto")
        self.ocr_preprocessor = OCRPreprocessor()
        self.gemini_processor = GeminiProcessor()
        self.template_matcher = TemplateMatcher(self.screenshot_capturer)
        self.passive_reader = PassiveReader(self)
        self.image_detector = ImageDetector(self.template_matcher)
        self.telegram_notifier = TelegramNotifier()
        self.input_controller = InputController()
    
    def execute_action(self, action: AutoAction):
        if action.action_type == ActionType.READ_PASSIVE:
            return self.passive_reader.run(action)
        elif action.action_type == ActionType.IMAGE_DETECT:
            return self.image_detector.detect(action)
        # ...

# ocr_engine.py (~150 dòng)
class OCREngine(ABC):
    @abstractmethod
    def recognize(self, img: np.ndarray) -> str:
        pass

class WinRTOCREngine(OCREngine):
    def recognize(self, img: np.ndarray) -> str:
        # 50 dòng WinRT logic
        pass

class TesseractOCREngine(OCREngine):
    def recognize(self, img: np.ndarray) -> str:
        # 50 dòng Tesseract logic
        pass

# gemini_processor.py (~150 dòng)
class GeminiProcessor:
    def process(self, ocr_text: str, action: AutoAction) -> str:
        # 150 dòng Gemini logic
        pass

# ... các file khác
```

---

## Giai Đoạn Refactoring

### Phase 1: Extract Interfaces (Tuần 1)
- Tạo abstract classes/interfaces
- Định nghĩa contracts

### Phase 2: Extract Classes (Tuần 2)
- Tách từng component ra file riêng
- Implement interfaces

### Phase 3: Integration (Tuần 3)
- Integrate các component vào SystemExecutor
- Test toàn bộ

### Phase 4: Cleanup (Tuần 4)
- Xóa code cũ
- Optimize imports
- Documentation

---

## Ưu Tiên Refactoring

1. **Cao:** OCR Engine, Gemini Processor (dễ tách, dùng nhiều)
2. **Trung:** Template Matcher, Passive Reader (phức tạp hơn)
3. **Thấp:** Input Controller, Telegram Notifier (đơn giản)

---

## Kết Luận

Refactoring thành modular architecture sẽ:
- Giảm độ phức tạp từ 2214 → ~300 dòng per file
- Tăng khả năng bảo trì
- Dễ test và debug
- Dễ thêm feature mới
- Code sạch hơn, dễ đọc hơn

**Khuyến nghị:** Bắt đầu với OCR Engine và Gemini Processor (dễ nhất, tác động lớn).
