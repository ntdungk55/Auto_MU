# Integration tests

## Mục đích

Kiểm tra contract và vòng đời khi nhiều thành phần làm việc cùng nhau.

## File dự kiến

- `test_game_state_mcp.py`: MCP tools đọc đúng state và event.
- `test_scenario_flow.py`: event, AI test adapter, MCP call và kết quả.
- `test_start_stop.py`: khởi động, dừng và giải phóng worker/model.
- `README.md`: mô tả phạm vi integration test.

Test phải kiểm tra MCP subprocess được đóng sạch và không để lại modifier key hoặc background worker.

← [Quay lại README cha](../README.md)
