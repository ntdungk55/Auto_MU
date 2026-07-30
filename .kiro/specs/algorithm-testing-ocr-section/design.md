# Feature Design: Algorithm Testing OCR Section

## 1. Impact Analysis

### 1.1. Tác động đến code hiện tại
- **Files cần sửa:**
  - `src/ui/multi_image_algorithm_testing_dialog.py`: Thêm OCR section vào Process Algorithm section hiện tại
  - Không có breaking changes với code hiện tại

- **Classes/methods bị ảnh hưởng:**
  - `MultiImageAlgorithmTestingDialog.__init__()`: Thêm OCR-related attributes
  - `MultiImageAlgorithmTestingDialog._init_ui()`: Cập nhật Process Algorithm section layout với 7 cột trong OCR results table (No., Engine, Algorithms, Screenshot, Text, Conf, Time)
  - `MultiImageAlgorithmTestingDialog._run_ocr()`: Đọc screenshot đang được chọn (không phải teaching image), lấy Fixed ROI từ action settings
  - `MultiImageAlgorithmTestingDialog._get_fixed_roi_from_action()`: NEW - Lấy Fixed ROI từ action settings (nếu action type là READ_PASSIVE)
  - `MultiImageAlgorithmTestingDialog._get_current_algorithms_names()`: NEW - Lấy danh sách tên thuật toán đã cấu hình
  - `OCRWorkerThread.__init__()`: Thêm parameters fixed_roi, algorithms_names, screenshot_name
  - `OCRWorkerThread.run()`: Thêm logic crop ảnh theo Fixed ROI trước khi preprocessing
  - `OCRWorkerThread` signals: Thêm parameters algorithms_names, screenshot_name, confidence

- **Breaking changes:** Không - Chỉ thêm tính năng mới vào layout hiện tại, không thay đổi logic existing

### 1.2. Dependencies
- **Thư viện mới cần thêm:**
  - `easyocr`: OCR đa ngôn ngữ, hỗ trợ tiếng Việt tốt (`pip install easyocr`)
  - `paddleocr` + `paddlepaddle`: OCR tiếng Việt rất tốt - chỉ hỗ trợ Python ≤ 3.12 (`pip install paddleocr paddlepaddle`)

- **Phụ thuộc modules:**
  - `src/logic/system_executor/ocr_engine.py`: OCRFactory, WinRTOCREngine, TesseractOCREngine, EasyOCREngine, PaddleOCREngine
  - `src/logic/system_executor/ocr_preprocessor.py`: OCRPreprocessor (nếu cần riêng cho OCR)
  - `src/logic/action_type.py`: AutoAction - để đọc Fixed ROI từ action settings
  - `PyQt6.QtWidgets`: QSplitter, QTableWidget, QPushButton cho UI components
  - `cv2`: Để crop ảnh theo Fixed ROI coordinates

### 1.3. Khó khăn kỹ thuật
- **Layout integration**: Thêm OCR section vào Process Algorithm section mà không làm UI quá phức tạp
  - **Giải pháp**: Sử dụng QSplitter horizontal trong Process Algorithm section: Algorithm Management (trái) và OCR Testing (phải)
- **OCR Engine Detection**: Tự động detect các OCR engines available trong app
  - **Giải pháp**: Sử dụng OCRFactory để enumerate available engines, fallback gracefully nếu engine không available
- **Performance**: OCR có thể chậm với ảnh lớn
  - **Giải pháp**: Chạy OCR trong background thread, hiển thị progress
- **Memory usage**: Giữ nhiều ảnh và kết quả OCR trong memory
  - **Giải pháp**: Chỉ cache kết quả OCR cho ảnh hiện tại, clear khi chọn ảnh khác

### 1.4. Rủi ro
- **UI thread blocking**: OCR chạy lâu có thể block UI
  - **Cách giảm thiểu**: Sử dụng QThread và signals để chạy OCR trong background
- **OCR engine failure**: WinRT hoặc Tesseract có thể fail
  - **Cách giảm thiểu**: Fallback mechanism trong OCRFactory, hiển thị error message rõ ràng
- **Large image processing**: Ảnh lớn có thể gây crash
  - **Cách giảm thiểu**: Resize ảnh xuống kích thước hợp lý trước khi OCR

