# System prompts

## Mục đích

Chứa system prompt dùng chung cho mọi AI provider/model trong sample.

## File dự kiến

- `game_controller.md`: vai trò AI, giới hạn quyền và cách sử dụng MCP tools.
- `event_handling_rules.md`: quy tắc xác minh state, chống vòng lặp và kết thúc event.
- `README.md`: mô tả phạm vi của system prompt.

## Quy tắc

- Provider/model khác nhau vẫn dùng cùng một system prompt.
- Không nhúng API key hoặc dữ liệu runtime vào file prompt.
- Thay đổi prompt phải có version và test tương ứng trong Prompt Builder.

← [Quay lại README cha](../README.md)
