"""Real-time original-window preview for the Window States used by one AI Chat tab."""

from __future__ import annotations

import base64
import json
import threading
from typing import Any, Callable

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRectF
from PyQt6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PyQt6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from .image_capture_dialog import ImageCaptureDialog


STATE_NAMES = (
    "map",
    "position",
    "healthBar",
    "autoState",
    "autoPlayManagement",
    "companionTraining",
)

STATE_COLORS = (
    QColor("#22d3ee"),
    QColor("#f59e0b"),
    QColor("#ef4444"),
    QColor("#a78bfa"),
    QColor("#22c55e"),
    QColor("#f472b6"),
)

PREVIEW_MARGIN = 12


class WindowStateMonitorWorker(QThread):
    """Poll the existing MCP Window State service without running OCR again."""

    snapshot_ready = pyqtSignal(object)
    request_failed = pyqtSignal(str)

    def __init__(self, tool_client: Any, enabled_states: set[str], parent=None) -> None:
        super().__init__(parent)
        self._tool_client = tool_client
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._enabled_states = set(enabled_states)
        self._configuration_dirty = True

    def set_enabled_states(self, enabled_states: set[str]) -> None:
        with self._lock:
            self._enabled_states = set(enabled_states)
            self._configuration_dirty = True

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                with self._lock:
                    enabled_states = set(self._enabled_states)
                    configure = self._configuration_dirty
                    self._configuration_dirty = False
                if configure:
                    self._tool_client.call_tool(
                        "configure_window_states",
                        {"enabled_states": [name for name in STATE_NAMES if name in enabled_states]},
                        timeout_seconds=4.0,
                    )
                if self._stop_event.is_set():
                    break
                payload = self._tool_client.call_tool(
                    "get_window_state_monitor_snapshot",
                    {},
                    timeout_seconds=4.0,
                )
                self.snapshot_ready.emit(payload)
            except Exception as error:
                self.request_failed.emit(str(error))
            self._stop_event.wait(0.75)


