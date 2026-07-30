"""Golden Invasion sub-handler for use within Monster Invasion."""

import re
import threading
from typing import Optional, Callable
from datetime import datetime, timedelta

from .event_tracking_helper import normalize_ocr_text

try:
    from rapidfuzz import fuzz as _fuzz
    def _fuzzy_match(pattern: str, text: str, threshold: float) -> bool:
        return _fuzz.partial_ratio(pattern, text) >= threshold
except ImportError:
    def _fuzzy_match(pattern: str, text: str, threshold: float) -> bool:  # type: ignore[misc]
        return pattern in text


_BOSS_DISPLAY: dict[str, str] = {
    "kim thiet vuong": "Kim Thiết Vương",
    "kim xa vuong": "Kim Xạ Vương",
    "chien binh vang": "Chiến Binh Vàng",
    "nguoi may vang": "Người Máy Vàng",
    "kim ngu tinh": "Kim Ngư Tinh",
    "kim ngu vuong": "Kim Ngư Vương",
    "kim xa thu": "Kim Xạ Thủ",
}
_BOSS_CANONICAL_KEYS = list(_BOSS_DISPLAY.keys())
PATTERNS_KILL = [
    r"(.+?)\s+da bi tieu diet boi\s+.+?\s+va dong doi tai\s+(.+)",
    r"(.+?)\s+da bi tieu diet boi\s+.+?\s+va dong dong tai\s+(.+)",
    r"(.+?)\s+da bi tieu diet boi\s+.+?\s+tai\s+(.+)",
]


class GoldenInvasionSubHandler:
    """Golden Invasion sub-handler for Monster Invasion fan-out.

    Same logic as GoldenInvasionHandler but receives text via fan-out
    from MonsterInvasionHandler instead of direct subscription.
    """

    def __init__(
        self,
        server_time: str,
        match_threshold: float,
        telegram_notifier: object,
        log_signal_emit: Callable[[str], None],
    ) -> None:
        self._server_time = server_time
        self._threshold = match_threshold
        self._telegram = telegram_notifier
        self._log = log_signal_emit
        self._state: str = "WAITING"
        self._channel_at_start: Optional[str] = None
        self._channel_current: Optional[str] = None
        self._killed_set: set = set()
        self._remaining_set: set = set(_BOSS_CANONICAL_KEYS)
        self._lock = threading.Lock()
        self._next_event_time: Optional[datetime] = None
        self._calculate_next_event_time()

    def _calculate_next_event_time(self) -> None:
        """Calculate next event time (every 3 hours from server_time base)."""
        now = datetime.now()
        hour, minute = map(int, self._server_time.split(":"))
        base_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        while base_time <= now:
            base_time += timedelta(hours=3)
        self._next_event_time = base_time
        self._log(f"[Golden Invasion] Next event: {base_time.strftime('%H:%M:%S')}")

    def _check_event_start(self) -> None:
        if self._state == "WAITING" and self._next_event_time:
            if datetime.now() >= self._next_event_time:
                self._state = "ACTIVE"
                self._channel_at_start = self._channel_current
                self._killed_set.clear()
                self._remaining_set = set(_BOSS_CANONICAL_KEYS)
                self._log("[Golden Invasion] Event ACTIVE")
                self._calculate_next_event_time()

    def _resolve_boss(self, extracted_name: str) -> Optional[str]:
        if extracted_name in _BOSS_DISPLAY:
            return extracted_name
        best_score = -1.0
        best_key: Optional[str] = None
        for norm_key in _BOSS_CANONICAL_KEYS:
            try:
                from rapidfuzz import fuzz as _rf
                score = float(_rf.partial_ratio(norm_key, extracted_name))
            except ImportError:
                b_words = set(norm_key.split())
                n_words = set(extracted_name.split())
                common = b_words & n_words
                score = (len(common) / max(len(b_words), 1)) * 100.0
            if score >= self._threshold and score > best_score:
                best_score = score
                best_key = norm_key
        return best_key

    def on_channel_text(self, text: str) -> None:
        """Update channel_current from Vung 1 OCR."""
        if not text:
            return
        with self._lock:
            self._channel_current = normalize_ocr_text(text)
            self._check_event_start()

    def on_notify_text(self, text: str) -> None:
        """Process kill notification from Vung 2 OCR."""
        if not text or self._state != "ACTIVE":
            return
        with self._lock:
            if self._state != "ACTIVE":
                return
            if self._channel_at_start is None:
                return
            normalized = normalize_ocr_text(text)
            for pattern in PATTERNS_KILL:
                match = re.search(pattern, normalized)
                if not match:
                    continue
                extracted_boss = match.group(1).strip()
                canonical_key = self._resolve_boss(extracted_boss)
                if canonical_key is None:
                    continue
                if canonical_key in self._killed_set:
                    continue
                if self._channel_current != self._channel_at_start:
                    self._log(f"[Golden Invasion] Channel changed, skip: {extracted_boss}")
                    continue
                self._killed_set.add(canonical_key)
                self._remaining_set.discard(canonical_key)
                display_name = _BOSS_DISPLAY[canonical_key]
                remaining_display = [_BOSS_DISPLAY[k] for k in self._remaining_set]
                remaining_str = (
                    ", ".join(remaining_display) if remaining_display else "(không còn con nào)"
                )
                message = (
                    f"{display_name} đã bị tiêu diệt ở SV {self._channel_current}\n"
                    f"SV {self._channel_current} hiện tại còn {remaining_str}"
                )
                self._send_telegram(message)
                if not self._remaining_set:
                    self._state = "WAITING"
                    self._log("[Golden Invasion] All bosses killed, back to WAITING")
                break

    def _send_telegram(self, message: str) -> None:
        try:
            if self._telegram:
                self._telegram.send_simple(message)
        except Exception as e:
            self._log(f"[Golden Invasion] Telegram error: {e}")

    def reset(self) -> None:
        """Reset state to WAITING, clear sets."""
        self._state = "WAITING"
        self._channel_at_start = None
        self._channel_current = None
        self._killed_set.clear()
        self._remaining_set = set(_BOSS_CANONICAL_KEYS)
