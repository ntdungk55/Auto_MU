"""Dialog for Gemini API settings."""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QComboBox, QGroupBox)
from PyQt6.QtCore import Qt
from typing import Callable


class GeminiSettingsDialog(QDialog):
    """Dialog to configure Gemini API Key and Model."""
    
    def __init__(self, 
                 load_saved_key: Callable[[], str],
                 save_key: Callable[[str], None],
                 load_saved_model: Callable[[], str],
                 save_model: Callable[[str], None],
                 parent=None):
        """Initialize the dialog.
        
        Args:
            load_saved_key: Function to load saved API key
            save_key: Function to save API key
            load_saved_model: Function to load saved model
            save_model: Function to save model
            parent: Parent widget
        """
        super().__init__(parent)
        self.load_saved_key = load_saved_key
        self.save_key = save_key
        self.load_saved_model = load_saved_model
        self.save_model = save_model
        
        self.setWindowTitle("Gemini API Settings")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        self._init_ui()
        self._load_settings()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout()
        
        # API Key group
        api_group = QGroupBox("API Key")
        api_layout = QVBoxLayout()
        
        api_label = QLabel("Gemini API Key:")
        api_layout.addWidget(api_label)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Nhập API Key của bạn...")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addWidget(self.api_key_input)
        
        show_key_btn = QPushButton("👁 Hiện/Ẩn")
        show_key_btn.setMaximumWidth(100)
        show_key_btn.clicked.connect(self._toggle_key_visibility)
        api_layout.addWidget(show_key_btn)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # Model group
        model_group = QGroupBox("Model")
        model_layout = QVBoxLayout()
        
        model_label = QLabel("Chọn Model:")
        model_layout.addWidget(model_label)
        
        self.model_combo = QComboBox()
        self.model_combo.addItem("gemini-1.5-flash", "gemini-1.5-flash")
        self.model_combo.addItem("gemini-1.5-pro", "gemini-1.5-pro")
        self.model_combo.addItem("gemini-2.0-flash", "gemini-2.0-flash")
        self.model_combo.addItem("gemini-2.0-flash-lite", "gemini-2.0-flash-lite")
        self.model_combo.addItem("gemini-2.0-pro", "gemini-2.0-pro")
        self.model_combo.addItem("gemini-2.5-flash", "gemini-2.5-flash")
        self.model_combo.addItem("gemini-2.5-pro", "gemini-2.5-pro")
        self.model_combo.addItem("Custom…", "custom")
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        model_layout.addWidget(self.model_combo)
        
        # Custom model input (hidden by default)
        self.custom_model_input = QLineEdit()
        self.custom_model_input.setPlaceholderText("Nhập tên model tùy chỉnh...")
        self.custom_model_input.setVisible(False)
        model_layout.addWidget(self.custom_model_input)
        
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("💾 Lưu")
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Hủy")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _on_model_changed(self, index):
        """Handle model selection change."""
        is_custom = self.model_combo.currentData() == "custom"
        self.custom_model_input.setVisible(is_custom)
    
    def _toggle_key_visibility(self):
        """Toggle API key visibility."""
        if self.api_key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
    
    def _load_settings(self):
        """Load saved settings."""
        try:
            # Load API key
            saved_key = self.load_saved_key()
            if saved_key:
                self.api_key_input.setText(saved_key)
            
            # Load model
            saved_model = self.load_saved_model()
            if saved_model:
                # Try to find in predefined models
                index = self.model_combo.findData(saved_model)
                if index >= 0:
                    self.model_combo.setCurrentIndex(index)
                else:
                    # Custom model
                    custom_index = self.model_combo.findData("custom")
                    if custom_index >= 0:
                        self.model_combo.setCurrentIndex(custom_index)
                        self.custom_model_input.setText(saved_model)
                        self.custom_model_input.setVisible(True)
        except Exception as e:
            print(f"[GeminiSettingsDialog] Error loading settings: {e}")
    
    def accept(self):
        """Save settings and close."""
        try:
            # Save API key
            api_key = self.api_key_input.text().strip()
            if api_key:
                self.save_key(api_key)
            
            # Save model
            if self.model_combo.currentData() == "custom":
                # Custom model
                model = self.custom_model_input.text().strip()
            else:
                # Predefined model
                model = self.model_combo.currentData()
            
            if model:
                self.save_model(model)
            
            super().accept()
        except Exception as e:
            print(f"[GeminiSettingsDialog] Error saving settings: {e}")
            super().reject()
