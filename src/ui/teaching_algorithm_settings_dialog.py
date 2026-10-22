"""Settings dialog for teaching algorithm tests."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..logic.teaching_matching import (
    DEFAULT_COORDINATE_MATCH_OFFSET,
    MAX_COORDINATE_MATCH_OFFSET,
    normalize_coordinate_match_offset,
)


class TeachingAlgorithmSettingsDialog(QDialog):
    """Edit settings shared by teaching algorithm test sessions."""

    def __init__(self, settings: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Teaching Settings")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        self.match_by_coordinates_checkbox = QCheckBox("Matching theo tọa độ")
        self.match_by_coordinates_checkbox.setChecked(
            bool(settings.get("match_by_coordinates", False))
        )
        self.match_by_coordinates_checkbox.setToolTip(
            "Ưu tiên vị trí tọa độ khi so khớp ảnh teaching với ảnh test."
        )
        layout.addWidget(self.match_by_coordinates_checkbox)

        self.coordinate_offset_widget = QWidget()
        offset_layout = QHBoxLayout(self.coordinate_offset_widget)
        offset_layout.setContentsMargins(20, 0, 0, 0)
        offset_layout.addWidget(QLabel("Offset mỗi cạnh:"))
        self.coordinate_offset_spin = QSpinBox()
        self.coordinate_offset_spin.setRange(0, MAX_COORDINATE_MATCH_OFFSET)
        self.coordinate_offset_spin.setSuffix(" px")
        self.coordinate_offset_spin.setValue(
            normalize_coordinate_match_offset(
                settings.get("coordinate_offset", DEFAULT_COORDINATE_MATCH_OFFSET)
            )
        )
        self.coordinate_offset_spin.setToolTip(
            "Mở rộng vùng matching sang trái, phải, trên và dưới theo số pixel này."
        )
        offset_layout.addWidget(self.coordinate_offset_spin)
        offset_layout.addStretch()
        self.coordinate_offset_widget.setVisible(
            self.match_by_coordinates_checkbox.isChecked()
        )
        self.match_by_coordinates_checkbox.toggled.connect(
            self.coordinate_offset_widget.setVisible
        )
        layout.addWidget(self.coordinate_offset_widget)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> dict:
        return {
            "match_by_coordinates": self.match_by_coordinates_checkbox.isChecked(),
            "coordinate_offset": self.coordinate_offset_spin.value(),
        }
