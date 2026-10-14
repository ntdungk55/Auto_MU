"""Tests for the replacement teaching algorithm lab."""

import json

from src.ai_control.chat_message_log import ChatMessageLog
from src.ui.teaching_algorithm_lab_widget import TeachingAlgorithmLabWidget


def test_chat_history_page_is_limited_to_five_turns():
    """The chat UI loads five complete turns per page."""
    assert ChatMessageLog.PAGE_TURNS == 5


def test_teaching_asset_paths_are_scoped_to_assets(tmp_path):
    """Teaching assets use the dedicated project asset folder."""
    image_path, metadata_path = TeachingAlgorithmLabWidget.asset_paths(tmp_path)

    assert image_path == tmp_path / "assets" / "teaching" / "current_teaching.png"
    assert metadata_path == tmp_path / "assets" / "teaching" / "current_teaching.json"


def test_teaching_metadata_round_trip(tmp_path):
    """Teaching metadata preserves the selected window geometry."""
    image_path, metadata_path = TeachingAlgorithmLabWidget.asset_paths(tmp_path)
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"placeholder")
    metadata_path.write_text(
        json.dumps({"window_width": 800, "window_height": 600, "corner_x1": 10}),
        encoding="utf-8",
    )

    metadata = TeachingAlgorithmLabWidget.load_teaching_metadata(tmp_path)

    assert metadata["window_width"] == 800
    assert metadata["corner_x1"] == 10
