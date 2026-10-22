"""Dialog for creating and editing teaching algorithm test sessions."""

from __future__ import annotations

import json
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from ..logic.action_type import ActionMode, ActionType, AutoAction
from ..logic.teaching_matching import (
    DEFAULT_COORDINATE_MATCH_OFFSET,
    expand_coordinate_bounds,
    normalize_coordinate_match_offset,
)
from ..logic.window_detector import WindowDetector
from .image_capture_dialog import ImageCaptureDialog
from .multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
from .teaching_algorithm_settings_dialog import TeachingAlgorithmSettingsDialog


DEFAULT_MATCH_THRESHOLD = 0.70


class TeachingAlgorithmTestDialog(QDialog):
    """Own the test setup UI that used to be embedded in the lab widget."""

    def __init__(self, parent=None, session_dir: str | None = None) -> None:
        super().__init__(parent)
        self.project_root = Path(__file__).resolve().parents[2]
        self.session_dir = Path(session_dir) if session_dir else None
        self.selected_algorithms: list[dict] = []
        self.target_window_hwnd: int | None = None
        self.teaching_image_path: Path | None = None
        self._pending_teaching_dir = Path(tempfile.mkdtemp(prefix="teaching_test_"))
        self.teaching_settings_path = self.project_root / "assets" / "teaching" / "settings.json"
        self.teaching_settings = self._load_teaching_settings()
        self.setWindowTitle("Tạo mới test" if not session_dir else "Chỉnh sửa test")
        self.setMinimumSize(560, 620)
        self._build_ui()
        self._load_session_details()
        self._refresh_windows()
        if self.session_dir:
            saved_teaching_path = self._resolve_teaching_image_path()
            if saved_teaching_path is not None:
                self._load_teaching_image(saved_teaching_path)
            else:
                self._clear_teaching_preview()
        else:
            self._clear_teaching_preview()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        details_group = QGroupBox("Thông tin test")
        details_layout = QFormLayout(details_group)
        self.test_name_edit = QLineEdit()
        self.test_name_edit.setPlaceholderText("Tên test (không bắt buộc)")
        details_layout.addRow("Tên test:", self.test_name_edit)
        self.test_description_edit = QPlainTextEdit()
        self.test_description_edit.setPlaceholderText("Mô tả (không bắt buộc)")
        self.test_description_edit.setMaximumHeight(80)
        details_layout.addRow("Mô tả:", self.test_description_edit)
        self.match_threshold_spin = QDoubleSpinBox()
        self.match_threshold_spin.setRange(0.01, 1.00)
        self.match_threshold_spin.setDecimals(2)
        self.match_threshold_spin.setSingleStep(0.01)
        self.match_threshold_spin.setValue(DEFAULT_MATCH_THRESHOLD)
        details_layout.addRow("Ngưỡng chấp nhận:", self.match_threshold_spin)
        layout.addWidget(details_group)

        window_group = QGroupBox("Window game")
        window_layout = QFormLayout(window_group)
        self.window_combo = QComboBox()
        self.window_combo.currentIndexChanged.connect(self._on_window_selected)
        window_layout.addRow("Chọn window:", self.window_combo)
        window_buttons = QHBoxLayout()
        refresh_button = QPushButton("Làm mới")
        refresh_button.clicked.connect(self._refresh_windows)
        window_buttons.addWidget(refresh_button)
        window_buttons.addStretch()
        window_layout.addRow(window_buttons)
        layout.addWidget(window_group)

        teaching_group = QGroupBox("Teaching image")
        teaching_layout = QVBoxLayout(teaching_group)
        self.teaching_preview = QLabel("Chưa có teaching image")
        self.teaching_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.teaching_preview.setMinimumSize(420, 260)
        self.teaching_preview.setStyleSheet("border: 1px solid #777;")
        teaching_layout.addWidget(self.teaching_preview)
        self.teaching_status = QLabel()
        self.teaching_status.setWordWrap(True)
        teaching_layout.addWidget(self.teaching_status)
        capture_button = QPushButton("Tạo ảnh teaching")
        capture_button.clicked.connect(self._capture_teaching_image)
        teaching_layout.addWidget(capture_button)
        layout.addWidget(teaching_group)

        algorithm_group = QGroupBox("Thuật toán được sử dụng")
        algorithm_layout = QVBoxLayout(algorithm_group)
        self.algorithms_list = QListWidget()
        self.algorithms_list.setMinimumHeight(90)
        algorithm_layout.addWidget(self.algorithms_list)
        layout.addWidget(algorithm_group)
        self._load_session_algorithms()

        layout.addStretch()
        buttons = QHBoxLayout()
        buttons.addStretch()
        self.test_button = QPushButton("Mở test algorithm")
        self.test_button.clicked.connect(self._open_algorithm_testing)
        buttons.addWidget(self.test_button)
        settings_button = QPushButton("Settings")
        settings_button.clicked.connect(self._open_teaching_settings)
        buttons.addWidget(settings_button)
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self._accept_dialog)
        buttons.addWidget(ok_button)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

    def _load_session_details(self) -> None:
        """Load the optional test name and description for an existing session."""
        if not self.session_dir:
            return
        try:
            metadata = json.loads(
                (self.session_dir / "session.json").read_text(encoding="utf-8")
            )
        except (OSError, TypeError, ValueError):
            return
        if not isinstance(metadata, dict):
            return
        self.test_name_edit.setText(str(metadata.get("name") or ""))
        self.test_description_edit.setPlainText(
            str(metadata.get("description") or "")
        )
        try:
            threshold = float(
                metadata.get("match_threshold", DEFAULT_MATCH_THRESHOLD)
            )
        except (TypeError, ValueError):
            threshold = DEFAULT_MATCH_THRESHOLD
        self.match_threshold_spin.setValue(
            max(self.match_threshold_spin.minimum(), min(self.match_threshold_spin.maximum(), threshold))
        )

    def _load_teaching_settings(self) -> dict:
        defaults = {
            "match_by_coordinates": False,
            "coordinate_offset": DEFAULT_COORDINATE_MATCH_OFFSET,
        }
        try:
            value = json.loads(self.teaching_settings_path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError):
            value = {}
        settings = {**defaults, **(value if isinstance(value, dict) else {})}

        if self.session_dir:
            try:
                session = json.loads(
                    (self.session_dir / "session.json").read_text(encoding="utf-8")
                )
            except (OSError, TypeError, ValueError):
                session = {}
            if isinstance(session, dict):
                if "match_by_coordinates" in session:
                    settings["match_by_coordinates"] = bool(
                        session["match_by_coordinates"]
                    )
                if "coordinate_offset" in session:
                    settings["coordinate_offset"] = session["coordinate_offset"]

        settings["coordinate_offset"] = normalize_coordinate_match_offset(
            settings.get("coordinate_offset")
        )
        return settings

    def _open_teaching_settings(self) -> None:
        dialog = TeachingAlgorithmSettingsDialog(self.teaching_settings, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.teaching_settings = dialog.values()
        save_errors: list[str] = []
        try:
            self.teaching_settings_path.parent.mkdir(parents=True, exist_ok=True)
            self.teaching_settings_path.write_text(
                json.dumps(self.teaching_settings, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            save_errors.append(f"Teaching Settings: {exc}")

        if self.session_dir:
            session_path = self.session_dir / "session.json"
            try:
                session = json.loads(session_path.read_text(encoding="utf-8"))
                if not isinstance(session, dict):
                    raise ValueError("session.json không chứa object hợp lệ")
                session["match_by_coordinates"] = bool(
                    self.teaching_settings.get("match_by_coordinates", False)
                )
                session["coordinate_offset"] = normalize_coordinate_match_offset(
                    self.teaching_settings.get("coordinate_offset")
                )
                session_path.write_text(
                    json.dumps(session, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except (OSError, TypeError, ValueError) as exc:
                save_errors.append(f"Item hiện tại: {exc}")

        if save_errors:
            QMessageBox.warning(
                self,
                "Lỗi",
                "Không lưu được đầy đủ cấu hình:\n" + "\n".join(save_errors),
            )

        teaching_image_path = self._resolve_teaching_image_path()
        if teaching_image_path is not None:
            self._load_teaching_image(teaching_image_path)

    def _accept_dialog(self) -> None:
        """Confirm and save the setup dialog state."""
        teaching_image_path = self._resolve_teaching_image_path()
        if teaching_image_path is None:
            QMessageBox.warning(
                self,
                "Thiếu teaching image",
                "Chưa có teaching image để lưu test.",
            )
            return

        if not self._save_dialog_config(teaching_image_path):
            return
        self.accept()

    def _save_dialog_config(self, teaching_image_path: Path) -> bool:
        """Persist setup data, including algorithm parameter values."""
        session_root = self.project_root / "build" / "images" / "algorithm_testing" / "sessions"
        session_root.mkdir(parents=True, exist_ok=True)
        if self.session_dir is None:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            self.session_dir = session_root / session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        metadata_path = self.session_dir / "session.json"
        try:
            metadata = (
                json.loads(metadata_path.read_text(encoding="utf-8"))
                if metadata_path.exists()
                else {}
            )
        except (OSError, TypeError, ValueError):
            metadata = {}

        captures_dir = self.session_dir / "captures"
        if not metadata.get("captures") and captures_dir.is_dir():
            metadata["captures"] = [
                {
                    "filename": capture.name,
                    "source_name": capture.name,
                    "score": None,
                    "bbox": None,
                }
                for capture in sorted(captures_dir.iterdir())
                if capture.is_file()
            ]

        saved_teaching_path = self.session_dir / "teaching.png"
        try:
            if teaching_image_path.resolve() != saved_teaching_path.resolve():
                shutil.copy2(teaching_image_path, saved_teaching_path)
            teaching_metadata_path = teaching_image_path.with_suffix(".json")
            if teaching_metadata_path.is_file():
                try:
                    metadata["teaching_metadata"] = json.loads(
                        teaching_metadata_path.read_text(encoding="utf-8")
                    )
                except (OSError, TypeError, ValueError):
                    pass
            metadata["teaching_metadata"] = self._complete_teaching_metadata(
                metadata.get("teaching_metadata", {}), teaching_image_path
            )
            metadata.update(
                {
                    "name": self.test_name_edit.text().strip(),
                    "description": self.test_description_edit.toPlainText().strip(),
                    "match_threshold": self.match_threshold_spin.value(),
                    "created_at": metadata.get("created_at") or datetime.now().isoformat(timespec="seconds"),
                    "window_title": self.window_combo.currentText(),
                    "window_hwnd": self.target_window_hwnd,
                    "match_by_coordinates": bool(
                        self.teaching_settings.get("match_by_coordinates", False)
                    ),
                    "coordinate_offset": normalize_coordinate_match_offset(
                        self.teaching_settings.get("coordinate_offset")
                    ),
                    "algorithms": self.selected_algorithms,
                    "teaching_image": "teaching.png",
                    "captures": metadata.get("captures", []),
                }
            )
            metadata_path.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except (OSError, TypeError, ValueError) as exc:
            QMessageBox.warning(self, "Lỗi", f"Không lưu được thông tin test: {exc}")
            return False
        return True

    def _refresh_windows(self) -> None:
        selected = self.target_window_hwnd
        self.window_combo.blockSignals(True)
        self.window_combo.clear()
        windows = list(WindowDetector.find_game_windows())
        prefix = "MU GamethuVN - Season 21"
        windows.sort(key=lambda pair: not str(pair[1]).strip().lower().startswith(prefix.lower()))
        for hwnd, title in windows:
            self.window_combo.addItem(title, int(hwnd))
        self.window_combo.blockSignals(False)
        index = self.window_combo.findData(selected) if selected else -1
        if index < 0 and self.window_combo.count() > 0:
            index = 0
        if index >= 0:
            self.window_combo.setCurrentIndex(index)
            self._on_window_selected(index)
        else:
            self.target_window_hwnd = None

    def _on_window_selected(self, index: int) -> None:
        value = self.window_combo.itemData(index)
        self.target_window_hwnd = int(value) if value else None

    def _load_teaching_image(self, image_path: Path | None = None) -> None:
        if image_path is None:
            self._clear_teaching_preview()
            return
        if not image_path.exists():
            self.teaching_preview.setText("Chưa có teaching image")
            self.teaching_status.setText(f"Không tìm thấy: {image_path}")
            return
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            self.teaching_preview.setText("Không thể đọc teaching image")
            self.teaching_status.setText(str(image_path))
            return
        preview_source, matching_bounds, teaching_rect = self._build_coordinate_preview(
            pixmap, image_path
        )
        target_size = self.teaching_preview.size()
        scale = min(
            target_size.width() / max(1, preview_source.width()),
            target_size.height() / max(1, preview_source.height()),
        )
        transformation = (
            Qt.TransformationMode.SmoothTransformation
            if scale < 1.0
            else Qt.TransformationMode.FastTransformation
        )
        display_pixmap = preview_source.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            transformation,
        )
        if matching_bounds and teaching_rect:
            self._draw_coordinate_preview_overlay(
                display_pixmap,
                preview_source.width(),
                preview_source.height(),
                teaching_rect,
            )
        self.teaching_preview.setPixmap(display_pixmap)
        self.teaching_status.setText(f"Đang dùng: {image_path}")

        if matching_bounds:
            left, top, right, bottom = matching_bounds
            offset = normalize_coordinate_match_offset(
                self.teaching_settings.get("coordinate_offset")
            )
            self.teaching_status.setText(
                f"{self.teaching_status.text()}\nMatching ROI + offset {offset}px: "
                f"({left}, {top}) - ({right}, {bottom})"
            )

    def _build_coordinate_preview(
        self, pixmap: QPixmap, image_path: Path
    ) -> tuple[
        QPixmap,
        tuple[int, int, int, int] | None,
        tuple[int, int, int, int] | None,
    ]:
        """Place the teaching crop inside its expanded coordinate matching ROI."""
        if not self.teaching_settings.get("match_by_coordinates", False):
            return pixmap, None, None

        metadata: dict = {}
        metadata_path = image_path.with_suffix(".json")
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError):
            if self.session_dir:
                try:
                    session = json.loads(
                        (self.session_dir / "session.json").read_text(encoding="utf-8")
                    )
                    metadata = session.get("teaching_metadata", {})
                except (OSError, TypeError, ValueError):
                    metadata = {}

        metadata = self._complete_teaching_metadata(metadata, image_path)
        x1 = metadata.get("corner_x1")
        y1 = metadata.get("corner_y1")
        x2 = metadata.get("corner_x2")
        y2 = metadata.get("corner_y2")
        window_width = int(metadata.get("window_width") or 800)
        window_height = int(metadata.get("window_height") or 600)
        bounds = expand_coordinate_bounds(
            x1,
            y1,
            x2,
            y2,
            self.teaching_settings.get("coordinate_offset"),
            window_width,
            window_height,
        )
        if not bounds:
            return pixmap, None, None

        left, top, right, bottom = bounds
        canvas = QPixmap(max(1, right - left), max(1, bottom - top))
        canvas.fill(QColor(35, 35, 35))
        painter = QPainter(canvas)
        crop_left = int(x1) - left
        crop_top = int(y1) - top
        painter.drawPixmap(crop_left, crop_top, pixmap)
        painter.end()
        teaching_rect = (crop_left, crop_top, pixmap.width(), pixmap.height())
        return canvas, bounds, teaching_rect

    @staticmethod
    def _draw_coordinate_preview_overlay(
        pixmap: QPixmap,
        source_width: int,
        source_height: int,
        teaching_rect: tuple[int, int, int, int],
    ) -> None:
        """Draw one-pixel overlays after scaling so zoom never thickens them."""
        if source_width <= 0 or source_height <= 0 or pixmap.isNull():
            return

        scale_x = pixmap.width() / source_width
        scale_y = pixmap.height() / source_height
        crop_left, crop_top, crop_width, crop_height = teaching_rect
        x = round(crop_left * scale_x)
        y = round(crop_top * scale_y)
        width = max(1, round(crop_width * scale_x))
        height = max(1, round(crop_height * scale_y))

        painter = QPainter(pixmap)
        teaching_pen = QPen(QColor(255, 0, 0), 1)
        teaching_pen.setCosmetic(True)
        painter.setPen(teaching_pen)
        painter.drawRect(x, y, max(0, width - 1), max(0, height - 1))

        matching_pen = QPen(QColor(255, 214, 10), 1)
        matching_pen.setCosmetic(True)
        painter.setPen(matching_pen)
        painter.drawRect(
            0,
            0,
            max(0, pixmap.width() - 1),
            max(0, pixmap.height() - 1),
        )
        painter.end()

    def _clear_teaching_preview(self) -> None:
        self.teaching_preview.clear()
        self.teaching_preview.setText("ChÆ°a cÃ³ teaching image")
        self.teaching_status.setText("Teaching image Ä‘ang Ä‘á»ƒ trá»‘ng.")

    def _resolve_teaching_image_path(self) -> Path | None:
        if self.teaching_image_path and self.teaching_image_path.is_file():
            return self.teaching_image_path
        if self.session_dir:
            try:
                metadata = json.loads(
                    (self.session_dir / "session.json").read_text(encoding="utf-8")
                )
                saved_name = metadata.get("teaching_image")
                saved_path = self.session_dir / str(saved_name) if saved_name else None
                if saved_path and saved_path.is_file():
                    return saved_path
            except (OSError, TypeError, ValueError):
                pass
        return None

    def _complete_teaching_metadata(self, metadata: dict, image_path: Path) -> dict:
        """Fill missing teaching coordinates from the saved image dimensions."""
        result = dict(metadata) if isinstance(metadata, dict) else {}
        coordinates = ("corner_x1", "corner_y1", "corner_x2", "corner_y2")
        if all(result.get(key) is not None for key in coordinates):
            return result

        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            return result
        result.update(
            {
                "corner_x1": 0,
                "corner_y1": 0,
                "corner_x2": pixmap.width(),
                "corner_y2": pixmap.height(),
                "window_width": 800,
                "window_height": 600,
            }
        )
        return result

    def _load_session_algorithms(self) -> None:
        """Show algorithms saved in the session being edited."""
        if not self.session_dir:
            return
        metadata_path = self.session_dir / "session.json"
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError):
            return
        self._set_algorithms(metadata.get("algorithms", []))

    def _set_algorithms(self, algorithms: list[dict] | None) -> None:
        self.selected_algorithms = list(algorithms or [])
        self.algorithms_list.clear()
        for algorithm in self.selected_algorithms:
            name = str(algorithm.get("name", "Không rõ thuật toán"))
            parameters = json.dumps(
                algorithm.get("config", {}),
                ensure_ascii=False,
                sort_keys=True,
            )
            self.algorithms_list.addItem(f"{name}\n  Tham số: {parameters}")
        if not self.selected_algorithms:
            self.algorithms_list.addItem("Chưa có thuật toán")

    def _capture_teaching_image(self) -> None:
        selected_index = self.window_combo.currentIndex()
        selected_value = (
            self.window_combo.currentData() if selected_index >= 0 else None
        )
        try:
            selected_hwnd = int(selected_value) if selected_value else None
        except (TypeError, ValueError):
            selected_hwnd = None

        if not selected_hwnd:
            QMessageBox.warning(self, "Cảnh báo", "Chưa chọn window game.")
            return

        try:
            import win32gui

            if not win32gui.IsWindow(selected_hwnd):
                QMessageBox.warning(
                    self,
                    "Cảnh báo",
                    "Window game vừa chọn không còn tồn tại. Hãy bấm Làm mới và chọn lại.",
                )
                return
        except ImportError:
            pass

        # The combobox is the source of truth at click time. Never fall back to
        # a handle cached when this edit dialog was opened.
        self.target_window_hwnd = selected_hwnd
        if not self._resize_game_window(selected_hwnd):
            return
        image_path = self._pending_teaching_dir / "teaching.png"
        metadata_path = self._pending_teaching_dir / "teaching.json"
        dialog = ImageCaptureDialog(
            selected_hwnd,
            parent=self,
            tool_id="teaching_lab",
            hide_click_selection=True,
            initial_image_path=str(image_path) if image_path.exists() else None,
            coordinate_match_offset=(
                normalize_coordinate_match_offset(
                    self.teaching_settings.get("coordinate_offset")
                )
                if self.teaching_settings.get("match_by_coordinates", False)
                else 0
            ),
        )
        if not dialog.exec():
            return
        result = dialog.get_cropped_image_path()
        source_path = Path(str(result[0] or "")) if result else Path()
        if not source_path.is_file():
            QMessageBox.warning(self, "Lỗi", "Không tạo được teaching image.")
            return
        try:
            if source_path.resolve() != image_path.resolve():
                shutil.copy2(source_path, image_path)
            metadata = {
                "corner_x1": result[3] if len(result) > 3 else None,
                "corner_y1": result[4] if len(result) > 4 else None,
                "corner_x2": result[5] if len(result) > 5 else None,
                "corner_y2": result[6] if len(result) > 6 else None,
                "window_width": result[7] if len(result) > 7 else None,
                "window_height": result[8] if len(result) > 8 else None,
            }
            metadata = self._complete_teaching_metadata(metadata, image_path)
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "Lỗi", f"Không lưu được teaching image: {exc}")
            return
        self.teaching_image_path = image_path
        self._load_teaching_image(image_path)
        pixmap = QPixmap(str(image_path))
        width = pixmap.width()
        height = pixmap.height()
        x1 = metadata.get("corner_x1")
        y1 = metadata.get("corner_y1")
        x2 = metadata.get("corner_x2")
        y2 = metadata.get("corner_y2")
        summary = (
            f"Teaching image: {width} x {height}px\n"
            f"Góc trên trái: ({x1}, {y1})\n"
            f"Góc trên phải: ({x2}, {y1})\n"
            f"Góc dưới trái: ({x1}, {y2})\n"
            f"Góc dưới phải: ({x2}, {y2})"
        )
        self.teaching_status.setText(summary)
        QMessageBox.information(self, "Đã lấy teaching image", summary)

    @staticmethod
    def _resize_game_window(hwnd: int, client_width: int = 800, client_height: int = 600) -> bool:
        """Resize the game client area before capturing a teaching image."""
        try:
            import win32con
            import win32gui

            window_rect = win32gui.GetWindowRect(hwnd)
            client_rect = win32gui.GetClientRect(hwnd)
            border_width = (window_rect[2] - window_rect[0]) - (client_rect[2] - client_rect[0])
            border_height = (window_rect[3] - window_rect[1]) - (client_rect[3] - client_rect[1])
            win32gui.SetWindowPos(
                hwnd,
                None,
                window_rect[0],
                window_rect[1],
                int(client_width + border_width),
                int(client_height + border_height),
                win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE,
            )
            time.sleep(0.15)
            return True
        except Exception as exc:
            QMessageBox.warning(
                None,
                "Lỗi resize window",
                f"Không thể resize game window về {client_width}x{client_height}: {exc}",
            )
            return False

    def _open_algorithm_testing(self) -> None:
        teaching_image_path = self._resolve_teaching_image_path()
        if teaching_image_path is None:
            QMessageBox.warning(
                self,
                "Thiếu teaching image",
                "Chưa có teaching image nên không thể mở MultiImage Algorithm Testing.",
            )
            return

        metadata = {}
        metadata_path = teaching_image_path.with_suffix(".json")
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError):
            if self.session_dir:
                try:
                    session_metadata = json.loads(
                        (self.session_dir / "session.json").read_text(encoding="utf-8")
                    )
                    metadata = session_metadata.get("teaching_metadata", {})
                except (OSError, TypeError, ValueError):
                    pass

        metadata = self._complete_teaching_metadata(metadata, teaching_image_path)

        action = AutoAction(
            name="Teaching Lab",
            purpose="Shared teaching image algorithm test",
            action_type=ActionType.IMAGE_DETECT,
            mode=ActionMode.ACTIVE,
            image_path=str(teaching_image_path),
        )
        action.teaching_match_by_coordinates = bool(
            self.teaching_settings.get("match_by_coordinates", False)
        )
        action.teaching_match_coordinate_offset = normalize_coordinate_match_offset(
            self.teaching_settings.get("coordinate_offset")
        )
        action.match_threshold = self.match_threshold_spin.value()
        for key, value in metadata.items():
            setattr(action, f"teaching_{key}", value)

        dialog = MultiImageAlgorithmTestingDialog(
            action=action,
            parent=self,
            target_window_hwnd=self.target_window_hwnd,
            tool_id="teaching_lab",
            algorithm_field="preprocessing_algorithms",
        )
        session_root = self.project_root / "build" / "images" / "algorithm_testing" / "sessions"
        session_root.mkdir(parents=True, exist_ok=True)
        dialog.test_sessions_dir = str(session_root)
        if self.session_dir:
            dialog.load_test_session(str(self.session_dir))
            # The Teaching dialog owns these settings. Loading an older session
            # must not overwrite values the user has just changed.
            dialog.action.teaching_match_by_coordinates = bool(
                self.teaching_settings.get("match_by_coordinates", False)
            )
            dialog.action.teaching_match_coordinate_offset = (
                normalize_coordinate_match_offset(
                    self.teaching_settings.get("coordinate_offset")
                )
            )
            dialog.action.match_threshold = self.match_threshold_spin.value()
            current_capture = dialog.captures_list.currentItem()
            if current_capture is not None:
                dialog._on_capture_selected(current_capture)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._set_algorithms(getattr(dialog.action, "preprocessing_algorithms", []))

    def reject(self) -> None:
        shutil.rmtree(self._pending_teaching_dir, ignore_errors=True)
        super().reject()
