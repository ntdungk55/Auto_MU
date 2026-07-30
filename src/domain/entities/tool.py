"""Tool entity - Single Source of Truth for tool data."""

from dataclasses import dataclass, field
from typing import Optional
from .action import AutoAction


@dataclass
class Tool:
    """Domain entity for automation tool."""
    
    name: str
    actions: list[AutoAction] = field(default_factory=list)
    
    # Loop settings
    loop_enabled: bool = False
    loop_mode: str = "forever"  # "forever" or "count"
    loop_count: int = 1
    loop_pre_delay_100ms: int = 0
    loop_post_delay_100ms: int = 0
    
    # Timeout behavior
    stop_on_timeout: bool = True
    restart_on_timeout: bool = False
    
    # Input blocking
    block_input_enabled: bool = False
    block_input_duration: float = 3.0
    
    @property
    def loop_pre_delay(self) -> float:
        """Pre-delay in seconds."""
        return self.loop_pre_delay_100ms / 10.0
    
    @property
    def loop_post_delay(self) -> float:
        """Post-delay in seconds."""
        return self.loop_post_delay_100ms / 10.0
    
    @classmethod
    def serializable_fields(cls) -> list[str]:
        """SSOT: All fields that should be serialized."""
        return [
            'name', 'actions',
            'loop_enabled', 'loop_mode', 'loop_count',
            'loop_pre_delay_100ms', 'loop_post_delay_100ms',
            'stop_on_timeout', 'restart_on_timeout',
            'block_input_enabled', 'block_input_duration',
        ]
