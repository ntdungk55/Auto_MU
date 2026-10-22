"""Load the sample system prompt without exposing file access to application code."""

from __future__ import annotations

from pathlib import Path


class SystemPromptLoader:
    """Load one UTF-8 system-prompt document."""

    def load(self, path: Path) -> str:
        """Return the non-empty prompt text from the configured file."""
        prompt = path.read_text(encoding="utf-8-sig").strip()
        if not prompt:
            raise ValueError("system prompt must not be empty")
        return prompt
