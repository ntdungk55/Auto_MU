"""Multi-Image Algorithm Testing Dialog - Test preprocessing algorithms with multiple window captures."""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QListWidget, QListWidgetItem, QComboBox, QProgressBar,
                             QMessageBox, QFileDialog, QSplitter, QGraphicsView, 
                             QGraphicsScene, QGraphicsPixmapItem, QWidget, QCheckBox,
                             QSpinBox, QDoubleSpinBox, QGridLayout, QTableWidget, 
                             QTableWidgetItem, QGraphicsSimpleTextItem, QPlainTextEdit)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QThread
from PyQt6.QtGui import QPixmap, QImage, QPen, QColor, QWheelEvent, QPainter, QBrush, QFont
from PyQt6.QtWidgets import QSlider
from typing import Optional
from ..logic.action_type import AutoAction
from ..logic.system_executor.ocr_preprocessor import OCRPreprocessor
from ..logic.system_executor.template_matching_preprocessor import TemplateMatchingPreprocessor
from ..logic.system_executor.window_capture import WindowCapture
from ..logic.window_detector import WindowDetector
import os
import re
import json
import cv2
import numpy as np
import threading
import time
import tempfile
import atexit
import shutil
from datetime import datetime


class ZoomableGraphicsView(QGraphicsView):
    """Custom QGraphicsView with zoom and pan support."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 5.0
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zooming."""
        # Get the position of the mouse cursor relative to the view
        old_pos = self.mapToScene(event.position().toPoint())
        
        # Calculate zoom factor
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor
        
        # Zoom in or out
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
        
        # Check zoom limits
        new_zoom = self.zoom_factor * zoom_factor
        if new_zoom < self.min_zoom or new_zoom > self.max_zoom:
            return
        
        # Apply zoom
        self.scale(zoom_factor, zoom_factor)
        self.zoom_factor = new_zoom
        
        # Get the new position of the mouse cursor
        new_pos = self.mapToScene(event.position().toPoint())
        
        # Calculate the difference
        delta = new_pos - old_pos
        
        # Adjust the view to keep the mouse cursor at the same scene position
        self.translate(delta.x(), delta.y())
    
    def reset_zoom(self):
        """Reset zoom to 1:1."""
        self.resetTransform()
        self.zoom_factor = 1.0


class RGBRangeChannelWidget(QWidget):
    """Composite widget for one RGB min/max pair."""

    rangeChanged = pyqtSignal(int, int)

    def __init__(self, min_value: int, max_value: int, parent=None):
        super().__init__(parent)
        self._updating = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.min_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.min_slider.setRange(0, 255)
        self.min_slider.setValue(int(min_value))
        self.min_spin = QSpinBox(self)
        self.min_spin.setRange(0, 255)
        self.min_spin.setValue(int(min_value))

        self.max_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.max_slider.setRange(0, 255)
        self.max_slider.setValue(int(max_value))
        self.max_spin = QSpinBox(self)
        self.max_spin.setRange(0, 255)
        self.max_spin.setValue(int(max_value))

        layout.addWidget(QLabel("Min", self))
        layout.addWidget(self.min_slider, 1)
        layout.addWidget(self.min_spin)
        layout.addWidget(QLabel("Max", self))
        layout.addWidget(self.max_slider, 1)
        layout.addWidget(self.max_spin)

        self.min_slider.valueChanged.connect(self._sync_min_from_slider)
        self.min_spin.valueChanged.connect(self._sync_min_from_spin)
        self.max_slider.valueChanged.connect(self._sync_max_from_slider)
        self.max_spin.valueChanged.connect(self._sync_max_from_spin)
        self._apply_constraints(emit_signal=False)

    def _set_min(self, value: int) -> None:
        self.min_slider.setValue(int(value))
        self.min_spin.setValue(int(value))

    def _set_max(self, value: int) -> None:
        self.max_slider.setValue(int(value))
        self.max_spin.setValue(int(value))

    def _apply_constraints(self, emit_signal: bool = True) -> None:
        if self._updating:
            return
        self._updating = True
        min_value = min(int(self.min_slider.value()), 254)
        max_value = max(int(self.max_slider.value()), 1)
        if min_value >= max_value:
            sender = self.sender()
            if sender in (self.min_slider, self.min_spin):
                min_value = max_value - 1
            else:
                max_value = min_value + 1
        min_value = max(0, min(min_value, 254))
        max_value = max(1, min(max_value, 255))
        if min_value >= max_value:
            min_value = max(0, max_value - 1)
        self._set_min(min_value)
        self._set_max(max_value)
        self._updating = False
        if emit_signal:
            self.rangeChanged.emit(min_value, max_value)

    def _sync_min_from_slider(self, value: int) -> None:
        if self._updating:
            return
        self.min_spin.setValue(int(value))
        self._apply_constraints()

    def _sync_min_from_spin(self, value: int) -> None:
        if self._updating:
            return
        self.min_slider.setValue(int(value))
        self._apply_constraints()

    def _sync_max_from_slider(self, value: int) -> None:
        if self._updating:
            return
        self.max_spin.setValue(int(value))
        self._apply_constraints()

    def _sync_max_from_spin(self, value: int) -> None:
        if self._updating:
            return
        self.max_slider.setValue(int(value))
        self._apply_constraints()


def _apply_rgb_range_filter_to_bgr(img: np.ndarray, config: dict) -> np.ndarray:
    """Keep only pixels inside the configured BGR ranges."""
    if img is None or img.size == 0:
        return img

    red_min = int(config.get("red_min", 0))
    red_max = int(config.get("red_max", 255))
    green_min = int(config.get("green_min", 0))
    green_max = int(config.get("green_max", 255))
    blue_min = int(config.get("blue_min", 0))
    blue_max = int(config.get("blue_max", 255))

    lower = np.array([blue_min, green_min, red_min], dtype=np.uint8)
    upper = np.array([blue_max, green_max, red_max], dtype=np.uint8)
    mask = cv2.inRange(img, lower, upper) > 0

    filtered = np.zeros_like(img)
    filtered[mask] = img[mask]
    return filtered


