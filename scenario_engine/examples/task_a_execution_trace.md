# Ví dụ thực thi việc A

## Yêu cầu của người dùng

```text
Chọn process game main.exe rồi nhấn Enter.
```

## Trường hợp 1: chỉ tìm thấy một process

1. Scenario Engine chọn scenario `task_a_select_and_press_enter`.
2. Scenario nạp skill `select_game_and_press_key`.
3. AI/MCP gọi:

   ```json
   {
     "tool": "select_game_process",
     "arguments": {
       "process_name": "main.exe"
     }
   }
   ```

4. Process MCP trả về một PID, ví dụ `4520`; Scenario Engine lưu kết quả vào
   biến `process_selection`.
5. Engine gọi `get_selected_process_info` và kiểm tra:

   - Process còn sống.
   - PID chưa bị process khác sử dụng lại.
   - Process có ít nhất một cửa sổ hiển thị.

6. Khi toàn bộ điều kiện đúng, engine gọi:

   ```json
   {
     "tool": "run_keyboard_action",
     "arguments": {
       "value": "enter",
       "text_input_enabled": false,
       "delay_seconds": 0.2
     }
   }
   ```

7. Keyboard MCP chỉ gửi Enter tới cửa sổ thuộc PID `4520`.
8. Nếu MCP trả `ok=true`, scenario kết thúc với trạng thái `complete`.

## Trường hợp 2: có nhiều process main.exe

1. `select_game_process` trả `selection_required=true` cùng danh sách ứng viên.
2. Engine chuyển sang step `ask_user_for_pid`.
3. AI hiển thị PID và tiêu đề cửa sổ, sau đó hỏi người dùng chọn PID.
4. AI không được tự chọn ngẫu nhiên.
5. Sau khi người dùng chọn, engine gọi lại `select_game_process` bằng PID rồi
   tiếp tục bước xác minh và nhấn Enter.

## Trường hợp 3: process tắt trước khi nhấn phím

1. `get_selected_process_info` trả `ok=false` hoặc `stale=true`.
2. Engine dừng trước step `run_keyboard_action`.
3. AI thông báo process không còn hợp lệ và yêu cầu người dùng chọn lại.

## Những giới hạn chống chạy sai

- Tối đa 20 MCP tool call cho toàn scenario.
- Skill này chỉ được dùng ba MCP tool đã khai báo.
- Mỗi step chỉ retry tối đa một lần.
- Không có vòng lặp vô hạn.
- Không gửi phím nếu process chưa được chọn và xác minh.

