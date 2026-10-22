"""Teaching image capture and preprocessing algorithm test UI."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
from datetime import datetime
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QDialog,
    QVBoxLayout,
    QWidget,
)

from .teaching_algorithm_test_dialog import TeachingAlgorithmTestDialog


class TeachingAlgorithmLabWidget(QWidget):
    """Capture a shared teaching image and open the existing algorithm tester."""

    @staticmethod
    def asset_paths(project_root: Path | None = None) -> tuple[Path, Path]:
        """Return the shared teaching image and metadata paths."""
        root = project_root or Path(__file__).resolve().parents[2]
        directory = root / "assets" / "teaching"
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
        self.test_sessions_dir = self.project_root / "build" / "images" / "algorithm_testing" / "sessions"
        self._build_ui()
        self._load_test_sessions()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Teaching Image & Algorithm Test</b>"))

        layout.addWidget(QLabel("Lịch sử test algorithm"))
        self.test_sessions_list = QListWidget()
        self.test_sessions_list.setMaximumHeight(110)
        self.test_sessions_list.setToolTip("Chọn một phiên để nạp lại ảnh, kết quả và algorithm đã lưu")
        self.test_sessions_list.itemDoubleClicked.connect(self._open_saved_test)
        self.test_sessions_list.itemSelectionChanged.connect(
            lambda: self.delete_test_button.setEnabled(self.test_sessions_list.currentItem() is not None)
        )
        layout.addWidget(self.test_sessions_list)

        test_buttons = QHBoxLayout()
        self.new_test_button = QPushButton("Tạo mới test")
        self.new_test_button.clicked.connect(self._open_algorithm_testing)
        test_buttons.addWidget(self.new_test_button)
        self.delete_test_button = QPushButton("Xóa test")
        self.delete_test_button.setEnabled(False)
        self.delete_test_button.clicked.connect(self._delete_selected_test)
        test_buttons.addWidget(self.delete_test_button)
        test_buttons.addStretch()
        layout.addLayout(test_buttons)

        layout.addStretch()

    def _load_test_sessions(self) -> None:
        """Load saved test sessions into the history list in this tab."""
        self.test_sessions_list.clear()
        self.delete_test_button.setEnabled(False)
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
            fallback_text = f"{display_time} | {window_title} | {count} ảnh"
            test_name = str(metadata.get("name") or "").strip()
            description = str(metadata.get("description") or "").strip()
            item = QListWidgetItem(test_name or fallback_text)
            if description:
                item.setToolTip(description)
            item.setData(Qt.ItemDataRole.UserRole, str(session_dir))
            self.test_sessions_list.addItem(item)

    def _open_saved_test(self, item: QListWidgetItem) -> None:
        """Open the selected test session in the test dialog for editing."""
        session_dir = item.data(Qt.ItemDataRole.UserRole)
        if not session_dir:
            return
        self._open_algorithm_testing(str(session_dir))

    def _delete_selected_test(self) -> None:
        """Delete the selected saved test session after confirmation."""
        item = self.test_sessions_list.currentItem()
        session_value = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not session_value:
            return

        root = self.test_sessions_dir.resolve()
        session_dir = Path(str(session_value)).resolve()
        try:
            session_dir.relative_to(root)
        except ValueError:
            QMessageBox.warning(self, "Lỗi", "Phiên test không nằm trong thư mục dữ liệu hợp lệ.")
            return
        if not session_dir.is_dir():
            QMessageBox.warning(self, "Lỗi", "Không tìm thấy thư mục phiên test.")
            self._load_test_sessions()
            return

        config_path = self.project_root / "mcp" / "config" / "mu_game_window.json"
        try:
            config = json.loads(config_path.read_text(encoding="utf-8-sig"))
            referenced_session_id = str(
                config["mainInfo"]["companionManagement1"].get(
                    "trainingTeachingSessionId", ""
                )
                or ""
            ).strip()
        except (OSError, KeyError, TypeError, ValueError) as exc:
            QMessageBox.warning(
                self,
                "Không thể kiểm tra tham chiếu",
                "Không thể xác định item có đang được dùng để nhận diện Train hay không. "
                f"Thao tác xóa đã bị chặn để bảo vệ dữ liệu.\n\n{exc}",
            )
            return

        if referenced_session_id == session_dir.name:
            QMessageBox.warning(
                self,
                "Không thể xóa test",
                "Item Teaching này đang được dùng để nhận diện trạng thái Train của "
                "nhân vật phụ. Hãy bỏ tham chiếu trước khi xóa.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Xác nhận xóa",
            "Bạn có chắc muốn xóa phiên test đã chọn không?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            shutil.rmtree(session_dir)
        except OSError as exc:
            QMessageBox.warning(self, "Lỗi", f"Không thể xóa phiên test: {exc}")
            return
        self._load_test_sessions()

    def _open_algorithm_testing(self, session_dir: str | None = None) -> None:
        """Open the dedicated dialog for creating or editing a test session."""
        dialog = TeachingAlgorithmTestDialog(parent=self, session_dir=session_dir)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_test_sessions()
