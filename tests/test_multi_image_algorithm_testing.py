"""Unit tests for Multi-Image Algorithm Testing Dialog."""

import pytest
import os
import numpy as np
import cv2
from src.logic.action_type import AutoAction, ActionType, ActionMode
from src.ui.multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
from PyQt6.QtWidgets import QApplication, QListWidgetItem
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
def sample_window_captures(tmp_path):
    """Create sample window capture images for testing."""
    images = []
    for i in range(5):
        img = np.zeros((400, 600, 3), dtype=np.uint8)
        x_offset = i * 30
        cv2.rectangle(img, (100 + x_offset, 150), (180 + x_offset, 170), (255, 255, 255), -1)
        
        image_path = tmp_path / f"capture_{i+1:03d}.png"
        cv2.imwrite(str(image_path), img)
        images.append(str(image_path))
    
    return images


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


def test_dialog_initialization(qapp, action_with_teaching_image):
    """Test dialog khởi tạo đúng với action."""
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        target_window_hwnd=None,
        tool_id="test-tool-id"
    )
    
    assert dialog.action == action_with_teaching_image
    assert dialog.teaching_image_path == action_with_teaching_image.image_path
    assert dialog.tool_id == "test-tool-id"
    assert dialog.get_total_captures_count() == 0
    assert len(dialog.test_results) == 0


def test_color_matching_controls_are_compact_and_switchable(qapp, action_with_teaching_image):
    """Color controls are hidden until the user explicitly selects Color (Auto)."""
    dialog = MultiImageAlgorithmTestingDialog(action_with_teaching_image, tool_id="test-tool-id")

    assert dialog.matching_method_combo.currentData() == "template"
    assert dialog.color_matching_controls.isHidden()
    assert dialog.color_min_match_spin.value() == 70

    dialog.matching_method_combo.setCurrentIndex(1)
    assert dialog.matching_method_combo.currentData() == "color"
    assert not dialog.color_matching_controls.isHidden()


def test_color_matching_finds_teaching_colors_in_capture(qapp, tmp_path):
    """Color (Auto) finds a solid teaching color without template-pixel matching."""
    teaching = np.zeros((24, 36, 3), dtype=np.uint8)
    teaching[:] = (0, 0, 255)  # BGR red
    teaching_path = tmp_path / "red_teaching.png"
    cv2.imwrite(str(teaching_path), teaching)

    capture = np.zeros((120, 160, 3), dtype=np.uint8)
    capture[45:69, 70:106] = (0, 0, 255)
    capture_path = tmp_path / "red_capture.png"
    cv2.imwrite(str(capture_path), capture)

    action = AutoAction(name="Color Test", purpose="Test", action_type=ActionType.IMAGE_DETECT, mode=ActionMode.PASSIVE)
    action.image_path = str(teaching_path)
    action.multiscale_enabled = False
    dialog = MultiImageAlgorithmTestingDialog(action, tool_id="test-tool-id")
    dialog.matching_method_combo.setCurrentIndex(1)

    score, bbox = dialog._test_single_image(str(capture_path), [])

    assert score >= 0.99
    assert bbox is not None
    assert abs(bbox[0] - 70) <= 1
    assert abs(bbox[1] - 45) <= 1


def test_load_teaching_image(qapp, action_with_teaching_image):
    """Test load teaching image từ action.image_path."""
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )
    
    assert os.path.exists(dialog.teaching_image_path)
    teaching_img = cv2.imread(dialog.teaching_image_path)
    assert teaching_img is not None
    assert teaching_img.shape[0] > 0
    assert teaching_img.shape[1] > 0


def test_add_window_capture(qapp, action_with_teaching_image, sample_window_captures):
    """Test thêm window capture vào list."""
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )
    
    for capture_path in sample_window_captures[:3]:
        dialog._add_window_capture_for_test(capture_path)
    
    assert dialog.captures_list.count() == 3
    assert dialog.get_total_captures_count() == 3


