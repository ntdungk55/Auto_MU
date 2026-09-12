# Auto_MU MCP servers

Mỗi thư mục con là một MCP server độc lập dành cho chạy thủ công hoặc MCP
Inspector. Logic thật nằm trong `src/ai_control/servers`; các file `server.py`
ở đây chỉ là launcher mỏng. Không thêm `mcp/__init__.py`, vì tên đó xung đột
với package MCP SDK đã cài.

Khi mở `TestAuto.exe`, ứng dụng tự khởi động server game và tab Gemini Chat
tự lấy toàn bộ tool bằng MCP `tools/list`.

## Keyboard server

Thư mục: `mcp/keyboard`

- `get_daily_events_dialog_info`: mở Daily Events bằng `S` nếu chưa mở, verify ảnh tiêu đề rồi đọc lượt Boss, đào ngọc, BC, Devil và IG. Trả năm số nguyên trong `remaining` cùng bằng chứng OCR; trường không đọc được là null và `success=false`. Sau khi đọc (kể cả OCR lỗi), click nút X theo teaching và verify dialog đã đóng; `dialog_close.closed=false` thì báo lỗi nhưng giữ các lượt đã đọc. Script `--direct` dùng cùng hành vi này.
- `open_companion_management_dialog`: mở và verify Manage Sub-Characters, sau đó click X và verify đã đóng; không đổi nhân vật.
- `get_companion_summoned_state`: nếu slot 1 có nhân vật phụ, mở Manage Sub-Characters (hoặc dùng dialog đã mở), verify ảnh tiêu đề rồi đọc tên, Server, Map, Level, Reset và Status từ teaching. Đọc xong click nút X theo teaching và verify tiêu đề đã biến mất; vẫn đóng khi OCR lỗi. Trả `character`, bằng chứng OCR và `dialog_close`; nếu đóng thất bại, trả lỗi kèm thông tin đã đọc. Slot trống trả `companion_summoned=false`, `character=null` và không click.

Test trực tiếp tool trên window đã chọn: `.\.venv\Scripts\python.exe .\mcp\test_get_companion_dialog_info.py`. Thêm `--output build/runtime/companion_info.json` để lưu result hoặc `--diagnostic-dir build/runtime/companion_info_crops` để lưu frame dialog và từng crop OCR. Nếu game chạy Administrator thì mở PowerShell bằng quyền Administrator trước khi chạy.
- `switch_to_companion_character`: mở quản lý, verify lại title cùng nút Enter Character ngay trước click, rồi xác minh window title đổi.
- `summon_companion_character(target_character)`: xác nhận slot trống, match ảnh title Character List, OCR duy nhất tên cần triệu hồi và xác nhận bằng indicator Play/Pause. Khi cần đóng do OCR lỗi, tool verify lại title trước khi click X.

Chỉ expose 5 tool ở trên. Các tool game dùng cửa sổ được chọn trên Gemini Chat. Tool thao tác
yêu cầu xác định được một cửa sổ; Gemini Chat đồng bộ cả PID và HWND. `target_character`
là nhân vật cần triệu hồi, không dùng để chọn window hiện tại. Tọa độ, ảnh teaching và
ngưỡng title lấy từ `mcp/config/mu_game_window.json` (`dialogs` và `mainInfo`).

Trước mỗi tool, wrapper gửi một click nền `PostMessage` vào tâm client area của đúng HWND để wake game rồi mới capture; không focus window, không gửi phím và không delay. Có thể kiểm tra riêng bằng `.\.venv\Scripts\python.exe .\mcp\test_wake_game_window.py --title NTD2008`. Chỉ result có `selection_required=true` mới nghĩa là phải chọn lại cửa sổ; các lỗi verify khác giữ `selection_required=false` và phải được báo nguyên nhân thật.

Trước khi click slot nhân vật phụ, tool tìm icon slot trống trong vùng lệch cho phép. Nếu không thấy icon trống, tool phải xác nhận đồng thời indicator Play/Pause và độ sáng vùng lõi icon qua nhiều frame mới coi là đã triệu hồi. Ngưỡng sáng nằm trong `mainInfo.companionManagement1.summonedBrightnessThreshold`. Khi ảnh bị cửa sổ khác che hoặc bằng chứng không đủ, tool trả `companion_summoned=null`, `companion_state="unknown"` và không gửi click.

Các script manual dùng chung logic với MCP:

- `test_get_daily_events_dialog_info.py`: kiểm tra luồng MCP mở và đọc năm lượt Daily Events; dùng `--direct --title NTD3006` để gọi trực tiếp cùng implementation. Script in JSON bằng chứng và năm giá trị; UNKNOWN là chưa đọc được, khác với 0 lượt.
- `test_open_companion_management_dialog.py`: mở, verify rồi đóng dialog quản lý; không bấm Enter Character.
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
