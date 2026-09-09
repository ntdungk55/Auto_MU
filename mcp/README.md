# Auto_MU MCP servers

Mỗi thư mục con là một MCP server độc lập dành cho chạy thủ công hoặc MCP
Inspector. Logic thật nằm trong `src/ai_control/servers`; các file `server.py`
ở đây chỉ là launcher mỏng. Không thêm `mcp/__init__.py`, vì tên đó xung đột
với package MCP SDK đã cài.

Khi mở `TestAuto.exe`, ứng dụng tự khởi động cả hai server và tab Gemini Chat
tự lấy toàn bộ tool bằng MCP `tools/list`.

## Keyboard server

Thư mục: `mcp/keyboard`

- `keyboard_action_schema`
- `create_keyboard_action`
- `validate_keyboard_action`
- `list_game_windows`
- `run_keyboard_action`

`list_game_windows` và `run_keyboard_action` chỉ dùng các cửa sổ thuộc process
đã được Process server chọn.

```powershell
& ".venv\Scripts\mcp.exe" run "mcp\keyboard\server.py:mcp" --transport stdio
& ".venv\Scripts\mcp.exe" dev "mcp\keyboard\server.py"
```

## Process server

Thư mục: `mcp/process`

- `select_game_process`: chọn theo PID, hoặc tìm theo tên process/tiêu đề cửa sổ.
- `get_selected_process_info`: kiểm tra process đang chọn, trạng thái sống và các cửa sổ.

Nếu tìm theo tên/tiêu đề mà có nhiều kết quả, server trả danh sách ứng viên để
AI gọi lại bằng PID; server không tự chọn ngẫu nhiên. Lựa chọn được chia sẻ qua
`build/runtime/selected_process.json` và được kiểm tra lại để phát hiện process
đã tắt hoặc PID bị tái sử dụng.

```powershell
& ".venv\Scripts\mcp.exe" run "mcp\process\server.py:mcp" --transport stdio
& ".venv\Scripts\mcp.exe" dev "mcp\process\server.py"
```
