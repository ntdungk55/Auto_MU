from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QComboBox, QPushButton, QFileDialog,
                             QGroupBox, QMessageBox, QSpinBox, QWidget, QCheckBox,
                             QScrollArea, QApplication, QCompleter, QDoubleSpinBox, QTextEdit)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from ..logic.action_type import ActionType, ActionMode, AutoAction
from .image_capture_dialog import ImageCaptureDialog
import os
import shutil
import json

from ..logic.dpapi import protect_to_b64, unprotect_from_b64

class ActionConfigDialog(QDialog):
    # Danh sách "valid input" để gợi ý + dropdown cho action Ấn Phím
    # (keyboard lib chấp nhận các chuỗi dạng: "tab", "esc", "ctrl+tab", ...)
    VALID_KEYS = (
        [""]  # cho phép rỗng -> user mở dropdown để chọn
        + ["tab", "esc", "enter", "space", "backspace", "delete", "insert"]
        + ["home", "end", "page up", "page down", "pageup", "pagedown"]
        + ["up", "down", "left", "right"]
        + ["shift", "ctrl", "alt", "caps lock", "num lock", "scroll lock"]
        + ["print screen", "pause", "menu", "windows"]
        + [f"f{i}" for i in range(1, 13)]
        + [chr(c) for c in range(ord("a"), ord("z") + 1)]
        + [str(i) for i in range(0, 10)]
    )

    def _build_key_input(self) -> QComboBox:
        """Editable dropdown + autocomplete (gợi ý phím hợp lệ)."""
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
        # Prefer env (current run)
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

    def __init__(self, action: AutoAction = None, parent=None, target_window_hwnd=None, restrict_action_type=None, tool_id: str = None):
        super().__init__(parent)
        # QUAN TRỌNG: Gán restrict_action_type NGAY LẬP TỨC, trước mọi thứ khác
        # Đảm bảo thuộc tính này luôn tồn tại trước khi init_ui() được gọi
        self.restrict_action_type = restrict_action_type if restrict_action_type is not None else None
        self.target_window_hwnd = target_window_hwnd
        self.tool_id = tool_id  # UUID of the tool
        # Guard để tránh signal của combobox overwrite dữ liệu action khi dialog vừa mở
        self._loading_action_data = True
        
        try:
            if action:
                import copy
                self.action = copy.deepcopy(action)
            else:
                self.action = AutoAction(
                    name="", purpose="", action_type=ActionType.KEYBOARD, 
                    mode=ActionMode.ACTIVE, value=""
                )
        except Exception as e:
            # Nếu có lỗi khi tạo action, vẫn tạo action mặc định
            self.action = AutoAction(
                name="", purpose="", action_type=ActionType.KEYBOARD, 
                mode=ActionMode.ACTIVE, value=""
            )
            print(f"[WARNING] Error creating action: {e}")
        
        self.setWindowTitle("Cấu hình Action")
        self.setFixedSize(500, 250)  # Giảm chiều cao vì không còn options
        self.init_ui()  # init_ui() sẽ đọc self.restrict_action_type
        self.load_action_data()
        self._loading_action_data = False
    
    def init_ui(self):
        # Đảm bảo restrict_action_type đã được gán (double check)
        if not hasattr(self, 'restrict_action_type'):
            self.restrict_action_type = None
        
        # Layout chính (không cần scroll nữa vì dialog nhỏ)
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Tên action
        layout.addWidget(QLabel("Nhập tên:"))
        self.name_input = QLineEdit()
        layout.addWidget(self.name_input)
        
        # Mục đích
        layout.addWidget(QLabel("Mục đích:"))
        self.purpose_input = QLineEdit()
        layout.addWidget(self.purpose_input)
        
        # Loại hành động + Settings button
        layout.addWidget(QLabel("Loại hành động:"))
        action_type_row = QHBoxLayout()
        self.action_type_combo = QComboBox()
        if self.restrict_action_type:
            # Chỉ cho phép chọn action type được chỉ định
            self.action_type_combo.addItem(self.restrict_action_type.value)
            self.action_type_combo.setEnabled(False)  # Khóa combo box
        else:
            self.action_type_combo.addItems([t.value for t in ActionType])
        action_type_row.addWidget(self.action_type_combo)
        
        # Settings button
        self.settings_btn = QPushButton("⚙️ Cài đặt")
        self.settings_btn.clicked.connect(self._open_action_settings)
        self.settings_btn.setFixedWidth(100)
        action_type_row.addWidget(self.settings_btn)
        
        # Test button
        self.test_btn = QPushButton("▶ Test")
        self.test_btn.setToolTip("Chạy thử action này")
        self.test_btn.clicked.connect(self._test_action)
        self.test_btn.setFixedWidth(70)
        action_type_row.addWidget(self.test_btn)
        
        action_type_row.addStretch()
        layout.addLayout(action_type_row)
        
        # Spacer để đẩy buttons xuống dưới
        layout.addStretch()
        
        # Nút OK/Cancel
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Hủy")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def _open_action_settings(self):
        """Open action-specific settings dialog."""
        action_type = next(t for t in ActionType if t.value == self.action_type_combo.currentText())
        
        if action_type == ActionType.KEYBOARD:
            from .keyboard_settings_dialog import KeyboardSettingsDialog
            dlg = KeyboardSettingsDialog(self.action, self)
            if dlg.exec():
                settings = dlg.get_settings()
                self.action.value = settings["value"]
                self.action.delay = settings["delay"]
                self.action.goto_step_enabled = settings["goto_step_enabled"]
                self.action.goto_step_index = settings["goto_step_index"]
                self.action.enable_post_key_image_check = settings["enable_post_key_image_check"]
                self.action.post_key_check_delay = settings["post_key_check_delay"]
                self.action.post_key_retry_count = settings["post_key_retry_count"]
                self.action.match_threshold = settings["match_threshold"]
                self.action.image_path = settings["image_path"]
                self.action.teaching_corner_x1 = settings["teaching_corner_x1"]
                self.action.teaching_corner_y1 = settings["teaching_corner_y1"]
                self.action.teaching_corner_x2 = settings["teaching_corner_x2"]
                self.action.teaching_corner_y2 = settings["teaching_corner_y2"]
                self.action.teaching_window_width = settings["teaching_window_width"]
                self.action.teaching_window_height = settings["teaching_window_height"]
        elif action_type == ActionType.MOUSE_CLICK:
            from .mouse_click_settings_dialog import MouseClickSettingsDialog
            dlg = MouseClickSettingsDialog(self.action, self, target_window_hwnd=self.target_window_hwnd, tool_id=self.tool_id)
            if dlg.exec():
                settings = dlg.get_settings()
                # Click mode settings
                self.action.click_by_coordinate = settings["click_by_coordinate"]
                self.action.coordinate_click_pos = settings["coordinate_click_pos"]
                # Image mode settings
                self.action.match_threshold = settings["match_threshold"]
                self.action.multiscale_enabled = settings["multiscale_enabled"]
                self.action.multiscale_min = settings["multiscale_min"]
                self.action.multiscale_max = settings["multiscale_max"]
                self.action.multiscale_step = settings["multiscale_step"]
                self.action.timeout = settings["timeout"]
                self.action.check_interval = settings["check_interval"]
                self.action.continue_on_timeout = settings["continue_on_timeout"]
                self.action.alt_click = settings["alt_click"]
                self.action.delay = settings["delay"]
                self.action.image_path = settings["image_path"]
                self.action.click_x = settings["click_x"]
                self.action.click_y = settings["click_y"]
                self.action.teaching_corner_x1 = settings["teaching_corner_x1"]
                self.action.teaching_corner_y1 = settings["teaching_corner_y1"]
                self.action.teaching_corner_x2 = settings["teaching_corner_x2"]
                self.action.teaching_corner_y2 = settings["teaching_corner_y2"]
                self.action.teaching_window_width = settings["teaching_window_width"]
                self.action.teaching_window_height = settings["teaching_window_height"]
                self.action.enable_post_click_image_check = settings["enable_post_click_image_check"]
                self.action.post_click_check_delay = settings["post_click_check_delay"]
                self.action.post_click_retry_count = settings["post_click_retry_count"]
                self.action.post_click_image_path = settings["post_click_image_path"]
                self.action.post_click_match_threshold = settings["post_click_match_threshold"]
                self.action.post_click_teaching_corner_x1 = settings["post_click_teaching_corner_x1"]
                self.action.post_click_teaching_corner_y1 = settings["post_click_teaching_corner_y1"]
                self.action.post_click_teaching_corner_x2 = settings["post_click_teaching_corner_x2"]
                self.action.post_click_teaching_corner_y2 = settings["post_click_teaching_corner_y2"]
                self.action.post_click_teaching_window_width = settings["post_click_teaching_window_width"]
                self.action.post_click_teaching_window_height = settings["post_click_teaching_window_height"]
                self.action.goto_step_enabled = settings["goto_step_enabled"]
                self.action.goto_step_index = settings["goto_step_index"]
                self.action.timeout_goto_enabled = settings["timeout_goto_enabled"]
                self.action.timeout_goto_step_index = settings["timeout_goto_step_index"]
        elif action_type == ActionType.IMAGE_DETECT:
            from .image_detect_settings_dialog import ImageDetectSettingsDialog
            dlg = ImageDetectSettingsDialog(self.action, self, target_window_hwnd=self.target_window_hwnd, tool_id=self.tool_id)
            if dlg.exec():
                settings = dlg.get_settings()
                self.action.match_threshold = settings["match_threshold"]
                self.action.multiscale_enabled = settings["multiscale_enabled"]
                self.action.multiscale_min = settings["multiscale_min"]
                self.action.multiscale_max = settings["multiscale_max"]
                self.action.multiscale_step = settings["multiscale_step"]
                self.action.timeout = settings["timeout"]
                self.action.check_interval = settings["check_interval"]
                self.action.continue_on_timeout = settings["continue_on_timeout"]
                self.action.delay = settings["delay"]
                self.action.read_data = settings["read_data"]
                self.action.ocr_engine = settings["ocr_engine"]
                self.action.ocr_bright_on_dark = settings["ocr_bright_on_dark"]
                self.action.ocr_upscale_enabled = settings["ocr_upscale_enabled"]
                self.action.ocr_upscale_factor = settings["ocr_upscale_factor"]
                self.action.ocr_enhance_contrast = settings["ocr_enhance_contrast"]
                self.action.ocr_sharpen = settings["ocr_sharpen"]
                self.action.ocr_denoise = settings["ocr_denoise"]
                self.action.gemini_enabled = settings["gemini_enabled"]
                self.action.gemini_timeout = settings["gemini_timeout"]
                self.action.notification_enabled = settings["notification_enabled"]
                self.action.notification_filter_keywords = settings["notification_filter_keywords"]
                self.action.notification_dedup_minutes = settings["notification_dedup_minutes"]
                self.action.image_path = settings["image_path"]
                self.action.teaching_corner_x1 = settings["teaching_corner_x1"]
                self.action.teaching_corner_y1 = settings["teaching_corner_y1"]
                self.action.teaching_corner_x2 = settings["teaching_corner_x2"]
                self.action.teaching_corner_y2 = settings["teaching_corner_y2"]
                self.action.goto_step_enabled = settings["goto_step_enabled"]
                self.action.goto_step_index = settings["goto_step_index"]
                self.action.timeout_goto_enabled = settings["timeout_goto_enabled"]
                self.action.timeout_goto_step_index = settings["timeout_goto_step_index"]
        elif action_type == ActionType.DYNAMIC_OCR_CONDITION:
            from .dynamic_ocr_condition_settings_dialog import DynamicOCRConditionSettingsDialog
            dlg = DynamicOCRConditionSettingsDialog(self.action, self, target_window_hwnd=self.target_window_hwnd, tool_id=self.tool_id)
            if dlg.exec():
                settings = dlg.get_settings()
                self.action.dynamic_ocr_target_mode = settings["dynamic_ocr_target_mode"]
                self.action.dynamic_ocr_rules = settings["dynamic_ocr_rules"]
                self.action.dynamic_ocr_patterns = settings["dynamic_ocr_patterns"]
                self.action.dynamic_ocr_rules = []
                self.action.dynamic_ocr_pattern_threshold = settings["dynamic_ocr_pattern_threshold"]
                self.action.dynamic_ocr_code = settings["dynamic_ocr_code"]
                self.action.match_threshold = settings["match_threshold"]
                self.action.timeout = settings["timeout"]
                self.action.check_interval = settings["check_interval"]
                self.action.ocr_engine = settings["ocr_engine"]
                self.action.image_path = settings["image_path"]
                self.action.teaching_corner_x1 = settings["teaching_corner_x1"]
                self.action.teaching_corner_y1 = settings["teaching_corner_y1"]
                self.action.teaching_corner_x2 = settings["teaching_corner_x2"]
                self.action.teaching_corner_y2 = settings["teaching_corner_y2"]
                self.action.teaching_window_width = settings["teaching_window_width"]
                self.action.teaching_window_height = settings["teaching_window_height"]
                self.action.use_fixed_roi = settings["use_fixed_roi"]
                self.action.roi_x = settings["roi_x"]
                self.action.roi_y = settings["roi_y"]
                self.action.roi_w = settings["roi_w"]
                self.action.roi_h = settings["roi_h"]
                self.action.goto_step_enabled = settings["goto_step_enabled"]
                self.action.goto_step_index = settings["goto_step_index"]
                self.action.timeout_goto_enabled = settings["timeout_goto_enabled"]
                self.action.timeout_goto_step_index = settings["timeout_goto_step_index"]
                self.action.template_matching_algorithms = settings["template_matching_algorithms"]
                self.action.ocr_algorithms = settings["ocr_algorithms"]
        elif action_type == ActionType.READ_PASSIVE:
            from .passive_read_settings_dialog import PassiveReadSettingsDialog
            dlg = PassiveReadSettingsDialog(self.action, self, target_window_hwnd=self.target_window_hwnd, tool_id=self.tool_id)
            if dlg.exec():
                settings = dlg.get_settings()
                print(f"[DEBUG] READ_PASSIVE settings: image_path={settings.get('image_path')}")
                self.action.passive_mode = settings["passive_mode"]
                self.action.passive_detect_timeout = settings["passive_detect_timeout"]
                self.action.passive_detect_threshold = settings["passive_detect_threshold"]
                self.action.continue_on_timeout = settings["continue_on_timeout"]
                self.action.passive_sample_every = settings["passive_sample_every"]
                self.action.passive_only_new_frame = settings["passive_only_new_frame"]
                self.action.passive_cancel_old = settings["passive_cancel_old"]
                self.action.passive_keywords = settings["passive_keywords"]
                self.action.use_fixed_roi = settings["use_fixed_roi"]
                self.action.roi_x = settings["roi_x"]
                self.action.roi_y = settings["roi_y"]
                self.action.roi_w = settings["roi_w"]
                self.action.roi_h = settings["roi_h"]
                self.action.ocr_engine = settings["ocr_engine"]
                self.action.ocr_bright_on_dark = settings["ocr_bright_on_dark"]
                self.action.ocr_upscale_enabled = settings["ocr_upscale_enabled"]
                self.action.ocr_upscale_factor = settings["ocr_upscale_factor"]
                self.action.ocr_enhance_contrast = settings["ocr_enhance_contrast"]
                self.action.ocr_sharpen = settings["ocr_sharpen"]
                self.action.ocr_denoise = settings["ocr_denoise"]
                self.action.gemini_enabled = settings["gemini_enabled"]
                self.action.gemini_timeout = settings["gemini_timeout"]
                self.action.notification_enabled = settings["notification_enabled"]
                self.action.notification_filter_keywords = settings["notification_filter_keywords"]
                self.action.notification_dedup_minutes = settings["notification_dedup_minutes"]
                self.action.goto_step_enabled = settings["goto_step_enabled"]
                self.action.goto_step_index = settings["goto_step_index"]
                self.action.image_path = settings["image_path"]
                self.action.teaching_corner_x1 = settings["teaching_corner_x1"]
                self.action.teaching_corner_y1 = settings["teaching_corner_y1"]
                self.action.teaching_corner_x2 = settings["teaching_corner_x2"]
                self.action.teaching_corner_y2 = settings["teaching_corner_y2"]
                self.action.ocr_algorithms = settings.get("ocr_algorithms", [])
                self.action.event_ocr_pattern = settings.get("event_ocr_pattern", "")
                self.action.event_match_threshold = settings.get("event_match_threshold", 100.0)
                self.action.event_ocr_engine = settings.get("event_ocr_engine", "auto")
                self.action.event_reappear_timeout_minutes = settings.get("event_reappear_timeout_minutes", 15)
                self.action.imperial_guardian_enabled = settings.get("imperial_guardian_enabled", False)
                self.action.imperial_guardian_no_player_alert_delay = settings.get("imperial_guardian_no_player_alert_delay", 10)
                self.action.imperial_guardian_teaching_corner_x1 = settings.get("imperial_guardian_teaching_corner_x1", 0)
                self.action.imperial_guardian_teaching_corner_y1 = settings.get("imperial_guardian_teaching_corner_y1", 0)
                self.action.imperial_guardian_teaching_corner_x2 = settings.get("imperial_guardian_teaching_corner_x2", 0)
                self.action.imperial_guardian_teaching_corner_y2 = settings.get("imperial_guardian_teaching_corner_y2", 0)
                self.action.imperial_guardian_ocr_engine = settings.get("imperial_guardian_ocr_engine", "auto")
                self.action.imperial_guardian_match_threshold = settings.get("imperial_guardian_match_threshold", 70.0)
                self.action.imperial_guardian_ocr_algorithms = settings.get("imperial_guardian_ocr_algorithms", [])
                self.action.imperial_guardian_teaching_image_path = settings.get("imperial_guardian_teaching_image_path", "")
                # Golden Invasion
                self.action.golden_invasion_enabled = settings.get("golden_invasion_enabled", False)
                self.action.golden_invasion_server_time = settings.get("golden_invasion_server_time", "01:30")
                self.action.golden_invasion_channel_roi_x1 = settings.get("golden_invasion_channel_roi_x1", 0)
                self.action.golden_invasion_channel_roi_y1 = settings.get("golden_invasion_channel_roi_y1", 0)
                self.action.golden_invasion_channel_roi_x2 = settings.get("golden_invasion_channel_roi_x2", 0)
                self.action.golden_invasion_channel_roi_y2 = settings.get("golden_invasion_channel_roi_y2", 0)
                self.action.golden_invasion_channel_ocr_engine = settings.get("golden_invasion_channel_ocr_engine", "auto")
                self.action.golden_invasion_channel_ocr_algorithms = settings.get("golden_invasion_channel_ocr_algorithms", [])
                self.action.golden_invasion_channel_teaching_image_path = settings.get("golden_invasion_channel_teaching_image_path", "")
                self.action.golden_invasion_notify_roi_x1 = settings.get("golden_invasion_notify_roi_x1", 0)
                self.action.golden_invasion_notify_roi_y1 = settings.get("golden_invasion_notify_roi_y1", 0)
                self.action.golden_invasion_notify_roi_x2 = settings.get("golden_invasion_notify_roi_x2", 0)
                self.action.golden_invasion_notify_roi_y2 = settings.get("golden_invasion_notify_roi_y2", 0)
                self.action.golden_invasion_notify_ocr_engine = settings.get("golden_invasion_notify_ocr_engine", "auto")
                self.action.golden_invasion_notify_ocr_algorithms = settings.get("golden_invasion_notify_ocr_algorithms", [])
                self.action.golden_invasion_notify_teaching_image_path = settings.get("golden_invasion_notify_teaching_image_path", "")
                self.action.golden_invasion_match_threshold = settings.get("golden_invasion_match_threshold", 70.0)
                for key in (
                    "monster_invasion_enabled",
                    "monster_invasion_channel_roi_x1",
                    "monster_invasion_channel_roi_y1",
                    "monster_invasion_channel_roi_x2",
                    "monster_invasion_channel_roi_y2",
                    "monster_invasion_channel_ocr_engine",
                    "monster_invasion_channel_ocr_algorithms",
                    "monster_invasion_channel_teaching_image_path",
                    "monster_invasion_notify_roi_x1",
                    "monster_invasion_notify_roi_y1",
                    "monster_invasion_notify_roi_x2",
                    "monster_invasion_notify_roi_y2",
                    "monster_invasion_notify_ocr_engine",
                    "monster_invasion_notify_ocr_algorithms",
                    "monster_invasion_notify_teaching_image_path",
                    "monster_invasion_match_threshold",
                    "monster_invasion_golden_invasion_enabled",
                    "monster_invasion_golden_invasion_server_time",
                    "monster_invasion_white_wizard_red_dragon_enabled",
                ):
                    if key in settings:
                        setattr(self.action, key, settings[key])
                print(f"[DEBUG] After save: self.action.image_path={self.action.image_path}")
        elif action_type == ActionType.EVENT_NOTIFY:
            from .event_notify_settings_dialog import EventNotifySettingsDialog
            dlg = EventNotifySettingsDialog(self.action, self)
            if dlg.exec():
                settings = dlg.get_settings()
                print(f"[DEBUG ActionConfig] Saving EVENT_NOTIFY settings: {settings}")
                self.action.event_notify_times = settings["event_notify_times"]
                self.action.event_prepare_start_s = settings["event_prepare_start_s"]
                self.action.event_prepare_end_s = settings["event_prepare_end_s"]
                self.action.delay = settings["delay"]
                print(f"[DEBUG ActionConfig] After save: action.event_notify_times={self.action.event_notify_times}, delay={self.action.delay}")
        elif action_type == ActionType.WAIT:
            from .wait_settings_dialog import WaitSettingsDialog
            dlg = WaitSettingsDialog(self.action, self)
            if dlg.exec():
                settings = dlg.get_settings()
                self.action.timeout = settings["timeout"]
    
    def load_action_data(self):
        """Load action data into dialog fields."""
        if self.action:
            self.name_input.setText(self.action.name)
            self.purpose_input.setText(self.action.purpose)
            
            action_text = self.action.action_type.value
            index = self.action_type_combo.findText(action_text)
            if index >= 0:
                self.action_type_combo.setCurrentIndex(index)
    
    def accept(self):
        """Override accept to save action data before closing dialog."""
        try:
            self.get_action()
            super().accept()
        except Exception as e:
            print(f"[ERROR] Failed to save action: {e}")
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu action: {e}")
    
    def get_action(self) -> AutoAction:
        self.action.name = self.name_input.text()
        self.action.purpose = self.purpose_input.text()
        # Always keep mode as ACTIVE for backward compatibility, but logic ignores it.
        self.action.mode = ActionMode.ACTIVE
        
        action_text = self.action_type_combo.currentText()
        self.action.action_type = next(t for t in ActionType if t.value == action_text)
        
        # Copy Imperial Guardian teaching image path if it exists
        if hasattr(self.action, 'imperial_guardian_teaching_image_path'):
            self.action.imperial_guardian_teaching_image_path = getattr(self.action, 'imperial_guardian_teaching_image_path', '')
        
        return self.action

    def _test_action(self):
        """Test the current action."""
        import threading
        import time
        
        # Check if window is selected
        if not self.target_window_hwnd:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn window game trước khi test!")
            return
        
        # Get current action state
        action = self.get_action()
        
        # Console logging when test starts
        print(f"\n{'='*60}")
        print(f"🚀 ACTION CONFIG DIALOG - TEST STARTED")
        print(f"{'='*60}")
        print(f"🎯 Action: {action.name}")
        print(f"📝 Purpose: {action.purpose}")
        print(f"📊 Type: {action.action_type.value}")
        print(f"🖼️  Target Window: {hex(self.target_window_hwnd) if self.target_window_hwnd else 'None'}")
        
        # Log OCR settings if applicable
        if hasattr(action, 'ocr_engine') or hasattr(action, 'imperial_guardian_enabled'):
            print(f"🔍 OCR Configuration:")
            if hasattr(action, 'ocr_engine'):
                print(f"    Generic OCR Engine: {getattr(action, 'ocr_engine', 'auto')}")
            if hasattr(action, 'imperial_guardian_enabled') and action.imperial_guardian_enabled:
                print(f"    Imperial Guardian: ✅ ENABLED")
                print(f"        Engine: {getattr(action, 'imperial_guardian_ocr_engine', 'auto')}")
                print(f"        Match Threshold: {getattr(action, 'imperial_guardian_match_threshold', 70.0)}%")
                print(f"        Algorithms: {len(getattr(action, 'imperial_guardian_ocr_algorithms', []))}")
            else:
                print(f"    Imperial Guardian: ❌ DISABLED")
        
        print(f"{'='*60}\n")
        
        # Disable test button during test
        self.test_btn.setEnabled(False)
        self.test_btn.setText("Testing...")
        
        def run_test():
            logs = []  # Collect logs
            
            def log_collector(msg: str):
                """Collect logs from SystemExecutor."""
                logs.append(msg)
            
            try:
                from ..logic.system_executor import SystemExecutor
                from ..logic.window_detector import WindowDetector
                
                # Focus game window
                try:
                    detector = WindowDetector()
                    detector.set_foreground_window(self.target_window_hwnd)
                    time.sleep(0.2)
                except Exception:
                    pass
                
                # Create executor with log collector
                executor = SystemExecutor(
                    target_window_hwnd=self.target_window_hwnd,
                    ui_log_func=log_collector
                )
                
                start_time = time.perf_counter()
                
                # Execute based on action type
                try:
                    if action.action_type.value == "Ấn Phím" or action.action_type.value == "Chờ":
                        success = executor.execute(action)
                    elif action.action_type.value == "Thông báo sự kiện":
                        # EVENT_NOTIFY: direct execute, no timeout loop
                        success = executor.execute(action)
                    else:
                        timeout = float(getattr(action, "timeout", 30.0) or 30.0)
                        success = executor.execute_with_timeout(action, timeout=timeout)
                except Exception as exec_err:
                    import traceback
                    error_trace = traceback.format_exc()
                    print(f"[Test Action] ERROR executing action: {exec_err}")
                    print(f"[Test Action] TRACEBACK:\n{error_trace}")
                    success = False
                
                elapsed = (time.perf_counter() - start_time) * 1000
                
                # Build result message with logs
                log_text = "\n".join(logs) if logs else "(Không có log)"
                
                # Show result in main thread using QTimer.singleShot
                if success:
                    msg = f"✅ Test thành công! ({elapsed:.0f}ms)\n\n{log_text}"
                    QTimer.singleShot(0, lambda: self._show_test_result(msg, True))
                else:
                    msg = f"❌ Test thất bại! ({elapsed:.0f}ms)\n\n{log_text}"
                    QTimer.singleShot(0, lambda: self._show_test_result(msg, False))
                    
            except Exception as e:
                msg = f"Lỗi test: {e}"
                QTimer.singleShot(0, lambda: self._show_test_result(msg, False))
            finally:
                # Re-enable button in main thread
                QTimer.singleShot(0, lambda: self._reset_test_button())
        
        thread = threading.Thread(target=run_test, daemon=True)
        thread.start()

    def _reset_test_button(self):
        """Reset test button state (called from main thread)."""
        self.test_btn.setEnabled(True)
        self.test_btn.setText("▶ Test")

    def _show_test_result(self, msg: str, success: bool):
        """Show test result in message box (called from main thread)."""
        # Strip HTML tags for plain text display
        import re
        plain_msg = re.sub(r'<[^>]+>', '', msg)  # Remove HTML tags
        plain_msg = plain_msg.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')  # Unescape HTML entities
        
        if success:
            QMessageBox.information(self, "Test Result", plain_msg)
        else:
            QMessageBox.warning(self, "Test Result", plain_msg)

