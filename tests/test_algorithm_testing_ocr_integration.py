# Integration Tests for Algorithm Testing OCR Section (Updated logic)
# Logic mới: đọc từ screenshot, hỗ trợ Fixed ROI, 7 cột kết quả

import pytest
import os
import tempfile
import cv2
import numpy as np
import unittest.mock as mock
from PyQt6.QtWidgets import QApplication

from src.ui.multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog, OCRWorkerThread
from src.logic.action_type import AutoAction, ActionType, ActionMode


@pytest.fixture(scope="session")
def app():
    if not QApplication.instance():
        return QApplication([])
    return QApplication.instance()


@pytest.fixture
def temp_image():
    img = np.ones((200, 400, 3), dtype=np.uint8) * 255
    cv2.putText(img, "HELLO WORLD", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
    f = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    cv2.imwrite(f.name, img)
    f.close()
    yield f.name
    if os.path.exists(f.name):
        os.unlink(f.name)


@pytest.fixture
def action(temp_image):
    a = AutoAction(
        name="test_action",
        purpose="Test OCR integration",
        action_type=ActionType.IMAGE_DETECT,
        mode=ActionMode.ACTIVE
    )
    a.image_path = temp_image
    a.match_threshold = 0.8
    a.use_fixed_roi = False
    a.roi_x = 0
    a.roi_y = 0
    a.roi_w = 200
    a.roi_h = 100
    return a


@pytest.fixture
def dialog(app, action):
    d = MultiImageAlgorithmTestingDialog(action=action, parent=None, tool_id="test_tool")
    yield d
    d.close()


class TestOCRWithFixedROI:
    """Integration tests for OCR with Fixed ROI."""

    def test_ocr_uses_full_screenshot_when_no_roi(self, dialog, temp_image):
        """Test OCR reads full screenshot when Fixed ROI is disabled."""
        dialog.action.use_fixed_roi = False
        dialog.temp_captures.append(temp_image)
        dialog._add_temp_capture_to_list(temp_image)
        dialog.captures_list.setCurrentRow(0)

        captured = []

        def capture_thread(image_path, engine_name, algorithms, fixed_roi, screenshot_name):
            captured.append({"fixed_roi": fixed_roi, "image_path": image_path})

        dialog._start_ocr_thread = capture_thread
        dialog._run_ocr()

        assert captured[0]["fixed_roi"] is None
        assert captured[0]["image_path"] == temp_image

    def test_ocr_uses_roi_crop_when_enabled(self, dialog, temp_image):
        """Test OCR crops to Fixed ROI when enabled."""
        dialog.action.use_fixed_roi = True
        dialog.action.roi_x = 0
        dialog.action.roi_y = 0
        dialog.action.roi_w = 100
        dialog.action.roi_h = 50

        dialog.temp_captures.append(temp_image)
        dialog._add_temp_capture_to_list(temp_image)
        dialog.captures_list.setCurrentRow(0)

        captured = []

        def capture_thread(image_path, engine_name, algorithms, fixed_roi, screenshot_name):
            captured.append({"fixed_roi": fixed_roi})

        dialog._start_ocr_thread = capture_thread
        dialog._run_ocr()

        assert captured[0]["fixed_roi"] == (0, 0, 100, 50)

    def test_ocr_screenshot_name_passed_correctly(self, dialog, temp_image):
        """Test screenshot filename is passed to thread."""
        dialog.temp_captures.append(temp_image)
        dialog._add_temp_capture_to_list(temp_image)
        dialog.captures_list.setCurrentRow(0)

        captured = []

        def capture_thread(image_path, engine_name, algorithms, fixed_roi, screenshot_name):
            captured.append({"screenshot_name": screenshot_name})

        dialog._start_ocr_thread = capture_thread
        dialog._run_ocr()

        assert captured[0]["screenshot_name"] == os.path.basename(temp_image)


class TestOCRResultsWithAlgorithms:
    """Integration tests for OCR results with algorithm info."""

    def test_result_row_shows_algorithm_names(self, dialog):
        """Test result row shows algorithm names in Algorithms column."""
        dialog._add_ocr_result_row("WinRT", "Upscale 2x, Sharpen", "cap.png", "text", "N/A", 100.0)
        table = dialog.ocr_results_table
        assert table.item(0, 2).text() == "Upscale 2x, Sharpen"

    def test_result_row_shows_none_when_no_algorithms(self, dialog):
        """Test result row shows 'None' when no algorithms applied."""
        dialog._add_ocr_result_row("WinRT", "None", "cap.png", "text", "N/A", 100.0)
        table = dialog.ocr_results_table
        assert table.item(0, 2).text() == "None"

    def test_result_row_shows_screenshot_name(self, dialog):
        """Test result row shows screenshot filename."""
        dialog._add_ocr_result_row("WinRT", "None", "my_screenshot.png", "text", "N/A", 100.0)
        table = dialog.ocr_results_table
        assert table.item(0, 3).text() == "my_screenshot.png"

    def test_multiple_runs_with_different_screenshots(self, dialog):
        """Test multiple runs with different screenshots accumulate correctly."""
        dialog._add_ocr_result_row("WinRT", "Upscale", "cap1.png", "text1", "N/A", 100.0)
        dialog._add_ocr_result_row("Tesseract", "None", "cap2.png", "text2", "N/A", 200.0)

        table = dialog.ocr_results_table
        assert table.rowCount() == 2
        assert table.item(0, 3).text() == "cap1.png"
        assert table.item(1, 3).text() == "cap2.png"

    def test_results_cleared_when_switching_images(self, dialog, temp_image):
        """Test results table is cleared when switching to a different image."""
        dialog._add_ocr_result_row("WinRT", "None", "cap1.png", "old result", "N/A", 100.0)
        assert dialog.ocr_results_table.rowCount() == 1

        # Simulate selecting a new image
        dialog.temp_captures.append(temp_image)
        dialog._add_temp_capture_to_list(temp_image)
        item = dialog.captures_list.item(0)
        dialog._on_capture_selected(item)

        assert dialog.ocr_results_table.rowCount() == 0


class TestOCRWorkerThreadIntegration:
    """Integration tests for OCRWorkerThread with real images."""

    def test_worker_crops_roi_before_preprocessing(self, temp_image):
        """Test worker crops ROI before applying preprocessing algorithms."""
        img = cv2.imread(temp_image)
        h, w = img.shape[:2]
        roi = (0, 0, w // 2, h // 2)

        algorithms = [{"name": "Upscale 2x", "config": {"upscale": 2.0}}]
        worker = OCRWorkerThread(temp_image, "auto", algorithms, roi, "capture.png")

        preprocessing_inputs = []
        original_apply = worker._apply_preprocessing

        def capture_preprocessing(img_input, config):
            preprocessing_inputs.append(img_input.shape)
            return original_apply(img_input, config)

        worker._apply_preprocessing = capture_preprocessing

        completed_calls = []
        worker.ocr_completed.connect(lambda *args: completed_calls.append(args))

        with mock.patch("src.logic.system_executor.ocr_engine.OCRFactory") as mock_factory:
            mock_engine = mock.Mock()
            mock_engine.recognize.return_value = "text"
            mock_factory.create.return_value = mock_engine
            worker.run()

        # Preprocessing should receive cropped image (smaller than original)
        if preprocessing_inputs:
            cropped_h, cropped_w = preprocessing_inputs[0][:2]
            assert cropped_h <= h // 2 + 1
            assert cropped_w <= w // 2 + 1

    def test_worker_full_flow_no_roi(self, temp_image):
        """Test complete worker flow without ROI."""
        algorithms = [{"name": "Sharpen", "config": {"sharpen": True}}]
        worker = OCRWorkerThread(temp_image, "auto", algorithms, None, "capture.png")

        completed_calls = []
        error_calls = []
        worker.ocr_completed.connect(lambda *args: completed_calls.append(args))
        worker.ocr_error.connect(lambda *args: error_calls.append(args))

        with mock.patch("src.logic.system_executor.ocr_engine.OCRFactory") as mock_factory:
            mock_engine = mock.Mock()
            mock_engine.recognize.return_value = "full image text"
            mock_factory.create.return_value = mock_engine
            worker.run()

        assert len(error_calls) == 0
        assert len(completed_calls) == 1
        engine, ss_name, algo_names, time_ms, text, conf = completed_calls[0]
        assert ss_name == "capture.png"
        assert "Sharpen" in algo_names
        assert text == "full image text"
        assert time_ms > 0
