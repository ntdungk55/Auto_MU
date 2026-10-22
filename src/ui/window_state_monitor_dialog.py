"""Real-time original-window preview for the Window States used by one AI Chat tab."""

from __future__ import annotations

import base64
import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRectF
from PyQt6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QFileDialog,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from .image_capture_dialog import ImageCaptureDialog, YoloAnnotationDialog
from .yolo_settings_dialog import YoloSettingsDialog
from ..logic.app_paths import get_app_state_path, get_learning_root, get_runtime_root
from ..logic.vision.yolo import YoloDetector
from ..logic.vision.yolo.exceptions import YoloError
from ..logic.vision.yolo.training import (
    nameplate_model_needs_training,
    prepare_nameplate_dataset,
    train_nameplate_model,
)


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


def _default_yolo_settings() -> dict[str, Any]:
    return {
        "source_folder": get_learning_root(),
        "model_path": "",
        "confidence": 0.25,
        "iou": 0.45,
    }


def _load_yolo_settings() -> dict[str, Any]:
    settings = _default_yolo_settings()
    try:
        with open(get_app_state_path(), "r", encoding="utf-8") as handle:
            state = json.load(handle) or {}
        saved = state.get("window_state_yolo_settings", {})
        if isinstance(saved, dict):
            settings.update({
                "source_folder": str(saved.get("source_folder") or settings["source_folder"]),
                "model_path": str(saved.get("model_path") or ""),
                "confidence": float(saved.get("confidence", settings["confidence"])),
                "iou": float(saved.get("iou", settings["iou"])),
            })
    except (OSError, TypeError, ValueError):
        pass
    return settings


