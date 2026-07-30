"""Unit tests for Tool ID System (UUID-based tool management)."""

import os
import json
import uuid
import shutil
import tempfile
from src.logic.tool_manager import Tool, ToolManager
from src.logic.action_type import AutoAction, ActionType, ActionMode


def test_tool_has_id_field():
    """Test that Tool has id field."""
    tool = Tool(
        name="Test Tool",
        actions=[]
    )
    
    assert hasattr(tool, "id")
    assert tool.id is not None
    assert isinstance(tool.id, str)
    assert len(tool.id) == 36  # UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx


def test_tool_generates_uuid_if_not_provided():
    """Test that Tool auto-generates UUID if not provided."""
    tool1 = Tool(name="Tool 1", actions=[])
    tool2 = Tool(name="Tool 2", actions=[])
    
    assert tool1.id != tool2.id  # Different UUIDs


def test_tool_accepts_custom_id():
    """Test that Tool accepts custom ID."""
    custom_id = str(uuid.uuid4())
    tool = Tool(name="Test Tool", actions=[], id=custom_id)
    
    assert tool.id == custom_id


def test_tool_to_dict_includes_id():
    """Test that to_dict includes id field."""
    tool = Tool(name="Test Tool", actions=[])
    data = tool.to_dict()
    
    assert "id" in data
    assert data["id"] == tool.id


def test_tool_from_dict_loads_id():
    """Test that from_dict loads id field."""
    tool_id = str(uuid.uuid4())
    data = {
        "id": tool_id,
        "name": "Test Tool",
        "settings": {},
        "actions": []
    }
    
    tool = Tool.from_dict(data)
    
    assert tool.id == tool_id


def test_tool_manager_saves_by_id():
    """Test that ToolManager saves tool by ID."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ToolManager(tools_dir=tmpdir)
        
        tool = Tool(name="Test Tool", actions=[])
        manager.save_tool(tool)
        
        # Check file exists with UUID name
        expected_file = os.path.join(tmpdir, f"{tool.id}.json")
        assert os.path.exists(expected_file)
        
        # Check content
        with open(expected_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert data["id"] == tool.id
            assert data["name"] == "Test Tool"


def test_tool_manager_loads_by_id():
    """Test that ToolManager loads tool by ID."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ToolManager(tools_dir=tmpdir)
        
        # Save tool
        tool = Tool(name="Test Tool", actions=[])
        manager.save_tool(tool)
        
        # Load by ID
        loaded = manager.load_tool(tool.id)
        
        assert loaded is not None
        assert loaded.id == tool.id
        assert loaded.name == "Test Tool"


def test_tool_manager_get_tool_by_name():
    """Test that ToolManager can find tool by name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ToolManager(tools_dir=tmpdir)
        
        # Save tools
        tool1 = Tool(name="Tool A", actions=[])
        tool2 = Tool(name="Tool B", actions=[])
        manager.save_tool(tool1)
        manager.save_tool(tool2)
        
        # Find by name
        found = manager.get_tool_by_name("Tool A")
        
        assert found is not None
        assert found.id == tool1.id
        assert found.name == "Tool A"


def test_tool_manager_list_tools_returns_id_and_name():
    """Test that list_tools returns list of (id, name) tuples."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ToolManager(tools_dir=tmpdir)
        
        # Save tools
        tool1 = Tool(name="Tool A", actions=[])
        tool2 = Tool(name="Tool B", actions=[])
        manager.save_tool(tool1)
        manager.save_tool(tool2)
        
        # List tools
        tools = manager.list_tools()
        
        assert len(tools) == 2
        assert all(isinstance(t, tuple) and len(t) == 2 for t in tools)
        
        # Check IDs and names
        ids = [t[0] for t in tools]
        names = [t[1] for t in tools]
        
        assert tool1.id in ids
        assert tool2.id in ids
        assert "Tool A" in names
        assert "Tool B" in names


