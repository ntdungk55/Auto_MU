"""Unit tests for Event Notify Checkbox Enable/Disable feature."""

import pytest
from PyQt6.QtWidgets import QApplication, QCheckBox, QTimeEdit
from PyQt6.QtCore import QTime, Qt
from PyQt6.QtTest import QTest

from src.logic.action_type import AutoAction
from src.ui.event_notify_settings_dialog import EventNotifySettingsDialog


class TestEventNotifyCheckbox:
    """Test checkbox enable/disable functionality in Event Notify dialog."""

    @pytest.fixture
    def app(self):
        """Create QApplication for testing."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    @pytest.fixture
    def action_with_old_format(self):
        """Create action with old string format times."""
        from src.logic.action_type import ActionType, ActionMode
        action = AutoAction(
            name="Test Action",
            purpose="Test",
            action_type=ActionType.EVENT_NOTIFY,
            mode=ActionMode.ACTIVE
        )
        action.event_notify_times = ["10:58", "09:10", "11:10"]
        action.event_prepare_start_s = 300
        action.event_prepare_end_s = 60
        action.delay = 2.0
        return action

    @pytest.fixture
    def action_with_new_format(self):
        """Create action with new dict format times."""
        from src.logic.action_type import ActionType, ActionMode
        action = AutoAction(
            name="Test Action",
            purpose="Test",
            action_type=ActionType.EVENT_NOTIFY,
            mode=ActionMode.ACTIVE
        )
        action.event_notify_times = [
            {"time": "10:58", "enabled": True},
            {"time": "09:10", "enabled": False},
            {"time": "11:10", "enabled": True}
        ]
        action.event_prepare_start_s = 300
        action.event_prepare_end_s = 60
        action.delay = 2.0
        return action

    def test_new_time_item_has_checkbox_checked_by_default(self, app, action_with_old_format):
        """Test that new time items have checkbox checked by default."""
        # Arrange
        dialog = EventNotifySettingsDialog(action_with_old_format)
        
        # Act
        dialog._add_time_item()
        
        # Assert
        assert dialog.times_list.count() == 4  # 3 existing + 1 new
        item = dialog.times_list.item(3)  # Last item
        widget = dialog.times_list.itemWidget(item)
        checkbox = widget.findChild(QCheckBox)
        
        assert checkbox is not None
        assert checkbox.isChecked() is True

    def test_checkbox_position_before_time_edit(self, app, action_with_old_format):
        """Test that checkbox is positioned before QTimeEdit."""
        # Arrange
        dialog = EventNotifySettingsDialog(action_with_old_format)
        
        # Act
        dialog._add_time_item()
        
        # Assert
        item = dialog.times_list.item(0)
        widget = dialog.times_list.itemWidget(item)
        layout = widget.layout()
        
        # First widget should be checkbox, second should be time edit
        checkbox = layout.itemAt(0).widget()
        time_edit = layout.itemAt(1).widget()
        
        assert isinstance(checkbox, QCheckBox)
        assert isinstance(time_edit, QTimeEdit)

    def test_unchecked_checkbox_grays_out_time_edit(self, app, action_with_old_format):
        """Test that unchecking checkbox grays out QTimeEdit."""
        # Arrange
        dialog = EventNotifySettingsDialog(action_with_old_format)
        dialog._add_time_item()
        
        item = dialog.times_list.item(0)
        widget = dialog.times_list.itemWidget(item)
        checkbox = widget.findChild(QCheckBox)
        time_edit = widget.findChild(QTimeEdit)
        
        # Act
        checkbox.setChecked(False)
        
        # Assert
        assert time_edit.isEnabled() is False

    def test_checked_checkbox_enables_time_edit(self, app, action_with_old_format):
        """Test that checking checkbox enables QTimeEdit."""
        # Arrange
        dialog = EventNotifySettingsDialog(action_with_old_format)
        dialog._add_time_item()
        
        item = dialog.times_list.item(0)
        widget = dialog.times_list.itemWidget(item)
        checkbox = widget.findChild(QCheckBox)
        time_edit = widget.findChild(QTimeEdit)
        
        # First uncheck, then check
        checkbox.setChecked(False)
        
        # Act
        checkbox.setChecked(True)
        
        # Assert
        assert time_edit.isEnabled() is True

    def test_load_old_format_converts_to_enabled_by_default(self, app, action_with_old_format):
        """Test that old string format is converted to enabled=true by default."""
        # Arrange & Act
        dialog = EventNotifySettingsDialog(action_with_old_format)
        
        # Assert
        assert dialog.times_list.count() == 3
        
        for i in range(3):
            item = dialog.times_list.item(i)
            widget = dialog.times_list.itemWidget(item)
            checkbox = widget.findChild(QCheckBox)
            assert checkbox.isChecked() is True

    def test_load_new_format_preserves_enabled_state(self, app, action_with_new_format):
        """Test that new dict format preserves enabled state."""
        # Arrange & Act
        dialog = EventNotifySettingsDialog(action_with_new_format)
        
        # Assert
        assert dialog.times_list.count() == 3
        
        # Check first item (enabled=True)
        item0 = dialog.times_list.item(0)
        widget0 = dialog.times_list.itemWidget(item0)
        checkbox0 = widget0.findChild(QCheckBox)
        time_edit0 = widget0.findChild(QTimeEdit)
        assert checkbox0.isChecked() is True
        assert time_edit0.isEnabled() is True
        
        # Check second item (enabled=False)
        item1 = dialog.times_list.item(1)
        widget1 = dialog.times_list.itemWidget(item1)
        checkbox1 = widget1.findChild(QCheckBox)
        time_edit1 = widget1.findChild(QTimeEdit)
        assert checkbox1.isChecked() is False
        assert time_edit1.isEnabled() is False
        
        # Check third item (enabled=True)
        item2 = dialog.times_list.item(2)
        widget2 = dialog.times_list.itemWidget(item2)
        checkbox2 = widget2.findChild(QCheckBox)
        time_edit2 = widget2.findChild(QTimeEdit)
        assert checkbox2.isChecked() is True
        assert time_edit2.isEnabled() is True

    def test_get_settings_returns_dict_format_with_enabled_state(self, app, action_with_old_format):
        """Test that get_settings returns new dict format with enabled state."""
        # Arrange
        dialog = EventNotifySettingsDialog(action_with_old_format)
        
        # Modify checkbox states
        item1 = dialog.times_list.item(1)
        widget1 = dialog.times_list.itemWidget(item1)
        checkbox1 = widget1.findChild(QCheckBox)
        checkbox1.setChecked(False)  # Disable second item
        
        # Act
        settings = dialog.get_settings()
        
        # Assert
        times = settings["event_notify_times"]
        assert len(times) == 3
        assert times[0]["enabled"] is True
        assert times[1]["enabled"] is False
        assert times[2]["enabled"] is True
        
        # Verify time values are preserved
        assert times[0]["time"] == "10:58"
        assert times[1]["time"] == "09:10"
        assert times[2]["time"] == "11:10"

    def test_collect_times_returns_dict_format(self, app, action_with_old_format):
        """Test that _collect_times returns dict format with enabled state."""
        # Arrange
        dialog = EventNotifySettingsDialog(action_with_old_format)
        
        # Disable middle item
        item1 = dialog.times_list.item(1)
        widget1 = dialog.times_list.itemWidget(item1)
        checkbox1 = widget1.findChild(QCheckBox)
        checkbox1.setChecked(False)
        
        # Act
        times = dialog._collect_times()
        
        # Assert
        assert len(times) == 3
        assert isinstance(times[0], dict)
        assert times[0] == {"time": "10:58", "enabled": True}
        assert times[1] == {"time": "09:10", "enabled": False}
        assert times[2] == {"time": "11:10", "enabled": True}

    def test_validation_passes_with_at_least_one_enabled_item(self, app, action_with_new_format):
        """Test that validation passes when at least one item is enabled."""
        # Arrange
        dialog = EventNotifySettingsDialog(action_with_new_format)
        
        # Act & Assert - should not raise any validation error
        dialog._on_save()  # This should call accept() if validation passes

    def test_empty_list_validation_fails(self, app):
        """Test that validation fails when no time items exist."""
        # Arrange
        from src.logic.action_type import ActionType, ActionMode
        from unittest.mock import patch
        
        action = AutoAction(
            name="Test Action",
            purpose="Test",
            action_type=ActionType.EVENT_NOTIFY,
            mode=ActionMode.ACTIVE
        )
        action.event_notify_times = []
        dialog = EventNotifySettingsDialog(action)
        
        # Act & Assert
        with patch('src.ui.event_notify_settings_dialog.QMessageBox.warning') as mock_warning:
            dialog._on_save()
            # Verify warning was shown
            mock_warning.assert_called_once()
            # Verify dialog was not accepted (accept() not called)
            assert not dialog.result()  # result() returns 0 if not accepted