"""Image Detect Action Settings Dialog."""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QSpinBox, QCheckBox, QDoubleSpinBox, 
                             QGroupBox, QComboBox, QMessageBox, QLineEdit, QTextEdit,
                             QWidget, QFileDialog, QScrollArea, QListWidget, QAbstractItemView)
from PyQt6.QtCore import Qt
from ..logic.action_type import AutoAction
from .algorithm_display_utils import update_algorithms_display
import os
import json
import shutil


class ImageDetectSettingsDialog(QDialog):
    """Dialog for configuring IMAGE_DETECT action settings."""
    
    def __init__(self, action: AutoAction, parent=None, target_window_hwnd=None, tool_id: str = None):
        super().__init__(parent)
        self.action = action
        self.target_window_hwnd = target_window_hwnd
        self.tool_id = tool_id
        self.setWindowTitle("Cài đặt Image Detect Action")
        self.setFixedSize(620, 700)
        self._init_ui()
        self._load_settings()
    
    def _init_ui(self):
        """Initialize UI components."""
        # Main layout for dialog
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # Content widget inside scroll area
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        
        # Image recognition group
        recognition_group = QGroupBox("Nhận diện ảnh")
        recognition_layout = QVBoxLayout()
        
        thr_row = QHBoxLayout()
        thr_row.addWidget(QLabel("Ngưỡng nhận diện:"))
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setMinimum(0.10)
        self.threshold_spin.setMaximum(0.99)
        self.threshold_spin.setSingleStep(0.01)
        self.threshold_spin.setDecimals(2)
        self.threshold_spin.setValue(0.40)
        self.threshold_spin.setToolTip("Ngưỡng thấp = dễ nhận nhưng dễ nhầm\nNgưỡng cao = chính xác nhưng dễ fail")
        thr_row.addWidget(self.threshold_spin)
        thr_row.addStretch()
        recognition_layout.addLayout(thr_row)
        
        self.multiscale_checkbox = QCheckBox("Cho phép thay đổi kích thước (Multi-scale)")
        self.multiscale_checkbox.setChecked(True)
        self.multiscale_checkbox.stateChanged.connect(self._on_multiscale_changed)
        recognition_layout.addWidget(self.multiscale_checkbox)
        
        # Multiscale range settings
        multiscale_range_layout = QHBoxLayout()
        multiscale_range_layout.addWidget(QLabel("Khoảng scale:"))
        multiscale_range_layout.addWidget(QLabel("Min:"))
        self.multiscale_min_spin = QDoubleSpinBox()
        self.multiscale_min_spin.setMinimum(0.10)
        self.multiscale_min_spin.setMaximum(2.00)
        self.multiscale_min_spin.setSingleStep(0.05)
        self.multiscale_min_spin.setDecimals(2)
        self.multiscale_min_spin.setValue(0.70)
        multiscale_range_layout.addWidget(self.multiscale_min_spin)
        
        multiscale_range_layout.addWidget(QLabel("Max:"))
        self.multiscale_max_spin = QDoubleSpinBox()
        self.multiscale_max_spin.setMinimum(0.10)
        self.multiscale_max_spin.setMaximum(3.00)
        self.multiscale_max_spin.setSingleStep(0.05)
        self.multiscale_max_spin.setDecimals(2)
        self.multiscale_max_spin.setValue(1.30)
        multiscale_range_layout.addWidget(self.multiscale_max_spin)
        
        multiscale_range_layout.addWidget(QLabel("Step:"))
        self.multiscale_step_spin = QDoubleSpinBox()
        self.multiscale_step_spin.setMinimum(0.01)
        self.multiscale_step_spin.setMaximum(0.50)
        self.multiscale_step_spin.setSingleStep(0.01)
        self.multiscale_step_spin.setDecimals(2)
        self.multiscale_step_spin.setValue(0.05)
        multiscale_range_layout.addWidget(self.multiscale_step_spin)
        multiscale_range_layout.addStretch()
        
        self.multiscale_range_widget = QWidget()
        self.multiscale_range_widget.setLayout(multiscale_range_layout)
        self.multiscale_range_widget.setVisible(True)
        recognition_layout.addWidget(self.multiscale_range_widget)
        
        recognition_group.setLayout(recognition_layout)
        layout.addWidget(recognition_group)
        
        # Timeout settings
        timeout_group = QGroupBox("Thời gian chờ")
        timeout_layout = QVBoxLayout()
        
        timeout_row = QHBoxLayout()
        timeout_row.addWidget(QLabel("Thời gian tối đa chờ:"))
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setMinimum(1)
        self.timeout_spin.setMaximum(36000)
        self.timeout_spin.setValue(50)
        self.timeout_spin.setSuffix(" x 100ms")
        timeout_row.addWidget(self.timeout_spin)
        timeout_row.addStretch()
        timeout_layout.addLayout(timeout_row)
        
        interval_row = QHBoxLayout()
        interval_row.addWidget(QLabel("Chu kỳ kiểm tra:"))
        self.check_interval_spin = QSpinBox()
        self.check_interval_spin.setMinimum(1)
        self.check_interval_spin.setMaximum(600)
        self.check_interval_spin.setValue(10)
        self.check_interval_spin.setSuffix(" x 100ms")
        interval_row.addWidget(self.check_interval_spin)
        interval_row.addStretch()
        timeout_layout.addLayout(interval_row)
        
        self.continue_on_timeout_checkbox = QCheckBox("Timeout → làm tiếp bước sau")
        timeout_layout.addWidget(self.continue_on_timeout_checkbox)
        
        # Timeout goto step
        timeout_goto_row = QHBoxLayout()
        self.timeout_goto_checkbox = QCheckBox("Timeout → nhảy về step:")
        self.timeout_goto_checkbox.stateChanged.connect(self._on_timeout_goto_changed)
        timeout_goto_row.addWidget(self.timeout_goto_checkbox)
        self.timeout_goto_spin = QSpinBox()
        self.timeout_goto_spin.setMinimum(0)
        self.timeout_goto_spin.setMaximum(100)
        self.timeout_goto_spin.setValue(1)
        self.timeout_goto_spin.setToolTip("0 = Restart cycle từ đầu (có delay)\n1-N = Nhảy về step cụ thể")
        self.timeout_goto_spin.setEnabled(False)
        self.timeout_goto_spin.setToolTip("Số thứ tự step (bắt đầu từ 1)")
        timeout_goto_row.addWidget(self.timeout_goto_spin)
        timeout_goto_row.addStretch()
        timeout_layout.addLayout(timeout_goto_row)
        
        delay_row = QHBoxLayout()
        delay_row.addWidget(QLabel("Delay sau khi thực hiện:"))
        self.delay_spin = QSpinBox()
        self.delay_spin.setMinimum(0)
        self.delay_spin.setMaximum(10000)
        self.delay_spin.setValue(10)
        self.delay_spin.setSuffix(" x 100ms")
        delay_row.addWidget(self.delay_spin)
        delay_row.addStretch()
        timeout_layout.addLayout(delay_row)
        
        timeout_group.setLayout(timeout_layout)
        layout.addWidget(timeout_group)
        
        # Read data group
        read_data_group = QGroupBox("Đọc dữ liệu")
        read_data_layout = QVBoxLayout()
        
        self.read_data_checkbox = QCheckBox("Đọc dữ liệu trong khung ảnh")
        self.read_data_checkbox.stateChanged.connect(self._on_read_data_changed)
        read_data_layout.addWidget(self.read_data_checkbox)
        
        read_data_group.setLayout(read_data_layout)
        layout.addWidget(read_data_group)
        
        # OCR settings (hidden by default)
        self.ocr_group = QGroupBox("Cài đặt OCR")
        ocr_layout = QVBoxLayout()
        
        ocr_engine_row = QHBoxLayout()
        ocr_engine_row.addWidget(QLabel("OCR engine:"))
        self.ocr_engine_combo = QComboBox()
        self.ocr_engine_combo.addItems([
            "Tự động (Auto)",
            "Windows OCR (WinRT)",
            "Tesseract (vie+eng)",
        ])
        ocr_engine_row.addWidget(self.ocr_engine_combo)
        ocr_engine_row.addStretch()
        ocr_layout.addLayout(ocr_engine_row)
        
        self.ocr_bright_on_dark_checkbox = QCheckBox("Làm nổi chữ sáng trên nền tối (OCR)")
        ocr_layout.addWidget(self.ocr_bright_on_dark_checkbox)
        
        # OCR preprocessing options
        ocr_layout.addWidget(QLabel("Tùy chọn tiền xử lý OCR:"))
        
        self.ocr_upscale_checkbox = QCheckBox("Phóng to ảnh trước OCR")
        self.ocr_upscale_checkbox.setChecked(True)
        self.ocr_upscale_checkbox.stateChanged.connect(self._on_ocr_upscale_changed)
        ocr_layout.addWidget(self.ocr_upscale_checkbox)
        
        upscale_factor_layout = QHBoxLayout()
        upscale_factor_layout.addWidget(QLabel("Hệ số phóng to:"))
        self.ocr_upscale_factor_spin = QDoubleSpinBox()
        self.ocr_upscale_factor_spin.setMinimum(1.0)
        self.ocr_upscale_factor_spin.setMaximum(5.0)
        self.ocr_upscale_factor_spin.setSingleStep(0.5)
        self.ocr_upscale_factor_spin.setDecimals(1)
        self.ocr_upscale_factor_spin.setValue(2.0)
        upscale_factor_layout.addWidget(self.ocr_upscale_factor_spin)
        upscale_factor_layout.addStretch()
        self.ocr_upscale_factor_widget = QWidget()
        self.ocr_upscale_factor_widget.setLayout(upscale_factor_layout)
        self.ocr_upscale_factor_widget.setVisible(True)
        ocr_layout.addWidget(self.ocr_upscale_factor_widget)
        
        self.ocr_enhance_contrast_checkbox = QCheckBox("Tăng độ tương phản (CLAHE)")
        self.ocr_enhance_contrast_checkbox.setChecked(True)
        ocr_layout.addWidget(self.ocr_enhance_contrast_checkbox)
        
        self.ocr_sharpen_checkbox = QCheckBox("Làm sắc nét (Unsharp Mask)")
        self.ocr_sharpen_checkbox.setChecked(True)
        ocr_layout.addWidget(self.ocr_sharpen_checkbox)
        
        self.ocr_denoise_checkbox = QCheckBox("Khử nhiễu (Bilateral Filter - chậm hơn)")
        self.ocr_denoise_checkbox.setChecked(False)
        ocr_layout.addWidget(self.ocr_denoise_checkbox)
        
        self.ocr_group.setLayout(ocr_layout)
        self.ocr_group.setVisible(False)
        layout.addWidget(self.ocr_group)
        
        # Gemini settings (hidden by default)
        self.gemini_group = QGroupBox("Cài đặt Gemini")
        gemini_layout = QVBoxLayout()
        
        self.gemini_checkbox = QCheckBox("Dùng Gemini để chiết xuất dữ liệu từ text OCR")
        self.gemini_checkbox.stateChanged.connect(self._on_gemini_changed)
        gemini_layout.addWidget(self.gemini_checkbox)
        
        # Gemini key status
        key_row = QHBoxLayout()
        self.gemini_key_status = QLabel("Chưa có key")
        self.gemini_key_status.setStyleSheet("color:#ff4d4d;")
        key_row.addWidget(self.gemini_key_status)
        self.gemini_key_btn = QPushButton("Cài key")
        self.gemini_key_btn.clicked.connect(self._open_gemini_key_dialog)
        key_row.addWidget(self.gemini_key_btn)
        key_row.addStretch()
        gemini_layout.addLayout(key_row)
        
        # Gemini timeout
        timeout_row = QHBoxLayout()
        timeout_row.addWidget(QLabel("Gemini timeout (giây):"))
        self.gemini_timeout_spin = QDoubleSpinBox()
        self.gemini_timeout_spin.setMinimum(1.0)
        self.gemini_timeout_spin.setMaximum(120.0)
        self.gemini_timeout_spin.setSingleStep(1.0)
        self.gemini_timeout_spin.setDecimals(0)
        self.gemini_timeout_spin.setValue(10.0)
        timeout_row.addWidget(self.gemini_timeout_spin)
        timeout_row.addStretch()
        gemini_layout.addLayout(timeout_row)
        
        # Gemini prompt
        gemini_layout.addWidget(QLabel("Gemini prompt (dùng {text} để chèn OCR text):"))
        self.gemini_prompt_btn = QPushButton("Cài đặt prompt")
        self.gemini_prompt_btn.clicked.connect(self._open_prompt_dialog)
        gemini_layout.addWidget(self.gemini_prompt_btn)
        
        self.gemini_group.setLayout(gemini_layout)
        self.gemini_group.setVisible(False)
        layout.addWidget(self.gemini_group)
        
        # Telegram notification (hidden by default)
        self.telegram_group = QGroupBox("Thông báo Telegram")
        telegram_layout = QVBoxLayout()
        
        self.notification_checkbox = QCheckBox("📱 Gửi kết quả đến Telegram")
        telegram_layout.addWidget(self.notification_checkbox)
        
        self.telegram_config_btn = QPushButton("⚙️ Cài đặt Telegram")
        self.telegram_config_btn.clicked.connect(self._open_telegram_config_dialog)
        telegram_layout.addWidget(self.telegram_config_btn)
        
        telegram_layout.addWidget(QLabel("🔍 Từ khóa bắt buộc (cách nhau bằng dấu phẩy):"))
        self.notification_filter_input = QLineEdit()
        self.notification_filter_input.setPlaceholderText("Ví dụ: success, completed, done")
        telegram_layout.addWidget(self.notification_filter_input)
        
        dedup_layout = QHBoxLayout()
        dedup_layout.addWidget(QLabel("Thời gian dedup (phút):"))
        self.notification_dedup_spin = QSpinBox()
        self.notification_dedup_spin.setMinimum(1)
        self.notification_dedup_spin.setMaximum(1440)  # Max 24 hours
        self.notification_dedup_spin.setValue(1)
        self.notification_dedup_spin.setToolTip("Tránh gửi thông báo trùng lặp trong khoảng thời gian này")
        dedup_layout.addWidget(self.notification_dedup_spin)
        dedup_layout.addStretch()
        telegram_layout.addLayout(dedup_layout)
        
        self.telegram_group.setLayout(telegram_layout)
        self.telegram_group.setVisible(False)
        layout.addWidget(self.telegram_group)
        
        # Teaching image
        teaching_group = QGroupBox("Ảnh Teaching")
        teaching_layout = QVBoxLayout()
        
        # Image path label
        self.image_path_label = QLabel("Chưa chọn ảnh")
        self.image_path_label.setWordWrap(True)
        teaching_layout.addWidget(self.image_path_label)
        
        # Buttons for image selection
        btn_row = QHBoxLayout()
        self.image_btn = QPushButton("Tạo ảnh Teaching")
        self.image_btn.clicked.connect(self._capture_teaching_image)
        btn_row.addWidget(self.image_btn)
        
        self.image_file_btn = QPushButton("Chọn file ảnh...")
        self.image_file_btn.clicked.connect(self._select_image_file)
        btn_row.addWidget(self.image_file_btn)
        
        self.test_algo_btn = QPushButton("🧪 Test Algorithms")
        self.test_algo_btn.clicked.connect(self._open_algorithm_testing_dialog)
        btn_row.addWidget(self.test_algo_btn)
        
        btn_row.addStretch()
        teaching_layout.addLayout(btn_row)
        
        teaching_group.setLayout(teaching_layout)
        layout.addWidget(teaching_group)
        
        # Template Matching Preprocessing section
        self._add_template_matching_preprocessing_section(layout)
        
        # Goto step
        goto_group = QGroupBox("Nhảy về step")
        goto_layout = QHBoxLayout()
        self.goto_step_checkbox = QCheckBox("🔄 Khi thành công, nhảy về step:")
        self.goto_step_checkbox.stateChanged.connect(self._on_goto_step_changed)
        goto_layout.addWidget(self.goto_step_checkbox)
        self.goto_step_spin = QSpinBox()
        self.goto_step_spin.setMinimum(0)
        self.goto_step_spin.setMaximum(100)
        self.goto_step_spin.setValue(1)
        self.goto_step_spin.setToolTip("0 = Restart cycle từ đầu (có delay)\n1-N = Nhảy về step cụ thể")
        self.goto_step_spin.setEnabled(False)
        self.goto_step_spin.setToolTip("Số thứ tự step (bắt đầu từ 1)")
        goto_layout.addWidget(self.goto_step_spin)
        goto_layout.addStretch()
        goto_group.setLayout(goto_layout)
        layout.addWidget(goto_group)
        
        # Add stretch to prevent layout expansion
        layout.addStretch()
        
        # Set content widget to scroll area
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        # Buttons (outside scroll area)
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(10, 5, 10, 10)
        btn_layout.addStretch()
        ok_btn = QPushButton("Lưu")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Hủy")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout)
        
        self.setLayout(main_layout)
    
    def _on_read_data_changed(self, state):
        """Show/hide OCR and Gemini settings when read_data changes."""
        enabled = bool(state)
        self.ocr_group.setVisible(enabled)
        self.gemini_group.setVisible(enabled)
    
    def _on_multiscale_changed(self, state):
        """Show/hide multiscale range settings."""
        self.multiscale_range_widget.setVisible(bool(state))
    
    def _on_ocr_upscale_changed(self, state):
        """Show/hide upscale factor widget."""
        self.ocr_upscale_factor_widget.setVisible(bool(state))
    
    def _on_gemini_changed(self, state):
        """Show/hide Telegram settings when Gemini changes."""
        enabled = bool(state)
        self.telegram_group.setVisible(enabled)
    
    def _on_goto_step_changed(self, state):
        """Enable/disable goto step spin box."""
        self.goto_step_spin.setEnabled(bool(state))
    
    def _on_timeout_goto_changed(self, state):
        """Enable/disable timeout goto step spin box."""
        self.timeout_goto_spin.setEnabled(bool(state))
        # Disable continue_on_timeout if timeout_goto is enabled
        if state:
            self.continue_on_timeout_checkbox.setChecked(False)
            self.continue_on_timeout_checkbox.setEnabled(False)
        else:
            self.continue_on_timeout_checkbox.setEnabled(True)
    
    def _capture_teaching_image(self):
        """Open image capture dialog."""
        parent_dialog = self.parent()
        if not hasattr(parent_dialog, 'target_window_hwnd') or not parent_dialog.target_window_hwnd:
            QMessageBox.warning(self, "Cảnh báo", "Chưa chọn window game ở màn hình chính!")
            return
        
        from .image_capture_dialog import ImageCaptureDialog
        dialog = ImageCaptureDialog(
            parent_dialog.target_window_hwnd,
            parent=self,
            tool_id=getattr(parent_dialog, "tool_id", None),
            hide_click_selection=True,  # IMAGE_DETECT không cần chọn điểm click
            initial_image_path=getattr(self.action, "image_path", None),
            initial_mask_regions=getattr(self.action, "mask_regions", None),
        )
        if dialog.exec():
            result = dialog.get_cropped_image_path()
            
            if len(result) == 9:
                image_path, _, _, corner_x1, corner_y1, corner_x2, corner_y2, window_width, window_height = result
            elif len(result) == 7:
                # Backward compatibility
                image_path, _, _, corner_x1, corner_y1, corner_x2, corner_y2 = result
                window_width, window_height = None, None
            else:
                image_path = result[0] if result else None
                corner_x1, corner_y1, corner_x2, corner_y2 = None, None, None, None
                window_width, window_height = None, None
            
            if image_path:
                self.action.image_path = image_path
                # Save mask regions
                self.action.mask_regions = dialog.get_mask_regions()
                filename = os.path.basename(image_path)
                self.image_path_label.setText(f"Đã chọn: {filename}")
                self._update_image_button_text()
                
                # Save teaching corners
                if corner_x1 is not None:
                    self.action.teaching_corner_x1 = corner_x1
                    self.action.teaching_corner_y1 = corner_y1
                    self.action.teaching_corner_x2 = corner_x2
                    self.action.teaching_corner_y2 = corner_y2
                
                # Save teaching window size
                if window_width is not None and window_height is not None:
                    self.action.teaching_window_width = window_width
                    self.action.teaching_window_height = window_height
    
    def _select_image_file(self):
        """Select image from file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh", "", "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )
        if filepath:
            parent_dialog = self.parent()
            base_dir = os.path.join("images", "teaching")
            try:
                from .image_capture_dialog import ImageCaptureDialog as _ICD
                sub = _ICD._sanitize_tool_folder_name(getattr(parent_dialog, "tool_name", None))
            except Exception:
                sub = ""
            images_dir = os.path.join(base_dir, sub) if sub else base_dir
            os.makedirs(images_dir, exist_ok=True)
            filename = os.path.basename(filepath)
            dest_path = os.path.join(images_dir, filename)
            shutil.copy2(filepath, dest_path)
            
            self.action.image_path = dest_path
            self.image_path_label.setText(f"Đã chọn: {filename}")
            self._update_image_button_text()
    
    def _open_algorithm_testing_dialog(self):
        """Open Multi-Image Algorithm Testing Dialog."""
        try:
            from .multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
            
            dialog = MultiImageAlgorithmTestingDialog(
                self.action,
                parent=self,
                target_window_hwnd=self.target_window_hwnd,
                tool_id=self.tool_id
            )
            
            if dialog.exec():
                # Data already saved to action in dialog
                pass
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể mở dialog:\n{type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_image_button_text(self):
        """Update button text based on whether image exists."""
        if self.action.image_path and os.path.exists(self.action.image_path):
            self.image_btn.setText("Xem/Sửa ảnh Teaching")
        else:
            self.image_btn.setText("Tạo ảnh Teaching")
    
    def _app_state_path(self) -> str:
        try:
            return os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "app_state.json")
        except Exception:
            return os.path.join(os.getcwd(), "app_state.json")
    
    def _load_app_state(self) -> dict:
        p = self._app_state_path()
        try:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f) or {}
        except Exception:
            pass
        return {}
    
    def _save_app_state(self, state: dict):
        p = self._app_state_path()
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def _get_saved_gemini_key(self) -> str:
        from ..logic.dpapi import unprotect_from_b64
        k = str(os.environ.get("GEMINI_API_KEY", "") or "").strip()
        if k:
            return k
        state = self._load_app_state()
        b64 = str(state.get("gemini_api_key_dpapi_b64", "") or "")
        if not b64:
            return ""
        try:
            return unprotect_from_b64(b64)
        except Exception:
            return ""
    
    def _set_saved_gemini_key(self, key: str):
        from ..logic.dpapi import protect_to_b64
        key = str(key or "").strip()
        if not key:
            return
        state = self._load_app_state()
        state["gemini_api_key_dpapi_b64"] = protect_to_b64(key)
        self._save_app_state(state)
        os.environ["GEMINI_API_KEY"] = key
    
    def _gemini_key_status_text(self) -> tuple[str, bool]:
        k = self._get_saved_gemini_key()
        if k:
            return ("Đã có key", True)
        return ("Chưa có key", False)
    
    def _refresh_gemini_key_status(self):
        try:
            txt, ok = self._gemini_key_status_text()
            self.gemini_key_status.setText(txt)
            self.gemini_key_status.setStyleSheet("color:#2ecc71;" if ok else "color:#ff4d4d;")
            self.gemini_key_btn.setText("Cài đặt key" if ok else "Cài key")
        except Exception:
            pass
    
    def _open_gemini_key_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Cài đặt Gemini API key")
        dlg.setFixedWidth(520)
        lay = QVBoxLayout()
        lab = QLabel("Nhập Gemini API key (ẩn khi gõ):")
        lay.addWidget(lab)
        inp = QLineEdit()
        inp.setEchoMode(QLineEdit.EchoMode.Password)
        inp.setText(self._get_saved_gemini_key())
        lay.addWidget(inp)
        row = QHBoxLayout()
        row.addStretch(1)
        ok_btn = QPushButton("Lưu")
        cancel_btn = QPushButton("Hủy")
        row.addWidget(ok_btn)
        row.addWidget(cancel_btn)
        lay.addLayout(row)
        dlg.setLayout(lay)

        def _save():
            k = (inp.text() or "").strip()
            if not k:
                QMessageBox.warning(dlg, "Thiếu key", "Bạn chưa nhập key.")
                return
            self._set_saved_gemini_key(k)
            dlg.accept()

        ok_btn.clicked.connect(_save)
        cancel_btn.clicked.connect(dlg.reject)

        if dlg.exec():
            self._refresh_gemini_key_status()
    
    def _open_prompt_dialog(self):
        """Open dialog to edit Gemini prompt."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Cài đặt Gemini Prompt")
        dlg.setFixedSize(600, 400)
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Nhập prompt cho Gemini (dùng {text} để chèn OCR text):"))
        
        prompt_edit = QTextEdit()
        prompt_edit.setPlainText(getattr(self.action, "prompt", "") or getattr(self.action, "gemini_prompt", "") or "")
        layout.addWidget(prompt_edit)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("Lưu")
        cancel_btn = QPushButton("Hủy")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        dlg.setLayout(layout)
        
        ok_btn.clicked.connect(dlg.accept)
        cancel_btn.clicked.connect(dlg.reject)
        
        if dlg.exec():
            self.action.prompt = prompt_edit.toPlainText()
            self.action.gemini_prompt = prompt_edit.toPlainText()
    
    def _open_telegram_config_dialog(self):
        """Open Telegram configuration dialog."""
        from .telegram_filter_dialog import TelegramFilterDialog
        dlg = TelegramFilterDialog(self.action, self)
        if dlg.exec():
            # Settings are saved directly to action in dialog
            pass
    
    def _add_template_matching_preprocessing_section(self, layout):
        """Add Template Matching Preprocessing section."""
        preprocessing_group = QGroupBox("⚙️ Template Matching Preprocessing")
        preprocessing_layout = QVBoxLayout()
        
        # Algorithm ListView (read-only)
        self.template_algorithms_list = QListWidget()
        self.template_algorithms_list.setMaximumHeight(120)
        self.template_algorithms_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        preprocessing_layout.addWidget(self.template_algorithms_list)
        
        # Configure button
        configure_btn = QPushButton("⚙️ Cấu hình Template Matching Algorithms")
        configure_btn.clicked.connect(self._open_template_matching_config)
        preprocessing_layout.addWidget(configure_btn)
        
        preprocessing_group.setLayout(preprocessing_layout)
        layout.addWidget(preprocessing_group)
    
    def _open_template_matching_config(self):
        """Open Multi-Image Testing Dialog for template matching."""
        from .multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
        
        # Pass current template_matching_algorithms to dialog
        dialog = MultiImageAlgorithmTestingDialog(
            action=self.action,
            parent=self,
            target_window_hwnd=self.target_window_hwnd,
            tool_id=self.tool_id
        )
        
        # Set current algorithms if any
        if hasattr(self.action, 'template_matching_algorithms') and self.action.template_matching_algorithms:
            # Load algorithms into dialog (this would need to be implemented in MultiImageAlgorithmTestingDialog)
            pass
        
        if dialog.exec():
            # Update display after dialog closes
            self._update_template_algorithms_display()
    
    def _update_template_algorithms_display(self):
        """Update template algorithms ListView display."""
        algorithms = getattr(self.action, 'template_matching_algorithms', [])
        update_algorithms_display(self.template_algorithms_list, algorithms)
    
    def _load_settings(self):
        """Load settings from action."""
        # Threshold
        try:
            thr = float(getattr(self.action, "match_threshold", 0.4))
            self.threshold_spin.setValue(max(0.10, min(0.99, thr)))
        except Exception:
            pass
        
        # Multiscale
        try:
            multiscale_enabled = bool(getattr(self.action, "multiscale_enabled", True))
            self.multiscale_checkbox.setChecked(multiscale_enabled)
            self.multiscale_range_widget.setVisible(multiscale_enabled)
        except Exception:
            pass
        
        # Multiscale range
        try:
            self.multiscale_min_spin.setValue(float(getattr(self.action, "multiscale_min", 0.70)))
            self.multiscale_max_spin.setValue(float(getattr(self.action, "multiscale_max", 1.30)))
            self.multiscale_step_spin.setValue(float(getattr(self.action, "multiscale_step", 0.05)))
        except Exception:
            pass
        
        # Timeout
        timeout_value = float(getattr(self.action, 'timeout', 5.0))
        self.timeout_spin.setValue(max(1, int(round(timeout_value * 10))))
        
        check_interval_value = float(getattr(self.action, 'check_interval', 1.0))
        self.check_interval_spin.setValue(max(1, int(round(check_interval_value * 10))))
        
        try:
            self.continue_on_timeout_checkbox.setChecked(bool(getattr(self.action, "continue_on_timeout", False)))
        except Exception:
            pass
        
        # Timeout goto step
        timeout_goto_enabled = bool(getattr(self.action, "timeout_goto_enabled", False))
        self.timeout_goto_checkbox.setChecked(timeout_goto_enabled)
        self.timeout_goto_spin.setEnabled(timeout_goto_enabled)
        idx = int(getattr(self.action, "timeout_goto_step_index", 0) or 0)
        self.timeout_goto_spin.setValue(idx)  # No conversion: 0=restart, 1=step1, 2=step2...
        # Disable continue_on_timeout if timeout_goto is enabled
        if timeout_goto_enabled:
            self.continue_on_timeout_checkbox.setEnabled(False)
        
        # Delay
        delay_in_100ms = int(self.action.delay * 10)
        self.delay_spin.setValue(delay_in_100ms)
        
        # Read data
        read_data = bool(getattr(self.action, "read_data", False))
        self.read_data_checkbox.setChecked(read_data)
        self.ocr_group.setVisible(read_data)
        self.gemini_group.setVisible(read_data)
        
        # OCR settings
        ocr_engine = str(getattr(self.action, "ocr_engine", "auto") or "auto")
        if ocr_engine == "winrt":
            self.ocr_engine_combo.setCurrentIndex(1)
        elif ocr_engine == "tesseract":
            self.ocr_engine_combo.setCurrentIndex(2)
        else:
            self.ocr_engine_combo.setCurrentIndex(0)
        
        self.ocr_bright_on_dark_checkbox.setChecked(bool(getattr(self.action, "ocr_bright_on_dark", False)))
        
        # OCR preprocessing options
        ocr_upscale_enabled = bool(getattr(self.action, "ocr_upscale_enabled", True))
        self.ocr_upscale_checkbox.setChecked(ocr_upscale_enabled)
        self.ocr_upscale_factor_widget.setVisible(ocr_upscale_enabled)
        self.ocr_upscale_factor_spin.setValue(float(getattr(self.action, "ocr_upscale_factor", 2.0) or 2.0))
        self.ocr_enhance_contrast_checkbox.setChecked(bool(getattr(self.action, "ocr_enhance_contrast", True)))
        self.ocr_sharpen_checkbox.setChecked(bool(getattr(self.action, "ocr_sharpen", True)))
        self.ocr_denoise_checkbox.setChecked(bool(getattr(self.action, "ocr_denoise", False)))
        
        # Gemini settings
        gemini_enabled = bool(getattr(self.action, "gemini_enabled", False))
        self.gemini_checkbox.setChecked(gemini_enabled)
        self.telegram_group.setVisible(gemini_enabled)
        
        self._refresh_gemini_key_status()
        
        self.gemini_timeout_spin.setValue(float(getattr(self.action, "gemini_timeout", 10.0) or 10.0))
        
        # Telegram notification
        self.notification_checkbox.setChecked(bool(getattr(self.action, "notification_enabled", False)))
        self.notification_filter_input.setText(str(getattr(self.action, "notification_filter_keywords", "") or ""))
        self.notification_dedup_spin.setValue(int(getattr(self.action, "notification_dedup_minutes", 1) or 1))
        
        # Goto step
        self.goto_step_checkbox.setChecked(bool(getattr(self.action, "goto_step_enabled", False)))
        idx = int(getattr(self.action, "goto_step_index", 0) or 0)
        self.goto_step_spin.setValue(idx)  # No conversion: 0=restart, 1=step1, 2=step2...
        self.goto_step_spin.setEnabled(bool(getattr(self.action, "goto_step_enabled", False)))
        
        # Teaching image
        if self.action.image_path:
            filename = os.path.basename(self.action.image_path)
            self.image_path_label.setText(f"Đã chọn: {filename}")
        self._update_image_button_text()
        
        # Template matching algorithms
        self._update_template_algorithms_display()
    
    def get_settings(self) -> dict:
        """Get settings from dialog.
        
        Returns:
            Dict with all image detect settings
        """
        # OCR engine mapping
        ocr_engine_map = {
            0: "auto",
            1: "winrt",
            2: "tesseract"
        }
        
        return {
            "match_threshold": float(self.threshold_spin.value()),
            "multiscale_enabled": bool(self.multiscale_checkbox.isChecked()),
            "multiscale_min": float(self.multiscale_min_spin.value()),
            "multiscale_max": float(self.multiscale_max_spin.value()),
            "multiscale_step": float(self.multiscale_step_spin.value()),
            "timeout": self.timeout_spin.value() / 10.0,
            "check_interval": self.check_interval_spin.value() / 10.0,
            "continue_on_timeout": bool(self.continue_on_timeout_checkbox.isChecked()),
            "delay": self.delay_spin.value() / 10.0,
            "read_data": bool(self.read_data_checkbox.isChecked()),
            "ocr_engine": ocr_engine_map.get(self.ocr_engine_combo.currentIndex(), "auto"),
            "ocr_bright_on_dark": bool(self.ocr_bright_on_dark_checkbox.isChecked()),
            "ocr_upscale_enabled": bool(self.ocr_upscale_checkbox.isChecked()),
            "ocr_upscale_factor": float(self.ocr_upscale_factor_spin.value()),
            "ocr_enhance_contrast": bool(self.ocr_enhance_contrast_checkbox.isChecked()),
            "ocr_sharpen": bool(self.ocr_sharpen_checkbox.isChecked()),
            "ocr_denoise": bool(self.ocr_denoise_checkbox.isChecked()),
            "gemini_enabled": bool(self.gemini_checkbox.isChecked()),
            "gemini_timeout": float(self.gemini_timeout_spin.value()),
            "notification_enabled": bool(self.notification_checkbox.isChecked()),
            "notification_filter_keywords": str(self.notification_filter_input.text() or "").strip(),
            "notification_dedup_minutes": int(self.notification_dedup_spin.value()),
            "image_path": self.action.image_path,
            "teaching_corner_x1": getattr(self.action, "teaching_corner_x1", None),
            "teaching_corner_y1": getattr(self.action, "teaching_corner_y1", None),
            "teaching_corner_x2": getattr(self.action, "teaching_corner_x2", None),
            "teaching_corner_y2": getattr(self.action, "teaching_corner_y2", None),
            "goto_step_enabled": bool(self.goto_step_checkbox.isChecked()),
            "goto_step_index": int(self.goto_step_spin.value()),  # No conversion: 0=restart, 1=step1, 2=step2...
            "timeout_goto_enabled": bool(self.timeout_goto_checkbox.isChecked()),
            "timeout_goto_step_index": int(self.timeout_goto_spin.value()),  # No conversion: 0=restart, 1=step1, 2=step2...
            "template_matching_algorithms": getattr(self.action, 'template_matching_algorithms', [])
        }
