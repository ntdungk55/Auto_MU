# Domain

## Mục đích

Chứa model và quy tắc nghiệp vụ thuần. Code trong đây không phụ thuộc PyQt, Gemini, EasyOCR, OpenVINO hoặc MCP SDK.

## File dự kiến

- `game_state.py` — `GameState`: snapshot OCR bất biến của một game window.
- `game_event.py` — `GameEvent`: state transition có thể kích hoạt một lượt xử lý AI.
- `scenario.py` — `Scenario`: prompt người dùng, target, event, allowed tools và giới hạn thực thi.
- `README.md`: mô tả phạm vi của domain.

## Quy tắc phụ thuộc

- Không import UI hoặc infrastructure.
- Không đọc file, gọi network, chụp màn hình hoặc gửi input.
- Model phải có thể kiểm thử mà không cần khởi động game hay AI.

← [Quay lại README cha](../README.md)
