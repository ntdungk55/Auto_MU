"""Game state domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class GameState:
    """Immutable OCR snapshot for one selected game window."""

    target_id: str
    hwnd: int
    captured_at: datetime
    main_info: dict[str, Any] = field(default_factory=dict)
