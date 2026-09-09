# Auto_MU Scenario Engine

Đây là bộ khung cấu hình cho Scenario Engine. System prompt dùng chung đã được
tab AI Chat nạp qua AI Model Factory. Các file scenario/skill mô tả rõ AI
**phải làm gì**, nhưng hiện chưa có executor tự động đọc/chạy chúng.

## Vai trò từng thư mục

- `scenarios/`: mục tiêu hoàn chỉnh do người dùng yêu cầu.
- `skills/`: quy trình nhỏ có thể tái sử dụng trong nhiều scenario.
- `prompt/system_prompt/`: luật toàn cục hướng dẫn AI vận hành Scenario Engine.
- `prompt/task_prompt/`: prompt chuyên biệt được gọi tại từng step AI.
- `examples/`: bản mô phỏng từng bước để kiểm tra thiết kế trước khi viết engine.

## Luồng dự kiến

```text
User command
    -> Scenario Engine chọn scenario
    -> Scenario nạp skill
    -> Skill gọi MCP tools
    -> MCP server thực thi action
    -> Scenario Engine kiểm tra kết quả
    -> Chuyển step, hỏi lại user hoặc kết thúc
```

## Ví dụ hiện có

Người dùng yêu cầu:

```text
Chọn process game main.exe rồi nhấn Enter.
```

Scenario tương ứng là `scenarios/task_a_select_and_press_enter.json`. Scenario
này gọi skill `skills/select_game_and_press_key.json`, sử dụng ba MCP tool:

1. `select_game_process`
2. `get_selected_process_info`
3. `run_keyboard_action`

Xem `examples/task_a_execution_trace.md` để thấy đầy đủ AI sẽ làm gì trong
trường hợp tìm thấy một process, nhiều process hoặc process đã tắt.

System prompt chính nằm tại
`prompt/system_prompt/scenario_engine_system_prompt.md`. Nội dung file này được
nạp làm system instruction khi tạo phiên chat mới và được dùng chung cho mọi
AI model adapter.

## AI Model Factory

Scenario Engine và vòng lặp MCP chỉ làm việc với contract chung trong
`src/ai_control/ai_models/contracts.py`. Provider hiện có là Gemini. Muốn thêm
provider mới, tạo một `AIModelAdapter` rồi đăng ký constructor với
`AIModelFactory`; system prompt vẫn được `SystemPromptLoader` nạp từ đúng file
chung ở trên.
