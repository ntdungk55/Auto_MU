"""White Wizard + Red Dragon event sub-handler."""

import re
import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Optional

from .event_tracking_helper import normalize_ocr_text


EVENT_SCHEDULE = [
    "00:10", "01:10", "08:10", "09:10", "10:10", "11:10", "11:40",
    "12:10", "12:40", "13:10", "14:10", "15:10", "16:10", "17:10",
    "18:10", "19:10", "19:40", "20:10", "20:40", "21:10", "21:40",
    "22:10", "23:10",
]
RESET_MINUTES = 25
BOSS_DISPLAY = {
    "phu thuy trang": "Phù Thủy Trắng",
    "rong do": "Rồng Đỏ",
}
BOSS_MAX_COUNT = {
    "phu thuysstrang": 2,
    "rong do": 2,
}
PATTERN_KILL = r"(.+?)\s+da bi tieu diet boi\s+.+?\s+va dong doi tai\s+(.+)"


class WhiteWizardRedDragonHandler:
    """Handle White Wizard + Red Dragon kill notifications from Monster Invasion."""

    def __init__(
        self,
        match_threshold: float,
        telegram_notifier: object,
        log_signal_emit: Callable[[str], None],
    ) -> None:
        self._threshold = match_threshold
        self._telegram = telegram_notifier
        self._log = log_signal_emit
        self._state: str = "WAITING"
        self._channel_at_start: Optional[str] = None
        self._channel_current: Optional[str] = None
        self._killed_map: dict[str, int] = {"phu thuy trang": 0, "rong do": 0}
        self._active_since: Optional[float] = None
        self._lock = threading.Lock()
        self._next_event_time: datetime = self._calculate_next_event_time()

    def _calculate_next_event_time(self) -> datetime:
        """Find the next fixed event schedule slot."""
        now = datetime.now()
        for slot in EVENT_SCHEDULE:
            hour, minute = map(int, slot.split(":"))
            event_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if event_time > now:
                self._log(f"[WW+RD] Next event: {event_time.strftime('%H:%M')}")
                return event_time

        hour, minute = map(int, EVENT_SCHEDULE[0].split(":"))
        tomorrow = now + timedelta(days=1)
        event_time = tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
        self._log(f"[WW+RD] Next event: {event_time.strftime('%H:%M')}")
        return event_time

    def _reset_counts(self) -> None:
        self._killed_map = {"phu thuy trang": 0, "rong do": 0}

    def _check_event_start(self) -> None:
        if self._state != "WAITING":
            return
        if datetime.now() < self._next_event_time:
            return
        self._state = "ACTIVE"
        self._channel_at_start = self._channel_current
        self._reset_counts()
        self._active_since = time.time()
        self._next_event_time = self._calculate_next_event_time()
        self._log("[WW+RD] Event ACTIVE")

    def _check_reset_timer(self) -> None:
        if self._state != "ACTIVE" or self._active_since is None:
            return
        if time.time() - self._active_since < RESET_MINUTES * 60:
            return
        self._state = "WAITING"
        self._active_since = None
        self._channel_at_start = None
        self._reset_counts()
        self._log("[WW+RD] Reset after 25 minutes, back to WAITING")

    def _resolve_boss(self, extracted_name: str) -> Optional[str]:
        try:
            from rapidfuzz import fuzz as _rf
            best_score = -1.0
            best_key = None
            for key in BOSS_DISPLAY:
                score = float(_rf.partial_ratio(key, extracted_name))
                if score >= self._threshold and score > best_score:
                    best_score = score
                    best_key = key
            return best_key
        except ImportError:
            for key in BOSS_DISPLAY:
                if key in extracted_name:
                    return key
            return None

    def on_channel_text(self, text: str) -> None:
        """Update current channel and drive scheduled state transitions."""
        if not text:
            return
        with self._lock:
            self._channel_current = normalize_ocr_text(text)
            self._check_event_start()
            self._check_reset_timer()

    def on_notify_text(self, text: str) -> None:
        """Process kill notification OCR text. Does not cache duplicate text."""
        if not text:
            return
        with self._lock:
            self._check_reset_timer()
            if self._state != "ACTIVE" or self._channel_at_start is None:
                return

            normalized = normalize_ocr_text(text)
            match = re.search(PATTERN_KILL, normalized)
            if not match:
                return

            canonical_key = self._resolve_boss(match.group(1).strip())
            if canonical_key is None:
                return
            if self._killed_map[canonical_key] >= BOSS_MAX_COUNT[canonical_key]:
                return
            if self._channel_current != self._channel_at_start:
                self._log(f"[WW+RD] Channel changed, skip: {match.group(1).strip()}")
                return

            self._killed_map[canonical_key] += 1
            self._send_kill_message(canonical_key, match.group(2).strip())

            if sum(self._killed_map.values()) >= sum(BOSS_MAX_COUNT.values()):
                self._state = "WAITING"
                self._active_since = None
                self._log("[WW+RD] All bosses killed, back to WAITING")

    def _send_kill_message(self, canonical_key: str, map_name: str) -> None:
        remaining_white = BOSS_MAX_COUNT["phu thuy trang"] - self._killed_map["phu thuy trang"]
        remaining_red = BOSS_MAX_COUNT["rong do"] - self._killed_map["rong do"]
        message = (
            f"{BOSS_DISPLAY[canonical_key]} đã bị tiêu diệt tại {map_name} "
            f"(SV {self._channel_current})\n"
            f"Còn {remaining_white} Phù Thủy Trắng và {remaining_red} Rồng Đỏ"
        )
        try:
            if self._telegram:
                self._telegram.send_simple(message)
        except Exception as e:
            self._log(f"[WW+RD] Telegram error: {e}")

    def reset(self) -> None:
        """Reset handler state."""
        self._state = "WAITING"
        self._channel_at_start = None
        self._channel_current = None
        self._active_since = None
        self._reset_counts()
