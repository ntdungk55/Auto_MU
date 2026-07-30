"""
Notification module for sending alerts to external devices (Telegram, ntfy, etc.)
"""
from .telegram import TelegramNotifier
from .config_dialog import TelegramConfigDialog

__all__ = ['TelegramNotifier', 'TelegramConfigDialog']

