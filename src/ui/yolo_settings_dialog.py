"""Dedicated settings dialog for the realtime YOLO monitor."""

from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
)

from ..logic.app_paths import get_learning_root, get_yolo_models_root
from ..logic.vision.yolo.model_manager import YoloModelManager
from ..logic.vision.yolo.training import prepare_nameplate_dataset, train_nameplate_model


class _YoloTrainingWorker(QThread):
    progress = pyqtSignal(str)
    completed = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, source_root: str, parent=None) -> None:
        super().__init__(parent)
        self.source_root = source_root

    def run(self) -> None:
        try:
            dataset_root = str(Path(get_yolo_models_root()).parent.parent / "datasets" / "nameplate")
            prepare_nameplate_dataset(self.source_root, dataset_root, self.progress.emit)
            model_path = train_nameplate_model(dataset_root, progress=self.progress.emit)
            self.completed.emit(model_path)
        except Exception as exc:
            self.failed.emit(str(exc))


class YoloSettingsDialog(QDialog):
    """Configure realtime YOLO without cluttering the Window State panel."""

    def __init__(self, settings: dict | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("YOLO Settings")
        self.setMinimumWidth(560)
        settings = settings or {}

        layout = QVBoxLayout(self)
        form = QFormLayout()

        source_row = QHBoxLayout()
        self.source_input = QLineEdit(str(settings.get("source_folder") or get_learning_root()))
        source_row.addWidget(self.source_input, 1)
        source_button = QPushButton("Chọn thư mục")
        source_button.clicked.connect(self._select_source_folder)
        source_row.addWidget(source_button)
        form.addRow("Teaching source:", source_row)

        self.model_combo = QComboBox()
        self.model_combo.addItem("Mặc định (Nameplate)", "")
        selected_model = str(settings.get("model_path") or "")
        for model_path in self._available_models():
            if os.path.abspath(model_path) == os.path.abspath(selected_model):
                selected_model = model_path
            self.model_combo.addItem(os.path.basename(model_path), model_path)
        if selected_model:
            index = self.model_combo.findData(selected_model)
            if index < 0:
                self.model_combo.addItem(os.path.basename(selected_model), selected_model)
                index = self.model_combo.count() - 1
            self.model_combo.setCurrentIndex(index)
        form.addRow("Model:", self.model_combo)

        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.01, 0.99)
        self.confidence_spin.setSingleStep(0.01)
        self.confidence_spin.setDecimals(2)
        self.confidence_spin.setValue(float(settings.get("confidence", 0.25) or 0.25))
        form.addRow("Confidence:", self.confidence_spin)

        self.iou_spin = QDoubleSpinBox()
        self.iou_spin.setRange(0.01, 0.99)
        self.iou_spin.setSingleStep(0.01)
        self.iou_spin.setDecimals(2)
        self.iou_spin.setValue(float(settings.get("iou", 0.45) or 0.45))
        form.addRow("IoU:", self.iou_spin)

        layout.addLayout(form)
        layout.addWidget(QLabel("Không chọn model = tự dùng model nameplate.onnx."))
        self.training_status = QLabel("Chưa train model nameplate.")
        self.train_button = QPushButton("Chuẩn bị dataset và train nameplate")
        self.train_button.clicked.connect(self._start_training)
        layout.addWidget(self.training_status)
        layout.addWidget(self.train_button)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._training_worker: _YoloTrainingWorker | None = None

    def _start_training(self) -> None:
        if self._training_worker is not None and self._training_worker.isRunning():
            return
        source = os.path.abspath(self.source_input.text().strip() or get_learning_root())
        self.train_button.setEnabled(False)
        self.training_status.setText("Đang chuẩn bị dataset...")
        self._training_worker = _YoloTrainingWorker(source, self)
        self._training_worker.progress.connect(self.training_status.setText)
        self._training_worker.completed.connect(self._training_completed)
        self._training_worker.failed.connect(self._training_failed)
        self._training_worker.start()

    def _training_completed(self, model_path: str) -> None:
        self.train_button.setEnabled(True)
        self.training_status.setText(f"Đã tạo model: {model_path}")
        self.model_combo.setCurrentIndex(0)
        QMessageBox.information(self, "Train hoàn tất", f"Đã tạo model nameplate:\n{model_path}")

    def _training_failed(self, message: str) -> None:
        self.train_button.setEnabled(True)
        self.training_status.setText("Train thất bại.")
        QMessageBox.critical(self, "Train thất bại", message)

    @staticmethod
    def _available_models() -> list[str]:
        # The default nameplate model is represented by the explicit default item.
        # Only show additional runtime models in the selectable list.
        return sorted(
            path for path in YoloModelManager.list_models()
            if os.path.basename(path).lower() not in {"yolo11n.onnx", "nameplate.onnx"}
        )

    def _select_source_folder(self) -> None:
        root = os.path.abspath(get_learning_root())
        os.makedirs(root, exist_ok=True)
        folder = QFileDialog.getExistingDirectory(self, "Chọn teaching source", root)
        if not folder:
            return
        selected = os.path.abspath(folder)
        try:
            valid = os.path.commonpath([root, selected]) == root
        except ValueError:
            valid = False
        if not valid:
            QMessageBox.warning(self, "Teaching source", f"Chỉ được chọn thư mục bên trong:\n{root}")
            return
        self.source_input.setText(selected)

    def _validate_and_accept(self) -> None:
        root = os.path.abspath(get_learning_root())
        source = os.path.abspath(self.source_input.text().strip() or root)
        try:
            valid = os.path.commonpath([root, source]) == root
        except ValueError:
            valid = False
        if not valid:
            QMessageBox.warning(self, "Teaching source", f"Chỉ được chọn thư mục bên trong:\n{root}")
            return
        self.source_input.setText(source)
        self.accept()

    def get_settings(self) -> dict:
        return {
            "source_folder": self.source_input.text().strip(),
            "model_path": str(self.model_combo.currentData() or ""),
            "confidence": float(self.confidence_spin.value()),
            "iou": float(self.iou_spin.value()),
        }
