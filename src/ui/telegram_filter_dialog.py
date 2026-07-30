"""Telegram Filter Dialog - Configure message filtering for Telegram notifications."""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QTextEdit, QGroupBox, QSpinBox)
from PyQt6.QtCore import Qt


class TelegramFilterDialog(QDialog):
    """Dialog for configuring Telegram notification filters."""
    
    def __init__(self, parent=None, filter_keywords: str = "", dedup_minutes: int = 1):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Cấu hình Filter Telegram")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout()
        
        # Filter keywords section
        filter_group = QGroupBox("🔍 Từ khóa bắt buộc")
        filter_layout = QVBoxLayout()
        
        filter_label = QLabel("Nhập từ khóa (cách nhau bằng dấu phẩy hoặc |):")
        filter_layout.addWidget(filter_label)
        
        self.filter_input = QLineEdit()
        self.filter_input.setText(filter_keywords)
        self.filter_input.setPlaceholderText("Ví dụ: success, completed | done")
        filter_layout.addWidget(self.filter_input)
        
        # Help text
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setMaximumHeight(120)
        help_text.setText(
            "📝 Hướng dẫn:\n"
            "• AND filter: 'keyword1, keyword2' → cả hai phải có\n"
            "• OR filter: 'keyword1 | keyword2' → chỉ cần một\n"
            "• Kết hợp: 'keyword1, keyword2 | keyword3' → (keyword1 AND keyword2) OR keyword3\n"
            "• Không phân biệt chữ hoa/thường"
        )
        filter_layout.addWidget(help_text)
        
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # Deduplication section
        dedup_group = QGroupBox("🔄 Tránh lặp thông báo")
        dedup_layout = QHBoxLayout()
        
        dedup_label = QLabel("Không gửi lặp trong vòng:")
        dedup_layout.addWidget(dedup_label)
        
        self.dedup_spin = QSpinBox()
        self.dedup_spin.setMinimum(1)
        self.dedup_spin.setMaximum(60)
        self.dedup_spin.setValue(dedup_minutes)
        self.dedup_spin.setSuffix(" phút")
        dedup_layout.addWidget(self.dedup_spin)
        
        dedup_layout.addStretch()
        dedup_group.setLayout(dedup_layout)
        layout.addWidget(dedup_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Hủy")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def get_filter_keywords(self) -> str:
        """Get filter keywords from input."""
        return self.filter_input.text().strip()
    
    def get_dedup_minutes(self) -> int:
        """Get deduplication time in minutes."""
        return self.dedup_spin.value()
