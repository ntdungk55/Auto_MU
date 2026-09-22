"""Management window for registered event observers."""

from __future__ import annotations

from typing import Any, Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout,
)

from src.ui.event_settings_dialog import EventSettingsDialog


class EventManagementDialog(QDialog):
    """List, edit, enable, and delete registered events."""

    def __init__(self, events: list[dict[str, Any]], on_changed: Callable[[list[dict[str, Any]]], None], status_getter: Callable[[str], str] | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Danh sách đăng ký event")
        self.resize(900, 420)
        self.events = [dict(item) for item in events]
        self._on_changed = on_changed
        self._status_getter = status_getter
        layout = QVBoxLayout(self)
        buttons = QHBoxLayout(); add = QPushButton("Tạo thêm event"); delete = QPushButton("Xóa event")
        add.clicked.connect(self._new); delete.clicked.connect(self._delete); buttons.addWidget(add); buttons.addWidget(delete); buttons.addStretch(1); layout.addLayout(buttons)
        self.table = QTableWidget(0, 5); self.table.setHorizontalHeaderLabels(["Enabled", "Tên event", "Prompt", "Observer", "Status"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows); self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.cellDoubleClicked.connect(self._edit); self.table.itemChanged.connect(self._prompt_changed); layout.addWidget(self.table)
        self._refresh()

    def _refresh(self) -> None:
        current = self.table.currentRow(); self.table.blockSignals(True); self.table.setRowCount(0)
        for row, event in enumerate(self.events):
            self.table.insertRow(row); event_id = str(event.get("event_id", ""))
            enabled = QCheckBox(); enabled.setChecked(bool(event.get("enabled", True))); enabled.toggled.connect(lambda value, eid=event_id: self._set_enabled(eid, value)); self.table.setCellWidget(row, 0, enabled)
            name = QTableWidgetItem(str(event.get("name", ""))); name.setData(Qt.ItemDataRole.UserRole, event_id); name.setFlags(name.flags() & ~Qt.ItemFlag.ItemIsEditable); self.table.setItem(row, 1, name)
            prompt = QTableWidgetItem(str(event.get("prompt", ""))); prompt.setData(Qt.ItemDataRole.UserRole, event_id); self.table.setItem(row, 2, prompt)
            observer = QTableWidgetItem("Location Observer"); observer.setFlags(observer.flags() & ~Qt.ItemFlag.ItemIsEditable); self.table.setItem(row, 3, observer)
            status = self._status_getter(event_id) if self._status_getter else ("Enabled" if event.get("enabled", True) else "Disabled"); status_item = QTableWidgetItem(status); status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable); self.table.setItem(row, 4, status_item)
        self.table.blockSignals(False)
        if self.events and current >= 0: self.table.selectRow(min(current, len(self.events) - 1))

    def _new(self) -> None:
        dialog = EventSettingsDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            event = dialog.get_event()
            if self._duplicate_name(event["name"]): QMessageBox.warning(self, "Tên bị trùng", "Tên event không phân biệt hoa thường và phải là duy nhất."); return
            self.events.append(event); self._commit()

    def _edit(self, row: int, _column: int) -> None:
        event_id = self._event_id(row)
        event = next((item for item in self.events if item.get("event_id") == event_id), None)
        if event is None: return
        dialog = EventSettingsDialog(event, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated = dialog.get_event()
            if self._duplicate_name(updated["name"], exclude_id=event_id): QMessageBox.warning(self, "Tên bị trùng", "Tên event không phân biệt hoa thường và phải là duy nhất."); return
            index = self.events.index(event); self.events[index] = updated; self._commit()

    def _delete(self) -> None:
        row = self.table.currentRow()
        if row < 0: return
        event_id = self._event_id(row); event = next(item for item in self.events if item.get("event_id") == event_id)
        answer = QMessageBox.question(self, "Xóa event", f"Xóa event '{event.get('name', '')}'?")
        if answer == QMessageBox.StandardButton.Yes:
            self.events = [item for item in self.events if item.get("event_id") != event_id]; self._commit()

    def _prompt_changed(self, item: QTableWidgetItem) -> None:
        if item.column() != 2: return
        event_id = item.data(Qt.ItemDataRole.UserRole); event = next((value for value in self.events if value.get("event_id") == event_id), None)
        if event is None: return
        prompt = item.text().strip()
        if not prompt:
            QMessageBox.warning(self, "Prompt không hợp lệ", "Prompt không được để trống."); self._refresh(); return
        event["prompt"] = prompt; self._commit()

    def _set_enabled(self, event_id: str, enabled: bool) -> None:
        event = next((value for value in self.events if value.get("event_id") == event_id), None)
        if event is not None: event["enabled"] = enabled; self._commit()

    def _event_id(self, row: int) -> str:
        item = self.table.item(row, 1); return str(item.data(Qt.ItemDataRole.UserRole)) if item else ""

    def _duplicate_name(self, name: str, exclude_id: str | None = None) -> bool:
        folded = name.casefold(); return any(str(item.get("name", "")).casefold() == folded and item.get("event_id") != exclude_id for item in self.events)

    def _commit(self) -> None:
        self._on_changed([dict(item) for item in self.events]); self._refresh()
