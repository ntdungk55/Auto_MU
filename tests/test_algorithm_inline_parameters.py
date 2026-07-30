"""Unit tests for Algorithm Inline Parameters feature."""

import pytest
import os
import numpy as np
import cv2
from src.logic.action_type import AutoAction, ActionType, ActionMode
from PyQt6.QtWidgets import QApplication, QSpinBox, QDoubleSpinBox
from PyQt6.QtCore import Qt


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def sample_teaching_image(tmp_path):
    """Create a sample teaching image for testing."""
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.rectangle(img, (20, 40), (80, 60), (255, 255, 255), -1)
    
    image_path = tmp_path / "teaching.png"
    cv2.imwrite(str(image_path), img)
    return str(image_path)


@pytest.fixture
def action_with_teaching_image(sample_teaching_image):
    """Create action with teaching image and settings."""
    action = AutoAction(
        name="Test Action",
        purpose="Test",
        action_type=ActionType.IMAGE_DETECT,
        mode=ActionMode.PASSIVE
    )
    action.image_path = sample_teaching_image
    action.match_threshold = 0.80
    action.multiscale_enabled = True
    action.multiscale_min = 0.7
    action.multiscale_max = 1.3
    action.multiscale_step = 0.05
    action.window_capture_paths = []
    action.window_capture_results = {}
    action.preprocessing_algorithms = []
    return action


def test_threshold_algorithm_in_defaults(qapp):
    """Test thuật toán threshold có trong DEFAULT_ALGORITHMS."""
    from src.ui.multi_image_algorithm_testing_dialog import DEFAULT_ALGORITHMS
    
    threshold_algos = [algo for algo in DEFAULT_ALGORITHMS if "threshold" in algo["id"].lower()]
    assert len(threshold_algos) > 0, "Should have threshold algorithm"
    
    threshold_algo = threshold_algos[0]
    assert "threshold_value" in threshold_algo.get("parameters", {}), "Should have threshold_value parameter"
    assert "threshold_type" in threshold_algo.get("parameters", {}), "Should have threshold_type parameter"


def test_adaptive_threshold_algorithms_in_defaults(qapp):
    """Test adaptive threshold algorithms exist with full parameter set."""
    from src.ui.multi_image_algorithm_testing_dialog import DEFAULT_ALGORITHMS

    mean_algo = next((algo for algo in DEFAULT_ALGORITHMS if algo["id"] == "adaptive_threshold_mean"), None)
    gaussian_algo = next((algo for algo in DEFAULT_ALGORITHMS if algo["id"] == "adaptive_threshold_gaussian"), None)

    assert mean_algo is not None, "Should have adaptive threshold mean algorithm"
    assert gaussian_algo is not None, "Should have adaptive threshold gaussian algorithm"

    for algo in (mean_algo, gaussian_algo):
        params = algo.get("parameters", {})
        assert "adaptive_max_value" in params, "Should expose max value parameter"
        assert "adaptive_threshold_type" in params, "Should expose threshold type parameter"
        assert "adaptive_block_size" in params, "Should expose block size parameter"
        assert "adaptive_c" in params, "Should expose C parameter"


def test_dominant_color_merge_algorithm_in_defaults(qapp):
    """Test dominant color merge algorithm có trong DEFAULT_ALGORITHMS."""
    from src.ui.multi_image_algorithm_testing_dialog import DEFAULT_ALGORITHMS

    dominant_algos = [algo for algo in DEFAULT_ALGORITHMS if algo["id"] == "dominant_color_merge"]
    assert len(dominant_algos) == 1, "Should have dominant color merge algorithm"

    dominant_algo = dominant_algos[0]
    assert "quant_step" in dominant_algo.get("parameters", {}), "Should have quant_step parameter"
    assert "distance_threshold" in dominant_algo.get("parameters", {}), "Should have distance_threshold parameter"
    assert "max_colors" in dominant_algo.get("parameters", {}), "Should have max_colors parameter"


def test_simplified_algorithms_list(qapp):
    """Test chỉ có algorithms đơn lẻ, không có kết hợp."""
    from src.ui.multi_image_algorithm_testing_dialog import DEFAULT_ALGORITHMS
    
    # Check không có algorithms kết hợp
    combined_algos = [algo for algo in DEFAULT_ALGORITHMS if "+" in algo["name"]]
    assert len(combined_algos) == 0, "Should not have combined algorithms"
    
    # Check có các algorithms tên lõi
    algo_names = [algo["name"] for algo in DEFAULT_ALGORITHMS]
    assert "Grayscale Only" in str(algo_names)  # Check substring to handle emoji
    assert "Upscale 2x" in str(algo_names)
    assert "Enhance Contrast" in str(algo_names)
    assert "Sharpen" in str(algo_names)
    assert "Binary Threshold" in str(algo_names)
    assert "Adaptive Threshold (Mean)" in str(algo_names)
    assert "Adaptive Threshold (Gaussian)" in str(algo_names)
    assert "Dominant Color Merge" in str(algo_names)


