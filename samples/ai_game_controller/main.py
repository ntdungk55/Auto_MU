"""Composition root for the AI game-process controller feature."""

from __future__ import annotations

from pathlib import Path

from .application.event_detector import EventDetector
from .application.process_controller import AIProcessController
from .application.scenario_engine import ScenarioEngine
from .application.scenario_manager import ScenarioManager
from .infrastructure.game_state_reader import GameStateReader
from .infrastructure.game_state_store import GameStateStore
from .infrastructure.process_selector import ProcessSelector
from .infrastructure.scenario_repository import ScenarioRepository
from .infrastructure.settings_store import SettingsStore
from .infrastructure.tesseract_recognizer import TesseractRecognizer
from .infrastructure.window_capture import GameWindowCapture


def create_ai_process_controller(scenario_path: Path | None = None) -> tuple[AIProcessController, ScenarioManager]:
    """Build the UI-independent controller and its scenario-management API."""
    root = Path(__file__).resolve().parent
    settings = SettingsStore().load(root / "config" / "app_settings.json")
    ocr_settings = settings.get("ocr", {})
    reader = GameStateReader(
        capture=GameWindowCapture(),
        recognizer=TesseractRecognizer(),
        teaching_path=root.parent.parent / "mcp" / "config" / "mu_game_window.json",
        width=int(ocr_settings.get("clientWidth", 800)),
        height=int(ocr_settings.get("clientHeight", 600)),
        scale=float(ocr_settings.get("scale", 1.0)),
        grayscale=bool(ocr_settings.get("grayscale", True)),
        threshold=int(ocr_settings.get("threshold", 80)),
    )
    scenario_manager = ScenarioManager(ScenarioRepository(scenario_path))
    controller = AIProcessController(
        game_state_reader=reader,
        game_state_store=GameStateStore(),
        event_detector=EventDetector(),
        scenario_engine=ScenarioEngine(),
        process_selector=ProcessSelector(),
        interval_ms=int(ocr_settings.get("intervalMs", 500)),
    )
    return controller, scenario_manager
