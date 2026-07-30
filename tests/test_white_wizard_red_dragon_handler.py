"""Unit tests for WhiteWizardRedDragonHandler state machine."""

import unittest
from unittest.mock import MagicMock
from datetime import datetime, timedelta


class TestWhiteWizardRedDragonHandler(unittest.TestCase):

    def _make_handler(self, match_threshold=70.0):
        from src.logic.system_executor.white_wizard_red_dragon_handler import WhiteWizardRedDragonHandler
        telegram = MagicMock()
        log = MagicMock()
        return WhiteWizardRedDragonHandler(
            match_threshold=match_threshold,
            telegram_notifier=telegram,
            log_signal_emit=log,
        ), telegram, log

    def _force_active(self, handler):
        import time
        handler._state = "ACTIVE"
        handler._channel_at_start = "cs1"
        handler._channel_current = "cs1"
        handler._active_since = time.time()

    def test_initial_state_is_waiting(self):
        h, _, _ = self._make_handler()
        self.assertEqual(h._state, "WAITING")

    def test_initial_killed_map_is_zero(self):
        h, _, _ = self._make_handler()
        self.assertEqual(h._killed_map["phu thuy trang"], 0)
        self.assertEqual(h._killed_map["rong do"], 0)

    def test_next_event_time_is_in_future(self):
        h, _, _ = self._make_handler()
        self.assertGreater(h._next_event_time, datetime.now())

    def test_transitions_to_active_at_event_time(self):
        h, _, _ = self._make_handler()
        h._next_event_time = datetime.now() - timedelta(seconds=1)
        h.on_channel_text("CS1")
        self.assertEqual(h._state, "ACTIVE")
        self.assertEqual(h._channel_at_start, "cs1")

    def test_active_resets_killed_map(self):
        h, _, _ = self._make_handler()
        h._killed_map["phu thuy trang"] = 1
        h._next_event_time = datetime.now() - timedelta(seconds=1)
        h.on_channel_text("CS1")
        self.assertEqual(h._killed_map["phu thuy trang"], 0)

    def test_kill_notification_sends_telegram(self):
        h, telegram, _ = self._make_handler()
        self._force_active(h)
        h.on_notify_text("Phu Thuy Trang da bi tieu diet boi PlayerX va dong doi tai Lorencia")
        telegram.send_simple.assert_called_once()

    def test_telegram_message_uses_vietnamese_display_name(self):
        h, telegram, _ = self._make_handler()
        self._force_active(h)
        h.on_notify_text("Phu Thuy Trang da bi tieu diet boi PlayerX va dong doi tai Lorencia")
        msg = telegram.send_simple.call_args[0][0]
        self.assertIn("Phù Thủy Trắng", msg)

    def test_telegram_message_contains_remaining_count(self):
        h, telegram, _ = self._make_handler()
        self._force_active(h)
        h.on_notify_text("Phu Thuy Trang da bi tieu diet boi PlayerX va dong doi tai Lorencia")
        msg = telegram.send_simple.call_args[0][0]
        self.assertIn("Còn", msg)
        self.assertIn("Rồng Đỏ", msg)

    def test_telegram_message_contains_channel(self):
        h, telegram, _ = self._make_handler()
        self._force_active(h)
        h.on_notify_text("Phu Thuy Trang da bi tieu diet boi PlayerX va dong doi tai Lorencia")
        msg = telegram.send_simple.call_args[0][0]
        self.assertIn("cs1", msg.lower())

    def test_telegram_message_does_not_contain_player_name(self):
        h, telegram, _ = self._make_handler()
        self._force_active(h)
        h.on_notify_text("Phu Thuy Trang da bi tieu diet boi PlayerXYZ va dong doi tai Lorencia")
        msg = telegram.send_simple.call_args[0][0]
        self.assertNotIn("PlayerXYZ", msg)

    def test_dedup_same_boss_type_max_2(self):
        h, telegram, _ = self._make_handler()
        self._force_active(h)
        h.on_notify_text("Phu Thuy Trang da bi tieu diet boi P1 va dong doi tai Lorencia")
        h.on_notify_text("Phu Thuy Trang da bi tieu diet boi P2 va dong doi tai Lorencia")
        h.on_notify_text("Phu Thuy Trang da bi tieu diet boi P3 va dong doi tai Lorencia")
        self.assertEqual(telegram.send_simple.call_count, 2)

    def test_different_boss_types_each_sent(self):
        h, telegram, _ = self._make_handler()
        self._force_active(h)
        h.on_notify_text("Phu Thuy Trang da bi tieu diet boi P1 va dong doi tai Lorencia")
        h.on_notify_text("Rong Do da bi tieu diet boi P2 va dong doi tai Lorencia")
        self.assertEqual(telegram.send_simple.call_count, 2)

    def test_channel_change_skips_notification(self):
        h, telegram, _ = self._make_handler()
        self._force_active(h)
        h._channel_current = "cs2"
        h.on_notify_text("Phu Thuy Trang da bi tieu diet boi P1 va dong doi tai Lorencia")
        telegram.send_simple.assert_not_called()

    def test_all_4_bosses_killed_transitions_to_waiting(self):
        h, _, _ = self._make_handler()
        self._force_active(h)
        h._killed_map["phu thuy trang"] = 1
        h._killed_map["rong do"] = 2
        h.on_notify_text("Phu Thuy Trang da bi tieu diet boi P1 va dong doi tai Lorencia")
        self.assertEqual(h._state, "WAITING")

    def test_remaining_count_decreases(self):
        h, _, _ = self._make_handler()
        self._force_active(h)
        h.on_notify_text("Phu Thuy Trang da bi tieu diet boi P1 va dong doi tai Lorencia")
        self.assertEqual(h._killed_map["phu thuy trang"], 1)

    def test_reset_after_25_minutes(self):
        import time
        h, _, _ = self._make_handler()
        self._force_active(h)
        h._active_since = time.time() - (26 * 60)
        h.on_channel_text("CS1")
        self.assertEqual(h._state, "WAITING")
        self.assertEqual(h._killed_map["phu thuy trang"], 0)

    def test_no_text_cache_same_text_processed_twice(self):
        """Same text processed twice — dedup by killed_map count, not text."""
        h, telegram, _ = self._make_handler()
        self._force_active(h)
        h.on_notify_text("Phu Thuy Trang da bi tieu diet boi P1 va dong doi tai Lorencia")
        h.on_notify_text("Phu Thuy Trang da bi tieu diet boi P1 va dong doi tai Lorencia")
        self.assertEqual(telegram.send_simple.call_count, 2)

    def test_waiting_state_ignores_notify(self):
        h, telegram, _ = self._make_handler()
        h.on_notify_text("Phu Thuy Trang da bi tieu diet boi P1 va dong doi tai Lorencia")
        telegram.send_simple.assert_not_called()

    def test_channel_at_start_none_skips(self):
        h, telegram, _ = self._make_handler()
        h._state = "ACTIVE"
        h._channel_at_start = None
        h._channel_current = "cs1"
        h.on_notify_text("Phu Thuy Trang da bi tieu diet boi P1 va dong doi tai Lorencia")
        telegram.send_simple.assert_not_called()

    def test_empty_text_no_crash(self):
        h, telegram, _ = self._make_handler()
        self._force_active(h)
        h.on_channel_text("")
        h.on_notify_text("")
        h.on_channel_text(None)  # type: ignore
        h.on_notify_text(None)  # type: ignore
        telegram.send_simple.assert_not_called()

    def test_reset_clears_state(self):
        h, _, _ = self._make_handler()
        self._force_active(h)
        h._killed_map["phu thuy trang"] = 1
        h.reset()
        self.assertEqual(h._state, "WAITING")
        self.assertEqual(h._killed_map["phu thuy trang"], 0)
        self.assertIsNone(h._channel_at_start)

    def test_unknown_boss_not_sent(self):
        h, telegram, _ = self._make_handler()
        self._force_active(h)
        h.on_notify_text("Rong Xanh da bi tieu diet boi P1 va dong doi tai Lorencia")
        telegram.send_simple.assert_not_called()


if __name__ == "__main__":
    unittest.main()
