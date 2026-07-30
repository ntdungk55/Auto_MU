"""Unit tests for Tool Copy Feature."""

import os
import tempfile
import shutil
import uuid
from unittest import TestCase
from src.logic.tool_manager import ToolManager, Tool
from src.logic.action_type import AutoAction, ActionType, ActionMode


class TestToolCopyFeature(TestCase):
    """Test tool copy functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directories for testing
        self.test_dir = tempfile.mkdtemp()
        self.tools_dir = os.path.join(self.test_dir, "tools")
        self.images_dir = os.path.join(self.test_dir, "images")
        os.makedirs(self.tools_dir)
        os.makedirs(self.images_dir)
        
        # Create tool manager with test directory
        self.tool_manager = ToolManager(self.tools_dir, self.images_dir)
        
        # Create sample tool first to get ID
        self.sample_tool = Tool(
            name="Sample Tool",
            actions=[],  # Will add actions after getting ID
            loop_enabled=True,
            loop_count=5,
            notify_on_timeout=True
        )
        
        # Create sample action with tool ID in path
        self.sample_action = AutoAction(
            name="Test Action",
            purpose="Test purpose",
            action_type=ActionType.MOUSE_CLICK,
            mode=ActionMode.ACTIVE,
            value="test_value",
            image_path=f"images/{self.sample_tool.id}/test_image.png",
            delay=1.0
        )
        
        # Add action to tool
        self.sample_tool.actions = [self.sample_action]
        
        # Save sample tool
        self.tool_manager.save_tool(self.sample_tool)
        
        # Create sample teaching image
        self.sample_tool_images_dir = os.path.join(self.images_dir, self.sample_tool.id)
        os.makedirs(self.sample_tool_images_dir)
        self.sample_image_path = os.path.join(self.sample_tool_images_dir, "test_image.png")
        with open(self.sample_image_path, 'w') as f:
            f.write("fake image content")
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
    def test_copy_tool_success(self):
        """Test successful tool copy."""
        # Arrange
        new_name = "Copied Tool"
        
        # Act
        copied_tool = self.tool_manager.copy_tool(self.sample_tool.id, new_name)
        
        # Assert
        self.assertIsNotNone(copied_tool)
        self.assertEqual(copied_tool.name, new_name)
        self.assertNotEqual(copied_tool.id, self.sample_tool.id)
        self.assertEqual(len(copied_tool.actions), len(self.sample_tool.actions))
        self.assertEqual(copied_tool.loop_enabled, self.sample_tool.loop_enabled)
        self.assertEqual(copied_tool.loop_count, self.sample_tool.loop_count)
        self.assertEqual(copied_tool.notify_on_timeout, self.sample_tool.notify_on_timeout)
    
    def test_copy_tool_with_images(self):
        """Test tool copy includes teaching images."""
        # Arrange
        new_name = "Tool with Images"
        
        # Act
        copied_tool = self.tool_manager.copy_tool(self.sample_tool.id, new_name)
        
        # Assert
        copied_images_dir = os.path.join(self.images_dir, copied_tool.id)
        self.assertTrue(os.path.exists(copied_images_dir))
        
        copied_image_path = os.path.join(copied_images_dir, "test_image.png")
        self.assertTrue(os.path.exists(copied_image_path))
        
        # Verify image content is copied
        with open(copied_image_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "fake image content")
    
    def test_copy_tool_updates_image_paths(self):
        """Test that image paths are updated in copied tool."""
        # Arrange
        new_name = "Tool with Updated Paths"
        
        # Act
        copied_tool = self.tool_manager.copy_tool(self.sample_tool.id, new_name)
        
        # Assert
        copied_action = copied_tool.actions[0]
        expected_path = os.path.join("images", copied_tool.id, "test_image.png")
        self.assertIn(copied_tool.id, copied_action.image_path)
        self.assertNotIn(self.sample_tool.id, copied_action.image_path)
    
    def test_copy_tool_duplicate_name_fails(self):
        """Test that copying with duplicate name fails."""
        # Arrange
        existing_name = self.sample_tool.name
        
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            self.tool_manager.copy_tool(self.sample_tool.id, existing_name)
        
        self.assertIn("already exists", str(context.exception))
    
    def test_copy_tool_empty_name_fails(self):
        """Test that copying with empty name fails."""
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            self.tool_manager.copy_tool(self.sample_tool.id, "")
        
        self.assertIn("cannot be empty", str(context.exception))
    
    def test_copy_tool_whitespace_name_fails(self):
        """Test that copying with whitespace-only name fails."""
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            self.tool_manager.copy_tool(self.sample_tool.id, "   ")
        
        self.assertIn("cannot be empty", str(context.exception))
    
    def test_copy_nonexistent_tool_fails(self):
        """Test that copying non-existent tool fails."""
        # Arrange
        fake_id = str(uuid.uuid4())
        
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            self.tool_manager.copy_tool(fake_id, "New Tool")
        
        self.assertIn("not found", str(context.exception))
    
    def test_copy_tool_without_images(self):
        """Test copying tool that has no teaching images."""
        # Arrange
        # Remove images directory
        shutil.rmtree(self.sample_tool_images_dir)
        new_name = "Tool without Images"
        
        # Act
        copied_tool = self.tool_manager.copy_tool(self.sample_tool.id, new_name)
        
        # Assert
        self.assertIsNotNone(copied_tool)
        self.assertEqual(copied_tool.name, new_name)
        # Should not create images directory if original has none
        copied_images_dir = os.path.join(self.images_dir, copied_tool.id)
        self.assertFalse(os.path.exists(copied_images_dir))
    
    def test_copy_tool_preserves_all_settings(self):
        """Test that all tool settings are preserved in copy."""
        # Arrange
        complex_tool = Tool(
            name="Complex Tool",
            actions=[self.sample_action],
            loop_enabled=True,
            loop_mode="count",
            loop_count=10,
            loop_pre_delay_100ms=50,
            loop_post_delay_100ms=30,
            stop_on_timeout=False,
            restart_on_timeout=True,
            run_lock_mode=2,
            user_input_mode="pause",
            pause_duration=15,
            notify_on_timeout=True,
            block_input_enabled=True,
            block_input_duration=5.0
        )
        self.tool_manager.save_tool(complex_tool)
        
        # Act
        copied_tool = self.tool_manager.copy_tool(complex_tool.id, "Complex Copy")
        
        # Assert
        self.assertEqual(copied_tool.loop_mode, complex_tool.loop_mode)
        self.assertEqual(copied_tool.loop_pre_delay_100ms, complex_tool.loop_pre_delay_100ms)
        self.assertEqual(copied_tool.loop_post_delay_100ms, complex_tool.loop_post_delay_100ms)
        self.assertEqual(copied_tool.stop_on_timeout, complex_tool.stop_on_timeout)
        self.assertEqual(copied_tool.restart_on_timeout, complex_tool.restart_on_timeout)
        self.assertEqual(copied_tool.run_lock_mode, complex_tool.run_lock_mode)
        self.assertEqual(copied_tool.user_input_mode, complex_tool.user_input_mode)
        self.assertEqual(copied_tool.pause_duration, complex_tool.pause_duration)
        self.assertEqual(copied_tool.notify_on_timeout, complex_tool.notify_on_timeout)
        self.assertEqual(copied_tool.block_input_enabled, complex_tool.block_input_enabled)
        self.assertEqual(copied_tool.block_input_duration, complex_tool.block_input_duration)
    
    def test_copy_tool_independence(self):
        """Test that copied tool is independent from original."""
        # Arrange
        new_name = "Independent Copy"
        
        # Act
        copied_tool = self.tool_manager.copy_tool(self.sample_tool.id, new_name)
        
        # Modify original tool
        self.sample_tool.loop_count = 999
        self.tool_manager.save_tool(self.sample_tool)
        
        # Reload copied tool
        reloaded_copy = self.tool_manager.load_tool(copied_tool.id)
        
        # Assert
        self.assertNotEqual(reloaded_copy.loop_count, 999)
        self.assertEqual(reloaded_copy.loop_count, 5)  # Original value
    
    def test_validate_unique_name_success(self):
        """Test name validation for unique names."""
        # Act & Assert
        self.assertTrue(self.tool_manager.validate_unique_name("Unique Name"))
        self.assertTrue(self.tool_manager.validate_unique_name("Another Unique Name"))
    
    def test_validate_unique_name_duplicate(self):
        """Test name validation for duplicate names."""
        # Act & Assert
        self.assertFalse(self.tool_manager.validate_unique_name(self.sample_tool.name))
    
    def test_validate_unique_name_with_exclusion(self):
        """Test name validation with exclusion (for rename scenarios)."""
        # Act & Assert
        # Should return True when excluding the tool with same name
        self.assertTrue(
            self.tool_manager.validate_unique_name(
                self.sample_tool.name, 
                exclude_id=self.sample_tool.id
            )
        )
        
        # Should return False when not excluding
        self.assertFalse(
            self.tool_manager.validate_unique_name(self.sample_tool.name)
        )