def test_algorithm_parameter_definitions(qapp):
    """Test tất cả algorithms có parameter definitions đúng."""
    from src.ui.multi_image_algorithm_testing_dialog import DEFAULT_ALGORITHMS
    
    # Test Upscale algorithm
    upscale_algos = [algo for algo in DEFAULT_ALGORITHMS if "upscale" in algo["id"]]
    assert len(upscale_algos) > 0
    
    upscale_algo = upscale_algos[0]
    params = upscale_algo.get("parameters", {})
    if "upscale" in params:
        scale_param = params["upscale"]
        assert scale_param["min"] >= 1.0
        assert scale_param["max"] <= 5.0
        assert scale_param["default"] == 2.0


def test_add_algorithm_with_settings_button(qapp, action_with_teaching_image):
    """Test add algorithm có nút settings luôn hiển thị."""
    from src.ui.multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )
    
    # Test algorithm có parameters (Upscale 2x)
    dialog.algorithm_combo.setCurrentIndex(1)  # Upscale 2x
    dialog._add_algorithm()
    
    assert dialog.algorithms_list.count() == 1
    
    # Check list item có settings button và parameters
    item = dialog.algorithms_list.item(0)
    widget = dialog.algorithms_list.itemWidget(item)
    
    assert widget is not None
    assert hasattr(widget, 'settings_btn'), "Should have settings button"
    assert widget.settings_btn.isEnabled(), "Settings button should be enabled for algorithms with parameters"
    assert hasattr(widget, 'params_widget'), "Should have params widget"
    assert hasattr(widget, 'parameter_widgets'), "Should have parameter_widgets attribute"
    
    # Parameters should be hidden by default
    assert not widget.params_widget.isVisible(), "Parameters should be hidden by default"
    
    # Test algorithm không có parameters (Grayscale Only)
    dialog.algorithm_combo.setCurrentIndex(0)  # Grayscale Only
    dialog._add_algorithm()
    
    assert dialog.algorithms_list.count() == 2
    
    # Check algorithm không có parameters vẫn có nút settings và enabled
    item2 = dialog.algorithms_list.item(1)
    widget2 = dialog.algorithms_list.itemWidget(item2)
    
    assert widget2 is not None
    assert hasattr(widget2, 'settings_btn'), "Should have settings button even without parameters"
    assert widget2.settings_btn.isEnabled(), "Settings button should be enabled for all algorithms"


def test_parameter_widget_creation(qapp, action_with_teaching_image):
    """Test tạo parameter widgets đúng type."""
    from src.ui.multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )
    
    # Test integer parameter → QSpinBox
    int_param = {
        "name": "threshold_value",
        "type": "int",
        "min": 0,
        "max": 255,
        "default": 127,
        "step": 1
    }
    
    widget = dialog._create_parameter_widget(int_param, 127)
    assert isinstance(widget, QSpinBox)
    assert widget.minimum() == 0
    assert widget.maximum() == 255
    assert widget.value() == 127
    
    # Test float parameter → QDoubleSpinBox
    float_param = {
        "name": "upscale",
        "type": "float",
        "min": 1.0,
        "max": 5.0,
        "default": 2.0,
        "step": 0.1
    }
    
    widget = dialog._create_parameter_widget(float_param, 2.0)
    assert isinstance(widget, QDoubleSpinBox)
    assert widget.minimum() == 1.0
    assert widget.maximum() == 5.0
    assert widget.value() == 2.0


def test_parameter_value_change_updates_config(qapp, action_with_teaching_image):
    """Test thay đổi parameter value cập nhật config."""
    from src.ui.multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )
    
    # Add algorithm
    dialog.algorithm_combo.setCurrentIndex(1)  # Upscale 2x
    dialog._add_algorithm()
    
    # Get algorithm config
    item = dialog.algorithms_list.item(0)
    algo_data = item.data(Qt.ItemDataRole.UserRole)
    original_config = algo_data["config"].copy()
    
    # Simulate parameter change
    widget = dialog.algorithms_list.itemWidget(item)
    if hasattr(widget, 'parameter_widgets') and 'upscale' in widget.parameter_widgets:
        scale_widget = widget.parameter_widgets['upscale']
        scale_widget.setValue(3.0)
        
        # Manually trigger parameter change since signal might not fire in test
        dialog._on_parameter_changed(algo_data, 'upscale', 3.0)
        
        # Check config updated in the item data (after fix)
        updated_item_data = item.data(Qt.ItemDataRole.UserRole)
        assert updated_item_data["config"].get("upscale") == 3.0


