"""Test Clean Architecture components."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from domain.value_objects.action_type import ActionType
from domain.entities.action import AutoAction
from domain.entities.tool import Tool
from domain.entities.execution_result import ActionResult, CycleResult


def test_action_type_enum():
    """Test ActionType enum values."""
    # Domain ActionType uses English names
    assert ActionType.KEYBOARD.name == "KEYBOARD"
    assert ActionType.MOUSE_CLICK.name == "MOUSE_CLICK"
    assert ActionType.IMAGE_DETECT.name == "IMAGE_DETECT"
    assert ActionType.WAIT.name == "WAIT"
    assert ActionType.READ_PASSIVE.name == "READ_PASSIVE"


def test_auto_action_creation():
    """Test AutoAction entity creation."""
    action = AutoAction(
        name="Test Action",
        action_type=ActionType.KEYBOARD,
        key="a",
        modifiers=["ctrl"],
    )
    
    assert action.name == "Test Action"
    assert action.action_type == ActionType.KEYBOARD
    assert action.key == "a"
    assert action.modifiers == ["ctrl"]
    assert action.timeout == 30.0  # default
    assert action.delay == 0.0  # default


def test_auto_action_serializable_fields():
    """Test AutoAction SSOT serializable_fields."""
    fields = AutoAction.serializable_fields()
    
    # Check essential fields exist
    assert 'name' in fields
    assert 'action_type' in fields
    assert 'timeout' in fields
    assert 'goto_step_enabled' in fields
    assert 'timeout_goto_enabled' in fields
    assert 'key' in fields
    assert 'image_path' in fields


def test_tool_creation():
    """Test Tool entity creation."""
    action = AutoAction(
        name="Action 1",
        action_type=ActionType.KEYBOARD,
        key="esc",
    )
    
    tool = Tool(
        name="Test Tool",
        actions=[action],
        loop_enabled=True,
        loop_count=3,
    )
    
    assert tool.name == "Test Tool"
    assert len(tool.actions) == 1
    assert tool.loop_enabled is True
    assert tool.loop_count == 3


def test_tool_delay_properties():
    """Test Tool delay property conversions."""
    tool = Tool(
        name="Test",
        loop_pre_delay_100ms=10,  # 1.0 second
        loop_post_delay_100ms=20,  # 2.0 seconds
    )
    
    assert tool.loop_pre_delay == 1.0
    assert tool.loop_post_delay == 2.0


def test_action_result_creation():
    """Test ActionResult value object."""
    result = ActionResult(
        success=True,
        action_name="Test",
        action_type=ActionType.KEYBOARD,
        execution_time_ms=150.5,
    )
    
    assert result.success is True
    assert result.action_name == "Test"
    assert result.execution_time_ms == 150.5
    assert result.timed_out is False
    assert result.cancelled is False


def test_cycle_result_creation():
    """Test CycleResult value object."""
    result = CycleResult(completed=True)
    
    assert result.completed is True
    assert result.cancelled is False
    assert result.next_action_index is None


def test_cycle_result_with_goto():
    """Test CycleResult with goto index."""
    result = CycleResult(next_action_index=2)
    
    assert result.completed is False
    assert result.next_action_index == 2


if __name__ == "__main__":
    test_action_type_enum()
    test_auto_action_creation()
    test_auto_action_serializable_fields()
    test_tool_creation()
    test_tool_delay_properties()
    test_action_result_creation()
    test_cycle_result_creation()
    test_cycle_result_with_goto()
    print("✅ All Clean Architecture tests passed!")
