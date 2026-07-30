"""Telegram Notifier - Send notifications via Telegram."""

import os
import requests
from ..action_type import AutoAction


class TelegramNotifier:
    """Handle Telegram notifications."""
    
    def __init__(self, ui_log_func=None):
        """Initialize Telegram notifier.
        
        Args:
            ui_log_func: Optional logging function
        """
        self.ui_log = ui_log_func or (lambda x: None)
    
    def send_simple(self, message: str) -> bool:
        """Send simple notification via Telegram without action context.
        
        Args:
            message: Message to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Get Telegram configuration
            bot_token = None
            chat_id = None
            
            # Try to load from app_state.json
            try:
                import json
                app_state_path = os.path.join(os.path.dirname(__file__), "..", "..", "app_state.json")
                if os.path.exists(app_state_path):
                    with open(app_state_path, "r", encoding="utf-8") as f:
                        state = json.load(f) or {}
                    
                    # Try to get encrypted token first
                    token_b64 = state.get("telegram_bot_token_dpapi_b64", "")
                    if token_b64:
                        try:
                            from ..dpapi import unprotect_from_b64
                            bot_token = unprotect_from_b64(token_b64)
                        except Exception:
                            pass
                    
                    # Fallback to plain text token
                    if not bot_token:
                        bot_token = state.get("telegram_bot_token", "").strip()
                    
                    # Get chat ID
                    chat_id = state.get("telegram_chat_id", "").strip()
            except Exception as e:
                self.ui_log(f"<b style='color:orange;'>[Telegram]</b> Không thể đọc app_state.json: {e}")
            
            # Fallback to environment variables
            if not bot_token:
                bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
            if not chat_id:
                chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
            
            if not bot_token or not chat_id:
                self.ui_log("<b style='color:orange;'>[Telegram]</b> Chưa cấu hình Telegram")
                return False
            
            # Send via Telegram API
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                self.ui_log(f"<b style='color:green;'>[Telegram]</b> Gửi thành công")
                return True
            else:
                self.ui_log(f"<b style='color:red;'>[Telegram]</b> Lỗi: {response.status_code}")
                return False
        except Exception as e:
            self.ui_log(f"<b style='color:red;'>[Telegram]</b> Exception: {e}")
            return False
    
    def send(self, action: AutoAction, content: str, is_gemini: bool = False) -> bool:
        """Send notification via Telegram.
        
        Args:
            action: AutoAction with notification configuration
            content: Content to send
            is_gemini: Whether content is from Gemini (for logging)
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Get Telegram configuration from app_state.json or environment
            bot_token = None
            chat_id = None
            
            # Try to load from app_state.json first
            try:
                import json
                app_state_path = os.path.join(os.path.dirname(__file__), "..", "..", "app_state.json")
                if os.path.exists(app_state_path):
                    with open(app_state_path, "r", encoding="utf-8") as f:
                        state = json.load(f) or {}
                    
                    # Try to get encrypted token first
                    token_b64 = state.get("telegram_bot_token_dpapi_b64", "")
                    if token_b64:
                        try:
                            from ..dpapi import unprotect_from_b64
                            bot_token = unprotect_from_b64(token_b64)
                        except Exception:
                            pass
                    
                    # Fallback to plain text token
                    if not bot_token:
                        bot_token = state.get("telegram_bot_token", "").strip()
                    
                    # Get chat ID
                    chat_id = state.get("telegram_chat_id", "").strip()
            except Exception as e:
                self.ui_log(f"<b style='color:orange;'>[Telegram]</b> Không thể đọc app_state.json: {e}")
            
            # Fallback to environment variables
            if not bot_token:
                bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
            if not chat_id:
                chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
            
            if not bot_token or not chat_id:
                self.ui_log("<b style='color:orange;'>[Telegram]</b> Chưa cấu hình Telegram (token hoặc chat_id trống)")
                return False
            
            # Build message
            source = "Gemini" if is_gemini else "OCR"
            message = f"[{source}] {content}"
            
            # Send via Telegram API
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                self.ui_log(f"<b style='color:green;'>[Telegram]</b> Gửi thành công ({source})")
                return True
            else:
                self.ui_log(f"<b style='color:red;'>[Telegram]</b> Lỗi: {response.status_code}")
                return False
        except Exception as e:
            self.ui_log(f"<b style='color:red;'>[Telegram]</b> Exception: {e}")
            return False
