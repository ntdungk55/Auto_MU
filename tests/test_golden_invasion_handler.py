"""Unit tests for GoldenInvasionHandler state machine."""

import unittest
from unittest.mock import MagicMock
from datetime import datetime, timedelta


class TestGoldenInvasionHandler(unittest.TestCase):
    """Tests for GoldenInvasionHandler state machine logic."""

    def _make_handler(self, server_time="01:30", match_threshold=70.0):
        from src.logic.system_executor.golden_invasion_handler import GoldenInvasionHandler
        telegram = MagicMock()
        log = MagicMock()
        handler = GoldenInvasionHandler(
            server_time=server_time,
            match_threshold=match_threshold,
            telegram_notifier=telegram,
            log_signal_emit=log,
        )
        return handler, telegram, log

    def _force_active(self, handler):
        handler._state = "ACTIVE"
        handler._channel_at_start = "cs1"
        handler._channel_current = "cs1"

    # ── Initial state ────────────────────────────────────────────────────────

    def test_initial_state_is_waiting(self):
        handler, _, _ = self._make_handler()
        self.assertEqual(handler._state, "WAITING")

    def test_initial_remaining_set_has_all_bosses(self):
        from src.logic.system_executor.golden_invasion_handler import _BOSS_CANONICAL_KEYS
        handler, _, _ = self._make_handler()
        self.assertEqual(handler._remaining_set, set(_BOSS_CANONICAL_KEYS))

    def test_initial_killed_set_is_empty(self):
        handler, _, _ = self._make_handler()
        self.assertEqual(len(handler._killed_set), 0)

    # ── WAITING state ────────────────────────────────────────────────────────

    def test_waiting_state_ignores_notify_text(self):
        handler, telegram, _ = self._make_handler()
        handler.on_notify_text("Kim Thiet Vuong da bi tieu diet boi PlayerX tai Lorencia")
        telegram.send_simple.assert_not_called()
        self.assertEqual(handler._state, "WAITING")

    def test_waiting_state_channel_text_updates_current(self):
        handler, _, _ = self._make_handler()
        handler.on_channel_text("CS1")
        self.assertEqual(handler._channel_current, "cs1")

    # ── ACTIVE state transition ──────────────────────────────────────────────

    def test_channel_text_triggers_active_at_event_time(self):
        handler, _, _ = self._make_handler(server_time="01:30")
        handler._next_event_time = datetime.now() - timedelta(seconds=1)
        handler.on_channel_text("CS1")
        self.assertEqual(handler._state, "ACTIVE")
        self.assertEqual(handler._channel_at_start, "cs1")

    def test_active_resets_killed_and_remaining_sets(self):
        from src.logic.system_executor.golden_invasion_handler import _BOSS_CANONICAL_KEYS
        handler, _, _ = self._make_handler()
        handler._killed_set.add("kim thiet vuong")
        handler._remaining_set.discard("kim thiet vuong")
        handler._next_event_time = datetime.now() - timedelta(seconds=1)
        handler.on_channel_text("CS1")
        self.assertEqual(handler._state, "ACTIVE")
        self.assertEqual(len(handler._killed_set), 0)
        self.assertEqual(handler._remaining_set, set(_BOSS_CANONICAL_KEYS))

    def test_active_snapshots_channel_at_start(self):
        handler, _, _ = self._make_handler()
        handler._channel_current = "cs2"
        handler._next_event_time = datetime.now() - timedelta(seconds=1)
        handler.on_channel_text("CS2")
        self.assertEqual(handler._channel_at_start, "cs2")

    # ── Boss kill detection ──────────────────────────────────────────────────

    def test_pattern1_boss_kill_sends_telegram(self):
        handler, telegram, _ = self._make_handler()
        self._force_active(handler)
        handler.on_notify_text(
            "Kim Thiet Vuong da bi tieu diet boi PlayerX va dong dong tai Lorencia"
        )
        telegram.send_simple.assert_called_once()

    def test_pattern2_boss_kill_sends_telegram(self):
        handler, telegram, _ = self._make_handler()
        self._force_active(handler)
        handler.on_notify_text(
            "Kim Xa Vuong da bi tieu diet boi PlayerY tai Noria"
        )
        telegram.send_simple.assert_called_once()

    def test_ocr_with_diacritics_sends_telegram(self):
        """OCR output with Vietnamese diacritics should also match after normalize."""
        handler, telegram, _ = self._make_handler()
        self._force_active(handler)
        handler.on_notify_text(
            "Kim Thiết Vương đã bị tiêu diệt bởi PlayerX tại Lorencia"
        )
        telegram.send_simple.assert_called_once()

    def test_telegram_message_uses_display_name_with_diacritics(self):
        """Telegram message must use canonical display name with Vietnamese diacritics."""
        handler, telegram, _ = self._make_handler()
        self._force_active(handler)
        handler.on_notify_text(
            "Kim Thiet Vuong da bi tieu diet boi PlayerX tai Lorencia"
        )
        msg = telegram.send_simple.call_args[0][0]
        self.assertIn("Kim Thiết Vương", msg)

    def test_telegram_message_contains_channel(self):
        handler, telegram, _ = self._make_handler()
        self._force_active(handler)
        handler.on_notify_text(
            "Kim Thiet Vuong da bi tieu diet boi PlayerX tai Lorencia"
        )
        msg = telegram.send_simple.call_args[0][0]
        self.assertIn("cs1", msg.lower())

    def test_telegram_message_does_not_contain_player_name(self):
        handler, telegram, _ = self._make_handler()
        self._force_active(handler)
        handler.on_notify_text(
            "Kim Thiet Vuong da bi tieu diet boi PlayerXYZ tai Lorencia"
        )
        msg = telegram.send_simple.call_args[0][0]
        self.assertNotIn("PlayerXYZ", msg)

    def test_telegram_message_contains_remaining_list(self):
        handler, telegram, _ = self._make_handler()
        self._force_active(handler)
        handler.on_notify_text(
            "Kim Thiet Vuong da bi tieu diet boi PlayerX tai Lorencia"
        )
        msg = telegram.send_simple.call_args[0][0]
        self.assertIn("hiện tại còn", msg)

    # ── Dedup ────────────────────────────────────────────────────────────────

    def test_same_boss_not_sent_twice(self):
        handler, telegram, _ = self._make_handler()
        self._force_active(handler)
        handler.on_notify_text(
            "Kim Thiet Vuong da bi tieu diet boi PlayerX tai Lorencia"
        )
        handler.on_notify_text(
            "Kim Thiet Vuong da bi tieu diet boi PlayerX tai Lorencia"
        )
        self.assertEqual(telegram.send_simple.call_count, 1)

    def test_different_bosses_each_sent_once(self):
        handler, telegram, _ = self._make_handler()
        self._force_active(handler)
        handler.on_notify_text(
            "Kim Thiet Vuong da bi tieu diet boi PlayerX tai Lorencia"
        )
        handler.on_notify_text(
            "Kim Xa Vuong da bi tieu diet boi PlayerY tai Noria"
        )
        self.assertEqual(telegram.send_simple.call_count, 2)

    # ── Channel validation ───────────────────────────────────────────────────

    def test_channel_changed_skips_notification(self):
        handler, telegram, _ = self._make_handler()
        self._force_active(handler)
        handler._channel_current = "cs2"
        handler.on_notify_text(
            "Kim Thiet Vuong da bi tieu diet boi PlayerX tai Lorencia"
        )
        telegram.send_simple.assert_not_called()

    def test_channel_unchanged_sends_notification(self):
        handler, telegram, _ = self._make_handler()
        self._force_active(handler)
        handler.on_notify_text(
            "Kim Thiet Vuong da bi tieu diet boi PlayerX tai Lorencia"
        )
        telegram.send_simple.assert_called_once()

    # ── Unknown boss ignored ─────────────────────────────────────────────────

    def test_unknown_boss_not_sent(self):
        handler, telegram, _ = self._make_handler()
        self._force_active(handler)
        handler.on_notify_text(
            "Rong Do da bi tieu diet boi PlayerX tai Lorencia"
        )
        telegram.send_simple.assert_not_called()

    # ── All bosses killed ────────────────────────────────────────────────────

    def test_all_bosses_killed_transitions_to_waiting(self):
        from src.logic.system_executor.golden_invasion_handler import _BOSS_CANONICAL_KEYS
        handler, _, _ = self._make_handler()
        self._force_active(handler)
        keys = list(_BOSS_CANONICAL_KEYS)
        for key in keys[:-1]:
            handler._killed_set.add(key)
            handler._remaining_set.discard(key)
        last_key = keys[-1]
        handler.on_notify_text(
            f"{last_key} da bi tieu diet boi PlayerX tai Lorencia"
        )
        self.assertEqual(handler._state, "WAITING")

    def test_remaining_set_decreases_on_kill(self):
        handler, _, _ = self._make_handler()
        self._force_active(handler)
        initial_count = len(handler._remaining_set)
        handler.on_notify_text(
            "Kim Thiet Vuong da bi tieu diet boi PlayerX tai Lorencia"
        )
        self.assertEqual(len(handler._remaining_set), initial_count - 1)

    def test_last_boss_message_shows_empty_remaining(self):
        from src.logic.system_executor.golden_invasion_handler import _BOSS_CANONICAL_KEYS
        handler, telegram, _ = self._make_handler()
        self._force_active(handler)
        keys = list(_BOSS_CANONICAL_KEYS)
        for key in keys[:-1]:
            handler._killed_set.add(key)
            handler._remaining_set.discard(key)
        last_key = keys[-1]
        handler.on_notify_text(
            f"{last_key} da bi tieu diet boi PlayerX tai Lorencia"
        )
        msg = telegram.send_simple.call_args[0][0]
        self.assertIn("không còn con nào", msg)

    # ── Event time calculation ───────────────────────────────────────────────

    def test_next_event_time_is_in_future(self):
        handler, _, _ = self._make_handler(server_time="01:30")
        self.assertGreater(handler._next_event_time, datetime.now())

    def test_server_time_0040_sets_minute_40(self):
        handler, _, _ = self._make_handler(server_time="00:40")
        self.assertEqual(handler._next_event_time.minute, 40)

    def test_server_time_0130_sets_minute_30(self):
        handler, _, _ = self._make_handler(server_time="01:30")
        self.assertEqual(handler._next_event_time.minute, 30)

    def test_next_event_recalculated_after_active(self):
        handler, _, _ = self._make_handler()
        handler._next_event_time = datetime.now() - timedelta(seconds=1)
        handler.on_channel_text("CS1")
        self.assertEqual(handler._state, "ACTIVE")
        self.assertGreater(handler._next_event_time, datetime.now())

    # ── Edge cases ───────────────────────────────────────────────────────────

    def test_empty_channel_text_no_crash(self):
        handler, _, _ = self._make_handler()
        handler.on_channel_text("")
        handler.on_channel_text(None)  # type: ignore
        self.assertEqual(handler._state, "WAITING")

    def test_empty_notify_text_no_crash(self):
        handler, telegram, _ = self._make_handler()
        self._force_active(handler)
        handler.on_notify_text("")
        handler.on_notify_text(None)  # type: ignore
        telegram.send_simple.assert_not_called()

    def test_channel_at_start_none_skips_notification(self):
        handler, telegram, _ = self._make_handler()
        handler._state = "ACTIVE"
        handler._channel_at_start = None
        handler._channel_current = "cs1"
        handler.on_notify_text(
            "Kim Thiet Vuong da bi tieu diet boi PlayerX tai Lorencia"
        )
        telegram.send_simple.assert_not_called()

    def test_reset_clears_state(self):
        from src.logic.system_executor.golden_invasion_handler import _BOSS_CANONICAL_KEYS
        handler, _, _ = self._make_handler()
        self._force_active(handler)
        handler._killed_set.add("kim thiet vuong")
        handler._remaining_set.discard("kim thiet vuong")
        handler.reset()
        self.assertEqual(handler._state, "WAITING")
        self.assertEqual(len(handler._killed_set), 0)
        self.assertEqual(handler._remaining_set, set(_BOSS_CANONICAL_KEYS))

    # ── Normalize and display ────────────────────────────────────────────────

    def test_boss_names_count_is_7(self):
        from src.logic.system_executor.golden_invasion_handler import BOSS_NAMES
        self.assertEqual(len(BOSS_NAMES), 7)

    def test_boss_display_names_have_diacritics(self):
        from src.logic.system_executor.golden_invasion_handler import _BOSS_DISPLAY
        all_display = " ".join(_BOSS_DISPLAY.values())
        has_diacritics = any(ord(c) > 127 for c in all_display)
        self.assertTrue(has_diacritics, "Display names should contain Vietnamese diacritics")

    def test_normalize_ocr_text_strips_diacritics(self):
        from src.logic.system_executor.event_tracking_helper import normalize_ocr_text
        result = normalize_ocr_text("Kim Thiết Vương đã bị tiêu diệt")
        self.assertEqual(result, "kim thiet vuong da bi tieu diet")

    def test_normalize_ocr_text_handles_d_with_stroke(self):
        from src.logic.system_executor.event_tracking_helper import normalize_ocr_text
        result = normalize_ocr_text("đã bắt đầu")
        self.assertNotIn("đ", result)
        self.assertIn("da", result)


if __name__ == "__main__":
    unittest.main()
