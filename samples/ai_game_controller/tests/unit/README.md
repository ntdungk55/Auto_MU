# Unit tests

## Mục đích

Kiểm tra domain rule và application logic mà không cần chạy game thật hoặc MCP subprocess thật.

## File dự kiến

- `test_event_detector.py`: event, debounce và cooldown.
- `test_prompt_builder.py`: nội dung prompt gửi cho AI.
- `test_execution_policy.py`: whitelist, target và giới hạn 20 tool calls.
- `test_device_scheduler.py`: chia CPU/GPU và fallback.
- `README.md`: mô tả phạm vi unit test.

External API hoặc hardware có thể được thay bằng test adapter; đối tượng đang được kiểm tra không được mock.

← [Quay lại README cha](../README.md)
