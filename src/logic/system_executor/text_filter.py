"""Text Filter - Process and filter OCR text before sending notifications."""

import time
from typing import List, Optional


class TextFilter:
    """Filter and process text for notification with deduplication."""
    
    def __init__(self):
        """Initialize text filter with deduplication cache."""
        self._last_sent_content = None
        self._last_sent_time = None
    
    @staticmethod
    def split_into_sentences(text: str) -> List[str]:
        """Split text into sentences by period.
        
        Args:
            text: Input text to split
            
        Returns:
            List of sentences
        """
        if not text:
            return []
        
        # Split by period and clean up
        sentences = text.split(".")
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
    
    @staticmethod
    def _parse_filter_keywords(keywords_str: str) -> tuple[List[str], List[List[str]]]:
        """Parse filter keywords into AND and OR groups.
        
        Format:
        - "keyword1, keyword2" → AND (both required)
        - "keyword1 | keyword2" → OR (one of them)
        - "keyword1, keyword2 | keyword3" → (keyword1 AND keyword2) OR keyword3
        
        Args:
            keywords_str: Filter keywords string
            
        Returns:
            Tuple of (and_keywords, or_groups)
        """
        if not keywords_str or not keywords_str.strip():
            return [], []
        
        and_keywords = []
        or_groups = []
        
        # Split by comma first (AND conditions)
        parts = keywords_str.split(",")
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Check if this part has OR conditions
            if "|" in part:
                or_items = [item.strip() for item in part.split("|") if item.strip()]
                if or_items:
                    or_groups.append(or_items)
            else:
                and_keywords.append(part)
        
        return and_keywords, or_groups
    
    @staticmethod
    def matches_filter(text: str, required_keywords: str) -> bool:
        """Check if text matches filter (case-insensitive).
        
        Args:
            text: Text to check
            required_keywords: Filter keywords
            
        Returns:
            True if text matches filter, False otherwise
        """
        if not required_keywords or not required_keywords.strip():
            return True
        
        # Convert to lowercase for case-insensitive matching
        text_lower = text.lower()
        
        and_keywords, or_groups = TextFilter._parse_filter_keywords(required_keywords)
        
        # Check AND keywords (all must be present)
        for keyword in and_keywords:
            if keyword.lower() not in text_lower:
                return False
        
        # Check OR groups (at least one from each group must be present)
        for or_group in or_groups:
            if not any(keyword.lower() in text_lower for keyword in or_group):
                return False
        
        return True
    
    def get_matching_sentences(self, text: str, required_keywords: str = "", dedup_minutes: int = 1) -> List[str]:
        """Get sentences that match filter (case-insensitive).
        
        Split text into sentences first, then filter by keywords.
        Checks deduplication to avoid sending same content within time window.
        
        Args:
            text: Text to process
            required_keywords: Filter keywords
            dedup_minutes: Minutes to avoid duplicate (default 1)
            
        Returns:
            List of sentences matching filter, or empty if duplicate within time window
        """
        if not text:
            return []
        
        # Check for duplicate content within time window
        if self._is_duplicate(text, dedup_minutes):
            return []
        
        # Split into sentences first
        sentences = self.split_into_sentences(text)
        
        if not required_keywords or not required_keywords.strip():
            return sentences
        
        # Filter sentences that match filter
        matching = []
        for sentence in sentences:
            if self.matches_filter(sentence, required_keywords):
                matching.append(sentence)
        
        return matching
    
    def _is_duplicate(self, content: str, dedup_minutes: int) -> bool:
        """Check if content is duplicate within time window.
        
        Args:
            content: Content to check
            dedup_minutes: Time window in minutes
            
        Returns:
            True if duplicate within time window, False otherwise
        """
        if not self._last_sent_content:
            return False
        
        if self._last_sent_content != content:
            return False
        
        if not self._last_sent_time:
            return False
        
        elapsed_seconds = time.time() - self._last_sent_time
        elapsed_minutes = elapsed_seconds / 60.0
        
        return elapsed_minutes < dedup_minutes
    
    def mark_sent(self, content: str):
        """Mark content as sent to prevent duplicate notifications.
        
        Args:
            content: Content that was sent
        """
        self._last_sent_content = content
        self._last_sent_time = time.time()
    
    def reset_cache(self):
        """Reset deduplication cache."""
        self._last_sent_content = None
        self._last_sent_time = None