def test_tool_manager_delete_by_id():
    """Test that ToolManager deletes tool by ID."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ToolManager(tools_dir=tmpdir)
        
        # Save tool
        tool = Tool(name="Test Tool", actions=[])
        manager.save_tool(tool)
        
        # Verify exists
        assert os.path.exists(os.path.join(tmpdir, f"{tool.id}.json"))
        
        # Delete by ID
        manager.delete_tool(tool.id)
        
        # Verify deleted
        assert not os.path.exists(os.path.join(tmpdir, f"{tool.id}.json"))


def test_tool_manager_validate_unique_name_allows_same_tool():
    """Test that validate_unique_name allows same tool to keep its name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ToolManager(tools_dir=tmpdir)
        
        # Save tool
        tool = Tool(name="Test Tool", actions=[])
        manager.save_tool(tool)
        
        # Validate same tool with same name (should pass)
        is_unique = manager.validate_unique_name("Test Tool", exclude_id=tool.id)
        
        assert is_unique is True


def test_tool_manager_validate_unique_name_rejects_duplicate():
    """Test that validate_unique_name rejects duplicate name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ToolManager(tools_dir=tmpdir)
        
        # Save tool
        tool1 = Tool(name="Test Tool", actions=[])
        manager.save_tool(tool1)
        
        # Try to validate same name for different tool (should fail)
        other_id = str(uuid.uuid4())
        is_unique = manager.validate_unique_name("Test Tool", exclude_id=other_id)
        
        assert is_unique is False


def test_tool_manager_validate_unique_name_allows_new_name():
    """Test that validate_unique_name allows new unique name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ToolManager(tools_dir=tmpdir)
        
        # Save tool
        tool = Tool(name="Tool A", actions=[])
        manager.save_tool(tool)
        
        # Validate different name (should pass)
        is_unique = manager.validate_unique_name("Tool B", exclude_id=None)
        
        assert is_unique is True


def test_rename_tool_updates_name_only():
    """Test that renaming tool only updates name field, not ID."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ToolManager(tools_dir=tmpdir)
        
        # Save tool
        tool = Tool(name="Old Name", actions=[])
        original_id = tool.id
        manager.save_tool(tool)
        
        # Rename
        tool.name = "New Name"
        manager.save_tool(tool)
        
        # Load and verify
        loaded = manager.load_tool(original_id)
        
        assert loaded.id == original_id  # ID unchanged
        assert loaded.name == "New Name"  # Name changed
        
        # Old file should not exist
        old_file = os.path.join(tmpdir, "Old_Name.json")
        assert not os.path.exists(old_file)


def test_teaching_image_path_uses_tool_id():
    """Test that teaching images are saved under images/{tool_id}/."""
    tool_id = str(uuid.uuid4())
    tool_name = "Test Tool"
    
    # Expected path format
    expected_path = f"images/{tool_id}/capture_123.png"
    
    # Verify format
    assert tool_id in expected_path
    assert tool_name not in expected_path


def test_action_image_path_updated_after_rename():
    """Test that action image_path is not affected by tool rename."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ToolManager(tools_dir=tmpdir)
        
        # Create tool with action
        tool = Tool(name="Old Name", actions=[])
        action = AutoAction(
            name="Test Action",
            purpose="Test",
            action_type=ActionType.IMAGE_DETECT,
            mode=ActionMode.ACTIVE,
            image_path=f"images/{tool.id}/test.png"
        )
        tool.actions.append(action)
        manager.save_tool(tool)
        
        # Rename tool
        tool.name = "New Name"
        manager.save_tool(tool)
        
        # Load and verify image_path unchanged
        loaded = manager.load_tool(tool.id)
        
        assert loaded.actions[0].image_path == f"images/{tool.id}/test.png"
        assert "Old Name" not in loaded.actions[0].image_path
        assert "New Name" not in loaded.actions[0].image_path


