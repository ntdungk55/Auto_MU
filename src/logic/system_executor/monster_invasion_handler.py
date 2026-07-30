"""Monster Invasion event handler - fan-out OCR text to sub-handlers."""

import threading
from typing import Callable


class MonsterInvasionHandler:
    """Fan-out handler for Monster Invasion event.

    Receives OCR text from 2 shared subscriptions (channel + notify)
    and dispatches to enabled sub-handlers independently.
    Each sub-handler processes text and sends Telegram notifications.
    """

    def __init__(
        self,
        sub_handlers: list,
        log_signal_emit: Callable[[str], None],
    ) -> None:
        self._sub_handlers = sub_handlers
        self._log = log_signal_emit
        self._lock = threading.Lock()

    def on_channel_text(self, text: str) -> None:
        """Fan-out channel OCR text to all sub-handlers."""
        with self._lock:
            for handler in self._sub_handlers:
                try:
                    handler.on_channel_text(text)
                except Exception as e:
                    self._log(f"[Monster Invasion] Sub-handler error (channel): {e}")

    def on_notify_text(self, text: str) -> None:
        """Fan-out notify OCR text to all sub-handlers."""
        with self._lock:
            for handler in self._sub_handlers:
                try:
                    handler.on_notify_text(text)
                except Exception as e:
                    self._log(f"[Monster Invasion] Sub-handler error (notify): {e}")

    def reset(self) -> None:
        """Reset all sub-handlers."""
        for handler in self._sub_handlers:
            try:
                handler.reset()
            except Exception:
                pass
