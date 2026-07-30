#!/usr/bin/env python3
"""
Test script to verify Fixed ROI functionality for READ_PASSIVE actions.
This script tests the saving and loading of Fixed ROI settings via PassiveReadSettingsDialog.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.logic.action_type import ActionType, ActionMode, AutoAction
from src.ui.passive_read_settings_dialog import PassiveReadSettingsDialog
from PyQt6.QtWidgets import QApplication


def test_fixed_roi_saving():
    """Test that Fixed ROI settings are properly saved and loaded via PassiveReadSettingsDialog."""
    # Create a READ_PASSIVE action
    action = AutoAction(
        name="Test Passive Read",
        purpose="Test Fixed ROI",
        action_type=ActionType.READ_PASSIVE,
        mode=ActionMode.ACTIVE,
        value=""
    )
    
    # Create QApplication (required for Qt widgets)
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Create PassiveReadSettingsDialog
    dialog = PassiveReadSettingsDialog(action=action)
    
    # Test 1: Check that Fixed ROI widgets exist
    assert hasattr(dialog, 'use_fixed_roi_checkbox'), "Fixed ROI checkbox should exist"
    assert hasattr(dialog, 'roi_x_spin'), "ROI X spinbox should exist"
    assert hasattr(dialog, 'roi_y_spin'), "ROI Y spinbox should exist"
    assert hasattr(dialog, 'roi_w_spin'), "ROI W spinbox should exist"
    assert hasattr(dialog, 'roi_h_spin'), "ROI H spinbox should exist"
    
    # Test 2: Set Fixed ROI checkbox to True and configure coordinates
    dialog.use_fixed_roi_checkbox.setChecked(True)
    dialog.roi_x_spin.setValue(100)
    dialog.roi_y_spin.setValue(200)
    dialog.roi_w_spin.setValue(300)
    dialog.roi_h_spin.setValue(150)
    
    # Test 3: Get settings and verify Fixed ROI settings are saved
    settings = dialog.get_settings()
    
    assert settings["use_fixed_roi"] == True, f"Expected use_fixed_roi=True, got {settings['use_fixed_roi']}"
    assert settings["roi_x"] == 100, f"Expected roi_x=100, got {settings['roi_x']}"
    assert settings["roi_y"] == 200, f"Expected roi_y=200, got {settings['roi_y']}"
    assert settings["roi_w"] == 300, f"Expected roi_w=300, got {settings['roi_w']}"
    assert settings["roi_h"] == 150, f"Expected roi_h=150, got {settings['roi_h']}"
    
    # Test 4: Create new dialog with action that has Fixed ROI settings and verify loading
    action2 = AutoAction(
        name="Test Passive Read 2",
        purpose="Test Fixed ROI Loading",
        action_type=ActionType.READ_PASSIVE,
        mode=ActionMode.ACTIVE,
        value=""
    )
    action2.use_fixed_roi = True
    action2.roi_x = 100
    action2.roi_y = 200
    action2.roi_w = 300
    action2.roi_h = 150
    
    dialog2 = PassiveReadSettingsDialog(action=action2)
    
    assert dialog2.use_fixed_roi_checkbox.isChecked() == True, "Fixed ROI checkbox should be checked after loading"
    assert dialog2.roi_x_spin.value() == 100, f"Expected loaded roi_x=100, got {dialog2.roi_x_spin.value()}"
    assert dialog2.roi_y_spin.value() == 200, f"Expected loaded roi_y=200, got {dialog2.roi_y_spin.value()}"
    assert dialog2.roi_w_spin.value() == 300, f"Expected loaded roi_w=300, got {dialog2.roi_w_spin.value()}"
    assert dialog2.roi_h_spin.value() == 150, f"Expected loaded roi_h=150, got {dialog2.roi_h_spin.value()}"
    
    # Test 5: Test unchecking the checkbox
    dialog2.use_fixed_roi_checkbox.setChecked(False)
    settings2 = dialog2.get_settings()
    
    assert settings2["use_fixed_roi"] == False, f"Expected use_fixed_roi=False after unchecking, got {settings2['use_fixed_roi']}"


def test_non_passive_action():
    """Test that AutoAction has default Fixed ROI values."""
    # Create a MOUSE_CLICK action
    action = AutoAction(
        name="Test Mouse Click",
        purpose="Test non-passive",
        action_type=ActionType.MOUSE_CLICK,
        mode=ActionMode.ACTIVE,
        value=""
    )
    
    # For non-READ_PASSIVE actions, Fixed ROI should have default values
    assert action.use_fixed_roi == False, "Default use_fixed_roi should be False"
    assert action.roi_x == 0, "Default roi_x should be 0"
    assert action.roi_y == 0, "Default roi_y should be 0"
    assert action.roi_w == 200, "Default roi_w should be 200"
    assert action.roi_h == 100, "Default roi_h should be 100"


if __name__ == "__main__":
    try:
        test_fixed_roi_saving()
        test_non_passive_action()
        print("\n🎉 All tests passed! Fixed ROI functionality is working correctly.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