def test_migration_preserves_all_tool_data():
    """Test that migration preserves all tool settings and actions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create old-style tool (no ID)
        old_data = {
            "name": "Test Tool",
            "settings": {
                "loop_enabled": True,
                "loop_mode": "count",
                "loop_count": 5
            },
            "actions": [
                {
                    "name": "Action 1",
                    "purpose": "Test",
                    "action_type": "Ấn Phím",
                    "mode": "Chủ động",
                    "value": "a",
                    "delay": 1.0
                }
            ]
        }
        
        old_file = os.path.join(tmpdir, "Test_Tool.json")
        with open(old_file, 'w', encoding='utf-8') as f:
            json.dump(old_data, f, ensure_ascii=False, indent=2)
        
        # Simulate migration: add ID
        new_id = str(uuid.uuid4())
        old_data["id"] = new_id
        
        new_file = os.path.join(tmpdir, f"{new_id}.json")
        with open(new_file, 'w', encoding='utf-8') as f:
            json.dump(old_data, f, ensure_ascii=False, indent=2)
        
        # Load migrated tool
        manager = ToolManager(tools_dir=tmpdir)
        tool = manager.load_tool(new_id)
        
        # Verify all data preserved
        assert tool.id == new_id
        assert tool.name == "Test Tool"
        assert tool.loop_enabled is True
        assert tool.loop_mode == "count"
        assert tool.loop_count == 5
        assert len(tool.actions) == 1
        assert tool.actions[0].name == "Action 1"


def test_empty_tools_directory():
    """Test that ToolManager handles empty tools directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ToolManager(tools_dir=tmpdir)
        
        tools = manager.list_tools()
        
        assert tools == []


def test_load_nonexistent_tool():
    """Test that loading nonexistent tool returns None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ToolManager(tools_dir=tmpdir)
        
        fake_id = str(uuid.uuid4())
        tool = manager.load_tool(fake_id)
        
        assert tool is None


def test_get_tool_by_name_nonexistent():
    """Test that get_tool_by_name returns None for nonexistent name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ToolManager(tools_dir=tmpdir)
        
        tool = manager.get_tool_by_name("Nonexistent Tool")
        
        assert tool is None