## 2. Technical Design

### 2.1. Architecture
```
MultiImageAlgorithmTestingDialog
├── Main Layout (QVBoxLayout) - EXISTING
│   ├── Preview Area (Teaching + Window Capture) - EXISTING
│   ├── Window Captures List - EXISTING
│   ├── Process Algorithm Section - MODIFIED
│   │   ├── Algorithm Management (Left) - EXISTING
│   │   │   ├── Algorithm Dropdown & Add Button
│   │   │   └── Algorithm List Widget
│   │   └── OCR Testing Section (Right) - MODIFIED
│   │       ├── OCR Controls
│   │       │   ├── Engine Selection Dropdown (Auto-detected)
│   │       │   ├── Run OCR Button
│   │       │   └── Progress Bar
│   │       └── OCR Results Table (7 columns)
│   │           ├── No. Column
│   │           ├── Engine Column
│   │           ├── Algorithms Column (NEW - danh sách thuật toán đã áp dụng)
│   │           ├── Screenshot Column (NEW - tên ảnh screenshot)
│   │           ├── Text Column
│   │           ├── Conf Column
│   │           └── Time Column
│   ├── Testing Controls - EXISTING
│   └── Bottom Buttons - EXISTING

OCRWorkerThread (MODIFIED)
├── Input: image_path, engine_name, algorithms, fixed_roi (Optional)
├── Logic:
│   ├── Load screenshot image (không phải teaching image)
│   ├── Crop theo fixed_roi nếu có
│   ├── Apply tất cả algorithms
│   └── Run OCR engine
└── Signals: ocr_completed(engine, screenshot_name, algo_names, time, text, conf)
            ocr_error(engine, screenshot_name, error)
```

### 2.2. Design Patterns
- **Factory Pattern**: Sử dụng OCRFactory.create() để tạo OCR engines và auto-detect available engines
- **Observer Pattern**: Sử dụng Qt signals để update UI từ background OCR thread
- **Builder Pattern**: Sử dụng OCRPreprocessor để apply preprocessing trước OCR

### 2.3. Code Organization
- **Files được tạo:**
  - Không tạo file mới - tất cả logic được thêm vào file hiện có

- **Files được sửa:**
  - `src/ui/multi_image_algorithm_testing_dialog.py`: Cập nhật Process Algorithm section layout và thêm OCR methods

## 3. Code Skeleton

### 3.1. OCR-related Attributes (thêm vào __init__)
```python
class MultiImageAlgorithmTestingDialog:
    def __init__(self, action: AutoAction, parent=None, target_window_hwnd=None, tool_id=None):
        # Existing code...
        
        # OCR-related attributes
        self.available_ocr_engines = self._detect_available_ocr_engines()
        self.ocr_results = {}  # Cache OCR results per image
        self.current_ocr_thread = None
        
        # OCR UI components (will be initialized in _init_ui)
        self.ocr_engine_combo = None
        self.run_ocr_btn = None
        self.ocr_progress_bar = None
        self.ocr_results_table = None
        
        # OCR signals
        self.ocr_completed = pyqtSignal(str, str, float, str)  # engine, image_path, time, text
        self.ocr_error = pyqtSignal(str, str, str)  # engine, image_path, error

def _detect_available_ocr_engines(self) -> list:
    """Detect available OCR engines in the app."""
    engines = []
    
    try:
        from logic.system_executor.ocr_engine import OCRFactory
        
        # Test each engine availability
        test_engines = ["auto", "winrt", "tesseract"]
        for engine_name in test_engines:
            try:
                engine = OCRFactory.create(engine_name)
                if engine:
                    engines.append(engine_name.title())
            except Exception:
                continue  # Engine not available
                
    except ImportError:
        # Fallback if OCRFactory not available
        engines = ["Auto"]
    
    return engines if engines else ["Auto"]  # Always have at least Auto
```

