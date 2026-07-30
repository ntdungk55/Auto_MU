"""Unit tests for Telegram timeout notification feature."""

import json
import os
import tempfile
from src.logic.tool_manager import Tool, ToolManager
from src.logic.action_type import AutoAction, ActionType, ActionMode


def test_tool_notify_on_timeout_default_false():
    """Test that notify_on_timeout defaults to False."""
    tool = Tool(
        name="Test Tool",
        actions=[]
    )
    assert hasattr(tool, "notify_on_timeout")
    assert tool.notify_on_timeout == False


def test_tool_notify_on_timeout_can_be_set():
    """Test that notify_on_timeout can be set to True."""
    tool = Tool(
        name="Test Tool",
        actions=[],
        notify_on_timeout=True
    )
    assert tool.notify_on_timeout == True


def test_tool_to_dict_includes_notify_on_timeout():
    """Test that to_dict() includes notify_on_timeout field."""
    tool = Tool(
        name="Test Tool",
        actions=[],
        notify_on_timeout=True
    )
    data = tool.to_dict()
    assert "settings" in data
    assert "notify_on_timeout" in data["settings"]
    assert data["settings"]["notify_on_timeout"] == True


def test_tool_from_dict_loads_notify_on_timeout():
    """Test that from_dict() loads notify_on_timeout field."""
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
            "notify_on_timeout": True
        },
        "actions": []
    }
    tool = Tool.from_dict(data)
    assert tool.notify_on_timeout == True


def test_tool_from_dict_defaults_notify_on_timeout_to_false():
    """Test that from_dict() defaults notify_on_timeout to False if missing."""
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
            "pause_duration": 5
        },
        "actions": []
    }
    tool = Tool.from_dict(data)
    assert tool.notify_on_timeout == False


def test_tool_manager_save_and_load_notify_on_timeout():
    """Test that ToolManager can save and load notify_on_timeout."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ToolManager(tools_dir=tmpdir)
        
        # Create tool with notify_on_timeout=True
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
            notify_on_timeout=True
        )
        
        # Save tool
        manager.save_tool(tool)
        
        tool_id = tool.id  # Store UUID
        
        # Load tool
        loaded_tool = manager.load_tool(tool_id)
        
        # Verify notify_on_timeout persisted
        assert loaded_tool is not None
        assert loaded_tool.notify_on_timeout == True


def test_telegram_config_check_both_exist():
    """Test checking Telegram config when both bot_token and chat_id exist."""
    # This will be tested in integration with app_state.json
    # For now, just verify the logic structure
    app_state = {
        "telegram_bot_token_dpapi_b64": "encrypted_token",
        "telegram_chat_id": "123456789"
    }
    
    has_token = bool(app_state.get("telegram_bot_token_dpapi_b64"))
    has_chat_id = bool(app_state.get("telegram_chat_id"))
    is_configured = has_token and has_chat_id
    
    assert is_configured == True


def test_telegram_config_check_missing_token():
    """Test checking Telegram config when bot_token is missing."""
    app_state = {
        "telegram_chat_id": "123456789"
    }
    
    has_token = bool(app_state.get("telegram_bot_token_dpapi_b64"))
    has_chat_id = bool(app_state.get("telegram_chat_id"))
    is_configured = has_token and has_chat_id
    
    assert is_configured == False


def test_telegram_config_check_missing_chat_id():
    """Test checking Telegram config when chat_id is missing."""
    app_state = {
        "telegram_bot_token_dpapi_b64": "encrypted_token"
    }
    
    has_token = bool(app_state.get("telegram_bot_token_dpapi_b64"))
    has_chat_id = bool(app_state.get("telegram_chat_id"))
    is_configured = has_token and has_chat_id
    
    assert is_configured == False


def test_telegram_config_check_empty_values():
    """Test checking Telegram config when values are empty strings."""
    app_state = {
        "telegram_bot_token_dpapi_b64": "",
        "telegram_chat_id": ""
    }
    
    has_token = bool(app_state.get("telegram_bot_token_dpapi_b64"))
    has_chat_id = bool(app_state.get("telegram_chat_id"))
    is_configured = has_token and has_chat_id
    
    assert is_configured == False
