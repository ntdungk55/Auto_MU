"""Verify Gemini Chat activity and tool-event presentation."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QSizePolicy, QVBoxLayout, QWidget

from src.ui.gemini_chat_widget import _BouncingDots, _ChatBubble, GeminiChatWidget, GeminiSettingsDialog


APP = QApplication.instance() or QApplication([])


def _application() -> QApplication:
    return APP


def test_bouncing_dots_advance_through_animation_phases() -> None:
    _application()
    dots = _BouncingDots()
    dots._timer.stop()
    phases = []
    for _ in range(6):
        dots._advance()
        phases.append(dots._phase)
    assert phases == [1, 2, 3, 4, 5, 0]


def test_tool_error_message_includes_tool_error_and_debug_details() -> None:
    text = GeminiChatWidget._format_tool_error(
        "get_companion_summoned_state",
        {"success": False, "error": "Could not capture the selected game window", "debug": {"stage": "capture_game_window"}},
    )

    assert "Tool lỗi: get_companion_summoned_state" in text
    assert "Could not capture the selected game window" in text
    assert '"stage": "capture_game_window"' in text


def test_busy_indicator_stays_below_left_aligned_tool_bubbles() -> None:
    _application()
    widget = GeminiChatWidget()

    widget._set_busy(True)
    indicator = widget._typing_indicator
    assert indicator is not None
    assert indicator.objectName() == "aiWorkingIndicator"

    widget._append_bubble("AI đang gọi tool: example", side="tool")
    indicator_index = widget.chat_layout.indexOf(indicator)
    tool_bubble = widget.chat_layout.itemAt(indicator_index - 1).widget()
    assert isinstance(tool_bubble, _ChatBubble)
    assert tool_bubble.side == "tool"
    assert tool_bubble.bubble.objectName() == "toolCallBubble"
    assert "#b9dcff" in tool_bubble.label.styleSheet()
    assert tool_bubble.layout().itemAt(0).widget() is tool_bubble.bubble

    widget._set_busy(False)
    assert widget._typing_indicator is None


def test_system_bubble_is_centered_and_wraps_at_eighty_percent_maximum() -> None:
    _application()
    container = QWidget()
    container.resize(620, 300)
    layout = QVBoxLayout(container)
    message = _ChatBubble(
        "Đã chọn process: MU GamethuVN - Season 21 (Golden - NTD2006) " * 3,
        side="system",
    )
    layout.addWidget(message)
    layout.addStretch(1)
    container.show()
    APP.processEvents()

    width_ratio = message.bubble.width() / message.width()
    assert width_ratio <= 0.8
    assert width_ratio >= 0.76
    assert message.label.wordWrap() is True
    bubble_left = message.bubble.mapTo(message, message.bubble.rect().topLeft()).x()
    bubble_right = message.width() - bubble_left - message.bubble.width()
    assert abs(bubble_left - bubble_right) <= 2
    assert message.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Maximum
    margins = message.bubble.layout().contentsMargins()
    assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (8, 5, 8, 5)
    assert message.height() <= message.sizeHint().height() + 2


def test_short_system_bubble_uses_content_width_below_maximum() -> None:
    _application()
    container = QWidget()
    container.resize(1000, 160)
    layout = QVBoxLayout(container)
    message = _ChatBubble(
        "Đã chọn process: MU GamethuVN - Season 21 (Golden - NTD2008)",
        side="system",
    )
    layout.addWidget(message)
    layout.addStretch(1)
    container.show()
    APP.processEvents()

    assert message.bubble.width() < message.width() * 0.8
    assert message.label.wordWrap() is True
    assert message.label.height() <= message.label.fontMetrics().height() + 2
    bubble_left = message.bubble.mapTo(message, message.bubble.rect().topLeft()).x()
    bubble_right = message.width() - bubble_left - message.bubble.width()
    assert abs(bubble_left - bubble_right) <= 2


def test_tool_notification_stays_on_one_line_until_eighty_percent() -> None:
    _application()
    container = QWidget()
    container.resize(720, 160)
    layout = QVBoxLayout(container)
    message = _ChatBubble("Tool hoàn tất: switch_to_companion_character", side="tool")
    layout.addWidget(message)
    layout.addStretch(1)
    container.show()
    APP.processEvents()

    assert message.bubble.width() < message.width() * 0.8
    assert message.label.wordWrap() is True
    assert message.label.height() <= message.label.fontMetrics().height() + 2
    assert message.bubble.mapTo(message, message.bubble.rect().topLeft()).x() <= 1

    narrow = QWidget()
    narrow.resize(300, 180)
    narrow_layout = QVBoxLayout(narrow)
    wrapped_tool = _ChatBubble("Tool hoàn tất: switch_to_companion_character", side="tool")
    narrow_layout.addWidget(wrapped_tool)
    narrow_layout.addStretch(1)
    narrow.show()
    APP.processEvents()
    assert "\u200b" in wrapped_tool.label.text()
    assert wrapped_tool.label.height() > wrapped_tool.label.fontMetrics().height()


def test_user_and_ai_bubbles_use_content_width_up_to_half_of_chat_width() -> None:
    _application()
    container = QWidget()
    container.resize(720, 300)
    layout = QVBoxLayout(container)
    long_text = "Nội dung chat dài cần được wrapping theo chiều rộng khung chat. " * 4
    ai_message = _ChatBubble(long_text, side="left")
    user_message = _ChatBubble(long_text, side="right")
    layout.addWidget(ai_message)
    layout.addWidget(user_message)
    layout.addStretch(1)
    container.show()
    APP.processEvents()

    for message in (ai_message, user_message):
        width_ratio = message.bubble.width() / message.width()
        assert 0.47 <= width_ratio <= 0.5
    assert ai_message.bubble.mapTo(ai_message, ai_message.bubble.rect().topLeft()).x() <= 7
    user_left = user_message.bubble.mapTo(user_message, user_message.bubble.rect().topLeft()).x()
    assert user_message.width() - user_left - user_message.bubble.width() <= 7
    assert user_message.label.alignment() & Qt.AlignmentFlag.AlignLeft

    short_ai = _ChatBubble("OK", side="left")
    short_user = _ChatBubble("OK", side="right")
    layout.insertWidget(2, short_ai)
    layout.insertWidget(3, short_user)
    APP.processEvents()
    assert short_ai.bubble.width() / short_ai.width() < 0.2
    assert short_user.bubble.width() / short_user.width() < 0.2
    short_user_left = short_user.bubble.mapTo(short_user, short_user.bubble.rect().topLeft()).x()
    assert short_user.width() - short_user_left - short_user.bubble.width() <= 7
