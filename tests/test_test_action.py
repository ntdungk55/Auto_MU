"""Unit tests for Test Action feature."""

import pytest
from src.logic.action_type import ActionType, ActionMode, AutoAction


class TestActionValidation:
    """Test action validation before testing."""
    
    def test_keyboard_action_has_value(self):
        """Test that KEYBOARD action has value set."""
        action = AutoAction(
            name="Test Key",
            purpose="Test",
            action_type=ActionType.KEYBOARD,
            mode=ActionMode.ACTIVE,
            value="tab"
        )
        assert action.value == "tab"
        assert action.action_type == ActionType.KEYBOARD
    
    def test_mouse_click_coordinate_mode_has_position(self):
        """Test that MOUSE_CLICK coordinate mode has position set."""
        action = AutoAction(
            name="Test Click",
            purpose="Test",
            action_type=ActionType.MOUSE_CLICK,
            mode=ActionMode.ACTIVE,
            value=""
        )
        action.click_by_coordinate = True
        action.coordinate_click_pos = (100, 200)
        
        assert action.click_by_coordinate is True
        assert action.coordinate_click_pos == (100, 200)
    
    def test_mouse_click_image_mode_has_image_path(self):
        """Test that MOUSE_CLICK image mode has image_path set."""
        action = AutoAction(
            name="Test Click",
            purpose="Test",
            action_type=ActionType.MOUSE_CLICK,
            mode=ActionMode.ACTIVE,
            value=""
        )
        action.click_by_coordinate = False
        action.image_path = "tools/test/image.png"
        
        assert action.click_by_coordinate is False
        assert action.image_path == "tools/test/image.png"
    
    def test_wait_action_has_timeout(self):
        """Test that WAIT action has timeout set."""
        action = AutoAction(
            name="Test Wait",
            purpose="Test",
            action_type=ActionType.WAIT,
            mode=ActionMode.ACTIVE,
            value=""
        )
        action.timeout = 2.5
        
        assert action.timeout == 2.5
        assert action.action_type == ActionType.WAIT


class TestActionTypeDetection:
    """Test action type detection for test execution."""
    
    def test_detect_keyboard_action(self):
        """Test detecting KEYBOARD action type."""
        action = AutoAction(
            name="Press Tab",
            purpose="Test",
            action_type=ActionType.KEYBOARD,
            mode=ActionMode.ACTIVE,
            value="tab"
        )
        assert action.action_type == ActionType.KEYBOARD
        assert action.action_type.value == "Ấn Phím"
    
    def test_detect_mouse_click_action(self):
        """Test detecting MOUSE_CLICK action type."""
        action = AutoAction(
            name="Click Button",
            purpose="Test",
            action_type=ActionType.MOUSE_CLICK,
            mode=ActionMode.ACTIVE,
            value=""
        )
        assert action.action_type == ActionType.MOUSE_CLICK
        assert action.action_type.value == "Click Chuột"
    
    def test_detect_image_detect_action(self):
        """Test detecting IMAGE_DETECT action type."""
        action = AutoAction(
            name="Detect Image",
            purpose="Test",
            action_type=ActionType.IMAGE_DETECT,
            mode=ActionMode.ACTIVE,
            value=""
        )
        assert action.action_type == ActionType.IMAGE_DETECT
        assert action.action_type.value == "Bắt Hình Ảnh"
    
    def test_detect_wait_action(self):
        """Test detecting WAIT action type."""
        action = AutoAction(
            name="Wait",
            purpose="Test",
            action_type=ActionType.WAIT,
            mode=ActionMode.ACTIVE,
            value=""
        )
        assert action.action_type == ActionType.WAIT
        assert action.action_type.value == "Chờ"


class TestConflictHandling:
    """Test conflict handling between test action and running tool."""
    
    def test_action_can_be_copied_for_test(self):
        """Test that action can be deep copied for isolated test."""
        import copy
        
        action = AutoAction(
            name="Original",
            purpose="Test",
            action_type=ActionType.KEYBOARD,
            mode=ActionMode.ACTIVE,
            value="tab"
        )
        action.delay = 0.5
        
        copied = copy.deepcopy(action)
        copied.name = "Copied"
        
        assert action.name == "Original"
        assert copied.name == "Copied"
        assert copied.value == "tab"
        assert copied.delay == 0.5
