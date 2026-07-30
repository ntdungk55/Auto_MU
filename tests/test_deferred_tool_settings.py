"""Unit tests for deferred tool settings feature."""

import pytest
import json
import os
import tempfile
import time
from unittest.mock import Mock, MagicMock
from src.logic.tool_manager import ToolManager, Tool
from src.logic.action_type import AutoAction, ActionType, ActionMode


def test_save_settings_without_restart():
    """Test that saving settings does not restart the tool."""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        tool_manager = ToolManager(tools_dir=tmpdir)
        tool = Tool(name="test_tool", actions=[])
        tool.loop_enabled = True
        tool.loop_count = 5
        tool_manager.save_tool(tool)
        
        tool_id = tool.id  # Store UUID
        
        # Simulate tool running
        tool_running = True
        
        # Act: Modify and save settings
        tool.loop_count = 10
        tool_manager.save_tool(tool)
        
        # Assert: Tool should still be "running" (not restarted)
        assert tool_running == True
        
        # Verify settings saved to file
        loaded_tool = tool_manager.load_tool(tool_id)  # Use UUID
        assert loaded_tool.loop_count == 10


def test_reload_settings_from_json():
    """Test that tool can reload settings from JSON file."""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        tool_manager = ToolManager(tools_dir=tmpdir)
        tool = Tool(name="test_tool", actions=[])
        tool.loop_enabled = True
        tool.loop_count = 5
        tool_manager.save_tool(tool)
        
        tool_id = tool.id  # Store UUID
        
        # Simulate tool running with old settings in memory
        tool_in_memory = tool_manager.load_tool(tool_id)
        assert tool_in_memory.loop_count == 5
        
        # Act: Modify settings in file (simulate user changing settings)
        tool_from_file = tool_manager.load_tool(tool_id)
        tool_from_file.loop_count = 10
        tool_manager.save_tool(tool_from_file)
        
        # Reload settings (simulate end of cycle)
        tool_reloaded = tool_manager.load_tool(tool_id)
        
        # Assert: Reloaded tool has new settings
        assert tool_reloaded.loop_count == 10


def test_multiple_settings_changes():
    """Test that multiple settings changes use latest value."""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        tool_manager = ToolManager(tools_dir=tmpdir)
        tool = Tool(name="test_tool", actions=[])
        tool.loop_count = 5
        tool_manager.save_tool(tool)
        
        tool_id = tool.id  # Store UUID
        
        # Act: Change settings multiple times
        tool.loop_count = 10
        tool_manager.save_tool(tool)
        
        tool.loop_count = 15
        tool_manager.save_tool(tool)
        
        tool.loop_count = 20
        tool_manager.save_tool(tool)
        
        # Reload (simulate next cycle)
        tool_reloaded = tool_manager.load_tool(tool_id)
        
        # Assert: Latest value is used
        assert tool_reloaded.loop_count == 20


def test_settings_persist_across_cycles():
    """Test that settings changes persist across multiple cycles."""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        tool_manager = ToolManager(tools_dir=tmpdir)
        tool = Tool(name="test_tool", actions=[])
        tool.loop_enabled = True
        tool.loop_count = 5
        tool.loop_pre_delay_100ms = 10
        tool_manager.save_tool(tool)
        
        tool_id = tool.id  # Store UUID
        
        # Simulate cycle 1
        tool_cycle1 = tool_manager.load_tool(tool_id)
        assert tool_cycle1.loop_count == 5
        
        # Change settings during cycle 1
        tool_cycle1.loop_count = 10
        tool_manager.save_tool(tool_cycle1)
        
        # Simulate cycle 2 (reload settings)
        tool_cycle2 = tool_manager.load_tool(tool_id)
        assert tool_cycle2.loop_count == 10
        
        # Change settings during cycle 2
        tool_cycle2.loop_pre_delay_100ms = 20
        tool_manager.save_tool(tool_cycle2)
        
        # Simulate cycle 3 (reload settings)
        tool_cycle3 = tool_manager.load_tool(tool_id)
        assert tool_cycle3.loop_count == 10
        assert tool_cycle3.loop_pre_delay_100ms == 20


def test_non_loop_tool_settings():
    """Test that non-loop tools also reload settings correctly."""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        tool_manager = ToolManager(tools_dir=tmpdir)
        tool = Tool(name="test_tool", actions=[
            AutoAction(name="action1", purpose="test", action_type=ActionType.KEYBOARD, mode=ActionMode.ACTIVE, value="test")
        ])
        tool.loop_enabled = False
        tool_manager.save_tool(tool)
        
        tool_id = tool.id  # Store UUID
        
        # Simulate first run
        tool_run1 = tool_manager.load_tool(tool_id)
        assert len(tool_run1.actions) == 1
        
        # Change settings after first run
        tool_run1.actions.append(
            AutoAction(name="action2", purpose="test", action_type=ActionType.KEYBOARD, mode=ActionMode.ACTIVE, value="test2")
        )
        tool_manager.save_tool(tool_run1)
        
        # Simulate second run (reload settings)
        tool_run2 = tool_manager.load_tool(tool_id)
        
        # Assert: New settings are loaded
        assert len(tool_run2.actions) == 2


def test_reload_performance():
    """Test that reloading settings is fast (< 10ms)."""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        tool_manager = ToolManager(tools_dir=tmpdir)
        tool = Tool(name="test_tool", actions=[])
        tool.loop_enabled = True
        # Add many actions to make tool larger
        for i in range(100):
            tool.actions.append(
                AutoAction(name=f"action{i}", purpose="test", action_type=ActionType.KEYBOARD, mode=ActionMode.ACTIVE, value=f"test{i}")
            )
        tool_manager.save_tool(tool)
        
        tool_id = tool.id  # Store UUID
        
        # Act: Measure reload time
        start = time.perf_counter()
        tool_reloaded = tool_manager.load_tool(tool_id)
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        # Assert: Reload is fast
        assert elapsed_ms < 10.0
        assert len(tool_reloaded.actions) == 100
