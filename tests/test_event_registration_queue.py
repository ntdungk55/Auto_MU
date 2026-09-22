from src.ai_control.chat_message_queue import ChatMessageQueue


def test_event_queue_rejects_duplicate_pending_event_id() -> None:
    queue = ChatMessageQueue()

    assert queue.enqueue_event("Check the character", "event-1") is True
    assert queue.enqueue_event("Check the character again", "event-1") is False


def test_event_queue_rejects_event_id_that_is_currently_active() -> None:
    queue = ChatMessageQueue()
    assert queue.enqueue_event("Check the character", "event-1") is True
    active = queue.pop_next()
    assert active is not None
    queue.mark_active(active)

    assert queue.enqueue_event("Check the character again", "event-1") is False


def test_deleting_event_does_not_remove_already_queued_prompt() -> None:
    queue = ChatMessageQueue()
    assert queue.enqueue_event("Keep this prompt", "deleted-event") is True

    assert [message.text for message in queue.pending()] == ["Keep this prompt"]
