"""Unit tests for ImperialGuardianHandler state machine."""

import time
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime


class TestImperialGuardianHandler(unittest.TestCase):
    """Tests for ImperialGuardianHandler state machine logic."""

    def _make_handler(self, delay_minutes: int = 10, match_threshold: float = 70.0):
        from src.logic.system_executor.imperial_guardian_handler import ImperialGuardianHandler
        telegram = MagicMock()
        log = MagicMock()
        return ImperialGuardianHandler(
            telegram_notifier=telegram,
            ui_log=log,
            delay_minutes=delay_minutes,
            match_threshold=match_threshold,
        ), telegram, log

    # ── State machine ────────────────────────────────────────────────────────

    def test_initial_state_is_waiting(self):
        handler, _, _ = self._make_handler()
        self.assertEqual(handler._state, "WAITING")

    def test_open_on_started_message_with_diacritics(self):
        """OCR with Vietnamese diacritics should match after normalize."""
        handler, telegram, _ = self._make_handler()
        handler.on_ocr_text("Sự kiện Imperial Guardian đã bắt đầu")
        self.assertEqual(handler._state, "OPEN")
        telegram.send_simple.assert_called_once()

    def test_open_on_started_message_no_diacritics(self):
        """OCR without diacritics should also match after normalize."""
        handler, telegram, _ = self._make_handler()
        handler.on_ocr_text("Su kien Imperial Guardian da bat dau")
        self.assertEqual(handler._state, "OPEN")
        telegram.send_simple.assert_called_once()

    def test_open_on_started_message_partial(self):
        """Partial OCR (missing 'su kien') should still match when it has 'da'."""
        handler, telegram, _ = self._make_handler()
        handler.on_ocr_text("imperial guardian da bat dau")
        self.assertEqual(handler._state, "OPEN")
        telegram.send_simple.assert_called_once()

    def test_countdown_does_not_open_from_waiting(self):
        """Countdown text must not be treated as an event start."""
        handler, telegram, _ = self._make_handler()
        handler.on_ocr_text("Su kien Imperial Guardian se bat dau sau 10 phut")
        self.assertEqual(handler._state, "WAITING")
        telegram.send_simple.assert_not_called()

    def test_countdown_does_not_open_from_closed(self):
        """Countdown text must not reopen a closed event."""
        handler, telegram, _ = self._make_handler()
        handler._state = "CLOSED"
        handler.on_ocr_text("Su kien Imperial Guardian se bat dau sau 15 phut")
        self.assertEqual(handler._state, "CLOSED")
        telegram.send_simple.assert_not_called()

    def test_telegram_open_message_has_diacritics(self):
        """Telegram notification must use Vietnamese with diacritics."""
        handler, telegram, _ = self._make_handler()
        handler.on_ocr_text("Su kien Imperial Guardian da bat dau")
        msg = telegram.send_simple.call_args[0][0]
        self.assertIn("đã bắt đầu", msg)

    def test_no_duplicate_open_notification(self):
        handler, telegram, _ = self._make_handler()
        handler.on_ocr_text("Su kien Imperial Guardian da bat dau")
        handler.on_ocr_text("Su kien Imperial Guardian da bat dau")
        self.assertEqual(telegram.send_simple.call_count, 1)

    def test_closed_on_countdown_above_reopen_time(self):
        handler, telegram, _ = self._make_handler()
        handler.on_ocr_text("Su kien Imperial Guardian da bat dau")
        with patch("src.logic.system_executor.imperial_guardian_handler.time") as mock_time:
            mock_time.localtime.return_value = time.struct_time((2024, 1, 1, 14, 0, 0, 0, 0, 0))
            mock_time.time.return_value = time.time()
            handler.on_ocr_text("Imperial Guardian se bat dau sau 30 phut")
        self.assertEqual(handler._state, "CLOSED")
        self.assertEqual(telegram.send_simple.call_count, 2)

    def test_closed_on_countdown_with_diacritics(self):
        """Countdown with diacritics should also trigger CLOSED after normalize."""
        handler, telegram, _ = self._make_handler()
        with patch("src.logic.system_executor.imperial_guardian_handler.time.localtime") as mock_localtime:
            mock_localtime.return_value = time.struct_time((2024, 1, 1, 14, 0, 0, 0, 0, 0))
            handler.on_ocr_text("Su kien Imperial Guardian da bat dau")
        with patch("src.logic.system_executor.imperial_guardian_handler.time") as mock_time:
            mock_time.localtime.return_value = time.struct_time((2024, 1, 1, 14, 0, 0, 0, 0, 0))
            mock_time.time.return_value = time.time()
            handler.on_ocr_text("Imperial Guardian sẽ bắt đầu sau 30 phút")
        self.assertEqual(handler._state, "CLOSED")

    def test_uses_latest_imperial_guardian_notification_in_mixed_blob(self):
        """Mixed OCR blob should use the latest Imperial Guardian notification."""
        handler, telegram, _ = self._make_handler()
        with patch("src.logic.system_executor.imperial_guardian_handler.time.localtime") as mock_localtime:
            mock_localtime.return_value = time.struct_time((2024, 1, 1, 14, 0, 0, 0, 0, 0))
            handler.on_ocr_text("Su kien Imperial Guardian da bat dau")
        blob = (
            "Phù Thúy Anh Sang đà b! tiêu diệt boi iKAISAi tại Lorencia "
            "kiện Imperial Guardian sẽ bắt đầu sau 1 phút nữa "
            "Sự kiện Imperial Guardian đã bắt đầu "
            "Sự kiện Stadium sẽ bắt đầu sau 30 phút nữa Archer Xuất hiện "
            "Sự kiện Imperial Guardian sẽ bắt đầu sau 30 phút nữa C Sự"
        )
        with patch("src.logic.system_executor.imperial_guardian_handler.time") as mock_time:
            mock_time.localtime.return_value = time.struct_time((2024, 1, 1, 14, 0, 0, 0, 0, 0))
            mock_time.time.return_value = time.time()
            handler.on_ocr_text(blob)

        self.assertEqual(handler._state, "CLOSED")
        msg = telegram.send_simple.call_args[0][0]
        self.assertIn("mở sau 30 phút", msg)

    def test_ignore_countdown_below_reopen_time(self):
        handler, telegram, _ = self._make_handler()
        handler.on_ocr_text("Su kien Imperial Guardian da bat dau")
        with patch("src.logic.system_executor.imperial_guardian_handler.time") as mock_time:
            mock_time.localtime.return_value = time.struct_time((2024, 1, 1, 14, 0, 0, 0, 0, 0))
            mock_time.time.return_value = time.time()
            handler.on_ocr_text("Imperial Guardian se bat dau sau 10 phut")
        self.assertEqual(handler._state, "OPEN")
        self.assertEqual(telegram.send_simple.call_count, 1)

    def test_no_player_alert_sent_after_delay(self):
        handler, telegram, _ = self._make_handler(delay_minutes=1)
        handler.on_ocr_text("Su kien Imperial Guardian da bat dau")
        handler._open_time = time.time() - 61
        with patch("src.logic.system_executor.imperial_guardian_handler.time.localtime") as mock_localtime:
            mock_localtime.return_value = time.struct_time((2024, 1, 1, 14, 0, 0, 0, 0, 0))
            handler.on_ocr_text("some other text that does not match patterns")
        self.assertEqual(telegram.send_simple.call_count, 2)

    def test_no_player_alert_runs_on_empty_ocr_text(self):
        handler, telegram, _ = self._make_handler(delay_minutes=1)
        handler.on_ocr_text("Su kien Imperial Guardian da bat dau")
        handler._open_time = time.time() - 61
        with patch("src.logic.system_executor.imperial_guardian_handler.time.localtime") as mock_localtime:
            mock_localtime.return_value = time.struct_time((2024, 1, 1, 14, 0, 0, 0, 0, 0))
            handler.on_ocr_text("")
        self.assertEqual(telegram.send_simple.call_count, 2)

    def test_no_player_alert_suppressed_before_noon(self):
        handler, telegram, _ = self._make_handler(delay_minutes=1)
        handler.on_ocr_text("Su kien Imperial Guardian da bat dau")
        handler._open_time = time.time() - 61
        with patch("src.logic.system_executor.imperial_guardian_handler.time.localtime") as mock_localtime:
            mock_localtime.return_value = time.struct_time((2024, 1, 1, 9, 0, 0, 0, 0, 0))
            handler.on_ocr_text("some other text that does not match patterns")
        self.assertEqual(telegram.send_simple.call_count, 1)
        self.assertFalse(handler._no_player_alert_sent)

    def test_no_player_alert_sent_only_once(self):
        handler, telegram, _ = self._make_handler(delay_minutes=1)
        handler.on_ocr_text("Su kien Imperial Guardian da bat dau")
        handler._open_time = time.time() - 61
        with patch("src.logic.system_executor.imperial_guardian_handler.time.localtime") as mock_localtime:
            mock_localtime.return_value = time.struct_time((2024, 1, 1, 14, 0, 0, 0, 0, 0))
            handler.on_ocr_text("some other text that does not match patterns")
            handler.on_ocr_text("some other text that does not match patterns")
        self.assertEqual(telegram.send_simple.call_count, 2)

    def test_no_player_alert_message_has_diacritics(self):
        """No-player alert Telegram message must use Vietnamese with diacritics."""
        handler, telegram, _ = self._make_handler(delay_minutes=1)
        handler.on_ocr_text("Su kien Imperial Guardian da bat dau")
        handler._open_time = time.time() - 61
        with patch("src.logic.system_executor.imperial_guardian_handler.time.localtime") as mock_localtime:
            mock_localtime.return_value = time.struct_time((2024, 1, 1, 14, 0, 0, 0, 0, 0))
            handler.on_ocr_text("some other text")
        msg = telegram.send_simple.call_args[0][0]
        self.assertIn("không có người", msg)

    # ── _get_reopen_time ─────────────────────────────────────────────────────

    def test_reopen_time_0_to_7(self):
        handler, _, _ = self._make_handler()
        with patch("src.logic.system_executor.imperial_guardian_handler.time") as mock_time:
            mock_time.localtime.return_value = time.struct_time((2024, 1, 1, 3, 0, 0, 0, 0, 0))
            self.assertEqual(handler._get_reopen_time(), 5)

    def test_reopen_time_7_to_12(self):
        handler, _, _ = self._make_handler()
        with patch("src.logic.system_executor.imperial_guardian_handler.time") as mock_time:
            mock_time.localtime.return_value = time.struct_time((2024, 1, 1, 9, 0, 0, 0, 0, 0))
            self.assertEqual(handler._get_reopen_time(), 10)

    def test_reopen_time_12_to_18(self):
        handler, _, _ = self._make_handler()
        with patch("src.logic.system_executor.imperial_guardian_handler.time") as mock_time:
            mock_time.localtime.return_value = time.struct_time((2024, 1, 1, 15, 0, 0, 0, 0, 0))
            self.assertEqual(handler._get_reopen_time(), 15)

    def test_reopen_time_18_to_20(self):
        handler, _, _ = self._make_handler()
        with patch("src.logic.system_executor.imperial_guardian_handler.time") as mock_time:
            mock_time.localtime.return_value = time.struct_time((2024, 1, 1, 19, 0, 0, 0, 0, 0))
            self.assertEqual(handler._get_reopen_time(), 20)

    def test_reopen_time_20_to_24(self):
        handler, _, _ = self._make_handler()
        with patch("src.logic.system_executor.imperial_guardian_handler.time") as mock_time:
            mock_time.localtime.return_value = time.struct_time((2024, 1, 1, 22, 0, 0, 0, 0, 0))
            self.assertEqual(handler._get_reopen_time(), 25)

    # ── _extract_minutes ─────────────────────────────────────────────────────

    def test_extract_minutes_standard_no_diacritics(self):
        handler, _, _ = self._make_handler()
        self.assertEqual(handler._extract_minutes("se bat dau sau 30 phut"), 30)

    def test_extract_minutes_with_spaces(self):
        handler, _, _ = self._make_handler()
        self.assertEqual(handler._extract_minutes("sau 45  phut nua"), 45)

    def test_extract_minutes_no_match(self):
        handler, _, _ = self._make_handler()
        self.assertIsNone(handler._extract_minutes("khong co so phut"))

    # ── Thread safety ────────────────────────────────────────────────────────

    def test_on_ocr_text_empty_string_no_crash(self):
        handler, _, _ = self._make_handler()
        handler.on_ocr_text("")
        handler.on_ocr_text(None)  # type: ignore
        self.assertEqual(handler._state, "WAITING")

    # ── Dedup ────────────────────────────────────────────────────────────────

    def test_dedup_same_text_no_duplicate_state_change(self):
        handler, telegram, _ = self._make_handler()
        handler.on_ocr_text("Su kien Imperial Guardian da bat dau")
        handler.on_ocr_text("Su kien Imperial Guardian da bat dau")
        self.assertEqual(telegram.send_simple.call_count, 1)

    def test_timer_check_runs_even_when_text_unchanged(self):
        """No-player alert timer must fire even if OCR text stays the same."""
        handler, telegram, _ = self._make_handler(delay_minutes=1)
        handler.on_ocr_text("Su kien Imperial Guardian da bat dau")
        handler._open_time = time.time() - 61
        with patch("src.logic.system_executor.imperial_guardian_handler.time.localtime") as mock_localtime:
            mock_localtime.return_value = time.struct_time((2024, 1, 1, 14, 0, 0, 0, 0, 0))
            handler.on_ocr_text("Su kien Imperial Guardian da bat dau")
        self.assertEqual(telegram.send_simple.call_count, 2)

    # ── CLOSED -> OPEN ───────────────────────────────────────────────────────

    def test_closed_to_open_on_started_message(self):
        handler, telegram, _ = self._make_handler()
        handler.on_ocr_text("Su kien Imperial Guardian da bat dau")
        with patch("src.logic.system_executor.imperial_guardian_handler.time") as mock_time:
            mock_time.localtime.return_value = time.struct_time((2024, 1, 1, 14, 0, 0, 0, 0, 0))
            mock_time.time.return_value = time.time()
            handler.on_ocr_text("Su kien Imperial Guardian se bat dau sau 30 phut")
        self.assertEqual(handler._state, "CLOSED")
        handler.on_ocr_text("Su kien Imperial Guardian da bat dau lan 2")
        self.assertEqual(handler._state, "OPEN")
        self.assertEqual(telegram.send_simple.call_count, 3)

    # ── normalize_ocr_text integration ───────────────────────────────────────

    def test_normalize_strips_diacritics_before_match(self):
        """Both diacritic and non-diacritic OCR should produce same normalized result."""
        from src.logic.system_executor.event_tracking_helper import normalize_ocr_text
        with_diacritics = normalize_ocr_text("Sự kiện Imperial Guardian đã bắt đầu")
        without_diacritics = normalize_ocr_text("Su kien Imperial Guardian da bat dau")
        self.assertEqual(with_diacritics, without_diacritics)

    def test_normalize_handles_d_stroke(self):
        """normalize_ocr_text must convert d-with-stroke to plain d."""
        from src.logic.system_executor.event_tracking_helper import normalize_ocr_text
        result = normalize_ocr_text("đã bắt đầu")
        self.assertNotIn("đ", result)
        self.assertIn("da", result)


if __name__ == "__main__":
    unittest.main()
