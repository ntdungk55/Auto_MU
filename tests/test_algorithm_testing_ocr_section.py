# Unit Tests for Algorithm Testing OCR Section (Updated logic)
# Logic mới: đọc từ screenshot, hỗ trợ Fixed ROI, 7 cột kết quả

import pytest
import os
import tempfile
import cv2
import numpy as np
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.ui.multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog, OCRWorkerThread
from src.ui.action_config_dialog import ActionConfigDialog
from src.ui.passive_read_settings_dialog import PassiveReadSettingsDialog
from src.logic.action_type import AutoAction, ActionType, ActionMode


@pytest.fixture(scope="session")
def app():
    """Create QApplication for testing."""
    if not QApplication.instance():
        return QApplication([])
    return QApplication.instance()


@pytest.fixture
def temp_image():
    """Create temporary test image."""
    img = np.ones((200, 400, 3), dtype=np.uint8) * 255
    cv2.putText(img, "TEST", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    cv2.imwrite(temp_file.name, img)
    temp_file.close()
    yield temp_file.name
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)


@pytest.fixture
def action(temp_image):
    """Create AutoAction with teaching image."""
    a = AutoAction(
        name="test_action",
        purpose="Test OCR",
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
    """Create dialog instance."""
    d = MultiImageAlgorithmTestingDialog(action=action, parent=None, tool_id="test_tool")
    yield d
    d.close()


class TestOCRSectionUIComponents:
    """Test OCR section UI components."""

    def test_ocr_ui_components_exist(self, dialog):
        """Test OCR UI components are initialized."""
        assert dialog.ocr_engine_combo is not None
        assert dialog.run_ocr_btn is not None
        assert dialog.ocr_progress_bar is not None
        assert dialog.ocr_results_table is not None

    def test_ocr_results_table_has_7_columns(self, dialog):
        """Test OCR results table has 7 columns with correct headers."""
        table = dialog.ocr_results_table
        assert table.columnCount() == 7
        expected = ["No.", "Engine", "Algorithms", "Screenshot", "Text", "Conf", "Time (ms)"]
        actual = [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())]
        assert actual == expected

    def test_available_ocr_engines_not_empty(self, dialog):
        """Test available OCR engines list is not empty."""
        assert len(dialog.available_ocr_engines) > 0
        assert "Auto" in dialog.available_ocr_engines

    def test_ocr_progress_bar_initially_hidden(self, dialog):
        """Test OCR progress bar is hidden initially."""
        assert not dialog.ocr_progress_bar.isVisible()


