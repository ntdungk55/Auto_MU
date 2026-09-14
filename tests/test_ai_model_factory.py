"""Tests for shared system prompt loading and provider-neutral AI adapters."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.ai_control.ai_models.contracts import AIChatSession, AIModelAdapter, AIResponse
from src.ai_control.ai_models.factory import AIModelFactory, create_default_ai_model_factory
from src.ai_control.ai_models.gemini_adapter import GeminiModelAdapter
from src.ai_control.ai_models.system_prompt_loader import (
    SYSTEM_PROMPT_RELATIVE_PATH,
    SystemPromptLoader,
)


class _FakeChatSession(AIChatSession):
    @property
    def history(self):
        return []

    def send(self, content):
        return AIResponse(text=str(content))

    def send_tool_results(self, results):
        return AIResponse(text="done")


class _FakeAdapter(AIModelAdapter):
    def __init__(self, *, model_name: str, **_):
        self._model_name = model_name

    @property
    def provider_name(self):
        return "fake"

    @property
    def model_name(self):
        return self._model_name

    def validate(self):
        return None

    def start_chat(self, *, system_prompt, tools, history=None):
        assert system_prompt
        return _FakeChatSession()


def test_factory_registers_and_creates_adapter():
    factory = AIModelFactory()
    factory.register("FAKE", _FakeAdapter)

    adapter = factory.create("fake", model_name="model-a")

    assert isinstance(adapter, _FakeAdapter)
    assert adapter.model_name == "model-a"
    assert factory.available_providers() == ("fake",)


def test_factory_rejects_unknown_and_duplicate_provider():
    factory = AIModelFactory()
    factory.register("fake", _FakeAdapter)

    with pytest.raises(ValueError, match="đã được đăng ký"):
        factory.register("FAKE", _FakeAdapter)
    with pytest.raises(ValueError, match="không được hỗ trợ"):
        factory.create("other", model_name="x")


def test_default_factory_contains_configured_providers():
    assert create_default_ai_model_factory().available_providers() == ("gemini", "openrouter")


def test_system_prompt_loader_reads_utf8_and_returns_checksum(tmp_path):
    prompt_path = tmp_path / SYSTEM_PROMPT_RELATIVE_PATH
    prompt_path.parent.mkdir(parents=True)
    prompt_path.write_text("System prompt dùng chung", encoding="utf-8")

    loaded = SystemPromptLoader(tmp_path).load()

    assert loaded.text == "System prompt dùng chung"
    assert loaded.path == prompt_path
    assert len(loaded.sha256) == 64


def test_system_prompt_loader_fails_on_missing_or_empty_file(tmp_path):
    loader = SystemPromptLoader(tmp_path)
    with pytest.raises(FileNotFoundError, match="Không tìm thấy system prompt"):
        loader.load()

    loader.prompt_path.parent.mkdir(parents=True)
    loader.prompt_path.write_text("   ", encoding="utf-8")
    with pytest.raises(ValueError, match="không được để trống"):
        loader.load()


def test_project_system_prompt_is_loadable():
    loaded = SystemPromptLoader().load()

    assert "Auto_MU Scenario Engine" in loaded.text
    assert loaded.path.name == "scenario_engine_system_prompt.md"


class _FakeRawChat:
    def __init__(self):
        self.history = []

    def send_message(self, _content):
        return SimpleNamespace(text="ok", candidates=[])


class _FakeRawModel:
    def __init__(self, sdk, model_name, tools, system_instruction):
        sdk.created = {
            "model_name": model_name,
            "tools": tools,
            "system_instruction": system_instruction,
        }

    def start_chat(self, history):
        chat = _FakeRawChat()
        chat.history = list(history)
        return chat


class _FakeGeminiSDK:
    created = None
    configured_key = None

    @classmethod
    def configure(cls, *, api_key):
        cls.configured_key = api_key

    @staticmethod
    def get_model(name):
        return {"name": name}

    @classmethod
    def GenerativeModel(cls, model_name, *, tools, system_instruction):
        return _FakeRawModel(cls, model_name, tools, system_instruction)


def test_gemini_adapter_receives_the_shared_system_prompt():
    adapter = GeminiModelAdapter(
        model_name="gemini-test",
        api_key="secret-test-key",
        sdk_module=_FakeGeminiSDK,
    )
    adapter.validate()

    chat = adapter.start_chat(
        system_prompt="ONE SHARED SYSTEM PROMPT",
        tools=[],
        history=[{"role": "user"}],
    )

    assert _FakeGeminiSDK.configured_key == "secret-test-key"
    assert _FakeGeminiSDK.created["system_instruction"] == "ONE SHARED SYSTEM PROMPT"
    assert _FakeGeminiSDK.created["model_name"] == "gemini-test"
    assert chat.history == [{"role": "user"}]
    assert chat.send("hello").text == "ok"