def _apply_dominant_color_merge_to_bgr(img: np.ndarray, config: dict) -> np.ndarray:
    """Merge close colors into the most frequent nearby quantized color."""
    if img is None or img.size == 0:
        return img

    quant_step = max(1, int(config.get("quant_step", 16)))
    distance_threshold = max(0.0, float(config.get("distance_threshold", 20.0)))
    max_colors = max(1, int(config.get("max_colors", 128)))

    work = img.astype(np.uint16, copy=False)
    quantized = ((work // quant_step) * quant_step).clip(0, 255).astype(np.uint8)
    flat = quantized.reshape(-1, 3)
    unique_colors, inverse, counts = np.unique(flat, axis=0, return_inverse=True, return_counts=True)
    if len(unique_colors) <= 1:
        return quantized

    order = np.argsort(-counts)
    tracked_indices = order[: min(len(order), max_colors)]
    color_vectors = unique_colors.astype(np.int16, copy=False)
    tracked_colors = color_vectors[tracked_indices]
    threshold_sq = distance_threshold * distance_threshold

    anchor_indices: list[int] = []
    assigned = np.zeros(len(tracked_indices), dtype=bool)
    for pos, unique_idx in enumerate(tracked_indices):
        if assigned[pos]:
            continue
        anchor_indices.append(int(unique_idx))
        deltas = tracked_colors.astype(np.int32) - color_vectors[unique_idx].astype(np.int32)
        dist_sq = np.sum(deltas * deltas, axis=1, dtype=np.int32)
        assigned |= dist_sq <= threshold_sq

    if not anchor_indices:
        return quantized

    anchors = color_vectors[np.array(anchor_indices, dtype=np.int32)]
    deltas_all = color_vectors.astype(np.int32)[:, None, :] - anchors.astype(np.int32)[None, :, :]
    dist_sq_all = np.sum(deltas_all * deltas_all, axis=2, dtype=np.int32)
    nearest_anchor_pos = np.argmin(dist_sq_all, axis=1)
    nearest_dist_sq = dist_sq_all[np.arange(len(unique_colors)), nearest_anchor_pos]

    representative_indices = np.arange(len(unique_colors), dtype=np.int32)
    anchor_lookup = np.array(anchor_indices, dtype=np.int32)
    close_mask = nearest_dist_sq <= threshold_sq
    representative_indices[close_mask] = anchor_lookup[nearest_anchor_pos[close_mask]]

    merged_colors = unique_colors[representative_indices]
    return merged_colors[inverse].reshape(quantized.shape)


# Default algorithms for template matching - nhóm theo loại với phân cách
DEFAULT_ALGORITHMS = [
    # === BASIC PROCESSING ===
    {"id": "grayscale", "name": "🔘 Grayscale Only", "config": {"grayscale": True}},
    
    # === SCALING ===
    {"id": "upscale_2x", "name": "🔍 Upscale 2x", "config": {"upscale": 2.0},
     "parameters": {
         "upscale": {"type": "float", "min": 1.0, "max": 5.0, "default": 2.0, "step": 0.1, "label": "Scale Factor"}
     }},
    {"id": "upscale_3x", "name": "🔍 Upscale 3x", "config": {"upscale": 3.0},
     "parameters": {
         "upscale": {"type": "float", "min": 1.0, "max": 5.0, "default": 3.0, "step": 0.1, "label": "Scale Factor"}
     }},
    
    # === ENHANCEMENT ===
    {"id": "enhance_contrast", "name": "✨ Enhance Contrast", "config": {"enhance_contrast": True},
     "parameters": {
         "contrast_level": {"type": "float", "min": 0.5, "max": 3.0, "default": 1.5, "step": 0.1, "label": "Contrast Level"}
     }},
    {"id": "sharpen", "name": "⚡ Sharpen", "config": {"sharpen": True},
     "parameters": {
         "sharpen_strength": {"type": "float", "min": 0.1, "max": 2.0, "default": 1.0, "step": 0.1, "label": "Sharpen Strength"}
     }},
    {"id": "histogram_equalization", "name": "📊 Histogram Equalization", "config": {"histogram_equalization": True}},
    {"id": "alpha_blend_recovery", "name": "🎭 Alpha Blend Recovery", "config": {"alpha_blend_recovery": True},
     "parameters": {
         "alpha": {"type": "float", "min": 0.01, "max": 0.99, "default": 0.7, "step": 0.01, "label": "Alpha (Transparency)"},
         "sigma": {"type": "float", "min": 5.0, "max": 50.0, "default": 15.0, "step": 1.0, "label": "Sigma (Blur Strength)"}
     }},
    
    # === NOISE REMOVAL - BASIC ===
    {"id": "denoise", "name": "🧹 Denoise (Bilateral)", "config": {"denoise": True},
     "parameters": {
         "denoise_strength": {"type": "int", "min": 1, "max": 10, "default": 5, "step": 1, "label": "Denoise Strength"}
     }},
    {"id": "median_filter", "name": "🧹 Median Filter", "config": {"median_filter": True},
     "parameters": {
         "median_kernel_size": {"type": "int", "min": 3, "max": 15, "default": 5, "step": 2, "label": "Kernel Size"}
     }},
    {"id": "gaussian_blur", "name": "🌫️ Gaussian Blur", "config": {"gaussian_blur": True},
     "parameters": {
         "gaussian_kernel_size": {"type": "int", "min": 3, "max": 15, "default": 5, "step": 2, "label": "Kernel Size"},
         "gaussian_sigma_x": {"type": "float", "min": 0.0, "max": 5.0, "default": 0.0, "step": 0.1, "label": "Sigma X (0=auto)"}
     }},
    
    # === NOISE REMOVAL - MORPHOLOGICAL ===
    {"id": "morphological_opening", "name": "🔧 Morphological Opening", "config": {"morphological_opening": True},
     "parameters": {
         "opening_kernel_size": {"type": "int", "min": 2, "max": 10, "default": 3, "step": 1, "label": "Kernel Size"}
     }},
    {"id": "morphological_closing", "name": "🔧 Morphological Closing", "config": {"morphological_closing": True},
     "parameters": {
         "closing_kernel_size": {"type": "int", "min": 2, "max": 10, "default": 3, "step": 1, "label": "Kernel Size"}
     }},
    
    # === NOISE REMOVAL - ADVANCED ===
    {"id": "remove_small_components", "name": "🎯 Remove Small Components", "config": {"remove_small_components": True},
     "parameters": {
         "min_component_area": {"type": "int", "min": 10, "max": 500, "default": 50, "step": 10, "label": "Min Area (pixels)"}
     }},
    {"id": "edge_preserving_filter", "name": "🛡️ Edge-Preserving Filter", "config": {"edge_preserving_filter": True},
     "parameters": {
         "epf_flags": {"type": "choice", "choices": [{"value": 1, "label": "Recursive"}, {"value": 2, "label": "Normalized Convolution"}], "default": 1, "label": "Filter Type"},
         "epf_sigma_s": {"type": "float", "min": 10.0, "max": 200.0, "default": 50.0, "step": 10.0, "label": "Sigma S"},
         "epf_sigma_r": {"type": "float", "min": 0.1, "max": 1.0, "default": 0.4, "step": 0.1, "label": "Sigma R"}
     }},
    {"id": "nlm_denoising", "name": "🚀 Non-Local Means Denoising", "config": {"nlm_denoising": True},
     "parameters": {
         "nlm_h": {"type": "float", "min": 3.0, "max": 20.0, "default": 10.0, "step": 1.0, "label": "Filter Strength"},
         "nlm_template_window_size": {"type": "int", "min": 3, "max": 15, "default": 7, "step": 2, "label": "Template Window"},
         "nlm_search_window_size": {"type": "int", "min": 7, "max": 35, "default": 21, "step": 2, "label": "Search Window"}
     }},
    
    # === EDGE DETECTION ===
    {"id": "canny_edge_detection", "name": "🔍 Canny Edge Detection", "config": {"canny_edge_detection": True},
     "parameters": {
         "canny_low_threshold": {"type": "int", "min": 10, "max": 200, "default": 50, "step": 10, "label": "Low Threshold"},
         "canny_high_threshold": {"type": "int", "min": 50, "max": 300, "default": 150, "step": 10, "label": "High Threshold"}
     }},
    
    # === THRESHOLDING ===
    {"id": "binary_threshold", "name": "⚫ Binary Threshold", "config": {"binary_threshold": True, "threshold_value": 127, "threshold_type": 0},
     "parameters": {
         "threshold_value": {"type": "int", "min": 0, "max": 255, "default": 127, "step": 1, "label": "Threshold Value"},
         "threshold_type": {"type": "choice", "choices": [{"value": 0, "label": "BINARY"}, {"value": 1, "label": "BINARY_INV"}], "default": 0, "label": "Threshold Type"}
     }},
    {"id": "adaptive_threshold_mean", "name": "◐ Adaptive Threshold (Mean)", "config": {
        "adaptive_threshold_mean": True,
        "adaptive_max_value": 255,
        "adaptive_threshold_type": 0,
        "adaptive_block_size": 11,
        "adaptive_c": 2
    },
     "parameters": {
         "adaptive_max_value": {"type": "int", "min": 0, "max": 255, "default": 255, "step": 1, "label": "Max Value"},
         "adaptive_threshold_type": {"type": "choice", "choices": [{"value": 0, "label": "BINARY"}, {"value": 1, "label": "BINARY_INV"}], "default": 0, "label": "Threshold Type"},
         "adaptive_block_size": {"type": "int", "min": 3, "max": 255, "default": 11, "step": 2, "label": "Block Size"},
         "adaptive_c": {"type": "int", "min": -50, "max": 50, "default": 2, "step": 1, "label": "Constant C"}
     }},
    {"id": "adaptive_threshold_gaussian", "name": "◑ Adaptive Threshold (Gaussian)", "config": {
        "adaptive_threshold_gaussian": True,
        "adaptive_max_value": 255,
        "adaptive_threshold_type": 0,
        "adaptive_block_size": 11,
        "adaptive_c": 2
    },
     "parameters": {
         "adaptive_max_value": {"type": "int", "min": 0, "max": 255, "default": 255, "step": 1, "label": "Max Value"},
         "adaptive_threshold_type": {"type": "choice", "choices": [{"value": 0, "label": "BINARY"}, {"value": 1, "label": "BINARY_INV"}], "default": 0, "label": "Threshold Type"},
         "adaptive_block_size": {"type": "int", "min": 3, "max": 255, "default": 11, "step": 2, "label": "Block Size"},
         "adaptive_c": {"type": "int", "min": -50, "max": 50, "default": 2, "step": 1, "label": "Constant C"}
     }},
    {"id": "rgb_range_filter", "name": "🎨 RGB Range Filter", "config": {
        "rgb_range_filter": True,
        "red_min": 180, "red_max": 255,
        "green_min": 150, "green_max": 255,
        "blue_min": 0, "blue_max": 120,
    },
     "parameters": {
         "red_range": {"type": "rgb_range_channel", "min_key": "red_min", "max_key": "red_max", "default_min": 180, "default_max": 255, "label": "Red"},
         "green_range": {"type": "rgb_range_channel", "min_key": "green_min", "max_key": "green_max", "default_min": 150, "default_max": 255, "label": "Green"},
         "blue_range": {"type": "rgb_range_channel", "min_key": "blue_min", "max_key": "blue_max", "default_min": 0, "default_max": 120, "label": "Blue"}
    }},
    {"id": "dominant_color_merge", "name": "Dominant Color Merge", "config": {
        "dominant_color_merge": True,
        "quant_step": 16,
        "distance_threshold": 20,
        "max_colors": 128,
    },
     "parameters": {
         "quant_step": {"type": "int", "min": 1, "max": 64, "default": 16, "step": 1, "label": "Quant Step"},
         "distance_threshold": {"type": "int", "min": 0, "max": 255, "default": 20, "step": 1, "label": "Distance Threshold"},
         "max_colors": {"type": "int", "min": 1, "max": 512, "default": 128, "step": 1, "label": "Max Colors"}
     }},
]


class MultiImageAlgorithmTestingDialog(QDialog):
    """Dialog for testing multiple window captures with preprocessing algorithms."""
    
    # Signals for thread-safe UI updates
    _test_progress_signal = pyqtSignal(int, str, float)  # (index, filename, score)
    _test_complete_signal = pyqtSignal()
    _test_error_signal = pyqtSignal(int, str, str)  # (index, filename, error)
    
    # OCR signals for thread-safe UI updates
    _ocr_completed_signal = pyqtSignal(str, str, str, float, str, str)  # engine, ss_name, algo_names, time, text, conf
    _ocr_error_signal = pyqtSignal(str, str, str)  # engine, ss_name, error
    
    def __init__(self, action: AutoAction, parent=None, target_window_hwnd=None, tool_id=None, algorithm_field=None):
        super().__init__(parent)
        self.action = action
        self.target_window_hwnd = target_window_hwnd
        self.selected_window_hwnd = target_window_hwnd  # Currently selected window for capture
        self.tool_id = tool_id or "default"
        self.algorithm_field = algorithm_field  # Field name for algorithm persistence
        
        # Use teaching image based on algorithm context
        if algorithm_field == "imperial_guardian_ocr_algorithms":
            self.teaching_image_path = getattr(action, "imperial_guardian_teaching_image_path", None)
        elif algorithm_field == "golden_invasion_channel_ocr_algorithms":
            self.teaching_image_path = getattr(action, "golden_invasion_channel_teaching_image_path", None)
        elif algorithm_field == "golden_invasion_notify_ocr_algorithms":
            self.teaching_image_path = getattr(action, "golden_invasion_notify_teaching_image_path", None)
        elif algorithm_field == "monster_invasion_channel_ocr_algorithms":
            self.teaching_image_path = getattr(action, "monster_invasion_channel_teaching_image_path", None)
        elif algorithm_field == "monster_invasion_notify_ocr_algorithms":
            self.teaching_image_path = getattr(action, "monster_invasion_notify_teaching_image_path", None)
        else:
            self.teaching_image_path = getattr(action, "image_path", None)
        
        # Window detector for process selection
        self.window_detector = WindowDetector()
        
        # Create temp directory for this session
        try:
            self.temp_dir = tempfile.mkdtemp(prefix="multi_image_test_")
            print(f"[DEBUG] Created temp dir: {self.temp_dir}")
        except Exception as e:
            print(f"[ERROR] Failed to create temp dir: {e}")
            # Fallback to current directory
            self.temp_dir = os.path.join(os.getcwd(), f"temp_multi_image_{int(time.time())}")
            os.makedirs(self.temp_dir, exist_ok=True)
        
        # Register cleanup on exit
        atexit.register(self._cleanup_temp_dir)
        
        # Store temp captures as file paths (in temp dir)
        self.temp_captures = []  # List of temp file paths
        self.saved_captures = []  # List of permanent file paths
        self.next_capture_id = 1  # Counter for unique IDs
        
        self.test_results = {}  # {capture_path: score}
        self.test_match_bboxes = {}  # {capture_path: (x, y, w, h)}
        self.algorithms = DEFAULT_ALGORITHMS.copy()
        self.stop_testing = False
        
        # Progress tracking counters
        self.current_test_total = 0
        self.current_test_completed = 0
        self.current_test_window_title = ""
        self.test_sessions_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "algorithm_tests")
        )
        os.makedirs(self.test_sessions_dir, exist_ok=True)
        
        # OCR-related attributes
        self.available_ocr_engines = self._detect_available_ocr_engines()
        self.ocr_results = {}  # Cache OCR results per image
        self.current_ocr_thread = None
        self._post_ocr_ignore_vietnamese_diacritics = True
        self._post_ocr_match_threshold = float(getattr(action, "event_match_threshold", 100.0) or 100.0)
        
        # OCR UI components (will be initialized in _init_ui)
        self.ocr_engine_combo = None
        self.run_ocr_btn = None
        self.ocr_progress_bar = None
        self.ocr_results_table = None
        
        self.setWindowTitle("🧪 Multi-Image Algorithm Testing")
        self.setMinimumSize(1200, 800)  # Minimum size
        self.resize(1400, 900)  # Default size, có thể resize
        
        # Allow maximize and full screen
        self.setWindowFlags(Qt.WindowType.Window | 
                           Qt.WindowType.WindowMaximizeButtonHint | 
                           Qt.WindowType.WindowCloseButtonHint |
                           Qt.WindowType.WindowMinimizeButtonHint)
        
        self._init_ui()
        self._connect_signals()
        self._check_teaching_image()
        self._refresh_windows()  # Initialize window list
        self._load_existing_data()

    def _detect_available_ocr_engines(self) -> list:
        """Detect available OCR engines in the app."""
        engines = []
        
        # Skip OCR engine detection in test environment to avoid access violations
        import os
        if os.environ.get('PYTEST_CURRENT_TEST'):
            return ["Auto"]  # Return fallback for tests
        
        try:
            from ..logic.system_executor.ocr_engine import OCRFactory
            
            # Test each engine availability with better error handling
            test_engines = ["auto", "tesseract", "easyocr", "paddleocr", "vietocr"]  # Skip winrt initially
            for engine_name in test_engines:
                try:
                    # Try to create engine but catch all exceptions
                    engine = OCRFactory.create(engine_name)
                    if engine:
                        engines.append(engine_name.title())
                except Exception as e:
                    print(f"[DEBUG] Engine {engine_name} not available: {e}")
                    continue  # Engine not available
            
            # Add winrt separately with extra protection
            try:
                engine = OCRFactory.create("winrt")
                if engine:
                    engines.append("Winrt")
            except Exception as e:
                print(f"[DEBUG] WinRT engine not available: {e}")
                    
        except ImportError as e:
            print(f"[DEBUG] OCRFactory not available: {e}")
            # Fallback if OCRFactory not available
            engines = ["Auto"]
        except Exception as e:
            print(f"[DEBUG] Error detecting OCR engines: {e}")
            engines = ["Auto"]
        
        return engines if engines else ["Auto"]  # Always have at least Auto

    def _create_algorithm_management_widget(self) -> QWidget:
        """Create algorithm management widget (existing functionality)."""
        algo_widget = QWidget()
        algo_layout = QVBoxLayout(algo_widget)
        
        # Checkbox để kiểm soát việc áp dụng thuật toán vào preview
        self.apply_algorithms_checkbox = QCheckBox("Áp dụng thuật toán vào preview ảnh")
        self.apply_algorithms_checkbox.setChecked(False)  # Mặc định là không áp dụng
        self.apply_algorithms_checkbox.stateChanged.connect(self._on_apply_algorithms_changed)
        algo_layout.addWidget(self.apply_algorithms_checkbox)
        
        # Algorithm dropdown and add button
        algo_row = QHBoxLayout()
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.setMinimumWidth(200)  # Set minimum width
        # Thêm các algorithm thực sự hữu ích (bỏ None Original)
        for algo in self.algorithms:
            self.algorithm_combo.addItem(algo["name"], algo)
        # Dropdown chỉ để chọn algorithm để thêm vào list, không affect preview
        algo_row.addWidget(self.algorithm_combo)
        
        add_algo_btn = QPushButton("➕ Add")
        add_algo_btn.setFixedWidth(80)  # Fixed width instead of stretching
        add_algo_btn.clicked.connect(self._add_algorithm)
        algo_row.addWidget(add_algo_btn)
        
        algo_row.addStretch()  # Add stretch to push items to left
        algo_layout.addLayout(algo_row)
        
        # Algorithm list
        self.algorithms_list = QListWidget()
        self.algorithms_list.setMaximumHeight(120)  # Fixed height for responsive layout
        self.algorithms_list.setMinimumHeight(80)   # Minimum height to prevent too small
        self.algorithms_list.setMaximumWidth(600)   # Max width to prevent over-stretching
        
        # Improve scroll behavior - smaller steps
        self.algorithms_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.algorithms_list.verticalScrollBar().setSingleStep(3)  # Very small scroll step
        self.algorithms_list.verticalScrollBar().setPageStep(30)   # Page scroll step
        
        algo_layout.addWidget(self.algorithms_list, stretch=0)  # No stretch - fixed size
        
        return algo_widget

    def _create_ocr_testing_widget(self) -> QWidget:
        """Create OCR testing widget."""
        ocr_widget = QWidget()
        ocr_layout = QVBoxLayout(ocr_widget)
        
        # OCR Controls
        ocr_layout.addWidget(QLabel("🔍 OCR Testing"))
        
        controls_layout = QHBoxLayout()
        
        # Engine selection (auto-detected)
        controls_layout.addWidget(QLabel("Engine:"))
        self.ocr_engine_combo = QComboBox()
        self.ocr_engine_combo.addItems(self.available_ocr_engines)
        controls_layout.addWidget(self.ocr_engine_combo)
        
        # Run OCR button
        self.run_ocr_btn = QPushButton("▶️ Run OCR")
        self.run_ocr_btn.clicked.connect(self._run_ocr)
        controls_layout.addWidget(self.run_ocr_btn)
        
        controls_layout.addStretch()
        ocr_layout.addLayout(controls_layout)
        
        # Progress bar
        self.ocr_progress_bar = QProgressBar()
        self.ocr_progress_bar.setVisible(False)
        ocr_layout.addWidget(self.ocr_progress_bar)
        
        # Results table
        ocr_layout.addWidget(QLabel("📊 OCR Results"))
        self.ocr_results_table = QTableWidget()
        self.ocr_results_table.setColumnCount(7)
        self.ocr_results_table.setHorizontalHeaderLabels(
            ["No.", "Engine", "Algorithms", "Screenshot", "Text", "Conf", "Time (ms)"]
        )
        self.ocr_results_table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.ocr_results_table.cellClicked.connect(self._on_ocr_cell_clicked)
        ocr_layout.addWidget(self.ocr_results_table)
        
        return ocr_widget
    
    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Preview area (30/70 split - Teaching nhỏ, Window Capture lớn)
        preview_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Teaching preview (nhỏ hơn)
        teaching_widget = QWidget()
        teaching_layout = QVBoxLayout(teaching_widget)
        teaching_layout.addWidget(QLabel("📷 Teaching Image (Scroll: Pan, Wheel: Zoom)"))
        self.teaching_view = ZoomableGraphicsView()
        self.teaching_view.setMaximumWidth(400)  # Giới hạn width
        self.teaching_scene = QGraphicsScene()
        self.teaching_view.setScene(self.teaching_scene)
        teaching_layout.addWidget(self.teaching_view)
        preview_splitter.addWidget(teaching_widget)
        
        # Window capture preview (lớn hơn)
        capture_widget = QWidget()
        capture_layout = QVBoxLayout(capture_widget)
        capture_layout.addWidget(QLabel("🖼️ Window Capture (Scroll: Pan, Wheel: Zoom)"))
        self.capture_view = ZoomableGraphicsView()
        self.capture_scene = QGraphicsScene()
        self.capture_view.setScene(self.capture_scene)
        capture_layout.addWidget(self.capture_view)
        preview_splitter.addWidget(capture_widget)
        
        # Set splitter ratios: 30% teaching, 70% capture (responsive)
        preview_splitter.setSizes([300, 700])
        
        layout.addWidget(preview_splitter, stretch=5)  # High stretch for responsive preview area
        
        # Load teaching image
        self._load_teaching_preview()
        
        # Window Captures List (fixed height for responsive layout)
        threshold_label = QLabel(f"🖼️ Window Captures (Max 50) - Threshold: {self.action.match_threshold:.2f}")
        layout.addWidget(threshold_label)
        self.captures_list = QListWidget()
        self.captures_list.setMaximumHeight(200)  # Fixed max height for responsive layout
        self.captures_list.setMaximumWidth(800)   # Max width to prevent over-stretching
        self.captures_list.itemClicked.connect(self._on_capture_selected)
        
        # Improve scroll behavior - smaller steps
        self.captures_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.captures_list.verticalScrollBar().setSingleStep(5)  # Small scroll step
        self.captures_list.verticalScrollBar().setPageStep(50)   # Page scroll step
        
        layout.addWidget(self.captures_list, stretch=0)  # No stretch - fixed size
        
        # Buttons for captures (bỏ Remove Selected button)
        btn_row = QHBoxLayout()
        self.load_btn = QPushButton("📁 Upload Local...")
        self.load_btn.setMinimumWidth(120)  # Set minimum width
        self.load_btn.clicked.connect(self._load_images)
        
        # Window selection for capture
        self.window_combo = QComboBox()
        self.window_combo.setMinimumWidth(200)
        self.window_combo.setToolTip("Chọn window để chụp ảnh")
        btn_row.addWidget(self.window_combo)
        
        self.refresh_window_btn = QPushButton("🔄")
        self.refresh_window_btn.setFixedWidth(30)
        self.refresh_window_btn.setToolTip("Làm mới danh sách window")
        self.refresh_window_btn.clicked.connect(self._refresh_windows)
        btn_row.addWidget(self.refresh_window_btn)
        
        self.capture_btn = QPushButton("📷 Capture New")
        self.capture_btn.setMinimumWidth(120)  # Set minimum width
        self.capture_btn.clicked.connect(self._capture_new)
        btn_row.addWidget(self.capture_btn)

        btn_row.addWidget(self.load_btn)
        
        btn_row.addStretch()  # Add stretch to push buttons to left
        layout.addLayout(btn_row)
        
        # Auto-save label
        save_path = f"images/{self.tool_id}/{self.action.name}/window_captures/"
        layout.addWidget(QLabel(f"Auto-saved to: {save_path}"))
        
        # Algorithm Management - sửa thành horizontal layout với OCR section
        layout.addWidget(QLabel("⚙️ Process Algorithm"))
        
        # Create horizontal splitter for Algorithm Management + OCR Testing
        process_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: Algorithm Management (existing)
        algo_widget = self._create_algorithm_management_widget()
        process_splitter.addWidget(algo_widget)
        
        # Right: OCR Testing Section (new)
        ocr_widget = self._create_ocr_testing_widget()
        process_splitter.addWidget(ocr_widget)
        
        # Set splitter ratios: 60% algorithm, 40% OCR
        process_splitter.setSizes([600, 400])
        
        layout.addWidget(process_splitter)
        
        # Matching controls stay beside the test button so the dialog does not
        # add another large settings panel.
        test_btn_row = QHBoxLayout()
        test_btn_row.addWidget(QLabel("Matching:"))
        self.matching_method_combo = QComboBox()
        self.matching_method_combo.addItem("Template", "template")
        self.matching_method_combo.addItem("Color (Auto)", "color")
        self.matching_method_combo.setToolTip(
            "Color (Auto) extracts the useful colors from the teaching image and searches by color regions."
        )
        self.matching_method_combo.currentIndexChanged.connect(self._update_color_matching_controls)
        test_btn_row.addWidget(self.matching_method_combo)

        self.color_matching_controls = QWidget()
        color_layout = QHBoxLayout(self.color_matching_controls)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.setSpacing(6)
        color_layout.addWidget(QLabel("Sensitivity:"))
        self.color_sensitivity_combo = QComboBox()
        self.color_sensitivity_combo.addItem("Strict", 1.5)
        self.color_sensitivity_combo.addItem("Balanced", 2.0)
        self.color_sensitivity_combo.addItem("Wide", 3.0)
        self.color_sensitivity_combo.setCurrentIndex(1)
        self.color_sensitivity_combo.setToolTip("How far a screen color may differ from the colors learned from the teaching image.")
        color_layout.addWidget(self.color_sensitivity_combo)
        color_layout.addWidget(QLabel("Min. color match:"))
        self.color_min_match_spin = QSpinBox()
        self.color_min_match_spin.setRange(10, 100)
        self.color_min_match_spin.setValue(70)
        self.color_min_match_spin.setSuffix("%")
        self.color_min_match_spin.setToolTip("Minimum color coverage required in a candidate region.")
        color_layout.addWidget(self.color_min_match_spin)
        self.color_ignore_background_checkbox = QCheckBox("Ignore background")
        self.color_ignore_background_checkbox.setChecked(True)
        self.color_ignore_background_checkbox.setToolTip("Ignore dull or dark pixels while learning colors from the teaching image.")
        color_layout.addWidget(self.color_ignore_background_checkbox)
        test_btn_row.addWidget(self.color_matching_controls)
        self._update_color_matching_controls()

        self.test_btn = QPushButton("🧪 Test Checked Images")
        self.test_btn.setMinimumWidth(150)  # Set minimum width
        self.test_btn.clicked.connect(self._run_test)
        test_btn_row.addWidget(self.test_btn)
        
        self.stop_btn = QPushButton("⏸️ Stop")
        self.stop_btn.setFixedWidth(80)  # Fixed width
        self.stop_btn.clicked.connect(self._stop_test)
        self.stop_btn.setEnabled(False)
        test_btn_row.addWidget(self.stop_btn)
        
        test_btn_row.addStretch()  # Add stretch to push buttons to left
        layout.addLayout(test_btn_row)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(600)  # Max width to prevent over-stretching
        self.progress_bar.setValue(0)  # Initialize to 0
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        layout.addWidget(self.progress_label)
        
        # Bottom buttons
        bottom_row = QHBoxLayout()
        
        # Add Apply buttons
        self._add_apply_buttons(bottom_row)
        
        bottom_row.addStretch()
        
        ok_btn = QPushButton("✅ OK")
        ok_btn.setFixedWidth(80)  # Fixed width
        ok_btn.clicked.connect(self._on_ok)
        bottom_row.addWidget(ok_btn)
        
        close_btn = QPushButton("❌ Close")
        close_btn.setFixedWidth(80)  # Fixed width
        close_btn.clicked.connect(self.reject)
        bottom_row.addWidget(close_btn)
        
        layout.addLayout(bottom_row)
        
        self.setLayout(layout)

    def _update_color_matching_controls(self) -> None:
        """Show the three compact Color (Auto) controls only when needed."""
        if hasattr(self, "color_matching_controls"):
            self.color_matching_controls.setVisible(
                self.matching_method_combo.currentData() == "color"
            )
    
    def _add_apply_buttons(self, layout):
        """Add Apply buttons for different modes."""
        self.apply_template_btn = QPushButton("📤 Apply to Template Matching")
        self.apply_template_btn.setFixedWidth(200)
        self.apply_template_btn.clicked.connect(self._apply_to_template_matching)
        layout.addWidget(self.apply_template_btn)
        
        self.apply_ocr_btn = QPushButton("📤 Apply to OCR Mode")
        self.apply_ocr_btn.setFixedWidth(150)
        self.apply_ocr_btn.clicked.connect(self._apply_to_ocr_mode)
        layout.addWidget(self.apply_ocr_btn)
    
    def _apply_to_template_matching(self):
        """Apply current algorithms to template matching."""
        algorithms = self._get_current_algorithms()
        self.action.template_matching_algorithms = algorithms
        QMessageBox.information(self, "Thành công", 
            f"Đã apply {len(algorithms)} algorithms cho Template Matching!")
    
    def _apply_to_ocr_mode(self):
        """Apply current algorithms to OCR mode."""
        algorithms = self._get_current_algorithms()
        # Save to specified algorithm field
        if self.algorithm_field:
            setattr(self.action, self.algorithm_field, algorithms)
        else:
            self.action.template_matching_algorithms = algorithms
        QMessageBox.information(self, "Thành công", 
            f"Đã apply {len(algorithms)} algorithms cho OCR Mode!")
    
    def _get_current_algorithms(self):
        """Extract algorithms from algorithms_list widget."""
        self._sync_algorithm_configs_from_widgets()
        algorithms = []
        
        # Get current algorithms from the algorithms list
        for i in range(self.algorithms_list.count()):
            item = self.algorithms_list.item(i)
            algorithm_data = item.data(Qt.ItemDataRole.UserRole)
            if algorithm_data:
                algorithms.append(algorithm_data)
        
        return algorithms

    def _sync_algorithm_configs_from_widgets(self):
        """Force-sync algorithm config from visible parameter widgets."""
        for i in range(self.algorithms_list.count()):
            item = self.algorithms_list.item(i)
            if not item:
                continue
            algo = item.data(Qt.ItemDataRole.UserRole)
            widget = self.algorithms_list.itemWidget(item)
            if not algo or not widget or not hasattr(widget, "parameter_widgets"):
                continue

            parameters = algo.get("parameters", {}) or {}
            for param_name, param_widget in getattr(widget, "parameter_widgets", {}).items():
                param_def = parameters.get(param_name, {})
                param_type = param_def.get("type")
                if param_type == "rgb_range_channel" and isinstance(param_widget, RGBRangeChannelWidget):
                    min_key = param_def.get("min_key")
                    max_key = param_def.get("max_key")
                    algo["config"]["rgb_range_filter"] = True
                    algo["config"][min_key] = int(param_widget.min_spin.value())
                    algo["config"][max_key] = int(param_widget.max_spin.value())
                elif isinstance(param_widget, QSpinBox):
                    algo["config"][param_name] = int(param_widget.value())
                elif isinstance(param_widget, QDoubleSpinBox):
                    algo["config"][param_name] = float(param_widget.value())
                elif isinstance(param_widget, QComboBox):
                    algo["config"][param_name] = param_widget.currentData()

            item.setData(Qt.ItemDataRole.UserRole, algo)
    
    def _connect_signals(self):
        """Connect signals for thread-safe UI updates."""
        self._test_progress_signal.connect(self._on_test_progress, Qt.ConnectionType.QueuedConnection)
        self._test_complete_signal.connect(self._on_test_complete, Qt.ConnectionType.QueuedConnection)
        self._test_error_signal.connect(self._on_test_error, Qt.ConnectionType.QueuedConnection)
        
        # OCR signals
        self._ocr_completed_signal.connect(self._on_ocr_completed, Qt.ConnectionType.QueuedConnection)
        self._ocr_error_signal.connect(self._on_ocr_error, Qt.ConnectionType.QueuedConnection)
    
    def _check_teaching_image(self):
        """Check if teaching image exists."""
        if not self.teaching_image_path or not os.path.exists(self.teaching_image_path):
            QMessageBox.warning(self, "Cảnh báo", 
                "Teaching image không tồn tại!\nVui lòng chọn teaching image trước.")
            self.test_btn.setEnabled(False)
            self.load_btn.setEnabled(False)
            self.capture_btn.setEnabled(False)
    
    def _load_teaching_preview(self):
        """Load teaching image into preview with algorithms applied and mask support."""
        if not self.teaching_image_path or not os.path.exists(self.teaching_image_path):
            return
        
        # Load image using cv2 for algorithm processing
        try:
            # Use Unicode-safe loading method
            with open(self.teaching_image_path, 'rb') as f:
                file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
            cv_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            
            if cv_img is None:
                # Fallback to QPixmap
                pixmap = QPixmap(self.teaching_image_path)
            else:
                # Apply all algorithms from the algorithms list in sequence
                processed_img = cv_img.copy()
                algorithms_applied = []
                
                # Calculate total upscale factor from algorithms
                total_upscale = 1.0
                
                # Check if algorithms_list exists and checkbox is checked
                if (hasattr(self, 'algorithms_list') and self.algorithms_list and 
                    hasattr(self, 'apply_algorithms_checkbox') and self.apply_algorithms_checkbox.isChecked()):
                    for i in range(self.algorithms_list.count()):
                        list_item = self.algorithms_list.item(i)
                        if list_item:
                            algorithm = list_item.data(Qt.ItemDataRole.UserRole)
                            if algorithm:
                                if algorithm["config"].get("upscale"):
                                    total_upscale *= algorithm["config"]["upscale"]
                                processed_img = self._apply_preprocessing(processed_img, algorithm["config"])
                                algorithms_applied.append(algorithm["name"])
                
                if algorithms_applied:
                    print(f"[DEBUG] Applied {len(algorithms_applied)} algorithms to teaching image: {', '.join(algorithms_applied)}")
                
                # Store upscale factor for mask scaling
                self._teaching_preview_upscale = total_upscale
                
                # Convert BGR to RGB for Qt
                rgb_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_img.shape
                bytes_per_line = ch * w
                
                # Create QImage and QPixmap
                q_image = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(q_image)
                
        except Exception as e:
            print(f"[DEBUG] Error processing teaching image: {e}")
            # Fallback to QPixmap
            pixmap = QPixmap(self.teaching_image_path)
            # No upscale if fallback
            self._teaching_preview_upscale = 1.0
        
        if pixmap.isNull():
            print(f"[DEBUG] Failed to load teaching image pixmap")
            return
        
        # Set default upscale if not set
        if not hasattr(self, '_teaching_preview_upscale'):
            self._teaching_preview_upscale = 1.0
        
        self.teaching_scene.clear()
        pixmap_item = self.teaching_scene.addPixmap(pixmap)
        
        # Enable smooth transformation
        pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        
        # Set scene rect to match pixmap bounds (keep original size)
        self.teaching_scene.setSceneRect(pixmap_item.boundingRect())
        
        # Don't auto-scale - let user scroll and zoom
        self.teaching_view.resetTransform()
        
        # Load and display mask regions if available
        self._load_teaching_masks()
    
    def _load_teaching_masks(self):
        """Load and display mask regions on teaching image."""
        mask_regions = getattr(self.action, 'mask_regions', [])
        if not mask_regions:
            return
        
        # Get upscale factor from preview (if algorithms were applied)
        upscale = getattr(self, '_teaching_preview_upscale', 1.0)
        
        print(f"[DEBUG] Loading {len(mask_regions)} mask regions (upscale: {upscale})")
        
        for region in mask_regions:
            try:
                x = float(region.get("x", 0))
                y = float(region.get("y", 0))
                w = float(region.get("w", 0))
                h = float(region.get("h", 0))
                
                # Scale mask regions according to upscale factor
                if upscale != 1.0:
                    x = x * upscale
                    y = y * upscale
                    w = w * upscale
                    h = h * upscale
                
                # Create mask rectangle
                rect = QRectF(x, y, w, h)
                mask_item = self.teaching_scene.addRect(rect)
                
                # Style mask (red semi-transparent)
                from PyQt6.QtGui import QPen, QBrush, QColor
                pen = QPen(QColor(255, 0, 0), 2)  # Red border
                brush = QBrush(QColor(255, 0, 0, 80))  # Red semi-transparent fill
                mask_item.setPen(pen)
                mask_item.setBrush(brush)
                mask_item.setZValue(1000)  # Above image
                
            except Exception as e:
                print(f"[WARN] Cannot load mask region: {e}")
    
    def _cleanup_temp_dir(self):
        """Clean up temp directory."""
        try:
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir)
                print(f"[DEBUG] Cleaned up temp dir: {self.temp_dir}")
                self.temp_dir = None  # Mark as cleaned
        except Exception as e:
            print(f"[WARN] Failed to cleanup temp dir: {e}")
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        self._cleanup_temp_dir()
        # Remove from atexit to prevent double cleanup
        try:
            atexit.unregister(self._cleanup_temp_dir)
        except ValueError:
            pass  # Already unregistered
        super().closeEvent(event)
    
    def _load_existing_data(self):
        """Load existing window captures and results from action."""
        # Load saved captures from files
        for path in getattr(self.action, "window_capture_paths", []):
            if os.path.exists(path):
                self.saved_captures.append(path)
                self._add_saved_capture_to_list(path)
        
        # Load test results
        self.test_results = dict(getattr(self.action, "window_capture_results", {}))
        
        # Load algorithms from correct field based on context
        if self.algorithm_field:
            saved_algorithms = getattr(self.action, self.algorithm_field, [])
        else:
            saved_algorithms = getattr(self.action, "template_matching_algorithms", [])
        if saved_algorithms:
            for algo in saved_algorithms:
                # Find the matching algorithm definition from self.algorithms
                matching_algo = None
                for available_algo in self.algorithms:
                    if available_algo["id"] == algo.get("id") or available_algo["name"] == algo.get("name"):
                        matching_algo = available_algo.copy()
                        # Update config with saved values
                        matching_algo["config"] = algo.get("config", {})
                        break
                
                if matching_algo:
                    # Use _add_algorithm logic to create proper UI widget
                    self._add_algorithm_from_data(matching_algo)
                else:
                    # Fallback: create simple item if algorithm definition not found
                    item = QListWidgetItem(algo["name"])
                    item.setData(Qt.ItemDataRole.UserRole, algo)
                    self.algorithms_list.addItem(item)
            print(f"[DEBUG] Loaded {len(saved_algorithms)} algorithms from action.{self.algorithm_field or 'template_matching_algorithms'}")
        
        # Update display
        self._update_results_display()
    
    def _get_capture_folder(self):
        """Get folder for window captures."""
        action_name = str(getattr(self.action, "name", "") or "").strip()
        safe_action_name = re.sub(r'[<>:"/\\|?*]', "", action_name).strip().rstrip(". ")
        if not safe_action_name:
            safe_action_name = "unnamed_action"
        folder = f"images/{self.tool_id}/{safe_action_name}/window_captures/"
        os.makedirs(folder, exist_ok=True)
        return folder

    def _save_test_session(self) -> None:
        """Persist the current test resources as an independent session."""
        if self.current_test_total <= 0:
            return

        session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        session_dir = os.path.join(self.test_sessions_dir, session_id)
        captures_dir = os.path.join(session_dir, "captures")
        os.makedirs(captures_dir, exist_ok=True)

        captures = []
        for index in range(self.captures_list.count()):
            item = self.captures_list.item(index)
            source_path = item.data(Qt.ItemDataRole.UserRole) if item else None
            if not source_path or not os.path.isfile(source_path):
                continue
            filename = f"capture_{index + 1:03d}{os.path.splitext(source_path)[1].lower() or '.png'}"
            destination = os.path.join(captures_dir, filename)
            try:
                shutil.copy2(source_path, destination)
            except OSError as exc:
                print(f"[WARN] Cannot save test session capture {source_path}: {exc}")
                continue
            captures.append({
                "filename": filename,
                "source_name": os.path.basename(source_path),
                "score": self.test_results.get(source_path),
                "bbox": list(self.test_match_bboxes[source_path]) if source_path in self.test_match_bboxes else None,
            })

        teaching_image_name = None
        if self.teaching_image_path and os.path.isfile(self.teaching_image_path):
            teaching_image_name = "teaching.png"
            try:
                shutil.copy2(
                    self.teaching_image_path,
                    os.path.join(session_dir, teaching_image_name),
                )
            except OSError as exc:
                print(f"[WARN] Cannot save teaching image for test session: {exc}")
                teaching_image_name = None

        metadata = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "window_title": self.current_test_window_title,
            "window_hwnd": self.selected_window_hwnd,
            "matching_method": self.matching_method_combo.currentData(),
            "algorithms": self._get_current_algorithms(),
            "teaching_image": teaching_image_name,
            "captures": captures,
        }
        try:
            with open(os.path.join(session_dir, "session.json"), "w", encoding="utf-8") as handle:
                json.dump(metadata, handle, ensure_ascii=False, indent=2)
        except (OSError, TypeError, ValueError) as exc:
            print(f"[WARN] Cannot save test session metadata: {exc}")
            shutil.rmtree(session_dir, ignore_errors=True)
            return

        parent = self.parent()
        if parent is not None and hasattr(parent, "_load_test_sessions"):
            parent._load_test_sessions()

    def load_test_session(self, session_dir: str) -> None:
        """Load a saved session into the current dialog."""
        if not session_dir:
            return
        metadata_path = os.path.join(session_dir, "session.json")
        try:
            with open(metadata_path, "r", encoding="utf-8") as handle:
                metadata = json.load(handle)
        except (OSError, ValueError, TypeError) as exc:
            QMessageBox.warning(self, "Lỗi", f"Không thể đọc phiên test: {exc}")
            return

        self.temp_captures.clear()
        self.saved_captures.clear()
        self.test_results.clear()
        self.test_match_bboxes.clear()
        self.captures_list.clear()

        captures_dir = os.path.join(session_dir, "captures")
        for capture in metadata.get("captures", []):
            filename = capture.get("filename")
            path = os.path.join(captures_dir, filename) if filename else ""
            if not os.path.isfile(path):
                continue
            self.saved_captures.append(path)
            self._add_saved_capture_to_list(path)
            score = capture.get("score")
            if score is not None:
                self.test_results[path] = float(score)
            bbox = capture.get("bbox")
            if bbox and len(bbox) == 4:
                self.test_match_bboxes[path] = tuple(bbox)

        self.current_test_window_title = metadata.get("window_title", "")
        self.selected_window_hwnd = metadata.get("window_hwnd") or self.selected_window_hwnd

        matching_method = metadata.get("matching_method")
        if matching_method:
            index = self.matching_method_combo.findData(matching_method)
            if index >= 0:
                self.matching_method_combo.setCurrentIndex(index)

        while self.algorithms_list.count():
            self.algorithms_list.takeItem(0)
        for algorithm in metadata.get("algorithms", []):
            self._add_algorithm_from_data(algorithm)

        self.current_test_total = len(metadata.get("captures", []))
        self.current_test_completed = self.current_test_total
        self.progress_bar.setValue(100 if self.current_test_total else 0)
        self.progress_label.setText(
            f"Đã nạp phiên test ({self.current_test_total}/{self.current_test_total})"
            if self.current_test_total else "Phiên test không có ảnh"
        )
        self._update_results_display()
    
    def _get_next_capture_filename(self):
        """Get next capture filename."""
        folder = self._get_capture_folder()
        existing = [f for f in os.listdir(folder) if f.startswith("capture_") and f.endswith(".png")]
        
        if not existing:
            return os.path.join(folder, "capture_001.png")
        
        numbers = [int(f.split("_")[1].split(".")[0]) for f in existing]
        next_num = max(numbers) + 1
        return os.path.join(folder, f"capture_{next_num:03d}.png")
    
    def _load_images(self):
        """Load images from local files and save to temp directory."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Chọn window captures", "", "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )
        
        if not file_paths:
            return
        
        for file_path in file_paths:
            total_captures = len(self.temp_captures) + len(self.saved_captures)
            if total_captures >= 50:
                QMessageBox.warning(self, "Cảnh báo", "Đã đạt giới hạn 50 window captures!")
                break
            
            try:
                # Copy to temp directory
                temp_filename = f"loaded_{self.next_capture_id:03d}.png"
                temp_path = os.path.join(self.temp_dir, temp_filename)
                
                import shutil
                shutil.copy2(file_path, temp_path)
                
                if not os.path.exists(temp_path):
                    print(f"[WARN] Failed to copy to temp: {temp_path}")
                    continue
                
                self.temp_captures.append(temp_path)
                self.next_capture_id += 1
                
                print(f"[DEBUG] Image copied to temp: {temp_path}")
                self._add_temp_capture_to_list(temp_path)
                
            except Exception as e:
                print(f"[WARN] Error copying image {file_path}: {e}")
    
    def _capture_new(self):
        """Capture new screenshot and save to temp file."""
        hwnd = self.selected_window_hwnd or self.target_window_hwnd
        
        if not hwnd:
            QMessageBox.warning(self, "Cảnh báo", "Chưa chọn window để chụp ảnh!")
            return
        
        total_captures = len(self.temp_captures) + len(self.saved_captures)
        if total_captures >= 50:
            QMessageBox.warning(self, "Cảnh báo", "Đã đạt giới hạn 50 window captures!")
            return
        
        try:
            # Create WindowCapture instance
            capturer = WindowCapture(hwnd)
            screenshot = capturer.capture()
            
            if screenshot is None:
                QMessageBox.warning(self, "Lỗi", "Không thể chụp screenshot!")
                return
            
            # Save to temp file
            temp_filename = f"capture_{self.next_capture_id:03d}.png"
            temp_path = os.path.join(self.temp_dir, temp_filename)
            
            # Use cv2.imencode for Unicode path support
            success, encoded_img = cv2.imencode('.png', screenshot)
            if not success:
                QMessageBox.warning(self, "Lỗi", "Không thể encode ảnh!")
                return
            
            # Write to file
            try:
                with open(temp_path, 'wb') as f:
                    f.write(encoded_img.tobytes())
            except Exception as e:
                QMessageBox.warning(self, "Lỗi", f"Không thể lưu temp file: {e}")
                return
            
            # Verify file was written successfully
            if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                QMessageBox.warning(self, "Lỗi", f"File temp không hợp lệ: {temp_path}")
                return
            
            self.temp_captures.append(temp_path)
            self.next_capture_id += 1
            
            print(f"[DEBUG] Screenshot saved to temp: {temp_path} (size: {os.path.getsize(temp_path)} bytes)")
            self._add_temp_capture_to_list(temp_path)
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi khi chụp screenshot: {e}")
            import traceback
            traceback.print_exc()
    
    def _refresh_windows(self):
        """Refresh window list for capture selection."""
        self.window_combo.clear()

        # Keep all detected game windows selectable, while putting the
        # requested Season 21 naming scheme first when it is present.
        prefix = "MU GamethuVN - Season 21"
        windows = list(self.window_detector.find_game_windows())
        windows.sort(key=lambda pair: not str(pair[1]).strip().lower().startswith(prefix.lower()))
        
        if not windows:
            self.window_combo.addItem("Không tìm thấy window", None)
        else:
            for hwnd, title in windows:
                self.window_combo.addItem(title, hwnd)
        
        # Set default selection to target_window_hwnd if available
        if self.target_window_hwnd:
            for i in range(self.window_combo.count()):
                if self.window_combo.itemData(i) == self.target_window_hwnd:
                    self.window_combo.setCurrentIndex(i)
                    self.selected_window_hwnd = self.target_window_hwnd
                    break
        
        # Connect selection change
        self.window_combo.currentIndexChanged.connect(self._on_window_selected)
    
    def _on_window_selected(self, index):
        """Handle window selection change."""
        if index >= 0:
            hwnd = self.window_combo.itemData(index)
            self.selected_window_hwnd = hwnd
            print(f"[DEBUG] Selected window for capture: {hwnd}")
    
    def _add_temp_capture_to_list(self, temp_path):
        """Add temporary capture to list with remove button."""
        filename = os.path.basename(temp_path)
        
        # Create custom widget for list item
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(5, 2, 5, 2)
        
        # Checkbox
        checkbox = QCheckBox()
        checkbox.setChecked(True)  # Auto-check new items
        item_layout.addWidget(checkbox)
        
        # Label with filename and status
        label = QLabel(f"{filename} | Not tested yet (temp)")
        label.setStyleSheet("QLabel { padding: 2px; }")
        item_layout.addWidget(label)
        
        item_layout.addStretch()
        
        # Remove button
        remove_btn = QPushButton("🗑️")
        remove_btn.setFixedSize(25, 25)
        remove_btn.setToolTip("Remove this capture")
        remove_btn.clicked.connect(lambda: self._remove_capture_item(temp_path))
        item_layout.addWidget(remove_btn)
        
        # Create list item
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, temp_path)
        item.setSizeHint(item_widget.sizeHint())
        
        self.captures_list.addItem(item)
        self.captures_list.setItemWidget(item, item_widget)
        
        # Store references for later updates
        item_widget.checkbox = checkbox
        item_widget.label = label
        item_widget.path = temp_path
        
        # Auto-select and display newly added capture
        self.captures_list.setCurrentItem(item)
        self._on_capture_selected(item)
    
    def _add_saved_capture_to_list(self, path):
        """Add saved capture (from file) to list with remove button."""
        filename = os.path.basename(path)
        
        # Create custom widget for list item
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(5, 2, 5, 2)
        
        # Checkbox
        checkbox = QCheckBox()
        checkbox.setChecked(True)  # Auto-check saved items too
        item_layout.addWidget(checkbox)
        
        # Label with filename and status
        label = QLabel(f"{filename} | Not tested yet")
        label.setStyleSheet("QLabel { padding: 2px; }")
        item_layout.addWidget(label)
        
        item_layout.addStretch()
        
        # Remove button
        remove_btn = QPushButton("🗑️")
        remove_btn.setFixedSize(25, 25)
        remove_btn.setToolTip("Remove this capture")
        remove_btn.clicked.connect(lambda: self._remove_capture_item(path))
        item_layout.addWidget(remove_btn)
        
        # Create list item
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setSizeHint(item_widget.sizeHint())
        
        self.captures_list.addItem(item)
        self.captures_list.setItemWidget(item, item_widget)
        
        # Store references for later updates
        item_widget.checkbox = checkbox
        item_widget.label = label
        item_widget.path = path
    
    def _get_capture_data(self, item_data):
        """Get capture data from item data (always a file path now)."""
        if isinstance(item_data, str) and os.path.exists(item_data):
            return {"path": item_data, "type": "file"}
        return None
    
    def _remove_capture_item(self, path: str):
        """Remove individual capture item."""
        # Remove from appropriate list
        if path in self.temp_captures:
            self.temp_captures.remove(path)
        elif path in self.saved_captures:
            self.saved_captures.remove(path)
        
        # Remove from test results
        if path in self.test_results:
            del self.test_results[path]
        if path in self.test_match_bboxes:
            del self.test_match_bboxes[path]
        
        # Remove from UI list
        for i in range(self.captures_list.count()):
            item = self.captures_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == path:
                self.captures_list.takeItem(i)
                break
    
    def _remove_selected(self):
        """Remove selected captures (updated for custom widgets)."""
        items_to_remove = []
        for i in range(self.captures_list.count()):
            item = self.captures_list.item(i)
            widget = self.captures_list.itemWidget(item)
            if widget and hasattr(widget, 'checkbox') and widget.checkbox.isChecked():
                items_to_remove.append((item, widget.path))
        
        for item, path in items_to_remove:
            # Remove from appropriate list
            if path in self.temp_captures:
                self.temp_captures.remove(path)
            elif path in self.saved_captures:
                self.saved_captures.remove(path)
            
            # Remove from test results
            if path in self.test_results:
                del self.test_results[path]
            if path in self.test_match_bboxes:
                del self.test_match_bboxes[path]
            
            # Remove from UI list
            row = self.captures_list.row(item)
            self.captures_list.takeItem(row)
    
    def _on_capture_selected(self, item):
        """Show selected capture in preview with algorithms from list applied."""
        item_data = item.data(Qt.ItemDataRole.UserRole)
        capture_data = self._get_capture_data(item_data)
        
        if not capture_data:
            print(f"[DEBUG] No capture data found for: {item_data}")
            return
        
        path = capture_data["path"]
        print(f"[DEBUG] Loading capture from: {path}")
        
        # Load pixmap from file (both temp and saved are files now)
        if not os.path.exists(path):
            print(f"[DEBUG] File not found: {path}")
            return
        
        # Use Unicode-safe loading method
        try:
            # Load image using cv2.imdecode for Unicode path support
            with open(path, 'rb') as f:
                file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
            cv_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            
            if cv_img is None:
                print(f"[DEBUG] Failed to decode image from: {path}")
                return
            
            original_h, original_w = cv_img.shape[:2]

            # Apply all algorithms from the algorithms list in sequence if checkbox is checked
            processed_img = cv_img.copy()
            algorithms_applied = []
            
            if self.apply_algorithms_checkbox.isChecked():
                for i in range(self.algorithms_list.count()):
                    list_item = self.algorithms_list.item(i)
                    if list_item:
                        algorithm = list_item.data(Qt.ItemDataRole.UserRole)
                        if algorithm:
                            print(f"[DEBUG] Applying algorithm: {algorithm['name']} with config: {algorithm['config']}")
                            processed_img = self._apply_preprocessing(processed_img, algorithm["config"])
                            algorithms_applied.append(algorithm["name"])
            
            if algorithms_applied:
                print(f"[DEBUG] Applied {len(algorithms_applied)} algorithms: {', '.join(algorithms_applied)}")
            elif self.apply_algorithms_checkbox.isChecked():
                print(f"[DEBUG] No algorithms in list - showing original image")
            else:
                print(f"[DEBUG] Algorithm preview disabled - showing original image")

            processed_h, processed_w = processed_img.shape[:2]
            self._capture_preview_transform = {
                "src_w": float(original_w),
                "src_h": float(original_h),
                "dst_w": float(processed_w),
                "dst_h": float(processed_h),
            }
            
            # Use processed image for display
            # Convert BGR to RGB for Qt
            rgb_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_img.shape
            bytes_per_line = ch * w
            
            # Create QImage and QPixmap
            q_image = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)
            
        except Exception as e:
            print(f"[DEBUG] Error loading image {path}: {e}")
            # Fallback to QPixmap (may fail with Unicode paths)
            pixmap = QPixmap(path)
            self._capture_preview_transform = {
                "src_w": float(pixmap.width()),
                "src_h": float(pixmap.height()),
                "dst_w": float(pixmap.width()),
                "dst_h": float(pixmap.height()),
            }
            
        if pixmap.isNull():
            print(f"[DEBUG] Failed to load pixmap from: {path}")
            return
        
        print(f"[DEBUG] Pixmap loaded: {pixmap.width()}x{pixmap.height()}")
        
        # Display pixmap at original size
        self.capture_scene.clear()
        pixmap_item = self.capture_scene.addPixmap(pixmap)
        
        # Enable smooth transformation
        pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        
        # Reset view transform
        self.capture_view.resetTransform()
        
        # Set scene rect to match pixmap bounds (keep original size)
        self.capture_scene.setSceneRect(pixmap_item.boundingRect())
        self._draw_capture_teaching_highlight(pixmap.width(), pixmap.height())
        self._draw_capture_best_match_highlight(path, pixmap.width(), pixmap.height())
        
        print(f"[DEBUG] Image displayed in capture_view with algorithm applied")
        
        # Clear OCR results for new image
        if hasattr(self, 'ocr_results_table') and self.ocr_results_table:
            self.ocr_results_table.setRowCount(0)
    
    def _add_algorithm_from_data(self, algo: dict):
        """Add algorithm from saved data with proper UI widget."""
        # Temporarily set the combo box to this algorithm
        for i in range(self.algorithm_combo.count()):
            if self.algorithm_combo.itemData(i)["id"] == algo["id"]:
                self.algorithm_combo.setCurrentIndex(i)
                break
        
        # Use the existing _add_algorithm logic but with custom algo data
        original_algo = self.algorithm_combo.currentData()
        
        # Create custom widget for list item (copied from _add_algorithm)
        item_widget = QWidget()
        main_layout = QVBoxLayout(item_widget)
        main_layout.setContentsMargins(5, 2, 5, 2)
        main_layout.setSpacing(2)
        
        # Top row: Algorithm name, settings button, and remove button
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        
        # Label with algorithm name
        label = QLabel(algo["name"])
        label.setStyleSheet("QLabel { padding: 2px; font-weight: bold; }")
        top_row.addWidget(label)
        
        top_row.addStretch()
        
        # Settings button (luôn hiển thị và enabled)
        parameters = original_algo.get("parameters", {})
        settings_btn = QPushButton("⚙️")
        settings_btn.setFixedSize(25, 25)
        settings_btn.setToolTip("Show/Hide settings" if parameters else "No settings available")
        top_row.addWidget(settings_btn)
        
        # Remove button
        remove_btn = QPushButton("🗑️")
        remove_btn.setFixedSize(25, 25)
        remove_btn.setToolTip("Remove this algorithm")
        remove_btn.clicked.connect(lambda: self._remove_algorithm_item(algo))
        top_row.addWidget(remove_btn)
        
        main_layout.addLayout(top_row)
        
        # Create list item FIRST (needed for toggle_params closure)
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, algo)
        
        # Parameters section (hidden by default)
        parameter_widgets = {}
        params_widget = None
        
        if parameters:
            # Create parameters widget (initially hidden)
            params_widget = QWidget()
            params_grid = QGridLayout(params_widget)
            params_grid.setContentsMargins(10, 5, 10, 5)
            params_grid.setSpacing(5)
            
            row = 0
            for param_name, param_def in parameters.items():
                # Parameter label
                param_label = QLabel(param_def["label"] + ":")
                param_label.setMinimumWidth(100)
                params_grid.addWidget(param_label, row, 0)
                
                # Parameter widget with saved value
                if param_def.get("type") == "rgb_range_channel":
                    saved_value = (
                        int(algo["config"].get(param_def.get("min_key"), param_def.get("default_min", 0))),
                        int(algo["config"].get(param_def.get("max_key"), param_def.get("default_max", 255))),
                    )
                else:
                    saved_value = algo["config"].get(param_name, param_def["default"])
                param_widget = self._create_parameter_widget(param_def, saved_value)
                
                # Connect parameter change to update config AND refresh preview
                if isinstance(param_widget, (QSpinBox, QDoubleSpinBox)):
                    param_widget.valueChanged.connect(
                        lambda value, pname=param_name, algo_ref=algo: self._on_parameter_changed_with_preview(algo_ref, pname, value)
                    )
                elif isinstance(param_widget, QComboBox):
                    param_widget.currentIndexChanged.connect(
                        lambda index, pname=param_name, widget=param_widget, algo_ref=algo: 
                        self._on_parameter_changed_with_preview(algo_ref, pname, widget.currentData())
                    )
                elif isinstance(param_widget, RGBRangeChannelWidget):
                    min_key = param_def.get("min_key")
                    max_key = param_def.get("max_key")
                    param_widget.rangeChanged.connect(
                        lambda min_value, max_value, algo_ref=algo, min_key=min_key, max_key=max_key:
                            self._on_rgb_range_changed_with_preview(algo_ref, min_key, max_key, min_value, max_value)
                    )

                params_grid.addWidget(param_widget, row, 1)
                parameter_widgets[param_name] = param_widget
                
                row += 1
            
            # Hide parameters by default
            params_widget.setVisible(False)
            main_layout.addWidget(params_widget)
        
        # Connect settings button to toggle visibility
        def toggle_params():
            if params_widget:  # Có parameters - toggle visibility
                is_visible = params_widget.isVisible()
                params_widget.setVisible(not is_visible)
                # Update item size hint
                item.setSizeHint(item_widget.sizeHint())
            else:  # Không có parameters - hiển thị thông báo
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(None, "Thông báo", 
                    f"Thuật toán '{algo['name']}' không có thông số để cài đặt.")
        
        settings_btn.clicked.connect(toggle_params)
        
        # Set initial size hint
        item.setSizeHint(item_widget.sizeHint())
        
        self.algorithms_list.addItem(item)
        self.algorithms_list.setItemWidget(item, item_widget)
        
        # Store references for later updates
        item_widget.label = label
        item_widget.algo = algo
        item_widget.parameter_widgets = parameter_widgets
        item_widget.params_widget = params_widget
        item_widget.settings_btn = settings_btn

    def _add_algorithm(self):
        """Add algorithm to list with collapsible parameter widgets."""
        algo = self.algorithm_combo.currentData()
        
        # Create custom widget for list item
        item_widget = QWidget()
        main_layout = QVBoxLayout(item_widget)
        main_layout.setContentsMargins(5, 2, 5, 2)
        main_layout.setSpacing(2)
        
        # Top row: Algorithm name, settings button, and remove button
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        
        # Label with algorithm name
        label = QLabel(algo["name"])
        label.setStyleSheet("QLabel { padding: 2px; font-weight: bold; }")
        top_row.addWidget(label)
        
        top_row.addStretch()
        
        # Settings button (luôn hiển thị và enabled)
        parameters = algo.get("parameters", {})
        settings_btn = QPushButton("⚙️")
        settings_btn.setFixedSize(25, 25)
        settings_btn.setToolTip("Show/Hide settings" if parameters else "No settings available")
        # Luôn enabled để user có thể click
        top_row.addWidget(settings_btn)
        
        # Remove button
        remove_btn = QPushButton("🗑️")
        remove_btn.setFixedSize(25, 25)
        remove_btn.setToolTip("Remove this algorithm")
        remove_btn.clicked.connect(lambda: self._remove_algorithm_item(algo))
        top_row.addWidget(remove_btn)
        
        main_layout.addLayout(top_row)
        
        # Create list item FIRST (needed for toggle_params closure)
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, algo)
        
        # Parameters section (hidden by default)
        parameter_widgets = {}
        params_widget = None
        
        if parameters:
            # Create parameters widget (initially hidden)
            params_widget = QWidget()
            params_grid = QGridLayout(params_widget)
            params_grid.setContentsMargins(10, 5, 10, 5)
            params_grid.setSpacing(5)
            
            row = 0
            for param_name, param_def in parameters.items():
                # Parameter label
                param_label = QLabel(param_def["label"] + ":")
                param_label.setMinimumWidth(100)
                params_grid.addWidget(param_label, row, 0)
                
                # Parameter widget
                if param_def.get("type") == "rgb_range_channel":
                    current_value = (
                        int(algo["config"].get(param_def.get("min_key"), param_def.get("default_min", 0))),
                        int(algo["config"].get(param_def.get("max_key"), param_def.get("default_max", 255))),
                    )
                else:
                    current_value = algo["config"].get(param_name, param_def["default"])
                param_widget = self._create_parameter_widget(param_def, current_value)
                
                # Connect parameter change to update config AND refresh preview
                if isinstance(param_widget, (QSpinBox, QDoubleSpinBox)):
                    param_widget.valueChanged.connect(
                        lambda value, pname=param_name, algo_ref=algo: self._on_parameter_changed_with_preview(algo_ref, pname, value)
                    )
                elif isinstance(param_widget, QComboBox):
                    param_widget.currentIndexChanged.connect(
                        lambda index, pname=param_name, widget=param_widget, algo_ref=algo: 
                        self._on_parameter_changed_with_preview(algo_ref, pname, widget.currentData())
                    )
                elif isinstance(param_widget, RGBRangeChannelWidget):
                    min_key = param_def.get("min_key")
                    max_key = param_def.get("max_key")
                    param_widget.rangeChanged.connect(
                        lambda min_value, max_value, algo_ref=algo, min_key=min_key, max_key=max_key:
                            self._on_rgb_range_changed_with_preview(algo_ref, min_key, max_key, min_value, max_value)
                    )

                params_grid.addWidget(param_widget, row, 1)
                parameter_widgets[param_name] = param_widget
                
                row += 1
            
            # Hide parameters by default
            params_widget.setVisible(False)
            main_layout.addWidget(params_widget)
        
        # Connect settings button to toggle visibility (luôn connect)
        def toggle_params():
            if params_widget:  # Có parameters - toggle visibility
                is_visible = params_widget.isVisible()
                params_widget.setVisible(not is_visible)
                # Update item size hint
                item.setSizeHint(item_widget.sizeHint())
            else:  # Không có parameters - hiển thị thông báo
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(None, "Thông báo", 
                    f"Thuật toán '{algo['name']}' không có thông số để cài đặt.")
        
        settings_btn.clicked.connect(toggle_params)
        
        # Set initial size hint
        item.setSizeHint(item_widget.sizeHint())
        
        self.algorithms_list.addItem(item)
        self.algorithms_list.setItemWidget(item, item_widget)
        
        # Store references for later updates
        item_widget.label = label
        item_widget.algo = algo
        item_widget.parameter_widgets = parameter_widgets
        item_widget.params_widget = params_widget
        item_widget.settings_btn = settings_btn
        
        # Refresh both teaching and window capture previews if checkbox is checked
        if self.apply_algorithms_checkbox.isChecked():
            self._load_teaching_preview()  # Refresh teaching preview
            
            current_item = self.captures_list.currentItem()
            if current_item:
                print(f"[DEBUG] Refreshing window capture preview after adding algorithm: {algo['name']}")
                self._on_capture_selected(current_item)
    
    def _create_parameter_widget(self, param_def: dict, current_value):
        """Create appropriate widget for parameter based on type."""
        param_type = param_def.get("type", "int")

        if param_type == "rgb_range_channel":
            if isinstance(current_value, tuple) and len(current_value) == 2:
                min_value = int(current_value[0])
                max_value = int(current_value[1])
            else:
                min_value = int(param_def.get("default_min", 0))
                max_value = int(param_def.get("default_max", 255))
            return RGBRangeChannelWidget(min_value, max_value)
        elif param_type == "int":
            widget = QSpinBox()
            widget.setMinimum(param_def.get("min", 0))
            widget.setMaximum(param_def.get("max", 100))
            widget.setSingleStep(param_def.get("step", 1))
            widget.setValue(int(current_value))
            return widget
            
        elif param_type == "float":
            widget = QDoubleSpinBox()
            widget.setMinimum(param_def.get("min", 0.0))
            widget.setMaximum(param_def.get("max", 10.0))
            widget.setSingleStep(param_def.get("step", 0.1))
            widget.setDecimals(2)
            widget.setValue(float(current_value))
            return widget
            
        elif param_type == "choice":
            widget = QComboBox()
            choices = param_def.get("choices", [])
            for choice in choices:
                widget.addItem(choice["label"], choice["value"])
            
            # Set current value
            for i in range(widget.count()):
                if widget.itemData(i) == current_value:
                    widget.setCurrentIndex(i)
                    break
            return widget
            
        else:
            # Fallback to spinbox
            widget = QSpinBox()
            widget.setValue(int(current_value) if isinstance(current_value, (int, float)) else 0)
            return widget
    
    def _on_parameter_changed(self, algo: dict, param_name: str, value):
        """Handle parameter value change."""
        # Update algorithm config
        algo["config"][param_name] = value
        
        # Update related config flags based on parameter
        if param_name == "upscale":
            algo["config"]["upscale"] = value
        elif param_name == "contrast_level":
            algo["config"]["enhance_contrast"] = True
            algo["config"]["contrast_level"] = value
        elif param_name == "sharpen_strength":
            algo["config"]["sharpen"] = True
            algo["config"]["sharpen_strength"] = value
        elif param_name == "denoise_strength":
            algo["config"]["denoise"] = True
            algo["config"]["denoise_strength"] = value
        elif param_name == "threshold_value":
            algo["config"]["binary_threshold"] = True
            algo["config"]["threshold_value"] = value
        elif param_name == "threshold_type":
            algo["config"]["binary_threshold"] = True
            algo["config"]["threshold_type"] = value
        elif param_name == "adaptive_max_value":
            algo["config"]["adaptive_threshold_mean"] = algo.get("id") == "adaptive_threshold_mean"
            algo["config"]["adaptive_threshold_gaussian"] = algo.get("id") == "adaptive_threshold_gaussian"
            algo["config"]["adaptive_max_value"] = value
        elif param_name == "adaptive_threshold_type":
            algo["config"]["adaptive_threshold_mean"] = algo.get("id") == "adaptive_threshold_mean"
            algo["config"]["adaptive_threshold_gaussian"] = algo.get("id") == "adaptive_threshold_gaussian"
            algo["config"]["adaptive_threshold_type"] = value
        elif param_name == "adaptive_block_size":
            algo["config"]["adaptive_threshold_mean"] = algo.get("id") == "adaptive_threshold_mean"
            algo["config"]["adaptive_threshold_gaussian"] = algo.get("id") == "adaptive_threshold_gaussian"
            algo["config"]["adaptive_block_size"] = value
        elif param_name == "adaptive_c":
            algo["config"]["adaptive_threshold_mean"] = algo.get("id") == "adaptive_threshold_mean"
            algo["config"]["adaptive_threshold_gaussian"] = algo.get("id") == "adaptive_threshold_gaussian"
            algo["config"]["adaptive_c"] = value
        # Morphological operations
        elif param_name == "opening_kernel_size":
            algo["config"]["morphological_opening"] = True
            algo["config"]["opening_kernel_size"] = value
        elif param_name == "closing_kernel_size":
            algo["config"]["morphological_closing"] = True
            algo["config"]["closing_kernel_size"] = value
        # Advanced noise removal
        elif param_name == "min_component_area":
            algo["config"]["remove_small_components"] = True
            algo["config"]["min_component_area"] = value
        elif param_name == "median_kernel_size":
            algo["config"]["median_filter"] = True
            algo["config"]["median_kernel_size"] = value
        elif param_name == "epf_flags":
            algo["config"]["edge_preserving_filter"] = True
            algo["config"]["epf_flags"] = value
        elif param_name == "epf_sigma_s":
            algo["config"]["edge_preserving_filter"] = True
            algo["config"]["epf_sigma_s"] = value
        elif param_name == "epf_sigma_r":
            algo["config"]["edge_preserving_filter"] = True
            algo["config"]["epf_sigma_r"] = value
        elif param_name == "nlm_h":
            algo["config"]["nlm_denoising"] = True
            algo["config"]["nlm_h"] = value
        elif param_name == "nlm_template_window_size":
            algo["config"]["nlm_denoising"] = True
            algo["config"]["nlm_template_window_size"] = value
        elif param_name == "nlm_search_window_size":
            algo["config"]["nlm_denoising"] = True
            algo["config"]["nlm_search_window_size"] = value
        # Template matching specific algorithms
        elif param_name == "gaussian_kernel_size":
            algo["config"]["gaussian_blur"] = True
            algo["config"]["gaussian_kernel_size"] = value
        elif param_name == "gaussian_sigma_x":
            algo["config"]["gaussian_blur"] = True
            algo["config"]["gaussian_sigma_x"] = value
        elif param_name == "canny_low_threshold":
            algo["config"]["canny_edge_detection"] = True
            algo["config"]["canny_low_threshold"] = value
        elif param_name == "canny_high_threshold":
            algo["config"]["canny_edge_detection"] = True
            algo["config"]["canny_high_threshold"] = value
        
        print(f"[DEBUG] Parameter {param_name} changed to {value}")
        print(f"[DEBUG] Updated config: {algo['config']}")
        
        # CRITICAL FIX: Find and update the correct item data
        # The algo object passed might be a reference, we need to update the actual item data
        for i in range(self.algorithms_list.count()):
            item = self.algorithms_list.item(i)
            if item:
                item_algo = item.data(Qt.ItemDataRole.UserRole)
                # Check if this is the same algorithm by comparing id and name
                if (item_algo and 
                    item_algo.get("id") == algo.get("id") and 
                    item_algo.get("name") == algo.get("name")):
                    # Update the item's algorithm data with the modified config
                    item_algo["config"] = algo["config"].copy()
                    item.setData(Qt.ItemDataRole.UserRole, item_algo)
                    print(f"[DEBUG] Updated item data for {item_algo['name']}: {item_algo['config']}")
                    break
        
        # Refresh preview if there's a selected capture
        current_item = self.captures_list.currentItem()
        if current_item:
            self._on_capture_selected(current_item)
    
    def _on_parameter_changed_with_preview(self, algo: dict, param_name: str, value):
        """Handle parameter value change with immediate preview update."""
        # Call the original parameter change handler
        self._on_parameter_changed(algo, param_name, value)
        
        # Force immediate preview update for both teaching and window capture if checkbox is checked
        if self.apply_algorithms_checkbox.isChecked():
            self._load_teaching_preview()  # Refresh teaching preview
            
            current_item = self.captures_list.currentItem()
            if current_item:
                print(f"[DEBUG] Forcing preview update after parameter change: {param_name}={value}")
                self._on_capture_selected(current_item)

    def _on_rgb_range_changed_with_preview(
        self,
        algo: dict,
        min_key: str,
        max_key: str,
        min_value: int,
        max_value: int,
    ) -> None:
        """Handle RGB min/max channel changes with preview update."""
        algo["config"]["rgb_range_filter"] = True
        algo["config"][min_key] = int(min_value)
        algo["config"][max_key] = int(max_value)
        print(f"[DEBUG] RGB range changed: {min_key}={min_value}, {max_key}={max_value}")

        for i in range(self.algorithms_list.count()):
            item = self.algorithms_list.item(i)
            if not item:
                continue
            item_algo = item.data(Qt.ItemDataRole.UserRole)
            if item_algo and item_algo.get("id") == algo.get("id") and item_algo.get("name") == algo.get("name"):
                item_algo["config"] = algo["config"].copy()
                item.setData(Qt.ItemDataRole.UserRole, item_algo)
                break

        if self.apply_algorithms_checkbox.isChecked():
            self._load_teaching_preview()
            current_item = self.captures_list.currentItem()
            if current_item:
                self._on_capture_selected(current_item)
    
    def _get_algorithm_parameters(self, algo: dict) -> dict:
        """Get algorithm parameters (for backward compatibility)."""
        return algo.get("parameters", {})
    
    def _remove_algorithm_item(self, algo: dict):
        """Remove individual algorithm item."""
        # Remove from UI list
        for i in range(self.algorithms_list.count()):
            item = self.algorithms_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == algo:
                self.algorithms_list.takeItem(i)
                break
        
        # Refresh both teaching and window capture previews if checkbox is checked
        if self.apply_algorithms_checkbox.isChecked():
            self._load_teaching_preview()  # Refresh teaching preview
            
            current_item = self.captures_list.currentItem()
            if current_item:
                print(f"[DEBUG] Refreshing window capture preview after removing algorithm: {algo['name']}")
                self._on_capture_selected(current_item)

    def _apply_rgb_range_filter(self, img: np.ndarray, config: dict) -> np.ndarray:
        """Keep only pixels within configured RGB ranges and hide the rest."""
        return _apply_rgb_range_filter_to_bgr(img, config)
    
    def _apply_preprocessing(self, img: np.ndarray, config: dict) -> np.ndarray:
        """Apply preprocessing to image using TemplateMatchingPreprocessor."""
        if not config:
            return img

        if config.get("dominant_color_merge"):
            img = _apply_dominant_color_merge_to_bgr(img, config)

        if config.get("rgb_range_filter"):
            img = self._apply_rgb_range_filter(img, config)
        
        # Apply binary threshold first if specified
        if config.get("binary_threshold"):
            threshold_value = config.get("threshold_value", 127)
            threshold_type = config.get("threshold_type", 0)  # 0 = THRESH_BINARY, 1 = THRESH_BINARY_INV
            
            # Convert to grayscale for thresholding
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply threshold
            thresh_type = cv2.THRESH_BINARY if threshold_type == 0 else cv2.THRESH_BINARY_INV
            _, binary = cv2.threshold(gray, threshold_value, 255, thresh_type)
            
            # Convert back to 3-channel for consistency
            img = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
            preprocessor = TemplateMatchingPreprocessor(img)
        elif config.get("adaptive_threshold_mean") or config.get("adaptive_threshold_gaussian"):
            adaptive_max_value = int(config.get("adaptive_max_value", 255))
            adaptive_threshold_type = config.get("adaptive_threshold_type", 0)
            adaptive_block_size = int(config.get("adaptive_block_size", 11))
            adaptive_c = int(config.get("adaptive_c", 2))

            adaptive_max_value = max(0, min(adaptive_max_value, 255))
            adaptive_block_size = max(3, adaptive_block_size)
            if adaptive_block_size % 2 == 0:
                adaptive_block_size += 1

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            thresh_type = cv2.THRESH_BINARY if adaptive_threshold_type == 0 else cv2.THRESH_BINARY_INV
            adaptive_method = (
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C
                if config.get("adaptive_threshold_gaussian")
                else cv2.ADAPTIVE_THRESH_MEAN_C
            )

            adaptive = cv2.adaptiveThreshold(
                gray,
                adaptive_max_value,
                adaptive_method,
                thresh_type,
                adaptive_block_size,
                adaptive_c,
            )

            img = cv2.cvtColor(adaptive, cv2.COLOR_GRAY2BGR)
            preprocessor = TemplateMatchingPreprocessor(img)
        else:
            preprocessor = TemplateMatchingPreprocessor(img)
            
            # Apply grayscale first if specified
            if config.get("grayscale"):
                # Convert to grayscale then back to 3-channel for consistency
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                preprocessor = TemplateMatchingPreprocessor(img)
        
        # Basic algorithms
        if config.get("upscale"):
            preprocessor = preprocessor.upscale(config["upscale"])
        if config.get("enhance_contrast"):
            # Use custom contrast level if provided
            contrast_level = config.get("contrast_level", 3.0)
            preprocessor = preprocessor.enhance_contrast(contrast_level)
        if config.get("sharpen"):
            # Use custom sharpen strength if provided
            sharpen_strength = config.get("sharpen_strength", 1.5)
            preprocessor = preprocessor.sharpen(sharpen_strength)
        if config.get("denoise"):
            # Use custom denoise strength if provided
            denoise_strength = config.get("denoise_strength", 9)
            preprocessor = preprocessor.denoise(denoise_strength)
        
        # Morphological operations
        if config.get("morphological_opening"):
            kernel_size = config.get("opening_kernel_size", 3)
            preprocessor = preprocessor.morphological_opening(kernel_size)
        if config.get("morphological_closing"):
            kernel_size = config.get("closing_kernel_size", 3)
            preprocessor = preprocessor.morphological_closing(kernel_size)
        
        # Advanced noise removal
        if config.get("remove_small_components"):
            min_area = config.get("min_component_area", 50)
            preprocessor = preprocessor.remove_small_components(min_area)
        if config.get("median_filter"):
            kernel_size = config.get("median_kernel_size", 5)
            preprocessor = preprocessor.median_filter(kernel_size)
        if config.get("edge_preserving_filter"):
            flags = config.get("epf_flags", 1)
            sigma_s = config.get("epf_sigma_s", 50.0)
            sigma_r = config.get("epf_sigma_r", 0.4)
            preprocessor = preprocessor.edge_preserving_filter(flags, sigma_s, sigma_r)
        if config.get("nlm_denoising"):
            h = config.get("nlm_h", 10.0)
            template_window_size = config.get("nlm_template_window_size", 7)
            search_window_size = config.get("nlm_search_window_size", 21)
            preprocessor = preprocessor.nlm_denoising(h, template_window_size, search_window_size)
        
        # Template matching specific algorithms
        if config.get("gaussian_blur"):
            kernel_size = config.get("gaussian_kernel_size", 5)
            sigma_x = config.get("gaussian_sigma_x", 0.0)
            preprocessor = preprocessor.gaussian_blur(kernel_size, sigma_x)
        if config.get("histogram_equalization"):
            preprocessor = preprocessor.histogram_equalization()
        if config.get("canny_edge_detection"):
            low_threshold = config.get("canny_low_threshold", 50)
            high_threshold = config.get("canny_high_threshold", 150)
            preprocessor = preprocessor.canny_edge_detection(low_threshold, high_threshold)
        if config.get("alpha_blend_recovery"):
            alpha = config.get("alpha", 0.7)
            sigma = config.get("sigma", 15.0)
            preprocessor = preprocessor.alpha_blend_recovery(alpha, sigma)
        
        return preprocessor.build()
    
    def _test_single_image(
        self,
        test_path: str,
        algorithms: list,
        matching_method: Optional[str] = None,
        color_options: Optional[dict] = None,
    ) -> tuple[float, Optional[tuple]]:
        """Test single image with algorithms from algorithms_list.
        
        Args:
            test_path: Path to test image
            algorithms: List of preprocessing algorithms
        
        Returns:
            Matching score (0.0-1.0), or -1.0 if error
        """
        try:
            def load_image_unicode(path: str):
                try:
                    with open(path, 'rb') as f:
                        file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
                    return cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                except Exception as e:
                    print(f"[WARN] Failed to load image {path}: {e}")
                    return None

            test_img = load_image_unicode(test_path)
            if test_img is None or not self.teaching_image_path:
                return -1.0, None

            matching_method = matching_method or self.matching_method_combo.currentData()
            if matching_method == "color":
                teaching_img = load_image_unicode(self.teaching_image_path)
                if teaching_img is None:
                    return -1.0, None
                for algorithm in algorithms:
                    config = algorithm.get("config", {})
                    teaching_img = self._apply_preprocessing(teaching_img, config)
                    test_img = self._apply_preprocessing(test_img, config)
                return self._match_by_color_regions(test_img, teaching_img, color_options)

            from ..logic.system_executor.system_executor import SystemExecutor

            executor = SystemExecutor(target_window_hwnd=None)
            image_result, max_val = executor.match_template_against_image_with_score_adaptive(
                screenshot_bgr=test_img,
                template_path=self.teaching_image_path,
                threshold=0.0,
                ignore_text=False,
                multiscale_enabled=bool(getattr(self.action, "multiscale_enabled", True)),
                multiscale_min=float(getattr(self.action, "multiscale_min", 0.70) or 0.70),
                multiscale_max=float(getattr(self.action, "multiscale_max", 1.30) or 1.30),
                multiscale_step=float(getattr(self.action, "multiscale_step", 0.05) or 0.05),
                mask_regions=getattr(self.action, "mask_regions", None),
                preprocessing_algorithms=algorithms,
                teaching_window_width=getattr(self.action, "teaching_window_width", None) or 800,
                teaching_window_height=getattr(self.action, "teaching_window_height", None) or 600,
            )

            max_val = float(max_val or 0.0)
            if not np.isfinite(max_val):
                max_val = 0.0
            score = max(0.0, min(1.0, max_val))
            bbox = None
            if image_result and len(image_result) >= 4:
                x, y, w, h = image_result[:4]
                bbox = (int(x), int(y), int(w), int(h))
            return score, bbox
        except Exception as e:
            print(f"Error testing {test_path}: {e}")
            return -1.0, None

    def _match_by_color_regions(
        self,
        test_bgr: np.ndarray,
        teaching_bgr: np.ndarray,
        color_options: Optional[dict] = None,
    ) -> tuple[float, Optional[tuple]]:
        """Find a teaching-sized region by automatically learned HSV colors.

        This intentionally scores color coverage in regions rather than comparing
        individual template pixels.  It is therefore useful for stable UI colors
        whose text or small details change between screenshots.
        """
        color_options = color_options or {
            "sensitivity": float(self.color_sensitivity_combo.currentData()),
            "minimum_score": self.color_min_match_spin.value() / 100.0,
            "ignore_background": self.color_ignore_background_checkbox.isChecked(),
        }
        profile = self._build_color_profile(
            teaching_bgr,
            ignore_background=color_options["ignore_background"],
            sensitivity=color_options["sensitivity"],
        )
        if profile is None:
            return 0.0, None

        centers, tolerances, teaching_coverage = profile
        test_hsv = cv2.cvtColor(test_bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
        color_mask = np.zeros(test_hsv.shape[:2], dtype=bool)
        for center, tolerance in zip(centers, tolerances):
            hue_delta = np.abs(test_hsv[:, :, 0] - center[0])
            hue_delta = np.minimum(hue_delta, 180.0 - hue_delta) * 2.0
            saturation_delta = np.abs(test_hsv[:, :, 1] - center[1])
            value_delta = np.abs(test_hsv[:, :, 2] - center[2])
            distance = np.sqrt(hue_delta ** 2 + saturation_delta ** 2 + value_delta ** 2)
            color_mask |= distance <= tolerance

        mask_float = color_mask.astype(np.float32)
        template_h, template_w = teaching_bgr.shape[:2]
        best_score, best_bbox = 0.0, None
        for scale in self._color_matching_scales():
            width, height = int(template_w * scale), int(template_h * scale)
            if width < 2 or height < 2 or width > test_bgr.shape[1] or height > test_bgr.shape[0]:
                continue
            coverage = cv2.boxFilter(mask_float, ddepth=-1, ksize=(width, height), normalize=True)
            _, max_value, _, max_location = cv2.minMaxLoc(coverage)
            score = min(1.0, float(max_value) / max(teaching_coverage, 0.01))
            if score > best_score:
                x = max(0, min(max_location[0] - width // 2, test_bgr.shape[1] - width))
                y = max(0, min(max_location[1] - height // 2, test_bgr.shape[0] - height))
                best_score, best_bbox = score, (x, y, width, height)

        minimum_score = color_options["minimum_score"]
        return (best_score, best_bbox) if best_score >= minimum_score else (best_score, None)

    def _build_color_profile(
        self,
        teaching_bgr: np.ndarray,
        ignore_background: bool,
        sensitivity: float,
    ) -> Optional[tuple]:
        """Extract up to three dominant, non-background HSV colors from teaching."""
        hsv = cv2.cvtColor(teaching_bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
        pixels = hsv.reshape(-1, 3)
        total_pixel_count = len(pixels)
        if ignore_background:
            pixels = pixels[(pixels[:, 1] >= 40) & (pixels[:, 2] >= 35)]
        if len(pixels) < 10:
            return None

        # Sampling keeps teaching images of any size responsive while preserving
        # the color distribution used to learn the automatic profile.
        if len(pixels) > 10_000:
            pixels = pixels[np.linspace(0, len(pixels) - 1, 10_000, dtype=int)]
        cluster_count = min(3, max(1, len(pixels) // 100))
        _, labels, centers = cv2.kmeans(
            pixels, cluster_count, None,
            (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0),
            3, cv2.KMEANS_PP_CENTERS,
        )
        labels = labels.reshape(-1)
        counts = np.bincount(labels, minlength=cluster_count)
        dominant = np.argsort(counts)[::-1]
        dominant = [index for index in dominant if counts[index] / len(pixels) >= 0.08]
        dominant = dominant or [int(np.argmax(counts))]

        selected_centers, tolerances = [], []
        for index in dominant:
            cluster_pixels = pixels[labels == index]
            center = centers[index]
            hue_delta = np.abs(cluster_pixels[:, 0] - center[0])
            hue_delta = np.minimum(hue_delta, 180.0 - hue_delta) * 2.0
            distances = np.sqrt(
                hue_delta ** 2
                + (cluster_pixels[:, 1] - center[1]) ** 2
                + (cluster_pixels[:, 2] - center[2]) ** 2
            )
            selected_centers.append(center)
            tolerances.append(max(18.0, float(np.percentile(distances, 90)) * sensitivity))

        # This is the expected color density of a perfect teaching-sized region.
        coverage = sum(counts[index] for index in dominant) / total_pixel_count
        return np.asarray(selected_centers), tolerances, float(coverage)

    def _color_matching_scales(self) -> list[float]:
        """Use the existing multiscale range, but keep color scans inexpensive."""
        if not bool(getattr(self.action, "multiscale_enabled", True)):
            return [1.0]
        minimum = float(getattr(self.action, "multiscale_min", 0.70) or 0.70)
        maximum = float(getattr(self.action, "multiscale_max", 1.30) or 1.30)
        step = max(0.1, float(getattr(self.action, "multiscale_step", 0.05) or 0.05))
        return list(np.arange(minimum, maximum + step * 0.5, step))
    
    def _create_mask_array(self, template: np.ndarray, mask_regions: list) -> np.ndarray:
        """Create mask array from mask regions for template matching.
        
        Args:
            template: Template image (grayscale)
            mask_regions: List of {"x": int, "y": int, "w": int, "h": int}
        
        Returns:
            Mask array (255 = match, 0 = ignore)
        """
        h, w = template.shape[:2]
        mask = np.ones((h, w), dtype=np.uint8) * 255
        
        if not mask_regions:
            return mask
        
        for region in mask_regions:
            try:
                x = int(region.get("x", 0))
                y = int(region.get("y", 0))
                w_reg = int(region.get("w", 0))
                h_reg = int(region.get("h", 0))
                
                # Clamp to template bounds
                x2 = min(x + w_reg, w)
                y2 = min(y + h_reg, h)
                x = max(0, x)
                y = max(0, y)
                
                # Set mask region to 0 (ignore)
                if x2 > x and y2 > y:
                    mask[y:y2, x:x2] = 0
            except Exception as e:
                print(f"[WARN] Error processing mask region: {e}")
                continue
        
        return mask
    
    def _match_multiscale(self, test_gray: np.ndarray, teaching_gray: np.ndarray, mask_regions: list = None) -> float:
        """Match template with multiscale.
        
        Args:
            test_gray: Test image (grayscale)
            teaching_gray: Teaching image (grayscale)
            mask_regions: List of mask regions to ignore
        """
        best_score = 0.0
        scale_min = getattr(self.action, "multiscale_min", 0.7)
        scale_max = getattr(self.action, "multiscale_max", 1.3)
        scale_step = getattr(self.action, "multiscale_step", 0.05)
        
        # Create base mask at original scale if mask_regions exist
        base_mask = None
        if mask_regions and len(mask_regions) > 0:
            base_mask = self._create_mask_array(teaching_gray, mask_regions)
        
        scale = scale_min
        while scale <= scale_max:
            h, w = teaching_gray.shape
            new_w, new_h = int(w * scale), int(h * scale)
            
            if new_w <= 0 or new_h <= 0 or new_w > test_gray.shape[1] or new_h > test_gray.shape[0]:
                scale += scale_step
                continue
            
            teaching_scaled = cv2.resize(teaching_gray, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            
            try:
                # Scale mask if exists
                mask_scaled = None
                if base_mask is not None:
                    mask_scaled = cv2.resize(base_mask, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
                    # Ensure mask is binary (0 or 255)
                    mask_scaled = (mask_scaled > 127).astype(np.uint8) * 255
                
                # Match with or without mask
                if mask_scaled is not None:
                    result = cv2.matchTemplate(test_gray, teaching_scaled, cv2.TM_CCOEFF_NORMED, mask=mask_scaled)
                else:
                    result = cv2.matchTemplate(test_gray, teaching_scaled, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                if max_val > best_score:
                    best_score = max_val
            except Exception:
                pass
            
            scale += scale_step
        
        return float(best_score)
    
    def _run_test(self):
        """Run test in background thread (updated for custom widgets)."""
        checked_items = []
        for i in range(self.captures_list.count()):
            item = self.captures_list.item(i)
            widget = self.captures_list.itemWidget(item)
            if widget and hasattr(widget, 'checkbox') and widget.checkbox.isChecked():
                checked_items.append((i, item, widget))
        
        if not checked_items:
            QMessageBox.information(self, "Thông báo", "Vui lòng chọn ít nhất 1 window capture để test!")
            return
        
        self.stop_testing = False
        self.test_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        
        # Store total for progress calculation
        self.current_test_total = len(checked_items)
        self.current_test_completed = 0
        selected_index = self.window_combo.currentIndex()
        self.current_test_window_title = (
            self.window_combo.itemText(selected_index) if selected_index >= 0 else ""
        )
        
        # Get algorithms from algorithms_list (user đã add)
        algorithms = self._get_current_algorithms()
        matching_method = self.matching_method_combo.currentData()
        color_options = None
        if matching_method == "color":
            # Read QWidget state on the GUI thread before starting the worker.
            color_options = {
                "sensitivity": float(self.color_sensitivity_combo.currentData()),
                "minimum_score": self.color_min_match_spin.value() / 100.0,
                "ignore_background": self.color_ignore_background_checkbox.isChecked(),
            }
        
        # Nếu không có thuật toán, dùng empty list (sẽ test với ảnh gốc)
        print(f"[DEBUG] Testing with {len(algorithms)} algorithms from list")
        
        def worker():
            total = len(checked_items)
            for idx, (i, item, widget) in enumerate(checked_items):
                if self.stop_testing:
                    break
                
                path = item.data(Qt.ItemDataRole.UserRole)
                filename = os.path.basename(path)
                
                score, bbox = self._test_single_image(path, algorithms, matching_method, color_options)
                
                if score >= 0:
                    if bbox:
                        self.test_match_bboxes[path] = bbox
                    elif path in self.test_match_bboxes:
                        del self.test_match_bboxes[path]
                    self._test_progress_signal.emit(i, filename, score)
                    self.test_results[path] = score
                else:
                    self._test_error_signal.emit(i, filename, "Failed to test")
            
            self._test_complete_signal.emit()
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
    
    def _stop_test(self):
        """Stop testing."""
        self.stop_testing = True
    
    def _on_test_progress(self, index: int, filename: str, score: float):
        """Update UI with test progress (updated for custom widgets).
        
        Args:
            index: Item index in list
            filename: Image filename
            score: Matching score (0.0-1.0)
        """
        item = self.captures_list.item(index)
        if item:
            widget = self.captures_list.itemWidget(item)
            if widget and hasattr(widget, 'label'):
                threshold = self.action.match_threshold
                status = "✅" if score >= threshold else "❌"
                capture_path = item.data(Qt.ItemDataRole.UserRole)
                bbox = self.test_match_bboxes.get(capture_path)
                bbox_text = f" | BBox {bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}" if bbox else ""
                widget.label.setText(f"{filename} | Match: {score:.2f} {status}{bbox_text}")
            if self.captures_list.currentItem() is item:
                self._on_capture_selected(item)
        
        self._advance_test_progress(filename)
    
    def _on_test_error(self, index: int, filename: str, error: str):
        """Handle test error (updated for custom widgets)."""
        item = self.captures_list.item(index)
        if item:
            widget = self.captures_list.itemWidget(item)
            if widget and hasattr(widget, 'label'):
                widget.label.setText(f"{filename} | Error: {error}")
        self._advance_test_progress(filename)

    def _advance_test_progress(self, filename: str) -> None:
        """Count both successful and failed items toward the run total."""
        if self.current_test_total <= 0:
            return
        self.current_test_completed = min(
            self.current_test_completed + 1, self.current_test_total
        )
        progress_percent = int(self.current_test_completed / self.current_test_total * 100)
        self.progress_bar.setValue(progress_percent)
        self.progress_label.setText(
            f"Testing: {filename}... ({self.current_test_completed}/{self.current_test_total})"
        )
    
    def _on_test_complete(self):
        """Test complete."""
        self.test_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if self.stop_testing:
            self.progress_label.setText(
                f"Test stopped ({self.current_test_completed}/{self.current_test_total})"
            )
        else:
            # Completion is authoritative even when an item failed. Failed
            # items are still completed work for the progress bar.
            self.current_test_completed = self.current_test_total
            self.progress_bar.setValue(100)
            self.progress_label.setText(
                f"Test complete! ({self.current_test_total}/{self.current_test_total})"
            )
            self._save_test_session()
        self._update_results_display()
    
    def _update_results_display(self):
        """Update results display with best score (updated for custom widgets)."""
        if not self.test_results:
            return
        
        # Find best score
        best_path = max(self.test_results, key=self.test_results.get)
        best_score = self.test_results[best_path]
        threshold = getattr(self.action, 'match_threshold', 0.8)  # Default fallback
        
        # Update all items
        for i in range(self.captures_list.count()):
            item = self.captures_list.item(i)
            if not item:  # Safety check
                continue
                
            path = item.data(Qt.ItemDataRole.UserRole)
            widget = self.captures_list.itemWidget(item)
            
            if path in self.test_results and widget and hasattr(widget, 'label'):
                score = self.test_results[path]
                status = "✅" if score >= threshold else "❌"
                best_marker = " ⭐ BEST" if path == best_path else ""
                filename = os.path.basename(path)
                widget.label.setText(f"{filename} | Match: {score:.2f} {status}{best_marker}")
    
    def _save_to_action(self):
        """Save current algorithms to action."""
        algorithms = []
        for i in range(self.algorithms_list.count()):
            item = self.algorithms_list.item(i)
            if item:
                algo = item.data(Qt.ItemDataRole.UserRole)
                print(f"[DEBUG] Saving algorithm: {algo['name']}, config: {algo['config']}")
                algorithms.append(algo)
        
        # Save to the specified algorithm field
        if self.algorithm_field:
            setattr(self.action, self.algorithm_field, algorithms)
        else:
            self.action.template_matching_algorithms = algorithms
    
    def _save_captures_to_action(self):
        """Save data to action."""
        # Copy temp captures to permanent location
        all_paths = self.saved_captures.copy()
        
        for temp_path in self.temp_captures:
            # Generate permanent file path
            dest_path = self._get_next_capture_filename()
            
            try:
                # Copy from temp to permanent location
                import shutil
                shutil.copy2(temp_path, dest_path)
                
                if os.path.exists(dest_path):
                    all_paths.append(dest_path)
                    print(f"[DEBUG] Saved temp capture to: {dest_path}")
                else:
                    print(f"[WARN] Failed to save temp capture: {dest_path}")
            except Exception as e:
                print(f"[WARN] Error saving temp capture {temp_path}: {e}")
        
        # Save to action
        self.action.window_capture_paths = all_paths
        self.action.window_capture_results = self.test_results
    
    def _add_window_capture_for_test(self, path: str):
        """Helper method for tests - add window capture directly to saved_captures."""
        if os.path.exists(path):
            self.saved_captures.append(path)
            self._add_saved_capture_to_list(path)
    
    def get_total_captures_count(self) -> int:
        """Get total number of captures (temp + saved)."""
        return len(self.temp_captures) + len(self.saved_captures)
    
    def get_all_capture_paths(self) -> list:
        """Get all capture paths (temp + saved)."""
        return self.temp_captures + self.saved_captures
    
    def _on_apply_algorithms_changed(self):
        """Handle checkbox state change for algorithm preview application."""
        is_checked = self.apply_algorithms_checkbox.isChecked()
        print(f"[DEBUG] Apply algorithms checkbox changed to: {is_checked}")
        
        # Refresh both teaching and window capture previews
        self._load_teaching_preview()  # Refresh teaching preview
        
        current_item = self.captures_list.currentItem()
        if current_item:
            print(f"[DEBUG] Refreshing window capture preview after checkbox change")
            self._on_capture_selected(current_item)
    
    def _on_ok(self):
        """OK button clicked."""
        self._save_to_action()
        self._save_captures_to_action()
        
        # Transfer algorithms to parent dialog if it's a settings dialog
        self._transfer_algorithms_to_parent()
        self._refresh_parent_after_save()
        
        self.accept()
    
    def _transfer_algorithms_to_parent(self):
        """Transfer current algorithms to parent settings dialog."""
        parent = self.parent()
        if not parent:
            return
        
        # Get current algorithms from the algorithms list
        algorithms = self._get_current_algorithms()
        
        # Check if parent is Image Detect Settings Dialog
        if getattr(self, "algorithm_field", None) and hasattr(parent, "action"):
            setattr(parent.action, self.algorithm_field, algorithms)
            if self.algorithm_field == "template_matching_algorithms" and hasattr(parent, "_update_matching_algorithms_display"):
                parent._update_matching_algorithms_display()
            elif self.algorithm_field == "ocr_algorithms" and hasattr(parent, "_update_ocr_algorithms_display"):
                parent._update_ocr_algorithms_display()
            print(f"[DEBUG] Transferred {len(algorithms)} algorithms to parent action.{self.algorithm_field}")
        elif hasattr(parent, '_update_template_algorithms_display') and hasattr(parent, 'action'):
            # Save algorithms to action
            parent.action.template_matching_algorithms = algorithms
            
            # Update parent's display
            parent._update_template_algorithms_display()
            
            print(f"[DEBUG] Transferred {len(algorithms)} algorithms to parent settings dialog")
            
            # Show success message
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Thành công", 
                f"Đã áp dụng {len(algorithms)} algorithms vào Action Settings!")
        else:
            print(f"[DEBUG] Parent is not a settings dialog, no algorithm transfer needed")

    def _refresh_parent_after_save(self):
        """Refresh parent UI after confirm so saved captures/settings are reflected."""
        parent = self.parent()
        if not parent:
            return
        try:
            if hasattr(parent, "_load_settings"):
                parent._load_settings()
            elif hasattr(parent, "_update_ocr_algorithms_display"):
                parent._update_ocr_algorithms_display()
        except Exception as e:
            print(f"[DEBUG] Parent refresh after save failed: {e}")

    def _get_fixed_roi_from_action(self) -> Optional[tuple]:
        """Get Fixed ROI from action settings.
        
        Returns:
            Tuple (x, y, w, h) if Fixed ROI is enabled, None otherwise.
        """
        if getattr(self.action, 'use_fixed_roi', False):
            x = getattr(self.action, 'roi_x', 0)
            y = getattr(self.action, 'roi_y', 0)
            w = getattr(self.action, 'roi_w', 200)
            h = getattr(self.action, 'roi_h', 100)
            if w > 0 and h > 0:
                return (x, y, w, h)
        return None
    
    def _get_imperial_guardian_roi_from_action(self) -> Optional[tuple]:
        """Get Imperial Guardian ROI from action settings.
        
        Returns:
            Tuple (x, y, w, h) if Imperial Guardian ROI is set, None otherwise.
        """
        # Check if Imperial Guardian ROI coordinates are set and form a valid rectangle
        x1 = getattr(self.action, 'imperial_guardian_teaching_corner_x1', None)
        y1 = getattr(self.action, 'imperial_guardian_teaching_corner_y1', None)
        x2 = getattr(self.action, 'imperial_guardian_teaching_corner_x2', None)
        y2 = getattr(self.action, 'imperial_guardian_teaching_corner_y2', None)
        
        if x1 is not None and y1 is not None and x2 is not None and y2 is not None:
            w = x2 - x1
            h = y2 - y1
            if w > 0 and h > 0:
                return (x1, y1, w, h)
        return None

    def _get_teaching_roi_from_action(self) -> Optional[tuple]:
        """Get the primary teaching ROI for the current context."""
        special_roi = self._get_special_event_roi_from_action()
        if special_roi:
            return special_roi

        x1 = getattr(self.action, 'teaching_corner_x1', None)
        y1 = getattr(self.action, 'teaching_corner_y1', None)
        x2 = getattr(self.action, 'teaching_corner_x2', None)
        y2 = getattr(self.action, 'teaching_corner_y2', None)
        if x1 is not None and y1 is not None and x2 is not None and y2 is not None:
            w = int(x2) - int(x1)
            h = int(y2) - int(y1)
            if w > 0 and h > 0:
                return (int(x1), int(y1), w, h)

        return self._get_fixed_roi_from_action()

    def _get_special_event_roi_from_action(self) -> Optional[tuple]:
        """Get event-specific OCR ROI for the current algorithm context."""
        if self.algorithm_field == "imperial_guardian_ocr_algorithms":
            return self._get_imperial_guardian_roi_from_action()

        if self.algorithm_field == "golden_invasion_channel_ocr_algorithms":
            prefix = "golden_invasion_channel_roi"
        elif self.algorithm_field == "golden_invasion_notify_ocr_algorithms":
            prefix = "golden_invasion_notify_roi"
        elif self.algorithm_field == "monster_invasion_channel_ocr_algorithms":
            prefix = "monster_invasion_channel_roi"
        elif self.algorithm_field == "monster_invasion_notify_ocr_algorithms":
            prefix = "monster_invasion_notify_roi"
        else:
            return None

        x1 = getattr(self.action, f"{prefix}_x1", None)
        y1 = getattr(self.action, f"{prefix}_y1", None)
        x2 = getattr(self.action, f"{prefix}_x2", None)
        y2 = getattr(self.action, f"{prefix}_y2", None)
        if x1 is None or y1 is None or x2 is None or y2 is None:
            return None

        x1 = int(x1)
        y1 = int(y1)
        w = int(x2) - x1
        h = int(y2) - y1
        if w > 0 and h > 0:
            return (x1, y1, w, h)
        return None

    def _draw_capture_teaching_highlight(self, image_width: int, image_height: int) -> None:
        """Overlay teaching ROI highlight on the window capture preview."""
        roi = self._get_teaching_roi_from_action()
        if not roi:
            return

        x, y, w, h = roi
        transform_info = getattr(self, "_capture_preview_transform", None) or {}
        src_w = float(transform_info.get("src_w", image_width) or image_width)
        src_h = float(transform_info.get("src_h", image_height) or image_height)
        dst_w = float(transform_info.get("dst_w", image_width) or image_width)
        dst_h = float(transform_info.get("dst_h", image_height) or image_height)
        scale_x = (dst_w / src_w) if src_w > 0 else 1.0
        scale_y = (dst_h / src_h) if src_h > 0 else 1.0
        x = float(x) * scale_x
        y = float(y) * scale_y
        w = float(w) * scale_x
        h = float(h) * scale_y
        if w <= 0 or h <= 0 or image_width <= 0 or image_height <= 0:
            return

        x = max(0, min(int(x), image_width - 1))
        y = max(0, min(int(y), image_height - 1))
        x2 = max(x + 1, min(int(x + w), image_width))
        y2 = max(y + 1, min(int(y + h), image_height))
        rect = QRectF(float(x), float(y), float(x2 - x), float(y2 - y))
        if rect.width() <= 0 or rect.height() <= 0:
            return

        overlay_pen = QPen(QColor(255, 214, 10), 2)
        overlay_brush = QBrush(QColor(255, 214, 10, 45))
        rect_item = self.capture_scene.addRect(rect, overlay_pen, overlay_brush)
        rect_item.setZValue(10)

        label_item = QGraphicsSimpleTextItem("Teaching ROI")
        label_item.setBrush(QBrush(QColor(255, 214, 10)))
        label_item.setPos(rect.left() + 4, rect.top() + 4)
        label_item.setZValue(11)
        self.capture_scene.addItem(label_item)

    def _draw_capture_best_match_highlight(self, capture_path: str, image_width: int, image_height: int) -> None:
        """Overlay the best template match bbox produced by Test Selected."""
        bbox = self.test_match_bboxes.get(capture_path)
        if not bbox:
            return

        x, y, w, h = bbox
        transform_info = getattr(self, "_capture_preview_transform", None) or {}
        src_w = float(transform_info.get("src_w", image_width) or image_width)
        src_h = float(transform_info.get("src_h", image_height) or image_height)
        dst_w = float(transform_info.get("dst_w", image_width) or image_width)
        dst_h = float(transform_info.get("dst_h", image_height) or image_height)
        scale_x = (dst_w / src_w) if src_w > 0 else 1.0
        scale_y = (dst_h / src_h) if src_h > 0 else 1.0
        x = float(x) * scale_x
        y = float(y) * scale_y
        w = float(w) * scale_x
        h = float(h) * scale_y
        if w <= 0 or h <= 0 or image_width <= 0 or image_height <= 0:
            return

        x = max(0, min(int(round(x)), image_width - 1))
        y = max(0, min(int(round(y)), image_height - 1))
        x2 = max(x + 1, min(int(round(x + w)), image_width))
        y2 = max(y + 1, min(int(round(y + h)), image_height))
        rect = QRectF(float(x), float(y), float(x2 - x), float(y2 - y))
        if rect.width() <= 0 or rect.height() <= 0:
            return

        pen_width = max(3, int(round(min(image_width, image_height) / 220)))
        outline_pen = QPen(QColor(0, 0, 0), pen_width + 2)
        match_pen = QPen(QColor(255, 0, 255), pen_width)
        match_brush = QBrush(QColor(255, 0, 255, 25))

        outline_item = self.capture_scene.addRect(rect, outline_pen, QBrush(Qt.BrushStyle.NoBrush))
        outline_item.setZValue(20)
        rect_item = self.capture_scene.addRect(rect, match_pen, match_brush)
        rect_item.setZValue(21)

        score = self.test_results.get(capture_path)
        label = "Best Match" if score is None else f"Best Match {float(score):.3f}"
        label_item = QGraphicsSimpleTextItem(label)
        label_font = QFont()
        label_font.setBold(True)
        label_font.setPointSize(max(10, int(round(min(image_width, image_height) / 90))))
        label_item.setFont(label_font)
        label_item.setBrush(QBrush(QColor(255, 0, 255)))
        label_item.setPos(rect.left() + pen_width, max(0.0, rect.top() - label_item.boundingRect().height() - pen_width))
        label_item.setZValue(22)
        self.capture_scene.addItem(label_item)

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
        algorithms = self._get_current_algorithms()
        matching_roi, matching_score = self._get_matching_roi_for_ocr(image_path, algorithms)
        fallback_roi = self._get_special_event_roi_from_action() or self._get_fixed_roi_from_action()
        if self.teaching_image_path and not matching_roi and not fallback_roi:
            self._show_ocr_message(f"Không OCR toàn màn hình: không tìm thấy matching ROI (score={matching_score:.3f})")
            return
        fixed_roi = matching_roi or fallback_roi
        screenshot_name = os.path.basename(image_path)
        if matching_roi:
            screenshot_name = f"{screenshot_name} [match {matching_score:.3f}]"

        self.ocr_progress_bar.setVisible(True)
        self.ocr_progress_bar.setRange(0, 0)
        self.run_ocr_btn.setEnabled(False)

        # Console logging when OCR starts
        print(f"\n{'='*60}")
        print(f"🚀 OCR PROCESS STARTED")
        print(f"{'='*60}")
        print(f"📊 Engine: {engine_name}")
        print(f"🖼️  Image: {image_path}")
        print(f"⚙️  Algorithms: {len(algorithms)} algorithms")
        for i, algo in enumerate(algorithms):
            print(f"    {i+1}. {algo.get('name', 'Unknown')}")
        print(f"🎯 ROI: {fixed_roi if fixed_roi else 'None (full image)'}")
        print(f"{'='*60}\n")

        print(f"[OCR] Matching ROI: {matching_roi if matching_roi else 'None'} score={matching_score:.3f}")
        print(f"[OCR] Final OCR ROI: {fixed_roi if fixed_roi else 'None (full image)'}")
        self._start_ocr_thread(image_path, engine_name, algorithms, fixed_roi, screenshot_name)

    def _get_matching_roi_for_ocr(self, image_path: str, algorithms: list) -> tuple[Optional[tuple], float]:
        """Return the matched template bbox so OCR reads the matched region instead of the whole screenshot."""
        if not self.teaching_image_path or not os.path.exists(self.teaching_image_path):
            return None, 0.0

        try:
            with open(image_path, "rb") as f:
                file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
            screenshot_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        except Exception as exc:
            print(f"[OCR] Cannot load screenshot for matching ROI: {exc}")
            return None, 0.0

        if screenshot_bgr is None:
            return None, 0.0

        try:
            from ..logic.system_executor.system_executor import SystemExecutor

            executor = SystemExecutor(target_window_hwnd=None)
            image_result, score = executor.match_template_against_image_with_score_adaptive(
                screenshot_bgr=screenshot_bgr,
                template_path=self.teaching_image_path,
                threshold=float(getattr(self.action, "match_threshold", 0.0) or 0.0),
                ignore_text=False,
                multiscale_enabled=bool(getattr(self.action, "multiscale_enabled", True)),
                multiscale_min=float(getattr(self.action, "multiscale_min", 0.70) or 0.70),
                multiscale_max=float(getattr(self.action, "multiscale_max", 1.30) or 1.30),
                multiscale_step=float(getattr(self.action, "multiscale_step", 0.05) or 0.05),
                mask_regions=getattr(self.action, "mask_regions", None),
                preprocessing_algorithms=algorithms,
                teaching_window_width=getattr(self.action, "teaching_window_width", None) or 800,
                teaching_window_height=getattr(self.action, "teaching_window_height", None) or 600,
            )
            score = float(score or 0.0)
            if not image_result or len(image_result) < 4:
                print(f"[OCR] No matching ROI found for OCR, score={score:.3f}")
                return None, score

            x, y, w, h = image_result[:4]
            roi = (int(x), int(y), int(w), int(h))
            print(f"[OCR] Using matching ROI for OCR: {roi}, score={score:.3f}")
            return roi, score
        except Exception as exc:
            print(f"[OCR] Matching ROI failed: {exc}")
            return None, 0.0

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
        
        # Console logging for OCR results
        print(f"\n{'='*60}")
        print(f"🔍 OCR RESULTS COMPLETED")
        print(f"{'='*60}")
        print(f"📊 Engine: {engine}")
        print(f"🖼️  Screenshot: {screenshot_name}")
        print(f"⚙️  Algorithms: {algo_names}")
        print(f"⏱️  Processing Time: {processing_time:.2f}s")
        print(f"📄 OCR Text:")
        print(f"{'-'*40}")
        if text.strip():
            print(f"\"{text.strip()}\"")
        else:
            print("(No text detected)")
        print(f"{'-'*40}")
        print(f"🎯 Confidence: {conf}")
        print(f"📏 Text Length: {len(text.strip())} characters")
        print(f"{'='*60}\n")

        self._add_ocr_result_row(engine, algo_names, screenshot_name, text, conf, processing_time)

    def _on_ocr_error(self, engine: str, screenshot_name: str, error: str):
        """Handle OCR error (thread-safe via signal)."""
        self.ocr_progress_bar.setVisible(False)
        self.run_ocr_btn.setEnabled(True)
        
        # Console logging for OCR errors
        print(f"\n{'='*60}")
        print(f"❌ OCR ERROR")
        print(f"{'='*60}")
        print(f"📊 Engine: {engine}")
        print(f"🖼️  Screenshot: {screenshot_name}")
        print(f"🚨 Error: {error}")
        print(f"{'='*60}\n")
        
        self._add_ocr_result_row(engine, "N/A", screenshot_name, f"Error: {error}", "N/A", 0.0)

    def _add_ocr_result_row(self, engine: str, algo_names: str, screenshot_name: str,
                             text: str, conf: str, processing_time: float):
        """Add a new row to OCR results table (7 columns).
        
        Columns: No., Engine, Algorithms, Screenshot, Text, Conf, Time (ms)
        """
        row = self.ocr_results_table.rowCount()
        self.ocr_results_table.insertRow(row)

        # Truncate long text to 50 chars + '...'
        display_text = text if len(text) <= 50 else text[:50] + "..."
        text_item = QTableWidgetItem(display_text)
        text_item.setToolTip(text)  # Full text on hover
        text_item.setData(Qt.ItemDataRole.UserRole, text)

        self.ocr_results_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.ocr_results_table.setItem(row, 1, QTableWidgetItem(engine.title()))
        self.ocr_results_table.setItem(row, 2, QTableWidgetItem(algo_names))
        self.ocr_results_table.setItem(row, 3, QTableWidgetItem(screenshot_name))
        self.ocr_results_table.setItem(row, 4, text_item)
        self.ocr_results_table.setItem(row, 5, QTableWidgetItem(conf))
        self.ocr_results_table.setItem(row, 6, QTableWidgetItem(f"{processing_time:.1f}"))

    def _show_ocr_message(self, message: str):
        """Show OCR message."""
        print(f"[OCR] {message}")

    def _on_ocr_cell_clicked(self, row: int, col: int):
        """Show OCR text and post-OCR pattern analysis when clicking Text column."""
        if col != 4:
            return
        item = self.ocr_results_table.item(row, col)
        if not item:
            return

        full_text = str(item.data(Qt.ItemDataRole.UserRole) or item.toolTip() or item.text() or "")
        default_pattern = str(getattr(self.action, "event_ocr_pattern", "") or "")
        current_threshold = float(getattr(self, "_post_ocr_match_threshold", 100.0) or 100.0)

        dialog = QDialog(self)
        dialog.setWindowTitle("OCR Text")
        dialog.resize(900, 650)
        layout = QVBoxLayout(dialog)

        splitter = QSplitter(Qt.Orientation.Horizontal, dialog)

        raw_panel = QWidget(splitter)
        raw_layout = QVBoxLayout(raw_panel)
        raw_layout.addWidget(QLabel("OCR Raw Text", raw_panel))
        editor = QPlainTextEdit(raw_panel)
        editor.setReadOnly(True)
        editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        editor.setPlainText(full_text)
        raw_layout.addWidget(editor)
        splitter.addWidget(raw_panel)

        analysis_panel = QWidget(splitter)
        analysis_layout = QVBoxLayout(analysis_panel)
        analysis_layout.addWidget(QLabel("Post-OCR Analysis", analysis_panel))
        analysis_layout.addWidget(QLabel("Pattern", analysis_panel))
        pattern_hint = QLabel(
            "Text thường: fuzzy match theo threshold | {...}: capture giá trị, bỏ qua khi tính match | [...]: phải khớp chính xác",
            analysis_panel,
        )
        pattern_hint.setWordWrap(True)
        analysis_layout.addWidget(pattern_hint)

        pattern_edit = QPlainTextEdit(analysis_panel)
        pattern_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        pattern_edit.setPlaceholderText("Sự kiện {event_name} sẽ bắt đầu sau [3] phút nữa")
        pattern_edit.setPlainText(default_pattern)
        pattern_edit.setMaximumHeight(110)
        analysis_layout.addWidget(pattern_edit)

        run_btn_row = QHBoxLayout()
        run_pattern_btn = QPushButton("Run theo pattern thông báo", analysis_panel)
        run_btn_row.addWidget(run_pattern_btn)
        settings_btn = QPushButton("Setting", analysis_panel)
        settings_btn.setFixedWidth(90)
        run_btn_row.addWidget(settings_btn)
        run_btn_row.addStretch()
        analysis_layout.addLayout(run_btn_row)

        analysis_layout.addWidget(QLabel("Result", analysis_panel))
        result_view = QPlainTextEdit(analysis_panel)
        result_view.setReadOnly(True)
        result_view.setMaximumHeight(90)
        analysis_layout.addWidget(result_view)

        analysis_layout.addWidget(QLabel("Analysis", analysis_panel))
        analysis_view = QPlainTextEdit(analysis_panel)
        analysis_view.setReadOnly(True)
        analysis_layout.addWidget(analysis_view)
        splitter.addWidget(analysis_panel)

        splitter.setSizes([450, 450])
        layout.addWidget(splitter)

        self._run_post_ocr_analysis(full_text, default_pattern, current_threshold, result_view, analysis_view)
        run_pattern_btn.clicked.connect(
            lambda: self._run_post_ocr_analysis(
                full_text,
                pattern_edit.toPlainText(),
                float(getattr(self, "_post_ocr_match_threshold", 100.0) or 100.0),
                result_view,
                analysis_view,
            )
        )
        settings_btn.clicked.connect(lambda: self._open_post_ocr_settings(dialog))

        close_btn = QPushButton("Đóng", dialog)
        close_btn.clicked.connect(dialog.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
        dialog.exec()

    def _open_post_ocr_settings(self, parent_dialog: QDialog) -> None:
        """Open settings for post-OCR analysis."""
        dialog = QDialog(parent_dialog)
        dialog.setWindowTitle("Post-OCR Settings")
        dialog.resize(360, 220)

        layout = QVBoxLayout(dialog)
        ignore_checkbox = QCheckBox("Ignore Vietnamese diacritics", dialog)
        ignore_checkbox.setChecked(bool(self._post_ocr_ignore_vietnamese_diacritics))
        layout.addWidget(ignore_checkbox)
        layout.addWidget(QLabel("Threshold", dialog))
        threshold_spin = QDoubleSpinBox(dialog)
        threshold_spin.setRange(0.0, 100.0)
        threshold_spin.setDecimals(1)
        threshold_spin.setSingleStep(1.0)
        threshold_spin.setSuffix(" %")
        threshold_spin.setValue(float(getattr(self, "_post_ocr_match_threshold", 100.0) or 100.0))
        layout.addWidget(threshold_spin)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("Lưu", dialog)
        cancel_btn = QPushButton("Đóng", dialog)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        save_btn.clicked.connect(
            lambda: self._save_post_ocr_settings(
                ignore_checkbox.isChecked(),
                float(threshold_spin.value()),
                dialog,
            )
        )
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec()

    def _save_post_ocr_settings(self, ignore_diacritics: bool, threshold: float, dialog: QDialog) -> None:
        """Save post-OCR analysis settings."""
        self._post_ocr_ignore_vietnamese_diacritics = bool(ignore_diacritics)
        self._post_ocr_match_threshold = float(threshold)
        dialog.accept()

    def _run_post_ocr_analysis(
        self,
        ocr_text: str,
        pattern: str,
        threshold: float,
        result_view: QPlainTextEdit,
        analysis_view: QPlainTextEdit,
    ) -> None:
        """Run post-OCR pattern analysis using the project event matcher."""
        pattern = str(pattern or "").strip()
        if not ocr_text.strip():
            result_view.setPlainText("No OCR text")
            analysis_view.setPlainText("OCR text is empty, nothing to analyze.")
            return

        if not pattern:
            result_view.setPlainText("No pattern")
            analysis_view.setPlainText("Pattern trống. Hãy nhập pattern rồi bấm Run theo pattern thông báo.")
            return

        ignore_diacritics = bool(self._post_ocr_ignore_vietnamese_diacritics)
        raw_lines = self._split_raw_post_ocr_lines(ocr_text)
        normalized_lines = self._normalize_post_ocr_lines(raw_lines, ignore_diacritics)
        lines = self._extract_post_ocr_lines(ocr_text, pattern, ignore_diacritics)
        match = self._match_post_ocr_pattern(lines, pattern, threshold, ignore_diacritics)
        normalized_text = "\n".join(normalized_lines)

        if match:
            score = float(match.get("score", 0.0) or 0.0)
            variables = list(match.get("variables", []) or [])
            line = str(match.get("line", "") or "")
            result_lines = [
                "Matched",
                f"Score: {score:.1f} / threshold {threshold:.1f}",
                f"Line: {line}",
            ]
            if variables:
                result_lines.append("Variables:")
                for key, value in variables:
                    result_lines.append(f"- {key} = {value}")
            result_view.setPlainText("\n".join(result_lines))

            analysis_lines = [
                f"Pattern: {pattern}",
                f"Ignore Vietnamese diacritics: {ignore_diacritics}",
                f"Matched line index: {int(match.get('line_index', 0) or 0)}",
                f"Raw OCR lines: {len(raw_lines)}",
                "Raw OCR lines:",
            ]
            analysis_lines.extend(self._format_post_ocr_line_blocks(raw_lines))
            analysis_lines.extend(
                [
                    "",
                    f"Normalized OCR lines: {len(normalized_lines)}",
                    "Normalized OCR lines:",
                ]
            )
            analysis_lines.extend(self._format_post_ocr_line_blocks(normalized_lines))
            analysis_lines.extend(
                [
                    "",
                    f"Extracted candidate lines: {len(lines)}",
                    "Candidate lines:",
                ]
            )
            analysis_lines.extend(self._format_post_ocr_line_blocks(lines))
            analysis_lines.extend(
                [
                    "",
                    "Normalized OCR text (line-preserved):",
                    normalized_text,
                ]
            )
            analysis_view.setPlainText("\n".join(analysis_lines))
            return

        result_view.setPlainText(f"Not matched\nThreshold: {threshold:.1f}")
        analysis_lines = [
            f"Pattern: {pattern}",
            f"Ignore Vietnamese diacritics: {ignore_diacritics}",
            "Result: no match",
        ]
        analysis_lines.extend([f"Raw OCR lines: {len(raw_lines)}", "Raw OCR lines:"])
        analysis_lines.extend(self._format_post_ocr_line_blocks(raw_lines))
        analysis_lines.extend(
            [
                "",
                f"Normalized OCR lines: {len(normalized_lines)}",
                "Normalized OCR lines:",
            ]
        )
        analysis_lines.extend(self._format_post_ocr_line_blocks(normalized_lines))
        analysis_lines.extend(
            [
                "",
                f"Extracted candidate lines: {len(lines)}",
                "Candidate lines:",
            ]
        )
        if lines:
            analysis_lines.extend(self._format_post_ocr_line_blocks(lines))
        else:
            analysis_lines.extend(self._format_post_ocr_line_blocks([]))
        analysis_lines.extend(["", "Normalized OCR text (line-preserved):", normalized_text])
        analysis_view.setPlainText("\n".join(analysis_lines))

    def _format_post_ocr_line_blocks(self, lines: list[str], separator_width: int = 54) -> list[str]:
        """Render OCR lines as readable blocks separated by fixed-width dashes."""
        separator = "-" * max(10, int(separator_width))
        if not lines:
            return ["<none>"]

        blocks: list[str] = []
        for index, line in enumerate(lines):
            blocks.append(str(line or ""))
            if index < len(lines) - 1:
                blocks.append(separator)
        return blocks

    def _split_raw_post_ocr_lines(self, text: str) -> list[str]:
        """Split OCR text into visible raw lines without flattening whitespace."""
        value = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
        return [line.strip() for line in value.split("\n") if line.strip()]

    def _normalize_post_ocr_lines(self, lines: list[str], ignore_diacritics: bool) -> list[str]:
        """Normalize OCR lines while preserving line boundaries for display."""
        normalized = []
        for line in lines:
            norm_line = self._normalize_post_ocr_text(line, ignore_diacritics)
            if norm_line:
                normalized.append(norm_line)
        return normalized

    def _normalize_post_ocr_text(self, text: str, ignore_diacritics: bool) -> str:
        """Normalize OCR text for post-analysis matching."""
        import re as _re
        import unicodedata

        value = str(text or "")
        if not value:
            return ""

        if ignore_diacritics:
            value = value.replace("\u0111", "d").replace("\u0110", "D")
            nfd = unicodedata.normalize("NFD", value)
            value = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
        value = value.lower()
        value = _re.sub(r"[|_~^`]", " ", value)
        value = _re.sub(r"\s+", " ", value).strip()
        return value

    def _extract_post_ocr_lines(self, ocr_text: str, pattern: str, ignore_diacritics: bool) -> list[str]:
        """Extract likely OCR lines for dialog-side post-analysis."""
        if not ocr_text:
            return []

        text = str(ocr_text or "").replace("\r\n", "\n").replace("\r", "\n")
        raw_lines = [" ".join(line.split()).strip() for line in text.split("\n") if line.strip()]
        candidate_lines = raw_lines[:] if raw_lines else []
        static_chunks = []
        for part in __import__("re").split(r"\{(?:NUMBER|TEXT|\w+)\}", pattern or ""):
            norm_part = self._normalize_post_ocr_text(part, ignore_diacritics)
            if len(norm_part) >= 4:
                static_chunks.append(norm_part)

        filtered_lines = []
        for line in candidate_lines:
            norm_line = self._normalize_post_ocr_text(line, ignore_diacritics)
            if static_chunks and any(chunk in norm_line for chunk in static_chunks):
                filtered_lines.append(line)
                continue
            if "su kien" in norm_line or "imperial guardian" in norm_line:
                filtered_lines.append(line)

        source_lines = filtered_lines or candidate_lines
        seen = set()
        result = []
        for line in source_lines:
            dedup_key = self._normalize_post_ocr_text(line, ignore_diacritics)
            if not dedup_key or dedup_key in seen:
                continue
            seen.add(dedup_key)
            result.append(line)
        return result

    def _match_post_ocr_pattern(
        self,
        lines: list[str],
        pattern: str,
        threshold: float,
        ignore_diacritics: bool,
    ) -> Optional[dict]:
        """Match OCR lines against the configured pattern using ordered fuzzy static chunks."""
        import re
        from difflib import SequenceMatcher

        if not lines or not pattern:
            return None

        try:
            from rapidfuzz import fuzz
        except Exception:
            fuzz = None
        strict_full_text_match = False

        def _score_ratio(left: str, right: str) -> float:
            left = str(left or "")
            right = str(right or "")
            if not left or not right:
                return 0.0
            if fuzz is not None:
                try:
                    return float(fuzz.ratio(left, right))
                except Exception:
                    pass
            return float(SequenceMatcher(None, left, right).ratio() * 100.0)

        def _ordered_chunk_match(candidate: str, chunks: list[dict]) -> Optional[dict]:
            """Match static chunks in order and score by weighted similarity/exact rules."""
            if not chunks:
                return None

            cursor = 0
            total_weight = 0
            total_score = 0.0
            chunk_matches: list[dict] = []

            for chunk_index, chunk_info in enumerate(chunks):
                search_text = candidate[cursor:]
                if not search_text:
                    return None

                best_local = None
                chunk = str(chunk_info.get("text", "") or "")
                mode = str(chunk_info.get("mode", "fuzzy") or "fuzzy")
                chunk_len = len(chunk)
                min_window = max(1, chunk_len - 4)
                max_window = min(len(search_text), chunk_len + max(8, chunk_len // 2))
                if max_window < min_window:
                    max_window = min_window

                if mode == "exact":
                    exact_match = re.search(
                        rf"(?<![0-9a-z]){re.escape(chunk)}(?![0-9a-z])",
                        search_text,
                    )
                    if not exact_match:
                        return None
                    best_local = {
                        "score": 100.0,
                        "start": cursor + int(exact_match.start()),
                        "end": cursor + int(exact_match.end()),
                        "matched_text": exact_match.group(0),
                        "chunk": chunk,
                        "chunk_index": chunk_index,
                        "mode": mode,
                    }
                else:
                    if strict_full_text_match:
                        chunk_tokens = [token for token in chunk.split() if token]
                        candidate_tokens = [
                            (match.group(0), int(match.start()), int(match.end()))
                            for match in re.finditer(r"\S+", search_text)
                        ]
                        if not chunk_tokens or not candidate_tokens:
                            return None

                        min_token_window = max(1, len(chunk_tokens) - 1)
                        max_token_window = min(len(candidate_tokens), len(chunk_tokens) + 2)

                        for start_idx in range(len(candidate_tokens)):
                            remaining_tokens = len(candidate_tokens) - start_idx
                            if remaining_tokens < min_token_window:
                                break
                            local_max_token_window = min(max_token_window, remaining_tokens)
                            for token_window_size in range(min_token_window, local_max_token_window + 1):
                                window = candidate_tokens[start_idx:start_idx + token_window_size]
                                sample_tokens = [token for token, _, _ in window]
                                position_count = max(len(chunk_tokens), len(sample_tokens))
                                pair_count = min(len(chunk_tokens), len(sample_tokens))
                                pair_scores = [
                                    _score_ratio(chunk_tokens[i], sample_tokens[i])
                                    for i in range(pair_count)
                                ]
                                token_score_sum = sum(pair_scores)
                                score = token_score_sum / float(position_count) if position_count > 0 else 0.0
                                if pair_scores and min(pair_scores) < 45.0:
                                    score *= 0.5
                                sample = " ".join(sample_tokens)
                                if best_local is None or score > best_local["score"]:
                                    best_local = {
                                        "score": score,
                                        "start": cursor + window[0][1],
                                        "end": cursor + window[-1][2],
                                        "matched_text": sample,
                                        "chunk": chunk,
                                        "chunk_index": chunk_index,
                                        "mode": mode,
                                        "token_scores": pair_scores,
                                    }
                    else:
                        for start in range(len(search_text)):
                            remaining = len(search_text) - start
                            if remaining < min_window:
                                break
                            local_max_window = min(max_window, remaining)
                            for window_size in range(min_window, local_max_window + 1):
                                sample = search_text[start:start + window_size]
                                score = _score_ratio(chunk, sample)
                                if best_local is None or score > best_local["score"]:
                                    best_local = {
                                        "score": score,
                                        "start": cursor + start,
                                        "end": cursor + start + window_size,
                                        "matched_text": sample,
                                        "chunk": chunk,
                                        "chunk_index": chunk_index,
                                        "mode": mode,
                                    }

                if best_local is None:
                    return None

                total_weight += chunk_len
                total_score += best_local["score"] * chunk_len
                chunk_matches.append(best_local)
                cursor = best_local["end"]

            overall_score = (total_score / total_weight) if total_weight > 0 else 0.0
            overall_score = max(0.0, min(100.0, overall_score))
            return {"score": overall_score, "chunks": chunk_matches}

        token_regex = re.compile(r"(\{[^}]+\}|\[[^\]]+\])")
        token_parts = token_regex.split(pattern)
        placeholders: list[str] = []
        chunk_specs: list[dict] = []
        raw_static_chunks: list[str] = []

        for token in token_parts:
            if not token:
                continue
            if token.startswith("{") and token.endswith("}"):
                placeholders.append(token[1:-1].strip())
                raw_static_chunks.append("")
                continue
            if token.startswith("[") and token.endswith("]"):
                exact_text = self._normalize_post_ocr_text(token[1:-1], ignore_diacritics)
                if exact_text:
                    chunk_specs.append({"text": exact_text, "mode": "exact"})
                    raw_static_chunks.append(token[1:-1])
                continue

            normalized_static = self._normalize_post_ocr_text(token, ignore_diacritics)
            if normalized_static:
                chunk_specs.append({"text": normalized_static, "mode": "fuzzy"})
                raw_static_chunks.append(token)

        placeholder_sanitized_pattern = re.sub(r"\{[^}]+\}", " ", pattern)
        placeholder_sanitized_pattern = re.sub(r"\[([^\]]+)\]", r"\1", placeholder_sanitized_pattern)
        normalized_pattern = self._normalize_post_ocr_text(
            placeholder_sanitized_pattern,
            ignore_diacritics,
        )
        strict_full_text_match = (not placeholders) and not any(
            str(spec.get("mode", "fuzzy") or "fuzzy") == "exact"
            for spec in chunk_specs
        )

        best_match = None
        best_score = -1.0
        for line_index, line in enumerate(lines):
            compare_line = self._normalize_post_ocr_text(line, ignore_diacritics)
            if not compare_line:
                continue

            variables: list[tuple[str, str]] = []
            chunk_debug: list[dict] = []

            if chunk_specs:
                ordered_match = _ordered_chunk_match(compare_line, chunk_specs)
                if ordered_match is None:
                    continue
                score = float(ordered_match["score"])
                chunk_debug = list(ordered_match["chunks"])

                if placeholders:
                    for idx, name in enumerate(placeholders):
                        prev_end = chunk_debug[idx]["end"] if idx < len(chunk_debug) else 0
                        next_start = chunk_debug[idx + 1]["start"] if idx + 1 < len(chunk_debug) else len(compare_line)
                        if idx == 0 and raw_static_chunks and not self._normalize_post_ocr_text(raw_static_chunks[0], ignore_diacritics):
                            prev_end = 0
                        if idx == len(placeholders) - 1 and len(raw_static_chunks) > len(placeholders) and not self._normalize_post_ocr_text(raw_static_chunks[-1], ignore_diacritics):
                            next_start = len(compare_line)
                        captured = compare_line[prev_end:next_start].strip()
                        variables.append((name, captured))
            else:
                score = _score_ratio(normalized_pattern, compare_line) if normalized_pattern else 0.0

            if score >= threshold and score > best_score:
                best_score = score
                best_match = {
                    "score": score,
                    "variables": variables,
                    "line": line,
                    "line_index": line_index,
                    "chunk_matches": chunk_debug,
                }

        return best_match


class OCRWorkerThread(QThread):
    """Background thread for OCR processing."""
    
    # engine, screenshot_name, algo_names, time_ms, text, conf
    ocr_completed = pyqtSignal(str, str, str, float, str, str)
    ocr_error = pyqtSignal(str, str, str)  # engine, screenshot_name, error
    
    def __init__(self, image_path: str, engine_name: str, algorithms: list,
                 fixed_roi: Optional[tuple] = None, screenshot_name: str = ""):
        super().__init__()
        self.image_path = image_path
        self.engine_name = engine_name
        self.algorithms = algorithms
        self.fixed_roi = fixed_roi  # (x, y, w, h) or None
        self.screenshot_name = screenshot_name or os.path.basename(image_path)
    
    def run(self):
        """Run OCR on screenshot with optional Fixed ROI crop."""
        try:
            import time
            start_time = time.perf_counter()
            
            import cv2
            img = cv2.imread(self.image_path)
            if img is None:
                self.ocr_error.emit(self.engine_name, self.screenshot_name, "Cannot load image")
                return
            
            # Crop theo Fixed ROI jika có
            if self.fixed_roi:
                x, y, w, h = self.fixed_roi
                img_h, img_w = img.shape[:2]
                
                # Validate ROI - emit error if completely outside image bounds
                if x >= img_w or y >= img_h or x + w <= 0 or y + h <= 0:
                    self.ocr_error.emit(self.engine_name, self.screenshot_name, 
                                      f"ROI {self.fixed_roi} is outside image bounds {img_w}x{img_h}")
                    return
                
                x = max(0, min(x, img_w - 1))
                y = max(0, min(y, img_h - 1))
                x2 = max(x + 1, min(x + w, img_w))
                y2 = max(y + 1, min(y + h, img_h))
                img = img[y:y2, x:x2]
            
            # Apply preprocessing algorithms và collect names
            algo_names = []
            for algo in self.algorithms:
                img = self._apply_preprocessing(img, algo.get("config", {}))
                algo_names.append(algo.get("name", "Unknown"))
            
            algo_names_str = ", ".join(algo_names) if algo_names else "None"
            
            # Run OCR
            try:
                from ..logic.system_executor.ocr_engine import OCRFactory
                engine = OCRFactory.create(self.engine_name)
                
                if not engine:
                    self.ocr_error.emit(self.engine_name, self.screenshot_name, "Engine not available")
                    return
                
                recognize_lines_fn = getattr(engine, "recognize_lines", None)
                if callable(recognize_lines_fn):
                    lines = recognize_lines_fn(img)
                    if isinstance(lines, (list, tuple)):
                        text = "\n".join(str(line or "").strip() for line in lines if str(line or "").strip()).strip()
                    else:
                        text = str(engine.recognize(img) or "")
                else:
                    text = str(engine.recognize(img) or "")
                processing_time = (time.perf_counter() - start_time) * 1000  # ms
                
                print(f"[DEBUG OCR] engine={self.engine_name}, text_len={len(text)}, text_preview={repr(text[:80])}")
                self.ocr_completed.emit(self.engine_name, self.screenshot_name, algo_names_str,
                                        processing_time, text, "N/A")
                
            except ImportError:
                self.ocr_error.emit(self.engine_name, self.screenshot_name, "OCR engine not available")
            
        except Exception as e:
            self.ocr_error.emit(self.engine_name, self.screenshot_name, str(e))
    
    def _apply_preprocessing(self, img: np.ndarray, config: dict) -> np.ndarray:
        """Apply single preprocessing algorithm."""
        try:
            from ..logic.system_executor.ocr_preprocessor import OCRPreprocessor

            if config.get("dominant_color_merge"):
                img = _apply_dominant_color_merge_to_bgr(img, config)

            if config.get("rgb_range_filter"):
                img = _apply_rgb_range_filter_to_bgr(img, config)

            preprocessor = OCRPreprocessor(img)
            
            if config.get("upscale"):
                preprocessor = preprocessor.upscale(config["upscale"])
            if config.get("enhance_contrast"):
                preprocessor = preprocessor.enhance_contrast()
            if config.get("sharpen"):
                preprocessor = preprocessor.sharpen()
            if config.get("denoise"):
                preprocessor = preprocessor.denoise()
            if config.get("threshold"):
                preprocessor = preprocessor.threshold(config["threshold"])
            
            return preprocessor.build()
            
        except Exception as e:
            print(f"[WARNING] Preprocessing failed: {e}, using original image")
            return img
        self._update_ocr_results_display(engine, 0.0, f"Error: {error}")

    def _update_ocr_results_display(self, engine: str, processing_time: float, text: str):
        """Update OCR results table."""
        # Add row to table
        row = self.ocr_results_table.rowCount()
        self.ocr_results_table.insertRow(row)
        
        # Set row data
        self.ocr_results_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.ocr_results_table.setItem(row, 1, QTableWidgetItem(engine.title()))
        self.ocr_results_table.setItem(row, 2, QTableWidgetItem(f"{processing_time:.1f}"))
        
        # Text preview (first 50 chars)
        preview = text[:50] + "..." if len(text) > 50 else text
        self.ocr_results_table.setItem(row, 3, QTableWidgetItem(preview))

    def _show_ocr_message(self, message: str):
        """Show OCR message."""
        print(f"[OCR] {message}")
        # Could also show in status bar or message box if needed
