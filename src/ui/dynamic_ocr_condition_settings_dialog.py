"""Settings dialog for Dynamic OCR Condition action."""

from __future__ import annotations

import copy
import os
import re
import shutil
import textwrap

from PyQt6.QtGui import QTextOption
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..logic.action_type import AutoAction
from .algorithm_display_utils import update_algorithms_display

TIMEOUT_INTERVAL_SECONDS = 0.1


class DynamicOCRConditionSettingsDialog(QDialog):
    """Configure generic OCR patterns and Python condition code."""

    def __init__(self, action: AutoAction, parent=None, target_window_hwnd=None, tool_id: str | None = None):
        super().__init__(parent)
        self.action = action
        self.target_window_hwnd = target_window_hwnd
        self.tool_id = tool_id
        self.setWindowTitle("Cài đặt Dynamic OCR Condition")
        self.setFixedSize(760, 860)
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)

        target_group = QGroupBox("Vùng đọc OCR")
        target_layout = QVBoxLayout()

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Chế độ tìm vùng đọc:"))
        self.target_mode_combo = QComboBox()
        self.target_mode_combo.addItem("ROI", "roi")
        self.target_mode_combo.addItem("Teaching Image", "teaching")
        self.target_mode_combo.currentIndexChanged.connect(self._on_target_mode_changed)
        mode_row.addWidget(self.target_mode_combo)
        mode_row.addStretch()
        target_layout.addLayout(mode_row)

        teaching_group = QGroupBox("Teaching Image")
        teaching_layout = QVBoxLayout()

        self.image_path_label = QLabel("Chưa chọn ảnh")
        self.image_path_label.setWordWrap(True)
        teaching_layout.addWidget(self.image_path_label)

        image_btn_row = QHBoxLayout()
        self.image_btn = QPushButton("Tạo ảnh Teaching")
        self.image_btn.clicked.connect(self._capture_teaching_image)
        image_btn_row.addWidget(self.image_btn)

        self.image_file_btn = QPushButton("Chọn file ảnh...")
        self.image_file_btn.clicked.connect(self._select_image_file)
        image_btn_row.addWidget(self.image_file_btn)
        image_btn_row.addStretch()
        teaching_layout.addLayout(image_btn_row)

        threshold_row = QHBoxLayout()
        threshold_row.addWidget(QLabel("Ngưỡng match teaching:"))
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.10, 0.99)
        self.threshold_spin.setSingleStep(0.01)
        self.threshold_spin.setDecimals(2)
        threshold_row.addWidget(self.threshold_spin)
        threshold_row.addStretch()
        teaching_layout.addLayout(threshold_row)

        success_goto_row = QHBoxLayout()
        self.goto_step_checkbox = QCheckBox("Khi thành công → nhảy về step:")
        self.goto_step_checkbox.stateChanged.connect(self._on_goto_step_changed)
        success_goto_row.addWidget(self.goto_step_checkbox)
        self.goto_step_spin = QSpinBox()
        self.goto_step_spin.setMinimum(0)
        self.goto_step_spin.setMaximum(100)
        self.goto_step_spin.setValue(1)
        self.goto_step_spin.setToolTip("0 = Restart cycle từ đầu\n1-N = Nhảy về step cụ thể")
        self.goto_step_spin.setEnabled(False)
        success_goto_row.addWidget(self.goto_step_spin)
        success_goto_row.addStretch()
        teaching_layout.addLayout(success_goto_row)

        timeout_goto_row = QHBoxLayout()
        self.timeout_goto_checkbox = QCheckBox("Khi timeout → nhảy về step:")
        self.timeout_goto_checkbox.stateChanged.connect(self._on_timeout_goto_changed)
        timeout_goto_row.addWidget(self.timeout_goto_checkbox)
        self.timeout_goto_spin = QSpinBox()
        self.timeout_goto_spin.setMinimum(0)
        self.timeout_goto_spin.setMaximum(100)
        self.timeout_goto_spin.setValue(1)
        self.timeout_goto_spin.setToolTip("0 = Restart cycle từ đầu\n1-N = Nhảy về step cụ thể")
        self.timeout_goto_spin.setEnabled(False)
        timeout_goto_row.addWidget(self.timeout_goto_spin)
        timeout_goto_row.addStretch()
        teaching_layout.addLayout(timeout_goto_row)

        timeout_interval_row = QHBoxLayout()
        timeout_interval_row.addWidget(QLabel("So chu ky timeout:"))
        self.timeout_interval_spin = QSpinBox()
        self.timeout_interval_spin.setRange(1, 99999)
        timeout_interval_row.addWidget(self.timeout_interval_spin)
        self.timeout_interval_info_label = QLabel(f"Moi chu ky hien tai: {TIMEOUT_INTERVAL_SECONDS:.2f}s")
        timeout_interval_row.addWidget(self.timeout_interval_info_label)
        timeout_interval_row.addStretch()
        teaching_layout.addLayout(timeout_interval_row)

        teaching_group.setLayout(teaching_layout)
        target_layout.addWidget(teaching_group)

        self._add_matching_algorithm_section(target_layout)
        self._add_ocr_algorithm_section(target_layout)

        self.roi_group = QGroupBox("ROI OCR")
        roi_layout = QGridLayout()
        self.use_roi_checkbox = QCheckBox("Bật ROI cố định")
        self.use_roi_checkbox.stateChanged.connect(self._on_roi_toggle_changed)
        roi_layout.addWidget(self.use_roi_checkbox, 0, 0, 1, 2)

        self.roi_x_spin = QSpinBox()
        self.roi_y_spin = QSpinBox()
        self.roi_w_spin = QSpinBox()
        self.roi_h_spin = QSpinBox()
        for spin in (self.roi_x_spin, self.roi_y_spin, self.roi_w_spin, self.roi_h_spin):
            spin.setRange(0, 99999)
        self.roi_w_spin.setValue(200)
        self.roi_h_spin.setValue(100)

        roi_layout.addWidget(QLabel("X"), 1, 0)
        roi_layout.addWidget(self.roi_x_spin, 1, 1)
        roi_layout.addWidget(QLabel("Y"), 1, 2)
        roi_layout.addWidget(self.roi_y_spin, 1, 3)
        roi_layout.addWidget(QLabel("W"), 2, 0)
        roi_layout.addWidget(self.roi_w_spin, 2, 1)
        roi_layout.addWidget(QLabel("H"), 2, 2)
        roi_layout.addWidget(self.roi_h_spin, 2, 3)
        self.roi_group.setLayout(roi_layout)
        target_layout.addWidget(self.roi_group)

        target_group.setLayout(target_layout)
        layout.addWidget(target_group)

        ocr_group = QGroupBox("OCR")
        ocr_layout = QHBoxLayout()
        ocr_layout.addWidget(QLabel("OCR engine:"))
        self.ocr_engine_combo = QComboBox()
        self.ocr_engine_combo.addItem("Tự động (Auto)", "auto")
        self.ocr_engine_combo.addItem("Windows OCR (WinRT)", "winrt")
        self.ocr_engine_combo.addItem("Tesseract", "tesseract")
        self.ocr_engine_combo.addItem("EasyOCR", "easyocr")
        self.ocr_engine_combo.addItem("VietOCR", "vietocr")
        ocr_layout.addWidget(self.ocr_engine_combo)
        ocr_layout.addStretch()
        ocr_group.setLayout(ocr_layout)
        layout.addWidget(ocr_group)

        pattern_group = QGroupBox("Text Matching / Pattern Templates")
        pattern_layout = QVBoxLayout()
        pattern_layout.addWidget(QLabel("Ví dụ: Sự kiện a bắt đầu sau {param1} phút"))

        pattern_threshold_row = QHBoxLayout()
        pattern_threshold_row.addWidget(QLabel("Pattern match threshold (%):"))
        self.pattern_threshold_spin = QDoubleSpinBox()
        self.pattern_threshold_spin.setRange(0.0, 100.0)
        self.pattern_threshold_spin.setSingleStep(1.0)
        self.pattern_threshold_spin.setDecimals(1)
        pattern_threshold_row.addWidget(self.pattern_threshold_spin)
        pattern_threshold_row.addStretch()
        pattern_layout.addLayout(pattern_threshold_row)

        self.patterns_table = QTableWidget(0, 1)
        self.patterns_table.setHorizontalHeaderLabels(["Pattern Template"])
        self.patterns_table.horizontalHeader().setStretchLastSection(True)
        self.patterns_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.patterns_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.patterns_table.setMinimumHeight(220)
        pattern_layout.addWidget(self.patterns_table)

        pattern_btn_row = QHBoxLayout()
        add_pattern_btn = QPushButton("➕ Add Pattern")
        add_pattern_btn.clicked.connect(self._add_pattern_row)
        pattern_btn_row.addWidget(add_pattern_btn)
        remove_pattern_btn = QPushButton("🗑 Remove Pattern")
        remove_pattern_btn.clicked.connect(self._remove_selected_pattern_row)
        pattern_btn_row.addWidget(remove_pattern_btn)
        test_pattern_btn = QPushButton("Test Text Matching")
        test_pattern_btn.clicked.connect(self._open_dynamic_ocr_test_dialog)
        pattern_btn_row.addWidget(test_pattern_btn)
        pattern_btn_row.addStretch()
        pattern_layout.addLayout(pattern_btn_row)
        pattern_group.setLayout(pattern_layout)
        layout.addWidget(pattern_group)

        coding_group = QGroupBox("Coding")
        coding_layout = QVBoxLayout()
        coding_layout.addWidget(QLabel("Biến có sẵn: các {param} extract được, ocr_text, lines"))

        self.code_edit = QTextEdit()
        self.code_edit.setPlaceholderText("return False")
        self.code_edit.setMinimumHeight(180)
        coding_layout.addWidget(self.code_edit)

        code_btn_row = QHBoxLayout()
        self.validate_code_btn = QPushButton("Check Code Syntax")
        self.validate_code_btn.clicked.connect(self._validate_current_code)
        code_btn_row.addWidget(self.validate_code_btn)
        self.code_status_label = QLabel("")
        code_btn_row.addWidget(self.code_status_label)
        code_btn_row.addStretch()
        coding_layout.addLayout(code_btn_row)

        self.code_comment_label = QLabel("Comment")
        coding_layout.addWidget(self.code_comment_label)
        self.code_comment_edit = QTextEdit()
        self.code_comment_edit.setPlaceholderText("Mô tả logic code...")
        self.code_comment_edit.setMinimumHeight(90)
        self.code_comment_edit.setReadOnly(True)
        self.code_comment_edit.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        coding_layout.addWidget(self.code_comment_edit)

        coding_group.setLayout(coding_layout)
        layout.addWidget(coding_group)

        layout.addStretch()
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

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

    def _add_ocr_algorithm_section(self, layout):
        group = QGroupBox("OCR Algorithms")
        group_layout = QVBoxLayout()

        self.ocr_algorithms_list = QListWidget()
        self.ocr_algorithms_list.setMaximumHeight(120)
        self.ocr_algorithms_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        group_layout.addWidget(self.ocr_algorithms_list)

        configure_btn = QPushButton("⚙️ Cấu hình OCR Algorithms")
        configure_btn.clicked.connect(self._open_ocr_algorithm_config)
        group_layout.addWidget(configure_btn)

        group.setLayout(group_layout)
        layout.addWidget(group)

    def _add_matching_algorithm_section(self, layout):
        group = QGroupBox("Matching Algorithms")
        group_layout = QVBoxLayout()

        self.matching_algorithms_list = QListWidget()
        self.matching_algorithms_list.setMaximumHeight(120)
        self.matching_algorithms_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        group_layout.addWidget(self.matching_algorithms_list)

        configure_btn = QPushButton("Configure Matching Algorithms")
        configure_btn.clicked.connect(self._open_matching_algorithm_config)
        group_layout.addWidget(configure_btn)

        group.setLayout(group_layout)
        layout.addWidget(group)

    def _add_pattern_row(self, pattern: str = ""):
        row = self.patterns_table.rowCount()
        self.patterns_table.insertRow(row)
        self.patterns_table.setItem(row, 0, QTableWidgetItem(str(pattern or "")))

    def _remove_selected_pattern_row(self):
        row = self.patterns_table.currentRow()
        if row >= 0:
            self.patterns_table.removeRow(row)

    def _collect_patterns(self) -> list[str]:
        patterns: list[str] = []
        for row in range(self.patterns_table.rowCount()):
            item = self.patterns_table.item(row, 0)
            pattern = str(item.text() if item else "").strip()
            if not pattern:
                continue
            for variable_name in re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", pattern):
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", variable_name):
                    raise ValueError(f"Pattern dòng {row + 1}: biến '{variable_name}' không hợp lệ")
            patterns.append(pattern)
        return patterns

    def _build_validation_context(self) -> dict:
        context = {"ocr_text": "", "lines": []}
        for pattern in self._collect_patterns():
            for variable_name in re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", pattern):
                context.setdefault(variable_name, 0)
        return context

    def _wrap_user_code(self, code: str) -> str:
        body = str(code or "").strip() or "return False"
        return "def __dynamic_eval__():\n" + textwrap.indent(body, "    ")

    def _validate_code(self, code: str):
        context = self._build_validation_context()
        safe_globals = {
            "__builtins__": {
                "abs": abs,
                "all": all,
                "any": any,
                "bool": bool,
                "float": float,
                "int": int,
                "len": len,
                "max": max,
                "min": min,
                "range": range,
                "str": str,
                "sum": sum,
            },
            "re": re,
        }
        safe_globals.update(context)
        exec(self._wrap_user_code(code), safe_globals, safe_globals)
        result = safe_globals["__dynamic_eval__"]()
        if not isinstance(result, bool):
            raise ValueError("Code phải return True hoặc False.")

    def _validate_current_code(self):
        try:
            self._validate_code(self.code_edit.toPlainText())
        except Exception as exc:
            self.code_status_label.setText("Code lỗi")
            self.code_status_label.setStyleSheet("color:#d32f2f;")
            QMessageBox.critical(self, "Code không hợp lệ", str(exc))
            return
        self.code_status_label.setText("Syntax hợp lệ")
        self.code_status_label.setStyleSheet("color:#2e7d32;")
        QMessageBox.information(
            self,
            "Hợp lệ",
            "Code chạy được và trả về bool. Kết quả True/False thật chỉ được tính trong Test Text Matching với param OCR thực tế.",
        )

    def accept(self):
        try:
            self._collect_patterns()
            self._validate_code(self.code_edit.toPlainText())
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi cấu hình", str(exc))
            return
        super().accept()

    def _on_target_mode_changed(self, _index: int):
        is_roi = self.target_mode_combo.currentData() == "roi"
        self.use_roi_checkbox.setEnabled(is_roi)
        self._on_roi_toggle_changed(self.use_roi_checkbox.isChecked())

    def _on_goto_step_changed(self, state):
        self.goto_step_spin.setEnabled(bool(state))

    def _on_timeout_goto_changed(self, state):
        self.timeout_goto_spin.setEnabled(bool(state))

    def _on_roi_toggle_changed(self, state):
        enabled = bool(state) and self.target_mode_combo.currentData() == "roi"
        for spin in (self.roi_x_spin, self.roi_y_spin, self.roi_w_spin, self.roi_h_spin):
            spin.setEnabled(enabled)

    def _capture_teaching_image(self):
        parent_dialog = self.parent()
        if not hasattr(parent_dialog, "target_window_hwnd") or not parent_dialog.target_window_hwnd:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn window game trước khi chụp ảnh!")
            return

        try:
            from .image_capture_dialog import ImageCaptureDialog

            capture_dialog = ImageCaptureDialog(
                parent_dialog.target_window_hwnd,
                parent=self,
                tool_id=self.tool_id,
                hide_click_selection=True,
                initial_image_path=getattr(self.action, "image_path", None),
                initial_mask_regions=getattr(self.action, "mask_regions", None),
            )
            if capture_dialog.exec():
                result = capture_dialog.get_cropped_image_path()
                if len(result) == 9:
                    image_path, _, _, corner_x1, corner_y1, corner_x2, corner_y2, window_width, window_height = result
                elif len(result) == 7:
                    image_path, _, _, corner_x1, corner_y1, corner_x2, corner_y2 = result
                    window_width, window_height = None, None
                else:
                    image_path = None
                    corner_x1 = corner_y1 = corner_x2 = corner_y2 = None
                    window_width = window_height = None

                if image_path:
                    self.action.image_path = image_path
                    self.action.teaching_corner_x1 = corner_x1
                    self.action.teaching_corner_y1 = corner_y1
                    self.action.teaching_corner_x2 = corner_x2
                    self.action.teaching_corner_y2 = corner_y2
                    self.action.teaching_window_width = window_width
                    self.action.teaching_window_height = window_height
                    self.action.mask_regions = list(capture_dialog.get_mask_regions() or [])
                    self._update_teaching_label()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", f"Không thể mở dialog capture:\n{exc}")

    def _select_image_file(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Chọn ảnh", "", "Image Files (*.png *.jpg *.jpeg *.bmp)")
        if not filepath:
            return

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
        self._update_teaching_label()

    def _open_algorithm_testing_dialog(self):
        self._open_ocr_algorithm_config()

    def _build_action_from_current_ui(self) -> AutoAction:
        temp_action = copy.deepcopy(self.action)
        settings = self.get_settings()
        temp_action.dynamic_ocr_target_mode = str(self.target_mode_combo.currentData() or "roi")
        temp_action.dynamic_ocr_rules = settings["dynamic_ocr_rules"]
        temp_action.dynamic_ocr_patterns = settings["dynamic_ocr_patterns"]
        temp_action.dynamic_ocr_pattern_threshold = settings["dynamic_ocr_pattern_threshold"]
        temp_action.dynamic_ocr_code = settings["dynamic_ocr_code"]
        temp_action.match_threshold = settings["match_threshold"]
        temp_action.timeout = settings["timeout"]
        temp_action.check_interval = settings["check_interval"]
        temp_action.delay = settings["delay"]
        temp_action.ocr_engine = settings["ocr_engine"]
        temp_action.image_path = settings["image_path"]
        temp_action.teaching_corner_x1 = settings["teaching_corner_x1"]
        temp_action.teaching_corner_y1 = settings["teaching_corner_y1"]
        temp_action.teaching_corner_x2 = settings["teaching_corner_x2"]
        temp_action.teaching_corner_y2 = settings["teaching_corner_y2"]
        temp_action.teaching_window_width = settings["teaching_window_width"]
        temp_action.teaching_window_height = settings["teaching_window_height"]
        temp_action.use_fixed_roi = settings["use_fixed_roi"]
        temp_action.roi_x = settings["roi_x"]
        temp_action.roi_y = settings["roi_y"]
        temp_action.roi_w = settings["roi_w"]
        temp_action.roi_h = settings["roi_h"]
        temp_action.goto_step_enabled = settings["goto_step_enabled"]
        temp_action.goto_step_index = settings["goto_step_index"]
        temp_action.timeout_goto_enabled = settings["timeout_goto_enabled"]
        temp_action.timeout_goto_step_index = settings["timeout_goto_step_index"]
        temp_action.template_matching_algorithms = settings["template_matching_algorithms"]
        temp_action.ocr_algorithms = settings["ocr_algorithms"]
        return temp_action

    def _open_dynamic_ocr_test_dialog(self):
        current_action = self._build_action_from_current_ui()
        image_path = str(getattr(current_action, "image_path", "") or "").strip()
        if not image_path:
            QMessageBox.warning(self, "Canh bao", "Can cau hinh teaching image truoc khi mo test dialog.")
            return

        try:
            patterns = self._collect_patterns()
        except Exception as exc:
            QMessageBox.critical(self, "Loi cau hinh", str(exc))
            return

        if not patterns:
            QMessageBox.warning(self, "Canh bao", "Can it nhat 1 pattern template de mo test dialog.")
            return

        code = str(self.code_edit.toPlainText() or "").strip()
        if not code:
            QMessageBox.warning(self, "Canh bao", "Can nhap coding truoc khi mo test dialog.")
            return

        try:
            self._validate_code(code)
        except Exception as exc:
            QMessageBox.critical(self, "Code khong hop le", str(exc))
            return

        from .dynamic_ocr_test_dialog import DynamicOCRTestDialog

        dialog = DynamicOCRTestDialog(
            action=current_action,
            parent=self,
            target_window_hwnd=self.target_window_hwnd,
            tool_id=self.tool_id,
        )
        dialog.exec()

    def _open_ocr_algorithm_config(self):
        from .multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog

        dialog = MultiImageAlgorithmTestingDialog(
            action=self.action,
            parent=self,
            target_window_hwnd=self.target_window_hwnd,
            tool_id=self.tool_id,
            algorithm_field="ocr_algorithms",
        )
        if dialog.exec():
            self._update_ocr_algorithms_display()

    def _open_matching_algorithm_config(self):
        from .multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog

        dialog = MultiImageAlgorithmTestingDialog(
            action=self.action,
            parent=self,
            target_window_hwnd=self.target_window_hwnd,
            tool_id=self.tool_id,
            algorithm_field="template_matching_algorithms",
        )
        if dialog.exec():
            self._update_matching_algorithms_display()

    def _update_ocr_algorithms_display(self):
        update_algorithms_display(self.ocr_algorithms_list, getattr(self.action, "ocr_algorithms", []) or [])

    def _update_matching_algorithms_display(self):
        update_algorithms_display(
            self.matching_algorithms_list,
            getattr(self.action, "template_matching_algorithms", []) or [],
        )

    def _update_teaching_label(self):
        if self.action.image_path:
            self.image_path_label.setText(f"Đã chọn: {os.path.basename(self.action.image_path)}")
            self.image_btn.setText("Xem/Sửa ảnh Teaching")
        else:
            self.image_path_label.setText("Chưa chọn ảnh")
            self.image_btn.setText("Tạo ảnh Teaching")

    def _update_comment_visibility(self):
        has_comment = bool(str(self.code_comment_edit.toPlainText() or "").strip())
        self.code_comment_label.setVisible(has_comment)
        self.code_comment_edit.setVisible(has_comment)

    def _load_settings(self):
        target_mode = str(getattr(self.action, "dynamic_ocr_target_mode", "roi") or "roi")
        idx = self.target_mode_combo.findData(target_mode)
        self.target_mode_combo.setCurrentIndex(idx if idx >= 0 else 0)

        self.threshold_spin.setValue(float(getattr(self.action, "match_threshold", 0.4) or 0.4))

        self.use_roi_checkbox.setChecked(bool(getattr(self.action, "use_fixed_roi", False)))
        self.roi_x_spin.setValue(int(getattr(self.action, "roi_x", 0) or 0))
        self.roi_y_spin.setValue(int(getattr(self.action, "roi_y", 0) or 0))
        self.roi_w_spin.setValue(int(getattr(self.action, "roi_w", 200) or 200))
        self.roi_h_spin.setValue(int(getattr(self.action, "roi_h", 100) or 100))
        self.goto_step_checkbox.setChecked(bool(getattr(self.action, "goto_step_enabled", False)))
        self.goto_step_spin.setValue(int(getattr(self.action, "goto_step_index", 0) or 0))
        self.goto_step_spin.setEnabled(bool(getattr(self.action, "goto_step_enabled", False)))
        self.timeout_goto_checkbox.setChecked(bool(getattr(self.action, "timeout_goto_enabled", False)))
        self.timeout_goto_spin.setValue(int(getattr(self.action, "timeout_goto_step_index", 0) or 0))
        self.timeout_goto_spin.setEnabled(bool(getattr(self.action, "timeout_goto_enabled", False)))
        timeout_seconds = float(getattr(self.action, "timeout", 5.0) or 5.0)
        timeout_intervals = max(1, int(round(timeout_seconds / TIMEOUT_INTERVAL_SECONDS)))
        self.timeout_interval_spin.setValue(timeout_intervals)

        ocr_engine = str(getattr(self.action, "ocr_engine", "auto") or "auto")
        idx = self.ocr_engine_combo.findData(ocr_engine)
        self.ocr_engine_combo.setCurrentIndex(idx if idx >= 0 else 0)

        self.code_edit.setPlainText(str(getattr(self.action, "dynamic_ocr_code", "return False") or "return False"))
        self.code_comment_edit.setPlainText("")
        self.pattern_threshold_spin.setValue(float(getattr(self.action, "dynamic_ocr_pattern_threshold", 80.0) or 80.0))

        patterns = []
        seen_patterns: set[str] = set()

        for pattern in list(getattr(self.action, "dynamic_ocr_patterns", []) or []):
            normalized = str(pattern or "").strip()
            if normalized and normalized not in seen_patterns:
                seen_patterns.add(normalized)
                patterns.append(normalized)

        if not patterns:
            for rule in list(getattr(self.action, "dynamic_ocr_rules", []) or []):
                pattern = str(rule.get("pattern", "") or "").strip()
                if pattern and pattern not in seen_patterns:
                    seen_patterns.add(pattern)
                    patterns.append(pattern)
        for pattern in patterns:
            self._add_pattern_row(pattern)

        self._update_teaching_label()
        self._update_matching_algorithms_display()
        self._update_ocr_algorithms_display()
        self._update_comment_visibility()
        self._on_target_mode_changed(self.target_mode_combo.currentIndex())

    def get_settings(self) -> dict:
        return {
            "dynamic_ocr_target_mode": str(self.target_mode_combo.currentData() or "roi"),
            "dynamic_ocr_rules": [],
            "dynamic_ocr_patterns": self._collect_patterns(),
            "dynamic_ocr_pattern_threshold": float(self.pattern_threshold_spin.value()),
            "dynamic_ocr_code": str(self.code_edit.toPlainText() or "").strip() or "return False",
            "match_threshold": float(self.threshold_spin.value()),
            "timeout": float(self.timeout_interval_spin.value()) * TIMEOUT_INTERVAL_SECONDS,
            "check_interval": float(getattr(self.action, "check_interval", 1.0) or 1.0),
            "delay": float(getattr(self.action, "delay", 1.0) or 1.0),
            "ocr_engine": str(self.ocr_engine_combo.currentData() or "auto"),
            "ocr_bright_on_dark": bool(getattr(self.action, "ocr_bright_on_dark", False)),
            "ocr_upscale_enabled": bool(getattr(self.action, "ocr_upscale_enabled", True)),
            "ocr_upscale_factor": float(getattr(self.action, "ocr_upscale_factor", 2.0) or 2.0),
            "ocr_enhance_contrast": bool(getattr(self.action, "ocr_enhance_contrast", True)),
            "ocr_sharpen": bool(getattr(self.action, "ocr_sharpen", True)),
            "ocr_denoise": bool(getattr(self.action, "ocr_denoise", False)),
            "image_path": self.action.image_path,
            "teaching_corner_x1": getattr(self.action, "teaching_corner_x1", None),
            "teaching_corner_y1": getattr(self.action, "teaching_corner_y1", None),
            "teaching_corner_x2": getattr(self.action, "teaching_corner_x2", None),
            "teaching_corner_y2": getattr(self.action, "teaching_corner_y2", None),
            "teaching_window_width": getattr(self.action, "teaching_window_width", None),
            "teaching_window_height": getattr(self.action, "teaching_window_height", None),
            "use_fixed_roi": bool(self.use_roi_checkbox.isChecked()),
            "roi_x": int(self.roi_x_spin.value()),
            "roi_y": int(self.roi_y_spin.value()),
            "roi_w": int(self.roi_w_spin.value()),
            "roi_h": int(self.roi_h_spin.value()),
            "goto_step_enabled": bool(self.goto_step_checkbox.isChecked()),
            "goto_step_index": int(self.goto_step_spin.value()),
            "timeout_goto_enabled": bool(self.timeout_goto_checkbox.isChecked()),
            "timeout_goto_step_index": int(self.timeout_goto_spin.value()),
            "template_matching_algorithms": list(getattr(self.action, "template_matching_algorithms", []) or []),
            "ocr_algorithms": list(getattr(self.action, "ocr_algorithms", []) or []),
        }