def _save_yolo_settings(settings: dict[str, Any]) -> None:
    try:
        path = get_app_state_path()
        try:
            with open(path, "r", encoding="utf-8") as handle:
                state = json.load(handle) or {}
        except (OSError, TypeError, ValueError):
            state = {}
        state["window_state_yolo_settings"] = {
            "source_folder": str(settings.get("source_folder") or get_learning_root()),
            "model_path": str(settings.get("model_path") or ""),
            "confidence": float(settings.get("confidence", 0.25)),
            "iou": float(settings.get("iou", 0.45)),
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
    except (OSError, TypeError, ValueError):
        pass


class WindowStateMonitorWorker(QThread):
    """Poll the existing MCP Window State service without running OCR again."""

    snapshot_ready = pyqtSignal(object)
    request_failed = pyqtSignal(str)
    yolo_log = pyqtSignal(str)

    def __init__(self, tool_client: Any, enabled_states: set[str], parent=None) -> None:
        super().__init__(parent)
        self._tool_client = tool_client
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._enabled_states = set(enabled_states)
        self._configuration_dirty = True
        self._yolo_enabled = False
        self._yolo_source_folder = ""
        self._yolo_model_path = ""
        self._yolo_confidence = 0.25
        self._yolo_iou = 0.45
        self._yolo_detector: YoloDetector | None = None
        self._yolo_cached_source_key = ""
        self._yolo_cached_detections = []
        self._yolo_cached_debug = {}
        self._yolo_training_attempted_key = ""

    def set_enabled_states(self, enabled_states: set[str]) -> None:
        with self._lock:
            self._enabled_states = set(enabled_states)
            self._configuration_dirty = True

    def set_yolo_config(
        self,
        enabled: bool,
        source_folder: str,
        model_path: str,
        confidence: float,
        iou: float,
    ) -> None:
        with self._lock:
            changed = (
                self._yolo_enabled != bool(enabled)
                or self._yolo_source_folder != str(source_folder or "")
                or self._yolo_model_path != str(model_path or "")
                or self._yolo_confidence != float(confidence)
                or self._yolo_iou != float(iou)
            )
            self._yolo_enabled = bool(enabled)
            self._yolo_source_folder = str(source_folder or "")
            self._yolo_model_path = str(model_path or "")
            self._yolo_confidence = float(confidence)
            self._yolo_iou = float(iou)
            if changed:
                self._yolo_detector = None
                self._yolo_cached_source_key = ""
                self._yolo_cached_detections = []
                self._yolo_cached_debug = {}
                self._yolo_training_attempted_key = ""
                self._log(
                    "config changed: enabled=%s source=%s model=%s confidence=%.2f iou=%.2f"
                    % (
                        self._yolo_enabled,
                        self._yolo_source_folder or "window-state",
                        self._yolo_model_path or "default",
                        self._yolo_confidence,
                        self._yolo_iou,
                    )
                )

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
                self._ensure_nameplate_model()
                if self._stop_event.is_set():
                    break
                payload = self._tool_client.call_tool(
                    "get_window_state_monitor_snapshot",
                    {},
                    timeout_seconds=4.0,
                )
                payload = self._run_yolo(payload)
                self.snapshot_ready.emit(payload)
            except Exception as error:
                self.request_failed.emit(str(error))
            self._stop_event.wait(0.75)

    def _ensure_nameplate_model(self) -> None:
        with self._lock:
            enabled = self._yolo_enabled
            source_folder = self._yolo_source_folder
            model_path = self._yolo_model_path
        if not enabled or model_path:
            return
        source_root = source_folder or get_learning_root()
        if not nameplate_model_needs_training(source_root):
            return
        try:
            newest = max(
                (path.stat().st_mtime_ns for path in Path(source_root).rglob("*") if path.is_file()),
                default=0,
            )
            attempt_key = f"{source_root}|{newest}"
            if attempt_key == self._yolo_training_attempted_key:
                return
            self._yolo_training_attempted_key = attempt_key
            self._log("training started: nameplate model missing or outdated")
            dataset_root = os.path.join(get_runtime_root(), "datasets", "nameplate")
            prepare_nameplate_dataset(source_root, dataset_root, self._log)
            model_path = train_nameplate_model(dataset_root, progress=self._log)
            with self._lock:
                self._yolo_detector = None
            self._log(f"training completed: model={model_path}")
        except Exception as error:
            self._log(f"training error: {type(error).__name__}: {error}")

    def _run_yolo(self, payload: object) -> object:
        with self._lock:
            enabled = self._yolo_enabled
            source_folder = self._yolo_source_folder
            model_path = self._yolo_model_path
            confidence = self._yolo_confidence
            iou = self._yolo_iou
            detector = self._yolo_detector
        if not enabled or not isinstance(payload, dict):
            return payload

        encoded = str(payload.get("image_jpeg_base64") or "")
        if not encoded:
            payload["yolo_error"] = "Window State chưa có ảnh nguồn"
            self._log("error: Window State payload has no image")
            return payload
        try:
            image_bytes = np.frombuffer(base64.b64decode(encoded), dtype=np.uint8)
            preview_image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
            if preview_image is None:
                raise YoloError("Không giải mã được ảnh Window State")
            source_result = self._load_source_image(source_folder)
            if source_result is None:
                source_image = preview_image
                source_image_path = "window-state snapshot"
                source_key = "window-state"
            else:
                source_image, source_image_path = source_result
                source_key = source_image_path
            if detector is None:
                detector = YoloDetector(model_path=model_path or None)
                with self._lock:
                    self._yolo_detector = detector
            source_key = self._source_image_key(source_image_path, source_key)
            cache_hit = source_key != "window-state" and source_key == self._yolo_cached_source_key
            if cache_hit:
                detections = self._yolo_cached_detections
                debug = self._yolo_cached_debug
            else:
                detections = detector.detect(source_image, confidence=confidence, iou=iou)
                debug = dict(detector.last_debug)
                self._yolo_cached_source_key = source_key
                self._yolo_cached_detections = detections
                self._yolo_cached_debug = debug
            source_h, source_w = source_image.shape[:2]
            preview_h, preview_w = preview_image.shape[:2]
            scale_x = preview_w / max(1, source_w)
            scale_y = preview_h / max(1, source_h)
            payload["yolo_detections"] = [
                {
                    "class_id": item.class_id,
                    "class_name": item.class_name,
                    "confidence": item.confidence,
                    "x1": item.x1 * scale_x,
                    "y1": item.y1 * scale_y,
                    "x2": item.x2 * scale_x,
                    "y2": item.y2 * scale_y,
                }
                for item in detections
            ]
            payload["yolo_error"] = ""
            if not cache_hit:
                self._log(
                    "inference ok: source_folder=%s source_image=%s model=%s "
                    "raw_candidates=%d max_confidence=%.3f threshold=%.3f "
                    "candidates_after_threshold=%d detections=%d"
                    % (
                        source_folder or "window-state",
                        source_image_path,
                        model_path or "nameplate-default",
                        int(debug.get("raw_candidates", 0)),
                        float(debug.get("max_confidence", 0.0)),
                        float(debug.get("threshold", confidence)),
                        int(debug.get("candidates_after_threshold", 0)),
                        len(detections),
                    )
                )
                for item in detections:
                    self._log(
                        "detection class_id=%d class=%s confidence=%.3f box=(%d,%d,%d,%d)"
                        % (
                            item.class_id,
                            item.class_name or "unknown",
                            item.confidence,
                            item.x1,
                            item.y1,
                            item.x2,
                            item.y2,
                        )
                    )
        except YoloError as error:
            payload["yolo_detections"] = []
            payload["yolo_error"] = str(error)
            self._log(f"inference error: {error}")
        except Exception as error:
            payload["yolo_detections"] = []
            payload["yolo_error"] = f"{type(error).__name__}: {error}"
            self._log(f"unexpected error: {type(error).__name__}: {error}")
        return payload

    def _log(self, message: str) -> None:
        line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [YOLO] {message}"
        try:
            log_dir = os.path.join(get_runtime_root(), "logs")
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, "yolo_runtime.log"), "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError:
            pass
        print(line)
        self.yolo_log.emit(line)

    @staticmethod
    def _load_source_image(folder: str) -> tuple[np.ndarray, str] | None:
        if not folder or not os.path.isdir(folder):
            return None
        candidates = [
            path for path in Path(folder).rglob("*")
            if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
        ]
        if not candidates:
            return None
        latest = max(candidates, key=lambda path: path.stat().st_mtime)
        data = np.fromfile(str(latest), dtype=np.uint8)
        image = cv2.imdecode(data, cv2.IMREAD_COLOR)
        return (image, str(latest)) if image is not None else None

    @staticmethod
    def _source_image_key(path: str, fallback: str) -> str:
        if fallback == "window-state":
            return fallback
        try:
            stat = os.stat(path)
            return f"{path}|{stat.st_mtime_ns}|{stat.st_size}"
        except OSError:
            return path


