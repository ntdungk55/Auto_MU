"""Teaching image capture and preprocessing algorithm test UI."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
from datetime import datetime
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..logic.action_type import ActionMode, ActionType, AutoAction
from ..logic.window_detector import WindowDetector
from .image_capture_dialog import ImageCaptureDialog
from .multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog


class TeachingAlgorithmLabWidget(QWidget):
    """Capture a shared teaching image and open the existing algorithm tester."""

    @staticmethod
    def asset_paths(project_root: Path | None = None) -> tuple[Path, Path]:
        """Return the shared teaching image and metadata paths."""
        root = project_root or Path(__file__).resolve().parents[2]
        directory = root / "assets" / "teaching_images"
        return directory / "current_teaching.png", directory / "current_teaching.json"

    @classmethod
    def load_teaching_metadata(cls, project_root: Path | None = None) -> dict[str, Any]:
        """Load shared teaching metadata, returning an empty mapping when absent."""
        _, metadata_path = cls.asset_paths(project_root)
        try:
            value = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError):
            return {}
        return value if isinstance(value, dict) else {}

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.project_root = Path(__file__).resolve().parents[2]
        self.target_window_hwnd: int | None = None
        self.test_sessions_dir = self.project_root / "assets" / "algorithm_tests"
        self._build_ui()
        self._load_test_sessions()
        self._refresh_windows()
        self._load_teaching_image()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Teaching Image & Algorithm Test</b>"))

        layout.addWidget(QLabel("Lịch sử test algorithm"))
        self.test_sessions_list = QListWidget()
        self.test_sessions_list.setMaximumHeight(110)
        self.test_sessions_list.setToolTip("Chọn một phiên để nạp lại ảnh, kết quả và algorithm đã lưu")
        self.test_sessions_list.itemClicked.connect(self._load_saved_teaching_image)
        layout.addWidget(self.test_sessions_list)

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
        teaching_buttons = QHBoxLayout()
        capture_button = QPushButton("Tạo ảnh teaching")
        capture_button.clicked.connect(self._capture_teaching_image)
        test_button = QPushButton("Test algorithm")
        test_button.clicked.connect(self._open_algorithm_testing)
        teaching_buttons.addWidget(capture_button)
        teaching_buttons.addWidget(test_button)
        teaching_buttons.addStretch()
        teaching_layout.addLayout(teaching_buttons)
        layout.addWidget(teaching_group)
        layout.addStretch()

    def _refresh_windows(self) -> None:
        """Refresh selectable game windows."""
        selected = self.target_window_hwnd
        self.window_combo.blockSignals(True)
        self.window_combo.clear()
        windows = list(WindowDetector.find_game_windows())
        prefix = "MU GamethuVN - Season 21"
        windows.sort(key=lambda pair: not str(pair[1]).strip().lower().startswith(prefix.lower()))
        for hwnd, title in windows:
            self.window_combo.addItem(title, int(hwnd))
        self.window_combo.blockSignals(False)
        if selected:
            index = self.window_combo.findData(selected)
            if index >= 0:
                self.window_combo.setCurrentIndex(index)
        if self.window_combo.currentIndex() >= 0:
            self._on_window_selected(self.window_combo.currentIndex())
        else:
            self.target_window_hwnd = None

    def _on_window_selected(self, index: int) -> None:
        """Store the selected game window handle."""
        value = self.window_combo.itemData(index)
        self.target_window_hwnd = int(value) if value else None

    def _load_teaching_image(self, image_path: Path | None = None) -> None:
        """Load the shared teaching image into the preview."""
        if image_path is None:
            image_path, _ = self.asset_paths(self.project_root)
        if not image_path.exists():
            self.teaching_preview.setText("Chưa có teaching image")
            self.teaching_status.setText(f"Không tìm thấy: {image_path}")
            return
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            self.teaching_preview.setText("Không thể đọc teaching image")
            self.teaching_status.setText(str(image_path))
            return
        self.teaching_preview.setPixmap(
            pixmap.scaled(
                self.teaching_preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.teaching_status.setText(f"Đang dùng: {image_path}")

    def _capture_teaching_image(self) -> None:
        """Capture and copy a teaching image into the shared assets folder."""
        if not self.target_window_hwnd:
            QMessageBox.warning(self, "Cảnh báo", "Chưa chọn window game.")
            return
        image_path, metadata_path = self.asset_paths(self.project_root)
        image_path.parent.mkdir(parents=True, exist_ok=True)
        dialog = ImageCaptureDialog(
            self.target_window_hwnd,
            parent=self,
            tool_id="teaching_lab",
            hide_click_selection=True,
            initial_image_path=str(image_path) if image_path.exists() else None,
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
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "Lỗi", f"Không lưu được teaching image: {exc}")
            return
        self._load_teaching_image()

    def _load_test_sessions(self) -> None:
        """Load saved test sessions into the history list in this tab."""
        self.test_sessions_list.clear()
        if not self.test_sessions_dir.is_dir():
            return

        sessions = []
        for session_dir in self.test_sessions_dir.iterdir():
            metadata_path = session_dir / "session.json"
            if not session_dir.is_dir() or not metadata_path.is_file():
                continue
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, TypeError, ValueError):
                continue
            sessions.append((metadata.get("created_at", ""), session_dir, metadata))

        for _, session_dir, metadata in sorted(sessions, reverse=True):
            created_at = metadata.get("created_at", "")
            try:
                display_time = datetime.fromisoformat(created_at).strftime("%d/%m/%Y %H:%M:%S")
            except (TypeError, ValueError):
                display_time = created_at or "Không rõ thời gian"
            count = len(metadata.get("captures", []))
            window_title = metadata.get("window_title") or "Không rõ window"
            item = QListWidgetItem(f"{display_time} | {window_title} | {count} ảnh")
            item.setData(Qt.ItemDataRole.UserRole, str(session_dir))
            self.test_sessions_list.addItem(item)

    def _load_saved_teaching_image(self, item: QListWidgetItem) -> None:
        """Load the teaching image saved with the selected test session."""
        session_dir = item.data(Qt.ItemDataRole.UserRole)
        if not session_dir:
            return
        try:
            metadata_path = Path(session_dir) / "session.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError) as exc:
            self.teaching_status.setText(f"Không đọc được thông tin phiên test: {exc}")
            return

        teaching_name = metadata.get("teaching_image")
        teaching_path = Path(session_dir) / teaching_name if teaching_name else None
        if teaching_path and teaching_path.is_file():
            self._load_teaching_image(teaching_path)
            created_at = metadata.get("created_at", "")
            window_title = metadata.get("window_title") or "Không rõ window"
            self.teaching_status.setText(
                f"Đã nạp teaching image của phiên {created_at}\nWindow: {window_title}\n"
                f"Nguồn: {teaching_path}"
            )
        else:
            self._load_teaching_image()
            self.teaching_status.setText("Phiên test không có teaching image đã lưu.")

    def _open_algorithm_testing(self, session_dir: str | None = None) -> None:
        """Open the existing multi-image algorithm testing dialog."""
        image_path, _ = self.asset_paths(self.project_root)
        if not image_path.is_file():
            QMessageBox.warning(self, "Thiếu teaching image", "Hãy tạo teaching image trước khi test algorithm.")
            return
        if not self.target_window_hwnd:
            QMessageBox.warning(self, "Cảnh báo", "Chưa chọn window game.")
            return
        metadata = self.load_teaching_metadata(self.project_root)
        action = AutoAction(
            name="Teaching Lab",
            purpose="Shared teaching image algorithm test",
            action_type=ActionType.IMAGE_DETECT,
            mode=ActionMode.ACTIVE,
            image_path=str(image_path),
        )
        action.teaching_corner_x1 = metadata.get("corner_x1")
        action.teaching_corner_y1 = metadata.get("corner_y1")
        action.teaching_corner_x2 = metadata.get("corner_x2")
        action.teaching_corner_y2 = metadata.get("corner_y2")
        dialog = MultiImageAlgorithmTestingDialog(
            action=action,
            parent=self,
            target_window_hwnd=self.target_window_hwnd,
            tool_id="teaching_lab",
            algorithm_field="preprocessing_algorithms",
        )
        if session_dir:
            dialog.load_test_session(session_dir)
        dialog.exec()
