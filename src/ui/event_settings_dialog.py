"""Dialog for creating and editing registered location events."""

from __future__ import annotations

import uuid
from typing import Any

from PyQt6.QtCore import QTime
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.logic.event_catalog import MAP_CATALOG, MapDefinition


class _ConditionWidget(QGroupBox):
    """Editor for one map and optional coordinate rectangle."""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(title, parent)
        form = QFormLayout(self)
        self.map_combo = QComboBox()
        for item in MAP_CATALOG:
            self.map_combo.addItem(item.name, item)
        form.addRow("Map:", self.map_combo)
        self.coordinates = QCheckBox("Thêm điều kiện tọa độ")
        self.coordinates.toggled.connect(self._set_coordinate_enabled)
        form.addRow(self.coordinates)
        self.min_x = self._spin(); self.max_x = self._spin()
        self.min_y = self._spin(); self.max_y = self._spin()
        row_x = QHBoxLayout(); row_x.addWidget(QLabel("min_x")); row_x.addWidget(self.min_x); row_x.addWidget(QLabel("max_x")); row_x.addWidget(self.max_x)
        row_y = QHBoxLayout(); row_y.addWidget(QLabel("min_y")); row_y.addWidget(self.min_y); row_y.addWidget(QLabel("max_y")); row_y.addWidget(self.max_y)
        form.addRow(row_x); form.addRow(row_y)
        self._set_coordinate_enabled(False)

    @staticmethod
    def _spin() -> QSpinBox:
        spin = QSpinBox(); spin.setRange(-100000, 100000)
        return spin

    def _set_coordinate_enabled(self, enabled: bool) -> None:
        for widget in (self.min_x, self.max_x, self.min_y, self.max_y):
            widget.setEnabled(enabled)

    def set_value(self, value: dict[str, Any] | None) -> None:
        if not isinstance(value, dict):
            return
        map_id = int(value.get("map_id", 0) or 0)
        index = next((i for i in range(self.map_combo.count()) if int(self.map_combo.itemData(i).id) == map_id), -1)
        if index >= 0:
            self.map_combo.setCurrentIndex(index)
        self.coordinates.setChecked(bool(value.get("use_coordinates", False)))
        for widget, key in ((self.min_x, "min_x"), (self.max_x, "max_x"), (self.min_y, "min_y"), (self.max_y, "max_y")):
            if value.get(key) is not None:
                widget.setValue(int(value[key]))

    def value(self) -> dict[str, Any]:
        map_value: MapDefinition = self.map_combo.currentData()
        return {
            "map_id": map_value.id,
            "map_name": map_value.name,
            "use_coordinates": self.coordinates.isChecked(),
            "min_x": self.min_x.value() if self.coordinates.isChecked() else None,
            "max_x": self.max_x.value() if self.coordinates.isChecked() else None,
            "min_y": self.min_y.value() if self.coordinates.isChecked() else None,
            "max_y": self.max_y.value() if self.coordinates.isChecked() else None,
        }


class EventSettingsDialog(QDialog):
    """Create or edit one registered event."""

    def __init__(self, event: dict[str, Any] | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Thêm/Sửa event")
        self.resize(560, 620)
        self._event = dict(event or {})
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit(str(self._event.get("name", "")))
        self.prompt_edit = QTextEdit(str(self._event.get("prompt", "")))
        self.prompt_edit.setMinimumHeight(70)
        self.enabled = QCheckBox(); self.enabled.setChecked(bool(self._event.get("enabled", True)))
        form.addRow("Tên event:", self.name_edit); form.addRow("Prompt:", self.prompt_edit); form.addRow("Enabled:", self.enabled)
        layout.addLayout(form)
        self.tabs = QTabWidget(); location_tab = QWidget(); location_layout = QVBoxLayout(location_tab)
        trigger_row = QHBoxLayout(); trigger_row.addWidget(QLabel("Phát event khi:"))
        self.trigger = QComboBox(); self.trigger.addItem("Đi vào", "enter"); self.trigger.addItem("Đi ra", "exit"); self.trigger.addItem("Đi từ nguồn tới đích", "source_to_destination")
        self.trigger.currentIndexChanged.connect(self._toggle_source)
        trigger_row.addWidget(self.trigger); location_layout.addLayout(trigger_row)
        self.source = _ConditionWidget("Source"); self.destination = _ConditionWidget("Destination")
        location_layout.addWidget(self.source); location_layout.addWidget(self.destination)
        self.tabs.addTab(location_tab, "Location Observer"); layout.addWidget(self.tabs)
        health_tab = QWidget(); health_form = QFormLayout(health_tab)
        self.health_threshold = QSpinBox(); self.health_threshold.setRange(0, 2_000_000); self.health_threshold.setValue(100)
        health_form.addRow("Phát khi HP dưới:", self.health_threshold)
        health_form.addRow(QLabel("Đọc từ Window State / healthBar. Chỉ phát một lần khi vừa xuống dưới ngưỡng."))
        self.tabs.addTab(health_tab, "Health Observer")
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save)
        buttons.accepted.connect(self._save); buttons.rejected.connect(self.reject); layout.addWidget(buttons)
        self._load_event(); self._toggle_source()

    def _load_event(self) -> None:
        observer_type = str(self._event.get("observer_type", "location"))
        self.tabs.setCurrentIndex(1 if observer_type == "health" else 0)
        if observer_type == "health":
            self.health_threshold.setValue(int(self._event.get("health_threshold", 100) or 0))
        mode = str(self._event.get("trigger_mode", "enter"))
        index = self.trigger.findData(mode)
        if index >= 0: self.trigger.setCurrentIndex(index)
        self.source.set_value(self._event.get("source")); self.destination.set_value(self._event.get("destination"))

    def _toggle_source(self) -> None:
        self.source.setVisible(self.trigger.currentData() == "source_to_destination")

    def _save(self) -> None:
        name = self.name_edit.text().strip(); prompt = self.prompt_edit.toPlainText().strip()
        if not name:
            QMessageBox.warning(self, "Dữ liệu không hợp lệ", "Tên event không được để trống.")
            return
        destination = self.destination.value(); source = self.source.value() if self.trigger.currentData() == "source_to_destination" else None
        for label, value in (("destination", destination), ("source", source)):
            if value is None: continue
            if value["use_coordinates"] and (value["min_x"] > value["max_x"] or value["min_y"] > value["max_y"]):
                QMessageBox.warning(self, "Dữ liệu không hợp lệ", f"Vùng tọa độ {label} không hợp lệ.")
                return
        self.accept()

    def get_event(self) -> dict[str, Any]:
        """Return the validated event configuration."""
        observer_type = "health" if self.tabs.currentIndex() == 1 else "location"
        return {
            "event_id": str(self._event.get("event_id") or uuid.uuid4().hex),
            "name": self.name_edit.text().strip(), "prompt": self.prompt_edit.toPlainText().strip(),
            "enabled": self.enabled.isChecked(), "observer_type": observer_type,
            "trigger_mode": self.trigger.currentData() if observer_type == "location" else "health_below",
            "source": self.source.value() if observer_type == "location" and self.trigger.currentData() == "source_to_destination" else None,
            "destination": self.destination.value() if observer_type == "location" else None,
            "health_threshold": self.health_threshold.value(),
        }
