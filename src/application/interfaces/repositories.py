"""Repository interfaces for data persistence."""

from abc import ABC, abstractmethod
from typing import Optional
from domain.entities.tool import Tool


class IToolRepository(ABC):
    """Port for tool persistence."""
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Tool]:
        """Get tool by name."""
        pass
    
    @abstractmethod
    def save(self, tool: Tool) -> None:
        """Save tool."""
        pass
    
    @abstractmethod
    def delete(self, name: str) -> bool:
        """Delete tool by name."""
        pass
    
    @abstractmethod
    def list_all(self) -> list[str]:
        """List all tool names."""
        pass
