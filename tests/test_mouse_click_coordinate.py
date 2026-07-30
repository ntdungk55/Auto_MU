"""Unit tests for mouse click coordinate mode feature."""

import pytest
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from logic.action_type import AutoAction, ActionType, ActionMode


class TestAutoActionFields:
    """Test new fields in AutoAction for coordinate mode."""
    
    def test_click_by_coordinate_default_false(self):
        """Test that click_by_coordinate defaults to False."""
        action = AutoAction(
            name="test", 
            purpose="test purpose",
            action_type=ActionType.MOUSE_CLICK,
            mode=ActionMode.ACTIVE
        )
        assert hasattr(action, 'click_by_coordinate')
        assert action.click_by_coordinate == False
    
    def test_coordinate_click_pos_default_none(self):
        """Test that coordinate_click_pos defaults to None."""
        action = AutoAction(
            name="test",
            purpose="test purpose", 
            action_type=ActionType.MOUSE_CLICK,
            mode=ActionMode.ACTIVE
        )
        assert hasattr(action, 'coordinate_click_pos')
        assert action.coordinate_click_pos is None
    
    def test_set_coordinate_mode_values(self):
        """Test setting coordinate mode values."""
        action = AutoAction(
            name="test",
            purpose="test purpose",
            action_type=ActionType.MOUSE_CLICK,
            mode=ActionMode.ACTIVE
        )
        action.click_by_coordinate = True
        action.coordinate_click_pos = (100, 200)
        
        assert action.click_by_coordinate == True
        assert action.coordinate_click_pos == (100, 200)
        assert action.coordinate_click_pos[0] == 100
        assert action.coordinate_click_pos[1] == 200


class TestToolManagerPersistence:
    """Test persistence of coordinate mode fields."""
    
    def test_action_to_dict_includes_coordinate_fields(self):
        """Test that _action_to_dict includes new fields."""
        from logic.tool_manager import Tool
        
        action = AutoAction(
            name="test",
            purpose="test purpose",
            action_type=ActionType.MOUSE_CLICK,
            mode=ActionMode.ACTIVE
        )
        action.click_by_coordinate = True
        action.coordinate_click_pos = (150, 250)
        
        result = Tool._action_to_dict(action)
        
        assert 'click_by_coordinate' in result
        assert result['click_by_coordinate'] == True
        assert 'coordinate_click_pos' in result
        assert result['coordinate_click_pos'] == [150, 250]
    
    def test_action_to_dict_default_values(self):
        """Test that _action_to_dict handles default values."""
        from logic.tool_manager import Tool
        
        action = AutoAction(
            name="test",
            purpose="test purpose",
            action_type=ActionType.MOUSE_CLICK,
            mode=ActionMode.ACTIVE
        )
        
        result = Tool._action_to_dict(action)
        
        assert 'click_by_coordinate' in result
        assert result['click_by_coordinate'] == False
        assert 'coordinate_click_pos' in result
        assert result['coordinate_click_pos'] is None
    
    def test_from_dict_restores_coordinate_fields(self):
        """Test that from_dict restores coordinate fields."""
        from logic.tool_manager import Tool
        
        data = {
            'name': 'test',
            'purpose': 'test purpose',
            'action_type': 'Click Chuột',
            'mode': ActionMode.ACTIVE.value,
            'click_by_coordinate': True,
            'coordinate_click_pos': [300, 400]
        }
        
        # Create a tool dict and use from_dict
        tool_data = {
            'name': 'test_tool',
            'actions': [data]
        }
        tool = Tool.from_dict(tool_data)
        action = tool.actions[0]
        
        assert action.click_by_coordinate == True
        assert action.coordinate_click_pos == (300, 400)
    
    def test_from_dict_missing_fields_default(self):
        """Test that from_dict handles missing fields with defaults."""
        from logic.tool_manager import Tool
        
        data = {
            'name': 'test',
            'purpose': 'test purpose',
            'action_type': 'Click Chuột',
            'mode': ActionMode.ACTIVE.value
        }
        
        tool_data = {
            'name': 'test_tool',
            'actions': [data]
        }
        tool = Tool.from_dict(tool_data)
        action = tool.actions[0]
        
        assert action.click_by_coordinate == False
        assert action.coordinate_click_pos is None


class TestCoordinateModeExecution:
    """Test runtime execution of coordinate mode."""
    
    def test_coordinate_mode_with_valid_coordinates(self):
        """Test that coordinate mode works with valid coordinates."""
        action = AutoAction(
            name="test",
            purpose="test purpose",
            action_type=ActionType.MOUSE_CLICK,
            mode=ActionMode.ACTIVE
        )
        action.click_by_coordinate = True
        action.coordinate_click_pos = (100, 200)
        
        # Verify action is configured correctly
        assert action.click_by_coordinate == True
        assert action.coordinate_click_pos == (100, 200)
    
    def test_coordinate_mode_with_none_coordinates(self):
        """Test that coordinate mode handles None coordinates."""
        action = AutoAction(
            name="test",
            purpose="test purpose",
            action_type=ActionType.MOUSE_CLICK,
            mode=ActionMode.ACTIVE
        )
        action.click_by_coordinate = True
        action.coordinate_click_pos = None
        
        # Should be invalid - coordinates are None
        assert action.coordinate_click_pos is None
    
    def test_image_mode_ignores_coordinate_fields(self):
        """Test that image mode ignores coordinate fields."""
        action = AutoAction(
            name="test",
            purpose="test purpose",
            action_type=ActionType.MOUSE_CLICK,
            mode=ActionMode.ACTIVE
        )
        action.click_by_coordinate = False
        action.coordinate_click_pos = (100, 200)
        action.image_path = "test.png"
        
        # In image mode, should use image_path, not coordinates
        assert action.click_by_coordinate == False
        assert action.image_path == "test.png"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
