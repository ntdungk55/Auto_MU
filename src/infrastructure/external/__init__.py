"""External adapters - wrap existing implementations."""

from .system_executor_adapter import SystemExecutorAdapter
from .input_blocker_adapter import InputBlockerAdapter
from .stop_controller import StopController

__all__ = [
    'SystemExecutorAdapter',
    'InputBlockerAdapter',
    'StopController',
]
