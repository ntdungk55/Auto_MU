from src.ai_control.chat_message_queue import ChatMessageQueue


def test_manual_messages_keep_fifo_priority_over_automatic_messages() -> None:
    queue = ChatMessageQueue()
    queue.enqueue_automatic("auto first", "timer-a")
    queue.enqueue_manual("manual first")
    queue.enqueue_manual("manual second")

    assert [queue.pop_next().text, queue.pop_next().text, queue.pop_next().text] == [
        "manual first", "manual second", "auto first",
    ]


def test_only_one_pending_message_is_kept_per_automatic_rule() -> None:
    queue = ChatMessageQueue()

    assert queue.enqueue_automatic("run", "timer-a") is True
    assert queue.enqueue_automatic("run again", "timer-a") is False
    assert [item.text for item in queue.pending()] == ["run"]


def test_clear_discards_all_pending_manual_and_automatic_messages() -> None:
    queue = ChatMessageQueue()
    queue.enqueue_manual("manual")
    queue.enqueue_automatic("automatic", "timer-a")

    queue.clear()

    assert queue.pending() == []
