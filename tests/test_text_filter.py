"""Tests for TextFilter class."""

import time
import pytest
from src.logic.system_executor.text_filter import TextFilter


class TestTextFilterSentenceSplitting:
    """Test sentence splitting functionality."""
    
    def test_split_single_sentence(self):
        """Test splitting single sentence."""
        tf = TextFilter()
        result = tf.split_into_sentences("Hello world")
        assert result == ["Hello world"]
    
    def test_split_multiple_sentences(self):
        """Test splitting multiple sentences."""
        tf = TextFilter()
        result = tf.split_into_sentences("First. Second. Third.")
        assert result == ["First", "Second", "Third"]
    
    def test_split_empty_string(self):
        """Test splitting empty string."""
        tf = TextFilter()
        result = tf.split_into_sentences("")
        assert result == []
    
    def test_split_with_extra_spaces(self):
        """Test splitting with extra spaces."""
        tf = TextFilter()
        result = tf.split_into_sentences("  First  .  Second  .")
        assert result == ["First", "Second"]


class TestTextFilterANDLogic:
    """Test AND filter logic (all keywords required)."""
    
    def test_and_filter_all_present(self):
        """Test AND filter when all keywords present."""
        tf = TextFilter()
        assert tf.matches_filter("Success and completed", "Success, completed")
    
    def test_and_filter_missing_one(self):
        """Test AND filter when one keyword missing."""
        tf = TextFilter()
        assert not tf.matches_filter("Success only", "Success, completed")
    
    def test_and_filter_case_insensitive(self):
        """Test AND filter is case-insensitive."""
        tf = TextFilter()
        assert tf.matches_filter("success and completed", "Success, completed")
        assert tf.matches_filter("Success and completed", "Success, completed")
        assert tf.matches_filter("SUCCESS AND COMPLETED", "success, completed")


class TestTextFilterORLogic:
    """Test OR filter logic (one keyword required)."""
    
    def test_or_filter_first_present(self):
        """Test OR filter when first keyword present."""
        tf = TextFilter()
        assert tf.matches_filter("Success", "Success | Failed")
    
    def test_or_filter_second_present(self):
        """Test OR filter when second keyword present."""
        tf = TextFilter()
        assert tf.matches_filter("Failed", "Success | Failed")
    
    def test_or_filter_none_present(self):
        """Test OR filter when no keyword present."""
        tf = TextFilter()
        assert not tf.matches_filter("Pending", "Success | Failed")


class TestTextFilterCombined:
    """Test combined AND/OR logic."""
    
    def test_combined_or_only(self):
        """Test OR filter: keyword1 | keyword2."""
        tf = TextFilter()
        assert tf.matches_filter("Success", "Success | Failed")
        assert tf.matches_filter("Failed", "Success | Failed")
        assert not tf.matches_filter("Pending", "Success | Failed")


class TestTextFilterGetMatchingSentences:
    """Test get_matching_sentences with filtering."""
    
    def test_get_matching_no_filter(self):
        """Test getting sentences without filter."""
        tf = TextFilter()
        text = "First. Second. Third."
        result = tf.get_matching_sentences(text, "")
        assert result == ["First", "Second", "Third"]
    
    def test_get_matching_with_filter(self):
        """Test getting sentences with filter."""
        tf = TextFilter()
        text = "Success completed. Failed process. Success again."
        result = tf.get_matching_sentences(text, "Success")
        assert result == ["Success completed", "Success again"]
    
    def test_get_matching_empty_text(self):
        """Test getting sentences from empty text."""
        tf = TextFilter()
        result = tf.get_matching_sentences("", "Success")
        assert result == []


class TestTextFilterDeduplication:
    """Test deduplication logic."""
    
    def test_dedup_same_content_within_window(self):
        """Test deduplication blocks same content within time window."""
        tf = TextFilter()
        text = "Success message"
        
        # First call should return sentences
        result1 = tf.get_matching_sentences(text, "", dedup_minutes=1)
        assert result1 == ["Success message"]
        
        # Mark as sent
        tf.mark_sent(text)
        
        # Second call immediately should return empty (duplicate)
        result2 = tf.get_matching_sentences(text, "", dedup_minutes=1)
        assert result2 == []
    
    def test_dedup_different_content(self):
        """Test deduplication allows different content."""
        tf = TextFilter()
        
        # First message
        result1 = tf.get_matching_sentences("First message", "", dedup_minutes=1)
        assert result1 == ["First message"]
        tf.mark_sent("First message")
        
        # Different message should not be blocked
        result2 = tf.get_matching_sentences("Second message", "", dedup_minutes=1)
        assert result2 == ["Second message"]
    
    def test_dedup_after_time_window(self):
        """Test deduplication allows same content after time window."""
        tf = TextFilter()
        text = "Success message"
        
        # First call
        result1 = tf.get_matching_sentences(text, "", dedup_minutes=1)
        assert result1 == ["Success message"]
        tf.mark_sent(text)
        
        # Simulate time passing (more than 1 minute)
        tf._last_sent_time = time.time() - 61  # 61 seconds ago
        
        # Second call should allow (outside time window)
        result2 = tf.get_matching_sentences(text, "", dedup_minutes=1)
        assert result2 == ["Success message"]
    
    def test_dedup_custom_window(self):
        """Test deduplication with custom time window."""
        tf = TextFilter()
        text = "Message"
        
        result1 = tf.get_matching_sentences(text, "", dedup_minutes=5)
        assert result1 == ["Message"]
        tf.mark_sent(text)
        
        # Simulate 3 minutes passing (within 5 minute window)
        tf._last_sent_time = time.time() - 180
        result2 = tf.get_matching_sentences(text, "", dedup_minutes=5)
        assert result2 == []  # Still blocked
        
        # Simulate 6 minutes passing (outside 5 minute window)
        tf._last_sent_time = time.time() - 360
        result3 = tf.get_matching_sentences(text, "", dedup_minutes=5)
        assert result3 == ["Message"]  # Allowed


class TestTextFilterReset:
    """Test cache reset functionality."""
    
    def test_reset_cache(self):
        """Test resetting deduplication cache."""
        tf = TextFilter()
        text = "Message"
        
        result1 = tf.get_matching_sentences(text, "")
        assert result1 == ["Message"]
        tf.mark_sent(text)
        
        # Should be blocked
        result2 = tf.get_matching_sentences(text, "")
        assert result2 == []
        
        # Reset cache
        tf.reset_cache()
        
        # Should be allowed again
        result3 = tf.get_matching_sentences(text, "")
        assert result3 == ["Message"]


class TestTextFilterIntegration:
    """Integration tests combining multiple features."""
    
    def test_filter_and_dedup_together(self):
        """Test filtering and deduplication working together."""
        tf = TextFilter()
        text = "Success completed. Failed process. Success again."
        
        # Get matching sentences
        result1 = tf.get_matching_sentences(text, "Success", dedup_minutes=1)
        assert result1 == ["Success completed", "Success again"]
        
        # Mark as sent
        tf.mark_sent(text)
        
        # Same text should be blocked
        result2 = tf.get_matching_sentences(text, "Success", dedup_minutes=1)
        assert result2 == []
        
        # Different text should be allowed
        result3 = tf.get_matching_sentences("Success new", "Success", dedup_minutes=1)
        assert result3 == ["Success new"]
