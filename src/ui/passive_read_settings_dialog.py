"""Passive Read Action Settings Dialog."""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QSpinBox, QCheckBox, QDoubleSpinBox, 
                             QGroupBox, QComboBox, QMessageBox, QLineEdit, QTextEdit, QWidget,
                             QFileDialog, QScrollArea, QListWidget, QAbstractItemView,
                             QTableWidget, QTableWidgetItem)
from PyQt6.QtCore import Qt
from ..logic.action_type import AutoAction
from .algorithm_display_utils import update_algorithms_display
import os
import json
import shutil


class PassiveReadSettingsDialog(QDialog):
    """Dialog for configuring READ_PASSIVE action settings."""
    
    def __init__(self, action: AutoAction, parent=None, target_window_hwnd=None, tool_id: str = None):
        super().__init__(parent)
        self.action = action
        self.target_window_hwnd = target_window_hwnd
        self.tool_id = tool_id
        self.setWindowTitle("Cài đặt Passive Read Action")
        self.setFixedSize(720, 650)
        self._init_ui()
        self._load_settings()
    
    def _init_ui(self):
        """Initialize UI components with 2-column layout for mode 1."""
        # Main layout for dialog
        dialog_layout = QVBoxLayout()
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # Content widget inside scroll area
        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)
        
        # Mode selection dropdown (at top)
        mode_group = QGroupBox("🔄 Chế độ hoạt động")
        mode_layout = QVBoxLayout()
        
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Chế độ:"))
        self.passive_mode_combo = QComboBox()
        self.passive_mode_combo.addItems(["Đọc dữ liệu", "Phát hiện hình ảnh", "Event Tracking", "Special Event Tracking"])  # 4 modes
        self.passive_mode_combo.setCurrentIndex(1)  # Default: Phát hiện hình ảnh
        self.passive_mode_combo.currentIndexChanged.connect(self._on_passive_mode_changed)
        mode_row.addWidget(self.passive_mode_combo)
        mode_row.addStretch()
        mode_layout.addLayout(mode_row)
        
        mode_group.setLayout(mode_layout)
        main_layout.addWidget(mode_group)
        
        # === MODE 2: Detect image settings (single column, compact) ===
        self.detect_group = QGroupBox("⏱️ Cài đặt phát hiện hình ảnh")
        detect_layout = QVBoxLayout()
        
        timeout_row = QHBoxLayout()
        timeout_row.addWidget(QLabel("Timeout (giây):"))
        self.passive_detect_timeout_spin = QDoubleSpinBox()
        self.passive_detect_timeout_spin.setMinimum(1.0)
        self.passive_detect_timeout_spin.setMaximum(3600.0)
        self.passive_detect_timeout_spin.setSingleStep(1.0)
        self.passive_detect_timeout_spin.setDecimals(1)
        self.passive_detect_timeout_spin.setValue(30.0)
        timeout_row.addWidget(self.passive_detect_timeout_spin)
        timeout_row.addStretch()
        detect_layout.addLayout(timeout_row)
        
        threshold_row = QHBoxLayout()
        threshold_row.addWidget(QLabel("Ngưỡng nhận diện:"))
        self.passive_detect_threshold_spin = QDoubleSpinBox()
        self.passive_detect_threshold_spin.setMinimum(0.1)
        self.passive_detect_threshold_spin.setMaximum(1.0)
        self.passive_detect_threshold_spin.setSingleStep(0.05)
        self.passive_detect_threshold_spin.setDecimals(2)
        self.passive_detect_threshold_spin.setValue(0.4)
        threshold_row.addWidget(self.passive_detect_threshold_spin)
        threshold_row.addStretch()
        detect_layout.addLayout(threshold_row)

        self.continue_on_timeout_checkbox = QCheckBox("Timeout → làm tiếp bước sau")
        detect_layout.addWidget(self.continue_on_timeout_checkbox)
        
        self.detect_group.setLayout(detect_layout)
        main_layout.addWidget(self.detect_group)
        
        # === MODE 1: Two-column layout container ===
        self.two_column_widget = QWidget()
        two_column_layout = QHBoxLayout()
        two_column_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left column: Passive Settings + OCR
        left_column = QVBoxLayout()
        
        # Passive settings group
        self.passive_group = QGroupBox("⚙️ Passive Settings")
        passive_layout = QVBoxLayout()
        
        sample_row = QHBoxLayout()
        sample_row.addWidget(QLabel("Chu kỳ xử lý:"))
        self.passive_sample_spin = QSpinBox()
        self.passive_sample_spin.setMinimum(1)
        self.passive_sample_spin.setMaximum(999)
        self.passive_sample_spin.setValue(1)
        sample_row.addWidget(self.passive_sample_spin)
        sample_row.addStretch()
        passive_layout.addLayout(sample_row)
        
        self.passive_only_new_checkbox = QCheckBox("Chỉ xử lý frame mới")
        self.passive_only_new_checkbox.setChecked(True)
        passive_layout.addWidget(self.passive_only_new_checkbox)
        
        self.passive_cancel_old_checkbox = QCheckBox("Cancel xử lý ảnh cũ")
        self.passive_cancel_old_checkbox.setChecked(False)
        passive_layout.addWidget(self.passive_cancel_old_checkbox)
        
        passive_layout.addWidget(QLabel("Từ khóa check:"))
        self.passive_keywords_edit = QLineEdit()
        self.passive_keywords_edit.setPlaceholderText("warning,error,success")
        passive_layout.addWidget(self.passive_keywords_edit)
        
        self.passive_group.setLayout(passive_layout)
        left_column.addWidget(self.passive_group)
        
        # OCR settings
        self.ocr_group = QGroupBox("📝 Cài đặt OCR")
        ocr_layout = QVBoxLayout()
        
        ocr_engine_row = QHBoxLayout()
        ocr_engine_row.addWidget(QLabel("Engine:"))
        self.ocr_engine_combo = QComboBox()
        self.ocr_engine_combo.addItems(["Auto", "WinRT", "Tesseract", "EasyOCR", "VietOCR"])
        ocr_engine_row.addWidget(self.ocr_engine_combo)
        ocr_engine_row.addStretch()
        ocr_layout.addLayout(ocr_engine_row)
        
        self.ocr_bright_on_dark_checkbox = QCheckBox("Chữ sáng/nền tối")
        ocr_layout.addWidget(self.ocr_bright_on_dark_checkbox)
        
        self.ocr_upscale_checkbox = QCheckBox("Phóng to ảnh")
        self.ocr_upscale_checkbox.setChecked(True)
        self.ocr_upscale_checkbox.stateChanged.connect(self._on_ocr_upscale_changed)
        ocr_layout.addWidget(self.ocr_upscale_checkbox)
        
        upscale_factor_layout = QHBoxLayout()
        upscale_factor_layout.addWidget(QLabel("Hệ số:"))
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
        ocr_layout.addWidget(self.ocr_upscale_factor_widget)
        
        self.ocr_enhance_contrast_checkbox = QCheckBox("Tăng contrast")
        self.ocr_enhance_contrast_checkbox.setChecked(True)
        ocr_layout.addWidget(self.ocr_enhance_contrast_checkbox)
        
        self.ocr_sharpen_checkbox = QCheckBox("Làm sắc nét")
        self.ocr_sharpen_checkbox.setChecked(True)
        ocr_layout.addWidget(self.ocr_sharpen_checkbox)
        
        self.ocr_denoise_checkbox = QCheckBox("Khử nhiễu")
        self.ocr_denoise_checkbox.setChecked(False)
        ocr_layout.addWidget(self.ocr_denoise_checkbox)
        
        preprocessing_row = QHBoxLayout()
        self.preprocessing_load_btn = QPushButton("📥 Load từ Lab")
        self.preprocessing_load_btn.clicked.connect(self._load_preprocessing_config)
        preprocessing_row.addWidget(self.preprocessing_load_btn)
        self.preprocessing_status_label = QLabel("")
        preprocessing_row.addWidget(self.preprocessing_status_label)
        preprocessing_row.addStretch()
        ocr_layout.addLayout(preprocessing_row)
        
        self.ocr_group.setLayout(ocr_layout)
        left_column.addWidget(self.ocr_group)
        
        # OCR Preprocessing section (only visible when mode = "Đọc dữ liệu")
        self._add_ocr_preprocessing_section(left_column)
        
        left_column.addStretch()
        
        two_column_layout.addLayout(left_column)
        
        # Right column: Gemini + Telegram
        right_column = QVBoxLayout()
        
        # Gemini settings
        self.gemini_group = QGroupBox("🤖 Cài đặt Gemini")
        gemini_layout = QVBoxLayout()
        
        self.gemini_checkbox = QCheckBox("Dùng Gemini chiết xuất dữ liệu")
        self.gemini_checkbox.stateChanged.connect(self._on_gemini_changed)
        gemini_layout.addWidget(self.gemini_checkbox)
        
        key_row = QHBoxLayout()
        self.gemini_key_status = QLabel("Chưa có key")
        self.gemini_key_status.setStyleSheet("color:#ff4d4d;")
        key_row.addWidget(self.gemini_key_status)
        self.gemini_key_btn = QPushButton("Cài key")
        self.gemini_key_btn.clicked.connect(self._open_gemini_key_dialog)
        key_row.addWidget(self.gemini_key_btn)
        key_row.addStretch()
        gemini_layout.addLayout(key_row)
        
        timeout_row2 = QHBoxLayout()
        timeout_row2.addWidget(QLabel("Timeout (s):"))
        self.gemini_timeout_spin = QDoubleSpinBox()
        self.gemini_timeout_spin.setMinimum(1.0)
        self.gemini_timeout_spin.setMaximum(120.0)
        self.gemini_timeout_spin.setSingleStep(1.0)
        self.gemini_timeout_spin.setDecimals(0)
        self.gemini_timeout_spin.setValue(10.0)
        timeout_row2.addWidget(self.gemini_timeout_spin)
        timeout_row2.addStretch()
        gemini_layout.addLayout(timeout_row2)
        
        self.gemini_prompt_btn = QPushButton("Cài đặt prompt")
        self.gemini_prompt_btn.clicked.connect(self._open_prompt_dialog)
        gemini_layout.addWidget(self.gemini_prompt_btn)
        
        self.gemini_group.setLayout(gemini_layout)
        right_column.addWidget(self.gemini_group)
        
        # Telegram notification
        self.telegram_group = QGroupBox("📱 Thông báo Telegram")
        telegram_layout = QVBoxLayout()
        
        self.notification_checkbox = QCheckBox("Gửi kết quả đến Telegram")
        telegram_layout.addWidget(self.notification_checkbox)
        
        self.telegram_config_btn = QPushButton("⚙️ Cài đặt Telegram")
        self.telegram_config_btn.clicked.connect(self._open_telegram_config_dialog)
        telegram_layout.addWidget(self.telegram_config_btn)
        
        telegram_layout.addWidget(QLabel("Từ khóa bắt buộc:"))
        self.notification_filter_input = QLineEdit()
        self.notification_filter_input.setPlaceholderText("success, done")
        telegram_layout.addWidget(self.notification_filter_input)
        
        dedup_layout = QHBoxLayout()
        dedup_layout.addWidget(QLabel("Dedup (phút):"))
        self.notification_dedup_spin = QSpinBox()
        self.notification_dedup_spin.setMinimum(1)
        self.notification_dedup_spin.setMaximum(1440)
        self.notification_dedup_spin.setValue(1)
        dedup_layout.addWidget(self.notification_dedup_spin)
        dedup_layout.addStretch()
        telegram_layout.addLayout(dedup_layout)
        
        self.telegram_group.setLayout(telegram_layout)
        self.telegram_group.setVisible(False)
        right_column.addWidget(self.telegram_group)
        right_column.addStretch()
        
        two_column_layout.addLayout(right_column)
        self.two_column_widget.setLayout(two_column_layout)
        main_layout.addWidget(self.two_column_widget)
        
        # === COMMON SECTIONS (both modes) ===
        
        # Fixed ROI group
        self.roi_group = QGroupBox("📍 Vùng đọc cố định (Fixed ROI)")
        roi_layout = QVBoxLayout()
        
        self.use_fixed_roi_checkbox = QCheckBox("Sử dụng vùng đọc cố định")
        self.use_fixed_roi_checkbox.stateChanged.connect(self._on_fixed_roi_changed)
        roi_layout.addWidget(self.use_fixed_roi_checkbox)
        
        roi_coords_layout = QHBoxLayout()
        roi_coords_layout.addWidget(QLabel("X:"))
        self.roi_x_spin = QSpinBox()
        self.roi_x_spin.setMinimum(0)
        self.roi_x_spin.setMaximum(10000)
        roi_coords_layout.addWidget(self.roi_x_spin)
        
        roi_coords_layout.addWidget(QLabel("Y:"))
        self.roi_y_spin = QSpinBox()
        self.roi_y_spin.setMinimum(0)
        self.roi_y_spin.setMaximum(10000)
        roi_coords_layout.addWidget(self.roi_y_spin)
        
        roi_coords_layout.addWidget(QLabel("W:"))
        self.roi_w_spin = QSpinBox()
        self.roi_w_spin.setMinimum(1)
        self.roi_w_spin.setMaximum(10000)
        self.roi_w_spin.setValue(200)
        roi_coords_layout.addWidget(self.roi_w_spin)
        
        roi_coords_layout.addWidget(QLabel("H:"))
        self.roi_h_spin = QSpinBox()
        self.roi_h_spin.setMinimum(1)
        self.roi_h_spin.setMaximum(10000)
        self.roi_h_spin.setValue(100)
        roi_coords_layout.addWidget(self.roi_h_spin)
        roi_coords_layout.addStretch()
        
        self.roi_coords_widget = QWidget()
        self.roi_coords_widget.setLayout(roi_coords_layout)
        self.roi_coords_widget.setVisible(False)
        roi_layout.addWidget(self.roi_coords_widget)
        
        self.roi_group.setLayout(roi_layout)
        main_layout.addWidget(self.roi_group)
        
        # Teaching image
        self.teaching_group = QGroupBox("🖼️ Ảnh Teaching")
        teaching_group = self.teaching_group
        teaching_layout = QVBoxLayout()
        
        self.image_path_label = QLabel("Chưa chọn ảnh")
        self.image_path_label.setWordWrap(True)
        teaching_layout.addWidget(self.image_path_label)
        
        btn_row = QHBoxLayout()
        self.image_btn = QPushButton("Tạo ảnh Teaching")
        self.image_btn.clicked.connect(self._capture_teaching_image)
        btn_row.addWidget(self.image_btn)
        
        self.image_file_btn = QPushButton("Chọn file ảnh...")
        self.image_file_btn.clicked.connect(self._select_image_file)
        btn_row.addWidget(self.image_file_btn)
        btn_row.addStretch()
        teaching_layout.addLayout(btn_row)
        
        # Test Algorithms button
        test_algo_btn = QPushButton("🧪 Test Algorithms")
        test_algo_btn.clicked.connect(self._open_algorithm_testing_dialog)
        teaching_layout.addWidget(test_algo_btn)
        
        # Selected Algorithms list (COMMON - for all modes)
        teaching_layout.addWidget(QLabel("Selected Algorithms:"))
        self.algorithms_list = QListWidget()
        self.algorithms_list.setMaximumHeight(100)
        self.algorithms_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        teaching_layout.addWidget(self.algorithms_list)
        
        teaching_group.setLayout(teaching_layout)
        main_layout.addWidget(teaching_group)
        
        # Goto step
        self.goto_group = QGroupBox("🔄 Nhảy về step")
        goto_group = self.goto_group
        goto_layout = QHBoxLayout()
        self.goto_step_checkbox = QCheckBox("Khi thành công, nhảy về step:")
        self.goto_step_checkbox.stateChanged.connect(self._on_goto_step_changed)
        goto_layout.addWidget(self.goto_step_checkbox)
        self.goto_step_spin = QSpinBox()
        self.goto_step_spin.setMinimum(0)
        self.goto_step_spin.setMaximum(100)
        self.goto_step_spin.setValue(1)
        self.goto_step_spin.setToolTip("0 = Restart cycle từ đầu (có delay)\n1-N = Nhảy về step cụ thể")
        self.goto_step_spin.setEnabled(False)
        goto_layout.addWidget(self.goto_step_spin)
        goto_layout.addStretch()
        goto_group.setLayout(goto_layout)
        main_layout.addWidget(goto_group)
        
        # Event Tracking Settings
        self._add_event_tracking_section(main_layout)
        
        # Special Event Tracking Settings
        self._add_special_event_tracking_section(main_layout)
        
        # Add stretch to prevent layout expansion
        main_layout.addStretch()
        
        # Set content widget to scroll area
        scroll_area.setWidget(content_widget)
        dialog_layout.addWidget(scroll_area)
        
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
        dialog_layout.addLayout(btn_layout)
        
        self.setLayout(dialog_layout)
    
    def _on_fixed_roi_changed(self, state):
        """Show/hide ROI coordinates when Fixed ROI changes."""
        enabled = bool(state)
        self.roi_coords_widget.setVisible(enabled)
    
    def _on_passive_mode_changed(self, index: int):
        """Show/hide groups based on passive mode selection.
        
        Args:
            index: 0 = Đọc dữ liệu (mode 1), 1 = Phát hiện hình ảnh (mode 2), 2 = Event Tracking (mode 3), 3 = Special Event Tracking (mode 4)
        """
        is_read_data = (index == 0)
        is_detect_image = (index == 1)
        is_event_tracking = (index == 2)
        is_special_event_tracking = (index == 3)
        
        # Mode 1 (Đọc dữ liệu): Show two-column layout with passive/OCR/Gemini/Telegram
        self.two_column_widget.setVisible(is_read_data)
        
        # OCR Preprocessing section only visible in mode 1 (Đọc dữ liệu)
        if hasattr(self, 'ocr_preprocessing_group'):
            self.ocr_preprocessing_group.setVisible(is_read_data)
            if is_read_data:
                self._update_ocr_algorithms_display()
        
        # Telegram only visible if Gemini enabled AND mode 1
        if is_read_data:
            self.telegram_group.setVisible(self.gemini_checkbox.isChecked())
        
        # Mode 2 (Phát hiện hình ảnh): Show detect settings only
        self.detect_group.setVisible(is_detect_image)
        
        # Mode 3 (Event Tracking): Show event tracking group only
        if hasattr(self, 'event_tracking_group'):
            self.event_tracking_group.setVisible(is_event_tracking)
        
        # Mode 4 (Special Event Tracking): Show special event tracking group only
        if hasattr(self, 'special_event_tracking_group'):
            self.special_event_tracking_group.setVisible(is_special_event_tracking)

        # Ẩn các section không liên quan khi Special Event Tracking
        is_not_special = not is_special_event_tracking
        self.roi_group.setVisible(is_not_special)
        if hasattr(self, 'teaching_group'):
            self.teaching_group.setVisible(is_not_special)
        if hasattr(self, 'goto_group'):
            self.goto_group.setVisible(is_not_special and not is_event_tracking)
    
    def _on_ocr_upscale_changed(self, state):
        """Show/hide upscale factor widget."""
        self.ocr_upscale_factor_widget.setVisible(bool(state))
    
    def _on_gemini_changed(self, state):
        """Show/hide Telegram settings when Gemini changes."""
        enabled = bool(state)
        self.telegram_group.setVisible(enabled)
    
    def _load_preprocessing_config(self):
        """Load preprocessing config from preprocessing_config.json."""
        config_path = os.path.join(os.path.dirname(__file__), "..", "preprocessing_config.json")
        if not os.path.exists(config_path):
            QMessageBox.warning(self, "Lỗi", "Chưa có cấu hình từ Lab Hiệu chỉnh.\nHãy vào tab 'Hiệu chỉnh', test thuật toán và nhấn 'Lưu cấu hình cho OCR'.")
            return
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.action.preprocessing_config = config
            algo_name = config.get("algorithm_name", config.get("algorithm", ""))
            self.preprocessing_status_label.setText(f"✓ {algo_name}")
            self.preprocessing_status_label.setStyleSheet("color: green;")
            QMessageBox.information(self, "Thành công", f"Đã load cấu hình:\n{algo_name}\n\nOCR sẽ tự động áp dụng preprocessing này.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể load cấu hình: {e}")
    
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
    
    def _add_ocr_preprocessing_section(self, left_column):
        """Add OCR Preprocessing section to left column."""
        self.ocr_preprocessing_group = QGroupBox("⚙️ OCR Preprocessing")
        ocr_preprocessing_layout = QVBoxLayout()
        
        # Algorithm ListView (read-only)
        self.ocr_algorithms_list = QListWidget()
        self.ocr_algorithms_list.setMaximumHeight(120)
        self.ocr_algorithms_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        ocr_preprocessing_layout.addWidget(self.ocr_algorithms_list)
        
        # Configure button
        configure_btn = QPushButton("⚙️ Cấu hình OCR Algorithms")
        configure_btn.clicked.connect(self._open_ocr_config)
        ocr_preprocessing_layout.addWidget(configure_btn)
        
        self.ocr_preprocessing_group.setLayout(ocr_preprocessing_layout)
        left_column.addWidget(self.ocr_preprocessing_group)
        
        # Initially hidden, will be shown when mode = "Đọc dữ liệu"
        self.ocr_preprocessing_group.setVisible(False)
    
    def _open_ocr_config(self):
        """Open Multi-Image Testing Dialog for OCR mode."""
        from .multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
        
        # Pass current ocr_algorithms to dialog
        dialog = MultiImageAlgorithmTestingDialog(
            action=self.action,
            parent=self,
            target_window_hwnd=self.target_window_hwnd,
            tool_id=self.tool_id,
            algorithm_field="ocr_algorithms"
        )
        
        # Set current algorithms if any
        if hasattr(self.action, 'ocr_algorithms') and self.action.ocr_algorithms:
            # Load algorithms into dialog (this would need to be implemented in MultiImageAlgorithmTestingDialog)
            pass
        
        if dialog.exec():
            # Update display after dialog closes
            self._update_ocr_algorithms_display()
            self._update_algorithms_display()  # Also update common list
    
    def _update_ocr_algorithms_display(self):
        """Update OCR algorithms ListView display."""
        algorithms = getattr(self.action, 'ocr_algorithms', [])
        update_algorithms_display(self.ocr_algorithms_list, algorithms)
    
    def _add_event_tracking_section(self, layout: QVBoxLayout):
        """Add Event Tracking Settings section to layout.
        
        Args:
            layout: Parent layout to add section to
        """
        self.event_tracking_group = QGroupBox("🔔 Event Tracking")
        event_layout = QVBoxLayout()
        
        # OCR Engine selection for event tracking
        engine_row = QHBoxLayout()
        engine_row.addWidget(QLabel("OCR Engine:"))
        self.event_ocr_engine_combo = QComboBox()
        self.event_ocr_engine_combo.addItems(["Auto", "WinRT", "Tesseract", "EasyOCR", "VietOCR"])
        engine_row.addWidget(self.event_ocr_engine_combo)
        engine_row.addStretch()
        event_layout.addLayout(engine_row)
        
        # ROI will be taken from Teaching image section (teaching_corner_x1, y1, x2, y2)
        
        # OCR Pattern
        event_layout.addWidget(QLabel("OCR Pattern:"))
        self.event_ocr_pattern_edit = QLineEdit()
        self.event_ocr_pattern_edit.setPlaceholderText("{event_name} sẽ bắt đầu sau {minutes} phút")
        event_layout.addWidget(self.event_ocr_pattern_edit)
        event_hint = QLabel("Match được pattern thì action này kết thúc ngay và tool chuyển sang action tiếp theo.")
        event_hint.setStyleSheet("color: gray; font-size: 11px;")
        event_hint.setWordWrap(True)
        event_layout.addWidget(event_hint)
        
        # Match Threshold
        threshold_row = QHBoxLayout()
        threshold_row.addWidget(QLabel("Match Threshold:"))
        self.event_match_threshold_spin = QDoubleSpinBox()
        self.event_match_threshold_spin.setMinimum(0.0)
        self.event_match_threshold_spin.setMaximum(100.0)
        self.event_match_threshold_spin.setValue(100.0)
        self.event_match_threshold_spin.setSuffix(" %")
        self.event_match_threshold_spin.setDecimals(1)
        threshold_row.addWidget(self.event_match_threshold_spin)
        threshold_row.addStretch()
        event_layout.addLayout(threshold_row)

        timeout_row = QHBoxLayout()
        timeout_row.addWidget(QLabel("Reset timeout:"))
        self.event_reappear_timeout_spin = QSpinBox()
        self.event_reappear_timeout_spin.setMinimum(1)
        self.event_reappear_timeout_spin.setMaximum(1440)
        self.event_reappear_timeout_spin.setValue(15)
        self.event_reappear_timeout_spin.setSuffix(" phút")
        timeout_row.addWidget(self.event_reappear_timeout_spin)
        timeout_row.addStretch()
        event_layout.addLayout(timeout_row)
        
        self.event_tracking_group.setLayout(event_layout)
        self.event_tracking_group.setVisible(False)  # Initially hidden, shown when mode = Event Tracking
        layout.addWidget(self.event_tracking_group)
    
    def _add_special_event_tracking_section(self, layout: QVBoxLayout):
        """Add Special Event Tracking Settings section to layout.
        
        Args:
            layout: Parent layout to add section to
        """
        self.special_event_tracking_group = QGroupBox("Special Events")
        event_layout = QVBoxLayout()
        
        # Imperial Guardian checkbox
        self.imperial_guardian_checkbox = QCheckBox("Imperial Guardian")
        self.imperial_guardian_checkbox.stateChanged.connect(self._on_imperial_guardian_changed)
        event_layout.addWidget(self.imperial_guardian_checkbox)
        
        # Imperial Guardian settings (collapsible)
        self.imperial_guardian_widget = QWidget()
        imperial_layout = QVBoxLayout()
        
        # Delay setting
        delay_row = QHBoxLayout()
        delay_row.addWidget(QLabel("No-player alert delay (minutes):"))
        self.imperial_guardian_delay_spin = QSpinBox()
        self.imperial_guardian_delay_spin.setMinimum(1)
        self.imperial_guardian_delay_spin.setMaximum(120)
        self.imperial_guardian_delay_spin.setValue(10)
        delay_row.addWidget(self.imperial_guardian_delay_spin)
        delay_row.addStretch()
        imperial_layout.addLayout(delay_row)

        # OCR Engine selection
        ocr_engine_row = QHBoxLayout()
        ocr_engine_row.addWidget(QLabel("OCR Engine:"))
        self.imperial_guardian_ocr_engine_combo = QComboBox()
        self.imperial_guardian_ocr_engine_combo.addItems(["Auto", "WinRT", "Tesseract", "EasyOCR", "VietOCR"])
        ocr_engine_row.addWidget(self.imperial_guardian_ocr_engine_combo)
        ocr_engine_row.addStretch()
        imperial_layout.addLayout(ocr_engine_row)

        # Match threshold
        threshold_row = QHBoxLayout()
        threshold_row.addWidget(QLabel("Match threshold:"))
        self.imperial_guardian_threshold_spin = QSpinBox()
        self.imperial_guardian_threshold_spin.setRange(0, 100)
        self.imperial_guardian_threshold_spin.setValue(70)
        self.imperial_guardian_threshold_spin.setSuffix("%")
        threshold_row.addWidget(self.imperial_guardian_threshold_spin)
        threshold_row.addStretch()
        imperial_layout.addLayout(threshold_row)

        # Teaching image ROI
        teaching_row = QHBoxLayout()
        teaching_row.addWidget(QLabel("Teaching image ROI:"))
        self.imperial_guardian_image_btn = QPushButton("Select Teaching Image")
        self.imperial_guardian_image_btn.clicked.connect(self._select_imperial_guardian_image)
        teaching_row.addWidget(self.imperial_guardian_image_btn)
        teaching_row.addStretch()
        imperial_layout.addLayout(teaching_row)
        
        # ROI coordinates display
        roi_display_row = QHBoxLayout()
        roi_display_row.addWidget(QLabel("ROI:"))
        self.imperial_guardian_roi_label = QLabel("Not configured")
        self.imperial_guardian_roi_label.setStyleSheet("color: gray;")
        roi_display_row.addWidget(self.imperial_guardian_roi_label)
        roi_display_row.addStretch()
        imperial_layout.addLayout(roi_display_row)

        # Test Algorithms button
        test_algo_btn = QPushButton("Test Algorithms")
        test_algo_btn.clicked.connect(self._open_imperial_guardian_algorithm_testing)
        imperial_layout.addWidget(test_algo_btn)

        # Selected Algorithms list (read-only)
        imperial_layout.addWidget(QLabel("Selected Algorithms:"))
        self.imperial_guardian_algorithms_list = QListWidget()
        self.imperial_guardian_algorithms_list.setMaximumHeight(80)
        self.imperial_guardian_algorithms_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        imperial_layout.addWidget(self.imperial_guardian_algorithms_list)
        
        self.imperial_guardian_widget.setLayout(imperial_layout)
        self.imperial_guardian_widget.setVisible(False)  # Initially collapsed
        event_layout.addWidget(self.imperial_guardian_widget)

        # Golden Invasion
        self.gi_checkbox = QCheckBox("Golden Invasion")
        self.gi_checkbox.stateChanged.connect(self._on_gi_checkbox_changed)
        event_layout.addWidget(self.gi_checkbox)

        self.gi_settings_widget = QWidget()
        gi_layout = QVBoxLayout(self.gi_settings_widget)

        from PyQt6.QtWidgets import QRadioButton
        time_group = QGroupBox("Server time")
        time_layout = QHBoxLayout()
        self.gi_time_0040 = QRadioButton("00:40")
        self.gi_time_0130 = QRadioButton("01:30")
        self.gi_time_0130.setChecked(True)
        time_layout.addWidget(self.gi_time_0040)
        time_layout.addWidget(self.gi_time_0130)
        time_group.setLayout(time_layout)
        gi_layout.addWidget(time_group)

        channel_group = QGroupBox("── Vùng 1: Channel ──")
        channel_layout = QVBoxLayout()
        self.gi_channel_roi_label = QLabel("ROI: chưa chọn")
        self.gi_channel_image_btn = QPushButton("Select Channel ROI")
        self.gi_channel_image_btn.clicked.connect(self._select_gi_channel_image)
        self.gi_channel_ocr_combo = QComboBox()
        self.gi_channel_ocr_combo.addItems(["auto", "winrt", "tesseract", "easyocr", "vietocr"])
        self.gi_channel_test_algo_btn = QPushButton("🧪 Test Algorithms - Channel")
        self.gi_channel_test_algo_btn.clicked.connect(self._open_gi_channel_algorithm_testing)
        self.gi_channel_algorithms_list = QListWidget()
        self.gi_channel_algorithms_list.setMaximumHeight(80)
        self.gi_channel_algorithms_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        channel_layout.addWidget(self.gi_channel_roi_label)
        channel_layout.addWidget(self.gi_channel_image_btn)
        channel_layout.addWidget(QLabel("OCR Engine:"))
        channel_layout.addWidget(self.gi_channel_ocr_combo)
        channel_layout.addWidget(self.gi_channel_test_algo_btn)
        channel_layout.addWidget(QLabel("Selected Algorithms:"))
        channel_layout.addWidget(self.gi_channel_algorithms_list)
        channel_group.setLayout(channel_layout)
        gi_layout.addWidget(channel_group)

        notify_group = QGroupBox("── Vùng 2: Thông báo ──")
        notify_layout = QVBoxLayout()
        self.gi_notify_roi_label = QLabel("ROI: chưa chọn")
        self.gi_notify_image_btn = QPushButton("Select Notify ROI")
        self.gi_notify_image_btn.clicked.connect(self._select_gi_notify_image)
        self.gi_notify_ocr_combo = QComboBox()
        self.gi_notify_ocr_combo.addItems(["auto", "winrt", "tesseract", "easyocr", "vietocr"])
        self.gi_notify_test_algo_btn = QPushButton("🧪 Test Algorithms - Thông báo")
        self.gi_notify_test_algo_btn.clicked.connect(self._open_gi_notify_algorithm_testing)
        self.gi_notify_algorithms_list = QListWidget()
        self.gi_notify_algorithms_list.setMaximumHeight(80)
        self.gi_notify_algorithms_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        notify_layout.addWidget(self.gi_notify_roi_label)
        notify_layout.addWidget(self.gi_notify_image_btn)
        notify_layout.addWidget(QLabel("OCR Engine:"))
        notify_layout.addWidget(self.gi_notify_ocr_combo)
        notify_layout.addWidget(self.gi_notify_test_algo_btn)
        notify_layout.addWidget(QLabel("Selected Algorithms:"))
        notify_layout.addWidget(self.gi_notify_algorithms_list)
        notify_group.setLayout(notify_layout)
        gi_layout.addWidget(notify_group)

        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Match threshold:"))
        self.gi_threshold_spin = QSpinBox()
        self.gi_threshold_spin.setRange(0, 100)
        self.gi_threshold_spin.setValue(70)
        self.gi_threshold_spin.setSuffix("%")
        threshold_layout.addWidget(self.gi_threshold_spin)
        threshold_layout.addStretch()
        gi_layout.addLayout(threshold_layout)

        self.gi_settings_widget.setVisible(False)
        event_layout.addWidget(self.gi_settings_widget)
        self.gi_checkbox.setVisible(False)

        # Monster Invasion
        self.mi_checkbox = QCheckBox("Monster Invasion")
        self.mi_checkbox.stateChanged.connect(self._on_mi_checkbox_changed)
        event_layout.addWidget(self.mi_checkbox)

        self.mi_settings_widget = QWidget()
        mi_layout = QVBoxLayout(self.mi_settings_widget)

        sub_event_group = QGroupBox("Sub-events")
        sub_event_layout = QVBoxLayout(sub_event_group)
        self.mi_gi_checkbox = QCheckBox("Golden Invasion")
        self.mi_ww_checkbox = QCheckBox("White Wizard + Red Dragon")
        sub_event_layout.addWidget(self.mi_gi_checkbox)
        sub_event_layout.addWidget(self.mi_ww_checkbox)
        mi_layout.addWidget(sub_event_group)

        from PyQt6.QtWidgets import QRadioButton
        mi_time_group = QGroupBox("Golden Invasion start time")
        mi_time_layout = QHBoxLayout(mi_time_group)
        self.mi_gi_time_0040 = QRadioButton("00:40")
        self.mi_gi_time_0130 = QRadioButton("01:30")
        self.mi_gi_time_0130.setChecked(True)
        mi_time_layout.addWidget(self.mi_gi_time_0040)
        mi_time_layout.addWidget(self.mi_gi_time_0130)
        mi_time_layout.addStretch()
        mi_layout.addWidget(mi_time_group)

        mi_channel_group = QGroupBox("Channel ROI")
        mi_channel_layout = QVBoxLayout(mi_channel_group)
        self.mi_channel_roi_label = QLabel("ROI: chưa chọn")
        self.mi_channel_image_btn = QPushButton("Select Channel ROI")
        self.mi_channel_image_btn.clicked.connect(self._select_mi_channel_image)
        self.mi_channel_ocr_combo = QComboBox()
        self.mi_channel_ocr_combo.addItems(["auto", "winrt", "tesseract", "easyocr", "vietocr"])
        self.mi_channel_test_algo_btn = QPushButton("🧪 Test Algorithms - Channel")
        self.mi_channel_test_algo_btn.clicked.connect(self._open_mi_channel_algorithm_testing)
        self.mi_channel_algorithms_list = QListWidget()
        self.mi_channel_algorithms_list.setMaximumHeight(80)
        self.mi_channel_algorithms_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        mi_channel_layout.addWidget(self.mi_channel_roi_label)
        mi_channel_layout.addWidget(self.mi_channel_image_btn)
        mi_channel_layout.addWidget(QLabel("OCR Engine:"))
        mi_channel_layout.addWidget(self.mi_channel_ocr_combo)
        mi_channel_layout.addWidget(self.mi_channel_test_algo_btn)
        mi_channel_layout.addWidget(QLabel("Algorithms:"))
        mi_channel_layout.addWidget(self.mi_channel_algorithms_list)
        mi_layout.addWidget(mi_channel_group)

        mi_notify_group = QGroupBox("Notify ROI")
        mi_notify_layout = QVBoxLayout(mi_notify_group)
        self.mi_notify_roi_label = QLabel("ROI: chưa chọn")
        self.mi_notify_image_btn = QPushButton("Select Notify ROI")
        self.mi_notify_image_btn.clicked.connect(self._select_mi_notify_image)
        self.mi_notify_ocr_combo = QComboBox()
        self.mi_notify_ocr_combo.addItems(["auto", "winrt", "tesseract", "easyocr", "vietocr"])
        self.mi_notify_test_algo_btn = QPushButton("🧪 Test Algorithms - Thông báo")
        self.mi_notify_test_algo_btn.clicked.connect(self._open_mi_notify_algorithm_testing)
        self.mi_notify_algorithms_list = QListWidget()
        self.mi_notify_algorithms_list.setMaximumHeight(80)
        self.mi_notify_algorithms_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        mi_notify_layout.addWidget(self.mi_notify_roi_label)
        mi_notify_layout.addWidget(self.mi_notify_image_btn)
        mi_notify_layout.addWidget(QLabel("OCR Engine:"))
        mi_notify_layout.addWidget(self.mi_notify_ocr_combo)
        mi_notify_layout.addWidget(self.mi_notify_test_algo_btn)
        mi_notify_layout.addWidget(QLabel("Algorithms:"))
        mi_notify_layout.addWidget(self.mi_notify_algorithms_list)
        mi_layout.addWidget(mi_notify_group)

        mi_threshold_layout = QHBoxLayout()
        mi_threshold_layout.addWidget(QLabel("Match threshold:"))
        self.mi_threshold_spin = QSpinBox()
        self.mi_threshold_spin.setRange(0, 100)
        self.mi_threshold_spin.setValue(70)
        self.mi_threshold_spin.setSuffix("%")
        mi_threshold_layout.addWidget(self.mi_threshold_spin)
        mi_threshold_layout.addStretch()
        mi_layout.addLayout(mi_threshold_layout)

        self.mi_settings_widget.setVisible(False)
        event_layout.addWidget(self.mi_settings_widget)

        self.special_event_tracking_group.setLayout(event_layout)
        self.special_event_tracking_group.setVisible(False)  # Initially hidden, shown when mode = Special Event Tracking
        layout.addWidget(self.special_event_tracking_group)
    
    def _update_algorithms_display(self):
        """Update algorithms ListView display (COMMON for all modes)."""
        algorithms = getattr(self.action, 'ocr_algorithms', [])
        update_algorithms_display(self.algorithms_list, algorithms)
    
    def _load_settings(self):
        """Load settings from action."""
        # Passive mode (now with 4 modes)
        passive_mode = str(getattr(self.action, "passive_mode", "detect_image") or "detect_image")
        if passive_mode == "read_data":
            self.passive_mode_combo.setCurrentIndex(0)
        elif passive_mode == "event_tracking":
            self.passive_mode_combo.setCurrentIndex(2)  # Event Tracking mode
        elif passive_mode == "special_event_tracking":
            self.passive_mode_combo.setCurrentIndex(3)  # Special Event Tracking mode
        else:
            self.passive_mode_combo.setCurrentIndex(1)  # Default: detect_image
        
        # Detect image settings
        self.passive_detect_timeout_spin.setValue(float(getattr(self.action, "passive_detect_timeout", 30.0) or 30.0))
        self.passive_detect_threshold_spin.setValue(float(getattr(self.action, "passive_detect_threshold", 0.4) or 0.4))
        self.continue_on_timeout_checkbox.setChecked(bool(getattr(self.action, "continue_on_timeout", False)))
        
        # Passive settings
        self.passive_sample_spin.setValue(int(getattr(self.action, "passive_sample_every", 1) or 1))
        self.passive_only_new_checkbox.setChecked(bool(getattr(self.action, "passive_only_new_frame", True)))
        self.passive_cancel_old_checkbox.setChecked(bool(getattr(self.action, "passive_cancel_old", False)))
        self.passive_keywords_edit.setText(str(getattr(self.action, "passive_keywords", "") or ""))
        
        # Fixed ROI
        use_fixed_roi = bool(getattr(self.action, "use_fixed_roi", False))
        self.use_fixed_roi_checkbox.setChecked(use_fixed_roi)
        self.roi_coords_widget.setVisible(use_fixed_roi)
        
        self.roi_x_spin.setValue(int(getattr(self.action, "roi_x", 0) or 0))
        self.roi_y_spin.setValue(int(getattr(self.action, "roi_y", 0) or 0))
        self.roi_w_spin.setValue(int(getattr(self.action, "roi_w", 200) or 200))
        self.roi_h_spin.setValue(int(getattr(self.action, "roi_h", 100) or 100))
        
        # OCR settings
        ocr_engine = str(getattr(self.action, "ocr_engine", "auto") or "auto")
        engine_load_map = {"auto": 0, "winrt": 1, "tesseract": 2, "easyocr": 3, "vietocr": 4}
        self.ocr_engine_combo.setCurrentIndex(engine_load_map.get(ocr_engine.lower(), 0))
        
        self.ocr_bright_on_dark_checkbox.setChecked(bool(getattr(self.action, "ocr_bright_on_dark", False)))
        
        # OCR preprocessing options
        ocr_upscale_enabled = bool(getattr(self.action, "ocr_upscale_enabled", True))
        self.ocr_upscale_checkbox.setChecked(ocr_upscale_enabled)
        self.ocr_upscale_factor_widget.setVisible(ocr_upscale_enabled)
        self.ocr_upscale_factor_spin.setValue(float(getattr(self.action, "ocr_upscale_factor", 2.0) or 2.0))
        self.ocr_enhance_contrast_checkbox.setChecked(bool(getattr(self.action, "ocr_enhance_contrast", True)))
        self.ocr_sharpen_checkbox.setChecked(bool(getattr(self.action, "ocr_sharpen", True)))
        self.ocr_denoise_checkbox.setChecked(bool(getattr(self.action, "ocr_denoise", False)))
        
        # Preprocessing config status
        if getattr(self.action, "preprocessing_config", None):
            config = self.action.preprocessing_config
            algo_name = config.get("algorithm_name", config.get("algorithm", ""))
            self.preprocessing_status_label.setText(f"✓ {algo_name}")
            self.preprocessing_status_label.setStyleSheet("color: green;")
        
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
        
        # Update visibility based on mode
        self._on_passive_mode_changed(self.passive_mode_combo.currentIndex())
        
        # OCR algorithms
        self._update_ocr_algorithms_display()
        
        # Event Tracking settings (no checkbox - controlled by passive_mode)
        self.event_ocr_pattern_edit.setText(str(getattr(self.action, "event_ocr_pattern", "") or ""))
        self.event_match_threshold_spin.setValue(float(getattr(self.action, "event_match_threshold", 100.0) or 100.0))
        self.event_reappear_timeout_spin.setValue(int(getattr(self.action, "event_reappear_timeout_minutes", 15) or 15))
        
        # Event OCR engine
        event_engine_map = {"auto": 0, "winrt": 1, "tesseract": 2, "easyocr": 3, "vietocr": 4}
        event_engine = str(getattr(self.action, "event_ocr_engine", "auto") or "auto").lower()
        self.event_ocr_engine_combo.setCurrentIndex(event_engine_map.get(event_engine, 0))

        # Event ROI will be taken from Teaching image (teaching_corner_x1, y1, x2, y2)
        
        # Special Event Tracking settings
        self.imperial_guardian_checkbox.setChecked(bool(getattr(self.action, "imperial_guardian_enabled", False)))
        self.imperial_guardian_delay_spin.setValue(int(getattr(self.action, "imperial_guardian_no_player_alert_delay", 10)))

        # Load OCR engine for Imperial Guardian
        _ig_ocr_engines = ["auto", "winrt", "tesseract", "easyocr", "vietocr"]
        _ig_ocr_engine = getattr(self.action, "imperial_guardian_ocr_engine", "auto")
        _ig_ocr_idx = _ig_ocr_engines.index(_ig_ocr_engine) if _ig_ocr_engine in _ig_ocr_engines else 0
        self.imperial_guardian_ocr_engine_combo.setCurrentIndex(_ig_ocr_idx)

        # Load match threshold
        self.imperial_guardian_threshold_spin.setValue(int(getattr(self.action, "imperial_guardian_match_threshold", 70.0)))

        # Load algorithms list
        from .algorithm_display_utils import update_algorithms_display
        update_algorithms_display(self.imperial_guardian_algorithms_list, getattr(self.action, "imperial_guardian_ocr_algorithms", []) or [])
        
        # Show/hide imperial guardian widget based on checkbox state
        self.imperial_guardian_widget.setVisible(self.imperial_guardian_checkbox.isChecked())
        
        # Update ROI label if coordinates are set
        x1 = getattr(self.action, "imperial_guardian_teaching_corner_x1", 0)
        y1 = getattr(self.action, "imperial_guardian_teaching_corner_y1", 0)
        x2 = getattr(self.action, "imperial_guardian_teaching_corner_x2", 0)
        y2 = getattr(self.action, "imperial_guardian_teaching_corner_y2", 0)
        
        if x2 > x1 and y2 > y1:
            self.imperial_guardian_roi_label.setText(f"({x1}, {y1}) to ({x2}, {y2})")
            self.imperial_guardian_roi_label.setStyleSheet("color: green;")
        else:
            self.imperial_guardian_roi_label.setText("Not configured")
            self.imperial_guardian_roi_label.setStyleSheet("color: gray;")

        # Golden Invasion standalone is legacy-only. New UI exposes it as a
        # Monster Invasion sub-event, so keep the old controls hidden/off.
        self.gi_checkbox.setChecked(False)
        self.gi_checkbox.setVisible(False)
        gi_server_time = getattr(self.action, "golden_invasion_server_time", "01:30")
        if gi_server_time == "00:40":
            self.gi_time_0040.setChecked(True)
        else:
            self.gi_time_0130.setChecked(True)
        self.gi_channel_ocr_combo.setCurrentText(getattr(self.action, "golden_invasion_channel_ocr_engine", "auto"))
        self.gi_notify_ocr_combo.setCurrentText(getattr(self.action, "golden_invasion_notify_ocr_engine", "auto"))
        self.gi_threshold_spin.setValue(int(getattr(self.action, "golden_invasion_match_threshold", 70.0)))
        self.gi_settings_widget.setVisible(False)
        gx1 = getattr(self.action, "golden_invasion_channel_roi_x1", 0)
        gy1 = getattr(self.action, "golden_invasion_channel_roi_y1", 0)
        gx2 = getattr(self.action, "golden_invasion_channel_roi_x2", 0)
        gy2 = getattr(self.action, "golden_invasion_channel_roi_y2", 0)
        if gx2 > gx1 and gy2 > gy1:
            self.gi_channel_roi_label.setText(f"ROI: ({gx1}, {gy1}) → ({gx2}, {gy2})")
            self.gi_channel_roi_label.setStyleSheet("color: green;")
        else:
            self.gi_channel_roi_label.setText("ROI: chưa chọn")
            self.gi_channel_roi_label.setStyleSheet("color: gray;")
        nx1 = getattr(self.action, "golden_invasion_notify_roi_x1", 0)
        ny1 = getattr(self.action, "golden_invasion_notify_roi_y1", 0)
        nx2 = getattr(self.action, "golden_invasion_notify_roi_x2", 0)
        ny2 = getattr(self.action, "golden_invasion_notify_roi_y2", 0)
        if nx2 > nx1 and ny2 > ny1:
            self.gi_notify_roi_label.setText(f"ROI: ({nx1}, {ny1}) → ({nx2}, {ny2})")
            self.gi_notify_roi_label.setStyleSheet("color: green;")
        else:
            self.gi_notify_roi_label.setText("ROI: chưa chọn")
            self.gi_notify_roi_label.setStyleSheet("color: gray;")
        update_algorithms_display(self.gi_channel_algorithms_list, getattr(self.action, "golden_invasion_channel_ocr_algorithms", []) or [])
        update_algorithms_display(self.gi_notify_algorithms_list, getattr(self.action, "golden_invasion_notify_ocr_algorithms", []) or [])

        # Monster Invasion settings
        self.mi_checkbox.setChecked(bool(getattr(self.action, "monster_invasion_enabled", False)))
        self.mi_gi_checkbox.setChecked(bool(getattr(self.action, "monster_invasion_golden_invasion_enabled", False)))
        self.mi_ww_checkbox.setChecked(bool(getattr(self.action, "monster_invasion_white_wizard_red_dragon_enabled", False)))
        mi_gi_server_time = getattr(self.action, "monster_invasion_golden_invasion_server_time", "01:30")
        if mi_gi_server_time == "00:40":
            self.mi_gi_time_0040.setChecked(True)
        else:
            self.mi_gi_time_0130.setChecked(True)
        self.mi_channel_ocr_combo.setCurrentText(getattr(self.action, "monster_invasion_channel_ocr_engine", "auto"))
        self.mi_notify_ocr_combo.setCurrentText(getattr(self.action, "monster_invasion_notify_ocr_engine", "auto"))
        self.mi_threshold_spin.setValue(int(getattr(self.action, "monster_invasion_match_threshold", 70.0)))
        self.mi_settings_widget.setVisible(self.mi_checkbox.isChecked())
        mcx1 = getattr(self.action, "monster_invasion_channel_roi_x1", 0)
        mcy1 = getattr(self.action, "monster_invasion_channel_roi_y1", 0)
        mcx2 = getattr(self.action, "monster_invasion_channel_roi_x2", 0)
        mcy2 = getattr(self.action, "monster_invasion_channel_roi_y2", 0)
        if mcx2 > mcx1 and mcy2 > mcy1:
            self.mi_channel_roi_label.setText(f"ROI: ({mcx1}, {mcy1}) → ({mcx2}, {mcy2})")
            self.mi_channel_roi_label.setStyleSheet("color: green;")
        else:
            self.mi_channel_roi_label.setText("ROI: chưa chọn")
            self.mi_channel_roi_label.setStyleSheet("color: gray;")
        mnx1 = getattr(self.action, "monster_invasion_notify_roi_x1", 0)
        mny1 = getattr(self.action, "monster_invasion_notify_roi_y1", 0)
        mnx2 = getattr(self.action, "monster_invasion_notify_roi_x2", 0)
        mny2 = getattr(self.action, "monster_invasion_notify_roi_y2", 0)
        if mnx2 > mnx1 and mny2 > mny1:
            self.mi_notify_roi_label.setText(f"ROI: ({mnx1}, {mny1}) → ({mnx2}, {mny2})")
            self.mi_notify_roi_label.setStyleSheet("color: green;")
        else:
            self.mi_notify_roi_label.setText("ROI: chưa chọn")
            self.mi_notify_roi_label.setStyleSheet("color: gray;")
        update_algorithms_display(self.mi_channel_algorithms_list, getattr(self.action, "monster_invasion_channel_ocr_algorithms", []) or [])
        update_algorithms_display(self.mi_notify_algorithms_list, getattr(self.action, "monster_invasion_notify_ocr_algorithms", []) or [])

        # Update algorithms display (common for all modes)
        self._update_algorithms_display()    
    def _on_goto_step_changed(self, state):
        """Enable/disable goto_step_spin based on checkbox state."""
        self.goto_step_spin.setEnabled(bool(state))
    
    def _capture_teaching_image(self):
        """Open image capture dialog."""
        if not self.target_window_hwnd:
            QMessageBox.warning(self, "Cảnh báo", "Chưa chọn window game ở màn hình chính!")
            return
        
        from .image_capture_dialog import ImageCaptureDialog
        dialog = ImageCaptureDialog(
            self.target_window_hwnd,
            parent=self,
            tool_id=self.tool_id,
            hide_click_selection=True,  # READ_PASSIVE không cần chọn điểm click
            initial_image_path=getattr(self.action, "image_path", None),
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
                filename = os.path.basename(image_path)
                self.image_path_label.setText(f"Đã chọn: {filename}")
                self._update_image_button_text()
                
                # Save teaching corners and update Fixed ROI spinboxes
                if corner_x1 is not None:
                    self.action.teaching_corner_x1 = corner_x1
                    self.action.teaching_corner_y1 = corner_y1
                    self.action.teaching_corner_x2 = corner_x2
                    self.action.teaching_corner_y2 = corner_y2
                    
                    # Update Fixed ROI spinboxes with crop coordinates
                    roi_x = int(corner_x1)
                    roi_y = int(corner_y1)
                    roi_w = int(corner_x2 - corner_x1)
                    roi_h = int(corner_y2 - corner_y1)
                    
                    self.roi_x_spin.setValue(roi_x)
                    self.roi_y_spin.setValue(roi_y)
                    self.roi_w_spin.setValue(max(1, roi_w))
                    self.roi_h_spin.setValue(max(1, roi_h))
                
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
            base_dir = "images"
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
    
    def _update_image_button_text(self):
        """Update button text based on whether image exists."""
        if self.action.image_path and os.path.exists(self.action.image_path):
            self.image_btn.setText("Xem/Sửa ảnh Teaching")
        else:
            self.image_btn.setText("Tạo ảnh Teaching")
    
    def _open_algorithm_testing_dialog(self):
        """Open Multi-Image Algorithm Testing Dialog."""
        try:
            from .multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
            
            dialog = MultiImageAlgorithmTestingDialog(
                self.action,
                parent=self,
                target_window_hwnd=self.target_window_hwnd,
                tool_id=self.tool_id,
                algorithm_field="ocr_algorithms"
            )
            
            if dialog.exec():
                # Data already saved to action in dialog
                # Update algorithms display (common list for all modes)
                self._update_algorithms_display()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể mở dialog:\n{type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    def get_settings(self) -> dict:
        """Get settings from dialog.
        
        Returns:
            Dict with all passive read settings
        """
        # OCR engine mapping
        ocr_engine_map = {
            0: "auto",
            1: "winrt",
            2: "tesseract",
            3: "easyocr",
            4: "vietocr",
        }
        
        # Passive mode mapping (now with 4 modes)
        passive_mode_map = {
            0: "read_data",
            1: "detect_image",
            2: "event_tracking",
            3: "special_event_tracking"  # New mode
        }
        
        return {
            "passive_mode": passive_mode_map.get(self.passive_mode_combo.currentIndex(), "detect_image"),
            "passive_detect_timeout": float(self.passive_detect_timeout_spin.value()),
            "passive_detect_threshold": float(self.passive_detect_threshold_spin.value()),
            "continue_on_timeout": bool(self.continue_on_timeout_checkbox.isChecked()),
            "passive_sample_every": int(self.passive_sample_spin.value()),
            "passive_only_new_frame": bool(self.passive_only_new_checkbox.isChecked()),
            "passive_cancel_old": bool(self.passive_cancel_old_checkbox.isChecked()),
            "passive_keywords": str(self.passive_keywords_edit.text() or "").strip(),
            "use_fixed_roi": bool(self.use_fixed_roi_checkbox.isChecked()),
            "roi_x": int(self.roi_x_spin.value()),
            "roi_y": int(self.roi_y_spin.value()),
            "roi_w": int(self.roi_w_spin.value()),
            "roi_h": int(self.roi_h_spin.value()),
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
            "goto_step_enabled": bool(self.goto_step_checkbox.isChecked()),
            "goto_step_index": int(self.goto_step_spin.value()),  # No conversion: 0=restart, 1=step1, 2=step2...
            "image_path": self.action.image_path,
            "teaching_corner_x1": getattr(self.action, "teaching_corner_x1", None),
            "teaching_corner_y1": getattr(self.action, "teaching_corner_y1", None),
            "teaching_corner_x2": getattr(self.action, "teaching_corner_x2", None),
            "teaching_corner_y2": getattr(self.action, "teaching_corner_y2", None),
            "ocr_algorithms": getattr(self.action, 'ocr_algorithms', []),
            # Event Tracking settings (match => finish action and continue tool)
            "event_ocr_pattern": str(self.event_ocr_pattern_edit.text() or "").strip(),
            "event_match_threshold": float(self.event_match_threshold_spin.value()),
            "event_ocr_engine": ["auto", "winrt", "tesseract", "easyocr", "vietocr"][self.event_ocr_engine_combo.currentIndex()],
            "event_reappear_timeout_minutes": int(self.event_reappear_timeout_spin.value()),
            # ROI will be taken from Teaching image (teaching_corner_x1, y1, x2, y2)
            # Special Event Tracking settings
            "imperial_guardian_enabled": bool(self.imperial_guardian_checkbox.isChecked()),
            "imperial_guardian_no_player_alert_delay": int(self.imperial_guardian_delay_spin.value()),
            "imperial_guardian_ocr_engine": ["auto", "winrt", "tesseract", "easyocr", "vietocr"][self.imperial_guardian_ocr_engine_combo.currentIndex()],
            "imperial_guardian_match_threshold": float(self.imperial_guardian_threshold_spin.value()),
            "imperial_guardian_ocr_algorithms": list(getattr(self.action, "imperial_guardian_ocr_algorithms", []) or []),
            "imperial_guardian_teaching_corner_x1": getattr(self.action, "imperial_guardian_teaching_corner_x1", 0),
            "imperial_guardian_teaching_corner_y1": getattr(self.action, "imperial_guardian_teaching_corner_y1", 0),
            "imperial_guardian_teaching_corner_x2": getattr(self.action, "imperial_guardian_teaching_corner_x2", 0),
            "imperial_guardian_teaching_corner_y2": getattr(self.action, "imperial_guardian_teaching_corner_y2", 0),
            "imperial_guardian_teaching_image_path": getattr(self.action, "imperial_guardian_teaching_image_path", ""),
            "golden_invasion_enabled": False,
            "golden_invasion_server_time": "00:40" if self.gi_time_0040.isChecked() else "01:30",
            "golden_invasion_channel_roi_x1": getattr(self.action, "golden_invasion_channel_roi_x1", 0),
            "golden_invasion_channel_roi_y1": getattr(self.action, "golden_invasion_channel_roi_y1", 0),
            "golden_invasion_channel_roi_x2": getattr(self.action, "golden_invasion_channel_roi_x2", 0),
            "golden_invasion_channel_roi_y2": getattr(self.action, "golden_invasion_channel_roi_y2", 0),
            "golden_invasion_channel_ocr_engine": self.gi_channel_ocr_combo.currentText(),
            "golden_invasion_channel_ocr_algorithms": list(getattr(self.action, "golden_invasion_channel_ocr_algorithms", []) or []),
            "golden_invasion_channel_teaching_image_path": getattr(self.action, "golden_invasion_channel_teaching_image_path", ""),
            "golden_invasion_notify_roi_x1": getattr(self.action, "golden_invasion_notify_roi_x1", 0),
            "golden_invasion_notify_roi_y1": getattr(self.action, "golden_invasion_notify_roi_y1", 0),
            "golden_invasion_notify_roi_x2": getattr(self.action, "golden_invasion_notify_roi_x2", 0),
            "golden_invasion_notify_roi_y2": getattr(self.action, "golden_invasion_notify_roi_y2", 0),
            "golden_invasion_notify_ocr_engine": self.gi_notify_ocr_combo.currentText(),
            "golden_invasion_notify_ocr_algorithms": list(getattr(self.action, "golden_invasion_notify_ocr_algorithms", []) or []),
            "golden_invasion_notify_teaching_image_path": getattr(self.action, "golden_invasion_notify_teaching_image_path", ""),
            "golden_invasion_match_threshold": float(self.gi_threshold_spin.value()),
            "monster_invasion_enabled": bool(self.mi_checkbox.isChecked()),
            "monster_invasion_channel_roi_x1": getattr(self.action, "monster_invasion_channel_roi_x1", 0),
            "monster_invasion_channel_roi_y1": getattr(self.action, "monster_invasion_channel_roi_y1", 0),
            "monster_invasion_channel_roi_x2": getattr(self.action, "monster_invasion_channel_roi_x2", 0),
            "monster_invasion_channel_roi_y2": getattr(self.action, "monster_invasion_channel_roi_y2", 0),
            "monster_invasion_channel_ocr_engine": self.mi_channel_ocr_combo.currentText(),
            "monster_invasion_channel_ocr_algorithms": list(getattr(self.action, "monster_invasion_channel_ocr_algorithms", []) or []),
            "monster_invasion_channel_teaching_image_path": getattr(self.action, "monster_invasion_channel_teaching_image_path", ""),
            "monster_invasion_notify_roi_x1": getattr(self.action, "monster_invasion_notify_roi_x1", 0),
            "monster_invasion_notify_roi_y1": getattr(self.action, "monster_invasion_notify_roi_y1", 0),
            "monster_invasion_notify_roi_x2": getattr(self.action, "monster_invasion_notify_roi_x2", 0),
            "monster_invasion_notify_roi_y2": getattr(self.action, "monster_invasion_notify_roi_y2", 0),
            "monster_invasion_notify_ocr_engine": self.mi_notify_ocr_combo.currentText(),
            "monster_invasion_notify_ocr_algorithms": list(getattr(self.action, "monster_invasion_notify_ocr_algorithms", []) or []),
            "monster_invasion_notify_teaching_image_path": getattr(self.action, "monster_invasion_notify_teaching_image_path", ""),
            "monster_invasion_match_threshold": float(self.mi_threshold_spin.value()),
            "monster_invasion_golden_invasion_enabled": bool(self.mi_gi_checkbox.isChecked()),
            "monster_invasion_golden_invasion_server_time": "00:40" if self.mi_gi_time_0040.isChecked() else "01:30",
            "monster_invasion_white_wizard_red_dragon_enabled": bool(self.mi_ww_checkbox.isChecked()),
        }
    
    def _on_imperial_guardian_changed(self, state):
        """Handle Imperial Guardian checkbox state change."""
        is_checked = state == 2  # Qt.Checked = 2
        self.imperial_guardian_widget.setVisible(is_checked)
    
    def _select_imperial_guardian_image(self):
        """Open ImageCaptureDialog to capture ROI for Imperial Guardian."""
        if not self.target_window_hwnd:
            QMessageBox.warning(self, "Cảnh báo", "Chưa chọn window game ở màn hình chính!")
            return

        from .image_capture_dialog import ImageCaptureDialog
        # Use existing Imperial Guardian teaching image if available
        existing_image_path = getattr(self.action, 'imperial_guardian_teaching_image_path', None)
        dialog = ImageCaptureDialog(
            self.target_window_hwnd,
            parent=self,
            tool_id=self.tool_id,
            hide_click_selection=True,
            initial_image_path=existing_image_path,
        )
        if dialog.exec():
            result = dialog.get_cropped_image_path()
            if len(result) >= 7:
                _, _, _, corner_x1, corner_y1, corner_x2, corner_y2 = result[:7]
            else:
                corner_x1 = corner_y1 = corner_x2 = corner_y2 = None

            if corner_x1 is not None:
                self.action.imperial_guardian_teaching_corner_x1 = int(corner_x1)
                self.action.imperial_guardian_teaching_corner_y1 = int(corner_y1)
                self.action.imperial_guardian_teaching_corner_x2 = int(corner_x2)
                self.action.imperial_guardian_teaching_corner_y2 = int(corner_y2)
                # Save the actual image path for Imperial Guardian
                self.action.imperial_guardian_teaching_image_path = result[0] if len(result) > 0 else None
                self.imperial_guardian_roi_label.setText(
                    f"ROI: ({int(corner_x1)}, {int(corner_y1)}) → ({int(corner_x2)}, {int(corner_y2)})"
                )
                self.imperial_guardian_roi_label.setStyleSheet("color: green;")
            else:
                self.imperial_guardian_roi_label.setText("ROI chua duoc chon")
                self.imperial_guardian_roi_label.setStyleSheet("color: red;")

    def _open_imperial_guardian_algorithm_testing(self) -> None:
        """Open MultiImageAlgorithmTestingDialog for Imperial Guardian ROI."""
        if not self.target_window_hwnd:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Canh bao", "Chua chon window game!")
            return
        from .multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
        from .algorithm_display_utils import update_algorithms_display
        dialog = MultiImageAlgorithmTestingDialog(
            action=self.action,
            parent=self,
            target_window_hwnd=self.target_window_hwnd,
            algorithm_field="imperial_guardian_ocr_algorithms"
        )
        if dialog.exec():
            # Get algorithms from dialog and save to imperial_guardian_ocr_algorithms
            algorithms = dialog._get_current_algorithms()
            self.action.imperial_guardian_ocr_algorithms = algorithms
            update_algorithms_display(self.imperial_guardian_algorithms_list, self.action.imperial_guardian_ocr_algorithms)


    def _on_gi_checkbox_changed(self, state: int) -> None:
        self.gi_settings_widget.setVisible(False)

    def _on_mi_checkbox_changed(self, state: int) -> None:
        self.mi_settings_widget.setVisible(bool(state))

    def _select_gi_channel_image(self) -> None:
        if not self.target_window_hwnd:
            QMessageBox.warning(self, "Cảnh báo", "Chưa chọn window game ở màn hình chính!")
            return
        from .image_capture_dialog import ImageCaptureDialog
        dialog = ImageCaptureDialog(
            self.target_window_hwnd,
            parent=self,
            tool_id=self.tool_id,
            hide_click_selection=True,
            initial_image_path=getattr(self.action, "golden_invasion_channel_teaching_image_path", None),
        )
        if dialog.exec():
            result = dialog.get_cropped_image_path()
            corner_x1 = corner_y1 = corner_x2 = corner_y2 = None
            if len(result) >= 7:
                _, _, _, corner_x1, corner_y1, corner_x2, corner_y2 = result[:7]
            if corner_x1 is not None:
                self.action.golden_invasion_channel_teaching_image_path = result[0] if len(result) > 0 else ""
                self.action.golden_invasion_channel_roi_x1 = int(corner_x1)
                self.action.golden_invasion_channel_roi_y1 = int(corner_y1)
                self.action.golden_invasion_channel_roi_x2 = int(corner_x2)
                self.action.golden_invasion_channel_roi_y2 = int(corner_y2)
                self.gi_channel_roi_label.setText(f"ROI: ({int(corner_x1)}, {int(corner_y1)}) → ({int(corner_x2)}, {int(corner_y2)})")
                self.gi_channel_roi_label.setStyleSheet("color: green;")
            else:
                self.gi_channel_roi_label.setText("ROI chưa được chọn")
                self.gi_channel_roi_label.setStyleSheet("color: red;")

    def _select_gi_notify_image(self) -> None:
        if not self.target_window_hwnd:
            QMessageBox.warning(self, "Cảnh báo", "Chưa chọn window game ở màn hình chính!")
            return
        from .image_capture_dialog import ImageCaptureDialog
        dialog = ImageCaptureDialog(
            self.target_window_hwnd,
            parent=self,
            tool_id=self.tool_id,
            hide_click_selection=True,
            initial_image_path=getattr(self.action, "golden_invasion_notify_teaching_image_path", None),
        )
        if dialog.exec():
            result = dialog.get_cropped_image_path()
            corner_x1 = corner_y1 = corner_x2 = corner_y2 = None
            if len(result) >= 7:
                _, _, _, corner_x1, corner_y1, corner_x2, corner_y2 = result[:7]
            if corner_x1 is not None:
                self.action.golden_invasion_notify_teaching_image_path = result[0] if len(result) > 0 else ""
                self.action.golden_invasion_notify_roi_x1 = int(corner_x1)
                self.action.golden_invasion_notify_roi_y1 = int(corner_y1)
                self.action.golden_invasion_notify_roi_x2 = int(corner_x2)
                self.action.golden_invasion_notify_roi_y2 = int(corner_y2)
                self.gi_notify_roi_label.setText(f"ROI: ({int(corner_x1)}, {int(corner_y1)}) → ({int(corner_x2)}, {int(corner_y2)})")
                self.gi_notify_roi_label.setStyleSheet("color: green;")
            else:
                self.gi_notify_roi_label.setText("ROI chưa được chọn")
                self.gi_notify_roi_label.setStyleSheet("color: red;")

    def _open_gi_channel_algorithm_testing(self) -> None:
        if not self.target_window_hwnd:
            QMessageBox.warning(self, "Cảnh báo", "Chưa chọn window game!")
            return
        from .multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
        from .algorithm_display_utils import update_algorithms_display
        dialog = MultiImageAlgorithmTestingDialog(action=self.action, parent=self, target_window_hwnd=self.target_window_hwnd, algorithm_field="golden_invasion_channel_ocr_algorithms")
        if dialog.exec():
            algorithms = dialog._get_current_algorithms()
            self.action.golden_invasion_channel_ocr_algorithms = algorithms
            update_algorithms_display(self.gi_channel_algorithms_list, self.action.golden_invasion_channel_ocr_algorithms)

    def _open_gi_notify_algorithm_testing(self) -> None:
        if not self.target_window_hwnd:
            QMessageBox.warning(self, "Cảnh báo", "Chưa chọn window game!")
            return
        from .multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
        from .algorithm_display_utils import update_algorithms_display
        dialog = MultiImageAlgorithmTestingDialog(action=self.action, parent=self, target_window_hwnd=self.target_window_hwnd, algorithm_field="golden_invasion_notify_ocr_algorithms")
        if dialog.exec():
            algorithms = dialog._get_current_algorithms()
            self.action.golden_invasion_notify_ocr_algorithms = algorithms
            update_algorithms_display(self.gi_notify_algorithms_list, self.action.golden_invasion_notify_ocr_algorithms)

    def _select_monster_invasion_image(self, role: str) -> None:
        if not self.target_window_hwnd:
            QMessageBox.warning(self, "Cảnh báo", "Chưa chọn window game ở màn hình chính!")
            return
        from .image_capture_dialog import ImageCaptureDialog

        prefix = f"monster_invasion_{role}"
        label = self.mi_channel_roi_label if role == "channel" else self.mi_notify_roi_label
        dialog = ImageCaptureDialog(
            self.target_window_hwnd,
            parent=self,
            tool_id=self.tool_id,
            hide_click_selection=True,
            initial_image_path=getattr(self.action, f"{prefix}_teaching_image_path", None),
        )
        if dialog.exec():
            result = dialog.get_cropped_image_path()
            corner_x1 = corner_y1 = corner_x2 = corner_y2 = None
            if len(result) >= 7:
                _, _, _, corner_x1, corner_y1, corner_x2, corner_y2 = result[:7]
            if corner_x1 is not None:
                setattr(self.action, f"{prefix}_teaching_image_path", result[0] if len(result) > 0 else "")
                setattr(self.action, f"{prefix}_roi_x1", int(corner_x1))
                setattr(self.action, f"{prefix}_roi_y1", int(corner_y1))
                setattr(self.action, f"{prefix}_roi_x2", int(corner_x2))
                setattr(self.action, f"{prefix}_roi_y2", int(corner_y2))
                label.setText(f"ROI: ({int(corner_x1)}, {int(corner_y1)}) → ({int(corner_x2)}, {int(corner_y2)})")
                label.setStyleSheet("color: green;")
            else:
                label.setText("ROI chưa được chọn")
                label.setStyleSheet("color: red;")

    def _select_mi_channel_image(self) -> None:
        self._select_monster_invasion_image("channel")

    def _select_mi_notify_image(self) -> None:
        self._select_monster_invasion_image("notify")

    def _open_monster_invasion_algorithm_testing(self, role: str) -> None:
        if not self.target_window_hwnd:
            QMessageBox.warning(self, "Cảnh báo", "Chưa chọn window game!")
            return
        from .multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
        from .algorithm_display_utils import update_algorithms_display

        field = f"monster_invasion_{role}_ocr_algorithms"
        target_list = self.mi_channel_algorithms_list if role == "channel" else self.mi_notify_algorithms_list
        dialog = MultiImageAlgorithmTestingDialog(
            action=self.action,
            parent=self,
            target_window_hwnd=self.target_window_hwnd,
            algorithm_field=field,
        )
        if dialog.exec():
            algorithms = dialog._get_current_algorithms()
            setattr(self.action, field, algorithms)
            update_algorithms_display(target_list, algorithms)

    def _open_mi_channel_algorithm_testing(self) -> None:
        self._open_monster_invasion_algorithm_testing("channel")

    def _open_mi_notify_algorithm_testing(self) -> None:
        self._open_monster_invasion_algorithm_testing("notify")
