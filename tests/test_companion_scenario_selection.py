"""Lock the read-only and conditional companion scenario boundaries."""

import json
from pathlib import Path


SCENARIOS = Path(__file__).resolve().parents[1] / "scenario_engine" / "scenarios"


def _load(name: str) -> dict:
    return json.loads((SCENARIOS / name).read_text(encoding="utf-8"))


def test_read_only_companion_scenario_has_no_level_gate_or_switch_action() -> None:
    scenario = _load("get_companion_summoned_state.json")
    assert "không yêu cầu Level 400" in scenario["description"]
    assert "chỉ lấy hoặc xem" in scenario["selection_rule"]
    assert [step["tool"] for step in scenario["steps"]] == ["get_companion_summoned_state"]
    assert "key=value" in scenario["result"]["response_rule"]
    assert "companion_summoned=" not in scenario["result"]["success_message"]
    assert scenario["result"]["success_message"].startswith("Nhân vật phụ hiện tại là")


def test_conditional_switch_requires_explicit_mt_or_lv_branch() -> None:
    scenario = _load("switch_to_companion_if_level_400.json")
    steps = {step["id"]: step for step in scenario["steps"]}
    assert scenario["limits"]["max_steps"] == 7
    assert scenario["limits"]["max_tool_calls"] == 3
    assert steps["read_current_character_map"]["tool"] == "get_current_character_map"
    assert steps["check_current_map_is_varka"]["on_true"] == "complete"
    assert steps["check_current_map_is_varka"]["on_false"] == "check_requested_coordinate_condition"
    assert steps["check_requested_coordinate_condition"]["on_true"] == "read_companion_information"
    assert "current_map.position.x" in steps["check_requested_coordinate_condition"]["condition"]
    assert "yêu cầu rõ ràng đổi/chuyển" in scenario["selection_rule"]
    assert steps["check_companion_level"]["on_false"] == "check_companion_level_not_above_400"
    assert ".mt" in steps["check_companion_level"]["condition"]
    assert ".lv" in steps["check_companion_level_not_above_400"]["condition"]
    assert steps["check_companion_level_not_above_400"]["on_false"] == "failed"
    assert "companion_info.success=true" in scenario["result"]["response_rule"]
    assert "Level kết thúc bằng `.mt` phải chạy step `switch_to_companion`" in scenario["result"]["response_rule"]
    assert "tuyệt đối không dùng no_switch_message" in scenario["result"]["response_rule"]
    assert "current_map.map là Varka" in scenario["result"]["response_rule"]


def test_coordinate_condition_switch_scenario_reads_position_before_switching() -> None:
    scenario = _load("switch_to_companion_if_position.json")
    steps = {step["id"]: step for step in scenario["steps"]}

    assert scenario["limits"]["max_tool_calls"] == 2
    assert steps["read_current_character_position"]["tool"] == "get_current_character_map"
    assert any("current_map.position.x" in assertion
               for assertion in steps["read_current_character_position"]["assert"])
    assert steps["check_requested_coordinate_condition"]["on_false"] == "complete"
    assert steps["check_requested_coordinate_condition"]["on_true"] == "switch_to_companion"
    assert steps["switch_to_companion"]["tool"] == "switch_to_companion_character"


def test_system_prompt_defines_nvp_alias_and_its_safe_actions() -> None:
    prompt_path = SCENARIOS.parent / "prompt" / "system_prompt" / "scenario_engine_system_prompt.md"
    prompt = prompt_path.read_text(encoding="utf-8-sig")

    assert "`nvp`, `nv phụ` và `nhân vật phụ`" in prompt
    assert "switch_to_companion_character" in prompt
    assert "switch_to_companion_if_position" in prompt
    assert "current_map.position.x" in prompt
    assert "summon_companion_character" in prompt
    assert "phải hỏi lại" in prompt
    assert "không hỏi về Level 400" in prompt
    assert "chỉ được chọn khi và chỉ khi người dùng nêu rõ điều kiện" in prompt
    assert "vì Level tool vừa đọc là `.mt`" in prompt
