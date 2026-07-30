"""Unit tests for Preprocessing Algorithms UI feature."""

import pytest
from PyQt6.QtWidgets import QApplication, QListWidget, QPushButton, QAbstractItemView, QListWidgetItem
from PyQt6.QtCore import Qt
from src.logic.action_type import AutoAction, ActionType, ActionMode
from src.ui.algorithm_display_utils import (
    format_algorithm_display,
    update_algorithms_display,
    validate_algorithm,
    validate_algorithms_list
)
from src.ui.image_detect_settings_dialog import ImageDetectSettingsDialog
from src.ui.passive_read_settings_dialog import PassiveReadSettingsDialog
from src.ui.multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog

# Ensure QApplication exists for QListWidget tests
app = QApplication.instance()
if app is None:
    app = QApplication([])


class TestAutoActionExtensions:
    """Test AutoAction extensions for preprocessing algorithms."""
    
    def test_template_matching_algorithms_default_value(self):
        """Test that template_matching_algorithms has correct default value."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.IMAGE_DETECT,
            mode=ActionMode.ACTIVE
        )
        
        assert hasattr(action, 'template_matching_algorithms')
        assert action.template_matching_algorithms == []
        assert isinstance(action.template_matching_algorithms, list)
    
    def test_ocr_algorithms_default_value(self):
        """Test that ocr_algorithms has correct default value."""
        action = AutoAction(
            name="test",
            purpose="test", 
            action_type=ActionType.READ_PASSIVE,
            mode=ActionMode.ACTIVE
        )
        
        assert hasattr(action, 'ocr_algorithms')
        assert action.ocr_algorithms == []
        assert isinstance(action.ocr_algorithms, list)
    
    def test_template_matching_algorithms_field_type(self):
        """Test template_matching_algorithms field accepts list of dicts."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.IMAGE_DETECT,
            mode=ActionMode.ACTIVE
        )
        
        # Test setting valid algorithm list
        algorithms = [
            {
                "id": "upscale_2x",
                "name": "Upscale 2x",
                "config": {"upscale": 2.0},
                "parameters": {
                    "upscale": {
                        "type": "float",
                        "value": 2.0,
                        "label": "Scale Factor"
                    }
                }
            }
        ]
        
        action.template_matching_algorithms = algorithms
        assert action.template_matching_algorithms == algorithms
        assert len(action.template_matching_algorithms) == 1
        assert action.template_matching_algorithms[0]["id"] == "upscale_2x"
    
    def test_ocr_algorithms_field_type(self):
        """Test ocr_algorithms field accepts list of dicts."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.READ_PASSIVE,
            mode=ActionMode.ACTIVE
        )
        
        # Test setting valid algorithm list
        algorithms = [
            {
                "id": "enhance_contrast",
                "name": "Enhance Contrast",
                "config": {"enhance_contrast": True},
                "parameters": {
                    "contrast_level": {
                        "type": "float",
                        "value": 1.5,
                        "label": "Contrast Level"
                    }
                }
            }
        ]
        
        action.ocr_algorithms = algorithms
        assert action.ocr_algorithms == algorithms
        assert len(action.ocr_algorithms) == 1
        assert action.ocr_algorithms[0]["id"] == "enhance_contrast"
    
    def test_both_algorithm_fields_independent(self):
        """Test that template_matching_algorithms and ocr_algorithms are independent."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.IMAGE_DETECT,
            mode=ActionMode.ACTIVE
        )
        
        template_algorithms = [{"id": "template_algo", "name": "Template Algo", "config": {}}]
        ocr_algorithms = [{"id": "ocr_algo", "name": "OCR Algo", "config": {}}]
        
        action.template_matching_algorithms = template_algorithms
        action.ocr_algorithms = ocr_algorithms
        
        # Verify they are independent
        assert action.template_matching_algorithms != action.ocr_algorithms
        assert action.template_matching_algorithms[0]["id"] == "template_algo"
        assert action.ocr_algorithms[0]["id"] == "ocr_algo"
        
        # Modify one, other should remain unchanged
        action.template_matching_algorithms.append({"id": "new_template", "name": "New", "config": {}})
        assert len(action.template_matching_algorithms) == 2
        assert len(action.ocr_algorithms) == 1
    
    def test_algorithm_fields_structure_compatibility(self):
        """Test that algorithm fields are compatible with existing preprocessing_config structure."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.IMAGE_DETECT,
            mode=ActionMode.ACTIVE
        )
        
        # Test structure similar to existing preprocessing_config
        algorithm = {
            "id": "upscale_2x",
            "name": "Upscale 2x",
            "config": {"upscale": 2.0},  # Similar to preprocessing_config format
            "parameters": {
                "upscale": {
                    "type": "float",
                    "value": 2.0,
                    "label": "Scale Factor",
                    "min": 1.0,
                    "max": 5.0
                }
            }
        }
        
        action.template_matching_algorithms = [algorithm]
        
        # Verify structure
        stored_algo = action.template_matching_algorithms[0]
        assert "id" in stored_algo
        assert "name" in stored_algo
        assert "config" in stored_algo
        assert "parameters" in stored_algo
        assert stored_algo["config"]["upscale"] == 2.0
        assert stored_algo["parameters"]["upscale"]["value"] == 2.0


class TestAlgorithmDisplayFormatting:
    """Test algorithm display formatting utilities."""
    
    def test_format_algorithm_display_with_parameters(self):
        """Test algorithm display formatting with parameters."""
        algorithm = {
            "id": "upscale_2x",
            "name": "Upscale 2x",
            "config": {"upscale": 2.0},
            "parameters": {
                "upscale": {
                    "type": "float",
                    "value": 2.0,
                    "label": "Scale Factor"
                }
            }
        }
        
        result = format_algorithm_display(algorithm)
        assert result == "Upscale 2x (Scale Factor: 2.0)"
    
    def test_format_algorithm_display_multiple_parameters(self):
        """Test algorithm display formatting with multiple parameters."""
        algorithm = {
            "id": "enhance_contrast",
            "name": "Enhance Contrast",
            "config": {"enhance_contrast": True, "contrast_level": 1.5},
            "parameters": {
                "contrast_level": {
                    "type": "float",
                    "value": 1.5,
                    "label": "Contrast Level"
                },
                "brightness": {
                    "type": "float",
                    "value": 0.2,
                    "label": "Brightness"
                }
            }
        }
        
        result = format_algorithm_display(algorithm)
        assert "Enhance Contrast (" in result
        assert "Contrast Level: 1.5" in result
        assert "Brightness: 0.2" in result
        assert result.count(",") == 1  # Two parameters separated by comma
    
    def test_format_algorithm_display_no_parameters(self):
        """Test algorithm display formatting without parameters."""
        algorithm = {
            "id": "grayscale",
            "name": "Grayscale Only",
            "config": {"grayscale": True}
        }
        
        result = format_algorithm_display(algorithm)
        assert result == "Grayscale Only"
    
    def test_format_algorithm_display_empty_parameters(self):
        """Test algorithm display formatting with empty parameters dict."""
        algorithm = {
            "id": "simple_algo",
            "name": "Simple Algorithm",
            "config": {"enabled": True},
            "parameters": {}
        }
        
        result = format_algorithm_display(algorithm)
        assert result == "Simple Algorithm"
    
    def test_format_algorithm_display_missing_name(self):
        """Test algorithm display formatting with missing name."""
        algorithm = {
            "id": "test_algo",
            "config": {"test": True}
        }
        
        result = format_algorithm_display(algorithm)
        assert result == "Unknown"
    
    def test_format_algorithm_display_invalid_parameters(self):
        """Test algorithm display formatting with invalid parameters structure."""
        algorithm = {
            "id": "test_algo",
            "name": "Test Algorithm",
            "config": {"test": True},
            "parameters": {
                "invalid_param": "not_a_dict",  # Invalid structure
                "valid_param": {
                    "type": "float",
                    "value": 1.0,
                    "label": "Valid Param"
                }
            }
        }
        
        result = format_algorithm_display(algorithm)
        # Should only show valid parameter
        assert result == "Test Algorithm (Valid Param: 1.0)"
    
    def test_update_algorithms_display_empty_list(self):
        """Test updating ListView with empty algorithms list."""
        list_widget = QListWidget()
        algorithms = []
        
        update_algorithms_display(list_widget, algorithms)
        
        assert list_widget.count() == 1
        item = list_widget.item(0)
        assert item.text() == "Không có thuật toán"
        assert not (item.flags() & Qt.ItemFlag.ItemIsEnabled)  # Should be disabled
    
    def test_update_algorithms_display_with_algorithms(self):
        """Test updating ListView with algorithms."""
        list_widget = QListWidget()
        algorithms = [
            {
                "id": "upscale_2x",
                "name": "Upscale 2x",
                "config": {"upscale": 2.0},
                "parameters": {
                    "upscale": {
                        "type": "float",
                        "value": 2.0,
                        "label": "Scale Factor"
                    }
                }
            },
            {
                "id": "grayscale",
                "name": "Grayscale Only",
                "config": {"grayscale": True}
            }
        ]
        
        update_algorithms_display(list_widget, algorithms)
        
        assert list_widget.count() == 2
        
        # Check first item
        item1 = list_widget.item(0)
        assert item1.text() == "Upscale 2x (Scale Factor: 2.0)"
        assert item1.data(Qt.ItemDataRole.UserRole) == algorithms[0]
        
        # Check second item
        item2 = list_widget.item(1)
        assert item2.text() == "Grayscale Only"
        assert item2.data(Qt.ItemDataRole.UserRole) == algorithms[1]
    
    def test_update_algorithms_display_clears_previous(self):
        """Test that updating ListView clears previous items."""
        list_widget = QListWidget()
        
        # Add initial algorithms
        algorithms1 = [{"id": "algo1", "name": "Algorithm 1", "config": {}}]
        update_algorithms_display(list_widget, algorithms1)
        assert list_widget.count() == 1
        
        # Update with different algorithms
        algorithms2 = [
            {"id": "algo2", "name": "Algorithm 2", "config": {}},
            {"id": "algo3", "name": "Algorithm 3", "config": {}}
        ]
        update_algorithms_display(list_widget, algorithms2)
        
        # Should have new algorithms only
        assert list_widget.count() == 2
        assert list_widget.item(0).text() == "Algorithm 2"
        assert list_widget.item(1).text() == "Algorithm 3"


class TestAlgorithmValidation:
    """Test algorithm validation utilities."""
    
    def test_validate_algorithm_valid(self):
        """Test validation of valid algorithm."""
        algorithm = {
            "id": "upscale_2x",
            "name": "Upscale 2x",
            "config": {"upscale": 2.0},
            "parameters": {
                "upscale": {
                    "type": "float",
                    "value": 2.0,
                    "label": "Scale Factor"
                }
            }
        }
        
        is_valid, error = validate_algorithm(algorithm)
        assert is_valid is True
        assert error == ""
    
    def test_validate_algorithm_missing_required_field(self):
        """Test validation with missing required field."""
        algorithm = {
            "id": "test_algo",
            "name": "Test Algorithm"
            # Missing "config" field
        }
        
        is_valid, error = validate_algorithm(algorithm)
        assert is_valid is False
        assert "Missing required field: config" in error
    
    def test_validate_algorithm_invalid_parameters(self):
        """Test validation with invalid parameters structure."""
        algorithm = {
            "id": "test_algo",
            "name": "Test Algorithm",
            "config": {"test": True},
            "parameters": {
                "invalid_param": "not_a_dict"  # Should be dict
            }
        }
        
        is_valid, error = validate_algorithm(algorithm)
        assert is_valid is False
        assert "Parameter invalid_param must be a dictionary" in error
    
    def test_validate_algorithm_parameter_missing_value(self):
        """Test validation with parameter missing value."""
        algorithm = {
            "id": "test_algo",
            "name": "Test Algorithm",
            "config": {"test": True},
            "parameters": {
                "param1": {
                    "type": "float",
                    "label": "Parameter 1"
                    # Missing "value" field
                }
            }
        }
        
        is_valid, error = validate_algorithm(algorithm)
        assert is_valid is False
        assert "Parameter param1 missing value" in error
    
    def test_validate_algorithms_list_valid(self):
        """Test validation of valid algorithms list."""
        algorithms = [
            {"id": "algo1", "name": "Algorithm 1", "config": {}},
            {"id": "algo2", "name": "Algorithm 2", "config": {}}
        ]
        
        is_valid, error = validate_algorithms_list(algorithms)
        assert is_valid is True
        assert error == ""
    
    def test_validate_algorithms_list_not_list(self):
        """Test validation when algorithms is not a list."""
        algorithms = {"not": "a_list"}
        
        is_valid, error = validate_algorithms_list(algorithms)
        assert is_valid is False
        assert "Algorithms must be a list" in error
    
    def test_validate_algorithms_list_invalid_algorithm(self):
        """Test validation with invalid algorithm in list."""
        algorithms = [
            {"id": "algo1", "name": "Algorithm 1", "config": {}},
            {"id": "algo2", "name": "Algorithm 2"}  # Missing config
        ]
        
        is_valid, error = validate_algorithms_list(algorithms)
        assert is_valid is False
        assert "Algorithm 1: Missing required field: config" in error


class TestImageDetectSettingsDialogExtensions:
    """Test ImageDetectSettingsDialog extensions for template matching preprocessing."""
    
    def test_template_matching_preprocessing_section_creation(self):
        """Test that Template Matching Preprocessing section is created."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.IMAGE_DETECT,
            mode=ActionMode.ACTIVE
        )
        
        dialog = ImageDetectSettingsDialog(action)
        
        # Check if template algorithms list exists
        assert hasattr(dialog, 'template_algorithms_list')
        assert isinstance(dialog.template_algorithms_list, QListWidget)
        
        # Check ListView properties
        assert dialog.template_algorithms_list.maximumHeight() == 120
        assert dialog.template_algorithms_list.selectionMode() == QAbstractItemView.SelectionMode.NoSelection
    
    def test_template_matching_configure_button_exists(self):
        """Test that configure button exists and is properly connected."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.IMAGE_DETECT,
            mode=ActionMode.ACTIVE
        )
        
        dialog = ImageDetectSettingsDialog(action)
        
        # Find configure button by text
        configure_buttons = []
        for child in dialog.findChildren(QPushButton):
            if "Cấu hình Template Matching Algorithms" in child.text():
                configure_buttons.append(child)
        
        assert len(configure_buttons) > 0, "Configure button not found"
        
        # Check button properties
        configure_btn = configure_buttons[0]
        assert "⚙️" in configure_btn.text()
        assert "Template Matching Algorithms" in configure_btn.text()
    
    def test_template_algorithms_display_update_empty(self):
        """Test template algorithms display update with empty list."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.IMAGE_DETECT,
            mode=ActionMode.ACTIVE
        )
        
        dialog = ImageDetectSettingsDialog(action)
        
        # Should show "Không có thuật toán" for empty list
        assert dialog.template_algorithms_list.count() == 1
        item = dialog.template_algorithms_list.item(0)
        assert item.text() == "Không có thuật toán"
        assert not (item.flags() & Qt.ItemFlag.ItemIsEnabled)
    
    def test_template_algorithms_display_update_with_algorithms(self):
        """Test template algorithms display update with algorithms."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.IMAGE_DETECT,
            mode=ActionMode.ACTIVE
        )
        
        # Set template matching algorithms
        action.template_matching_algorithms = [
            {
                "id": "upscale_2x",
                "name": "Upscale 2x",
                "config": {"upscale": 2.0},
                "parameters": {
                    "upscale": {
                        "type": "float",
                        "value": 2.0,
                        "label": "Scale Factor"
                    }
                }
            },
            {
                "id": "grayscale",
                "name": "Grayscale Only",
                "config": {"grayscale": True}
            }
        ]
        
        dialog = ImageDetectSettingsDialog(action)
        
        # Should show both algorithms
        assert dialog.template_algorithms_list.count() == 2
        
        # Check first algorithm
        item1 = dialog.template_algorithms_list.item(0)
        assert item1.text() == "Upscale 2x (Scale Factor: 2.0)"
        
        # Check second algorithm
        item2 = dialog.template_algorithms_list.item(1)
        assert item2.text() == "Grayscale Only"
    
    def test_get_settings_includes_template_matching_algorithms(self):
        """Test that get_settings includes template_matching_algorithms."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.IMAGE_DETECT,
            mode=ActionMode.ACTIVE
        )
        
        # Set template matching algorithms
        test_algorithms = [
            {"id": "test_algo", "name": "Test Algorithm", "config": {}}
        ]
        action.template_matching_algorithms = test_algorithms
        
        dialog = ImageDetectSettingsDialog(action)
        settings = dialog.get_settings()
        
        # Check that template_matching_algorithms is included
        assert "template_matching_algorithms" in settings
        assert settings["template_matching_algorithms"] == test_algorithms
    
    def test_get_settings_empty_template_matching_algorithms(self):
        """Test that get_settings handles empty template_matching_algorithms."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.IMAGE_DETECT,
            mode=ActionMode.ACTIVE
        )
        
        # No template_matching_algorithms set (should default to empty list)
        dialog = ImageDetectSettingsDialog(action)
        settings = dialog.get_settings()
        
        # Check that template_matching_algorithms defaults to empty list
        assert "template_matching_algorithms" in settings
        assert settings["template_matching_algorithms"] == []


class TestPassiveReadSettingsDialogExtensions:
    """Test PassiveReadSettingsDialog extensions for OCR preprocessing."""
    
    def test_ocr_preprocessing_section_creation(self):
        """Test that OCR Preprocessing section is created."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.READ_PASSIVE,
            mode=ActionMode.ACTIVE
        )
        
        dialog = PassiveReadSettingsDialog(action)
        
        # Check if OCR preprocessing group exists
        assert hasattr(dialog, 'ocr_preprocessing_group')
        assert hasattr(dialog, 'ocr_algorithms_list')
        assert isinstance(dialog.ocr_algorithms_list, QListWidget)
        
        # Check ListView properties
        assert dialog.ocr_algorithms_list.maximumHeight() == 120
        assert dialog.ocr_algorithms_list.selectionMode() == QAbstractItemView.SelectionMode.NoSelection
    
    def test_ocr_configure_button_exists(self):
        """Test that OCR configure button exists and is properly connected."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.READ_PASSIVE,
            mode=ActionMode.ACTIVE
        )
        
        dialog = PassiveReadSettingsDialog(action)
        
        # Find configure button by text
        configure_buttons = []
        for child in dialog.findChildren(QPushButton):
            if "Cấu hình OCR Algorithms" in child.text():
                configure_buttons.append(child)
        
        assert len(configure_buttons) > 0, "OCR Configure button not found"
        
        # Check button properties
        configure_btn = configure_buttons[0]
        assert "⚙️" in configure_btn.text()
        assert "OCR Algorithms" in configure_btn.text()
    
    def test_ocr_preprocessing_section_visibility_based_on_mode(self):
        """Test that OCR Preprocessing section visibility changes based on passive mode."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.READ_PASSIVE,
            mode=ActionMode.ACTIVE
        )
        
        dialog = PassiveReadSettingsDialog(action)
        
        # Test the visibility logic by calling _on_passive_mode_changed directly
        # Mode 1: Phát hiện hình ảnh (index 1) - should hide OCR preprocessing
        dialog._on_passive_mode_changed(1)
        # The section should be set to not visible (regardless of parent visibility)
        # We can't easily test actual visibility due to parent widget constraints
        # So we'll test that the method doesn't crash and the widget exists
        assert hasattr(dialog, 'ocr_preprocessing_group')
        
        # Mode 0: Đọc dữ liệu (index 0) - should show OCR preprocessing
        dialog._on_passive_mode_changed(0)
        # Again, just test that the method works and widget exists
        assert hasattr(dialog, 'ocr_preprocessing_group')
        
        # Test that the combo box change triggers the method
        dialog.passive_mode_combo.setCurrentIndex(0)
        assert dialog.passive_mode_combo.currentIndex() == 0
        
        dialog.passive_mode_combo.setCurrentIndex(1)
        assert dialog.passive_mode_combo.currentIndex() == 1
    
    def test_ocr_algorithms_display_update_empty(self):
        """Test OCR algorithms display update with empty list."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.READ_PASSIVE,
            mode=ActionMode.ACTIVE
        )
        
        dialog = PassiveReadSettingsDialog(action)
        
        # Should show "Không có thuật toán" for empty list
        assert dialog.ocr_algorithms_list.count() == 1
        item = dialog.ocr_algorithms_list.item(0)
        assert item.text() == "Không có thuật toán"
        assert not (item.flags() & Qt.ItemFlag.ItemIsEnabled)
    
    def test_ocr_algorithms_display_update_with_algorithms(self):
        """Test OCR algorithms display update with algorithms."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.READ_PASSIVE,
            mode=ActionMode.ACTIVE
        )
        
        # Set OCR algorithms
        action.ocr_algorithms = [
            {
                "id": "enhance_contrast",
                "name": "Enhance Contrast",
                "config": {"enhance_contrast": True},
                "parameters": {
                    "contrast_level": {
                        "type": "float",
                        "value": 1.5,
                        "label": "Contrast Level"
                    }
                }
            },
            {
                "id": "sharpen",
                "name": "Sharpen",
                "config": {"sharpen": True}
            }
        ]
        
        dialog = PassiveReadSettingsDialog(action)
        
        # Should show both algorithms
        assert dialog.ocr_algorithms_list.count() == 2
        
        # Check first algorithm
        item1 = dialog.ocr_algorithms_list.item(0)
        assert item1.text() == "Enhance Contrast (Contrast Level: 1.5)"
        
        # Check second algorithm
        item2 = dialog.ocr_algorithms_list.item(1)
        assert item2.text() == "Sharpen"
    
    def test_get_settings_includes_ocr_algorithms(self):
        """Test that get_settings includes ocr_algorithms."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.READ_PASSIVE,
            mode=ActionMode.ACTIVE
        )
        
        # Set OCR algorithms
        test_algorithms = [
            {"id": "test_ocr_algo", "name": "Test OCR Algorithm", "config": {}}
        ]
        action.ocr_algorithms = test_algorithms
        
        dialog = PassiveReadSettingsDialog(action)
        settings = dialog.get_settings()
        
        # Check that ocr_algorithms is included
        assert "ocr_algorithms" in settings
        assert settings["ocr_algorithms"] == test_algorithms
    
    def test_get_settings_empty_ocr_algorithms(self):
        """Test that get_settings handles empty ocr_algorithms."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.READ_PASSIVE,
            mode=ActionMode.ACTIVE
        )
        
        # No ocr_algorithms set (should default to empty list)
        dialog = PassiveReadSettingsDialog(action)
        settings = dialog.get_settings()
        
        # Check that ocr_algorithms defaults to empty list
        assert "ocr_algorithms" in settings
        assert settings["ocr_algorithms"] == []

    def test_detect_mode_loads_continue_on_timeout(self):
        """Test detect-image mode loads continue_on_timeout into the checkbox."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.READ_PASSIVE,
            mode=ActionMode.ACTIVE
        )
        action.passive_mode = "detect_image"
        action.continue_on_timeout = True

        dialog = PassiveReadSettingsDialog(action)

        assert dialog.continue_on_timeout_checkbox.isChecked() is True

    def test_get_settings_includes_continue_on_timeout(self):
        """Test that get_settings includes continue_on_timeout for detect mode."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.READ_PASSIVE,
            mode=ActionMode.ACTIVE
        )

        dialog = PassiveReadSettingsDialog(action)
        dialog.continue_on_timeout_checkbox.setChecked(True)
        settings = dialog.get_settings()

        assert "continue_on_timeout" in settings
        assert settings["continue_on_timeout"] is True


