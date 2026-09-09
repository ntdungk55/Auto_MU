# Logs

## Mục đích

Chứa JSONL log sinh ra khi chạy sample. Không dùng thư mục này làm kênh chia sẻ state giữa các process.

## File runtime dự kiến

- `events.jsonl`: các game event đã phát sinh.
- `agent_calls.jsonl`: metadata prompt, AI decision và MCP calls.
- `errors.jsonl`: lỗi OCR, MCP hoặc model.
- `README.md`: mô tả định dạng và phạm vi log.

## Quy tắc

- Không ghi API key hoặc secret.
- Mỗi dòng phải là một JSON object hoàn chỉnh.
- Log runtime không được commit.

← [Quay lại README cha](../README.md)
