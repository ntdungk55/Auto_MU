"""Application entry point for the AI Game Controller sample."""

from __future__ import annotations

from .ui.main_window import MainWindow


class AIGameControllerApp:
    """Compose and run the sample application's top-level UI."""

    def __init__(self) -> None:
        self.main_window = MainWindow()

    def run(self) -> int:
        """Run the sample after a concrete Qt bootstrap is implemented."""
        raise NotImplementedError("Qt application bootstrap is not implemented yet")
