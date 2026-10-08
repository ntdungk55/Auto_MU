from datetime import datetime, timedelta, timezone
import json

from src.ai_control.chat_message_log import ChatMessageLog


def _record(turn_id: str, side: str, timestamp: datetime, text: str) -> dict:
    return {
        "turn_id": turn_id,
        "side": side,
        "text": text,
        "timestamp": timestamp.isoformat(),
    }


def test_character_key_is_safe_and_separates_character_names():
    assert ChatMessageLog.character_key("MU GameThuVN - Season 21 (Golden - NTD3012)") == "NTD3012"
    assert ChatMessageLog.character_key("MU GameThuVN - Season 21 (Golden - NTD5001)") == "NTD5001"


def test_load_turn_page_returns_five_turns_and_paginates(tmp_path):
    store = ChatMessageLog(tmp_path)
    now = datetime.now(timezone.utc)
    for index in range(25):
        turn_id = f"turn-{index}"
        store.append("NTD3012", _record(turn_id, "right", now + timedelta(seconds=index * 2), f"Q{index}"))
        store.append("NTD3012", _record(turn_id, "left", now + timedelta(seconds=index * 2 + 1), f"A{index}"))

    newest, has_more = store.load_turn_page("NTD3012")
    assert len(newest) == 5
    assert newest[0][0]["text"] == "Q20"
    assert newest[-1][-1]["text"] == "A24"
    assert has_more is True

    older, has_more = store.load_turn_page("NTD3012", offset=5)
    assert len(older) == 5
    assert older[0][0]["text"] == "Q15"
    assert older[-1][-1]["text"] == "A19"
    assert has_more is True

    oldest, has_more = store.load_turn_page("NTD3012", offset=20)
    assert len(oldest) == 5
    assert oldest[0][0]["text"] == "Q0"
    assert oldest[-1][-1]["text"] == "A4"
    assert has_more is False


def test_purge_expired_removes_inactive_character_history(tmp_path):
    store = ChatMessageLog(tmp_path)
    now = datetime.now(timezone.utc)
    store.append("Inactive", _record("old", "right", now - timedelta(days=8), "old"))
    store.append("Active", _record("new", "right", now, "new"))

    store.purge_expired(now=now)

    assert store.load_turn_page("Inactive")[0] == []
    assert store.load_turn_page("Active")[0][0][0]["text"] == "new"
    assert not (tmp_path / "Inactive").exists()


def test_malformed_lines_do_not_break_history(tmp_path):
    store = ChatMessageLog(tmp_path)
    directory = tmp_path / "NTD3012"
    directory.mkdir()
    path = directory / "2026-09-26.jsonl"
    path.write_text("not json\n" + json.dumps(_record("turn", "right", datetime.now(timezone.utc), "ok")) + "\n", encoding="utf-8")

    page, _ = store.load_turn_page("NTD3012")

    assert page[0][0]["text"] == "ok"
