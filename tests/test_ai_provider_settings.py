import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.ui.gemini_chat_widget import GeminiSettingsDialog, GeminiChatWidget


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


def test_provider_sdk_packages_are_selected_by_provider():
    assert GeminiChatWidget._provider_package("openrouter") == "openai"
    assert GeminiChatWidget._provider_package("gemini") == "google-generativeai"


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


def test_openrouter_catalog_keeps_tool_capable_text_models_and_prices_per_token():
    models = GeminiSettingsDialog._parse_openrouter_models({"data": [
        {"id": "zulu", "supported_parameters": ["tools"], "architecture": {"output_modalities": ["text"]}, "pricing": {"prompt": "0.0000001", "completion": "0.0000002"}},
        {"id": "alpha", "supported_parameters": ["tools"], "architecture": {"output_modalities": ["text"]}, "pricing": {"prompt": "0.000002", "completion": "0.000004"}},
        {"id": "no-tools", "supported_parameters": [], "architecture": {"output_modalities": ["text"]}, "pricing": {"prompt": "0", "completion": "0"}},
    ]})

    assert models == [("alpha", 0.000002, 0.000004), ("zulu", 0.0000001, 0.0000002)]
    assert GeminiSettingsDialog._openrouter_model_label(*models[1]).endswith("$0.1 in / $0.2 out / 1M token")