class WindowStateCanvas(QWidget):
    """Paint the original capture with active ROI and mask overlays."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._image = QImage()
        self._states: list[dict[str, Any]] = []
        self.setMinimumSize(640, 480)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_snapshot(self, payload: dict[str, Any]) -> None:
        encoded = str(payload.get("image_jpeg_base64") or "")
        if encoded:
            try:
                image = QImage.fromData(base64.b64decode(encoded), "JPG")
                if not image.isNull():
                    self._image = image
            except (TypeError, ValueError):
                pass
        states = payload.get("states")
        self._states = list(states) if isinstance(states, list) else []
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#09090b"))
        if self._image.isNull():
            painter.setPen(QColor("#a1a1aa"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Đang chờ ảnh Window State…")
            return

        image_rect = self._target_image_rect()
        painter.drawImage(image_rect, self._image)
        frame_pen = QPen(QColor("#3f3f46"), 1)
        frame_pen.setCosmetic(True)
        painter.setPen(frame_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(image_rect)
        scale_x = image_rect.width() / max(1, self._image.width())
        scale_y = image_rect.height() / max(1, self._image.height())

        font = QFont(painter.font())
        font.setPixelSize(10)
        painter.setFont(font)
        for index, state in enumerate(self._states):
            if not bool(state.get("enabled")):
                continue
            color = STATE_COLORS[index % len(STATE_COLORS)]
            roi = self._rectangle(state.get("roi"))
            if roi is None:
                continue
            roi_rect = self._scaled_rect(roi, image_rect, scale_x, scale_y)
            pen = QPen(color, 2)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(roi_rect)

            for mask in state.get("masks") or []:
                mask_values = self._rectangle(mask)
                if mask_values is None:
                    continue
                mask_rect = self._scaled_rect(mask_values, image_rect, scale_x, scale_y)
                mask_color = QColor(color)
                mask_color.setAlpha(75)
                painter.fillRect(mask_rect, mask_color)
                painter.drawRect(mask_rect)

            label = self._result_label(state)
            if label:
                self._draw_roi_label(painter, roi_rect, label, color)

    def _target_image_rect(self) -> QRectF:
        margin = float(PREVIEW_MARGIN)
        width = max(1.0, float(self.width()) - margin * 2.0)
        height = max(1.0, float(self.height()) - margin * 2.0)
        image_ratio = self._image.width() / max(1, self._image.height())
        if width / max(1.0, height) > image_ratio:
            draw_height = height
            draw_width = draw_height * image_ratio
        else:
            draw_width = width
            draw_height = draw_width / image_ratio
        return QRectF(
            margin + (width - draw_width) / 2.0,
            margin + (height - draw_height) / 2.0,
            draw_width,
            draw_height,
        )

    @staticmethod
    def _rectangle(value: Any) -> tuple[float, float, float, float] | None:
        if not isinstance(value, dict):
            return None
        try:
            if all(key in value for key in ("x1", "y1", "x2", "y2")):
                x1, y1, x2, y2 = (float(value[key]) for key in ("x1", "y1", "x2", "y2"))
            else:
                x1 = float(value["x"])
                y1 = float(value["y"])
                x2 = x1 + float(value["w"])
                y2 = y1 + float(value["h"])
        except (KeyError, TypeError, ValueError):
            return None
        return (x1, y1, x2, y2) if x2 > x1 and y2 > y1 else None

    @staticmethod
    def _scaled_rect(
        values: tuple[float, float, float, float],
        image_rect: QRectF,
        scale_x: float,
        scale_y: float,
    ) -> QRectF:
        x1, y1, x2, y2 = values
        return QRectF(
            image_rect.left() + x1 * scale_x,
            image_rect.top() + y1 * scale_y,
            (x2 - x1) * scale_x,
            (y2 - y1) * scale_y,
        )

    @staticmethod
    def _format_result(value: Any) -> str:
        if isinstance(value, dict):
            if "x" in value and "y" in value:
                return f"{value['x']},{value['y']}"
            if "current" in value:
                return str(value["current"])
            return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return "" if value is None else str(value).strip()

    @classmethod
    def _result_label(cls, state: dict[str, Any]) -> str:
        result = cls._format_result(state.get("result")) or "-"
        confidence = state.get("confidence")
        try:
            confidence_text = f"{float(confidence):.3f}"
        except (TypeError, ValueError):
            confidence_text = "-"
        return f"{state.get('name', 'ROI')}: {result} - {confidence_text}"

    @staticmethod
    def _draw_roi_label(painter: QPainter, roi_rect: QRectF, text: str, color: QColor) -> None:
        metrics = painter.fontMetrics()
        padding = 3
        width = metrics.horizontalAdvance(text) + padding * 2
        height = metrics.height() + 2
        left = roi_rect.left()
        top = max(0.0, roi_rect.top() - height)
        background = QRectF(left, top, width, height)
        fill = QColor("#09090b")
        fill.setAlpha(215)
        painter.fillRect(background, fill)
        painter.setPen(color)
        painter.drawText(
            background.adjusted(padding, 0, -padding, 0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            text,
        )


class WindowStateMonitorDialog(QDialog):
    """Per-chat monitor and runtime state switcher."""

    enabled_states_changed = pyqtSignal(object)

    def __init__(
        self,
        *,
        tool_client: Any,
        target_title: str,
        target_window_hwnd: int | None = None,
        enabled_states: set[str],
        on_enabled_states_changed: Callable[[set[str]], None] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Window State — {target_title}")
        self.resize(1000, 760)
        self.setMinimumSize(760, 580)
        self._enabled_states = set(enabled_states)
        self._target_window_hwnd = target_window_hwnd
        self._state_buttons: dict[str, QPushButton] = {}
        self._on_enabled_states_changed = on_enabled_states_changed

        layout = QVBoxLayout(self)

        control_panel = QGroupBox("Control panel")
        control_layout = QHBoxLayout(control_panel)
        capture_btn = QPushButton("Chụp teaching")
        capture_btn.clicked.connect(self._open_teaching_capture)
        control_layout.addWidget(capture_btn)
        control_layout.addStretch(1)
        layout.addWidget(control_panel)

        self.canvas = WindowStateCanvas()
        layout.addWidget(self.canvas, 1)

        cards_scroll = QScrollArea()
        cards_scroll.setWidgetResizable(True)
        cards_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        cards_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cards_scroll.setFixedHeight(64)
        cards_container = QWidget()
        cards_layout = QHBoxLayout(cards_container)
        cards_layout.setContentsMargins(4, 4, 4, 4)
        cards_layout.setSpacing(6)
        for name in STATE_NAMES:
            button = QPushButton(name)
            button.setCheckable(True)
            button.setChecked(name in self._enabled_states)
            button.clicked.connect(lambda checked, state_name=name: self._toggle_state(state_name, checked))
            self._state_buttons[name] = button
            cards_layout.addWidget(button)
            self._refresh_state_button(name)
        cards_layout.addStretch(1)
        cards_scroll.setWidget(cards_container)
        layout.addWidget(cards_scroll)

        self._worker = WindowStateMonitorWorker(tool_client, self._enabled_states, self)
        self._worker.snapshot_ready.connect(self._on_snapshot)
        self._worker.start()

    def _open_teaching_capture(self) -> None:
        if not self._target_window_hwnd:
            QMessageBox.warning(self, "Chụp teaching", "Chưa có cửa sổ game được chọn.")
            return
        dialog = ImageCaptureDialog(
            target_window_hwnd=self._target_window_hwnd,
            parent=self,
            hide_click_selection=True,
            manual_save=True,
        )
        dialog.exec()

    def _toggle_state(self, name: str, enabled: bool) -> None:
        if enabled:
            self._enabled_states.add(name)
        else:
            self._enabled_states.discard(name)
        self._refresh_state_button(name)
        self._worker.set_enabled_states(self._enabled_states)
        current = set(self._enabled_states)
        self.enabled_states_changed.emit(current)
        if self._on_enabled_states_changed is not None:
            self._on_enabled_states_changed(current)

    def _refresh_state_button(self, name: str) -> None:
        button = self._state_buttons[name]
        if button.isChecked():
            button.setStyleSheet(
                "QPushButton{background:#166534;color:#dcfce7;border:1px solid #22c55e;"
                "border-radius:8px;padding:7px 11px;font-weight:600;}"
                "QPushButton:hover{background:#15803d;}"
            )
        else:
            button.setStyleSheet(
                "QPushButton{background:#3f3f46;color:#a1a1aa;border:1px solid #52525b;"
                "border-radius:8px;padding:7px 11px;}"
                "QPushButton:hover{background:#52525b;color:#e4e4e7;}"
            )

    def _on_snapshot(self, payload: object) -> None:
        if not isinstance(payload, dict):
            self._on_error("Window State trả về dữ liệu không hợp lệ")
            return
        if payload.get("image_jpeg_base64"):
            self.canvas.set_snapshot(payload)

    def closeEvent(self, event) -> None:
        self._worker.stop()
        self._worker.wait(5500)
        super().closeEvent(event)
