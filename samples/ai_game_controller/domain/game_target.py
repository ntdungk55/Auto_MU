"""Game-window target model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GameTarget:
    """A selectable game process and its top-level window."""

    target_id: str
    hwnd: int
    process_name: str
    window_title: str
