"""Integration-oriented tests for event tracking configuration."""

from src.logic.action_type import ActionMode, ActionType, AutoAction
from src.logic.system_executor.event_tracking_helper import match_ocr_pattern
from src.logic.tool_manager import Tool


class TestEventTrackingIntegration:
    """Test new event tracking behavior."""

    def test_event_tracking_requires_pattern_and_teaching_roi(self):
        action = AutoAction(
            name="Test Event Tracking",
            purpose="Test",
            action_type=ActionType.READ_PASSIVE,
            mode=ActionMode.ACTIVE,
            passive_mode="event_tracking",
            event_ocr_pattern="{event_name} sẽ bắt đầu sau {minutes} phút",
            teaching_corner_x1=100,
            teaching_corner_y1=200,
            teaching_corner_x2=400,
            teaching_corner_y2=250,
        )

        assert action.passive_mode == "event_tracking"
        assert action.event_ocr_pattern
        assert action.teaching_corner_x1 == 100
        assert action.teaching_corner_y1 == 200
        assert action.teaching_corner_x2 == 400
        assert action.teaching_corner_y2 == 250

    def test_event_tracking_match_represents_action_completion_trigger(self):
        action = AutoAction(
            name="Test Event Tracking",
            purpose="Test",
            action_type=ActionType.READ_PASSIVE,
            mode=ActionMode.ACTIVE,
            passive_mode="event_tracking",
            event_ocr_pattern="{event_name} sẽ bắt đầu sau {minutes} phút",
            event_match_threshold=100.0,
        )

        ocr_text = "Boss Rồng sẽ bắt đầu sau 5 phút"
        result = match_ocr_pattern(ocr_text, action.event_ocr_pattern, action.event_match_threshold)

        assert result is not None
        assert ("event_name", "Boss Rồng") in result["variables"]
        assert ("minutes", "5") in result["variables"]


class TestEventTrackingPersistence:
    """Test event tracking persistence for the new model."""

    def test_event_tracking_settings_saved_to_action(self):
        action = AutoAction(
            name="Test Event Tracking",
            purpose="Test",
            action_type=ActionType.READ_PASSIVE,
            mode=ActionMode.ACTIVE,
        )

        action.passive_mode = "event_tracking"
        action.event_ocr_pattern = "{event_name} sẽ bắt đầu sau {minutes} phút"
        action.event_match_threshold = 85.0
        action.event_ocr_engine = "easyocr"
        action.event_reappear_timeout_minutes = 15
        action.teaching_corner_x1 = 100
        action.teaching_corner_y1 = 200
        action.teaching_corner_x2 = 400
        action.teaching_corner_y2 = 250

        assert action.passive_mode == "event_tracking"
        assert action.event_ocr_pattern == "{event_name} sẽ bắt đầu sau {minutes} phút"
        assert action.event_match_threshold == 85.0
        assert action.event_ocr_engine == "easyocr"
        assert action.event_reappear_timeout_minutes == 15

    def test_event_tracking_settings_serialized_to_dict(self):
        action = AutoAction(
            name="Test Event Tracking",
            purpose="Test",
            action_type=ActionType.READ_PASSIVE,
            mode=ActionMode.ACTIVE,
            passive_mode="event_tracking",
            event_ocr_pattern="{event_name} sẽ bắt đầu sau {minutes} phút",
            event_match_threshold=85.0,
            event_ocr_engine="easyocr",
            event_reappear_timeout_minutes=15,
            teaching_corner_x1=100,
            teaching_corner_y1=200,
            teaching_corner_x2=400,
            teaching_corner_y2=250,
        )

        action_dict = Tool._action_to_dict(action)

        assert "event_ocr_pattern" in action_dict
        assert "event_match_threshold" in action_dict
        assert "event_ocr_engine" in action_dict
        assert "event_reappear_timeout_minutes" in action_dict
        assert action_dict["event_reappear_timeout_minutes"] == 15
        assert "event_delay_threshold" not in action_dict
        assert "event_reset_interval" not in action_dict
        assert "event_telegram_message" not in action_dict
