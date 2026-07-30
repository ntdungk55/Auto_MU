"""Keyboard Action Settings Dialog."""

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QDialog,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..logic.action_type import AutoAction


class KeyboardSettingsDialog(QDialog):
    """Dialog for configuring KEYBOARD action settings."""

    VALID_KEYS = (
        [""]
        + ["tab", "esc", "enter", "space", "backspace", "delete", "insert"]
        + ["home", "end", "page up", "page down", "pageup", "pagedown"]
        + ["up", "down", "left", "right"]
        + ["shift", "ctrl", "alt", "caps lock", "num lock", "scroll lock"]
        + ["print screen", "pause", "menu", "windows"]
        + [f"f{i}" for i in range(1, 13)]
        + [chr(c) for c in range(ord("a"), ord("z") + 1)]
        + [str(i) for i in range(0, 10)]
    )

    def __init__(self, action: AutoAction, parent=None):
        super().__init__(parent)
        self.action = action
        self.teaching_corners = None
        self.setWindowTitle("Cài đặt Keyboard Action")
        self.setFixedSize(560, 460)
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

        layout.addWidget(QLabel("Phím nhấn:"))
        self.key_input = self._build_key_input()
        layout.addWidget(self.key_input)

        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Delay sau khi thực hiện:"))
        self.delay_spin = QSpinBox()
        self.delay_spin.setMinimum(0)
        self.delay_spin.setMaximum(10000)
        self.delay_spin.setValue(10)
        self.delay_spin.setSuffix(" x 100ms")
        delay_layout.addWidget(self.delay_spin)
        delay_layout.addStretch()
        layout.addLayout(delay_layout)

        goto_layout = QHBoxLayout()
        self.goto_step_checkbox = QCheckBox("🔄 Khi thành công, nhảy về step:")
        self.goto_step_checkbox.stateChanged.connect(self._on_goto_step_changed)
        goto_layout.addWidget(self.goto_step_checkbox)
        self.goto_step_spin = QSpinBox()
        self.goto_step_spin.setMinimum(0)
        self.goto_step_spin.setMaximum(100)
        self.goto_step_spin.setValue(1)
        self.goto_step_spin.setEnabled(False)
        self.goto_step_spin.setToolTip("0 = Restart cycle từ đầu, 1-N = nhảy về step cụ thể")
        goto_layout.addWidget(self.goto_step_spin)
        goto_layout.addStretch()
        layout.addLayout(goto_layout)

        self.post_key_group = QGroupBox("Kiểm tra kết quả sau khi ấn phím")
        post_key_layout = QVBoxLayout()

        self.post_key_checkbox = QCheckBox("Bật chế độ ấn phím rồi chờ teaching image xuất hiện")
        self.post_key_checkbox.stateChanged.connect(self._on_post_key_check_changed)
        post_key_layout.addWidget(self.post_key_checkbox)

        self.post_key_detail_widget = QWidget()
        detail_layout = QVBoxLayout(self.post_key_detail_widget)
        detail_layout.setContentsMargins(0, 0, 0, 0)

        self.image_path_label = QLabel("Chưa chọn ảnh")
        self.image_path_label.setWordWrap(True)
        detail_layout.addWidget(self.image_path_label)

        image_btn_row = QHBoxLayout()
        self.image_btn = QPushButton("Tạo ảnh Teaching")
        self.image_btn.clicked.connect(self._capture_teaching_image)
        image_btn_row.addWidget(self.image_btn)
        image_btn_row.addStretch()
        detail_layout.addLayout(image_btn_row)

        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Match threshold:"))
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setMinimum(0.10)
        self.threshold_spin.setMaximum(0.99)
        self.threshold_spin.setSingleStep(0.01)
        self.threshold_spin.setDecimals(2)
        self.threshold_spin.setValue(0.40)
        threshold_layout.addWidget(self.threshold_spin)
        threshold_layout.addStretch()
        detail_layout.addLayout(threshold_layout)

        check_delay_layout = QHBoxLayout()
        check_delay_layout.addWidget(QLabel("Delay trước khi check ảnh:"))
        self.post_key_check_delay_spin = QDoubleSpinBox()
        self.post_key_check_delay_spin.setMinimum(0.1)
        self.post_key_check_delay_spin.setMaximum(30.0)
        self.post_key_check_delay_spin.setSingleStep(0.1)
        self.post_key_check_delay_spin.setDecimals(1)
        self.post_key_check_delay_spin.setValue(1.0)
        self.post_key_check_delay_spin.setSuffix(" giây")
        check_delay_layout.addWidget(self.post_key_check_delay_spin)
        check_delay_layout.addStretch()
        detail_layout.addLayout(check_delay_layout)

        retry_layout = QHBoxLayout()
        retry_layout.addWidget(QLabel("Số lần retry bấm lại phím:"))
        self.post_key_retry_spin = QSpinBox()
        self.post_key_retry_spin.setMinimum(0)
        self.post_key_retry_spin.setMaximum(20)
        self.post_key_retry_spin.setValue(0)
        retry_layout.addWidget(self.post_key_retry_spin)
        retry_layout.addStretch()
        detail_layout.addLayout(retry_layout)

        post_key_layout.addWidget(self.post_key_detail_widget)
        self.post_key_group.setLayout(post_key_layout)
        layout.addWidget(self.post_key_group)

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

    def _build_key_input(self) -> QComboBox:
        cb = QComboBox()
        cb.setEditable(True)
        cb.setMaxVisibleItems(20)
        cb.addItems(list(self.VALID_KEYS))
        cb.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        try:
            cb.lineEdit().setPlaceholderText("Gõ để tìm (vd: tab, esc, ctrl+tab...)")
        except Exception:
            pass

        completer = QCompleter(list(self.VALID_KEYS))
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        try:
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
        except Exception:
            pass
        cb.setCompleter(completer)
        return cb

    def _capture_teaching_image(self):
        parent_dialog = self.parent()
        if not hasattr(parent_dialog, "target_window_hwnd") or not parent_dialog.target_window_hwnd:
            QMessageBox.warning(self, "Cảnh báo", "Chưa chọn window game ở màn hình chính!")
            return

        from .image_capture_dialog import ImageCaptureDialog

        dialog = ImageCaptureDialog(
            parent_dialog.target_window_hwnd,
            parent=self,
            tool_id=getattr(parent_dialog, "tool_id", None),
            hide_click_selection=True,
            hide_region_selection=False,
            initial_image_path=getattr(self.action, "image_path", None),
        )
        if dialog.exec():
            result = dialog.get_cropped_image_path()
            if len(result) == 9:
                image_path, _, _, corner_x1, corner_y1, corner_x2, corner_y2, window_width, window_height = result
            elif len(result) == 7:
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
                if corner_x1 is not None:
                    self.teaching_corners = (corner_x1, corner_y1, corner_x2, corner_y2)
                    self.action.teaching_corner_x1 = corner_x1
                    self.action.teaching_corner_y1 = corner_y1
                    self.action.teaching_corner_x2 = corner_x2
                    self.action.teaching_corner_y2 = corner_y2
                if window_width is not None and window_height is not None:
                    self.action.teaching_window_width = window_width
                    self.action.teaching_window_height = window_height
                self._update_image_button_text()

    def _update_image_button_text(self):
        has_teaching = False
        if self.action.image_path and os.path.exists(self.action.image_path):
            has_teaching = True
        elif self.teaching_corners and len(self.teaching_corners) == 4:
            has_teaching = True
        self.image_btn.setText("Xem/Sửa ảnh Teaching" if has_teaching else "Tạo ảnh Teaching")

    def _load_settings(self):
        try:
            self.key_input.setCurrentText(str(getattr(self.action, "value", "") or ""))
        except Exception:
            pass

        self.delay_spin.setValue(int(self.action.delay * 10))
        self.goto_step_checkbox.setChecked(bool(getattr(self.action, "goto_step_enabled", False)))
        self.goto_step_spin.setValue(int(getattr(self.action, "goto_step_index", 0) or 0))
        self.goto_step_spin.setEnabled(bool(getattr(self.action, "goto_step_enabled", False)))

        self.post_key_checkbox.setChecked(bool(getattr(self.action, "enable_post_key_image_check", False)))
        self.post_key_check_delay_spin.setValue(float(getattr(self.action, "post_key_check_delay", 1.0) or 1.0))
        self.post_key_retry_spin.setValue(int(getattr(self.action, "post_key_retry_count", 0) or 0))
        try:
            thr = float(getattr(self.action, "match_threshold", 0.4))
            self.threshold_spin.setValue(max(0.10, min(0.99, thr)))
        except Exception:
            pass

        if self.action.image_path:
            filename = os.path.basename(self.action.image_path)
            self.image_path_label.setText(f"Đã chọn: {filename}")

        try:
            x1 = getattr(self.action, "teaching_corner_x1", None)
            y1 = getattr(self.action, "teaching_corner_y1", None)
            x2 = getattr(self.action, "teaching_corner_x2", None)
            y2 = getattr(self.action, "teaching_corner_y2", None)
            if all(v is not None for v in [x1, y1, x2, y2]):
                self.teaching_corners = (x1, y1, x2, y2)
        except Exception:
            pass

        self._update_image_button_text()
        self._on_post_key_check_changed(self.post_key_checkbox.checkState())

    def _on_goto_step_changed(self, state):
        self.goto_step_spin.setEnabled(bool(state))

    def _on_post_key_check_changed(self, state):
        self.post_key_detail_widget.setEnabled(bool(state))

    def get_settings(self) -> dict:
        teaching_x1 = None
        teaching_y1 = None
        teaching_x2 = None
        teaching_y2 = None
        if self.teaching_corners and len(self.teaching_corners) == 4:
            teaching_x1, teaching_y1, teaching_x2, teaching_y2 = self.teaching_corners

        return {
            "value": str(self.key_input.currentText() or "").strip(),
            "delay": self.delay_spin.value() / 10.0,
            "goto_step_enabled": bool(self.goto_step_checkbox.isChecked()),
            "goto_step_index": int(self.goto_step_spin.value()),
            "enable_post_key_image_check": bool(self.post_key_checkbox.isChecked()),
            "post_key_check_delay": float(self.post_key_check_delay_spin.value()),
            "post_key_retry_count": int(self.post_key_retry_spin.value()),
            "match_threshold": float(self.threshold_spin.value()),
            "image_path": self.action.image_path,
            "teaching_corner_x1": teaching_x1,
            "teaching_corner_y1": teaching_y1,
            "teaching_corner_x2": teaching_x2,
            "teaching_corner_y2": teaching_y2,
            "teaching_window_width": getattr(self.action, "teaching_window_width", None),
            "teaching_window_height": getattr(self.action, "teaching_window_height", None),
        }
