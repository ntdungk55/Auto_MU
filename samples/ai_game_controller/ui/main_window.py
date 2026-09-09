"""Main PyQt window for the AI Game Controller sample."""

from __future__ import annotations

from typing import Any

from PyQt6.QtWidgets import QMainWindow


class MainWindow(QMainWindow):
    """Collect target/scenario input and expose Start/Stop controls."""

    def __init__(self, process_controller: Any | None = None) -> None:
        super().__init__()
        self.process_controller = process_controller
        self.setWindowTitle("AI Game Controller sample")