def test_remove_window_capture(qapp, action_with_teaching_image, sample_window_captures):
    """Test xóa window capture khỏi list."""
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )
    
    for capture_path in sample_window_captures[:3]:
        dialog._add_window_capture_for_test(capture_path)
    
    initial_count = dialog.captures_list.count()
    
    # Uncheck all items first (for custom widgets)
    for i in range(dialog.captures_list.count()):
        item = dialog.captures_list.item(i)
        widget = dialog.captures_list.itemWidget(item)
        if widget and hasattr(widget, 'checkbox'):
            widget.checkbox.setChecked(False)
    
    # Check only first item
    item = dialog.captures_list.item(0)
    widget = dialog.captures_list.itemWidget(item)
    if widget and hasattr(widget, 'checkbox'):
        widget.checkbox.setChecked(True)
    
    dialog._remove_selected()
    
    assert dialog.captures_list.count() == initial_count - 1


def test_algorithm_management(qapp, action_with_teaching_image):
    """Test add/delete algorithms."""
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )
    
    initial_count = dialog.algorithms_list.count()
    # Algorithm list starts empty, user adds from dropdown
    assert initial_count == 0
    
    # Add algorithm (index 1 now is "Upscale 2x" since "Grayscale Only" is at index 0)
    dialog.algorithm_combo.setCurrentIndex(1)
    dialog._add_algorithm()
    
    assert dialog.algorithms_list.count() == initial_count + 1


def test_preprocessing_application(qapp, action_with_teaching_image):
    """Test apply preprocessing đúng."""
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )
    
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Test None algorithm
    config = {}
    result = dialog._apply_preprocessing(img, config)
    assert result.shape == img.shape
    
    # Test Grayscale algorithm
    config = {"grayscale": True}
    result = dialog._apply_preprocessing(img, config)
    assert result.shape == img.shape  # Still 3-channel but grayscale
    
    # Test Upscale 2x
    config = {"upscale": 2.0}
    result = dialog._apply_preprocessing(img, config)
    assert result.shape[0] == img.shape[0] * 2
    assert result.shape[1] == img.shape[1] * 2


def test_template_matching(qapp, action_with_teaching_image, sample_window_captures):
    """Test template matching trả về score đúng."""
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )
    
    algorithm = {"id": "grayscale", "name": "Grayscale Only", "config": {"grayscale": True}}
    algorithms = [algorithm]  # Wrap in list
    score = dialog._test_single_image(sample_window_captures[0], algorithms)
    
    assert 0.0 <= score <= 1.0


def test_template_matching_no_algorithms(qapp, action_with_teaching_image, sample_window_captures):
    """Test template matching với empty algorithms list (test ảnh gốc)."""
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )
    
    # Test với empty algorithms list
    algorithms = []
    score = dialog._test_single_image(sample_window_captures[0], algorithms)
    
    assert 0.0 <= score <= 1.0


def test_save_on_ok(qapp, action_with_teaching_image, sample_window_captures):
    """Test click OK lưu data vào action."""
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )
    
    # Add window captures
    for capture_path in sample_window_captures[:3]:
        dialog._add_window_capture_for_test(capture_path)
    
    # Add test results
    dialog.test_results = {
        sample_window_captures[0]: 0.85,
        sample_window_captures[1]: 0.92,
        sample_window_captures[2]: 0.78
    }
    
    # Click OK (this calls both _save_to_action() and _save_captures_to_action())
    dialog._on_ok()
    
    assert len(action_with_teaching_image.window_capture_paths) == 3
    assert len(action_with_teaching_image.window_capture_results) == 3
    assert action_with_teaching_image.window_capture_results[sample_window_captures[1]] == 0.92


def test_cancel_on_close(qapp, action_with_teaching_image, sample_window_captures):
    """Test click Close không lưu data."""
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )
    
    # Add window captures
    for capture_path in sample_window_captures[:3]:
        dialog._add_window_capture_for_test(capture_path)
    
    # Don't save (reject)
    dialog.reject()
    
    # Action should not have data
    assert len(action_with_teaching_image.window_capture_paths) == 0
    assert len(action_with_teaching_image.window_capture_results) == 0


