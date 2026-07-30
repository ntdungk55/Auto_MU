"""Integration tests for special event tracking subscription lifecycle."""

import unittest
from unittest.mock import MagicMock, patch


class TestSpecialEventSubscriptionLifecycle(unittest.TestCase):
    """Tests for setup/teardown of ScreenScanService subscriptions."""

    def _make_action(self, enabled=True, x1=10, y1=20, x2=200, y2=100, delay=10):
        """Create a fake action with Imperial Guardian enabled and Golden Invasion disabled."""
        action = MagicMock()
        action.name = "test_action"
        # Imperial Guardian
        action.imperial_guardian_enabled = enabled
        action.imperial_guardian_no_player_alert_delay = delay
        action.imperial_guardian_teaching_corner_x1 = x1
        action.imperial_guardian_teaching_corner_y1 = y1
        action.imperial_guardian_teaching_corner_x2 = x2
        action.imperial_guardian_teaching_corner_y2 = y2
        action.imperial_guardian_ocr_engine = "auto"
        action.imperial_guardian_match_threshold = 70.0
        action.imperial_guardian_ocr_algorithms = []
        # Golden Invasion explicitly disabled to avoid unexpected branch execution
        action.golden_invasion_enabled = False
        action.golden_invasion_server_time = "01:30"
        action.golden_invasion_channel_roi_x1 = 0
        action.golden_invasion_channel_roi_y1 = 0
        action.golden_invasion_channel_roi_x2 = 0
        action.golden_invasion_channel_roi_y2 = 0
        action.golden_invasion_channel_ocr_engine = "auto"
        action.golden_invasion_channel_ocr_algorithms = []
        action.golden_invasion_notify_roi_x1 = 0
        action.golden_invasion_notify_roi_y1 = 0
        action.golden_invasion_notify_roi_x2 = 0
        action.golden_invasion_notify_roi_y2 = 0
        action.golden_invasion_notify_ocr_engine = "auto"
        action.golden_invasion_notify_ocr_algorithms = []
        action.golden_invasion_match_threshold = 70.0
        # Monster Invasion explicitly disabled to avoid unexpected branch execution
        action.monster_invasion_enabled = False
        action.monster_invasion_channel_roi_x1 = 0
        action.monster_invasion_channel_roi_y1 = 0
        action.monster_invasion_channel_roi_x2 = 0
        action.monster_invasion_channel_roi_y2 = 0
        action.monster_invasion_channel_ocr_engine = "auto"
        action.monster_invasion_channel_ocr_algorithms = []
        action.monster_invasion_notify_roi_x1 = 0
        action.monster_invasion_notify_roi_y1 = 0
        action.monster_invasion_notify_roi_x2 = 0
        action.monster_invasion_notify_roi_y2 = 0
        action.monster_invasion_notify_ocr_engine = "auto"
        action.monster_invasion_notify_ocr_algorithms = []
        action.monster_invasion_match_threshold = 70.0
        action.monster_invasion_golden_invasion_enabled = False
        action.monster_invasion_golden_invasion_server_time = "01:30"
        action.monster_invasion_white_wizard_red_dragon_enabled = False
        action.event_ocr_engine = "auto"
        return action

    def _make_executor(self):
        from src.logic.system_executor.system_executor import SystemExecutor
        executor = SystemExecutor.__new__(SystemExecutor)
        executor.target_window_hwnd = 12345
        executor.telegram_notifier = MagicMock()
        executor._ui_log = MagicMock()
        executor.engine = MagicMock()
        executor.engine.is_running = True
        executor.engine.should_stop_completely = False
        return executor

    def test_setup_subscribes_when_enabled_and_roi_valid(self):
        executor = self._make_executor()
        action = self._make_action(enabled=True, x1=10, y1=20, x2=200, y2=100)
        mock_service = MagicMock()
        with patch("src.logic.system_executor.screen_scan_service.ScreenScanService") as mock_svc_cls:
            mock_svc_cls.get_instance.return_value = mock_service
            executor._setup_special_event_subscriptions(action, 12345)
        mock_service.subscribe.assert_called_once()

    def test_setup_skips_when_roi_invalid(self):
        executor = self._make_executor()
        action = self._make_action(enabled=True, x1=100, y1=20, x2=50, y2=100)
        mock_service = MagicMock()
        with patch("src.logic.system_executor.screen_scan_service.ScreenScanService") as mock_svc_cls:
            mock_svc_cls.get_instance.return_value = mock_service
            executor._setup_special_event_subscriptions(action, 12345)
        mock_service.subscribe.assert_not_called()
        executor._ui_log.assert_called()

    def test_setup_skips_when_disabled(self):
        executor = self._make_executor()
        action = self._make_action(enabled=False)
        mock_service = MagicMock()
        with patch("src.logic.system_executor.screen_scan_service.ScreenScanService") as mock_svc_cls:
            mock_svc_cls.get_instance.return_value = mock_service
            executor._setup_special_event_subscriptions(action, 12345)
        mock_service.subscribe.assert_not_called()

    def test_teardown_unsubscribes(self):
        """Teardown must unsubscribe imperial_guardian subscription."""
        executor = self._make_executor()
        action = self._make_action()
        mock_service = MagicMock()
        with patch("src.logic.system_executor.screen_scan_service.ScreenScanService") as mock_svc_cls:
            mock_svc_cls.get_instance.return_value = mock_service
            executor._teardown_special_event_subscriptions(action)
        self.assertGreaterEqual(mock_service.unsubscribe.call_count, 1)
        all_call_args = [call[0][0] for call in mock_service.unsubscribe.call_args_list]
        self.assertTrue(
            any("imperial_guardian" in arg for arg in all_call_args),
            f"Expected imperial_guardian in unsubscribe calls, got: {all_call_args}"
        )

    def test_subscription_id_contains_action_identity(self):
        executor = self._make_executor()
        action = self._make_action(enabled=True, x1=10, y1=20, x2=200, y2=100)
        captured_sub = []
        mock_service = MagicMock()
        mock_service.subscribe.side_effect = lambda sub: captured_sub.append(sub)
        with patch("src.logic.system_executor.screen_scan_service.ScreenScanService") as mock_svc_cls:
            mock_svc_cls.get_instance.return_value = mock_service
            executor._setup_special_event_subscriptions(action, 12345)
        self.assertEqual(len(captured_sub), 1)
        self.assertIn("special_event", captured_sub[0].action_id)
        self.assertIn("imperial_guardian", captured_sub[0].action_id)

    def test_ocr_engine_propagated_to_subscription(self):
        """imperial_guardian_ocr_engine must be passed to OCRSubscription."""
        executor = self._make_executor()
        action = self._make_action(enabled=True, x1=10, y1=20, x2=200, y2=100)
        action.imperial_guardian_ocr_engine = "tesseract"
        captured_sub = []
        mock_service = MagicMock()
        mock_service.subscribe.side_effect = lambda sub: captured_sub.append(sub)
        with patch("src.logic.system_executor.screen_scan_service.ScreenScanService") as mock_svc_cls:
            mock_svc_cls.get_instance.return_value = mock_service
            executor._setup_special_event_subscriptions(action, 12345)
        self.assertEqual(len(captured_sub), 1)
        self.assertEqual(captured_sub[0].ocr_engine, "tesseract")

    def test_golden_invasion_subscriptions_are_paired(self):
        """Golden Invasion channel/notify subscriptions must be grouped as one OCR pair."""
        executor = self._make_executor()
        action = self._make_action(enabled=False)
        action.golden_invasion_enabled = True
        action.golden_invasion_channel_roi_x1 = 10
        action.golden_invasion_channel_roi_y1 = 20
        action.golden_invasion_channel_roi_x2 = 110
        action.golden_invasion_channel_roi_y2 = 70
        action.golden_invasion_notify_roi_x1 = 30
        action.golden_invasion_notify_roi_y1 = 40
        action.golden_invasion_notify_roi_x2 = 230
        action.golden_invasion_notify_roi_y2 = 120
        captured_sub = []
        mock_service = MagicMock()
        mock_service.subscribe.side_effect = lambda sub: captured_sub.append(sub)

        with patch("src.logic.system_executor.screen_scan_service.ScreenScanService") as mock_svc_cls:
            mock_svc_cls.get_instance.return_value = mock_service
            executor._setup_special_event_subscriptions(action, 12345)

        self.assertEqual(len(captured_sub), 2)
        roles = {sub.pair_role for sub in captured_sub}
        group_ids = {sub.pair_group_id for sub in captured_sub}
        self.assertEqual(roles, {"channel", "notify"})
        self.assertEqual(len(group_ids), 1)
        self.assertTrue(all(sub.pair_log_callback for sub in captured_sub))

    def test_golden_invasion_pair_log_reports_pattern_match(self):
        """Pair log should state whether notify OCR matches any Golden Invasion kill pattern."""
        executor = self._make_executor()
        logs = []
        executor._ui_log = logs.append

        executor._log_golden_invasion_ocr_pair(
            "group-1",
            {
                "channel": "CS1",
                "notify": "Kim Thiet Vuong da bi tieu diet boi PlayerX tai Lorencia",
            },
        )

        self.assertEqual(len(logs), 1)
        self.assertIn("matched=<b>True</b>", logs[0])
        self.assertIn("patterns=<code>P3</code>", logs[0])

    def test_monster_invasion_subscriptions_are_paired(self):
        """Monster Invasion channel/notify subscriptions must share one OCR pair."""
        executor = self._make_executor()
        action = self._make_action(enabled=False)
        action.monster_invasion_enabled = True
        action.monster_invasion_golden_invasion_enabled = True
        action.monster_invasion_white_wizard_red_dragon_enabled = True
        action.monster_invasion_channel_roi_x1 = 10
        action.monster_invasion_channel_roi_y1 = 20
        action.monster_invasion_channel_roi_x2 = 110
        action.monster_invasion_channel_roi_y2 = 70
        action.monster_invasion_notify_roi_x1 = 30
        action.monster_invasion_notify_roi_y1 = 40
        action.monster_invasion_notify_roi_x2 = 230
        action.monster_invasion_notify_roi_y2 = 120
        captured_sub = []
        mock_service = MagicMock()
        mock_service.subscribe.side_effect = lambda sub: captured_sub.append(sub)

        with patch("src.logic.system_executor.screen_scan_service.ScreenScanService") as mock_svc_cls:
            mock_svc_cls.get_instance.return_value = mock_service
            executor._setup_special_event_subscriptions(action, 12345)

        self.assertEqual(len(captured_sub), 2)
        roles = {sub.pair_role for sub in captured_sub}
        group_ids = {sub.pair_group_id for sub in captured_sub}
        self.assertEqual(roles, {"channel", "notify"})
        self.assertEqual(len(group_ids), 1)
        self.assertTrue(all("monster_invasion" in sub.action_id for sub in captured_sub))

    def test_monster_invasion_skips_without_sub_event(self):
        """Monster Invasion must not subscribe when no child event is enabled."""
        executor = self._make_executor()
        action = self._make_action(enabled=False)
        action.monster_invasion_enabled = True
        action.monster_invasion_channel_roi_x1 = 10
        action.monster_invasion_channel_roi_y1 = 20
        action.monster_invasion_channel_roi_x2 = 110
        action.monster_invasion_channel_roi_y2 = 70
        action.monster_invasion_notify_roi_x1 = 30
        action.monster_invasion_notify_roi_y1 = 40
        action.monster_invasion_notify_roi_x2 = 230
        action.monster_invasion_notify_roi_y2 = 120
        mock_service = MagicMock()

        with patch("src.logic.system_executor.screen_scan_service.ScreenScanService") as mock_svc_cls:
            mock_svc_cls.get_instance.return_value = mock_service
            executor._setup_special_event_subscriptions(action, 12345)

        mock_service.subscribe.assert_not_called()


if __name__ == "__main__":
    unittest.main()
