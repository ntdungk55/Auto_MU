"""Priority queue for chat turns: manual messages precede scheduled messages."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class QueuedChatMessage:
    text: str
    source: str  # manual | automatic
    rule_id: str | None = None
    image_path: str | None = None


class ChatMessageQueue:
    def __init__(self) -> None:
        self._manual: deque[QueuedChatMessage] = deque()
        self._automatic: deque[QueuedChatMessage] = deque()
        self._active_event_ids: set[str] = set()

    def enqueue_manual(self, text: str, image_path: str | None = None) -> None:
        self._manual.append(QueuedChatMessage(text=text, source="manual", image_path=image_path))

    def enqueue_automatic(self, text: str, rule_id: str) -> bool:
        if any(item.rule_id == rule_id for item in self._automatic):
            return False
        self._automatic.append(QueuedChatMessage(text=text, source="automatic", rule_id=rule_id))
        return True

    def enqueue_event(self, text: str, event_id: str) -> bool:
        """Queue an event prompt unless the same event is pending or active."""
        if event_id in self._active_event_ids or any(item.rule_id == event_id for item in self._automatic):
            return False
        self._automatic.append(QueuedChatMessage(text=text, source="event", rule_id=event_id))
        return True

    def mark_active(self, message: QueuedChatMessage) -> None:
        """Track an event message currently being processed."""
        if message.source == "event" and message.rule_id:
            self._active_event_ids.add(message.rule_id)

    def clear_active(self, message: QueuedChatMessage) -> None:
        """Release an active event identity after processing."""
        if message.source == "event" and message.rule_id:
            self._active_event_ids.discard(message.rule_id)

    def pop_next(self) -> QueuedChatMessage | None:
        return self._manual.popleft() if self._manual else (self._automatic.popleft() if self._automatic else None)

    def pending(self) -> list[QueuedChatMessage]:
        return [*self._manual, *self._automatic]

    def clear(self) -> None:
        self._manual.clear()
        self._automatic.clear()
        self._active_event_ids.clear()