class TestFixedROI:
    """Test Fixed ROI logic."""

    def test_get_fixed_roi_returns_none_when_disabled(self, dialog):
        """Test _get_fixed_roi_from_action returns None when use_fixed_roi=False."""
        dialog.action.use_fixed_roi = False
        result = dialog._get_fixed_roi_from_action()
        assert result is None

    def test_get_fixed_roi_returns_tuple_when_enabled(self, dialog):
        """Test _get_fixed_roi_from_action returns (x,y,w,h) when enabled."""
        dialog.action.use_fixed_roi = True
        dialog.action.roi_x = 10
        dialog.action.roi_y = 20
        dialog.action.roi_w = 100
        dialog.action.roi_h = 50
        result = dialog._get_fixed_roi_from_action()
        assert result == (10, 20, 100, 50)

    def test_get_fixed_roi_returns_none_when_zero_size(self, dialog):
        """Test _get_fixed_roi_from_action returns None when w or h is 0."""
        dialog.action.use_fixed_roi = True
        dialog.action.roi_w = 0
        dialog.action.roi_h = 0
        result = dialog._get_fixed_roi_from_action()
        assert result is None

    def test_golden_invasion_channel_context_uses_channel_image_and_roi(self, app, action, temp_image):
        """Golden Invasion channel algorithm testing must use channel teaching context."""
        action.golden_invasion_channel_teaching_image_path = temp_image
        action.golden_invasion_channel_roi_x1 = 10
        action.golden_invasion_channel_roi_y1 = 20
        action.golden_invasion_channel_roi_x2 = 110
        action.golden_invasion_channel_roi_y2 = 70

        d = MultiImageAlgorithmTestingDialog(
            action=action,
            parent=None,
            tool_id="test_tool",
            algorithm_field="golden_invasion_channel_ocr_algorithms",
        )
        try:
            assert d.teaching_image_path == temp_image
            assert d._get_special_event_roi_from_action() == (10, 20, 100, 50)
        finally:
            d.close()

    def test_golden_invasion_notify_context_uses_notify_image_and_roi(self, app, action, temp_image):
        """Golden Invasion notify algorithm testing must use notify teaching context."""
        action.golden_invasion_notify_teaching_image_path = temp_image
        action.golden_invasion_notify_roi_x1 = 30
        action.golden_invasion_notify_roi_y1 = 40
        action.golden_invasion_notify_roi_x2 = 130
        action.golden_invasion_notify_roi_y2 = 90

        d = MultiImageAlgorithmTestingDialog(
            action=action,
            parent=None,
            tool_id="test_tool",
            algorithm_field="golden_invasion_notify_ocr_algorithms",
        )
        try:
            assert d.teaching_image_path == temp_image
            assert d._get_special_event_roi_from_action() == (30, 40, 100, 50)
        finally:
            d.close()

    def test_monster_invasion_channel_context_uses_channel_image_and_roi(self, app, action, temp_image):
        """Monster Invasion channel algorithm testing must use channel teaching context."""
        action.monster_invasion_channel_teaching_image_path = temp_image
        action.monster_invasion_channel_roi_x1 = 12
        action.monster_invasion_channel_roi_y1 = 22
        action.monster_invasion_channel_roi_x2 = 112
        action.monster_invasion_channel_roi_y2 = 72

        d = MultiImageAlgorithmTestingDialog(
            action=action,
            parent=None,
            tool_id="test_tool",
            algorithm_field="monster_invasion_channel_ocr_algorithms",
        )
        try:
            assert d.teaching_image_path == temp_image
            assert d._get_special_event_roi_from_action() == (12, 22, 100, 50)
        finally:
            d.close()

    def test_monster_invasion_notify_context_uses_notify_image_and_roi(self, app, action, temp_image):
        """Monster Invasion notify algorithm testing must use notify teaching context."""
        action.monster_invasion_notify_teaching_image_path = temp_image
        action.monster_invasion_notify_roi_x1 = 32
        action.monster_invasion_notify_roi_y1 = 42
        action.monster_invasion_notify_roi_x2 = 132
        action.monster_invasion_notify_roi_y2 = 92

        d = MultiImageAlgorithmTestingDialog(
            action=action,
            parent=None,
            tool_id="test_tool",
            algorithm_field="monster_invasion_notify_ocr_algorithms",
        )
        try:
            assert d.teaching_image_path == temp_image
            assert d._get_special_event_roi_from_action() == (32, 42, 100, 50)
        finally:
            d.close()


class TestPassiveSpecialEventSettingsSave:
    """Test READ_PASSIVE settings propagation from ActionConfigDialog."""

    def test_passive_dialog_hides_standalone_golden_invasion_ui(self, app):
        action = AutoAction(
            name="passive",
            purpose="special events",
            action_type=ActionType.READ_PASSIVE,
            mode=ActionMode.ACTIVE,
        )
        action.passive_mode = "special_event_tracking"
        action.golden_invasion_enabled = True

        d = PassiveReadSettingsDialog(action=action, parent=None)
        try:
            assert not d.gi_checkbox.isVisible()
            assert not d.gi_settings_widget.isVisible()
            assert d.get_settings()["golden_invasion_enabled"] is False
        finally:
            d.close()


