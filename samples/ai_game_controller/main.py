"""Composition root for the AI game-process controller feature."""

from __future__ import annotations

import os
from pathlib import Path

from .application.prompt_builder import PromptBuilder
from .application.event_detector import EventDetector
from .application.process_controller import AIProcessController
from .application.scenario_engine import ScenarioEngine
from .application.scenario_manager import ScenarioManager
from .infrastructure.game_state_reader import GameStateReader
from .infrastructure.game_state_store import GameStateStore
from .infrastructure.ai_agent_factory import AIAgentFactory
from .infrastructure.gemini_agent import GeminiAgent
from .infrastructure.process_selector import ProcessSelector
from .infrastructure.scenario_repository import ScenarioRepository
from .infrastructure.settings_store import SettingsStore
from .infrastructure.system_prompt_loader import SystemPromptLoader
from .infrastructure.tesseract_recognizer import TesseractRecognizer
from .infrastructure.window_capture import GameWindowCapture


def create_ai_process_controller(
    scenario_path: Path | None = None,
    api_key: str | None = None,
    model_name: str | None = None,
) -> tuple[AIProcessController, ScenarioManager]:
    """Build the UI-independent controller and its scenario-management API."""
    root = Path(__file__).resolve().parent
    settings = SettingsStore().load(root / "config" / "app_settings.json")
    ocr_settings = settings.get("ocr", {})
    agent_settings = settings.get("agent", {})
    path_settings = settings.get("paths", {})
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
    agent_factory = AIAgentFactory()
    agent_factory.register("gemini", GeminiAgent)
    ai_agent = agent_factory.create(
        str(agent_settings.get("provider", "gemini")),
        api_key=api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", ""),
        model_name=model_name if model_name is not None else str(agent_settings.get("model", "")),
    )
    system_prompt_path = (root / "config" / str(path_settings.get("systemPrompt", "../prompts/system_prompt.md"))).resolve()
    controller = AIProcessController(
        game_state_reader=reader,
        game_state_store=GameStateStore(),
        event_detector=EventDetector(),
        scenario_engine=ScenarioEngine(
            prompt_builder=PromptBuilder(),
            ai_agent=ai_agent,
            system_prompt=SystemPromptLoader().load(system_prompt_path),
        ),
        process_selector=ProcessSelector(),
        interval_ms=int(ocr_settings.get("intervalMs", 500)),
    )
    return controller, scenario_manager