def test_binary_threshold_preprocessing(qapp, action_with_teaching_image):
    """Test binary threshold preprocessing hoạt động đúng."""
    from src.ui.multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )
    
    # Test image
    img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    
    # Apply binary threshold
    config = {
        "binary_threshold": True,
        "threshold_value": 127,
        "threshold_type": 0  # THRESH_BINARY
    }
    
    result = dialog._apply_preprocessing(img, config)
    
    # Check result is binary (only 0 and 255 values)
    gray_result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
    unique_values = np.unique(gray_result)
    assert len(unique_values) <= 2, "Binary threshold should produce max 2 unique values"
    assert 0 in unique_values or 255 in unique_values, "Should contain 0 or 255"


def test_dominant_color_merge_preprocessing(qapp, action_with_teaching_image):
    """Test dominant color merge gom các màu gần nhau về màu chiếm ưu thế."""
    from src.ui.multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog

    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )

    img = np.zeros((4, 4, 3), dtype=np.uint8)
    img[:3, :, :] = (0, 248, 0)
    img[3, :, :] = (0, 240, 0)

    config = {
        "dominant_color_merge": True,
        "quant_step": 8,
        "distance_threshold": 12,
        "max_colors": 16,
    }

    result = dialog._apply_preprocessing(img, config)
    unique_colors = np.unique(result.reshape(-1, 3), axis=0)

    assert unique_colors.shape[0] == 1, "Close colors should be merged into one dominant color"
    assert np.array_equal(unique_colors[0], np.array([0, 248, 0], dtype=np.uint8))


def test_parameter_validation_limits(qapp, action_with_teaching_image):
    """Test parameter validation với min/max limits."""
    from src.ui.multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )
    
    # Test QSpinBox limits
    int_param = {
        "name": "test_param",
        "type": "int",
        "min": 10,
        "max": 50,
        "default": 25,
        "step": 1
    }
    
    widget = dialog._create_parameter_widget(int_param, 25)
    
    # Try to set value outside range
    widget.setValue(100)  # Above max
    assert widget.value() == 50, "Should clamp to maximum"
    
    widget.setValue(-10)  # Below min
    assert widget.value() == 10, "Should clamp to minimum"


def test_settings_button_toggle_visibility(qapp, action_with_teaching_image):
    """Test nút settings toggle visibility của parameters."""
    from src.ui.multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )
    
    # Show dialog để đảm bảo widgets được render
    dialog.show()
    qapp.processEvents()  # Process Qt events
    
    # Add algorithm có parameters
    dialog.algorithm_combo.setCurrentIndex(1)  # Upscale 2x
    dialog._add_algorithm()
    
    # Process events để đảm bảo item được render
    qapp.processEvents()
    
    item = dialog.algorithms_list.item(0)
    widget = dialog.algorithms_list.itemWidget(item)
    
    # Initially hidden
    assert not widget.params_widget.isVisible()
    
    # Click settings button to show
    widget.settings_btn.click()
    qapp.processEvents()  # Process click event
    assert widget.params_widget.isVisible()
    
    # Click again to hide
    widget.settings_btn.click()
    qapp.processEvents()  # Process click event
    assert not widget.params_widget.isVisible()
    
    # Clean up
    dialog.close()


def test_backward_compatibility_old_format(qapp, action_with_teaching_image):
    """Test backward compatibility với old algorithm format."""
    from src.ui.multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )
    
    # Old format algorithm (chỉ có config, không có parameters)
    old_algo = {
        "id": "old_upscale",
        "name": "Old Upscale",
        "config": {"upscale": 2.0}
        # Không có "parameters" key
    }
    
    # Should not crash when processing old format
    result = dialog._get_algorithm_parameters(old_algo)
    assert isinstance(result, dict), "Should return empty dict for old format"


def test_save_algorithm_parameters_to_action(qapp, action_with_teaching_image):
    """Test lưu algorithm parameters vào action."""
    from src.ui.multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )
    
    # Add algorithm với custom parameters
    dialog.algorithm_combo.setCurrentIndex(1)  # Upscale 2x
    dialog._add_algorithm()
    
    # Modify parameters
    item = dialog.algorithms_list.item(0)
    widget = dialog.algorithms_list.itemWidget(item)
    algo_data = item.data(Qt.ItemDataRole.UserRole)
    
    if hasattr(widget, 'parameter_widgets') and 'upscale' in widget.parameter_widgets:
        widget.parameter_widgets['upscale'].setValue(3.5)
        # Manually trigger parameter change since signal might not fire in test
        dialog._on_parameter_changed(algo_data, 'upscale', 3.5)
    
    # Save to action
    dialog._save_to_action()
    
    # Check action has algorithm with parameters
    saved_algos = action_with_teaching_image.preprocessing_algorithms
    assert len(saved_algos) == 1
    
    saved_algo = saved_algos[0]
    assert "config" in saved_algo
    assert saved_algo["config"].get("upscale") == 3.5


