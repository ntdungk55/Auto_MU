# Application

## Mục đích

Chứa use case và phần điều phối luồng event. Layer này không chụp màn hình, không gọi Gemini SDK và không gửi phím trực tiếp.

## File dự kiến

- `scenario_engine.py` — `ScenarioEngine`: điều phối event, AI decision, MCP calls và xác minh.
- `event_detector.py` — `EventDetector`: chuyển state transition thành game event.
- `prompt_builder.py` — `PromptBuilder`: ghép system prompt, scenario, event và game state.
- `execution_policy.py` — `ExecutionPolicy`: kiểm tra allowed tools, target và giới hạn 20 tool calls.
- `process_controller.py` — `ProcessController`: quản lý Start, Stop, Restart và Emergency Stop.
- `README.md`: mô tả phạm vi của application.

## Quy tắc phụ thuộc

- Được phụ thuộc vào `domain`.
- Chỉ gọi infrastructure thông qua dependency được truyền vào constructor.
- Không chứa code phụ thuộc trực tiếp vào PyQt hoặc MCP SDK.

← [Quay lại README cha](../README.md)
