"""
Telegram Bot notification service
"""
import requests
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Send notifications via Telegram Bot API"""
    
    BASE_URL = "https://api.telegram.org/bot{token}/{method}"
    
    @staticmethod
    def send_message(bot_token: str, chat_id: str, text: str, parse_mode: str = "HTML") -> Tuple[bool, str]:
        """
        Send text message to Telegram chat
        
        Args:
            bot_token: Bot token from @BotFather
            chat_id: Chat ID of recipient
            text: Message text (supports HTML formatting if parse_mode="HTML")
            parse_mode: "HTML" or "Markdown" or None
            
        Returns:
            (success: bool, error_message: str)
        """
        if not bot_token or not chat_id:
            return False, "Bot token hoặc Chat ID trống"
        
        url = TelegramNotifier.BASE_URL.format(token=bot_token, method="sendMessage")
        payload = {
            "chat_id": chat_id,
            "text": text,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("ok"):
                logger.info(f"Telegram message sent to {chat_id}")
                return True, ""
            else:
                error_msg = data.get("description", "Unknown error")
                logger.error(f"Telegram API error: {error_msg}")
                return False, error_msg
                
        except requests.RequestException as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(f"Telegram send failed: {error_msg}")
            return False, error_msg
    
    @staticmethod
    def send_photo(bot_token: str, chat_id: str, photo_path: str, caption: str = "") -> Tuple[bool, str]:
        """
        Send photo to Telegram chat
        
        Args:
            bot_token: Bot token from @BotFather
            chat_id: Chat ID of recipient
            photo_path: Path to image file
            caption: Optional caption text
            
        Returns:
            (success: bool, error_message: str)
        """
        if not bot_token or not chat_id:
            return False, "Bot token hoặc Chat ID trống"
        
        url = TelegramNotifier.BASE_URL.format(token=bot_token, method="sendPhoto")
        
        try:
            with open(photo_path, 'rb') as photo_file:
                files = {'photo': photo_file}
                data = {
                    'chat_id': chat_id,
                    'caption': caption,
                    'parse_mode': 'HTML'
                }
                response = requests.post(url, data=data, files=files, timeout=15)
                response.raise_for_status()
                result = response.json()
                
                if result.get("ok"):
                    logger.info(f"Telegram photo sent to {chat_id}")
                    return True, ""
                else:
                    error_msg = result.get("description", "Unknown error")
                    logger.error(f"Telegram API error: {error_msg}")
                    return False, error_msg
                    
        except FileNotFoundError:
            return False, f"File không tồn tại: {photo_path}"
        except requests.RequestException as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(f"Telegram photo send failed: {error_msg}")
            return False, error_msg
    
    @staticmethod
    def test_connection(bot_token: str, chat_id: str) -> Tuple[bool, str]:
        """
        Test Telegram bot configuration
        
        Returns:
            (success: bool, message: str)
        """
        if not bot_token:
            return False, "Bot token trống"
        if not chat_id:
            return False, "Chat ID trống"
        
        # Test bot token by calling getMe
        url = TelegramNotifier.BASE_URL.format(token=bot_token, method="getMe")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("ok"):
                return False, f"Bot token không hợp lệ: {data.get('description', 'Unknown')}"
            
            bot_info = data.get("result", {})
            bot_name = bot_info.get("first_name", "Unknown")
            bot_username = bot_info.get("username", "unknown")
            
            # Try to send a test message
            success, error = TelegramNotifier.send_message(
                bot_token, 
                chat_id, 
                "✅ <b>Test thông báo thành công!</b>\n\nBot đã được cấu hình đúng."
            )
            
            if success:
                return True, f"Kết nối thành công!\nBot: {bot_name} (@{bot_username})"
            else:
                return False, f"Bot token hợp lệ nhưng không gửi được tin nhắn đến chat_id={chat_id}\n\nLỗi: {error}\n\nKiểm tra lại Chat ID hoặc đảm bảo bạn đã start bot bằng /start"
                
        except requests.RequestException as e:
            return False, f"Không thể kết nối đến Telegram API: {str(e)}"
    
    @staticmethod
    def get_chat_id_instructions() -> str:
        """Return instructions for getting chat ID"""
        return """
<b>Cách lấy Chat ID:</b>

<b>Phương pháp 1 (Dùng @userinfobot):</b>
1. Mở Telegram, tìm kiếm <code>@userinfobot</code>
2. Nhấn Start
3. Bot sẽ trả về Chat ID của bạn (số)

<b>Phương pháp 2 (Dùng @RawDataBot):</b>
1. Tìm kiếm <code>@RawDataBot</code>
2. Nhấn Start
3. Xem dòng "id": ... trong JSON

<b>Phương pháp 3 (Dùng Web API):</b>
1. Gửi 1 tin nhắn bất kỳ cho bot của bạn
2. Truy cập: <code>https://api.telegram.org/bot&lt;YOUR_BOT_TOKEN&gt;/getUpdates</code>
3. Tìm <code>"chat":{"id":...</code> trong JSON response
""".strip()