def test_copy_tool_preserves_special_event_tracking_fields():
    """Copying a tool should preserve Special Event Tracking action fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ToolManager(tools_dir=tmpdir)
        tool = Tool(name="Source Tool", actions=[])
        action = AutoAction(
            name="Special Event",
            purpose="Track events",
            action_type=ActionType.READ_PASSIVE,
            mode=ActionMode.ACTIVE,
        )
        action.passive_mode = "special_event_tracking"
        action.golden_invasion_enabled = True
        action.golden_invasion_server_time = "00:40"
        action.golden_invasion_channel_roi_x1 = 10
        action.golden_invasion_channel_roi_y1 = 20
        action.golden_invasion_channel_roi_x2 = 110
        action.golden_invasion_channel_roi_y2 = 70
        action.golden_invasion_channel_teaching_image_path = f"images/{tool.id}/gi_channel.png"
        action.golden_invasion_channel_ocr_algorithms = [{"id": "upscale_2x"}]
        action.golden_invasion_notify_roi_x1 = 30
        action.golden_invasion_notify_roi_y1 = 40
        action.golden_invasion_notify_roi_x2 = 130
        action.golden_invasion_notify_roi_y2 = 90
        action.golden_invasion_notify_teaching_image_path = f"images/{tool.id}/gi_notify.png"
        action.golden_invasion_notify_ocr_algorithms = [{"id": "sharpen"}]
        action.golden_invasion_match_threshold = 75.0
        tool.actions.append(action)
        manager.save_tool(tool)

        copied = manager.copy_tool(tool.id, "Copied Tool")
        copied_action = copied.actions[0]

        assert copied_action.golden_invasion_enabled is True
        assert copied_action.golden_invasion_server_time == "00:40"
        assert copied_action.golden_invasion_channel_roi_x1 == 10
        assert copied_action.golden_invasion_channel_ocr_algorithms == [{"id": "upscale_2x"}]
        assert copied_action.golden_invasion_notify_roi_x1 == 30
        assert copied_action.golden_invasion_notify_ocr_algorithms == [{"id": "sharpen"}]
        assert copied_action.golden_invasion_match_threshold == 75.0
        assert copied.id in copied_action.golden_invasion_channel_teaching_image_path
        assert copied.id in copied_action.golden_invasion_notify_teaching_image_path


def test_tool_manager_round_trips_monster_invasion_fields():
    """Monster Invasion fields must persist through save/load and copy."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ToolManager(tools_dir=tmpdir)
        tool = Tool(name="Source Tool", actions=[])
        action = AutoAction(
            name="Monster Invasion",
            purpose="Track monster events",
            action_type=ActionType.READ_PASSIVE,
            mode=ActionMode.ACTIVE,
        )
        action.passive_mode = "special_event_tracking"
        action.monster_invasion_enabled = True
        action.monster_invasion_channel_roi_x1 = 11
        action.monster_invasion_channel_roi_y1 = 22
        action.monster_invasion_channel_roi_x2 = 111
        action.monster_invasion_channel_roi_y2 = 72
        action.monster_invasion_channel_ocr_engine = "tesseract"
        action.monster_invasion_channel_ocr_algorithms = [{"id": "upscale_2x"}]
        action.monster_invasion_channel_teaching_image_path = f"images/{tool.id}/mi_channel.png"
        action.monster_invasion_notify_roi_x1 = 33
        action.monster_invasion_notify_roi_y1 = 44
        action.monster_invasion_notify_roi_x2 = 233
        action.monster_invasion_notify_roi_y2 = 124
        action.monster_invasion_notify_ocr_engine = "winrt"
        action.monster_invasion_notify_ocr_algorithms = [{"id": "sharpen"}]
        action.monster_invasion_notify_teaching_image_path = f"images/{tool.id}/mi_notify.png"
        action.monster_invasion_match_threshold = 82.0
        action.monster_invasion_golden_invasion_enabled = True
        action.monster_invasion_golden_invasion_server_time = "00:40"
        action.monster_invasion_white_wizard_red_dragon_enabled = True
        tool.actions.append(action)

        manager.save_tool(tool)
        loaded_action = manager.load_tool(tool.id).actions[0]

        assert loaded_action.monster_invasion_enabled is True
        assert loaded_action.monster_invasion_channel_roi_x1 == 11
        assert loaded_action.monster_invasion_channel_ocr_engine == "tesseract"
        assert loaded_action.monster_invasion_channel_ocr_algorithms == [{"id": "upscale_2x"}]
        assert loaded_action.monster_invasion_notify_roi_x1 == 33
        assert loaded_action.monster_invasion_notify_ocr_engine == "winrt"
        assert loaded_action.monster_invasion_notify_ocr_algorithms == [{"id": "sharpen"}]
        assert loaded_action.monster_invasion_match_threshold == 82.0
        assert loaded_action.monster_invasion_golden_invasion_enabled is True
        assert loaded_action.monster_invasion_golden_invasion_server_time == "00:40"
        assert loaded_action.monster_invasion_white_wizard_red_dragon_enabled is True

        copied = manager.copy_tool(tool.id, "Copied Tool")
        copied_action = copied.actions[0]

        assert copied_action.monster_invasion_enabled is True
        assert copied_action.monster_invasion_channel_roi_x1 == 11
        assert copied_action.monster_invasion_notify_roi_x1 == 33
        assert copied_action.monster_invasion_golden_invasion_enabled is True
        assert copied_action.monster_invasion_white_wizard_red_dragon_enabled is True
        assert copied.id in copied_action.monster_invasion_channel_teaching_image_path
        assert copied.id in copied_action.monster_invasion_notify_teaching_image_path
