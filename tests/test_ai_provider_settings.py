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
    assert dialog.model_combo.findText("google/gemini-2.5-flash") >= 0
    dialog.save_model()
    assert saved_models == [("openrouter", "google/gemini-2.5-flash")]


def test_provider_sdk_packages_are_selected_by_provider():
    assert GeminiChatWidget._provider_package("openrouter") == "openai"
    assert GeminiChatWidget._provider_package("gemini") == "google-generativeai"
