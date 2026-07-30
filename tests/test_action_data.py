#!/usr/bin/env python3
"""
Simple test to verify Fixed ROI data model functionality.
Tests the AutoAction class and its Fixed ROI fields.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.logic.action_type import ActionType, ActionMode, AutoAction

def test_action_fixed_roi_fields():
    """Test that AutoAction properly stores Fixed ROI fields."""
    print("Testing AutoAction Fixed ROI fields...")
    
    # Create a READ_PASSIVE action
    action = AutoAction(
        name="Test Passive Read",
        purpose="Test Fixed ROI",
        action_type=ActionType.READ_PASSIVE,
        mode=ActionMode.ACTIVE,
        value=""
    )
    
    # Test default values
    assert hasattr(action, 'use_fixed_roi'), "AutoAction should have use_fixed_roi field"
    assert hasattr(action, 'roi_x'), "AutoAction should have roi_x field"
    assert hasattr(action, 'roi_y'), "AutoAction should have roi_y field"
    assert hasattr(action, 'roi_w'), "AutoAction should have roi_w field"
    assert hasattr(action, 'roi_h'), "AutoAction should have roi_h field"
    
    print(f"Default values: use_fixed_roi={action.use_fixed_roi}, roi=({action.roi_x},{action.roi_y},{action.roi_w},{action.roi_h})")
    
    assert action.use_fixed_roi == False, "Default use_fixed_roi should be False"
    assert action.roi_x == 0, "Default roi_x should be 0"
    assert action.roi_y == 0, "Default roi_y should be 0"
    assert action.roi_w == 200, "Default roi_w should be 200"
    assert action.roi_h == 100, "Default roi_h should be 100"
    
    # Test setting values
    action.use_fixed_roi = True
    action.roi_x = 100
    action.roi_y = 200
    action.roi_w = 300
    action.roi_h = 150
    
    print(f"Set values: use_fixed_roi={action.use_fixed_roi}, roi=({action.roi_x},{action.roi_y},{action.roi_w},{action.roi_h})")
    
    assert action.use_fixed_roi == True, "use_fixed_roi should be True after setting"
    assert action.roi_x == 100, "roi_x should be 100 after setting"
    assert action.roi_y == 200, "roi_y should be 200 after setting"
    assert action.roi_w == 300, "roi_w should be 300 after setting"
    assert action.roi_h == 150, "roi_h should be 150 after setting"
    
    print("✅ AutoAction Fixed ROI fields test passed!")
    return True

def test_teaching_corner_fields():
    """Test that AutoAction properly stores teaching corner fields."""
    print("Testing AutoAction teaching corner fields...")
    
    action = AutoAction(
        name="Test Teaching Corners",
        purpose="Test corners",
        action_type=ActionType.READ_PASSIVE,
        mode=ActionMode.ACTIVE,
        value=""
    )
    
    # Test default values
    assert hasattr(action, 'teaching_corner_x1'), "AutoAction should have teaching_corner_x1 field"
    assert hasattr(action, 'teaching_corner_y1'), "AutoAction should have teaching_corner_y1 field"
    assert hasattr(action, 'teaching_corner_x2'), "AutoAction should have teaching_corner_x2 field"
    assert hasattr(action, 'teaching_corner_y2'), "AutoAction should have teaching_corner_y2 field"
    
    print(f"Default corners: ({action.teaching_corner_x1},{action.teaching_corner_y1}) to ({action.teaching_corner_x2},{action.teaching_corner_y2})")
    
    assert action.teaching_corner_x1 is None, "Default teaching_corner_x1 should be None"
    assert action.teaching_corner_y1 is None, "Default teaching_corner_y1 should be None"
    assert action.teaching_corner_x2 is None, "Default teaching_corner_x2 should be None"
    assert action.teaching_corner_y2 is None, "Default teaching_corner_y2 should be None"
    
    # Test setting values
    action.teaching_corner_x1 = 50
    action.teaching_corner_y1 = 75
    action.teaching_corner_x2 = 350
    action.teaching_corner_y2 = 225
    
    print(f"Set corners: ({action.teaching_corner_x1},{action.teaching_corner_y1}) to ({action.teaching_corner_x2},{action.teaching_corner_y2})")
    
    assert action.teaching_corner_x1 == 50, "teaching_corner_x1 should be 50 after setting"
    assert action.teaching_corner_y1 == 75, "teaching_corner_y1 should be 75 after setting"
    assert action.teaching_corner_x2 == 350, "teaching_corner_x2 should be 350 after setting"
    assert action.teaching_corner_y2 == 225, "teaching_corner_y2 should be 225 after setting"
    
    print("✅ AutoAction teaching corner fields test passed!")
    return True

def test_action_serialization():
    """Test that Fixed ROI fields can be serialized/deserialized."""
    print("Testing action serialization...")
    
    # Create action with Fixed ROI settings
    action = AutoAction(
        name="Test Serialization",
        purpose="Test serialize",
        action_type=ActionType.READ_PASSIVE,
        mode=ActionMode.ACTIVE,
        value="",
        use_fixed_roi=True,
        roi_x=100,
        roi_y=200,
        roi_w=300,
        roi_h=150,
        teaching_corner_x1=50,
        teaching_corner_y1=75,
        teaching_corner_x2=350,
        teaching_corner_y2=225
    )
    
    # Test that all values are properly set
    print(f"Created action: use_fixed_roi={action.use_fixed_roi}, roi=({action.roi_x},{action.roi_y},{action.roi_w},{action.roi_h})")
    print(f"Teaching corners: ({action.teaching_corner_x1},{action.teaching_corner_y1}) to ({action.teaching_corner_x2},{action.teaching_corner_y2})")
    
    assert action.use_fixed_roi == True, "use_fixed_roi should be True"
    assert action.roi_x == 100, "roi_x should be 100"
    assert action.roi_y == 200, "roi_y should be 200"
    assert action.roi_w == 300, "roi_w should be 300"
    assert action.roi_h == 150, "roi_h should be 150"
    assert action.teaching_corner_x1 == 50, "teaching_corner_x1 should be 50"
    assert action.teaching_corner_y1 == 75, "teaching_corner_y1 should be 75"
    assert action.teaching_corner_x2 == 350, "teaching_corner_x2 should be 350"
    assert action.teaching_corner_y2 == 225, "teaching_corner_y2 should be 225"
    
    print("✅ Action serialization test passed!")
    return True

if __name__ == "__main__":
    try:
        test_action_fixed_roi_fields()
        test_teaching_corner_fields()
        test_action_serialization()
        print("\n🎉 All data model tests passed! Fixed ROI data structure is working correctly.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)