### 3.2. UI Layout Modification (_create_ocr_testing_widget)
```python
def _create_ocr_testing_widget(self) -> QWidget:
    """Create OCR testing widget with 7-column results table."""
    ocr_widget = QWidget()
    ocr_layout = QVBoxLayout(ocr_widget)
    
    ocr_layout.addWidget(QLabel("🔍 OCR Testing"))
    
    controls_layout = QHBoxLayout()
    controls_layout.addWidget(QLabel("Engine:"))
    self.ocr_engine_combo = QComboBox()
    self.ocr_engine_combo.addItems(self.available_ocr_engines)
    controls_layout.addWidget(self.ocr_engine_combo)
    
    self.run_ocr_btn = QPushButton("▶️ Run OCR")
    self.run_ocr_btn.clicked.connect(self._run_ocr)
    controls_layout.addWidget(self.run_ocr_btn)
    controls_layout.addStretch()
    ocr_layout.addLayout(controls_layout)
    
    self.ocr_progress_bar = QProgressBar()
    self.ocr_progress_bar.setVisible(False)
    ocr_layout.addWidget(self.ocr_progress_bar)
    
    ocr_layout.addWidget(QLabel("📊 OCR Results"))
    self.ocr_results_table = QTableWidget()
    self.ocr_results_table.setColumnCount(7)
    self.ocr_results_table.setHorizontalHeaderLabels(
        ["No.", "Engine", "Algorithms", "Screenshot", "Text", "Conf", "Time (ms)"]
    )
    ocr_layout.addWidget(self.ocr_results_table)
    
    return ocr_widget
```

### 3.3. OCR Execution Methods (MODIFIED - đọc từ screenshot + Fixed ROI)
```python
def _get_fixed_roi_from_action(self) -> Optional[tuple]:
    """Get Fixed ROI from action settings.
    
    Returns:
        Tuple (x, y, w, h) nếu có Fixed ROI, None nếu không
    """
    if getattr(self.action, 'use_fixed_roi', False):
        x = getattr(self.action, 'roi_x', 0)
        y = getattr(self.action, 'roi_y', 0)
        w = getattr(self.action, 'roi_w', 200)
        h = getattr(self.action, 'roi_h', 100)
        if w > 0 and h > 0:
            return (x, y, w, h)
    return None

def _run_ocr(self):
    """Run OCR on current selected screenshot image."""
    current_item = self.captures_list.currentItem()
    if not current_item:
        self._show_ocr_message("Vui lòng chọn một ảnh screenshot để chạy OCR")
        return
    
    item_data = current_item.data(Qt.ItemDataRole.UserRole)
    image_path = item_data if isinstance(item_data, str) else (item_data.get("path") if item_data else None)
    
    if not image_path:
        self._show_ocr_message("Không thể lấy đường dẫn ảnh")
        return
    
    engine_name = self.ocr_engine_combo.currentText().lower()
    fixed_roi = self._get_fixed_roi_from_action()
    algorithms = self._get_current_algorithms()
    screenshot_name = os.path.basename(image_path)
    
    self.ocr_progress_bar.setVisible(True)
    self.ocr_progress_bar.setRange(0, 0)
    self.run_ocr_btn.setEnabled(False)
    
    self._start_ocr_thread(image_path, engine_name, algorithms, fixed_roi, screenshot_name)

def _start_ocr_thread(self, image_path: str, engine_name: str, algorithms: list, 
                       fixed_roi: Optional[tuple], screenshot_name: str):
    """Start OCR processing in background thread."""
    if self.current_ocr_thread and self.current_ocr_thread.isRunning():
        self.current_ocr_thread.quit()
        self.current_ocr_thread.wait()
    
    self.current_ocr_thread = OCRWorkerThread(image_path, engine_name, algorithms, fixed_roi, screenshot_name)
    self.current_ocr_thread.ocr_completed.connect(
        lambda engine, ss_name, algo_names, t, text, conf: 
            self._ocr_completed_signal.emit(engine, ss_name, algo_names, t, text, conf)
    )
    self.current_ocr_thread.ocr_error.connect(
        lambda engine, ss_name, error: self._ocr_error_signal.emit(engine, ss_name, error)
    )
    self.current_ocr_thread.start()

def _on_ocr_completed(self, engine: str, screenshot_name: str, algo_names: str, 
                       processing_time: float, text: str, conf: str):
    """Handle OCR completion (thread-safe via signal)."""
    self.ocr_progress_bar.setVisible(False)
    self.run_ocr_btn.setEnabled(True)
    self._add_ocr_result_row(engine, algo_names, screenshot_name, text, conf, processing_time)

def _on_ocr_error(self, engine: str, screenshot_name: str, error: str):
    """Handle OCR error (thread-safe via signal)."""
    self.ocr_progress_bar.setVisible(False)
    self.run_ocr_btn.setEnabled(True)
    self._add_ocr_result_row(engine, "N/A", screenshot_name, f"Error: {error}", "N/A", 0.0)

def _add_ocr_result_row(self, engine: str, algo_names: str, screenshot_name: str, 
                         text: str, conf: str, processing_time: float):
    """Add a new row to OCR results table."""
    row = self.ocr_results_table.rowCount()
    self.ocr_results_table.insertRow(row)
    
    preview = text[:50] + "..." if len(text) > 50 else text
    
    self.ocr_results_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
    self.ocr_results_table.setItem(row, 1, QTableWidgetItem(engine.title()))
    self.ocr_results_table.setItem(row, 2, QTableWidgetItem(algo_names))
    self.ocr_results_table.setItem(row, 3, QTableWidgetItem(screenshot_name))
    self.ocr_results_table.setItem(row, 4, QTableWidgetItem(preview))
    self.ocr_results_table.setItem(row, 5, QTableWidgetItem(conf))
    self.ocr_results_table.setItem(row, 6, QTableWidgetItem(f"{processing_time:.1f}"))
```

