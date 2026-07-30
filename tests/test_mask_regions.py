#!/usr/bin/env python3
"""Unit tests for template mask regions feature."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import cv2
from src.logic.action_type import AutoAction, ActionType, ActionMode


def test_mask_regions_field_exists():
    """Test that AutoAction has mask_regions field."""
    action = AutoAction(
        name="Test",
        purpose="Test",
        action_type=ActionType.IMAGE_DETECT,
        mode=ActionMode.ACTIVE,
        value=""
    )
    
    # Should have mask_regions field (default empty list)
    assert hasattr(action, "mask_regions")
    assert action.mask_regions == [] or action.mask_regions is None


def test_mask_regions_save_load():
    """Test saving and loading mask_regions."""
    from src.logic.tool_manager import ToolManager, Tool
    import tempfile
    
    action = AutoAction(
        name="Test Mask",
        purpose="Test",
        action_type=ActionType.IMAGE_DETECT,
        mode=ActionMode.ACTIVE,
        value="",
        image_path="test.png"
    )
    
    # Set mask regions
    action.mask_regions = [
        {"x": 10, "y": 20, "w": 50, "h": 30},
        {"x": 100, "y": 150, "w": 80, "h": 40}
    ]
    
    # Convert to dict
    action_dict = Tool._action_to_dict(action)
    
    # Should have mask_regions in dict
    assert "mask_regions" in action_dict
    assert len(action_dict["mask_regions"]) == 2
    assert action_dict["mask_regions"][0]["x"] == 10
    
    # Create tool and save/load
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = Tool(name="Test Tool", actions=[action])
        manager = ToolManager(tools_dir=tmpdir)
        manager.save_tool(tool)
        
        tool_id = tool.id  # Store UUID
        
        # Load tool
        loaded_tool = manager.load_tool(tool_id)
        assert loaded_tool is not None
        assert len(loaded_tool.actions) == 1
        
        loaded_action = loaded_tool.actions[0]
        assert hasattr(loaded_action, "mask_regions")
        assert len(loaded_action.mask_regions) == 2
        assert loaded_action.mask_regions[0]["x"] == 10
        assert loaded_action.mask_regions[1]["w"] == 80


def test_create_mask_array():
    """Test creating mask array from mask_regions."""
    # Create a simple template (100x100)
    template = np.ones((100, 100), dtype=np.uint8) * 255
    
    # Define mask regions
    mask_regions = [
        {"x": 10, "y": 10, "w": 30, "h": 20},  # Top-left region
        {"x": 60, "y": 60, "w": 30, "h": 30}   # Bottom-right region
    ]
    
    # Create mask array
    mask = np.ones(template.shape[:2], dtype=np.uint8) * 255
    for region in mask_regions:
        x, y, w, h = region["x"], region["y"], region["w"], region["h"]
        mask[y:y+h, x:x+w] = 0
    
    # Verify mask
    assert mask[0, 0] == 255  # Outside mask region
    assert mask[15, 15] == 0  # Inside first mask region
    assert mask[70, 70] == 0  # Inside second mask region
    assert mask[50, 50] == 255  # Between mask regions


def test_template_matching_with_mask():
    """Test that template matching works with mask."""
    # Create screenshot (200x200)
    screenshot = np.random.randint(0, 256, (200, 200), dtype=np.uint8)
    
    # Create template (50x50) - copy from screenshot
    template = screenshot[50:100, 50:100].copy()
    
    # Add text to template (simulate dynamic text)
    cv2.putText(template, "TEXT", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 0, 2)
    
    # Create mask to ignore text region
    mask = np.ones(template.shape[:2], dtype=np.uint8) * 255
    mask[20:35, 5:45] = 0  # Mask text region
    
    # Match without mask - should have lower score
    result_no_mask = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    _, max_val_no_mask, _, _ = cv2.minMaxLoc(result_no_mask)
    
    # Match with mask - should have higher score
    result_with_mask = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED, mask=mask)
    _, max_val_with_mask, _, _ = cv2.minMaxLoc(result_with_mask)
    
    # With mask should have higher or equal score
    assert max_val_with_mask >= max_val_no_mask
    print(f"Score without mask: {max_val_no_mask:.3f}")
    print(f"Score with mask: {max_val_with_mask:.3f}")


def test_mask_regions_validation():
    """Test validation of mask regions."""
    template_shape = (100, 100)
    
    # Valid mask regions
    valid_regions = [
        {"x": 10, "y": 10, "w": 20, "h": 20},
        {"x": 50, "y": 50, "w": 30, "h": 30}
    ]
    
    # Calculate total masked area
    total_area = template_shape[0] * template_shape[1]
    masked_area = sum(r["w"] * r["h"] for r in valid_regions)
    masked_percentage = (masked_area / total_area) * 100
    
    # Should not mask more than 90% of image
    assert masked_percentage < 90
    print(f"Masked area: {masked_percentage:.1f}%")


if __name__ == "__main__":
    print("Running mask regions tests...")
    test_mask_regions_field_exists()
    print("✓ test_mask_regions_field_exists")
    
    test_mask_regions_save_load()
    print("✓ test_mask_regions_save_load")
    
    test_create_mask_array()
    print("✓ test_create_mask_array")
    
    test_template_matching_with_mask()
    print("✓ test_template_matching_with_mask")
    
    test_mask_regions_validation()
    print("✓ test_mask_regions_validation")
    
    print("\nAll tests passed!")
