"""Factory for creating engine instances."""

from typing import Literal


def create_engine(
    engine_type: Literal["legacy", "clean"],
    signals,
    executor,
    tool_manager=None,
):
    """Create engine instance based on type.
    
    Args:
        engine_type: "legacy" for AutoBotEngine, "clean" for CleanArchitectureEngine
        signals: PyQt signals object
        executor: SystemExecutor instance
        tool_manager: Optional ToolManager instance
    
    Returns:
        Engine instance (AutoBotEngine or CleanArchitectureEngine)
    """
    if engine_type == "clean":
        from .engine import CleanArchitectureEngine
        return CleanArchitectureEngine(signals, executor, tool_manager)
    else:
        # Import legacy engine from main.py would cause circular import
        # So we return None and let caller handle it
        return None
