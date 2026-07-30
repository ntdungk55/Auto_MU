"""Imperial Guardian event tracking handler."""

import re
import time
import threading
from typing import Optional, Callable

from .event_tracking_helper import normalize_ocr_text

try:
    from rapidfuzz import fuzz as _fuzz
    def _fuzzy_match(pattern: str, text: str, threshold: float) -> bool:
        return _fuzz.partial_ratio(pattern, text) >= threshold
except ImportError:
    def _fuzzy_match(pattern: str, text: str, threshold: float) -> bool:  # type: ignore[misc]
        return pattern in text


REOPEN_RULES = [
    (0, 7, 5), (7, 12, 10), (12, 18, 15), (18, 20, 20), (20, 24, 25),
]
NO_PLAYER_ALERT_START_HOUR = 12

# Patterns dang khong dau - normalize_ocr_text() dam bao OCR text cung ve dang nay
# Khong can bien the loi encoding hay dau tieng Viet
PATTERNS_OPEN = [
    "su kien imperial guardian da bat dau",
    "imperial guardian da bat dau",
]
PATTERNS_COUNTDOWN = [
    "su kien imperial guardian se bat dau sau",
    "imperial guardian se bat dau sau",
    "imperial guardian bat dau sau",
]


class ImperialGuardianHandler:
    """Handler for Imperial Guardian event tracking state machine.

    State machine: WAITING -> OPEN -> CLOSED -> OPEN (cycle)
    OCR text is normalized before caching, logging, and matching.
    Telegram messages use proper Vietnamese with diacritics.
    """

    def __init__(
        self,
        telegram_notifier=None,
        ui_log=None,
        delay_minutes: int = 10,
        match_threshold: float = 70.0,
    ) -> None:
        self.telegram_notifier = telegram_notifier
        self.ui_log = ui_log or (lambda msg: print(f"[ImperialGuardian] {msg}"))
        self.delay_minutes = delay_minutes
        self.match_threshold = match_threshold
        self._state = "WAITING"
        self._open_time: Optional[float] = None
        self._no_player_alert_sent = False
        self._cached_text: Optional[str] = None
        self._lock = threading.Lock()

    def _log(self, message: str) -> None:
        self.ui_log(f"[Imperial Guardian] {message}")

    def _send_telegram(self, message: str) -> None:
        """Send Telegram notification. Message uses Vietnamese with diacritics."""
        if self.telegram_notifier:
            try:
                self.telegram_notifier.send_simple(message)
            except Exception as e:
                self._log(f"Failed to send Telegram: {e}")

    def _match(self, normalized_text: str, patterns: list) -> bool:
        """Match normalized text against list of normalized patterns."""
        return any(_fuzzy_match(p, normalized_text, self.match_threshold) for p in patterns)

    def _extract_minutes(self, normalized_text: str) -> Optional[int]:
        """Extract minutes from normalized text. Supports 'phut' and spacing variations."""
        m = re.search(r'(\d+)\s*phut', normalized_text)
        return int(m.group(1)) if m else None

    def _extract_latest_imperial_guardian_text(self, normalized_text: str) -> str:
        """Return the latest Imperial Guardian notification segment from OCR blob."""
        marker = "imperial guardian"
        positions = [m.start() for m in re.finditer(re.escape(marker), normalized_text)]
        if not positions:
            return normalized_text

        start = positions[-1]
        next_event = re.search(r"\bsu kien\b", normalized_text[start + len(marker):])
        if next_event:
            end = start + len(marker) + next_event.start()
            return normalized_text[start:end].strip()
        return normalized_text[start:].strip()

    def _get_reopen_time(self) -> int:
        hour = time.localtime().tm_hour
        for start, end, minutes in REOPEN_RULES:
            if start <= hour < end:
                return minutes
        return 25

    def _is_no_player_alert_window(self) -> bool:
        """Return whether no-player alerts are valid at the current local hour."""
        return time.localtime().tm_hour >= NO_PLAYER_ALERT_START_HOUR

    def _check_no_player_alert(self) -> None:
        if self._state != "OPEN" or self._no_player_alert_sent or self._open_time is None:
            return
        if not self._is_no_player_alert_window():
            return
        try:
            elapsed = time.time() - self._open_time
            if elapsed > self.delay_minutes * 60:
                self._no_player_alert_sent = True
                self._send_telegram(
                    f"Sự kiện Imperial Guardian đang không có người tham gia sau {self.delay_minutes} phút"
                )
        except (TypeError, Exception):
            pass

    def _process(self, normalized_text: str) -> None:
        """Process normalized OCR text against event patterns."""
        normalized_text = self._extract_latest_imperial_guardian_text(normalized_text)

        if self._match(normalized_text, PATTERNS_COUNTDOWN):
            x = self._extract_minutes(normalized_text)
            if self._state == "OPEN" and x is not None and x >= self._get_reopen_time():
                self._state = "CLOSED"
                self._open_time = None
                self._send_telegram(
                    f"Sự kiện Imperial Guardian đã đóng, mở sau {x} phút"
                )
            return

        if self._match(normalized_text, PATTERNS_OPEN):
            if self._state != "OPEN":
                self._state = "OPEN"
                self._open_time = time.time()
                self._no_player_alert_sent = False
                self._send_telegram("Sự kiện Imperial Guardian đã bắt đầu")
            return

    def on_ocr_text(self, text: str) -> None:
        """Handle OCR text. Normalize before cache, log, and match.

        Timer check runs before dedup so no-player alert fires even on repeated text.
        """
        with self._lock:
            self._check_no_player_alert()

            if not text:
                return

            # Normalize: strip diacritics, d->d, lowercase, collapse whitespace
            normalized = normalize_ocr_text(text)

            self._log(f"OCR normalized: '{normalized}' (state={self._state})")

            if normalized == self._cached_text:
                return  # dedup: skip pattern matching, timer already checked above
            self._cached_text = normalized

            self._process(normalized)

    def reset(self) -> None:
        """Reset handler state."""
        self._state = "WAITING"
        self._open_time = None
        self._no_player_alert_sent = False
        self._cached_text = None
