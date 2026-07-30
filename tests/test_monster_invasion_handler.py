"""Unit tests for MonsterInvasionHandler fan-out logic."""

import unittest
from unittest.mock import MagicMock


class TestMonsterInvasionHandler(unittest.TestCase):
    """Tests for MonsterInvasionHandler fan-out behavior."""

    def _make_handler(self, sub_handlers=None):
        from src.logic.system_executor.monster_invasion_handler import MonsterInvasionHandler
        log = MagicMock()
        return MonsterInvasionHandler(sub_handlers=sub_handlers or [], log_signal_emit=log), log

    def _make_sub(self):
        sub = MagicMock()
        sub.on_channel_text = MagicMock()
        sub.on_notify_text = MagicMock()
        sub.reset = MagicMock()
        return sub

    def test_fanout_channel_text_to_all_sub_handlers(self):
        sub1, sub2 = self._make_sub(), self._make_sub()
        h, _ = self._make_handler([sub1, sub2])
        h.on_channel_text("CS1")
        sub1.on_channel_text.assert_called_once_with("CS1")
        sub2.on_channel_text.assert_called_once_with("CS1")

    def test_fanout_notify_text_to_all_sub_handlers(self):
        sub1, sub2 = self._make_sub(), self._make_sub()
        h, _ = self._make_handler([sub1, sub2])
        h.on_notify_text("kill msg")
        sub1.on_notify_text.assert_called_once_with("kill msg")
        sub2.on_notify_text.assert_called_once_with("kill msg")

    def test_exception_in_first_does_not_stop_second(self):
        sub1, sub2 = self._make_sub(), self._make_sub()
        sub1.on_channel_text.side_effect = RuntimeError("boom")
        h, log = self._make_handler([sub1, sub2])
        h.on_channel_text("CS1")
        sub2.on_channel_text.assert_called_once_with("CS1")
        log.assert_called()

    def test_exception_in_notify_does_not_stop_other(self):
        sub1, sub2 = self._make_sub(), self._make_sub()
        sub1.on_notify_text.side_effect = ValueError("bad")
        h, _ = self._make_handler([sub1, sub2])
        h.on_notify_text("kill msg")
        sub2.on_notify_text.assert_called_once_with("kill msg")

    def test_reset_calls_all_sub_handlers(self):
        sub1, sub2 = self._make_sub(), self._make_sub()
        h, _ = self._make_handler([sub1, sub2])
        h.reset()
        sub1.reset.assert_called_once()
        sub2.reset.assert_called_once()

    def test_reset_exception_does_not_stop_other(self):
        sub1, sub2 = self._make_sub(), self._make_sub()
        sub1.reset.side_effect = Exception("fail")
        h, _ = self._make_handler([sub1, sub2])
        h.reset()
        sub2.reset.assert_called_once()

    def test_empty_sub_handlers_no_crash(self):
        h, _ = self._make_handler([])
        h.on_channel_text("CS1")
        h.on_notify_text("msg")
        h.reset()


if __name__ == "__main__":
    unittest.main()
