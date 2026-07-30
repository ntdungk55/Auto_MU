"""Unit tests for special event tracking persistence (round-trip and backward compat)."""

import unittest


class TestSpecialEventTrackingPersistence(unittest.TestCase):
    """Tests for imperial_guardian_* fields persistence in tool_manager."""

    def _make_action(self, **kwargs):
        """Create AutoAction with given field values."""
        try:
            from action_type import AutoAction, ActionType
        except ImportError:
            from src.logic.action_type import AutoAction, ActionType
        action = AutoAction(
            name="test_action",
            purpose="test",
            action_type=ActionType.READ_PASSIVE,
        )
        for k, v in kwargs.items():
            setattr(action, k, v)
        return action

    def _round_trip(self, action):
        """Serialize action to dict then deserialize back."""
        try:
            from tool_manager import Tool
        except ImportError:
            from src.logic.tool_manager import Tool
        d = Tool._action_to_dict(action)
        new_action = self._make_action()
        new_action.imperial_guardian_enabled = bool(d.get("imperial_guardian_enabled", False))
        new_action.imperial_guardian_no_player_alert_delay = int(d.get("imperial_guardian_no_player_alert_delay", 10) or 10)
        new_action.imperial_guardian_teaching_corner_x1 = int(d.get("imperial_guardian_teaching_corner_x1", 0) or 0)
        new_action.imperial_guardian_teaching_corner_y1 = int(d.get("imperial_guardian_teaching_corner_y1", 0) or 0)
        new_action.imperial_guardian_teaching_corner_x2 = int(d.get("imperial_guardian_teaching_corner_x2", 0) or 0)
        new_action.imperial_guardian_teaching_corner_y2 = int(d.get("imperial_guardian_teaching_corner_y2", 0) or 0)
        return new_action

    def test_round_trip_enabled_true(self):
        action = self._make_action(
            imperial_guardian_enabled=True,
            imperial_guardian_no_player_alert_delay=15,
            imperial_guardian_teaching_corner_x1=10,
            imperial_guardian_teaching_corner_y1=20,
            imperial_guardian_teaching_corner_x2=100,
            imperial_guardian_teaching_corner_y2=80,
        )
        restored = self._round_trip(action)
        self.assertTrue(restored.imperial_guardian_enabled)
        self.assertEqual(restored.imperial_guardian_no_player_alert_delay, 15)
        self.assertEqual(restored.imperial_guardian_teaching_corner_x1, 10)
        self.assertEqual(restored.imperial_guardian_teaching_corner_y1, 20)
        self.assertEqual(restored.imperial_guardian_teaching_corner_x2, 100)
        self.assertEqual(restored.imperial_guardian_teaching_corner_y2, 80)

    def test_round_trip_enabled_false(self):
        action = self._make_action(imperial_guardian_enabled=False)
        restored = self._round_trip(action)
        self.assertFalse(restored.imperial_guardian_enabled)

    def test_backward_compat_missing_fields_use_defaults(self):
        """JSON cũ không có fields mới → default values."""
        old_data = {}
        action = self._make_action()
        action.imperial_guardian_enabled = bool(old_data.get("imperial_guardian_enabled", False))
        action.imperial_guardian_no_player_alert_delay = int(old_data.get("imperial_guardian_no_player_alert_delay", 10) or 10)
        action.imperial_guardian_teaching_corner_x1 = int(old_data.get("imperial_guardian_teaching_corner_x1", 0) or 0)
        action.imperial_guardian_teaching_corner_y1 = int(old_data.get("imperial_guardian_teaching_corner_y1", 0) or 0)
        action.imperial_guardian_teaching_corner_x2 = int(old_data.get("imperial_guardian_teaching_corner_x2", 0) or 0)
        action.imperial_guardian_teaching_corner_y2 = int(old_data.get("imperial_guardian_teaching_corner_y2", 0) or 0)

        self.assertFalse(action.imperial_guardian_enabled)
        self.assertEqual(action.imperial_guardian_no_player_alert_delay, 10)
        self.assertEqual(action.imperial_guardian_teaching_corner_x1, 0)

    def test_action_to_dict_contains_all_fields(self):
        """_action_to_dict phải include tất cả 6 fields."""
        try:
            from tool_manager import Tool
        except ImportError:
            from src.logic.tool_manager import Tool

        action = self._make_action(
            imperial_guardian_enabled=True,
            imperial_guardian_no_player_alert_delay=20,
        )
        d = Tool._action_to_dict(action)
        self.assertIn("imperial_guardian_enabled", d)
        self.assertIn("imperial_guardian_no_player_alert_delay", d)
        self.assertIn("imperial_guardian_teaching_corner_x1", d)
        self.assertIn("imperial_guardian_teaching_corner_y1", d)
        self.assertIn("imperial_guardian_teaching_corner_x2", d)
        self.assertIn("imperial_guardian_teaching_corner_y2", d)
        self.assertTrue(d["imperial_guardian_enabled"])
        self.assertEqual(d["imperial_guardian_no_player_alert_delay"], 20)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for special event tracking persistence (round-trip and backward compat)."""

import unittest


class TestSpecialEventTrackingPersistence(unittest.TestCase):
    """Tests for imperial_guardian_* fields persistence in tool_manager."""

    def _make_action(self, **kwargs):
        """Create AutoAction with given field values."""
        try:
            from action_type import AutoAction, ActionType, ActionMode
        except ImportError:
            from src.logic.action_type import AutoAction, ActionType, ActionMode
        action = AutoAction(
            name="test_action",
            purpose="test",
            action_type=ActionType.READ_PASSIVE,
            mode=ActionMode.PASSIVE,
        )
        for k, v in kwargs.items():
            setattr(action, k, v)
        return action

    def _round_trip(self, action):
        """Serialize action to dict then deserialize back using production loader."""
        try:
            from tool_manager import Tool
        except ImportError:
            from src.logic.tool_manager import Tool
        # Create a real Tool with the action
        tool = Tool(name="test_tool", actions=[action])
        # Serialize to dict
        tool_dict = tool.to_dict()
        # Deserialize using production from_dict()
        restored_tool = Tool.from_dict(tool_dict)
        return restored_tool.actions[0]

    def test_round_trip_enabled_true(self):
        action = self._make_action(
            imperial_guardian_enabled=True,
            imperial_guardian_no_player_alert_delay=15,
            imperial_guardian_teaching_corner_x1=10,
            imperial_guardian_teaching_corner_y1=20,
            imperial_guardian_teaching_corner_x2=100,
            imperial_guardian_teaching_corner_y2=80,
            imperial_guardian_ocr_engine="winrt",
        )
        restored = self._round_trip(action)
        self.assertTrue(restored.imperial_guardian_enabled)
        self.assertEqual(restored.imperial_guardian_no_player_alert_delay, 15)
        self.assertEqual(restored.imperial_guardian_teaching_corner_x1, 10)
        self.assertEqual(restored.imperial_guardian_teaching_corner_y1, 20)
        self.assertEqual(restored.imperial_guardian_teaching_corner_x2, 100)
        self.assertEqual(restored.imperial_guardian_teaching_corner_y2, 80)
        self.assertEqual(restored.imperial_guardian_ocr_engine, "winrt")

    def test_round_trip_enabled_false(self):
        action = self._make_action(imperial_guardian_enabled=False)
        restored = self._round_trip(action)
        self.assertFalse(restored.imperial_guardian_enabled)

    def test_backward_compat_missing_fields_use_defaults(self):
        """JSON cũ không có fields mới → default values via production loader."""
        try:
            from tool_manager import Tool
            from action_type import ActionType, ActionMode
        except ImportError:
            from src.logic.tool_manager import Tool
            from src.logic.action_type import ActionType, ActionMode
        
        # Create old JSON data without imperial_guardian_* fields
        old_tool_data = {
            "id": "test-id",
            "name": "test_tool",
            "actions": [{
                "name": "test_action",
                "purpose": "test",
                "action_type": ActionType.READ_PASSIVE.value,  # Use actual enum value
                "mode": ActionMode.PASSIVE.value,
                "passive_mode": "special_event_tracking",
                "params": {}
                # Note: no imperial_guardian_* fields
            }]
        }
        
        # Load using production from_dict()
        restored_tool = Tool.from_dict(old_tool_data)
        
        # Should have at least one action
        self.assertGreater(len(restored_tool.actions), 0)
        action = restored_tool.actions[0]
        
        # Verify defaults applied
        self.assertFalse(action.imperial_guardian_enabled)
        self.assertEqual(action.imperial_guardian_no_player_alert_delay, 10)
        self.assertEqual(action.imperial_guardian_teaching_corner_x1, 0)
        self.assertEqual(action.imperial_guardian_ocr_engine, "auto")

    def test_action_to_dict_contains_all_fields(self):
        """_action_to_dict phải include tất cả 6 fields."""
        try:
            from tool_manager import Tool
        except ImportError:
            from src.logic.tool_manager import Tool

        action = self._make_action(
            imperial_guardian_enabled=True,
            imperial_guardian_no_player_alert_delay=20,
        )
        d = Tool._action_to_dict(action)
        self.assertIn("imperial_guardian_enabled", d)
        self.assertIn("imperial_guardian_no_player_alert_delay", d)
        self.assertIn("imperial_guardian_teaching_corner_x1", d)
        self.assertIn("imperial_guardian_teaching_corner_y1", d)
        self.assertIn("imperial_guardian_teaching_corner_x2", d)
        self.assertIn("imperial_guardian_teaching_corner_y2", d)
        self.assertIn("imperial_guardian_ocr_engine", d)
        self.assertTrue(d["imperial_guardian_enabled"])
        self.assertEqual(d["imperial_guardian_no_player_alert_delay"], 20)
        self.assertEqual(d["imperial_guardian_ocr_engine"], "auto")


if __name__ == "__main__":
    unittest.main()
