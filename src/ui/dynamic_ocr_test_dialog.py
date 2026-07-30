"""Test dialog for Dynamic OCR Condition action."""

from __future__ import annotations

import copy
import os
import shutil
import tempfile

import cv2
import numpy as np
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPen, QPixmap, QWheelEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from ..logic.action_type import AutoAction
from ..logic.system_executor.system_executor import SystemExecutor
from ..logic.system_executor.window_capture import WindowCapture
from ..logic.window_detector import WindowDetector


DIAGNOSTICS_ROLE = int(Qt.ItemDataRole.UserRole) + 1


class ZoomableGraphicsView(QGraphicsView):
    """QGraphicsView with wheel zoom and drag pan, matching algorithm testing preview behavior."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 8.0

    def wheelEvent(self, event: QWheelEvent):
        old_pos = self.mapToScene(event.position().toPoint())
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor
        zoom_factor = zoom_in_factor if event.angleDelta().y() > 0 else zoom_out_factor
        new_zoom = self.zoom_factor * zoom_factor
        if new_zoom < self.min_zoom or new_zoom > self.max_zoom:
            return

        self.scale(zoom_factor, zoom_factor)
        self.zoom_factor = new_zoom
        new_pos = self.mapToScene(event.position().toPoint())
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())

    def reset_zoom(self):
        self.resetTransform()
        self.zoom_factor = 1.0


def _load_bgr_unicode(image_path: str) -> np.ndarray | None:
    try:
        with open(image_path, "rb") as f:
            file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
        return cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    except Exception:
        return None


class DynamicOCRTestDialog(QDialog):
    """Run Dynamic OCR Condition against captured or local sample images."""

    def __init__(self, action: AutoAction, parent=None, target_window_hwnd=None, tool_id: str | None = None):
        super().__init__(parent)
        self.action = copy.deepcopy(action)
        self.target_window_hwnd = target_window_hwnd
        self.selected_window_hwnd = target_window_hwnd
        self.tool_id = tool_id
        self.window_detector = WindowDetector()
        self.executor = SystemExecutor(target_window_hwnd=None, ui_log_func=lambda _msg: None)
        self.temp_dir = tempfile.mkdtemp(prefix="dynamic_ocr_test_")
        self.sample_paths: list[str] = []
        self._selection_generation = 0

        self.setWindowTitle("Dynamic OCR Test")
        self.resize(1280, 860)
        self._init_ui()
        self._refresh_windows()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        source_group = QGroupBox("Sample Images")
        source_layout = QVBoxLayout()

        window_row = QHBoxLayout()
        window_row.addWidget(QLabel("Window game:"))
        self.window_combo = QComboBox()
        self.window_combo.currentIndexChanged.connect(self._on_window_selected)
        window_row.addWidget(self.window_combo, 1)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_windows)
        window_row.addWidget(refresh_btn)
        capture_btn = QPushButton("Capture From Window")
        capture_btn.clicked.connect(self._capture_from_window)
        window_row.addWidget(capture_btn)
        load_btn = QPushButton("Load Local Images")
        load_btn.clicked.connect(self._load_local_images)
        window_row.addWidget(load_btn)
        source_layout.addLayout(window_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_widget = QGroupBox("Captured / Loaded Images")
        left_widget.setMinimumWidth(420)
        left_layout = QVBoxLayout()
        self.samples_list = QListWidget()
        self.samples_list.setWordWrap(True)
        self.samples_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.samples_list.currentItemChanged.connect(self._on_sample_selected)
        left_layout.addWidget(self.samples_list)
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)

        right_widget = QGroupBox("Preview And Results")
        right_layout = QVBoxLayout()

        self.preview_scene = QGraphicsScene(self)
        self.preview_view = ZoomableGraphicsView()
        self.preview_view.setScene(self.preview_scene)
        self.preview_view.setMinimumSize(520, 260)
        self.preview_view.setStyleSheet("QGraphicsView { border: 1px solid #666; background: #111; }")
        self._preview_pixmap_item = None
        self._last_preview_pixmap = None
        self._last_preview_bbox = None
        self._last_preview_source_shape = None
        self._preview_fit_pending = True
        self.show_ocr_preview_checkbox = QCheckBox("Apply OCR algorithms to preview")
        self.show_ocr_preview_checkbox.stateChanged.connect(self._on_preview_mode_toggled)
        self.show_matching_preview_checkbox = QCheckBox("Apply matching algorithms to preview")
        self.show_matching_preview_checkbox.stateChanged.connect(self._on_matching_preview_mode_toggled)
        preview_toolbar = QHBoxLayout()
        preview_toolbar.addWidget(self.show_ocr_preview_checkbox)
        preview_toolbar.addWidget(self.show_matching_preview_checkbox)
        preview_toolbar.addStretch()
        self.reset_zoom_btn = QPushButton("Reset Zoom")
        self.reset_zoom_btn.clicked.connect(self._reset_preview_zoom)
        preview_toolbar.addWidget(self.reset_zoom_btn)
        right_layout.addLayout(preview_toolbar)
        right_layout.addWidget(self.preview_view)

        self.match_crop_label = QLabel("No matched region")
        self.match_crop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.match_crop_label.setMinimumSize(320, 140)
        self.match_crop_label.setStyleSheet("QLabel { border: 1px solid #666; background: #111; color: #ddd; }")
        right_layout.addWidget(self.match_crop_label)

        status_group = QGroupBox("Pipeline Status")
        status_layout = QFormLayout()
        self.match_status_label = QLabel("-")
        self.sample_status_label = QLabel("-")
        self.mode_status_label = QLabel(str(getattr(self.action, "dynamic_ocr_target_mode", "roi") or "roi"))
        self.bbox_status_label = QLabel("-")
        self.ocr_status_label = QLabel("-")
        self.extract_status_label = QLabel("-")
        self.code_status_label = QLabel("-")
        self.final_result_label = QLabel("-")
        status_layout.addRow("Sample:", self.sample_status_label)
        status_layout.addRow("Mode:", self.mode_status_label)
        status_layout.addRow("Teaching match:", self.match_status_label)
        status_layout.addRow("BBox:", self.bbox_status_label)
        status_layout.addRow("OCR:", self.ocr_status_label)
        status_layout.addRow("Extract:", self.extract_status_label)
        status_layout.addRow("Code:", self.code_status_label)
        status_layout.addRow("Final result:", self.final_result_label)
        status_group.setLayout(status_layout)
        right_layout.addWidget(status_group)

        lower_grid = QGridLayout()

        self.ocr_text_edit = QTextEdit()
        self.ocr_text_edit.setReadOnly(True)
        self.ocr_text_edit.setPlaceholderText("OCR text...")
        lower_grid.addWidget(QLabel("OCR Text"), 0, 0)
        lower_grid.addWidget(self.ocr_text_edit, 1, 0)

        self.lines_edit = QTextEdit()
        self.lines_edit.setReadOnly(True)
        self.lines_edit.setPlaceholderText("lines...")
        lower_grid.addWidget(QLabel("Lines"), 0, 1)
        lower_grid.addWidget(self.lines_edit, 1, 1)

        self.params_table = QTableWidget(0, 2)
        self.params_table.setHorizontalHeaderLabels(["Param", "Value (type)"])
        self.params_table.horizontalHeader().setStretchLastSection(True)
        self.params_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        lower_grid.addWidget(QLabel("Matched Params"), 2, 0, 1, 2)
        lower_grid.addWidget(self.params_table, 3, 0, 1, 2)

        right_layout.addLayout(lower_grid)
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 5)

        source_layout.addWidget(splitter)
        source_group.setLayout(source_layout)
        main_layout.addWidget(source_group)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        main_layout.addLayout(close_row)

    def _refresh_windows(self):
        self.window_combo.blockSignals(True)
        self.window_combo.clear()

        windows = self.window_detector.find_windows_by_title("Mu Online - GamethuVN.com")
        if not windows:
            windows = self.window_detector.find_windows_by_title("Mu Online")
        if not windows:
            windows = self.window_detector.find_windows_by_title("GamethuVN")
        if not windows:
            windows = self.window_detector.find_windows_by_title("MU ONLINE")
        if not windows:
            windows = self.window_detector.find_windows_by_title("MU")

        if not windows:
            self.window_combo.addItem("No window found", None)
        else:
            for hwnd, title in windows:
                self.window_combo.addItem(title, hwnd)

        if self.target_window_hwnd:
            for index in range(self.window_combo.count()):
                if self.window_combo.itemData(index) == self.target_window_hwnd:
                    self.window_combo.setCurrentIndex(index)
                    self.selected_window_hwnd = self.target_window_hwnd
                    break

        self.window_combo.blockSignals(False)
        if self.window_combo.count() > 0 and self.window_combo.currentIndex() < 0:
            self.window_combo.setCurrentIndex(0)
        self._on_window_selected(self.window_combo.currentIndex())

    def _on_window_selected(self, index: int):
        if index >= 0:
            self.selected_window_hwnd = self.window_combo.itemData(index)

    def _capture_from_window(self):
        hwnd = self.selected_window_hwnd or self.target_window_hwnd
        if not hwnd:
            QMessageBox.warning(self, "Warning", "Please select a game window first.")
            return

        try:
            screenshot = WindowCapture(hwnd).capture()
            if screenshot is None:
                QMessageBox.warning(self, "Error", "Could not capture screenshot from selected window.")
                return
            filename = f"capture_{len(self.sample_paths) + 1:03d}.png"
            temp_path = os.path.join(self.temp_dir, filename)
            success, encoded_img = cv2.imencode(".png", screenshot)
            if not success:
                QMessageBox.warning(self, "Error", "Could not encode captured screenshot.")
                return
            with open(temp_path, "wb") as f:
                f.write(encoded_img.tobytes())
            self._add_sample(temp_path)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Capture failed:\n{exc}")

    def _load_local_images(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Choose sample images",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if not file_paths:
            return

        for file_path in file_paths:
            ext = os.path.splitext(file_path)[1] or ".png"
            dest_path = os.path.join(self.temp_dir, f"local_{len(self.sample_paths) + 1:03d}{ext}")
            try:
                shutil.copy2(file_path, dest_path)
            except Exception as exc:
                QMessageBox.warning(self, "Warning", f"Could not load image:\n{file_path}\n{exc}")
                continue
            self._add_sample(dest_path)

    def _add_sample(self, image_path: str):
        self.sample_paths.append(image_path)
        item = QListWidgetItem(os.path.basename(image_path))
        item.setData(Qt.ItemDataRole.UserRole, image_path)
        self.samples_list.addItem(item)
        self.samples_list.setCurrentItem(item)

    def _on_sample_selected(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None):
        if current is None:
            return

        self._selection_generation += 1
        selection_generation = self._selection_generation
        self._preview_fit_pending = True
        image_path = str(current.data(Qt.ItemDataRole.UserRole) or "")
        self._set_processing_state(os.path.basename(image_path))
        screenshot_bgr = _load_bgr_unicode(image_path)
        if screenshot_bgr is None:
            self._set_error_state("Could not read selected image.")
            return

        sample_executor = SystemExecutor(target_window_hwnd=None, ui_log_func=lambda _msg: None)
        diagnostics = sample_executor.evaluate_dynamic_ocr_condition_on_image(
            self.action,
            screenshot_bgr,
            include_best_bbox=True,
        )
        diagnostics["_sample_path"] = image_path
        current.setData(DIAGNOSTICS_ROLE, diagnostics)

        # Selection can be changed by queued UI events while OCR/matching is running.
        # Never let an old result overwrite the panel for a newer selection.
        if (
            selection_generation != self._selection_generation
            or self.samples_list.currentItem() is not current
            or str(current.data(Qt.ItemDataRole.UserRole) or "") != image_path
        ):
            self._update_sample_item_status(current, diagnostics)
            return

        self._update_sample_item_status(current, diagnostics)
        self._update_preview(diagnostics, screenshot_bgr)
        self._update_results(diagnostics)

    def _update_sample_item_status(self, item: QListWidgetItem, diagnostics: dict):
        if item is None:
            return

        base_name = os.path.basename(str(item.data(Qt.ItemDataRole.UserRole) or ""))
        mode = str(diagnostics.get("mode", "roi") or "roi")
        if mode == "teaching":
            score = float(diagnostics.get("teaching_score", 0.0) or 0.0)
            bbox = diagnostics.get("teaching_bbox")
            status = "Match OK" if diagnostics.get("teaching_match_found") else "Best only"
            if bbox:
                item.setText(f"{base_name} | {status} | Score {score:.3f} | BBox {bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}")
            else:
                item.setText(f"{base_name} | No match | Score {score:.3f}")
        else:
            target_bgr = diagnostics.get("target_bgr")
            if target_bgr is not None and getattr(target_bgr, "shape", None) is not None:
                height, width = target_bgr.shape[:2]
                item.setText(f"{base_name} | ROI {width}x{height}")
            else:
                item.setText(f"{base_name} | ROI")

    def _update_preview(self, diagnostics: dict, screenshot_bgr: np.ndarray):
        teaching_bbox = diagnostics.get("teaching_bbox")
        source_shape = screenshot_bgr.shape[:2]

        if self.show_ocr_preview_checkbox.isChecked():
            try:
                preview_bgr = self.executor._prepare_bgr_for_ocr(screenshot_bgr, self.action)
            except Exception as e:
                preview_bgr = screenshot_bgr.copy()
                self._append_log(f"<b style='color:red;'>[Preview]</b> Không áp dụng được OCR algorithms: {e}")
            match_crop = diagnostics.get("ocr_preview_bgr")
            if match_crop is None:
                match_crop = diagnostics.get("target_bgr")
            self._set_match_crop_bgr(match_crop)
        elif self.show_matching_preview_checkbox.isChecked():
            try:
                preview_bgr = self.executor._apply_preprocessing_algorithms(
                    screenshot_bgr,
                    getattr(self.action, "template_matching_algorithms", []) or [],
                )
            except Exception as e:
                preview_bgr = screenshot_bgr.copy()
                self._append_log(f"<b style='color:red;'>[Preview]</b> Khong ap dung duoc matching algorithms: {e}")
            self._set_match_crop_bgr(diagnostics.get("target_bgr"))
        else:
            preview_bgr = screenshot_bgr.copy()
            self._set_match_crop_bgr(diagnostics.get("target_bgr"))
        self._set_preview_bgr(preview_bgr, teaching_bbox, source_shape)

    def _on_preview_mode_toggled(self, _state):
        if self.show_ocr_preview_checkbox.isChecked() and self.show_matching_preview_checkbox.isChecked():
            self.show_matching_preview_checkbox.blockSignals(True)
            self.show_matching_preview_checkbox.setChecked(False)
            self.show_matching_preview_checkbox.blockSignals(False)
        self._refresh_current_preview()

    def _on_matching_preview_mode_toggled(self, _state):
        if self.show_matching_preview_checkbox.isChecked() and self.show_ocr_preview_checkbox.isChecked():
            self.show_ocr_preview_checkbox.blockSignals(True)
            self.show_ocr_preview_checkbox.setChecked(False)
            self.show_ocr_preview_checkbox.blockSignals(False)
        self._refresh_current_preview()

    def _refresh_current_preview(self):
        current_item = self.samples_list.currentItem()
        if current_item is not None:
            self._preview_fit_pending = True
            self._on_sample_selected(current_item, None)

    def _set_preview_bgr(
        self,
        bgr_img: np.ndarray | None,
        teaching_bbox: tuple[int, int, int, int] | None = None,
        source_shape: tuple[int, int] | None = None,
    ):
        if bgr_img is None or getattr(bgr_img, "size", 0) == 0:
            self.preview_scene.clear()
            self._preview_pixmap_item = None
            self._last_preview_pixmap = None
            self._last_preview_bbox = None
            self._last_preview_source_shape = None
            return

        if len(bgr_img.shape) == 2:
            rgb_img = cv2.cvtColor(bgr_img, cv2.COLOR_GRAY2RGB)
        else:
            rgb_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)

        height, width = rgb_img.shape[:2]
        bytes_per_line = rgb_img.strides[0]
        q_image = QImage(rgb_img.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        self.preview_scene.clear()
        self._preview_pixmap_item = self.preview_scene.addPixmap(pixmap)
        self._preview_pixmap_item.setZValue(0)
        self.preview_scene.setSceneRect(QRectF(0, 0, float(width), float(height)))
        self._last_preview_pixmap = pixmap
        self._last_preview_bbox = teaching_bbox
        self._last_preview_source_shape = source_shape or bgr_img.shape[:2]
        self._draw_match_scene_overlay(width, height)
        if self._preview_fit_pending:
            self._reset_preview_zoom()
            self._preview_fit_pending = False

    def _reset_preview_zoom(self):
        if self.preview_scene.sceneRect().isNull():
            return
        self.preview_view.reset_zoom()
        self.preview_view.fitInView(self.preview_scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _draw_match_scene_overlay(self, image_width: int, image_height: int) -> None:
        bbox = self._last_preview_bbox
        source_shape = self._last_preview_source_shape
        if not bbox or not source_shape:
            return

        source_h, source_w = source_shape
        if source_w <= 0 or source_h <= 0 or image_width <= 0 or image_height <= 0:
            return

        x, y, w, h = bbox
        scale_x = float(image_width) / float(source_w)
        scale_y = float(image_height) / float(source_h)
        x = float(x) * scale_x
        y = float(y) * scale_y
        w = float(w) * scale_x
        h = float(h) * scale_y
        if w <= 0 or h <= 0:
            return

        x = max(0, min(int(round(x)), image_width - 1))
        y = max(0, min(int(round(y)), image_height - 1))
        x2 = max(x + 1, min(int(round(x + w)), image_width))
        y2 = max(y + 1, min(int(round(y + h)), image_height))
        rect = QRectF(float(x), float(y), float(x2 - x), float(y2 - y))
        if rect.width() <= 0 or rect.height() <= 0:
            return

        pen_width = max(3, int(round(min(image_width, image_height) / 220)))
        fill_brush = QBrush(QColor(255, 0, 255, 22))
        outline_pen = QPen(QColor(0, 0, 0), pen_width + 2)
        highlight_pen = QPen(QColor(255, 0, 255), pen_width)

        outline_item = self.preview_scene.addRect(rect, outline_pen, QBrush(Qt.BrushStyle.NoBrush))
        outline_item.setZValue(10)
        rect_item = self.preview_scene.addRect(rect, highlight_pen, fill_brush)
        rect_item.setZValue(11)

        label_item = QGraphicsSimpleTextItem("BEST MATCH")
        label_font = QFont()
        label_font.setBold(True)
        label_font.setPointSize(max(10, int(round(min(image_width, image_height) / 90))))
        label_item.setFont(label_font)
        label_item.setBrush(QBrush(QColor(255, 0, 255)))
        label_item.setPos(rect.left() + pen_width, max(0.0, rect.top() - label_item.boundingRect().height() - pen_width))
        label_item.setZValue(12)
        self.preview_scene.addItem(label_item)

    def _set_match_crop_bgr(self, bgr_img: np.ndarray | None):
        if bgr_img is None or getattr(bgr_img, "size", 0) == 0:
            self.match_crop_label.setPixmap(QPixmap())
            self.match_crop_label.setText("No matched region")
            return

        if len(bgr_img.shape) == 2:
            rgb_img = cv2.cvtColor(bgr_img, cv2.COLOR_GRAY2RGB)
        else:
            rgb_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)

        height, width = rgb_img.shape[:2]
        bytes_per_line = rgb_img.strides[0]
        q_image = QImage(rgb_img.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        self.match_crop_label.setText("")
        self.match_crop_label.setPixmap(
            pixmap.scaled(
                self.match_crop_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._preview_fit_pending and not self.preview_scene.sceneRect().isNull():
            self._reset_preview_zoom()

    def _set_status_label(self, label: QLabel, text: str, ok: bool | None):
        label.setText(text)
        if ok is True:
            label.setStyleSheet("color:#2e7d32; font-weight:600;")
        elif ok is False:
            label.setStyleSheet("color:#d32f2f; font-weight:600;")
        else:
            label.setStyleSheet("")

    def _append_log(self, message: str):
        print(message)

    def _set_error_state(self, message: str):
        self.preview_scene.clear()
        self._preview_pixmap_item = None
        self._last_preview_pixmap = None
        self._last_preview_bbox = None
        self._last_preview_source_shape = None
        self.match_crop_label.setPixmap(QPixmap())
        self.match_crop_label.setText("No matched region")
        self.ocr_text_edit.setPlainText("")
        self.lines_edit.setPlainText("")
        self.params_table.setRowCount(0)
        self.bbox_status_label.setText("-")
        self._set_status_label(self.match_status_label, "Fail", False)
        self._set_status_label(self.ocr_status_label, "Fail", False)
        self._set_status_label(self.extract_status_label, "Fail", False)
        self._set_status_label(self.code_status_label, message, False)
        self._set_status_label(self.final_result_label, "False", False)

    def _update_results(self, diagnostics: dict):
        mode = str(diagnostics.get("mode", "roi") or "roi")
        error = str(diagnostics.get("error", "") or "")
        match_found = bool(diagnostics.get("teaching_match_found", False))
        self.sample_status_label.setText(os.path.basename(str(diagnostics.get("_sample_path", "") or "")) or "-")
        self.mode_status_label.setText(mode)
        bbox = diagnostics.get("teaching_bbox")
        if bbox:
            self.bbox_status_label.setText(f"{bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]}")
        else:
            self.bbox_status_label.setText("-")

        if mode == "teaching":
            score = float(diagnostics.get("teaching_score", 0.0) or 0.0)
            match_text = f"{'OK' if match_found else 'Best only'} ({score:.3f})"
            self._set_status_label(self.match_status_label, match_text, match_found)
        else:
            self._set_status_label(self.match_status_label, "ROI mode", None)

        ocr_text = str(diagnostics.get("ocr_text", "") or "")
        self.ocr_text_edit.setPlainText(ocr_text)
        self.lines_edit.setPlainText("\n".join(diagnostics.get("lines", []) or []))
        self._set_status_label(self.ocr_status_label, diagnostics.get("engine_used", "Fail") or "Fail", bool(ocr_text))

        extracted_values = dict(diagnostics.get("extracted_values", {}) or {})
        self.params_table.setRowCount(0)
        for row, (key, value) in enumerate(extracted_values.items()):
            self.params_table.insertRow(row)
            self.params_table.setItem(row, 0, QTableWidgetItem(str(key)))
            if value is None:
                value_text = "null"
            else:
                value_text = f"{value!r} ({type(value).__name__})"
            self.params_table.setItem(row, 1, QTableWidgetItem(value_text))
        self._set_status_label(self.extract_status_label, "OK" if extracted_values else "No params", bool(extracted_values))

        code_result = diagnostics.get("code_result")
        if error:
            self._set_status_label(self.code_status_label, error, False)
            self._set_status_label(self.final_result_label, "False", False)
        else:
            code_text = str(code_result)
            if extracted_values:
                values_text = ", ".join(
                    f"{key}={value!r}:{type(value).__name__}" for key, value in extracted_values.items()
                )
                code_text = f"{code_text} | {values_text}"
            self._set_status_label(self.code_status_label, code_text, bool(code_result))
            self._set_status_label(self.final_result_label, str(bool(code_result)), bool(code_result))

    def _set_processing_state(self, sample_name: str):
        self.sample_status_label.setText(sample_name or "-")
        self._set_status_label(self.match_status_label, "Processing...", None)
        self.bbox_status_label.setText("-")
        self._set_status_label(self.ocr_status_label, "Processing...", None)
        self._set_status_label(self.extract_status_label, "-", None)
        self._set_status_label(self.code_status_label, "-", None)
        self._set_status_label(self.final_result_label, "-", None)
        self.ocr_text_edit.setPlainText("")
        self.lines_edit.setPlainText("")
        self.params_table.setRowCount(0)

    def closeEvent(self, event):
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass
        super().closeEvent(event)