class TestPostOCRPatternMatching:
    """Test dialog-side post-OCR fuzzy matching with placeholders."""

    def test_placeholder_pattern_matches_by_static_chunks(self, dialog):
        dialog._post_ocr_ignore_vietnamese_diacritics = True
        lines = ["Sự kiặn Imperal Guardian s5 bắt đàu sau 3 phút nữa"]
        pattern = "Sự kiện {event_name} sẽ bắt đầu sau {minutes} phút nữa"

        match = dialog._match_post_ocr_pattern(
            lines,
            pattern,
            threshold=55.0,
            ignore_diacritics=True,
        )

        assert match is not None
        assert float(match.get("score", 0.0)) >= 55.0
        assert match.get("line") == lines[0]

    def test_placeholder_pattern_respects_order_of_static_chunks(self, dialog):
        dialog._post_ocr_ignore_vietnamese_diacritics = True
        lines = ["3 phút nữa sự kiện imperial guardian bắt đầu"]
        pattern = "Sự kiện {event_name} sẽ bắt đầu sau {minutes} phút nữa"

        match = dialog._match_post_ocr_pattern(
            lines,
            pattern,
            threshold=55.0,
            ignore_diacritics=True,
        )

        assert match is None

    def test_exact_brackets_require_exact_match(self, dialog):
        dialog._post_ocr_ignore_vietnamese_diacritics = True
        pattern = "Sự kiện {event_name} sẽ bắt đầu sau [3] phút nữa"

        matched = dialog._match_post_ocr_pattern(
            ["Sự kiện Imperial Guardian sẽ bắt đầu sau 3 phút nữa"],
            pattern,
            threshold=70.0,
            ignore_diacritics=True,
        )
        not_matched = dialog._match_post_ocr_pattern(
            ["Sự kiện Imperial Guardian sẽ bắt đầu sau 5 phút nữa"],
            pattern,
            threshold=70.0,
            ignore_diacritics=True,
        )

        assert matched is not None
        assert not_matched is None

    def test_exact_brackets_do_not_match_substring_tokens(self, dialog):
        dialog._post_ocr_ignore_vietnamese_diacritics = True
        pattern = "Sự kiện {event_name} sẽ bắt đầu sau [1] phút nữa"

        match = dialog._match_post_ocr_pattern(
            ["Sự kiện Rồng Đỏ tấn công sẽ bắt đầu sau 10 phút nữa"],
            pattern,
            threshold=70.0,
            ignore_diacritics=True,
        )

        assert match is None

    def test_different_event_state_text_does_not_match(self, dialog):
        dialog._post_ocr_ignore_vietnamese_diacritics = True
        pattern = "Su kien Imperial Guardian da bat dau"

        match = dialog._match_post_ocr_pattern(
            ["Sự kiện Impenial Guardian sẽ bất dàu sau 15 phút nữa"],
            pattern,
            threshold=70.0,
            ignore_diacritics=True,
        )

        assert match is None

    def test_post_ocr_score_is_capped_at_100(self, dialog):
        dialog._post_ocr_ignore_vietnamese_diacritics = True
        pattern = "Su kien Imperial Guardian da bat dau"

        match = dialog._match_post_ocr_pattern(
            ["Sự kien Imperial Guarcian đa bẳt đâu"],
            pattern,
            threshold=0.0,
            ignore_diacritics=True,
        )

        assert match is not None
        assert 0.0 <= float(match.get("score", 0.0) or 0.0) <= 100.0

    def test_action_config_copies_golden_invasion_settings(self, app):
        action = AutoAction(
            name="passive",
            purpose="special events",
            action_type=ActionType.READ_PASSIVE,
            mode=ActionMode.ACTIVE,
        )
        settings = {
            "passive_mode": "special_event_tracking",
            "passive_detect_timeout": 30.0,
            "passive_detect_threshold": 0.4,
            "passive_sample_every": 1,
            "passive_only_new_frame": True,
            "passive_cancel_old": False,
            "passive_keywords": "",
            "use_fixed_roi": False,
            "roi_x": 0,
            "roi_y": 0,
            "roi_w": 200,
            "roi_h": 100,
            "ocr_engine": "auto",
            "ocr_bright_on_dark": False,
            "ocr_upscale_enabled": True,
            "ocr_upscale_factor": 2.0,
            "ocr_enhance_contrast": True,
            "ocr_sharpen": True,
            "ocr_denoise": False,
            "gemini_enabled": False,
            "gemini_timeout": 10.0,
            "notification_enabled": False,
            "notification_filter_keywords": "",
            "notification_dedup_minutes": 1,
            "continue_on_timeout": True,
            "goto_step_enabled": False,
            "goto_step_index": 0,
            "image_path": None,
            "teaching_corner_x1": None,
            "teaching_corner_y1": None,
            "teaching_corner_x2": None,
            "teaching_corner_y2": None,
            "ocr_algorithms": [],
            "event_ocr_pattern": "",
            "event_match_threshold": 100.0,
            "event_ocr_engine": "auto",
            "imperial_guardian_enabled": False,
            "imperial_guardian_no_player_alert_delay": 10,
            "imperial_guardian_teaching_corner_x1": 0,
            "imperial_guardian_teaching_corner_y1": 0,
            "imperial_guardian_teaching_corner_x2": 0,
            "imperial_guardian_teaching_corner_y2": 0,
            "imperial_guardian_teaching_image_path": "",
            "imperial_guardian_ocr_engine": "auto",
            "imperial_guardian_match_threshold": 70.0,
            "imperial_guardian_ocr_algorithms": [],
            "golden_invasion_enabled": True,
            "golden_invasion_server_time": "00:40",
            "golden_invasion_channel_roi_x1": 10,
            "golden_invasion_channel_roi_y1": 20,
            "golden_invasion_channel_roi_x2": 110,
            "golden_invasion_channel_roi_y2": 70,
            "golden_invasion_channel_ocr_engine": "tesseract",
            "golden_invasion_channel_ocr_algorithms": [{"id": "upscale_2x"}],
            "golden_invasion_channel_teaching_image_path": "images/tool/gi_channel.png",
            "golden_invasion_notify_roi_x1": 30,
            "golden_invasion_notify_roi_y1": 40,
            "golden_invasion_notify_roi_x2": 130,
            "golden_invasion_notify_roi_y2": 90,
            "golden_invasion_notify_ocr_engine": "easyocr",
            "golden_invasion_notify_ocr_algorithms": [{"id": "sharpen"}],
            "golden_invasion_notify_teaching_image_path": "images/tool/gi_notify.png",
            "golden_invasion_match_threshold": 75.0,
            "monster_invasion_enabled": True,
            "monster_invasion_channel_roi_x1": 12,
            "monster_invasion_channel_roi_y1": 22,
            "monster_invasion_channel_roi_x2": 112,
            "monster_invasion_channel_roi_y2": 72,
            "monster_invasion_channel_ocr_engine": "tesseract",
            "monster_invasion_channel_ocr_algorithms": [{"id": "mi_channel"}],
            "monster_invasion_channel_teaching_image_path": "images/tool/mi_channel.png",
            "monster_invasion_notify_roi_x1": 32,
            "monster_invasion_notify_roi_y1": 42,
            "monster_invasion_notify_roi_x2": 132,
            "monster_invasion_notify_roi_y2": 92,
            "monster_invasion_notify_ocr_engine": "winrt",
            "monster_invasion_notify_ocr_algorithms": [{"id": "mi_notify"}],
            "monster_invasion_notify_teaching_image_path": "images/tool/mi_notify.png",
            "monster_invasion_match_threshold": 82.0,
            "monster_invasion_golden_invasion_enabled": True,
            "monster_invasion_golden_invasion_server_time": "00:40",
            "monster_invasion_white_wizard_red_dragon_enabled": True,
        }

        class FakePassiveDialog:
            def __init__(self, *args, **kwargs):
                pass

            def exec(self):
                return True

            def get_settings(self):
                return settings

        d = ActionConfigDialog(action=action)
        try:
            with patch("src.ui.passive_read_settings_dialog.PassiveReadSettingsDialog", FakePassiveDialog):
                d._open_action_settings()

            assert d.action.continue_on_timeout is True
            assert d.action.golden_invasion_enabled is True
            assert d.action.golden_invasion_server_time == "00:40"
            assert d.action.golden_invasion_channel_roi_x1 == 10
            assert d.action.golden_invasion_channel_ocr_engine == "tesseract"
            assert d.action.golden_invasion_channel_ocr_algorithms == [{"id": "upscale_2x"}]
            assert d.action.golden_invasion_channel_teaching_image_path == "images/tool/gi_channel.png"
            assert d.action.golden_invasion_notify_roi_x1 == 30
            assert d.action.golden_invasion_notify_ocr_engine == "easyocr"
            assert d.action.golden_invasion_notify_ocr_algorithms == [{"id": "sharpen"}]
            assert d.action.golden_invasion_notify_teaching_image_path == "images/tool/gi_notify.png"
            assert d.action.golden_invasion_match_threshold == 75.0
            assert d.action.monster_invasion_enabled is True
            assert d.action.monster_invasion_channel_roi_x1 == 12
            assert d.action.monster_invasion_channel_ocr_engine == "tesseract"
            assert d.action.monster_invasion_channel_ocr_algorithms == [{"id": "mi_channel"}]
            assert d.action.monster_invasion_channel_teaching_image_path == "images/tool/mi_channel.png"
            assert d.action.monster_invasion_notify_roi_x1 == 32
            assert d.action.monster_invasion_notify_ocr_engine == "winrt"
            assert d.action.monster_invasion_notify_ocr_algorithms == [{"id": "mi_notify"}]
            assert d.action.monster_invasion_notify_teaching_image_path == "images/tool/mi_notify.png"
            assert d.action.monster_invasion_match_threshold == 82.0
            assert d.action.monster_invasion_golden_invasion_enabled is True
            assert d.action.monster_invasion_golden_invasion_server_time == "00:40"
            assert d.action.monster_invasion_white_wizard_red_dragon_enabled is True
        finally:
            d.close()