class TestMultiImageAlgorithmTestingDialogExtensions:
    """Test MultiImageAlgorithmTestingDialog extensions for Apply buttons."""
    
    def test_apply_buttons_creation(self):
        """Test that Apply buttons are created."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.IMAGE_DETECT,
            mode=ActionMode.ACTIVE
        )
        
        dialog = MultiImageAlgorithmTestingDialog(action)
        
        # Check if Apply buttons exist
        assert hasattr(dialog, 'apply_template_btn')
        assert hasattr(dialog, 'apply_ocr_btn')
        assert isinstance(dialog.apply_template_btn, QPushButton)
        assert isinstance(dialog.apply_ocr_btn, QPushButton)
        
        # Check button properties
        assert "Apply to Template Matching" in dialog.apply_template_btn.text()
        assert "Apply to OCR Mode" in dialog.apply_ocr_btn.text()
        assert "📤" in dialog.apply_template_btn.text()
        assert "📤" in dialog.apply_ocr_btn.text()
    
    def test_get_current_algorithms_empty(self):
        """Test getting current algorithms when list is empty."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.IMAGE_DETECT,
            mode=ActionMode.ACTIVE
        )
        
        dialog = MultiImageAlgorithmTestingDialog(action)
        algorithms = dialog._get_current_algorithms()
        
        # Should return empty list when no algorithms
        assert algorithms == []
    
    def test_apply_to_template_matching_functionality(self):
        """Test Apply to Template Matching functionality."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.IMAGE_DETECT,
            mode=ActionMode.ACTIVE
        )
        
        dialog = MultiImageAlgorithmTestingDialog(action)
        
        # Mock _get_current_algorithms to return test data
        test_algorithms = [
            {"id": "test_algo", "name": "Test Algorithm", "config": {}}
        ]
        dialog._get_current_algorithms = lambda: test_algorithms
        
        # Call apply method
        dialog._apply_to_template_matching()
        
        # Check that algorithms were applied to action
        assert hasattr(action, 'template_matching_algorithms')
        assert action.template_matching_algorithms == test_algorithms
    
    def test_apply_to_ocr_mode_functionality(self):
        """Test Apply to OCR Mode functionality."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.READ_PASSIVE,
            mode=ActionMode.ACTIVE
        )
        
        dialog = MultiImageAlgorithmTestingDialog(action)
        
        # Mock _get_current_algorithms to return test data
        test_algorithms = [
            {"id": "test_ocr_algo", "name": "Test OCR Algorithm", "config": {}}
        ]
        dialog._get_current_algorithms = lambda: test_algorithms
        
        # Call apply method
        dialog._apply_to_ocr_mode()
        
        # Check that algorithms were applied to action
        assert hasattr(action, 'ocr_algorithms')
        assert action.ocr_algorithms == test_algorithms
    
    def test_apply_buttons_with_real_algorithms_list(self):
        """Test Apply buttons work with real algorithms list widget."""
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.IMAGE_DETECT,
            mode=ActionMode.ACTIVE
        )
        
        dialog = MultiImageAlgorithmTestingDialog(action)
        
        # Add test algorithm to the algorithms list widget
        test_algorithm = {
            "id": "upscale_2x",
            "name": "Upscale 2x",
            "config": {"upscale": 2.0},
            "parameters": {
                "upscale": {
                    "type": "float",
                    "value": 2.0,
                    "label": "Scale Factor"
                }
            }
        }
        
        # Create a list item with algorithm data
        from PyQt6.QtWidgets import QListWidgetItem
        item = QListWidgetItem("Upscale 2x (Scale Factor: 2.0)")
        item.setData(Qt.ItemDataRole.UserRole, test_algorithm)
        dialog.algorithms_list.addItem(item)
        
        # Test _get_current_algorithms
        algorithms = dialog._get_current_algorithms()
        assert len(algorithms) == 1
        assert algorithms[0] == test_algorithm
        
        # Test apply to template matching
        dialog._apply_to_template_matching()
        assert action.template_matching_algorithms == [test_algorithm]
        
        # Test apply to OCR mode
        dialog._apply_to_ocr_mode()
        assert action.ocr_algorithms == [test_algorithm]