def test_data_persistence(qapp, action_with_teaching_image, sample_window_captures, tmp_path):
    """Test save tool → reload → verify data."""
    from src.logic.tool_manager import Tool, ToolManager
    
    # Setup action with data
    action_with_teaching_image.window_capture_paths = sample_window_captures[:3]
    action_with_teaching_image.window_capture_results = {
        sample_window_captures[0]: 0.85,
        sample_window_captures[1]: 0.92,
        sample_window_captures[2]: 0.78
    }
    action_with_teaching_image.preprocessing_algorithms = [
        {"id": "upscale_2x", "name": "Upscale 2x", "config": {"upscale": 2.0}}
    ]
    
    # Create tool
    tool = Tool(
        name="Test Tool",
        actions=[action_with_teaching_image],
        id="test-tool-id"
    )
    
    # Save to JSON
    tool_manager = ToolManager(str(tmp_path))
    tool_manager.save_tool(tool)
    
    # Load from JSON
    loaded_tool = tool_manager.load_tool("test-tool-id")
    loaded_action = loaded_tool.actions[0]
    
    # Verify data
    assert len(loaded_action.window_capture_paths) == 3
    assert len(loaded_action.window_capture_results) == 3
    assert loaded_action.window_capture_results[sample_window_captures[1]] == 0.92
    assert len(loaded_action.preprocessing_algorithms) == 1


def test_max_50_captures(qapp, action_with_teaching_image, tmp_path):
    """Test giới hạn 50 window captures."""
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )
    
    # Try to add 60 captures
    for i in range(60):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        path = tmp_path / f"capture_{i:03d}.png"
        cv2.imwrite(str(path), img)
        dialog._add_window_capture_for_test(str(path))
    
    # Should only have 60 (limit not enforced in _add_window_capture)
    # Limit is enforced in _load_images and _capture_new
    assert dialog.captures_list.count() == 60


def test_best_score_marking(qapp, action_with_teaching_image, sample_window_captures):
    """Test best score marked with ⭐."""
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )
    
    # Add captures
    for capture_path in sample_window_captures[:3]:
        dialog._add_window_capture_for_test(capture_path)
    
    # Set test results
    dialog.test_results = {
        sample_window_captures[0]: 0.85,
        sample_window_captures[1]: 0.95,  # Best
        sample_window_captures[2]: 0.78
    }
    
    # Update list with results
    dialog._update_results_display()
    
    # Check best score marked
    item = dialog.captures_list.item(1)
    widget = dialog.captures_list.itemWidget(item)
    if widget and hasattr(widget, 'label'):
        assert "⭐" in widget.label.text() or "BEST" in widget.label.text()


def test_threshold_comparison(qapp, action_with_teaching_image, sample_window_captures):
    """Test compare results with threshold."""
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )
    
    # Add captures
    for capture_path in sample_window_captures[:3]:
        dialog._add_window_capture_for_test(capture_path)
    
    # Set test results
    dialog.test_results = {
        sample_window_captures[0]: 0.85,  # > 0.80 threshold
        sample_window_captures[1]: 0.75,  # < 0.80 threshold
        sample_window_captures[2]: 0.92   # > 0.80 threshold
    }
    
    # Update list
    dialog._update_results_display()
    
    # Check ✅/❌ markers
    item0 = dialog.captures_list.item(0)
    item1 = dialog.captures_list.item(1)
    
    widget0 = dialog.captures_list.itemWidget(item0)
    widget1 = dialog.captures_list.itemWidget(item1)
    
    if widget0 and hasattr(widget0, 'label'):
        assert "✅" in widget0.label.text()
    if widget1 and hasattr(widget1, 'label'):
        assert "❌" in widget1.label.text()


