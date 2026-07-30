from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QRadioButton, QSpinBox, QPushButton, QComboBox, QGroupBox, QButtonGroup
from ..logic.tool_manager import ToolManager


class ToolSettingsDialog(QDialog):
    """Dialog chỉnh setting chung cho toàn tool (loop + timeout behavior)."""

    def __init__(self, tool_id: str, tool_manager: ToolManager, parent=None):
        super().__init__(parent)
        self.tool_id = tool_id
        self.tool_manager = tool_manager
        
        # Load tool to get name for title
        tool = self.tool_manager.load_tool(tool_id)
        tool_name = tool.name if tool else "Unknown"
        self.setWindowTitle(f"Tool Settings - {tool_name}")
        self.setFixedSize(520, 420)
        self._loading = False
        self._init_ui()
        self._load()

    def _init_ui(self):
        # Prevent signal handlers firing while building widgets (init-order safety)
        prev_loading = bool(getattr(self, "_loading", False))
        self._loading = True
        layout = QVBoxLayout()

        self.loop_checkbox = QCheckBox("Lặp tool")
        self.loop_checkbox.toggled.connect(self._on_changed)
        layout.addWidget(self.loop_checkbox)

        mode_layout = QHBoxLayout()
        self.loop_forever_radio = QRadioButton("Lặp vĩnh viễn")
        self.loop_count_radio = QRadioButton("Lặp số lần:")
        mode_layout.addWidget(self.loop_forever_radio)
        mode_layout.addWidget(self.loop_count_radio)

        self.loop_count_spin = QSpinBox()
        self.loop_count_spin.setMinimum(1)
        self.loop_count_spin.setMaximum(999999)
        self.loop_count_spin.setValue(1)
        mode_layout.addWidget(self.loop_count_spin)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Delay trước chạy:"))
        self.loop_pre_delay_spin = QSpinBox()
        self.loop_pre_delay_spin.setMinimum(0)
        self.loop_pre_delay_spin.setMaximum(999999)
        self.loop_pre_delay_spin.setSuffix(" x 100ms")
        delay_layout.addWidget(self.loop_pre_delay_spin)

        delay_layout.addWidget(QLabel("Delay sau chạy:"))
        self.loop_post_delay_spin = QSpinBox()
        self.loop_post_delay_spin.setMinimum(0)
        self.loop_post_delay_spin.setMaximum(999999)
        self.loop_post_delay_spin.setSuffix(" x 100ms")
        delay_layout.addWidget(self.loop_post_delay_spin)
        delay_layout.addStretch()
        layout.addLayout(delay_layout)

        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Timeout:"))
        self.stop_on_timeout_checkbox = QCheckBox("Dừng tool khi timeout")
        self.restart_on_timeout_checkbox = QCheckBox("Timeout → chạy lại từ đầu")
        self.stop_on_timeout_checkbox.toggled.connect(self._on_timeout_behavior_toggled)
        self.restart_on_timeout_checkbox.toggled.connect(self._on_timeout_behavior_toggled)
        timeout_layout.addWidget(self.stop_on_timeout_checkbox)
        timeout_layout.addWidget(self.restart_on_timeout_checkbox)
        timeout_layout.addStretch()
        layout.addLayout(timeout_layout)

        # Run lock / Running dialog behavior
        lock_layout = QHBoxLayout()
        lock_layout.addWidget(QLabel("Khóa khi chạy:"))
        self.run_lock_mode_combo = QComboBox()
        self.run_lock_mode_combo.addItem("1) Không khóa (không dialog)", 0)
        self.run_lock_mode_combo.addItem("2) Chỉ hiện khi xử lý (không gồm delay)", 1)
        self.run_lock_mode_combo.addItem("3) Khóa toàn thời gian (kể cả delay)", 2)
        self.run_lock_mode_combo.currentIndexChanged.connect(self._on_changed)
        lock_layout.addWidget(self.run_lock_mode_combo)
        lock_layout.addStretch()
        layout.addLayout(lock_layout)

        # User Input Mode section
        user_input_group = QGroupBox("Khi người dùng thao tác chuột/bàn phím")
        user_input_layout = QVBoxLayout()
        user_input_layout.setSpacing(4)  # Reduce spacing between items
        user_input_layout.setContentsMargins(8, 8, 8, 8)  # Reduce margins
        
        self.user_input_button_group = QButtonGroup(self)
        
        self.user_input_ignore_radio = QRadioButton("Vẫn chạy (bỏ qua)")
        self.user_input_pause_radio = QRadioButton("Tạm dừng")
        self.user_input_stop_radio = QRadioButton("Dừng hẳn")
        
        self.user_input_button_group.addButton(self.user_input_ignore_radio, 0)
        self.user_input_button_group.addButton(self.user_input_pause_radio, 1)
        self.user_input_button_group.addButton(self.user_input_stop_radio, 2)
        
        user_input_layout.addWidget(self.user_input_ignore_radio)
        
        # Pause option with duration spinbox
        pause_layout = QHBoxLayout()
        pause_layout.setSpacing(4)  # Reduce spacing
        pause_layout.setContentsMargins(0, 0, 0, 0)
        pause_layout.addWidget(self.user_input_pause_radio)
        self.pause_duration_spin = QSpinBox()
        self.pause_duration_spin.setMinimum(1)
        self.pause_duration_spin.setMaximum(300)
        self.pause_duration_spin.setValue(5)
        self.pause_duration_spin.setSuffix(" giây")
        self.pause_duration_spin.setFixedWidth(100)
        pause_layout.addWidget(self.pause_duration_spin)
        pause_layout.addStretch()
        user_input_layout.addLayout(pause_layout)
        
        user_input_layout.addWidget(self.user_input_stop_radio)
        
        user_input_group.setLayout(user_input_layout)
        layout.addWidget(user_input_group)
        
        # Connect user input signals
        self.user_input_ignore_radio.toggled.connect(self._on_user_input_mode_changed)
        self.user_input_pause_radio.toggled.connect(self._on_user_input_mode_changed)
        self.user_input_stop_radio.toggled.connect(self._on_user_input_mode_changed)
        self.pause_duration_spin.valueChanged.connect(self._on_changed)
        
        # Telegram timeout notification
        self.notify_on_timeout_checkbox = QCheckBox("Thông báo Telegram khi timeout")
        self.notify_on_timeout_checkbox.toggled.connect(self._on_notify_checkbox_toggled)
        layout.addWidget(self.notify_on_timeout_checkbox)
        
        # Input blocking settings
        input_blocking_group = QGroupBox("Khóa input khi thực hiện action")
        input_blocking_layout = QVBoxLayout()
        input_blocking_layout.setSpacing(4)
        input_blocking_layout.setContentsMargins(8, 8, 8, 8)
        
        self.block_input_checkbox = QCheckBox("Khóa input khi thực hiện action")
        self.block_input_checkbox.toggled.connect(self._on_block_input_toggled)
        input_blocking_layout.addWidget(self.block_input_checkbox)
        
        duration_layout = QHBoxLayout()
        duration_layout.setSpacing(4)
        duration_layout.addWidget(QLabel("Thời gian khóa tối đa:"))
        self.block_input_duration_spin = QSpinBox()
        self.block_input_duration_spin.setMinimum(1)  # 0.1s in units of 0.1s
        self.block_input_duration_spin.setMaximum(100)  # 10.0s in units of 0.1s
        self.block_input_duration_spin.setValue(30)  # 3.0s default
        self.block_input_duration_spin.setSuffix(" x 0.1 giây")
        self.block_input_duration_spin.setFixedWidth(120)
        self.block_input_duration_spin.valueChanged.connect(self._on_changed)
        duration_layout.addWidget(self.block_input_duration_spin)
        duration_layout.addStretch()
        input_blocking_layout.addLayout(duration_layout)
        
        self.block_input_warning_label = QLabel("⚠️ Ấn F12 để dừng hoàn toàn")
        self.block_input_warning_label.setStyleSheet("color: orange; font-weight: bold;")
        self.block_input_warning_label.setVisible(False)
        input_blocking_layout.addWidget(self.block_input_warning_label)
        
        input_blocking_group.setLayout(input_blocking_layout)
        layout.addWidget(input_blocking_group)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Hủy")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

        # Connect signals after widgets exist (avoid init-order crash)
        self.loop_forever_radio.toggled.connect(self._on_changed)
        self.loop_count_radio.toggled.connect(self._on_changed)
        self.loop_count_spin.valueChanged.connect(self._on_changed)
        self.loop_pre_delay_spin.valueChanged.connect(self._on_changed)
        self.loop_post_delay_spin.valueChanged.connect(self._on_changed)

        # Default trong dialog: lặp theo số lần (tối thiểu 1)
        try:
            self.loop_count_radio.setChecked(True)
        except Exception:
            pass

        # Restore loading flag
        self._loading = prev_loading

    def _update_loop_ui_visibility(self):
        # Defensive: during early init, widgets may not exist yet.
        if not hasattr(self, "loop_checkbox"):
            return
        if not hasattr(self, "loop_forever_radio"):
            return
        if not hasattr(self, "loop_count_radio"):
            return
        if not hasattr(self, "loop_count_spin"):
            return
        if not hasattr(self, "loop_pre_delay_spin"):
            return
        if not hasattr(self, "loop_post_delay_spin"):
            return

        enabled = bool(self.loop_checkbox.isChecked())
        # Loop mode settings chỉ có ý nghĩa khi loop bật
        self.loop_forever_radio.setEnabled(enabled)
        self.loop_count_radio.setEnabled(enabled)
        self.loop_count_spin.setEnabled(enabled and self.loop_count_radio.isChecked())
        # Option B: delay luôn có ý nghĩa (kể cả không lặp) -> luôn enable
        self.loop_pre_delay_spin.setEnabled(True)
        self.loop_post_delay_spin.setEnabled(True)

    def _load(self):
        tool = self.tool_manager.load_tool(self.tool_id)
        if not tool:
            return
        self._loading = True
        try:
            self.loop_checkbox.setChecked(bool(getattr(tool, "loop_enabled", False)))
            mode = getattr(tool, "loop_mode", "forever")
            if mode == "count":
                self.loop_count_radio.setChecked(True)
            else:
                self.loop_forever_radio.setChecked(True)
            self.loop_count_spin.setValue(int(getattr(tool, "loop_count", 1) or 1))
            self.loop_pre_delay_spin.setValue(int(getattr(tool, "loop_pre_delay_100ms", 0) or 0))
            self.loop_post_delay_spin.setValue(int(getattr(tool, "loop_post_delay_100ms", 0) or 0))
            self.stop_on_timeout_checkbox.setChecked(bool(getattr(tool, "stop_on_timeout", True)))
            self.restart_on_timeout_checkbox.setChecked(bool(getattr(tool, "restart_on_timeout", False)))
            # run lock mode
            mode = int(getattr(tool, "run_lock_mode", 0) or 0)
            idx = self.run_lock_mode_combo.findData(mode)
            if idx >= 0:
                self.run_lock_mode_combo.setCurrentIndex(idx)
            else:
                self.run_lock_mode_combo.setCurrentIndex(0)
            
            # User input mode
            user_input_mode = str(getattr(tool, "user_input_mode", "ignore") or "ignore")
            if user_input_mode == "pause":
                self.user_input_pause_radio.setChecked(True)
            elif user_input_mode == "stop":
                self.user_input_stop_radio.setChecked(True)
            else:
                self.user_input_ignore_radio.setChecked(True)
            
            self.pause_duration_spin.setValue(int(getattr(tool, "pause_duration", 5) or 5))
            
            # Telegram timeout notification
            self.notify_on_timeout_checkbox.setChecked(bool(getattr(tool, "notify_on_timeout", False)))
            
            # Input blocking settings
            self.block_input_checkbox.setChecked(bool(getattr(tool, "block_input_enabled", False)))
            duration_value = float(getattr(tool, "block_input_duration", 3.0) or 3.0)
            # Convert to units of 0.1s (e.g., 3.0s -> 30)
            self.block_input_duration_spin.setValue(int(duration_value * 10))
            self._update_block_input_ui()
            
            self._update_loop_ui_visibility()
            self._update_user_input_ui()
        finally:
            self._loading = False

    def _save(self):
        tool = self.tool_manager.load_tool(self.tool_id)
        if not tool:
            return
        tool.loop_enabled = bool(self.loop_checkbox.isChecked())
        tool.loop_mode = "count" if self.loop_count_radio.isChecked() else "forever"
        tool.loop_count = int(self.loop_count_spin.value())
        tool.loop_pre_delay_100ms = int(self.loop_pre_delay_spin.value())
        tool.loop_post_delay_100ms = int(self.loop_post_delay_spin.value())
        tool.stop_on_timeout = bool(self.stop_on_timeout_checkbox.isChecked())
        tool.restart_on_timeout = bool(self.restart_on_timeout_checkbox.isChecked())
        if tool.restart_on_timeout:
            tool.stop_on_timeout = False
        # run lock mode
        try:
            tool.run_lock_mode = int(self.run_lock_mode_combo.currentData() or 0)
        except Exception:
            tool.run_lock_mode = 0
        
        # User input mode
        if self.user_input_pause_radio.isChecked():
            tool.user_input_mode = "pause"
        elif self.user_input_stop_radio.isChecked():
            tool.user_input_mode = "stop"
        else:
            tool.user_input_mode = "ignore"
        tool.pause_duration = int(self.pause_duration_spin.value())
        
        # Telegram timeout notification
        tool.notify_on_timeout = bool(self.notify_on_timeout_checkbox.isChecked())
        
        # Input blocking settings
        tool.block_input_enabled = bool(self.block_input_checkbox.isChecked())
        # Convert from units of 0.1s to seconds (e.g., 30 -> 3.0s)
        tool.block_input_duration = float(self.block_input_duration_spin.value()) / 10.0
        
        self.tool_manager.save_tool(tool)

    def _on_changed(self, *_args):
        if self._loading:
            return
        self._update_loop_ui_visibility()
        self._save()

    def _on_timeout_behavior_toggled(self, *_args):
        if self._loading:
            return
        if self.restart_on_timeout_checkbox.isChecked():
            self.stop_on_timeout_checkbox.setChecked(False)
        if self.stop_on_timeout_checkbox.isChecked():
            self.restart_on_timeout_checkbox.setChecked(False)
        self._save()

    def _on_user_input_mode_changed(self, *_args):
        if self._loading:
            return
        self._update_user_input_ui()
        self._save()
    
    def _update_user_input_ui(self):
        """Update user input UI based on selected mode."""
        if not hasattr(self, "pause_duration_spin"):
            return
        # Enable pause duration only when pause mode is selected
        self.pause_duration_spin.setEnabled(self.user_input_pause_radio.isChecked())
    
    def _update_block_input_ui(self):
        """Update block input UI based on checkbox state."""
        if not hasattr(self, "block_input_checkbox"):
            return
        enabled = self.block_input_checkbox.isChecked()
        self.block_input_duration_spin.setEnabled(enabled)
        self.block_input_warning_label.setVisible(enabled)
    
    def _on_block_input_toggled(self, *_args):
        """Handle block input checkbox toggle."""
        if self._loading:
            return
        self._update_block_input_ui()
        self._save()

    def _is_telegram_configured(self) -> bool:
        """Check if Telegram is configured in app_state.json.
        
        Returns:
            True if both bot_token and chat_id exist and not empty
        """
        try:
            import json
            import os
            app_state_path = os.path.join(os.path.dirname(__file__), "..", "app_state.json")
            if not os.path.exists(app_state_path):
                return False
            
            with open(app_state_path, "r", encoding="utf-8") as f:
                state = json.load(f) or {}
            
            # Check bot_token (encrypted or plain)
            has_token = bool(state.get("telegram_bot_token_dpapi_b64", "").strip() or 
                           state.get("telegram_bot_token", "").strip())
            
            # Check chat_id
            has_chat_id = bool(state.get("telegram_chat_id", "").strip())
            
            return has_token and has_chat_id
        except Exception:
            return False
    
    def _on_notify_checkbox_toggled(self, checked: bool):
        """Handle notify checkbox toggle."""
        if self._loading:
            return
        
        if checked:
            # Check if Telegram is configured
            if not self._is_telegram_configured():
                # Show message box
                from PyQt6.QtWidgets import QMessageBox
                reply = QMessageBox.question(
                    self,
                    "Telegram chưa cấu hình",
                    "Telegram chưa được cấu hình. Bạn có muốn mở cài đặt Telegram không?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # Open Telegram config dialog
                    try:
                        from .telegram_filter_dialog import TelegramConfigDialog
                        dialog = TelegramConfigDialog(parent=self)
                        dialog.exec()
                    except Exception as e:
                        QMessageBox.warning(self, "Lỗi", f"Không thể mở cài đặt Telegram: {e}")
                
                # Uncheck the checkbox
                self._loading = True
                self.notify_on_timeout_checkbox.setChecked(False)
                self._loading = False
                return
        
        # Save setting
        self._save()
