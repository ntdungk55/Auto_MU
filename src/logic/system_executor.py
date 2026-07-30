"""System Executor - Backward compatibility wrapper.

This module imports from the refactored system_executor package.
"""

from .system_executor import SystemExecutor
from .system_executor.text_filter import TextFilter

__all__ = ["SystemExecutor", "TextFilter"]