def test_parameter_change_triggers_preview_update(qapp, action_with_teaching_image, sample_teaching_image):
    """Test thay đổi parameter triggers preview update ngay lập tức."""
    from src.ui.multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )
    
    # Add a window capture for preview
    dialog._add_window_capture_for_test(sample_teaching_image)
    
    # Select the capture
    item = dialog.captures_list.item(0)
    dialog.captures_list.setCurrentItem(item)
    
    # Add algorithm
    dialog.algorithm_combo.setCurrentIndex(1)  # Upscale 2x
    dialog._add_algorithm()
    
    # Show parameters
    algo_item = dialog.algorithms_list.item(0)
    widget = dialog.algorithms_list.itemWidget(algo_item)
    widget.settings_btn.click()  # Show parameters
    
    # Mock the preview update method to track calls
    original_method = dialog._on_capture_selected
    update_count = 0
    
    def mock_update(item):
        nonlocal update_count
        update_count += 1
        original_method(item)
    
    dialog._on_capture_selected = mock_update
    
    # Change parameter should trigger preview update
    if hasattr(widget, 'parameter_widgets') and 'upscale' in widget.parameter_widgets:
        initial_count = update_count
        widget.parameter_widgets['upscale'].setValue(2.5)
        # Should have triggered preview update
        assert update_count > initial_count, "Parameter change should trigger preview update"


def test_test_with_custom_parameters(qapp, action_with_teaching_image, sample_teaching_image):
    """Test testing algorithms với custom parameters."""
    from src.ui.multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )
    
    # Add window capture
    dialog._add_window_capture_for_test(sample_teaching_image)
    
    # Add algorithm với custom parameters
    dialog.algorithm_combo.setCurrentIndex(1)  # Upscale 2x
    dialog._add_algorithm()
    
    # Modify parameters
    algo_item = dialog.algorithms_list.item(0)
    algo_data = algo_item.data(Qt.ItemDataRole.UserRole)
    algo_data["config"]["upscale"] = 3.0  # Custom value
    
    # Test single image với custom config
    score = dialog._test_single_image(sample_teaching_image, [algo_data])
    
    assert 0.0 <= score <= 1.0, "Should return valid score"
    # The actual score depends on image content, but should not crash


def test_adaptive_threshold_parameter_changes_update_config(qapp, action_with_teaching_image):
    """Test adaptive threshold parameter edits persist to algorithm config."""
    from src.ui.multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog

    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )

    adaptive_index = next(
        i for i in range(dialog.algorithm_combo.count())
        if dialog.algorithm_combo.itemData(i)["id"] == "adaptive_threshold_mean"
    )
    dialog.algorithm_combo.setCurrentIndex(adaptive_index)
    dialog._add_algorithm()

    item = dialog.algorithms_list.item(0)
    algo_data = item.data(Qt.ItemDataRole.UserRole)

    dialog._on_parameter_changed(algo_data, "adaptive_max_value", 200)
    dialog._on_parameter_changed(algo_data, "adaptive_threshold_type", 1)
    dialog._on_parameter_changed(algo_data, "adaptive_block_size", 19)
    dialog._on_parameter_changed(algo_data, "adaptive_c", -4)

    updated_item_data = item.data(Qt.ItemDataRole.UserRole)
    assert updated_item_data["config"].get("adaptive_threshold_mean") is True
    assert updated_item_data["config"].get("adaptive_max_value") == 200
    assert updated_item_data["config"].get("adaptive_threshold_type") == 1
    assert updated_item_data["config"].get("adaptive_block_size") == 19
    assert updated_item_data["config"].get("adaptive_c") == -4


def test_adaptive_threshold_preprocessing(qapp, action_with_teaching_image):
    """Test adaptive threshold preprocessing produces a binary result."""
    from src.ui.multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog

    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )

    gradient = np.tile(np.arange(0, 100, dtype=np.uint8), (100, 1))
    img = cv2.cvtColor(gradient, cv2.COLOR_GRAY2BGR)

    config = {
        "adaptive_threshold_gaussian": True,
        "adaptive_max_value": 255,
        "adaptive_threshold_type": 0,
        "adaptive_block_size": 18,
        "adaptive_c": 3,
    }

    result = dialog._apply_preprocessing(img, config)

    gray_result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
    unique_values = np.unique(gray_result)
    assert len(unique_values) <= 2, "Adaptive threshold should produce max 2 unique values"
    assert set(unique_values).issubset({0, 255}), "Adaptive threshold should produce only binary values"
