"""
Telegram notification configuration dialog
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QTextEdit, QGroupBox)
from PyQt6.QtCore import Qt
import os
import json
from .telegram import TelegramNotifier

try:
    from ..dpapi import protect_to_b64, unprotect_from_b64
except ImportError:
    protect_to_b64 = None
    unprotect_from_b64 = None


class TelegramConfigDialog(QDialog):
    """Dialog để cấu hình Telegram Bot notification"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cài đặt Telegram Notification")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        self._init_ui()
        self._load_settings()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        # Instructions group
        instruction_group = QGroupBox("📖 Hướng dẫn setup Telegram Bot")
        instruction_layout = QVBoxLayout()
        
        instruction_text = QTextEdit()
        instruction_text.setReadOnly(True)
        instruction_text.setMaximumHeight(200)
        instruction_text.setHtml("""
<h3>Bước 1: Tạo Bot Token</h3>
<ol>
<li>Mở Telegram, tìm kiếm <b>@BotFather</b></li>
<li>Gửi lệnh: <code>/newbot</code></li>
<li>Đặt tên cho bot (vd: My Automation Bot)</li>
<li>Đặt username cho bot (vd: my_auto_bot)</li>
<li>BotFather sẽ trả về <b>Bot Token</b> (dạng: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz)</li>
<li>Copy token đó và dán vào ô "Bot Token" bên dưới</li>
</ol>

<h3>Bước 2: Lấy Chat ID</h3>
<ol>
<li>Tìm kiếm <b>@userinfobot</b> trên Telegram</li>
<li>Nhấn Start</li>
<li>Bot sẽ trả về Chat ID của bạn (dạng: 123456789)</li>
<li>Copy Chat ID đó và dán vào ô "Chat ID" bên dưới</li>
</ol>

<h3>Bước 3: Start Bot</h3>
<ol>
<li>Tìm kiếm bot của bạn trên Telegram (username đã tạo ở Bước 1)</li>
<li>Nhấn <b>Start</b> để cho phép bot gửi tin nhắn cho bạn</li>
</ol>
""")
        instruction_layout.addWidget(instruction_text)
        instruction_group.setLayout(instruction_layout)
        layout.addWidget(instruction_group)
        
        # Settings group
        settings_group = QGroupBox("⚙️ Cấu hình")
        settings_layout = QVBoxLayout()
        
        # Bot Token
        token_label = QLabel("Bot Token:")
        self.token_edit = QLineEdit()
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_edit.setPlaceholderText("1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
        
        token_row = QHBoxLayout()
        token_row.addWidget(token_label, 1)
        token_row.addWidget(self.token_edit, 3)
        
        show_token_btn = QPushButton("👁️ Hiện")
        show_token_btn.setCheckable(True)
        show_token_btn.setMaximumWidth(60)
        show_token_btn.toggled.connect(lambda checked: 
            self.token_edit.setEchoMode(QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password)
        )
        token_row.addWidget(show_token_btn)
        settings_layout.addLayout(token_row)
        
        # Chat ID
        chat_id_label = QLabel("Chat ID:")
        self.chat_id_edit = QLineEdit()
        self.chat_id_edit.setPlaceholderText("123456789")
        
        chat_id_row = QHBoxLayout()
        chat_id_row.addWidget(chat_id_label, 1)
        chat_id_row.addWidget(self.chat_id_edit, 3)
        settings_layout.addLayout(chat_id_row)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Test button
        self.test_btn = QPushButton("🧪 Test kết nối (gửi tin nhắn thử)")
        self.test_btn.clicked.connect(self._test_connection)
        layout.addWidget(self.test_btn)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("💾 Lưu")
        save_btn.clicked.connect(self._save_and_close)
        save_btn.setDefault(True)
        
        cancel_btn = QPushButton("❌ Hủy")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def _app_state_path(self) -> str:
        """Get app_state.json path"""
        try:
            return os.path.join(
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")), 
                "app_state.json"
            )
        except Exception:
            return os.path.join(os.getcwd(), "app_state.json")
    
    def _load_app_state(self) -> dict:
        """Load app_state.json"""
        path = self._app_state_path()
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f) or {}
        except Exception:
            pass
        return {}
    
    def _save_app_state(self, state: dict):
        """Save app_state.json"""
        path = self._app_state_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def _load_settings(self):
        """Load saved Telegram settings"""
        state = self._load_app_state()
        
        # Load bot token (DPAPI encrypted)
        if protect_to_b64 and unprotect_from_b64:
            token_b64 = state.get("telegram_bot_token_dpapi_b64", "")
            if token_b64:
                try:
                    token = unprotect_from_b64(token_b64)
                    self.token_edit.setText(token)
                except Exception:
                    pass
        
        # Load chat ID (plain text, not sensitive)
        chat_id = state.get("telegram_chat_id", "")
        self.chat_id_edit.setText(chat_id)
    
    def _save_and_close(self):
        """Save settings and close dialog"""
        bot_token = self.token_edit.text().strip()
        chat_id = self.chat_id_edit.text().strip()
        
        if not bot_token:
            QMessageBox.warning(self, "Thiếu Bot Token", "Vui lòng nhập Bot Token")
            return
        
        if not chat_id:
            QMessageBox.warning(self, "Thiếu Chat ID", "Vui lòng nhập Chat ID")
            return
        
        # Save to app_state.json
        state = self._load_app_state()
        
        # Encrypt bot token with DPAPI
        if protect_to_b64:
            state["telegram_bot_token_dpapi_b64"] = protect_to_b64(bot_token)
        else:
            state["telegram_bot_token"] = bot_token  # Fallback: plain text
        
        state["telegram_chat_id"] = chat_id
        
        self._save_app_state(state)
        
        QMessageBox.information(
            self, 
            "Lưu thành công", 
            "Cài đặt Telegram đã được lưu.\n\nBạn có thể bật thông báo trong Action Settings."
        )
        self.accept()
    
    def _test_connection(self):
        """Test Telegram connection"""
        bot_token = self.token_edit.text().strip()
        chat_id = self.chat_id_edit.text().strip()
        
        if not bot_token:
            QMessageBox.warning(self, "Thiếu Bot Token", "Vui lòng nhập Bot Token trước khi test")
            return
        
        if not chat_id:
            QMessageBox.warning(self, "Thiếu Chat ID", "Vui lòng nhập Chat ID trước khi test")
            return
        
        # Disable button during test
        self.test_btn.setEnabled(False)
        self.test_btn.setText("⏳ Đang test...")
        
        # Run test
        success, message = TelegramNotifier.test_connection(bot_token, chat_id)
        
        # Re-enable button
        self.test_btn.setEnabled(True)
        self.test_btn.setText("🧪 Test kết nối (gửi tin nhắn thử)")
        
        # Show result
        if success:
            QMessageBox.information(
                self, 
                "✅ Kết nối thành công", 
                f"{message}\n\nKiểm tra Telegram để xem tin nhắn test!"
            )
        else:
            QMessageBox.critical(
                self, 
                "❌ Kết nối thất bại", 
                f"Không thể kết nối đến Telegram.\n\n{message}"
            )

