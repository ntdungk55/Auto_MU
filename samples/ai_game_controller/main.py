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
from src.ai_control.ai_manager import AIManager

from .infrastructure.managed_ai_agent import ManagedAIAgent
from .infrastructure.process_selector import ProcessSelector
from .infrastructure.scenario_repository import ScenarioRepository
from .infrastructure.settings_store import SettingsStore
from .infrastructure.system_prompt_loader import SystemPromptLoader
from .infrastructure.easyocr_recognizer import EasyOCRRecognizer
from .infrastructure.window_capture import GameWindowCapture


def create_ai_process_controller(
    scenario_path: Path | None = None,
    api_key: str | None = None,
    model_name: str | None = None,
    provider: str | None = None,
    provider_configs: dict[str, dict[str, str]] | None = None,
) -> tuple[AIProcessController, ScenarioManager]:
    """Build the UI-independent controller and its scenario-management API."""
    root = Path(__file__).resolve().parent
    settings = SettingsStore().load(root / "config" / "app_settings.json")
    ocr_settings = settings.get("ocr", {})
    agent_settings = settings.get("agent", {})
    path_settings = settings.get("paths", {})
    reader = GameStateReader(
        capture=GameWindowCapture(),
        recognizer=EasyOCRRecognizer(),
        teaching_path=root.parent.parent / "mcp" / "config" / "mu_game_window.json",
        width=int(ocr_settings.get("clientWidth", 800)),
        height=int(ocr_settings.get("clientHeight", 600)),
        scale=float(ocr_settings.get("scale", 1.0)),
        grayscale=bool(ocr_settings.get("grayscale", True)),
        threshold=int(ocr_settings.get("threshold", 80)),
    )
    scenario_manager = ScenarioManager(ScenarioRepository(scenario_path))
    provider_name = str(provider or agent_settings.get("provider", "openrouter")).strip().casefold()
    configs = dict(provider_configs or {})
    if not configs:
        configs[provider_name] = {
            "api_key": api_key if api_key is not None else os.environ.get(f"{provider_name.upper()}_API_KEY", ""),
            "model_name": model_name if model_name is not None else str(agent_settings.get("model", "")),
        }
    manager = AIManager()
    ordered_providers = [provider_name, *(name for name in configs if name != provider_name)]
    for name in ordered_providers:
        config = configs.get(name, {})
        configured_model = str(config.get("model_name", "") or "").strip()
        configured_key = str(config.get("api_key", "") or "").strip()
        if not configured_model or not configured_key:
            continue
        adapter_config: dict[str, object] = {"api_key": configured_key}
        if name == "gemini":
            try:
                import google.generativeai as genai
            except ImportError:
                genai = None
            adapter_config["sdk_module"] = genai
        manager.register_model(
            f"{name}:{configured_model}",
            provider=name,
            model_name=configured_model,
            adapter_config=adapter_config,
            supports_tools=True,
            intelligence_level=2,
            priority=10 if name == provider_name else 0,
        )
    ai_agent = ManagedAIAgent(manager)
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