class WindowStateCanvas(QWidget):
    """Paint the original capture with active ROI and mask overlays."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._image = QImage()
        self._states: list[dict[str, Any]] = []
        self._yolo_detections: list[dict[str, Any]] = []
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
        detections = payload.get("yolo_detections")
        self._yolo_detections = list(detections) if isinstance(detections, list) else []
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

        for detection in self._yolo_detections:
            box = self._rectangle(detection)
            if box is None:
                continue
            rect = self._scaled_rect(box, image_rect, scale_x, scale_y)
            color = QColor("#34d399")
            pen = QPen(color, 2)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)
            name = str(detection.get("class_name") or detection.get("class_id", "object"))
            try:
                score = f"{float(detection.get('confidence')):.3f}"
            except (TypeError, ValueError):
                score = "-"
            self._draw_roi_label(painter, rect, f"{name}: {score}", color)

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
        control_layout = QVBoxLayout(control_panel)
        self._yolo_status_label = QLabel("YOLO: chưa khởi động")
        self._yolo_status_label.setWordWrap(True)
        control_layout.addWidget(self._yolo_status_label)
        capture_btn = QPushButton("Chụp teaching")
        capture_btn.clicked.connect(self._open_teaching_capture)
        yolo_capture_btn = QPushButton("YOLO Teaching")
        yolo_capture_btn.clicked.connect(self._open_yolo_annotation)
        capture_row = QHBoxLayout()
        capture_row.addWidget(capture_btn)
        capture_row.addWidget(yolo_capture_btn)
        capture_row.addStretch(1)
        control_layout.addLayout(capture_row)

        self._yolo_settings = _load_yolo_settings()
        yolo_settings_btn = QPushButton("YOLO Settings")
        yolo_settings_btn.clicked.connect(self._open_yolo_settings)
        capture_row.addWidget(yolo_settings_btn)
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
        self._state_buttons["yolo"] = QPushButton("YOLO")
        self._state_buttons["yolo"].setCheckable(True)
        self._state_buttons["yolo"].clicked.connect(self._toggle_yolo)
        cards_layout.addWidget(self._state_buttons["yolo"])
        self._refresh_state_button("yolo")
        cards_layout.addStretch(1)
        cards_scroll.setWidget(cards_container)
        layout.addWidget(cards_scroll)

        self._worker = WindowStateMonitorWorker(tool_client, self._enabled_states, self)
        self._worker.snapshot_ready.connect(self._on_snapshot)
        self._worker.yolo_log.connect(self._on_yolo_log)
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

    def _open_yolo_annotation(self) -> None:
        dialog = YoloAnnotationDialog(
            target_window_hwnd=self._target_window_hwnd,
            parent=self,
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

    def _toggle_yolo(self, enabled: bool) -> None:
        self._refresh_state_button("yolo")
        self._worker.set_yolo_config(
            enabled=enabled,
            source_folder=self._yolo_settings["source_folder"],
            model_path=self._yolo_settings["model_path"],
            confidence=self._yolo_settings["confidence"],
            iou=self._yolo_settings["iou"],
        )

    def _open_yolo_settings(self) -> None:
        dialog = YoloSettingsDialog(self._yolo_settings, parent=self)
        if dialog.exec():
            self._yolo_settings = dialog.get_settings()
            _save_yolo_settings(self._yolo_settings)
            if self._state_buttons["yolo"].isChecked():
                self._toggle_yolo(True)

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

    def _on_yolo_log(self, message: str) -> None:
        self._yolo_status_label.setText(message)
        if "error" in message.lower():
            self._state_buttons["yolo"].setToolTip(message)

    def closeEvent(self, event) -> None:
        self._worker.stop()
        self._worker.wait(5500)
        super().closeEvent(event)
