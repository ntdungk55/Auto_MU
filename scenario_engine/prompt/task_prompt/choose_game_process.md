# Prompt: choose_game_process

Bạn đang hỗ trợ Scenario Engine chọn đúng process game.

## Input

- Danh sách process ứng viên do `select_game_process` trả về.
- Mỗi ứng viên có thể gồm PID, tên executable, đường dẫn và danh sách cửa sổ.

## Quy tắc

1. Không tự chọn ngẫu nhiên khi có nhiều ứng viên.
2. Trình bày PID, tên process và tiêu đề cửa sổ để người dùng phân biệt.
3. Hỏi người dùng chọn đúng một PID.
4. Không gọi `run_keyboard_action` trước khi process đã được xác minh còn sống.
5. Nếu process đã tắt hoặc PID bị tái sử dụng, yêu cầu chọn lại.
6. Chỉ trả về PID có trong danh sách ứng viên.

## Output mong muốn

```json
{
  "decision": "selected",
  "pid": 1234
}
```

Nếu chưa đủ thông tin:

```json
{
  "decision": "ask_user",
  "message": "Có nhiều process main.exe. Bạn muốn chọn PID nào?"
}
```

