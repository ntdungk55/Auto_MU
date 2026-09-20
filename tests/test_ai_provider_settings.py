import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.ui.gemini_chat_widget import GeminiSettingsDialog, GeminiChatWidget, _ChatBubble


APP = QApplication.instance() or QApplication([])


def test_provider_change_uses_its_models_and_never_reuses_the_previous_key():
    saved_models = []
    dialog = GeminiSettingsDialog(
        initial_provider="gemini",
        initial_key="gemini-secret",
        initial_model="gemini-2.5-flash",
        on_save_model=lambda provider, model: saved_models.append((provider, model)),
    )

    dialog.provider_combo.setCurrentIndex(dialog.provider_combo.findData("openrouter"))

    assert dialog.selected_provider() == "openrouter"
    assert dialog.key_input.text() == ""
    assert dialog.model_combo.findData("google/gemini-2.5-flash") >= 0
    dialog.save_model()
    assert saved_models == [("openrouter", "google/gemini-2.5-flash")]


def test_chat_bubble_renders_safe_markdown_and_simplifies_inline_math():
    bubble = _ChatBubble(
        "**Map**: `Kanturu` và $abs(x - 140) <= 20$\n\n<img src='bad'>",
        side="left",
    )

    rendered = bubble.label.text()
    assert bubble.label.textFormat() == Qt.TextFormat.RichText
    assert "font-weight:700" in rendered
    assert "font-family:'monospace'" in rendered
    assert "$abs" not in rendered
    assert "&lt;img src='bad'&gt;" in rendered


def test_provider_sdk_packages_are_selected_by_provider():
    assert GeminiChatWidget._provider_package("openrouter") == "openai"
    assert GeminiChatWidget._provider_package("ollama") == ""
    assert GeminiChatWidget._provider_package("gemini") == "google-generativeai"
    assert GeminiChatWidget._provider_sdk_available("ollama") is True


def test_widget_loads_credentials_and_models_for_each_provider():
    widget = GeminiChatWidget(
        load_saved_provider=lambda: "openrouter",
        load_saved_key=lambda provider: f"{provider}-key",
        load_saved_model=lambda provider: f"{provider}-model",
        managed_process_tab=True,
    )

    assert widget._key_for_provider("openrouter") == "openrouter-key"
    assert widget._key_for_provider("gemini") == "gemini-key"
    assert widget._model_for_provider("openrouter") == "openrouter-model"
    assert widget._model_for_provider("gemini") == "gemini-model"


def test_ollama_provider_offers_the_two_local_models_without_an_api_key():
    dialog = GeminiSettingsDialog(
        initial_provider="ollama",
        initial_model="gemma4:e2b",
        ollama_models=["gemma4:e2b", "MichelRosselli/bonsai-27b:latest"],
    )

    assert dialog.selected_provider() == "ollama"
    assert [dialog.model_combo.itemText(i) for i in range(dialog.model_combo.count())] == [
        "gemma4:e2b",
        "MichelRosselli/bonsai-27b:latest",
    ]
    assert dialog.key_input.isEnabled() is False
    assert dialog.refresh_models_btn.isHidden() is True


def test_ollama_model_refresh_replaces_a_removed_saved_model(monkeypatch):
    import src.ai_control.ai_models.ollama_adapter as adapter_module

    class FakeAdapter:
        def __init__(self, **_kwargs):
            pass

        def available_models(self):
            return ("gemma4:e2b",)

    monkeypatch.setattr(adapter_module, "OllamaModelAdapter", FakeAdapter)
    saved_models = []
    widget = GeminiChatWidget(
        load_saved_provider=lambda: "ollama",
        load_saved_model=lambda provider: "MichelRosselli/bonsai-27b:latest",
        save_model=lambda provider, model: saved_models.append((provider, model)),
        managed_process_tab=True,
    )

    assert widget._refresh_ollama_models() == ["gemma4:e2b"]
    assert widget._current_model() == "gemma4:e2b"
    assert saved_models == [("ollama", "gemma4:e2b")]


def test_ollama_model_refresh_clears_selection_when_server_is_empty(monkeypatch):
    import src.ai_control.ai_models.ollama_adapter as adapter_module

    class FakeAdapter:
        def __init__(self, **_kwargs):
            pass

        def available_models(self):
            return ()

    monkeypatch.setattr(adapter_module, "OllamaModelAdapter", FakeAdapter)
    saved_models = []
    widget = GeminiChatWidget(
        load_saved_provider=lambda: "ollama",
        load_saved_model=lambda provider: "removed:model",
        save_model=lambda provider, model: saved_models.append((provider, model)),
        managed_process_tab=True,
    )

    assert widget._refresh_ollama_models() == []
    assert widget._current_model() == ""
    assert widget.settings_btn.text().startswith("Chọn model")
    assert saved_models == [("ollama", "")]


def test_process_does_not_connect_when_ollama_has_no_models(monkeypatch):
    target = SimpleNamespace(
        target_id="123:456",
        hwnd=456,
        process_name="game.exe",
        window_title="MU GameThuVN",
    )
    controller_calls = []
    widget = GeminiChatWidget(
        load_saved_provider=lambda: "ollama",
        load_saved_model=lambda provider: "removed:model",
        load_tab_ai_settings=lambda selected: {
            "provider": "ollama",
            "model": "removed:model",
        },
        create_ai_process_controller=lambda *_args: controller_calls.append(True),
        managed_process_tab=True,
    )
    monkeypatch.setattr(widget, "_refresh_ollama_models", lambda selected=None: [])
    widget.process_combo.addItem("MU GameThuVN", target)

    widget._on_process_selected(widget.process_combo.count() - 1)

    assert controller_calls == []
    assert widget._chat is None
    assert widget.status_lbl.text() == "Ollama không có model; chưa kết nối"