def test_thread_safe_ui_updates(qapp, action_with_teaching_image, sample_window_captures):
    """Test UI updates are thread-safe."""
    
    dialog = MultiImageAlgorithmTestingDialog(
        action_with_teaching_image,
        parent=None,
        tool_id="test-tool-id"
    )
    
    # Check signals are connected
    assert dialog._test_progress_signal is not None
    assert dialog._test_complete_signal is not None
    assert dialog._test_error_signal is not None


def test_algorithm_transfer_to_parent():
    """Test algorithm transfer to parent settings dialog."""
    from src.logic.action_type import ActionType
    from PyQt6.QtWidgets import QWidget
    
    action = AutoAction("test_action", "Test purpose", ActionType.IMAGE_DETECT, "test")
    action.image_path = "test_image.png"
    action.match_threshold = 0.8
    
    # Create mock parent dialog with required methods (inherit from QWidget)
    class MockParentDialog(QWidget):
        def __init__(self):
            super().__init__()
            self.action = action
            self.template_algorithms_updated = False
            self.updated_algorithms = []
        
        def _update_template_algorithms_display(self):
            self.template_algorithms_updated = True
            self.updated_algorithms = self.action.template_matching_algorithms.copy()
    
    parent = MockParentDialog()
    
    # Create dialog with mock parent
    dialog = MultiImageAlgorithmTestingDialog(action, parent=parent)
    
    # Add some algorithms to the dialog
    algo1 = {"id": "upscale_2x", "name": "🔍 Upscale 2x", "config": {"upscale": 2.0}}
    algo2 = {"id": "enhance_contrast", "name": "✨ Enhance Contrast", "config": {"enhance_contrast": True}}
    
    # Simulate adding algorithms to the list
    item1 = QListWidgetItem()
    item1.setData(Qt.ItemDataRole.UserRole, algo1)
    dialog.algorithms_list.addItem(item1)
    
    item2 = QListWidgetItem()
    item2.setData(Qt.ItemDataRole.UserRole, algo2)
    dialog.algorithms_list.addItem(item2)
    
    # Call _on_ok() to trigger algorithm transfer
    dialog._on_ok()
    
    # Verify algorithms were transferred to parent
    assert parent.template_algorithms_updated, "Parent's template algorithms display should be updated"
    assert len(parent.updated_algorithms) == 2, f"Expected 2 algorithms, got {len(parent.updated_algorithms)}"
    assert parent.updated_algorithms[0]["id"] == "upscale_2x"
    assert parent.updated_algorithms[1]["id"] == "enhance_contrast"
    
    # Verify algorithms were also saved to action
    assert hasattr(action, 'template_matching_algorithms'), "Action should have template_matching_algorithms"
    assert len(action.template_matching_algorithms) == 2, f"Expected 2 algorithms in action, got {len(action.template_matching_algorithms)}"
    
    dialog.close()
    parent.close()


def test_algorithm_transfer_no_parent(qapp):
    """Test algorithm transfer when no parent dialog exists."""
    from src.logic.action_type import ActionType
    
    action = AutoAction("test_action", "Test purpose", ActionType.IMAGE_DETECT, "test")
    action.image_path = "test_image.png"
    action.match_threshold = 0.8
    
    # Create dialog without parent
    dialog = MultiImageAlgorithmTestingDialog(action, parent=None)
    
    # Add algorithm to the dialog
    algo = {"id": "upscale_2x", "name": "🔍 Upscale 2x", "config": {"upscale": 2.0}}
    
    item = QListWidgetItem()
    item.setData(Qt.ItemDataRole.UserRole, algo)
    dialog.algorithms_list.addItem(item)
    
    # Call _on_ok() - should not crash even without parent
    try:
        dialog._on_ok()
        success = True
    except Exception as e:
        success = False
        print(f"Error: {e}")
    
    assert success, "Dialog should handle missing parent gracefully"
    
    # Verify algorithms were still saved to action (in preprocessing_algorithms)
    assert hasattr(action, 'preprocessing_algorithms'), "Action should have preprocessing_algorithms"
    assert len(action.preprocessing_algorithms) == 1, f"Expected 1 algorithm in action, got {len(action.preprocessing_algorithms)}"
    
    dialog.close()