class TestOCRResultsDisplay:
    """Test OCR results display with new 7-column format."""

    def test_add_ocr_result_row_adds_new_row(self, dialog):
        """Test _add_ocr_result_row adds a new row to table."""
        dialog._add_ocr_result_row("WinRT", "Upscale 2x", "capture1.png", "Hello", "N/A", 120.5)
        assert dialog.ocr_results_table.rowCount() == 1

    def test_add_ocr_result_row_correct_values(self, dialog):
        """Test _add_ocr_result_row sets correct values in all 7 columns."""
        dialog._add_ocr_result_row("WinRT", "Upscale, Contrast", "capture1.png", "Hello World", "N/A", 120.5)
        table = dialog.ocr_results_table
        assert table.item(0, 0).text() == "1"
        assert table.item(0, 1).text() == "Winrt"
        assert table.item(0, 2).text() == "Upscale, Contrast"
        assert table.item(0, 3).text() == "capture1.png"
        assert table.item(0, 4).text() == "Hello World"
        assert table.item(0, 5).text() == "N/A"
        assert table.item(0, 6).text() == "120.5"

    def test_add_ocr_result_row_truncates_long_text(self, dialog):
        """Test long text is truncated to 50 chars + '...'."""
        long_text = "A" * 100
        dialog._add_ocr_result_row("WinRT", "None", "capture.png", long_text, "N/A", 100.0)
        text_cell = dialog.ocr_results_table.item(0, 4).text()
        assert len(text_cell) == 53
        assert text_cell.endswith("...")

    def test_multiple_rows_accumulate(self, dialog):
        """Test multiple Run OCR calls add rows without replacing."""
        dialog._add_ocr_result_row("WinRT", "None", "cap1.png", "First", "N/A", 100.0)
        dialog._add_ocr_result_row("Tesseract", "Upscale", "cap2.png", "Second", "N/A", 200.0)
        assert dialog.ocr_results_table.rowCount() == 2
        assert dialog.ocr_results_table.item(0, 0).text() == "1"
        assert dialog.ocr_results_table.item(1, 0).text() == "2"

    def test_on_ocr_error_adds_error_row(self, dialog):
        """Test _on_ocr_error adds error row to table."""
        dialog._on_ocr_error("WinRT", "capture.png", "Engine not available")
        table = dialog.ocr_results_table
        assert table.rowCount() == 1
        assert "Error:" in table.item(0, 4).text()

    def test_on_ocr_completed_hides_progress(self, dialog):
        """Test _on_ocr_completed hides progress bar and re-enables button."""
        dialog.ocr_progress_bar.setVisible(True)
        dialog.run_ocr_btn.setEnabled(False)
        dialog._on_ocr_completed("WinRT", "cap.png", "Upscale", 100.0, "text", "N/A")
        assert not dialog.ocr_progress_bar.isVisible()
        assert dialog.run_ocr_btn.isEnabled()