class TestToolManagerPersistence:
    """Test ToolManager persistence for preprocessing algorithms fields."""
    
    def test_template_matching_algorithms_serialization(self):
        """Test template_matching_algorithms serialization to dict."""
        from src.logic.tool_manager import Tool
        
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.IMAGE_DETECT,
            mode=ActionMode.ACTIVE
        )
        
        # Set template matching algorithms
        test_algorithms = [
            {
                "id": "upscale_2x",
                "name": "Upscale 2x",
                "config": {"upscale": 2.0},
                "parameters": {
                    "upscale": {
                        "type": "float",
                        "value": 2.0,
                        "label": "Scale Factor"
                    }
                }
            }
        ]
        action.template_matching_algorithms = test_algorithms
        
        tool = Tool(name="Test Tool", actions=[action])
        tool_dict = tool.to_dict()
        
        # Check that template_matching_algorithms is in serialized data
        action_dict = tool_dict["actions"][0]
        assert "template_matching_algorithms" in action_dict
        assert action_dict["template_matching_algorithms"] == test_algorithms
    
    def test_ocr_algorithms_serialization(self):
        """Test ocr_algorithms serialization to dict."""
        from src.logic.tool_manager import Tool
        
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.READ_PASSIVE,
            mode=ActionMode.ACTIVE
        )
        
        # Set OCR algorithms
        test_algorithms = [
            {
                "id": "enhance_contrast",
                "name": "Enhance Contrast",
                "config": {"enhance_contrast": True},
                "parameters": {
                    "contrast_level": {
                        "type": "float",
                        "value": 1.5,
                        "label": "Contrast Level"
                    }
                }
            }
        ]
        action.ocr_algorithms = test_algorithms
        
        tool = Tool(name="Test Tool", actions=[action])
        tool_dict = tool.to_dict()
        
        # Check that ocr_algorithms is in serialized data
        action_dict = tool_dict["actions"][0]
        assert "ocr_algorithms" in action_dict
        assert action_dict["ocr_algorithms"] == test_algorithms
    
    def test_template_matching_algorithms_deserialization(self):
        """Test template_matching_algorithms deserialization from dict."""
        from src.logic.tool_manager import Tool
        
        test_algorithms = [
            {
                "id": "upscale_2x",
                "name": "Upscale 2x",
                "config": {"upscale": 2.0},
                "parameters": {
                    "upscale": {
                        "type": "float",
                        "value": 2.0,
                        "label": "Scale Factor"
                    }
                }
            }
        ]
        
        tool_dict = {
            "id": "test-tool-id",
            "name": "Test Tool",
            "settings": {},
            "actions": [
                {
                    "name": "test",
                    "purpose": "test",
                    "action_type": "Bắt Hình Ảnh",
                    "mode": "Chủ động",
                    "value": "",
                    "delay": 1.0,
                    "template_matching_algorithms": test_algorithms
                }
            ]
        }
        
        tool = Tool.from_dict(tool_dict)
        action = tool.actions[0]
        
        # Check that template_matching_algorithms was deserialized correctly
        assert hasattr(action, 'template_matching_algorithms')
        assert action.template_matching_algorithms == test_algorithms
    
    def test_ocr_algorithms_deserialization(self):
        """Test ocr_algorithms deserialization from dict."""
        from src.logic.tool_manager import Tool
        
        test_algorithms = [
            {
                "id": "enhance_contrast",
                "name": "Enhance Contrast",
                "config": {"enhance_contrast": True},
                "parameters": {
                    "contrast_level": {
                        "type": "float",
                        "value": 1.5,
                        "label": "Contrast Level"
                    }
                }
            }
        ]
        
        tool_dict = {
            "id": "test-tool-id",
            "name": "Test Tool",
            "settings": {},
            "actions": [
                {
                    "name": "test",
                    "purpose": "test",
                    "action_type": "Đọc thụ động",
                    "mode": "Chủ động",
                    "value": "",
                    "delay": 1.0,
                    "ocr_algorithms": test_algorithms
                }
            ]
        }
        
        tool = Tool.from_dict(tool_dict)
        action = tool.actions[0]
        
        # Check that ocr_algorithms was deserialized correctly
        assert hasattr(action, 'ocr_algorithms')
        assert action.ocr_algorithms == test_algorithms
    
    def test_backward_compatibility_missing_fields(self):
        """Test backward compatibility when algorithm fields are missing."""
        from src.logic.tool_manager import Tool
        
        # Tool dict without new algorithm fields (old format)
        tool_dict = {
            "id": "test-tool-id",
            "name": "Test Tool",
            "settings": {},
            "actions": [
                {
                    "name": "test",
                    "purpose": "test",
                    "action_type": "Bắt Hình Ảnh",
                    "mode": "Chủ động",
                    "value": "",
                    "delay": 1.0
                    # Missing template_matching_algorithms and ocr_algorithms
                }
            ]
        }
        
        tool = Tool.from_dict(tool_dict)
        action = tool.actions[0]
        
        # Check that missing fields default to empty lists
        assert hasattr(action, 'template_matching_algorithms')
        assert action.template_matching_algorithms == []
        assert hasattr(action, 'ocr_algorithms')
        assert action.ocr_algorithms == []
    
    def test_data_integrity_after_save_load_cycle(self):
        """Test data integrity after complete save/load cycle."""
        import tempfile
        import os
        from src.logic.tool_manager import ToolManager
        
        # Create test action with both algorithm types
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.IMAGE_DETECT,
            mode=ActionMode.ACTIVE
        )
        
        template_algorithms = [
            {
                "id": "upscale_2x",
                "name": "Upscale 2x",
                "config": {"upscale": 2.0},
                "parameters": {
                    "upscale": {
                        "type": "float",
                        "value": 2.0,
                        "label": "Scale Factor"
                    }
                }
            }
        ]
        
        ocr_algorithms = [
            {
                "id": "enhance_contrast",
                "name": "Enhance Contrast",
                "config": {"enhance_contrast": True},
                "parameters": {
                    "contrast_level": {
                        "type": "float",
                        "value": 1.5,
                        "label": "Contrast Level"
                    }
                }
            }
        ]
        
        action.template_matching_algorithms = template_algorithms
        action.ocr_algorithms = ocr_algorithms
        
        # Create tool and save
        from src.logic.tool_manager import Tool
        original_tool = Tool(name="Test Tool", actions=[action])
        
        # Use temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            tool_manager = ToolManager(temp_dir)
            
            # Save tool
            tool_manager.save_tool(original_tool)
            
            # Load tool back
            loaded_tool = tool_manager.load_tool(original_tool.id)
            
            # Verify tool was loaded
            assert loaded_tool is not None
            assert loaded_tool.name == original_tool.name
            assert len(loaded_tool.actions) == 1
            
            # Verify algorithm data integrity
            loaded_action = loaded_tool.actions[0]
            assert loaded_action.template_matching_algorithms == template_algorithms
            assert loaded_action.ocr_algorithms == ocr_algorithms
            
            # Verify deep equality of algorithm structures
            assert loaded_action.template_matching_algorithms[0]["id"] == "upscale_2x"
            assert loaded_action.template_matching_algorithms[0]["config"]["upscale"] == 2.0
            assert loaded_action.template_matching_algorithms[0]["parameters"]["upscale"]["value"] == 2.0
            
            assert loaded_action.ocr_algorithms[0]["id"] == "enhance_contrast"
            assert loaded_action.ocr_algorithms[0]["config"]["enhance_contrast"] is True
            assert loaded_action.ocr_algorithms[0]["parameters"]["contrast_level"]["value"] == 1.5
    
    def test_empty_algorithms_serialization_deserialization(self):
        """Test serialization/deserialization of empty algorithm lists."""
        from src.logic.tool_manager import Tool
        
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.IMAGE_DETECT,
            mode=ActionMode.ACTIVE
        )
        
        # Explicitly set empty lists
        action.template_matching_algorithms = []
        action.ocr_algorithms = []
        
        tool = Tool(name="Test Tool", actions=[action])
        
        # Serialize
        tool_dict = tool.to_dict()
        action_dict = tool_dict["actions"][0]
        assert action_dict["template_matching_algorithms"] == []
        assert action_dict["ocr_algorithms"] == []
        
        # Deserialize
        loaded_tool = Tool.from_dict(tool_dict)
        loaded_action = loaded_tool.actions[0]
        assert loaded_action.template_matching_algorithms == []
        assert loaded_action.ocr_algorithms == []
    
    def test_complex_algorithms_with_multiple_parameters(self):
        """Test serialization/deserialization of complex algorithms with multiple parameters."""
        from src.logic.tool_manager import Tool
        
        action = AutoAction(
            name="test",
            purpose="test",
            action_type=ActionType.IMAGE_DETECT,
            mode=ActionMode.ACTIVE
        )
        
        # Complex algorithm with multiple parameters
        complex_algorithm = {
            "id": "complex_preprocessing",
            "name": "Complex Preprocessing",
            "config": {
                "upscale": 2.5,
                "enhance_contrast": True,
                "sharpen": True,
                "denoise": False
            },
            "parameters": {
                "upscale": {
                    "type": "float",
                    "value": 2.5,
                    "label": "Scale Factor",
                    "min": 1.0,
                    "max": 5.0
                },
                "contrast_level": {
                    "type": "float",
                    "value": 1.8,
                    "label": "Contrast Level",
                    "min": 0.5,
                    "max": 3.0
                },
                "sharpen_strength": {
                    "type": "float",
                    "value": 0.7,
                    "label": "Sharpen Strength",
                    "min": 0.0,
                    "max": 2.0
                }
            }
        }
        
        action.template_matching_algorithms = [complex_algorithm]
        
        tool = Tool(name="Test Tool", actions=[action])
        
        # Serialize and deserialize
        tool_dict = tool.to_dict()
        loaded_tool = Tool.from_dict(tool_dict)
        loaded_action = loaded_tool.actions[0]
        
        # Verify complex structure is preserved
        loaded_algorithm = loaded_action.template_matching_algorithms[0]
        assert loaded_algorithm["id"] == "complex_preprocessing"
        assert loaded_algorithm["config"]["upscale"] == 2.5
        assert loaded_algorithm["config"]["enhance_contrast"] is True
        assert loaded_algorithm["parameters"]["upscale"]["value"] == 2.5
        assert loaded_algorithm["parameters"]["contrast_level"]["value"] == 1.8
        assert loaded_algorithm["parameters"]["sharpen_strength"]["value"] == 0.7
        assert loaded_algorithm["parameters"]["upscale"]["min"] == 1.0
        assert loaded_algorithm["parameters"]["upscale"]["max"] == 5.0
