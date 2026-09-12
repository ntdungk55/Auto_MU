"""Verify Gemini Chat activity and tool-event presentation."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QSizePolicy, QVBoxLayout, QWidget

from src.ui.gemini_chat_widget import _BouncingDots, _ChatBubble, GeminiChatWidget


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


def test_busy_indicator_stays_below_left_aligned_tool_bubbles() -> None:
    _application()
    widget = GeminiChatWidget()

    widget._set_busy(True)
    indicator = widget._typing_indicator
    assert indicator is not None
    assert indicator.objectName() == "aiWorkingIndicator"

    widget._append_bubble("AI đang gọi tool: example", side="tool", meta="Scenario")
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
    container.resize(620, 160)
    layout = QVBoxLayout(container)
    message = _ChatBubble("Connected: gemini-2.5-flash", side="system")
    layout.addWidget(message)
    layout.addStretch(1)
    container.show()
    APP.processEvents()

    assert message.bubble.width() < message.width() * 0.8
    bubble_left = message.bubble.mapTo(message, message.bubble.rect().topLeft()).x()
    bubble_right = message.width() - bubble_left - message.bubble.width()
    assert abs(bubble_left - bubble_right) <= 2


def test_user_and_ai_bubbles_always_use_half_of_chat_width() -> None:
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

    short_ai = _ChatBubble("OK", side="left")
    short_user = _ChatBubble("OK", side="right")
    layout.insertWidget(2, short_ai)
    layout.insertWidget(3, short_user)
    APP.processEvents()
    assert 0.47 <= short_ai.bubble.width() / short_ai.width() <= 0.5
    assert 0.47 <= short_user.bubble.width() / short_user.width() <= 0.5
