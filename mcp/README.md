# Auto_MU MCP servers

Mỗi thư mục con là một MCP server độc lập dành cho chạy thủ công hoặc MCP
Inspector. Logic thật nằm trong `src/ai_control/servers`; các file `server.py`
ở đây chỉ là launcher mỏng. Không thêm `mcp/__init__.py`, vì tên đó xung đột
với package MCP SDK đã cài.

Khi mở `TestAuto.exe`, ứng dụng tự khởi động server game và tab Gemini Chat
tự lấy toàn bộ tool bằng MCP `tools/list`.

## Keyboard server

Thư mục: `mcp/keyboard`

- `get_daily_events_dialog_info`: mở Daily Events bằng `S` nếu chưa mở, verify ảnh tiêu đề rồi đọc lượt Boss, đào ngọc, BC, Devil và IG. Trả năm số nguyên trong `remaining` cùng bằng chứng OCR; trường không đọc được là null và `success=false`. Giữ dialog mở sau khi đọc.
- `open_companion_management_dialog`: mở và verify Manage Sub-Characters, không đổi nhân vật.
- `get_companion_summoned_state`: nếu slot 1 có nhân vật phụ, mở Manage Sub-Characters (hoặc dùng dialog đã mở), verify ảnh tiêu đề rồi đọc tên, Server, Map, Level, Reset và Status từ teaching. Đọc xong click nút X theo teaching và verify tiêu đề đã biến mất; vẫn đóng khi OCR lỗi. Trả `character`, bằng chứng OCR và `dialog_close`; nếu đóng thất bại, trả lỗi kèm thông tin đã đọc. Slot trống trả `companion_summoned=false`, `character=null` và không click.
- `switch_to_companion_character`: mở quản lý, bấm Enter Character và xác minh window title đổi.
- `summon_companion_character(target_character)`: match ảnh title Character List, OCR tên cần triệu hồi và xác nhận bằng icon slot.

Chỉ expose 5 tool ở trên. Các tool game dùng cửa sổ được chọn trên Gemini Chat. Tool thao tác
yêu cầu xác định được một cửa sổ; Gemini Chat đồng bộ cả PID và HWND. `target_character`
là nhân vật cần triệu hồi, không dùng để chọn window hiện tại. Tọa độ, ảnh teaching và
ngưỡng title lấy từ `mcp/config/mu_game_window.json` (`dialogs` và `mainInfo`).

Các script manual dùng chung logic với MCP:

- `test_get_daily_events_dialog_info.py`: kiểm tra luồng MCP mở và đọc năm lượt Daily Events; dùng `--direct --title NTD3006` để gọi trực tiếp cùng implementation. Script in JSON bằng chứng và năm giá trị; UNKNOWN là chưa đọc được, khác với 0 lượt.
- `test_open_companion_management_dialog.py`: chỉ mở/verify dialog quản lý; không bấm Enter Character.
- `test_template_match_companion_dialog.py`: đổi nhân vật; `--check-companion-state` chỉ đọc trạng thái.
- `test_summon_companion_character.py`: triệu hồi; `--teach-title-template` chỉ có ở script manual, không expose cho AI.

`src/ai_control/companion_switcher.py` và `companion_summoner.py` giữ logic dùng chung;
MCP không chạy lại script CLI bằng subprocess. Các scenario tương ứng nằm trong
`scenario_engine/scenarios`. Sau khi cập nhật code, khởi động lại phiên MCP để nạp tool mới.

```powershell
& ".venv\Scripts\mcp.exe" run "mcp\keyboard\server.py:mcp" --transport stdio
& ".venv\Scripts\mcp.exe" dev "mcp\keyboard\server.py"
```

## Target selection and scenario catalog

Process selection is internal application code, not an MCP tool. The app persists
PID, creation time and HWND in `build/runtime/selected_process.json`; game tools
revalidate this selection before acting. No Process MCP server starts by default.

There is no `list_scenario`, `list_scenarios` or `list_senario` tool. The five scenario
JSON files are loaded into the chat prompt when a session starts. Reconnect the
chat to refresh both the scenario catalog and MCP tools after code changes.
