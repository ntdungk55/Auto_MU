"""Wait Action Settings Dialog."""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QSpinBox, QGroupBox, QWidget, QScrollArea)
from PyQt6.QtCore import Qt
from ..logic.action_type import AutoAction


class WaitSettingsDialog(QDialog):
    """Dialog for configuring WAIT action settings."""
    
    def __init__(self, action: AutoAction, parent=None):
        super().__init__(parent)
        self.action = action
        self.setWindowTitle("Cài đặt Wait Action")
        self.setFixedSize(400, 200)
        self._init_ui()
        self._load_settings()
    
    def _init_ui(self):
        """Initialize UI components."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # Content widget
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        
        # Wait time group
        wait_group = QGroupBox("Thời gian chờ")
        wait_layout = QVBoxLayout()
        
        timeout_row = QHBoxLayout()
        timeout_row.addWidget(QLabel("Thời gian chờ:"))
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setMinimum(1)
        self.timeout_spin.setMaximum(36000)  # Max 1 hour
        self.timeout_spin.setValue(10)
        self.timeout_spin.setSuffix(" x 100ms")
        self.timeout_spin.setToolTip("Thời gian chờ (đơn vị 100ms)")
        timeout_row.addWidget(self.timeout_spin)
        timeout_row.addStretch()
        wait_layout.addLayout(timeout_row)
        
        wait_group.setLayout(wait_layout)
        layout.addWidget(wait_group)
        
        # Add stretch
        layout.addStretch()
        
        # Set content widget to scroll area
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(10, 5, 10, 10)
        btn_layout.addStretch()
        ok_btn = QPushButton("Lưu")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Hủy")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout)
        
        self.setLayout(main_layout)
    
    def _load_settings(self):
        """Load settings from action."""
        timeout_value = float(getattr(self.action, 'timeout', 1.0))
        self.timeout_spin.setValue(max(1, int(round(timeout_value * 10))))
    
    def get_settings(self) -> dict:
        """Get settings from dialog.
        
        Returns:
            Dict with wait settings
        """
        return {
            "timeout": self.timeout_spin.value() / 10.0,
        }
