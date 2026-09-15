"""Verify Gemini Chat activity and tool-event presentation."""

import os
import threading
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QSizePolicy, QVBoxLayout, QWidget

from src.ui.gemini_chat_widget import AIChatWorkspace, AutoMessageDialog, _BouncingDots, _ChatBubble, GeminiChatWidget, GeminiSettingsDialog
from src.ai_control.ai_models.contracts import AIUsage
from src.ai_control.ai_tool_bridge import AIMCPResult


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


def test_turn_meta_shows_provider_reported_token_total_after_duration() -> None:
    meta = GeminiChatWidget._format_turn_meta(
        1234,
        "google/gemini-2.5-flash",
        AIMCPResult("done", 2, False, AIUsage(input_tokens=100, output_tokens=23, total_tokens=123)),
    )

    assert meta.startswith("1.23s | 123 token |")
    assert "google/gemini-2.5-flash" not in meta


def test_chat_timestamps_are_shown_only_for_user_ai_and_automatic_messages() -> None:
    _application()
    user_message = _ChatBubble("User", side="right", timestamp="12:34:56")
    ai_message = _ChatBubble("AI", side="left", timestamp="12:34:56")
    automatic_message = _ChatBubble("Automatic", side="automatic", timestamp="12:34:56")
    tool_message = _ChatBubble("Tool", side="tool")

    for message in (user_message, ai_message, automatic_message):
        assert message.timestamp_label is not None
        assert message.timestamp_label.text() == "12:34:56"
    assert tool_message.timestamp_label is None


def test_automatic_message_row_is_editable_directly_and_starts_stopped() -> None:
    dialog = AutoMessageDialog([{"id": "rule-1", "text": "Kiểm tra", "kind": "interval", "interval_seconds": 300, "enabled": False}])

    assert dialog.table.item(0, 0).text() == "Kiểm tra"
    assert dialog.table.editTriggers() & dialog.table.EditTrigger.DoubleClicked
    assert dialog.table.item(0, 3).text() == "Đã dừng"

    dialog.table.item(0, 0).setText("Nội dung mới")
    APP.processEvents()
    assert dialog.rules[0]["text"] == "Nội dung mới"


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


def test_ai_activity_button_cancels_the_active_turn() -> None:
    widget = GeminiChatWidget()
    widget._set_chat_available(True)
    cancel_event = threading.Event()
    widget._message_queue.enqueue_manual("Tin dang cho")
    widget._active_turn_cancel = cancel_event
    widget._refresh_ai_activity_button()

    assert widget.ai_activity_btn.text() == "■"
    assert widget.ai_activity_btn.isEnabled()
    widget._cancel_active_turn()

    assert cancel_event.is_set()
    assert widget._message_queue.pending() == []
    assert widget.ai_activity_btn.text() == "↵"
    assert widget.ai_activity_btn.isEnabled()


def test_pending_message_bubble_is_created_and_shows_an_empty_queue() -> None:
    widget = GeminiChatWidget()

    assert widget._queue_bubble is not None
    assert not widget._queue_bubble.isHidden()
    assert "(0)" in widget._queue_bubble.text()


def test_process_tab_title_uses_the_character_name_from_window_title() -> None:
    target = SimpleNamespace(window_title="MU GameThuVN - Season 21 (Golden - NTD3001)")

    assert AIChatWorkspace._character_name(target) == "NTD3001"


def test_pending_message_bubble_overlays_the_bottom_of_the_chat_viewport() -> None:
    widget = GeminiChatWidget()
    widget.scroll.viewport().resize(600, 300)
    widget._position_queue_bubble()
    bubble = widget._queue_bubble
    assert bubble is not None
    assert bubble.parentWidget() is widget.scroll.viewport()
    assert bubble.geometry().bottom() <= widget.scroll.viewport().rect().bottom() - 7

    widget._message_queue.enqueue_manual("Tin dang cho")
    widget._queue_expanded = True
    widget._refresh_queue_bubble()
    assert bubble.height() > 22
    assert bubble.geometry().bottom() <= widget.scroll.viewport().rect().bottom() - 7


def test_running_automatic_messages_have_a_left_overlay_bubble() -> None:
    widget = GeminiChatWidget()
    widget.scroll.viewport().resize(600, 300)
    widget._auto_rules = [{"id": "rule-1", "text": "Kiem tra", "kind": "interval", "interval_seconds": 300, "enabled": True}]
    widget._reset_auto_schedule()
    widget._position_queue_bubble()

    automatic = widget._auto_status_bubble
    queue = widget._queue_bubble
    assert automatic is not None and queue is not None
    assert automatic.parentWidget() is widget.scroll.viewport()
    assert automatic.geometry().left() < queue.geometry().left()

    widget._toggle_auto_status_bubble()
    assert automatic.height() > 22
    assert not widget._queue_expanded


def test_expanded_automatic_bubble_elides_prompt_without_hiding_remaining_time() -> None:
    widget = GeminiChatWidget()
    widget.scroll.viewport().resize(420, 300)
    long_prompt = "Ná»™i dung tá»± Ä‘á»™ng ráº¥t dÃ i " * 30
    widget._auto_rules = [{"id": "rule-1", "text": long_prompt, "kind": "interval", "interval_seconds": 300, "enabled": True}]
    widget._reset_auto_schedule()
    widget._auto_status_expanded = True
    text = widget._auto_status_text("Tá»± Ä‘á»™ng (1)", widget._auto_rules, 380)

    assert text.endswith("s")
    assert "…" in text
    assert long_prompt not in text


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


def test_double_clicking_any_chat_bubble_text_copies_the_message() -> None:
    _application()
    container = QWidget()
    layout = QVBoxLayout(container)
    message = _ChatBubble("Nội dung cần sao chép", side="automatic")
    layout.addWidget(message)
    container.show()
    APP.processEvents()

    QTest.mouseDClick(message.label, Qt.MouseButton.LeftButton)
    APP.processEvents()

    assert QApplication.clipboard().text() == "Nội dung cần sao chép"
    assert "#9a3412" in message.bubble.styleSheet()
