from src.ai_control.servers import notifications


def test_send_telegram_message_rejects_empty_message() -> None:
    assert notifications.send_telegram_message("") == {
        "success": False,
        "error": "message must be a non-empty string",
    }


def test_send_telegram_message_uses_configured_sender(monkeypatch) -> None:
    monkeypatch.setattr(
        notifications,
        "send_configured_message",
        lambda message: (True, ""),
    )

    assert notifications.send_telegram_message("HP thấp") == {"success": True}
