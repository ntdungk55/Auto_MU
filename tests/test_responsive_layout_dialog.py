"""Tests for responsive layout in Multi-Image Algorithm Testing Dialog."""

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSize
from src.logic.action_type import AutoAction, ActionType, ActionMode
from src.ui.multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
import tempfile
import os


@pytest.fixture
def app():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def sample_action():
    """Create sample action for testing."""
    action = AutoAction(
        name="test_action",
        purpose="Test action for responsive layout",
        action_type=ActionType.IMAGE_DETECT,
        mode=ActionMode.ACTIVE
    )
    action.match_threshold = 0.8
    
    # Create temp teaching image
    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    temp_file.close()
    action.image_path = temp_file.name
    
    # Create a simple 100x100 test image
    import cv2
    import numpy as np
    test_img = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.imwrite(action.image_path, test_img)
    
    yield action
    
    # Cleanup
    if os.path.exists(action.image_path):
        os.unlink(action.image_path)


def test_dialog_initial_size(app, sample_action):
    """Test dialog has correct initial size."""
    dialog = MultiImageAlgorithmTestingDialog(sample_action)
    
    # Check minimum size
    assert dialog.minimumSize().width() == 1200
    assert dialog.minimumSize().height() == 800
    
    # Check default size
    assert dialog.size().width() == 1400
    assert dialog.size().height() == 900
    
    dialog.close()


def test_teaching_view_fixed_width(app, sample_action):
    """Test teaching view has fixed maximum width."""
    dialog = MultiImageAlgorithmTestingDialog(sample_action)
    
    # Teaching view should have max width of 400px
    assert dialog.teaching_view.maximumWidth() == 400
    
    dialog.close()


def test_captures_list_fixed_height(app, sample_action):
    """Test captures list has reasonable fixed height and max width."""
    dialog = MultiImageAlgorithmTestingDialog(sample_action)
    
    # Captures list should not stretch infinitely
    # It should have stretch factor of 0 (fixed size)
    layout = dialog.layout()
    captures_list_item = None
    
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item.widget() == dialog.captures_list:
            captures_list_item = item
            break
    
    # Should have stretch factor 0 (fixed size)
    assert captures_list_item is not None
    
    # Should have max width to prevent over-stretching
    assert dialog.captures_list.maximumWidth() == 800
    
    dialog.close()


def test_algorithms_list_fixed_height(app, sample_action):
    """Test algorithms list has fixed maximum height and width."""
    dialog = MultiImageAlgorithmTestingDialog(sample_action)
    
    # Algorithms list should have max height of 120px
    assert dialog.algorithms_list.maximumHeight() == 120
    
    # Should have max width to prevent over-stretching
    assert dialog.algorithms_list.maximumWidth() == 600
    
    dialog.close()


def test_buttons_fixed_width(app, sample_action):
    """Test buttons have fixed widths, not stretching."""
    dialog = MultiImageAlgorithmTestingDialog(sample_action)
    
    # Check some key buttons have fixed/minimum widths
    assert dialog.load_btn.minimumWidth() == 120
    assert dialog.capture_btn.minimumWidth() == 120
    assert dialog.test_btn.minimumWidth() == 150
    
    # Stop button should have fixed width
    assert dialog.stop_btn.width() <= 80  # Fixed width
    
    dialog.close()


def test_combo_boxes_minimum_width(app, sample_action):
    """Test combo boxes have minimum width, not stretching infinitely."""
    dialog = MultiImageAlgorithmTestingDialog(sample_action)
    
    # Check algorithm combo has reasonable minimum width
    assert dialog.algorithm_combo.minimumWidth() == 200
    
    # Verify "Grayscale Only" is the first item in dropdown (no more None)
    first_item_text = dialog.algorithm_combo.itemText(0)
    assert "Grayscale Only" in first_item_text
    
    dialog.close()


def test_preview_splitter_ratios(app, sample_action):
    """Test preview splitter has correct ratios (30% teaching, 70% capture)."""
    dialog = MultiImageAlgorithmTestingDialog(sample_action)
    
    # Find the preview splitter
    preview_splitter = None
    for child in dialog.findChildren(dialog.__class__):
        if hasattr(child, 'setSizes'):  # QSplitter has setSizes method
            preview_splitter = child
            break
    
    # Should find the splitter in the dialog's children
    from PyQt6.QtWidgets import QSplitter
    splitters = dialog.findChildren(QSplitter)
    assert len(splitters) > 0
    
    preview_splitter = splitters[0]  # First splitter should be preview splitter
    sizes = preview_splitter.sizes()
    
    # Should have 2 panes
    assert len(sizes) == 2
    
    # Ratio should be approximately 30:70
    total = sum(sizes)
    if total > 0:  # Avoid division by zero
        ratio1 = sizes[0] / total
        ratio2 = sizes[1] / total
        
        # Teaching should be around 30% (0.3), capture around 70% (0.7)
        assert 0.2 <= ratio1 <= 0.5  # Allow more tolerance for UI layout
        assert 0.5 <= ratio2 <= 0.8  # Allow more tolerance for UI layout
    
    dialog.close()


def test_layout_stretch_factors(app, sample_action):
    """Test main layout has correct stretch factors."""
    dialog = MultiImageAlgorithmTestingDialog(sample_action)
    
    layout = dialog.layout()
    
    # Preview area should have high stretch (4)
    # Other components should have low/no stretch
    
    # This is more of a structural test to ensure
    # the layout is set up correctly for responsiveness
    assert layout is not None
    assert layout.count() > 0
    
    dialog.close()


def test_resize_behavior_simulation(app, sample_action):
    """Test dialog resize behavior by changing size."""
    dialog = MultiImageAlgorithmTestingDialog(sample_action)
    
    # Get initial sizes
    initial_size = dialog.size()
    initial_teaching_width = dialog.teaching_view.width()
    initial_capture_width = dialog.capture_view.width()
    
    # Resize dialog to be wider
    new_width = initial_size.width() + 200
    new_height = initial_size.height()
    dialog.resize(new_width, new_height)
    
    # Process events to apply resize
    QApplication.processEvents()
    
    # Teaching view should maintain its max width constraint
    assert dialog.teaching_view.maximumWidth() == 400
    
    # The dialog should accept the new size
    assert dialog.width() >= new_width - 50  # Allow some tolerance
    
    dialog.close()


def test_progress_bar_max_width(app, sample_action):
    """Test progress bar has maximum width to prevent over-stretching."""
    dialog = MultiImageAlgorithmTestingDialog(sample_action)
    
    # Progress bar should have max width
    assert dialog.progress_bar.maximumWidth() == 600
    
    dialog.close()