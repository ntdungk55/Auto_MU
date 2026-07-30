# Manual Test Plan: Test Action và Status Panel

## Test Case 1: Test Action Button trong ToolEditorWindow - Chưa chọn window

**Mục đích:** Kiểm tra hiển thị dialog khi chưa chọn window game

**Điều kiện tiên quyết:**
- App đã khởi động
- Chưa chọn window game nào (combo box window trống hoặc chưa chọn)
- Có ít nhất 1 tool với 1 action

**Các bước thực hiện:**
1. Mở ToolEditorWindow (click "Sửa Tool")
2. Click nút "Test" cạnh một action bất kỳ

**Kết quả mong đợi:**
- Hiển thị dialog thông báo "Vui lòng chọn window game trước"
- Action không được thực thi

---

## Test Case 2: Test Action Button - KEYBOARD action

**Mục đích:** Kiểm tra test action loại KEYBOARD

**Điều kiện tiên quyết:**
- App đã khởi động
- Đã chọn window game (ví dụ: Notepad)
- Có tool với action KEYBOARD (ấn phím "tab")

**Các bước thực hiện:**
1. Mở Notepad và chọn nó trong combo box window
2. Mở ToolEditorWindow
3. Click nút "Test" cạnh action KEYBOARD

**Kết quả mong đợi:**
- Window game được focus
- Phím "tab" được ấn trong Notepad
- Log hiển thị "✓ Thành công" hoặc "✗ Thất bại"
- Hiển thị thời gian chạy

---

## Test Case 3: Test Action Button - MOUSE_CLICK coordinate mode

**Mục đích:** Kiểm tra test action click chuột theo tọa độ

**Điều kiện tiên quyết:**
- App đã khởi động
- Đã chọn window game
- Có tool với action MOUSE_CLICK ở chế độ tọa độ (coordinate_click_pos đã set)

**Các bước thực hiện:**
1. Chọn window game
2. Mở ToolEditorWindow
3. Click nút "Test" cạnh action MOUSE_CLICK (tọa độ)

**Kết quả mong đợi:**
- Window game được focus
- Chuột click vào tọa độ đã cấu hình
- Log hiển thị kết quả

---

## Test Case 4: Test Action Button - MOUSE_CLICK image mode

**Mục đích:** Kiểm tra test action click chuột theo hình ảnh

**Điều kiện tiên quyết:**
- App đã khởi động
- Đã chọn window game
- Có tool với action MOUSE_CLICK ở chế độ hình ảnh (có teaching image)

**Các bước thực hiện:**
1. Chọn window game
2. Mở ToolEditorWindow
3. Click nút "Test" cạnh action MOUSE_CLICK (hình ảnh)

**Kết quả mong đợi:**
- Window game được focus
- Hệ thống tìm kiếm hình ảnh trong window
- Nếu tìm thấy: click vào vị trí và log "✓ Thành công"
- Nếu không tìm thấy (timeout): log "✗ Thất bại" hoặc "TIMEOUT"

---

## Test Case 5: Test Action Button trong ActionConfigDialog

**Mục đích:** Kiểm tra nút Test trong dialog cấu hình action

**Điều kiện tiên quyết:**
- App đã khởi động
- Đã chọn window game

**Các bước thực hiện:**
1. Mở ToolEditorWindow
2. Double-click vào một action để mở ActionConfigDialog
3. Click nút "Test" (cạnh nút "Cài đặt")

**Kết quả mong đợi:**
- Action được thực thi như Test Case 2/3/4 tùy loại action
- Log hiển thị kết quả

---

## Test Case 6: Status Panel - Toggle hiển thị

**Mục đích:** Kiểm tra toggle mở/đóng Status Panel

**Điều kiện tiên quyết:**
- App đã khởi động
- Có tool trong danh sách running

**Các bước thực hiện:**
1. Add tool vào danh sách running
2. Click nút "Xem process"
3. Quan sát panel mở rộng
4. Click nút "Xem process" lần nữa
5. Quan sát panel thu gọn

**Kết quả mong đợi:**
- Click lần 1: Panel mở rộng, hiển thị danh sách action
- Click lần 2: Panel thu gọn

---

## Test Case 7: Status Panel - Highlight action đang chạy

**Mục đích:** Kiểm tra highlight action đang thực thi

**Điều kiện tiên quyết:**
- App đã khởi động
- Đã chọn window game
- Có tool với nhiều action (ít nhất 3 action)

**Các bước thực hiện:**
1. Add tool vào danh sách running
2. Click "Xem process" để mở panel
3. Click "Run" để chạy tool
4. Quan sát panel khi tool chạy

**Kết quả mong đợi:**
- Action đang chạy được highlight bằng màu nổi bật
- Khi chuyển sang action tiếp theo, highlight di chuyển theo
- Hiển thị thời gian chạy của action đang thực thi

---

## Test Case 8: Status Panel - Reset khi loop

**Mục đích:** Kiểm tra reset thời gian khi tool chuyển sang chu kỳ mới

**Điều kiện tiên quyết:**
- App đã khởi động
- Đã chọn window game
- Có tool với loop enabled

**Các bước thực hiện:**
1. Cấu hình tool với loop enabled
2. Add tool vào danh sách running
3. Click "Xem process" để mở panel
4. Click "Run" để chạy tool
5. Đợi tool hoàn thành 1 vòng và bắt đầu vòng mới

**Kết quả mong đợi:**
- Khi bắt đầu vòng mới, thời gian hiển thị reset về 0
- Highlight quay lại action đầu tiên

---

## Test Case 9: Conflict - Test Action khi tool đang chạy

**Mục đích:** Kiểm tra xử lý conflict khi test action trong khi tool đang chạy

**Điều kiện tiên quyết:**
- App đã khởi động
- Đã chọn window game
- Có tool đang chạy

**Các bước thực hiện:**
1. Chạy tool (click Run)
2. Trong khi tool đang chạy, mở ToolEditorWindow
3. Click nút "Test" cạnh một action

**Kết quả mong đợi:**
- Tool đang chạy bị dừng
- Log thông báo về việc dừng tool
- Test action được thực thi

---

## Test Case 10: Status Panel khi không có tool chạy

**Mục đích:** Kiểm tra hiển thị panel khi không có tool nào đang chạy

**Điều kiện tiên quyết:**
- App đã khởi động
- Có tool trong danh sách running nhưng không chạy (Stopped)

**Các bước thực hiện:**
1. Add tool vào danh sách running (không click Run)
2. Click "Xem process" để mở panel

**Kết quả mong đợi:**
- Panel hiển thị danh sách action
- Không có action nào được highlight
- Không hiển thị thời gian chạy

---

## Cài đặt cần kiểm tra

| Setting | Giá trị test |
|---------|--------------|
| Window game | Notepad hoặc game thực tế |
| Action KEYBOARD | value = "tab" |
| Action MOUSE_CLICK (tọa độ) | coordinate_click_pos = (100, 100) |
| Action MOUSE_CLICK (hình ảnh) | Có teaching image hợp lệ |
| Tool loop | loop_enabled = True, loop_mode = "forever" |
