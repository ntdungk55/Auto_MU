"""Unit tests for input blocking feature."""

import json
import os
import tempfile
from src.logic.tool_manager import Tool, ToolManager
from src.logic.action_type import AutoAction, ActionType, ActionMode


def test_tool_block_input_enabled_default_false():
    """Test that block_input_enabled defaults to False."""
    tool = Tool(
        name="Test Tool",
        actions=[]
    )
    assert hasattr(tool, "block_input_enabled")
    assert tool.block_input_enabled == False


def test_tool_block_input_duration_default_3():
    """Test that block_input_duration defaults to 3.0."""
    tool = Tool(
        name="Test Tool",
        actions=[]
    )
    assert hasattr(tool, "block_input_duration")
    assert tool.block_input_duration == 3.0


def test_tool_block_input_enabled_can_be_set():
    """Test that block_input_enabled can be set to True."""
    tool = Tool(
        name="Test Tool",
        actions=[],
        block_input_enabled=True
    )
    assert tool.block_input_enabled == True


def test_tool_block_input_duration_can_be_set():
    """Test that block_input_duration can be set to custom value."""
    tool = Tool(
        name="Test Tool",
        actions=[],
        block_input_duration=5.0
    )
    assert tool.block_input_duration == 5.0


def test_tool_block_input_duration_clamped_min():
    """Test that block_input_duration is clamped to minimum 0.1."""
    tool = Tool(
        name="Test Tool",
        actions=[],
        block_input_duration=0.05
    )
    assert tool.block_input_duration == 0.1


def test_tool_block_input_duration_clamped_max():
    """Test that block_input_duration is clamped to maximum 10.0."""
    tool = Tool(
        name="Test Tool",
        actions=[],
        block_input_duration=15.0
    )
    assert tool.block_input_duration == 10.0


def test_tool_to_dict_includes_block_input_settings():
    """Test that to_dict() includes block_input settings."""
    tool = Tool(
        name="Test Tool",
        actions=[],
        block_input_enabled=True,
        block_input_duration=5.0
    )
    data = tool.to_dict()
    assert "settings" in data
    assert "block_input_enabled" in data["settings"]
    assert "block_input_duration" in data["settings"]
    assert data["settings"]["block_input_enabled"] == True
    assert data["settings"]["block_input_duration"] == 5.0


def test_tool_from_dict_loads_block_input_settings():
    """Test that from_dict() loads block_input settings."""
    data = {
        "name": "Test Tool",
        "settings": {
            "loop_enabled": False,
            "loop_mode": "forever",
            "loop_count": 1,
            "loop_pre_delay_100ms": 0,
            "loop_post_delay_100ms": 0,
            "stop_on_timeout": True,
            "restart_on_timeout": False,
            "run_lock_mode": 0,
            "user_input_mode": "ignore",
            "pause_duration": 5,
            "notify_on_timeout": False,
            "block_input_enabled": True,
            "block_input_duration": 5.0
        },
        "actions": []
    }
    tool = Tool.from_dict(data)
    assert tool.block_input_enabled == True
    assert tool.block_input_duration == 5.0


def test_tool_from_dict_defaults_block_input_settings():
    """Test that from_dict() defaults block_input settings if missing."""
    data = {
        "name": "Test Tool",
        "settings": {
            "loop_enabled": False,
            "loop_mode": "forever",
            "loop_count": 1,
            "loop_pre_delay_100ms": 0,
            "loop_post_delay_100ms": 0,
            "stop_on_timeout": True,
            "restart_on_timeout": False,
            "run_lock_mode": 0,
            "user_input_mode": "ignore",
            "pause_duration": 5,
            "notify_on_timeout": False
        },
        "actions": []
    }
    tool = Tool.from_dict(data)
    assert tool.block_input_enabled == False
    assert tool.block_input_duration == 3.0


def test_tool_manager_save_and_load_block_input_settings():
    """Test that ToolManager can save and load block_input settings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ToolManager(tools_dir=tmpdir)
        
        # Create tool with block_input settings
        action = AutoAction(
            name="Test Action",
            purpose="Test",
            action_type=ActionType.KEYBOARD,
            mode=ActionMode.ACTIVE,
            value="test"
        )
        tool = Tool(
            name="Test Tool",
            actions=[action],
            block_input_enabled=True,
            block_input_duration=7.5
        )
        
        # Save tool
        manager.save_tool(tool)
        
        tool_id = tool.id  # Store UUID
        
        # Load tool
        loaded_tool = manager.load_tool(tool_id)
        
        # Verify settings persisted
        assert loaded_tool is not None
        assert loaded_tool.block_input_enabled == True
        assert loaded_tool.block_input_duration == 7.5


def test_block_input_duration_range_validation():
    """Test that block_input_duration validates range correctly."""
    # Test valid values
    tool1 = Tool(name="T1", actions=[], block_input_duration=0.1)
    assert tool1.block_input_duration == 0.1
    
    tool2 = Tool(name="T2", actions=[], block_input_duration=5.0)
    assert tool2.block_input_duration == 5.0
    
    tool3 = Tool(name="T3", actions=[], block_input_duration=10.0)
    assert tool3.block_input_duration == 10.0
    
    # Test clamping
    tool4 = Tool(name="T4", actions=[], block_input_duration=0.0)
    assert tool4.block_input_duration == 0.1
    
    tool5 = Tool(name="T5", actions=[], block_input_duration=20.0)
    assert tool5.block_input_duration == 10.0