def test_each_chat_tab_can_load_its_own_provider_and_model():
    target = object()
    widget = GeminiChatWidget(
        load_saved_provider=lambda: "openrouter",
        load_saved_model=lambda provider: f"global-{provider}",
        load_tab_ai_settings=lambda selected: {
            "provider": "ollama",
            "model": "MichelRosselli/bonsai-27b:latest",
        } if selected is target else {},
        managed_process_tab=True,
    )

    widget._load_settings_for_target(target)

    assert widget._current_provider() == "ollama"
    assert widget._current_model() == "MichelRosselli/bonsai-27b:latest"


def test_chat_tab_saves_provider_and_model_for_its_selected_process():
    saved = []
    saved_providers = []
    saved_models = []
    target = object()
    widget = GeminiChatWidget(
        save_provider=saved_providers.append,
        save_model=lambda provider, model: saved_models.append((provider, model)),
        save_tab_ai_settings=lambda selected, provider, model: saved.append(
            (selected, provider, model)
        ),
        managed_process_tab=True,
    )
    widget._selected_game_target = target

    widget._save_current_tab_settings("ollama", "gemma4:e2b")

    assert saved == [(target, "ollama", "gemma4:e2b")]
    assert saved_providers == ["ollama"]
    assert saved_models == [("ollama", "gemma4:e2b")]
    assert widget._current_provider() == "ollama"
    assert widget._current_model() == "gemma4:e2b"
    assert "gemma4:e2b" in widget.settings_btn.text()


def test_composer_places_settings_with_attachment_and_automatic_actions():
    widget = GeminiChatWidget(
        load_saved_provider=lambda: "ollama",
        load_saved_model=lambda provider: "gemma4:e2b",
        managed_process_tab=True,
    )

    action_widgets = [
        widget.composer_actions.itemAt(index).widget()
        for index in range(widget.composer_actions.count())
    ]

    assert widget.attach_btn in action_widgets
    assert widget.auto_messages_btn in action_widgets
    assert widget.settings_btn in action_widgets
    assert widget.ai_activity_btn in action_widgets
    assert "gemma4:e2b" in widget.settings_btn.text()
    assert widget.attach_btn.icon().isNull() is False
    assert widget.auto_messages_btn.icon().isNull() is False
    assert "border-radius:11px" in widget.attach_btn.styleSheet()
    assert "border-radius:11px" in widget.auto_messages_btn.styleSheet()


def test_last_selected_model_is_restored_in_a_new_chat_widget():
    state = {"provider": "openrouter", "models": {}}

    first = GeminiChatWidget(
        load_saved_provider=lambda: state["provider"],
        save_provider=lambda provider: state.__setitem__("provider", provider),
        load_saved_model=lambda provider: state["models"].get(provider, ""),
        save_model=lambda provider, model: state["models"].__setitem__(provider, model),
        managed_process_tab=True,
    )
    first._save_current_tab_settings("ollama", "MichelRosselli/bonsai-27b:latest")

    reopened = GeminiChatWidget(
        load_saved_provider=lambda: state["provider"],
        load_saved_model=lambda provider: state["models"].get(provider, ""),
        managed_process_tab=True,
    )

    assert reopened._current_provider() == "ollama"
    assert reopened._current_model() == "MichelRosselli/bonsai-27b:latest"
    assert "MichelRosselli/bonsai-27b:latest" in reopened.settings_btn.text()


def test_ollama_tab_does_not_register_billable_fallback_providers(monkeypatch):
    import src.ai_control.ai_manager as ai_manager_module

    class FakeManager:
        instances = []

        def __init__(self):
            self.registered = []
            self.__class__.instances.append(self)

        def register_model(self, model_id, **config):
            self.registered.append((model_id, config))

        def validate_models(self):
            return tuple(model_id for model_id, _ in self.registered)

        def start_chat(self, **_kwargs):
            return object()

        def model_status(self):
            return tuple(
                {
                    "id": model_id,
                    "provider": config["provider"],
                    "model_name": config["model_name"],
                }
                for model_id, config in self.registered
            )

    monkeypatch.setattr(ai_manager_module, "AIManager", FakeManager)
    widget = GeminiChatWidget(
        load_saved_provider=lambda: "ollama",
        load_saved_model=lambda provider: "gemma4:e2b" if provider == "ollama" else "paid-model",
        load_saved_key=lambda provider: "paid-key",
        managed_process_tab=True,
    )
    widget._scenario_tool_client = SimpleNamespace(
        load_scenario_snapshot=lambda: {"ok": True},
        refresh_tools=lambda timeout_seconds: [],
    )
    widget._scenario_system_prompt = lambda _snapshot: "system"

    assert widget._connect_ai() is True
    assert [config["provider"] for _, config in FakeManager.instances[-1].registered] == ["ollama"]


def test_openrouter_catalog_keeps_tool_capable_text_models_and_prices_per_token():
    models = GeminiSettingsDialog._parse_openrouter_models({"data": [
        {"id": "zulu", "supported_parameters": ["tools"], "architecture": {"output_modalities": ["text"]}, "pricing": {"prompt": "0.0000001", "completion": "0.0000002"}},
        {"id": "alpha", "supported_parameters": ["tools"], "architecture": {"output_modalities": ["text"]}, "pricing": {"prompt": "0.000002", "completion": "0.000004"}},
        {"id": "no-tools", "supported_parameters": [], "architecture": {"output_modalities": ["text"]}, "pricing": {"prompt": "0", "completion": "0"}},
    ]})

    assert models == [("alpha", 0.000002, 0.000004), ("zulu", 0.0000001, 0.0000002)]
    assert GeminiSettingsDialog._openrouter_model_label(*models[1]).endswith("$0.1 in / $0.2 out / 1M token")