class TestRunOCR:
    """Test _run_ocr method."""

    def test_run_ocr_without_selected_image(self, dialog):
        """Test _run_ocr shows message when no image selected."""
        dialog.captures_list.clearSelection()
        messages = []
        original = dialog._show_ocr_message
        dialog._show_ocr_message = lambda m: messages.append(m)
        dialog._run_ocr()
        dialog._show_ocr_message = original
        assert len(messages) == 1

    def test_run_ocr_passes_fixed_roi_to_thread(self, dialog, temp_image):
        """Test _run_ocr passes Fixed ROI to OCRWorkerThread."""
        dialog.action.use_fixed_roi = True
        dialog.action.roi_x = 10
        dialog.action.roi_y = 20
        dialog.action.roi_w = 100
        dialog.action.roi_h = 50

        dialog.temp_captures.append(temp_image)
        dialog._add_temp_capture_to_list(temp_image)
        dialog.captures_list.setCurrentRow(0)

        threads_created = []
        original = dialog._start_ocr_thread

        def capture_thread(image_path, engine_name, algorithms, fixed_roi, screenshot_name):
            threads_created.append({
                "image_path": image_path,
                "fixed_roi": fixed_roi,
                "screenshot_name": screenshot_name
            })

        dialog._start_ocr_thread = capture_thread
        dialog._run_ocr()
        dialog._start_ocr_thread = original

        assert len(threads_created) == 1
        assert threads_created[0]["fixed_roi"] == (10, 20, 100, 50)
        assert threads_created[0]["screenshot_name"] == os.path.basename(temp_image)

    def test_run_ocr_passes_none_roi_when_disabled(self, dialog, temp_image):
        """Test _run_ocr passes None for fixed_roi when disabled."""
        dialog.action.use_fixed_roi = False

        dialog.temp_captures.append(temp_image)
        dialog._add_temp_capture_to_list(temp_image)
        dialog.captures_list.setCurrentRow(0)

        threads_created = []

        def capture_thread(image_path, engine_name, algorithms, fixed_roi, screenshot_name):
            threads_created.append({"fixed_roi": fixed_roi})

        dialog._start_ocr_thread = capture_thread
        dialog._run_ocr()

        assert threads_created[0]["fixed_roi"] is None


