"""Unit tests for event tracking line extraction and state handling."""

from src.logic.system_executor.event_tracking_helper import (
    extract_event_tracking_lines,
    match_event_tracking_lines,
    match_ocr_pattern,
    update_event_tracking_state,
)


class TestEventTrackingPatternMatch:
    """Test event tracking OCR pattern matching."""

    def test_exact_match_extracts_variables(self):
        text = "Boss Rồng sẽ bắt đầu sau 5 phút"
        pattern = "{event_name} sẽ bắt đầu sau {minutes} phút"

        result = match_ocr_pattern(text, pattern, 100.0)

        assert result is not None
        assert result["score"] == 100.0
        assert ("event_name", "Boss Rồng") in result["variables"]
        assert ("minutes", "5") in result["variables"]

    def test_non_matching_text_returns_none(self):
        text = "Không có sự kiện nào"
        pattern = "{event_name} sẽ bắt đầu sau {minutes} phút"

        result = match_ocr_pattern(text, pattern, 100.0)

        assert result is None

    def test_match_can_find_pattern_inside_multiline_ocr_text(self):
        text = "Thông báo khác\nBoss Rồng sẽ bắt đầu sau 5 phút\nDòng cuối"
        pattern = "{event_name} sẽ bắt đầu sau {minutes} phút"

        result = match_ocr_pattern(text, pattern, 100.0)

        assert result is not None
        assert result["line"] == "Boss Rồng sẽ bắt đầu sau 5 phút"
        assert ("minutes", "5") in result["variables"]


class TestEventTrackingLines:
    """Test OCR line extraction for event tracking."""

    def test_extract_event_lines_prefers_pattern_related_rows(self):
        ocr_text = (
            "Cập nhật tại sàn giao dịch: 1 tỷ Zen 214 bạc\n"
            "Sự kiện Imperial Guardian sẽ bắt đầu sau 3 phút nữa\n"
            "Sự kiện Imperial Guardian sẽ bắt đầu sau 1 phút nữa"
        )
        pattern = "Sự kiện Imperial Guardian sẽ bắt đầu sau {minutes} phút"

        lines = extract_event_tracking_lines(ocr_text, pattern)

        assert lines == [
            "Sự kiện Imperial Guardian sẽ bắt đầu sau 3 phút nữa",
            "Sự kiện Imperial Guardian sẽ bắt đầu sau 1 phút nữa",
        ]

    def test_extract_event_lines_can_split_blob_by_event_anchor(self):
        ocr_text = (
            "Cập nhật tại sàn giao dịch: 1 tỷ Zen 214 bạc "
            "Sự kiện Quảng Trường Quỷ sẽ mở trong vòng 1 phút "
            "Sự kiện Imperial Guardian sẽ bắt đầu sau 3 phút nữa"
        )
        pattern = "Sự kiện Imperial Guardian sẽ bắt đầu sau {minutes} phút"

        lines = extract_event_tracking_lines(ocr_text, pattern)

        assert "Sự kiện Imperial Guardian sẽ bắt đầu sau 3 phút nữa" in lines
        assert all("Cập nhật tại sàn giao dịch" not in line for line in lines)

    def test_match_event_tracking_lines_ignores_non_matching_rows(self):
        lines = [
            "Cánh cửa vào Sự kiện Tháp Kanturu đã mở",
            "Sự kiện Imperial Guardian sẽ bắt đầu sau 3 phút nữa",
            "Cập nhật tại sàn giao dịch: 1 tỷ Zen 214 bạc",
        ]
        pattern = "Sự kiện Imperial Guardian sẽ bắt đầu sau {minutes} phút"

        result = match_event_tracking_lines(lines, pattern, 90.0)

        assert result is not None
        assert result["line"] == "Sự kiện Imperial Guardian sẽ bắt đầu sau 3 phút nữa"
        assert result["line_index"] == 1
        assert ("minutes", "3") in result["variables"]


class TestEventTrackingState:
    """Test state transitions for event tracking trigger decisions."""

    def test_first_seen_pattern_passes_immediately(self):
        cache = {}

        result = update_event_tracking_state(cache, "Sự kiện Imperial Guardian sẽ bắt đầu sau 3 phút", 100.0, 900.0)

        assert result == {"should_pass": True, "reason": "first_seen"}

    def test_duplicate_visible_pattern_does_not_pass(self):
        cache = {}
        update_event_tracking_state(cache, "Sự kiện Imperial Guardian sẽ bắt đầu sau 3 phút", 100.0, 900.0)

        result = update_event_tracking_state(cache, "Sự kiện Imperial Guardian sẽ bắt đầu sau 3 phút", 110.0, 900.0)

        assert result == {"should_pass": False, "reason": "duplicate_visible"}

    def test_reappeared_same_pattern_after_timeout_passes_again(self):
        cache = {}
        pattern = "Sự kiện Imperial Guardian sẽ bắt đầu sau 3 phút"

        update_event_tracking_state(cache, pattern, 100.0, 900.0)
        update_event_tracking_state(cache, None, 120.0, 900.0)

        result = update_event_tracking_state(cache, pattern, 120.0 + 901.0, 900.0)

        assert result == {"should_pass": True, "reason": "reappeared_after_timeout"}
