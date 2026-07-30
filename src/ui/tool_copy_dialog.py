"""Dialog for copying tools with new name."""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox)
from PyQt6.QtCore import Qt
from typing import Optional


class ToolCopyDialog(QDialog):
    """Dialog for entering new tool name when copying."""
    
    def __init__(self, tool_manager, parent=None):
        """Initialize the dialog.
        
        Args:
            tool_manager: ToolManager instance for validation
            parent: Parent widget
        """
        super().__init__(parent)
        self.tool_manager = tool_manager
        self.new_name: Optional[str] = None
        
        self.setWindowTitle("Sao chép Tool")
        self.setModal(True)
        self.setFixedSize(400, 150)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()
        
        # Title label
        title_label = QLabel("Nhập tên cho tool mới:")
        layout.addWidget(title_label)
        
        # Name input
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nhập tên tool mới")
        self.name_input.textChanged.connect(self._on_text_changed)
        self.name_input.returnPressed.connect(self._on_ok_clicked)
        layout.addWidget(self.name_input)
        
        # Error label
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red;")
        self.error_label.hide()
        layout.addWidget(self.error_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self._on_ok_clicked)
        self.ok_button.setEnabled(False)  # Disabled until valid name entered
        button_layout.addWidget(self.ok_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Focus on input
        self.name_input.setFocus()
    
    def _on_text_changed(self):
        """Handle text change in name input."""
        text = self.name_input.text().strip()
        
        # Clear previous error
        self.error_label.hide()
        
        # Validate name
        if not text:
            self.ok_button.setEnabled(False)
            return
        
        # Check if name already exists
        if not self.tool_manager.validate_unique_name(text):
            self.error_label.setText("Tên tool đã tồn tại")
            self.error_label.show()
            self.ok_button.setEnabled(False)
            return
        
        # Name is valid
        self.ok_button.setEnabled(True)
    
    def _on_ok_clicked(self):
        """Handle OK button click."""
        text = self.name_input.text().strip()
        
        # Final validation
        if not text:
            self.error_label.setText("Tên tool không được để trống")
            self.error_label.show()
            return
        
        if not self.tool_manager.validate_unique_name(text):
            self.error_label.setText("Tên tool đã tồn tại")
            self.error_label.show()
            return
        
        # Accept with valid name
        self.new_name = text
        self.accept()
    
    def get_new_name(self) -> Optional[str]:
        """Get the entered new name.
        
        Returns:
            New tool name if dialog was accepted, None otherwise
        """
        return self.new_name