class TestOCRWorkerThread:
    """Test OCRWorkerThread with new logic."""

    def test_worker_loads_screenshot_not_teaching(self, temp_image):
        """Test worker loads the screenshot image (not teaching image)."""
        worker = OCRWorkerThread(temp_image, "auto", [], None, "capture.png")
        assert worker.image_path == temp_image
        assert worker.screenshot_name == "capture.png"

    def test_worker_crops_image_with_valid_roi(self, temp_image):
        """Test worker crops image correctly with valid Fixed ROI."""
        img = cv2.imread(temp_image)
        h, w = img.shape[:2]
        roi = (0, 0, w // 2, h // 2)

        worker = OCRWorkerThread(temp_image, "auto", [], roi, "capture.png")

        completed_calls = []
        error_calls = []

        def on_completed(*args):
            completed_calls.append(args)

        def on_error(*args):
            error_calls.append(args)

        worker.ocr_completed.connect(on_completed)
        worker.ocr_error.connect(on_error)

        # Patch OCR engine
        import unittest.mock as mock
        with mock.patch("src.logic.system_executor.ocr_engine.OCRFactory") as mock_factory:
            mock_engine = mock.Mock()
            mock_engine.recognize.return_value = "cropped text"
            mock_factory.create.return_value = mock_engine
            worker.run()

        # Should succeed (no error)
        assert len(error_calls) == 0

    def test_worker_emits_error_for_invalid_roi(self, temp_image):
        """Test worker emits error when ROI is outside image bounds."""
        roi = (99999, 99999, 100, 100)  # Way outside image
        worker = OCRWorkerThread(temp_image, "auto", [], roi, "capture.png")

        error_calls = []
        worker.ocr_error.connect(lambda e, s, err: error_calls.append(err))
        worker.run()

        assert len(error_calls) == 1
        assert "outside image bounds" in error_calls[0]

    def test_worker_emits_error_for_invalid_image(self):
        """Test worker emits error for non-existent image."""
        worker = OCRWorkerThread("/nonexistent/path.png", "auto", [], None, "capture.png")

        error_calls = []
        worker.ocr_error.connect(lambda e, s, err: error_calls.append(err))
        worker.run()

        assert len(error_calls) == 1
        assert "Cannot load image" in error_calls[0]

    def test_worker_signal_includes_algo_names_and_screenshot(self, temp_image):
        """Test worker ocr_completed signal includes algo_names and screenshot_name."""
        algorithms = [
            {"name": "Upscale 2x", "config": {"upscale": 2.0}},
            {"name": "Sharpen", "config": {"sharpen": True}},
        ]
        worker = OCRWorkerThread(temp_image, "auto", algorithms, None, "my_capture.png")

        completed_calls = []
        worker.ocr_completed.connect(lambda *args: completed_calls.append(args))

        import unittest.mock as mock
        with mock.patch("src.logic.system_executor.ocr_engine.OCRFactory") as mock_factory:
            mock_engine = mock.Mock()
            mock_engine.recognize.return_value = "hello"
            mock_factory.create.return_value = mock_engine
            worker.run()

        assert len(completed_calls) == 1
        engine, ss_name, algo_names, time_ms, text, conf = completed_calls[0]
        assert ss_name == "my_capture.png"
        assert "Upscale 2x" in algo_names
        assert "Sharpen" in algo_names

    def test_worker_algo_names_none_when_no_algorithms(self, temp_image):
        """Test worker shows 'None' in algo_names when no algorithms configured."""
        worker = OCRWorkerThread(temp_image, "auto", [], None, "capture.png")

        completed_calls = []
        worker.ocr_completed.connect(lambda *args: completed_calls.append(args))

        import unittest.mock as mock
        with mock.patch("src.logic.system_executor.ocr_engine.OCRFactory") as mock_factory:
            mock_engine = mock.Mock()
            mock_engine.recognize.return_value = "text"
            mock_factory.create.return_value = mock_engine
            worker.run()

        assert len(completed_calls) == 1
        _, _, algo_names, _, _, _ = completed_calls[0]
        assert algo_names == "None"
