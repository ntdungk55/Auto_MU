"""Event Notify (Alarm/Gate) Action Settings Dialog."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QGroupBox,
    QWidget,
    QScrollArea,
    QMessageBox,
    QTimeEdit,
    QListWidget,
    QListWidgetItem,
    QCheckBox,
)
from PyQt6.QtCore import QTime, Qt

from ..logic.action_type import AutoAction


class EventNotifySettingsDialog(QDialog):
    """Dialog for configuring EVENT_NOTIFY action settings."""

    def __init__(self, action: AutoAction, parent=None):
        super().__init__(parent)
        self.action = action
        self.setWindowTitle("Cài đặt Thông báo sự kiện")
        self.setFixedSize(560, 420)

        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)

        note = QLabel(
            "Lưu ý: hãy đảm bảo giờ máy tính khớp với giờ server/game.\n"
            "Action này sẽ trả Timeout nếu thời gian hiện tại nằm ngoài các khoảng cho phép."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        # Event times group
        times_group = QGroupBox("🕒 Các mốc thời gian sự kiện (HH:MM)")
        times_layout = QVBoxLayout()

        # List widget for times
        self.times_list = QListWidget()
        self.times_list.setMinimumHeight(150)
        self.times_list.setMaximumHeight(200)
        times_layout.addWidget(self.times_list)

        # Add button
        add_row = QHBoxLayout()
        self.add_btn = QPushButton("➕ Thêm mốc")
        self.add_btn.clicked.connect(self._add_time_item)
        add_row.addWidget(self.add_btn)
        add_row.addStretch()
        times_layout.addLayout(add_row)

        times_group.setLayout(times_layout)
        layout.addWidget(times_group)

        # Prepare window group
        window_group = QGroupBox("⏱️ Khoảng thời gian chuẩn bị (giây)")
        window_layout = QVBoxLayout()

        start_row = QHBoxLayout()
        start_row.addWidget(QLabel("Bắt đầu chuẩn bị trước:"))
        self.prepare_start_spin = QSpinBox()
        self.prepare_start_spin.setMinimum(0)
        self.prepare_start_spin.setMaximum(86400)
        self.prepare_start_spin.setValue(300)
        self.prepare_start_spin.setSuffix(" s")
        self.prepare_start_spin.valueChanged.connect(self._sync_prepare_limits)
        start_row.addWidget(self.prepare_start_spin)
        start_row.addStretch()
        window_layout.addLayout(start_row)

        end_row = QHBoxLayout()
        end_row.addWidget(QLabel("Kết thúc chuẩn bị trước:"))
        self.prepare_end_spin = QSpinBox()
        self.prepare_end_spin.setMinimum(0)
        self.prepare_end_spin.setMaximum(86400)
        self.prepare_end_spin.setValue(60)
        self.prepare_end_spin.setSuffix(" s")
        self.prepare_end_spin.valueChanged.connect(self._sync_prepare_limits)
        end_row.addWidget(self.prepare_end_spin)
        end_row.addStretch()
        window_layout.addLayout(end_row)

        hint = QLabel("Ví dụ: 12:00, start=300s, end=60s ⇒ cho phép chạy 11:55–11:59")
        hint.setWordWrap(True)
        window_layout.addWidget(hint)

        window_group.setLayout(window_layout)
        layout.addWidget(window_group)

        # Delay group
        delay_group = QGroupBox("⏱️ Delay")
        delay_layout = QVBoxLayout()
        
        delay_row = QHBoxLayout()
        delay_row.addWidget(QLabel("Delay sau khi thực hiện:"))
        self.delay_spin = QSpinBox()
        self.delay_spin.setMinimum(0)
        self.delay_spin.setMaximum(10000)
        self.delay_spin.setValue(10)  # Default 1.0s (10 x 100ms)
        self.delay_spin.setSuffix(" x 100ms")
        self.delay_spin.setToolTip("Thời gian delay sau khi action chạy xong (đơn vị 100ms)")
        delay_row.addWidget(self.delay_spin)
        delay_row.addStretch()
        delay_layout.addLayout(delay_row)
        
        delay_group.setLayout(delay_layout)
        layout.addWidget(delay_group)

        layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        # Buttons
        btns = QHBoxLayout()
        btns.setContentsMargins(10, 5, 10, 10)
        btns.addStretch()
        save_btn = QPushButton("Lưu")
        save_btn.clicked.connect(self._on_save)
        cancel_btn = QPushButton("Hủy")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        main_layout.addLayout(btns)

        self.setLayout(main_layout)

    def _sync_prepare_limits(self):
        """Ensure start > end by limiting end's maximum."""
        start_v = int(self.prepare_start_spin.value())
        # end must be < start_v
        self.prepare_end_spin.setMaximum(max(0, start_v - 1))
        if self.prepare_end_spin.value() >= start_v and start_v > 0:
            self.prepare_end_spin.setValue(max(0, start_v - 1))

    def _add_time_item(self, initial_time: QTime | None = None, enabled: bool = True):
        """Add a new time item to the list with checkbox, QTimeEdit and delete button."""
        item = QListWidgetItem()
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        
        # Create widget for the item
        widget = QWidget()
        row_layout = QHBoxLayout(widget)
        row_layout.setContentsMargins(4, 2, 4, 2)
        row_layout.setSpacing(8)

        # Checkbox (before time edit)
        checkbox = QCheckBox()
        checkbox.setChecked(enabled)
        checkbox.setToolTip("Enable/disable mốc thời gian này")
        row_layout.addWidget(checkbox)

        # Time edit
        te = QTimeEdit()
        te.setDisplayFormat("HH:mm")
        # Check if initial_time is a valid QTime object
        if isinstance(initial_time, QTime) and initial_time.isValid():
            te.setTime(initial_time)
        else:
            # Default: current time + 60 seconds
            now = QTime.currentTime()
            next_min = now.addSecs(60)
            te.setTime(next_min)
        te.setToolTip("Mốc giờ xảy ra sự kiện (giờ:phút)")
        te.setEnabled(enabled)  # Gray out if disabled
        row_layout.addWidget(te)

        # Connect checkbox to time edit enable/disable
        def on_checkbox_changed(state):
            is_enabled = state == Qt.CheckState.Checked.value
            te.setEnabled(is_enabled)
        
        checkbox.stateChanged.connect(on_checkbox_changed)

        # Delete button - use a closure to capture item correctly
        rm_btn = QPushButton("🗑️ Xóa")
        rm_btn.setFixedWidth(70)
        # Create a closure that captures the item
        def make_remove_handler(item_ref):
            def handler(checked=False):
                self._remove_time_item(item_ref)
            return handler
        rm_btn.clicked.connect(make_remove_handler(item))
        row_layout.addWidget(rm_btn)

        row_layout.addStretch()
        
        # Set widget to item
        item.setSizeHint(widget.sizeHint())
        self.times_list.addItem(item)
        self.times_list.setItemWidget(item, widget)

    def _remove_time_item(self, item: QListWidgetItem):
        """Remove a time item from the list."""
        row = self.times_list.row(item)
        if row >= 0:
            self.times_list.takeItem(row)

    def _load_settings(self):
        # Load times - handle both old format (list of strings) and new format (list of dicts)
        times = list(getattr(self.action, "event_notify_times", []) or [])
        print(f"[DEBUG EventNotify] Loading settings: times={times}, count={len(times)}")
        
        if times:
            for t in times:
                try:
                    # Handle new dict format: {"time": "10:58", "enabled": true}
                    if isinstance(t, dict):
                        time_str = str(t.get("time", "")).strip()
                        enabled = bool(t.get("enabled", True))
                        print(f"[DEBUG EventNotify] Loading dict format: {time_str}, enabled={enabled}")
                    # Handle old string format: "10:58" (convert to enabled=True)
                    else:
                        time_str = str(t or "").strip()
                        enabled = True  # Default enabled for backward compatibility
                        print(f"[DEBUG EventNotify] Loading string format: {time_str}, enabled={enabled}")
                    
                    if not time_str:
                        continue
                        
                    q = QTime.fromString(time_str, "HH:mm")
                    if q.isValid():
                        print(f"[DEBUG EventNotify] Adding time item: {time_str} -> {q.toString('HH:mm')}, enabled={enabled}")
                        self._add_time_item(q, enabled)
                    else:
                        print(f"[DEBUG EventNotify] Invalid time format: {time_str}")
                except Exception as e:
                    print(f"[DEBUG EventNotify] Error loading time {t}: {e}")
                    continue
        
        print(f"[DEBUG EventNotify] After load: list count={self.times_list.count()}")

        # Load window seconds
        self.prepare_start_spin.setValue(int(getattr(self.action, "event_prepare_start_s", 300) or 300))
        self.prepare_end_spin.setValue(int(getattr(self.action, "event_prepare_end_s", 60) or 60))
        self._sync_prepare_limits()
        
        # Load delay (convert from seconds to 100ms units)
        delay_in_100ms = int((float(getattr(self.action, "delay", 1.0) or 1.0)) * 10)
        self.delay_spin.setValue(delay_in_100ms)

    def _collect_times(self) -> list[dict]:
        """Collect all times from the list widget in new dict format."""
        out: list[dict] = []
        for i in range(self.times_list.count()):
            item = self.times_list.item(i)
            if item:
                widget = self.times_list.itemWidget(item)
                if widget:
                    # Find QCheckBox and QTimeEdit in the widget
                    checkbox = widget.findChild(QCheckBox)
                    time_edit = widget.findChild(QTimeEdit)
                    
                    if checkbox is not None and time_edit is not None:
                        time_str = time_edit.time().toString("HH:mm")
                        enabled = checkbox.isChecked()
                        out.append({"time": time_str, "enabled": enabled})
        
        # De-dup while preserving order (based on time string)
        seen = set()
        dedup: list[dict] = []
        for item in out:
            time_key = item["time"]
            if time_key not in seen:
                seen.add(time_key)
                dedup.append(item)
        return dedup

    def _on_save(self):
        # Validation: must have at least 1 time item
        if self.times_list.count() == 0:
            QMessageBox.warning(
                self,
                "Cấu hình chưa hợp lệ",
                "Vui lòng thêm ít nhất 1 mốc thời gian bằng cách bấm nút '➕ Thêm mốc'."
            )
            return
        
        times = self._collect_times()
        if not times:
            QMessageBox.warning(
                self,
                "Cấu hình chưa hợp lệ",
                "Không thể đọc được mốc thời gian. Vui lòng kiểm tra lại."
            )
            return

        start_s = int(self.prepare_start_spin.value())
        end_s = int(self.prepare_end_spin.value())
        if start_s <= end_s:
            QMessageBox.warning(
                self,
                "Cấu hình chưa hợp lệ",
                "Thời gian 'bắt đầu chuẩn bị trước' phải lớn hơn 'kết thúc chuẩn bị trước'.",
            )
            return

        self.accept()

    def get_settings(self) -> dict:
        times = self._collect_times()
        settings = {
            "event_notify_times": times,
            "event_prepare_start_s": int(self.prepare_start_spin.value()),
            "event_prepare_end_s": int(self.prepare_end_spin.value()),
            "delay": self.delay_spin.value() / 10.0,  # Convert from 100ms units to seconds
        }
        print(f"[DEBUG EventNotify] Saving settings: {settings}")
        return settings

