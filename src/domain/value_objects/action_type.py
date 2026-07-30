"""Action type enumeration - Single Source of Truth."""

from enum import Enum


class ActionType(Enum):
    """Types of automation actions."""
    KEYBOARD = "Bàn phím"
    MOUSE_CLICK = "Click Chuột"
    IMAGE_DETECT = "Phát hiện ảnh"
    WAIT = "Chờ"
    READ_PASSIVE = "Đọc thụ động"