### 3.4. OCR Worker Thread (MODIFIED - thêm Fixed ROI + screenshot_name)
```python
class OCRWorkerThread(QThread):
    """Background thread for OCR processing."""
    
    # engine, screenshot_name, algo_names, time_ms, text, conf
    ocr_completed = pyqtSignal(str, str, str, float, str, str)
    ocr_error = pyqtSignal(str, str, str)  # engine, screenshot_name, error
    
    def __init__(self, image_path: str, engine_name: str, algorithms: list, 
                 fixed_roi: Optional[tuple], screenshot_name: str):
        super().__init__()
        self.image_path = image_path
        self.engine_name = engine_name
        self.algorithms = algorithms
        self.fixed_roi = fixed_roi  # (x, y, w, h) hoặc None
        self.screenshot_name = screenshot_name
    
    def run(self):
        """Run OCR on screenshot with optional Fixed ROI crop."""
        try:
            start_time = time.perf_counter()
            
            img = cv2.imread(self.image_path)
            if img is None:
                self.ocr_error.emit(self.engine_name, self.screenshot_name, "Cannot load image")
                return
            
            # Crop theo Fixed ROI nếu có
            if self.fixed_roi:
                x, y, w, h = self.fixed_roi
                img_h, img_w = img.shape[:2]
                x2 = min(x + w, img_w)
                y2 = min(y + h, img_h)
                if x < img_w and y < img_h:
                    img = img[y:y2, x:x2]
                else:
                    self.ocr_error.emit(self.engine_name, self.screenshot_name, "Invalid ROI coordinates")
                    return
            
            # Apply tất cả algorithms
            algo_names = []
            for algo in self.algorithms:
                img = self._apply_preprocessing(img, algo.get("config", {}))
                algo_names.append(algo.get("name", "Unknown"))
            
            algo_names_str = ", ".join(algo_names) if algo_names else "None"
            
            # Run OCR
            from ..logic.system_executor.ocr_engine import OCRFactory
            engine = OCRFactory.create(self.engine_name)
            if not engine:
                self.ocr_error.emit(self.engine_name, self.screenshot_name, "Engine not available")
                return
            
            text = engine.recognize(img)
            processing_time = (time.perf_counter() - start_time) * 1000
            
            self.ocr_completed.emit(self.engine_name, self.screenshot_name, algo_names_str, 
                                     processing_time, text, "N/A")
            
        except Exception as e:
            self.ocr_error.emit(self.engine_name, self.screenshot_name, str(e))
```

### 3.5. Signal Updates (MODIFIED)
```python
# Trong MultiImageAlgorithmTestingDialog class:
# Cập nhật signal definitions
_ocr_completed_signal = pyqtSignal(str, str, str, float, str, str)  # engine, ss_name, algo_names, time, text, conf
_ocr_error_signal = pyqtSignal(str, str, str)  # engine, ss_name, error
```